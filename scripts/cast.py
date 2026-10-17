"""The cast of the fully generative version: likeness headshots per character, their character sheets (Nano Banana
Pro edit, the same approach as the S07+S08 test), and the cast review page -> review/dist/cast.html (ignored: it
shows real people's photos).

Headshot candidates are gathered into reference/cast/<who>/raw/ with a sources.json (where each came from). The
picks below are cropped to the head and shoulders and written to reference/cast/<who>/headshot-N.jpg; those are the
sheet's references. A sheet is cached by its output name: bump the character's rev to redo it.

  uv run --group analysis --group voice --group gen python scripts/cast.py headshots|sheets|page|all
"""

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import fal_run  # noqa: E402
from variants_page import box, esc, media, render_page  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference" / "cast"
OUT = ROOT / "media" / "cast"
PAGE = ROOT / "review" / "dist" / "cast.html"

# head-and-shoulders headshots per character: (file in reference/cast/<who>/raw/, crop box (l, t, r, b) or None)
PICKS: dict[str, list[tuple[str, tuple[int, int, int, int] | None]]] = {
  "steipete": [("openai-builders-2026-frontal.png", (480, 0, 1380, 900)), ("ted-2026-three-quarter.png", (390, 0, 1290, 900)),
               ("openai-builders-2026-profile.png", (180, 0, 1260, 1080)), ("openai-builders-2026-three-quarter-closeup.png", (330, 0, 1410, 1080))],
  "matt": [("yt-2026-frontal.png", (705, 10, 1255, 560)), ("pe-2026-threequarter-smile.png", (870, 0, 1560, 690)),
           ("pe-2026-profile-smile.png", (900, 0, 1590, 690)), ("aihero-studio-3q-right.png", (90, 0, 600, 510)),
           # side and upward angles for the S10 close-up (rev 4): his head turned, tilted back, looking up, mouth open
           ("side/pe-2026-3q-left-lookup-mouth-open.png", (860, 60, 1460, 660)), ("side/pe-2026-3q-left-chin-up-talking.png", (900, 40, 1500, 640)),
           ("side/pe-2026-near-profile-left-chin-up.png", (860, 40, 1480, 660)), ("side/pe-2026-steep-3q-left-talking.png", (860, 0, 1480, 620)),
           ("side/offerzen-2023-low-angle-3q-left-looking-up.png", (960, 40, 1500, 580))],
  "swyx": [("swyx-thursday-nights-2024.jpg", (704, 141, 1971, 1408)), ("swyx-ls-frontal-2026.png", (585, 15, 1215, 645)),
           ("swyx-ls-three-quarter-2026.png", (675, 0, 1275, 600)), ("swyx-aie-stage-2026.jpg", (627, 53, 1107, 533)),
           ("swyx-ls-smile-2026.png", (585, 15, 1215, 645))],
  # 2026 only: his X avatar and older headshots (2013) show short hair and red frames, not his current look
  "simonw": [("simonw-2026-build-3q-smile.png", (570, 60, 1230, 720)), ("simonw-2026-lenny-front-neutral.png", (540, 120, 1500, 1080)),
             ("simonw-2026-lenny-front-smile.png", (555, 120, 1515, 1080)), ("simonw-2026-build-3q-neutral.png", (510, 60, 1170, 720))],
}

