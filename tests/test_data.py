"""Offline checks on the committed timeline data: the project's own rules, enforced on what's in git (no media needed)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = json.loads((ROOT / "data" / "script.json").read_text())
LINES = {ln["id"]: ln for ln in SCRIPT["lines"]}
CAPTIONS = json.loads((ROOT / "captions" / "captions.json").read_text())["lines"]


def test_shots_tile_the_window_and_lines_stay_locked():
  w, shots = SCRIPT["window"], sorted(SCRIPT["shots"], key=lambda s: s["start"])
  assert shots[0]["start"] == w["start"] and shots[-1]["end"] == w["end"]
  assert all(abs(a["end"] - b["start"]) < 1e-6 for a, b in zip(shots, shots[1:])), "shots must be contiguous"
  ids = {s["id"] for s in shots}
  for ln in SCRIPT["lines"]:
    assert set(ln["shot"].split(">")) <= ids, ln["id"]  # "S11>S12": a line that runs across a cut
    assert w["start"] <= ln["start"] < ln["end"] <= w["end"], ln["id"]
    assert ln["parody"].strip(), ln["id"]
    # parody lines stay within 2 syllables of the original; a deliberate overrun is recorded in the line's ref
    if abs(ln["syl"] - ln["origSyl"]) > 2:
      assert "syllab" in (ln.get("ref") or "").lower(), f"{ln['id']}: overrun not recorded in ref"


def test_reads_are_placed_whole_never_retimed():
  chorus = json.loads((ROOT / "data" / "chorus.json").read_text())["lines"]
  for lid, c in chorus.items():
    assert lid in LINES
    (ra, rb), (pa, pb) = c["raw"], c["placed"]
    assert abs((pb - pa) - (rb - ra)) < 1e-3, f"{lid}: chorus line stretched or squeezed"
  for name in ("di.json", "di-gen.json"):
    for lid, d in json.loads((ROOT / "data" / name).read_text())["lines"].items():
      assert lid in LINES
      assert abs((d["placed"][1] - d["placed"][0]) - d["natural"]) < 0.002, f"{name} {lid}: read re-timed"


def test_captions_match_the_script_and_never_overlap():
  norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())  # "A-I" and "AI" read the same
  assert {ln["id"] for ln in CAPTIONS} == set(LINES), "every line is captioned once"
  prev_out = 0.0
  for ln in CAPTIONS:
    assert norm("".join(w["text"] for w in ln["words"])) == norm(LINES[ln["id"]]["parody"]), ln["id"]
    assert prev_out <= ln["in"] < ln["out"], f"{ln['id']}: overlaps the line before"
    starts = [w["start"] for w in ln["words"]]
    assert starts == sorted(starts), f"{ln['id']}: words out of order"
    assert all(ln["in"] <= w["start"] <= w["end"] <= ln["out"] for w in ln["words"]), ln["id"]
    prev_out = ln["out"]


def test_caption_composition_is_built_from_captions_json():
  html = (ROOT / "captions" / "compositions" / "captions.html").read_text()
  for ln in CAPTIONS:
    cue = re.search(rf'id="cap-{ln["id"]}"[^>]*data-start="([0-9.]+)" data-duration="([0-9.]+)"', html)
    assert cue, f"{ln['id']}: missing from captions.html; run `npm run build` in captions/"
    assert abs(float(cue[1]) - ln["in"]) < 1e-3 and abs(float(cue[2]) - (ln["out"] - ln["in"])) < 1e-3, ln["id"]
