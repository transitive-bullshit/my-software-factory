"""Word-timed captions for the fully generative cut -> captions/captions.json (the caption layer's one source).

Each line's text is the locked parody line (data/script.json). Each word's time is force-aligned (torchaudio's MMS
aligner, the known words against the audio) in the read it was cut from: the DI and fire watch reads (data/voices.json)
as they are, the chorus take (media/voices/chorus-music/<variant>/) on its vocal stem, separated once and cached next to
the take. Whisper only finds where each line sits in its read. Times are then shifted to where that read sits on the
generative cut's timeline (data/di-gen.json, data/chorus.json) and onto the rendered cut (scripts/full.py spans: it
drops 98.5–99.2 s). A line's first word starts at its measured audible onset, its last word ends at the audible end.

Run this when the audio changes; edit captions/captions.json by hand for wording or timing tweaks, then re-render with
`npm run captions` in captions/.

  uv run --group analysis --group voice --group gen python scripts/captions.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from audio import ROOT, decode, find_line, norm, whisper_words  # noqa: E402
from di import edges  # noqa: E402
import full  # noqa: E402

OUT = ROOT / "captions" / "captions.json"
# how a line reads on screen when the script spells it for the voice
DISPLAY = {"A-I": "AI", "A-S-I": "ASI"}
SPEAKER = {"D": "jensen", "F": "firewatch", "C": "chorus", "R": "chorus"}
LEAD, HOLD, GAP = 0.12, 0.7, 0.04  # caption shows this early, lingers this long after the last word, gap before the next


def forced(items: list[tuple[Path, float, float, list[str], bool]]) -> list[list[tuple[float, float]]]:
  """(start, end) per word for known words in audio windows (file, from, to, words, from_onset): torchaudio's MMS forced
  aligner, in its own process (torch apart from MLX). A trailing star soaks up whatever follows the line; a leading one
  too, unless the window starts at the line's measured onset (then the first word starts there, not a syllable late)."""
  code = """
import json, sys, numpy as np, soundfile as sf, torch, torchaudio
b = torchaudio.pipelines.MMS_FA
model, tokenize, align = b.get_model(with_star=True), b.get_tokenizer(), b.get_aligner()
audio, out = {}, []
for f, lo, hi, words, at_onset in json.loads(sys.stdin.read()):
  if f not in audio:
    y, sr = sf.read(f, dtype="float32")
    y = y.mean(axis=1) if y.ndim > 1 else y
    audio[f] = torchaudio.functional.resample(torch.from_numpy(np.ascontiguousarray(y)), sr, 16000)
  seg = audio[f][max(0, int(lo * 16000)):int(hi * 16000)].unsqueeze(0)
  with torch.inference_mode():
    em, _ = model(seg)
  spans = align(em[0], tokenize([*([] if at_onset else ["*"]), *words, "*"]))[0 if at_onset else 1:-1]
  r = seg.size(1) / em.size(1) / 16000
  out.append([[max(0, lo) + w[0].start * r, max(0, lo) + w[-1].end * r] for w in spans])
print(json.dumps(out))
"""
  clean = lambda t: "".join(c for c in t.lower() if c.isalpha() or c == "'")
  payload = [[str(f), lo, hi, [clean(w) for w in words], at] for f, lo, hi, words, at in items]
  run = subprocess.run([sys.executable, "-c", code], input=json.dumps(payload), capture_output=True, text=True)
  if run.returncode:
    sys.exit(run.stderr[-2000:])
  return json.loads(run.stdout.strip().splitlines()[-1])


