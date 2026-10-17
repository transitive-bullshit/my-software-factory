"""Fire watch (F01) voice options from ElevenLabs: a stock voice, soldier voices from the shared library, and Voice
Design previews of a young private. Every option reads the line; outputs go to media/voices/firewatch/ with an
options.json the review pages read. Pick one by setting data/voices.json fireWatch.read.

  python3 scripts/firewatch.py
"""

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import eleven  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "media" / "voices" / "firewatch"
TAG = "[shouting, eager to please]"
LIBRARY = ["George - War-torn Seargant", "Jerry B. - Gruff and Gritty Commander"]  # names as listed in the library
DESIGN = ("A 19-year-old American army private on fire watch, standing at rigid attention in a barracks at night. "
          "Loud, crisp and eager to please, a little breathless, every word shouted to a superior. Clean close-mic recording, no reverb.")


def library_voice(name: str) -> dict:
  """A shared-library voice by its exact listed name, added to My Voices once (library voices use no voice slot)."""
  qs = urllib.parse.urlencode({"page_size": 30, "search": name, "language": "en"})
  hits = [v for v in eleven.call("GET", f"/v1/shared-voices?{qs}").get("voices", []) if v["name"] == name]
  if not hits:
    sys.exit(f"library voice not found: {name}")
  v = hits[0]
  local = "MSF " + name.split(" - ")[0].rstrip(".") + " (" + name.split(" - ")[1].split()[0] + ")"
  mine = {x["name"]: x["voice_id"] for x in eleven.call("GET", "/v1/voices")["voices"]}
  if local not in mine:
    mine[local] = eleven.call("POST", f"/v1/voices/add/{v['public_owner_id']}/{v['voice_id']}", {"new_name": local})["voice_id"]
  return {"name": v["name"], "voice_id": mine[local], "kind": "library", "description": v.get("description", "")}


def main() -> None:
  OUT.mkdir(parents=True, exist_ok=True)
  script = json.loads((ROOT / "data" / "script.json").read_text())
  line = next(ln["parody"] for ln in script["lines"] if ln["id"] == "F01")
  voices = json.loads((ROOT / "data" / "voices.json").read_text())
  stock = next(v for v in voices["chorus"] if v["name"] == "Harry")
  options = [{"name": "Harry (stock)", "voice_id": stock["voice_id"], "kind": "stock", "description": stock["label"]}]
  options += [library_voice(n) for n in LIBRARY]
  for o in options:
    slug = o["name"].split(" ")[0].lower().rstrip(".")
    f = eleven.tts(o["voice_id"], f"{TAG} {line}", OUT / f"{slug}.mp3", model_id="eleven_v3")
    o["file"] = str(f.relative_to(ROOT))
    print(f"{o['name']:28} {o['file']}")

  # Voice Design: the preview text opens with the line, so each preview's first sentence is the read
  spec = {"model_id": "eleven_ttv_v3", "voice_description": DESIGN, "seed": 19,
          "text": f"{line} Yes, sir! Fire watch reporting, sir! All agents still running, sir! {line}"}
  (OUT / "design-spec.json").write_text(json.dumps(spec, indent=2))
  eleven.design("firewatch", str(OUT / "design-spec.json"))
  meta = json.loads((ROOT / "media" / "voices" / "design" / "firewatch" / "previews.json").read_text())
  from audio import decode, find_line, whisper_words  # noqa: E402  (MLX in a subprocess; numpy here)
  import numpy as np
  import soundfile as sf

  for p in meta["previews"]:
    src = ROOT / "media" / "voices" / "design" / "firewatch" / p["file"]
    words = whisper_words(src)
    hit = find_line(words, line)
    if not hit:
      print(f"  {p['file']}: line not found, skipped")
      continue
    y = decode(src)
    a, b = words[hit[0]]["start"], words[hit[1]]["end"]
    nxt = words[hit[1] + 1]["start"] if hit[1] + 1 < len(words) else b + 0.3
    clip = y[int(max(0, a - 0.05) * 44100) : int(min(nxt - 0.02, b + 0.25) * 44100)]
    k = p["file"].split(".")[0]
    dest = OUT / f"design-{k}.wav"
    sf.write(dest, clip.astype(np.float32), 44100)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(dest), "-b:a", "192k", str(dest.with_suffix(".mp3"))], check=True)
    options.append({"name": f"Young private (design {k.split('-')[-1]})", "kind": "design", "description": DESIGN,
                    "generated_voice_id": p["generated_voice_id"], "file": str(dest.with_suffix(".mp3").relative_to(ROOT))})
    print(f"{options[-1]['name']:28} {options[-1]['file']}")
  (OUT / "options.json").write_text(json.dumps(options, indent=2) + "\n")


if __name__ == "__main__":
  main()
