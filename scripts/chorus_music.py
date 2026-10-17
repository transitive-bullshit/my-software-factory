"""The chorus: every recruit line from ONE Eleven Music generation, so the crowd voice is consistent across the
whole chant. Scenes are separated by pauses inside that one take; we cut at the quietest point of each pause and
lay the raw scene clips on the timeline. No stretching, no room processing: the raw take is the source of truth.

  uv run --group analysis python scripts/chorus_music.py generate         # all variants, then a split report
  uv run --group analysis python scripts/chorus_music.py build gaps       # cut, place, data/chorus.json, render

Variants differ only in how the pauses are asked for:
  chunks  one timed chunk per scene, each ending in "{then a beat of silence}"
  gaps    one timed chunk per scene, with a 3 s silent chunk between scenes
  single  one chunk for everything, scenes separated by "{pause for a beat}"
"""

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import eleven  # noqa: E402
from audio import ROOT, SR, ff, find_line, render_pass, whisper_words  # noqa: E402

OUT = ROOT / "media" / "voices" / "chorus-music"
SEED = 3
MODEL = "music_v2_5"
DIRECTION = "{thirty recruits chanting together, spoken not sung}"
POS = ["spoken unison chant", "gang vocals", "thirty young men shouting in unison", "military cadence", "a cappella",
       "no instruments", "dry barracks room", "1980s film dialogue"]
NEG = ["singing", "melody", "rap", "drums", "instruments", "harmony", "music bed", "choir"]
PAUSE = {"text": "[Pause]\n{silence: thirty recruits hold still, nobody speaks}", "duration_ms": 3000,
         "positive_styles": ["silence", "near silence", "still room"],
         "negative_styles": ["voices", "chanting", "speech", "singing", "music", "instruments", "drums", "noise"]}
SLOT_OVERRIDES = {"C01": (42.14, 44.05)}  # 3 syllables over: starts early and uses the gap before C02
VARIANTS = ("chunks", "gaps", "single")


def scenes(script: dict) -> list[dict]:
  """Chorus lines grouped by the shot they start in, in order."""
  out: list[dict] = []
  for ln in sorted((l for l in script["lines"] if l["voice"].startswith("chorus")), key=lambda l: l["start"]):
    shot = ln["shot"].split(">")[0]
    if not out or out[-1]["id"] != shot:
      out.append({"id": shot, "lines": []})
    out[-1]["lines"].append(ln)
  for sc in out:
    a = SLOT_OVERRIDES.get(sc["lines"][0]["id"], (sc["lines"][0]["start"],))[0]
    sc["slot"] = (a, sc["lines"][-1]["end"])
  return out


def plan(variant: str, scs: list[dict]) -> dict:
  block = lambda sc: "\n".join(ln["parody"] for ln in sc["lines"])  # noqa: E731
  span = lambda sc: sc["slot"][1] - sc["slot"][0]  # noqa: E731
  if variant == "single":
    text = f"[Barracks chant]\n{DIRECTION}\n" + "\n{pause for a beat}\n".join(block(sc) for sc in scs)
    total = sum(span(sc) + 1.5 for sc in scs)
    return {"chunks": [{"text": text, "duration_ms": round(total * 1000), "positive_styles": POS, "negative_styles": NEG}]}
  chunks = []
  for k, sc in enumerate(scs):
    if variant == "gaps" and k:
      chunks.append(PAUSE)
    tail = "\n{then a beat of silence}" if variant == "chunks" else ""
    pad = 1.5 if variant == "chunks" else 0.3
    chunks.append({"text": f"[Barracks chant]\n{DIRECTION}\n{block(sc)}{tail}",
                   "duration_ms": max(3000, round((span(sc) + pad) * 1000)), "positive_styles": POS, "negative_styles": NEG})
  return {"chunks": chunks}


def stereo(path: Path) -> np.ndarray:
  wav = path.with_name(path.stem + ".stereo.wav")
  if not wav.exists():
    ff("-i", str(path), "-ac", "2", "-ar", str(SR), str(wav))
  return sf.read(wav, dtype="float32")[0]


def analyze(variant: str, scs: list[dict]) -> dict:
  """Find every line in the take; measure each between-scene gap and pick a cut point inside it."""
  take = OUT / variant / "full.mp3"
  y = np.abs(stereo(take)).mean(1)
  words = whisper_words(take)
  hop = int(0.02 * SR)
  env = np.array([np.sqrt(np.mean(y[i : i + hop] ** 2)) for i in range(0, len(y) - hop, hop)]) + 1e-9
  db = 20 * np.log10(env / env.max())
  lines, cursor = {}, 0
  for sc in scs:
    for ln in sc["lines"]:
      hit = find_line(words, ln["parody"], cursor)
      if hit:
        s0, s1, score = hit
        lines[ln["id"]] = {"raw": [round(words[s0]["start"], 3), round(words[s1]["end"], 3)], "score": round(score, 2),
                           "heard": "".join(w["word"] for w in words[s0 : s1 + 1]).strip()}
        cursor = s1 + 1
  report = {"variant": variant, "duration": round(len(y) / SR, 2), "lines": lines,
            "missing": [ln["id"] for sc in scs for ln in sc["lines"] if ln["id"] not in lines], "gaps": []}
  for k in range(len(scs) - 1):
    last, nxt = scs[k]["lines"][-1]["id"], scs[k + 1]["lines"][0]["id"]
    if last not in lines or nxt not in lines:
      continue
    a, b = lines[last]["raw"][1], lines[nxt]["raw"][0]
    ia, ib = int(a * SR / hop), max(int(a * SR / hop) + 1, int(b * SR / hop))
    seg = db[ia:ib]
    cut = (ia + int(np.argmin(seg))) * hop / SR if len(seg) else (a + b) / 2
    report["gaps"].append({"after": scs[k]["id"], "seconds": round(b - a, 2),
                           "floor_db": round(float(np.percentile(seg, 50)) if len(seg) else 0.0, 1), "cut": round(cut, 3)})
  return report


