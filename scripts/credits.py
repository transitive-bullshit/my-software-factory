"""The end credits card of the fully generative cut, rendered locally with HyperFrames (no generative model).

The card itself is a HyperFrames composition, captions/compositions/credits-card.html: black, creator and cast with
their profile pictures in rings, the main tools, subtle animation. Edit it there (or in Studio) and re-render with
`npm run credits` in captions/ -> renders/full/credits.mp4, which scripts/full.py crossfades onto the end of the cut.

This script prepares the profile pictures: the largest copies found of each person's current X picture
(media/credits/sources/, see AVATARS), cropped square to lossless PNGs in captions/assets/avatars/, then renders the card.

  uv run --group analysis python scripts/credits.py
"""

import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "media" / "credits" / "sources"
PROJECT = ROOT / "captions"
# handle -> (source in media/credits/sources/, square crop as (centre x, centre y, side) fractions of the width, or None)
AVATARS = {
  "transitive_bs": ("transitive_bs-author.jpg", None),  # 1024 px, from the author
  "JensenHuang": ("nvidia-jensen.jpg", (0.43, 0.29, 0.56)),  # 1920 px NVIDIA press portrait (his X picture), head and shoulders
  "mattpocockuk": ("yt-matt.jpg", None),  # 900 px, his YouTube channel's copy of the picture the author picked (X: 351)
  "steipete": ("x-steipete.png", None),  # 512 px X original; his site and GitHub use another photo
  "swyx": ("swyx-900.webp", None),  # 900 px copy of the X picture, from the author (X: 400, GitHub: 460)
  "simonw": ("gh-simonw.img", None),  # 460 px GitHub copy of the X picture (X: 256; the author's pick)
  "poteto": ("x-poteto.jpg", None),  # 400 px X original; GitHub uses another picture
}


def avatars() -> None:
  out = PROJECT / "assets" / "avatars"
  shutil.rmtree(out, ignore_errors=True)
  out.mkdir(parents=True)
  for handle, (name, crop) in AVATARS.items():
    im = Image.open(SOURCES / name).convert("RGB")
    if crop:
      cx, cy, side = (v * im.width for v in crop)
      im = im.crop((round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2)))
    n = min(im.size)
    im.crop(((im.width - n) // 2, (im.height - n) // 2, (im.width + n) // 2, (im.height + n) // 2)).save(out / f"{handle}.png")


def main() -> None:
  avatars()
  subprocess.run(["npm", "run", "credits"], cwd=PROJECT, check=True)


if __name__ == "__main__":
  main()