WARDROBE = "a plain white crew-neck t-shirt"
CAST = {
  "jensen": {
    "name": "Jensen Huang", "role": "Drill instructor · S07, S12, S14, S15",
    "refs": ["reference/cast/jensen/jensen-1.jpg", "reference/cast/jensen/jensen-2.jpg", "reference/cast/jensen/jensen-3.jpg"],
    "approved": "media/variants/generative/sheet-jensen.png",
  },
  # rev 4 (author, round 5): S10's close-up (low angle, head tilted back, looking up) didn't look like him. The approved
  # r3 sheet stays the base look; nine real photos (five of them side and upward angles) anchor a second row of the
  # angles the shot needs
  "matt": {
    "name": "Matt Pocock", "role": "Recruit, the hook · S08, S10 close-up", "rev": 4,
    "approved": "media/cast/sheet-matt-r4-1.png", "base": "media/cast/sheet-matt-r3-1.png",  # r4 B approved (round 5)
    "prompt": ("Character reference sheet of the man in these photos (Matt Pocock). The first image is his approved character "
               "sheet: keep that look exactly (plain light-grey studio background, even soft light, photographic, no text). Keep "
               "his exact face from the photos: long narrow face, prominent cheekbones, his ears, bald crown with short sides, "
               "round tortoiseshell glasses, light stubble and a light moustache. Six head-and-shoulders views in two rows. Top "
               "row: front, three-quarter and profile, as in the first image. Bottom row, the angles of a close-up from a low "
               "angle, matching the photos where his head is turned and tilted back: a three-quarter view seen from slightly "
               "below with his head tilted back, looking up, mouth open mid-word; a near-profile with his chin raised, looking "
               "up, mouth open; and a three-quarter view with his big, natural open smile. He is cast as a 1980s Marine recruit "
               f"in {WARDROBE}."),
  },
  "steipete": {
    "name": "Peter Steinberger", "role": "Recruit · S09 and S13 (wides)", "rev": 1,
    "prompt": ("Character reference sheet of the man in these photos (Peter Steinberger), keeping his exact face, hairstyle, "
               "glasses and facial hair as in the photos. Three views side by side on a plain light-grey studio background: "
               f"front, three-quarter, profile, head and shoulders. He is cast as a 1980s Marine recruit in {WARDROBE}. "
               "Focused, good-humoured expression. Even soft light, photographic."),
  },
  "swyx": {
    "name": "swyx", "role": "Recruit · S11 close-up", "rev": 2,
    # the film's recruit in this slot must not carry over in any way: likeness, build, haircut and expression are swyx's own
    # rev 2: rev 1 took the swept-back hair of the 2024 photo; his hair now is short and textured (the 2026 photos)
    "prompt": ("Character reference sheet of the man in these photos (swyx, Shawn Wang). Keep his exact likeness as in the "
               "photos: face, face shape, build, skin, and his current short black hair, cut short at the sides and textured, "
               "slightly spiky on top, as in the 2026 photos. Three views side by side on a "
               "plain light-grey studio background: front, three-quarter, profile, head and shoulders. He is cast as a 1980s "
               f"Marine recruit in {WARDROBE}, looking sharp, with a confident, warm, focused expression. Even soft, flattering "
               "light, photographic."),
  },
  "simonw": {
    "name": "Simon Willison", "role": "Fire watch, the last line · S12, S14, S15", "rev": 1,
    "prompt": ("Character reference sheet of the man in these photos (Simon Willison), keeping his exact face, hairstyle, "
               "glasses and facial hair as in the photos. On a plain light-grey studio background: three full-length views "
               "side by side (front, three-quarter, profile) and a head-and-shoulders close-up of his face from the front. He "
               "is cast as a 1980s Marine recruit on fire watch: a polished chrome helmet liner, with his own shoulder-length "
               "hair hanging down from under it, a plain white crew-neck "
               "t-shirt, olive drab utility trousers and black boots, standing at rigid attention with his hands at his sides. "
               "Composed, deadpan expression. Even soft light, photographic."),
  },
}


def tag(rev: int) -> str:
  return "" if rev == 1 else f"-r{rev}"


def refs(who: str) -> list[str]:
  if "refs" in CAST[who]:
    return CAST[who]["refs"]
  base = [CAST[who]["base"]] if "base" in CAST[who] else []
  return base + [f"reference/cast/{who}/headshot-{i + 1}.jpg" for i in range(len(PICKS.get(who, [])))]


def headshots() -> None:
  for who, picks in PICKS.items():
    for i, (name, crop) in enumerate(picks):
      im = Image.open(REF / who / "raw" / name)
      if im.mode in ("RGBA", "LA", "P"):  # studio cut-outs: flatten onto a dark backdrop
        im = im.convert("RGBA")
        im = Image.alpha_composite(Image.new("RGBA", im.size, (38, 38, 40, 255)), im)
      im = im.convert("RGB")
      if crop:
        im = im.crop(crop)
      im.thumbnail((2048, 2048))
      dest = REF / who / f"headshot-{i + 1}.jpg"
      im.save(dest, quality=93)
      print(f"{who}: {dest.relative_to(ROOT)} {im.size} <- {name}")