def generate() -> None:
  script = json.loads((ROOT / "data" / "script.json").read_text())
  scs = scenes(script)
  for v in VARIANTS:
    d = OUT / v
    d.mkdir(parents=True, exist_ok=True)
    p = plan(v, scs)
    (d / "plan.json").write_text(json.dumps(p, indent=2))
    eleven.compose(p, d / "full.mp3", model_id=MODEL, seed=SEED)
    r = analyze(v, scs)
    (d / "report.json").write_text(json.dumps(r, indent=2))
    gaps = ", ".join(f"{g['after']} {g['seconds']:.2f}s @{g['floor_db']:.0f}dB" for g in r["gaps"])
    weak = [f"{k}({x['score']})" for k, x in r["lines"].items() if x["score"] < 1]
    print(f"{v:7} {r['duration']:5.1f}s  missing {r['missing'] or '-'}  fuzzy {weak or '-'}\n        gaps: {gaps}")


def build(variant: str) -> None:
  script = json.loads((ROOT / "data" / "script.json").read_text())
  scs = scenes(script)
  r = json.loads((OUT / variant / "report.json").read_text())
  if r["missing"]:
    sys.exit(f"{variant} is missing {r['missing']}; pick another variant or regenerate")
  y = stereo(OUT / variant / "full.mp3")
  # Whisper puts a word's start inside the silence before it (0.5-0.7 s early after a pause): use the audible onset
  mono, hop, prev = np.abs(y).mean(1), int(0.01 * SR), 0.0
  for sc in scs:
    for ln in sc["lines"]:
      a, b = r["lines"][ln["id"]]["raw"]
      lo = max(prev, a - 0.1)
      seg = mono[int(lo * SR) : int(b * SR)]
      env = np.array([seg[i : i + hop].max() for i in range(0, max(0, len(seg) - hop), hop)])
      loud = np.nonzero(env > 0.1 * env.max())[0] if len(env) else []
      r["lines"][ln["id"]]["raw"] = [round(lo + loud[0] * hop / SR, 3) if len(loud) else a, b]
      prev = b
  lead_in = 0.25  # at most this much of the pause stays in front of a scene
  cuts = [max(0.0, r["lines"][scs[0]["lines"][0]["id"]]["raw"][0] - lead_in)]
  cuts += [g["cut"] for g in r["gaps"]]
  cuts += [min(len(y) / SR, r["lines"][scs[-1]["lines"][-1]["id"]]["raw"][1] + 0.8)]
  w0, w1 = script["window"]["start"], script["window"]["end"]
  n = int((w1 - w0 + 2.0) * SR)
  track = np.zeros((n, 2), np.float32)
  fade = int(0.008 * SR)
  scenes_dir = OUT / variant / "scenes"
  scenes_dir.mkdir(exist_ok=True)
  out = {"source": str((OUT / variant / "full.mp3").relative_to(ROOT)), "model": MODEL, "seed": SEED, "variant": variant,
         "$comment": "Raw Eleven Music take, cut at the between-scene pauses and laid on the source-clip timeline. "
                     "'raw' times are in the take, 'placed' times in source-clip seconds (meme time = placed - window.start).",
         "scenes": [], "lines": {}}
  prev_end = -1.0
  for k, sc in enumerate(scs):
    first, last = sc["lines"][0]["id"], sc["lines"][-1]["id"]
    c0, c1 = max(cuts[k], r["lines"][first]["raw"][0] - lead_in), cuts[k + 1]
    clip = y[int(c0 * SR) : int(c1 * SR)].copy()
    clip[:fade] *= np.linspace(0, 1, fade)[:, None]
    clip[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sf.write(scenes_dir / f"{sc['id']}.wav", clip, SR)
    want = sc["slot"][0]
    start = max(want, prev_end + 0.2)  # a scene never starts on top of the last one
    offset = start - r["lines"][first]["raw"][0]  # raw take time -> source time
    i = int((offset + c0 - w0) * SR)
    track[i : i + len(clip)] += clip[: n - i]
    prev_end = r["lines"][last]["raw"][1] + offset
    for ln in sc["lines"]:
      raw = r["lines"][ln["id"]]["raw"]
      out["lines"][ln["id"]] = {"raw": raw, "placed": [round(raw[0] + offset, 3), round(raw[1] + offset, 3)],
                                "slot": [ln["start"], ln["end"]]}
    out["scenes"].append({"id": sc["id"], "lines": [ln["id"] for ln in sc["lines"]], "cut": [round(c0, 3), round(c1, 3)],
                          "placed_at": round(offset + c0, 3), "speech": [round(start, 3), round(prev_end, 3)],
                          "slot": [round(x, 3) for x in sc["slot"]], "drift": round(prev_end - sc["slot"][1], 2)})
    print(f"{sc['id']}: take {c1 - c0:5.2f}s  speech {start:6.2f}-{prev_end:6.2f}  slot {sc['slot'][0]:6.2f}-{sc['slot'][1]:6.2f}"
          f"  ends {prev_end - sc['slot'][1]:+.2f}s vs slot")
  (ROOT / "data" / "chorus.json").write_text(json.dumps(out, indent=2) + "\n")
  sf.write(OUT / variant / "track.wav", track, SR)

  print(render_pass().relative_to(ROOT))


if __name__ == "__main__":
  if sys.argv[1:2] == ["generate"]:
    generate()
  elif sys.argv[1:2] == ["build"] and len(sys.argv) == 3:
    build(sys.argv[2])
  else:
    sys.exit(__doc__)
