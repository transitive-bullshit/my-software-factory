"""Solo lines (Jensen's D01–D07 and the fire watch's F01) from their approved reads, placed on the timeline, then the
full review pass (chorus + solos).

Reads come from data/voices.json: di.reads (each with the lines it contains) and fireWatch.read. The audio is never
re-timed: no stretching, squeezing or re-spacing (it always sounds worse than the raw read). A read is cut as ONE
piece from its first line's audible start to its last line's end and starts on its first line's slot; lines inside
a multi-line read keep the read's own cadence, and the timeline adapts. A line with no lip sync to hit (off screen,
silhouette, back to camera) may start a little early to clear the next speaker.

A read may also be placed off its slot on purpose (PLACE), and a variant cut can move reads on its own timeline
(VARIANTS): `--variant NAME` writes data/di-NAME.json, media/voices/di/di[-dry]-NAME.wav and the full-pass-NAME mix.

  uv run --group analysis --group voice python scripts/di.py [--variant gen]
"""

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, lfilter

sys.path.insert(0, str(Path(__file__).parent))
from audio import END_HOLD, ROOT, SR, decode, find_line, place, render_pass, tail_ir, whisper_words  # noqa: E402

OUT = ROOT / "media" / "voices" / "di"
# lines with no lip sync to hit (off screen, silhouette, back to camera) may start early instead of being squeezed
EARLY_OK = {"D04": 0.3, "D06": 0.3, "D07": 0.6}
PRE, POST = 0.02, 0.12
IN_LINE, WET_HP = 0.0, 200.0  # reverb while a line is said (none: the word stays as clean as the raw take; it rings out fully after), and the tail's high-pass (Hz)
# reads placed off their slot on purpose: where the read starts (source-clip seconds)
PLACE = {"D01": 39.8}  # author: "Prompt!" came too late in S07 (slot 40.65)
# variant timelines: the fully generative cut gets to "Auto-merge!" sooner (author), 1 s after "Push!" ends; its S13
# shortens to match (scripts/full.py). The base timeline keeps the film's timing (the timing and voice review pages).
VARIANTS = {"gen": {"D05": 95.6}}


def edges(y: np.ndarray, words: list[dict], s0: int, s1: int) -> tuple[float, float]:
  """Audible start and end of the words s0..s1, searched between the neighbouring words."""
  a, b = words[s0]["start"], words[s1]["end"]
  lo = max(0.0, (words[s0 - 1]["end"] + 0.02) if s0 > 0 else a - 0.3, a - 0.3)
  hi = min(len(y) / SR, (words[s1 + 1]["start"] - 0.02) if s1 + 1 < len(words) else b + 0.4, b + 0.4)
  wide = y[int(lo * SR) : int(hi * SR)]
  hop = int(0.005 * SR)
  env = np.array([np.abs(wide[k : k + hop]).max() for k in range(0, len(wide) - hop, hop)])
  loud = np.nonzero(env > 0.1 * env.max())[0]
  tail = np.nonzero(env > 0.03 * env.max())[0]
  return lo + loud[0] * hop / SR, lo + (tail[-1] + 1) * hop / SR


def held(n: int, spans: list[list[float]], w0: float, ramp: float = 0.03) -> np.ndarray:
  """Reverb gain over the track: IN_LINE while any line is being said, 1 elsewhere, with smoothed edges."""
  g = np.ones(n, np.float32)
  for a, b in spans:
    g[max(0, int((a - w0) * SR)) : max(0, int((b - w0) * SR))] = IN_LINE
  k = int(ramp * SR)
  return np.convolve(g, np.ones(k) / k, "same").astype(np.float32)