def sheets() -> None:
  for who, c in CAST.items():
    if "prompt" not in c:
      continue
    r = refs(who)
    if len(r) < 3:
      print(f"{who}: only {len(r)} headshots, skipped")
      continue
    name = f"sheet-{who}{tag(c['rev'])}"
    print(who, fal_run.run("fal-ai/nano-banana-pro/edit",
                           {"prompt": c["prompt"], "image_urls": ["@" + p for p in r], "aspect_ratio": "16:9", "resolution": "2K",
                            "num_images": 2, "output_format": "png"},
                           OUT / name, est_cost=0.30, job=f"cast/{name}"))


def sources(who: str) -> dict[str, dict]:
  for p in (REF / who / "raw" / "sources.json", REF / who / "sources.json"):
    if p.exists():
      return {Path(s["file"]).name: s for s in json.loads(p.read_text())}
  return {}


def page() -> None:
  sections = []
  for who, c in CAST.items():
    src = sources(who)
    shots = []
    for i, f in enumerate(refs(who)):
      raw = PICKS[who][i][0] if who in PICKS else Path(f).name
      s = src.get(raw, {})
      cap = f'Headshot {i + 1}' + (f' · <a href="{esc(s["source"], quote=True)}" target="_blank">source</a>' if s.get("source") else "")
      shots.append(f'<figure>{media(f, "img")}<figcaption>{cap}</figcaption></figure>')
    sheets_html = []
    if c.get("approved"):
      sheets_html.append(f'<figure class="opt use">{media(c["approved"], "img")}<figcaption><b>Approved sheet</b> (S07+S08 test)</figcaption></figure>')
    if "prompt" in c:
      name = f"sheet-{who}{tag(c['rev'])}"
      for k, f in enumerate(sorted(OUT.glob(f"{name}.png")) + sorted(OUT.glob(f"{name}-[0-9].png"))):
        label = f"{c['name']} · sheet option {'AB'[k]}"
        sheets_html.append(f'<figure class="opt">{media(str(f.relative_to(ROOT)), "img")}<figcaption><b>Option {"AB"[k]}</b>'
                           f'{" (new headshots)" if c.get("approved") else ""}</figcaption>'
                           f'{box(f"{who}-sheet-{k}", label, "Approve, or what to change?")}</figure>')
    prompt = f'<details><summary class="dim">Sheet prompt</summary><p class="dim">{esc(c["prompt"])}</p></details>' if "prompt" in c else ""
    sections.append(
      f'<section class="variant" id="{who}"><h2>{esc(c["name"])} <span>{esc(c["role"])}</span></h2>'
      f'<h3>Likeness headshots ({len(shots)})</h3><div class="grid4">{"".join(shots)}</div>'
      f'<h3>Character sheet</h3><div class="grid2s">{"".join(sheets_html)}</div>{prompt}'
      f'{box(who, c["name"], "Likeness, look, anything to change?")}</section>')
  body = ('<p class="sub">The cast of the fully generative version, for approval before the full render. Each sheet is drawn '
          'by Nano Banana Pro from the headshots shown above it. The recruits keep their own hair, so they stay recognizable.</p>'
          + "".join(sections)
          + f'<div class="general"><label>General</label>{box("general", "General", "Anything across the cast?")}</div>'
          '<style>.grid4 {display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px} '
          '.grid4 img {aspect-ratio:1; object-fit:cover} .grid2s {display:grid; grid-template-columns:repeat(auto-fill,minmax(420px,1fr)); gap:12px} '
          '.opt.use img {outline:3px solid var(--accent)} details {margin-top:8px} @media (max-width:520px) {.grid2s {grid-template-columns:1fr}}</style>')
  PAGE.parent.mkdir(parents=True, exist_ok=True)
  PAGE.write_text(render_page("Software Factory Cast", "cast sheets", body, "cast:v1", "Cast review feedback"))
  print(PAGE.relative_to(ROOT))


STEPS = {"headshots": headshots, "sheets": sheets, "page": page}

if __name__ == "__main__":
  todo = list(STEPS) if sys.argv[1:] == ["all"] else sys.argv[1:]
  if not todo or any(t not in STEPS for t in todo):
    sys.exit(__doc__)
  for t in todo:
    print(f"== {t}")
    STEPS[t]()