def fill(times: list[tuple[float, float] | None], a: float, b: float) -> list[list[float]]:
  """Clamp into the line's audible span [a, b], interpolate unmatched tokens, keep times increasing."""
  n = len(times)
  known = [i for i, t in enumerate(times) if t]
  res: list[list[float]] = []
  for i, t in enumerate(times):
    if t:
      s, e = t
    else:  # between the nearest matched neighbours (or the line edges)
      prev = max((k for k in known if k < i), default=None)
      nxt = min((k for k in known if k > i), default=None)
      lo = times[prev][1] if prev is not None else a
      hi = times[nxt][0] if nxt is not None else b
      span = (hi - lo) / ((nxt if nxt is not None else n) - (prev if prev is not None else -1))
      s = lo + span * (i - (prev if prev is not None else -1) - 1)
      e = s + span
    res.append([max(a, min(b, s)), max(a, min(b, e))])
  res[0][0] = a  # the first word starts at the audible onset
  res[-1][1] = max(res[-1][1], min(b, res[-1][1] + 0.05)) if n > 1 else b
  res[-1][1] = b
  for i in range(1, n):
    res[i][0] = max(res[i][0], res[i - 1][0] + 0.02)
    end = max(res[i - 1][1], res[i - 1][0] + 0.06)
    # a word stays lit until the next one starts, across a short breath (aligned spans end early)
    res[i - 1][1] = res[i][0] if res[i][0] - end < 0.35 else min(end, res[i][0])
  return res


def vocal_env(take: Path, hop: float = 0.005) -> tuple[np.ndarray, float]:
  """RMS envelope of the take's vocal stem (MelBand RoFormer in its own process, cached next to the take)."""
  stem = take.with_name(take.stem + ".vocals.wav")
  if not stem.exists():
    subprocess.run([sys.executable, "-c", f"""
from audio_separator.separator import Separator
s = Separator(output_dir={str(take.parent)!r}, output_format="WAV")
s.load_model(model_filename="vocals_mel_band_roformer.ckpt")
s.separate({str(take)!r}, custom_output_names={{"Vocals": {take.stem + ".vocals"!r}, "Other": {take.stem + ".bed"!r}}})
"""], check=True, capture_output=True)
  y, sr = sf.read(stem)
  y = y.mean(axis=1) if y.ndim > 1 else y
  n, w = int(sr * hop), int(sr * 0.02)
  return np.sqrt(np.convolve(y ** 2, np.ones(w) / w, mode="same"))[::n], hop


def onset(env: np.ndarray, hop: float, lo: float, hi: float, peak: float, rel: float = 0.1) -> float | None:
  """Where the line's first sustained rise crosses rel x its peak (-20 dB, as di.edges) in [lo, hi], once any tail of the line
  before has decayed below that."""
  lo = max(0.0, lo)
  seg = env[int(lo / hop):int(hi / hop)]
  thr = rel * peak
  quiet = np.nonzero(seg < thr)[0]
  if not len(quiet):
    return None
  for i in range(quiet[0], len(seg) - 8):
    if (seg[i:i + 8] > thr).all():  # 40 ms
      return lo + i * hop
  return None


def to_cut(t: float, sp: dict, starts: dict) -> float:
  """Source-clip seconds -> seconds in the rendered generative cut."""
  for sid, (a, b) in sp.items():
    if a <= t < b:
      return starts[sid] + t - a
  last = list(sp)[-1]
  if t >= sp[last][1]:
    return starts[last] + t - sp[last][0]
  # inside dropped time: snap to the next shot's start
  nxt = min((sid for sid, (a, _) in sp.items() if a > t), key=lambda s: sp[s][0])
  return starts[nxt]