def main(variant: str | None = None) -> None:
  moved = {**PLACE, **VARIANTS.get(variant, {})}
  sfx = f"-{variant}" if variant else ""
  script = json.loads((ROOT / "data" / "script.json").read_text())
  voices = json.loads((ROOT / "data" / "voices.json").read_text())
  OUT.mkdir(parents=True, exist_ok=True)
  by_id = {ln["id"]: ln for ln in script["lines"]}
  w0, w1 = script["window"]["start"], script["window"]["end"]
  n = int((w1 - w0 + END_HOLD + 0.5) * SR)
  onsets = sorted(ln["start"] for ln in script["lines"])
  reads = list(voices["di"]["reads"])
  if voices.get("fireWatch", {}).get("read"):
    reads.append({"file": voices["fireWatch"]["read"], "lines": ["F01"]})

  track = np.zeros(n, np.float32)
  placed: dict[str, dict] = {}
  for cfg in reads:
    path = ROOT / cfg["file"]
    y = decode(path)
    words = whisper_words(path)
    found, cursor = [], 0
    for lid in cfg["lines"]:
      hit = find_line(words, by_id[lid]["parody"], cursor)
      if not hit:
        sys.exit(f"{lid}: not found in {path.name}")
      found.append((lid, *edges(y, words, hit[0], hit[1])))
      cursor = hit[1] + 1

    a0, b1 = found[0][1], found[-1][2]
    first = by_id[found[0][0]]
    nxt = next((t for t in onsets if t > by_id[found[-1][0]]["start"] + 0.05), w1 + END_HOLD)
    overrun = (first["start"] + b1 - a0) - (nxt - 0.08)  # would the read run into whoever speaks next?
    shift = min(EARLY_OK.get(first["id"], 0.0), max(0.0, overrun))
    start = moved.get(first["id"], first["start"] - shift)
    clip = y[int(max(0, a0 - PRE) * SR) : int(min(len(y) / SR, b1 + POST) * SR)]
    k = int((start - PRE - w0) * SR)
    track[k : k + len(clip)] += clip[: n - k]
    for lid, a, b in found:
      placed[lid] = {"placed": [round(start + a - a0, 3), round(start + b - a0, 3)], "slot": [by_id[lid]["start"], by_id[lid]["end"]],
                     "natural": round(b - a, 3), "source": cfg["file"]}
      print(f"{lid} {by_id[lid]['parody']:30} {placed[lid]['placed'][0]:7.2f}-{placed[lid]['placed'][1]:7.2f}  "
            f"slot {by_id[lid]['start']:7.2f}  ({placed[lid]['placed'][0] - by_id[lid]['start']:+.2f}s)  [{path.name}]")
    if overrun - shift > 0.01:
      print(f"  ! {cfg['file']} runs {overrun - shift:.2f}s into the next line")

  (ROOT / "data" / f"di{sfx}.json").write_text(json.dumps(
    {"$comment": "Where each solo line sounds, in source-clip seconds (meme time = placed - window.start). Written by scripts/di.py.",
     "lines": placed}, indent=2) + "\n")

  sf.write(OUT / f"di-dry{sfx}.wav", track, SR)  # the raw reads on the timeline: drives lip sync

  # same barracks, close to the camera: the raw read plus the room's tail. No early reflections or air damping: their
  # 3.6–18 ms copies comb-filtered the voice, and with the tail filling the short silences inside words, "Prompt!" came
  # out as "Pront" (author, rounds 3–4). No tail while a line is said; it rings out once the line ends, as loud as
  # before, with its lowest end (which rings longest) trimmed.
  st, send = place(track, 2.5, 0.4, reflections=False, damp=False)  # in-line, the voice is the raw read, panned
  ir = tail_ir()
  wet = np.stack([fftconvolve(send, ir[:, c])[: len(send)] for c in range(2)], 1)
  wet = lfilter(*butter(2, WET_HP / (SR / 2), "high"), wet, axis=0)
  wet = wet / (np.abs(wet).max() + 1e-9) * held(len(wet), [v["placed"] for v in placed.values()], w0)[:, None]
  solo = st + 0.18 * wet * np.abs(st).max()
  solo = (solo / (np.abs(solo).max() + 1e-9) * 0.8).astype(np.float32)[:n]
  sf.write(OUT / f"di{sfx}.wav", solo, SR)
  print(render_pass(f"full-pass{sfx}", OUT / f"di{sfx}.wav").relative_to(ROOT))


if __name__ == "__main__":
  main(sys.argv[2] if sys.argv[1:2] == ["--variant"] else None)
