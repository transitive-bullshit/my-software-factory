"""Timestamped contact sheets of the source clip -> frames/sheets/ (ignored).

Run: uv run --group analysis python scripts/sheets.py [start] [end] [fps]
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media" / "source.mp4"
OUT = ROOT / "frames" / "sheets"
COLS, ROWS, W = 4, 5, 480


def main() -> None:
  start = float(sys.argv[1]) if len(sys.argv) > 1 else 39.0
  end = float(sys.argv[2]) if len(sys.argv) > 2 else 106.5
  fps = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
  tmp = OUT / "tmp"
  tmp.mkdir(parents=True, exist_ok=True)
  for f in tmp.glob("*.jpg"):
    f.unlink()
  subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-to", str(end), "-i", str(SRC),
     "-vf", f"fps={fps},scale={W}:-2", "-q:v", "3", str(tmp / "%04d.jpg")],
    check=True,
  )
  frames = sorted(tmp.glob("*.jpg"))
  font = ImageFont.load_default(size=26)
  per = COLS * ROWS
  for i in range(0, len(frames), per):
    batch = frames[i : i + per]
    w, h = Image.open(batch[0]).size
    sheet = Image.new("RGB", (COLS * (w + 4) + 4, ROWS * (h + 4) + 4), "black")
    for j, f in enumerate(batch):
      t = start + (i + j) / fps
      im = Image.open(f)
      ImageDraw.Draw(im).text((8, 6), f"{t:.1f}s", fill="yellow", font=font, stroke_width=3, stroke_fill="black")
      sheet.paste(im, (4 + (j % COLS) * (w + 4), 4 + (j // COLS) * (h + 4)))
    t0, t1 = start + i / fps, start + (i + len(batch) - 1) / fps
    sheet.save(OUT / f"sheet-{t0:05.1f}-{t1:05.1f}.jpg", quality=85)
  print("\n".join(sorted(str(p.relative_to(ROOT)) for p in OUT.glob("sheet-*.jpg"))))


if __name__ == "__main__":
  main()