def main() -> None:
  script = json.loads((ROOT / "data" / "script.json").read_text())
  by_id = {ln["id"]: ln for ln in script["lines"]}
  voices = json.loads((ROOT / "data" / "voices.json").read_text())
  di = json.loads((ROOT / "data" / "di-gen.json").read_text())["lines"]
  chorus = json.loads((ROOT / "data" / "chorus.json").read_text())
  sp, starts = full.spans("generative"), full.out_start("generative")
  timed: dict[str, list[list[float]]] = {}

  # where each line sits: Whisper finds it in its read; the audible edges and the cut placement give its span
  jobs = []  # (line id, audio window, line span in the read, placed span, where the read's audio starts to sound)
  reads = [*voices["di"]["reads"], {"file": voices["fireWatch"]["read"], "lines": ["F01"]}]
  for cfg in reads:  # solo reads: clean, so the audible edges are the line's onset and end
    path = ROOT / cfg["file"]
    words, y = whisper_words(path), decode(path)
    cursor = 0
    for lid in cfg["lines"]:
      hit = find_line(words, by_id[lid]["parody"], cursor)
      if not hit:
        sys.exit(f"{lid}: not found in {path.name}")
      a, b = edges(y, words, hit[0], hit[1])
      jobs.append((lid, (path, a - 0.03, b + 0.12, True), (a, b), di[lid]["placed"], a))
      cursor = hit[1] + 1

  # the chorus take: a line's raw start is a cut point; the singing's onset is measured on the take's vocal stem
  take_dir = ROOT / "media" / "voices" / "chorus-music" / chorus["variant"]
  stem = take_dir / "full.stereo.vocals.wav"
  env, hop = vocal_env(take_dir / "full.stereo.wav")
  for lid, c in chorus["lines"].items():
    (ra, rb) = c["raw"]
    peak = env[int(ra / hop):int(rb / hop)].max()
    sung = onset(env, hop, ra - 0.15, min(rb, ra + 1.2), peak)
    win = (stem, sung - 0.03, rb + 0.12, True) if sung is not None else (stem, ra - 0.15, rb + 0.12, False)
    jobs.append((lid, win, (ra, rb), c["placed"], sung))

  # every word, force-aligned in its read, then shifted onto the cut's source timeline
  aligned = forced([(f, lo, hi, by_id[lid]["parody"].split(), at) for lid, (f, lo, hi, at), *_ in jobs])
  for (lid, _, (ra, rb), (pa, pb), sung), words in zip(jobs, aligned):
    shift = pa - ra
    start = sung if sung is not None else words[0][0]  # the measured onset, else where the aligner hears the first word
    timed[lid] = fill([(s + shift, e + shift) for s, e in words], start + shift, pb)
    if abs(start + shift - pa) > 0.08:
      print(f"{lid}: first word {start + shift - pa:+.2f} s from the cut point")

  lines = []
  for lid in sorted(timed, key=lambda k: timed[k][0][0]):
    tokens = by_id[lid]["parody"].split()
    words = [{"text": DISPLAY.get(t.rstrip(".,!?"), t.rstrip(".,!?")) + t[len(t.rstrip(".,!?")):],
              "start": round(to_cut(s, sp, starts), 3), "end": round(to_cut(e, sp, starts), 3)} for t, (s, e) in zip(tokens, timed[lid])]
    first = words[0]["start"]
    shot = max((sid for sid in sp if starts[sid] <= first + 1e-6), key=lambda k: starts[k])  # the shot the line starts in
    lines.append({"id": lid, "shot": shot.split("-")[0], "speaker": SPEAKER[lid[0]], "words": words})

  # when each line shows: a beat before its first word, lingering after its last, never overlapping the next
  body_end = sum(b - a for a, b in sp.values())
  for i, ln in enumerate(lines):
    prev_end = lines[i - 1]["words"][-1]["end"] if i else 0.0
    first = ln["words"][0]["start"]
    ln["in"] = round(min(first, max(0.0, first - LEAD, prev_end + GAP)), 3)  # never after its first word
  for i, ln in enumerate(lines):
    nxt = lines[i + 1]["in"] - GAP if i + 1 < len(lines) else body_end + 0.3
    ln["out"] = round(min(ln["words"][-1]["end"] + HOLD, nxt), 3)  # never on screen with the next line
    for w in ln["words"]:  # where sung lines overlap, the earlier one hands over at the next one's entrance
      w["end"] = min(w["end"], ln["out"])
      w["start"] = min(w["start"], w["end"])

  OUT.parent.mkdir(parents=True, exist_ok=True)
  OUT.write_text(json.dumps({
    "$comment": ("Captions for renders/full/generative.mp4, times in seconds of that cut. Edit text or timings here, "
                 "then `npm run captions` in captions/. Regenerated from the audio by scripts/captions.py."),
    "video": "renders/full/generative.mp4",
    "lines": lines,
  }, indent=1) + "\n")
  for ln in lines:
    print(f"{ln['id']:4} {ln['in']:6.2f}-{ln['out']:6.2f}  " + " ".join(f"{w['text']}@{w['start']:.2f}" for w in ln["words"]))


if __name__ == "__main__":
  main()
