"""The vertical plate: a full-height 9:16 window (607.5x1080) of the cut's footage, scaled to 1080x1920 -> assets/plate.mp4.

The source is the cut's footage before the title frame and the credits (media/full/cuts/generative-video.mp4, the shots
joined frame for frame; the clips in renders/full/shots/ are cut to their audio and run a few frames short). Each shot
keeps its window on the speaker; where the subject walks the window pans with him, through keyframes eased with a
monotone cubic so it starts and stops softly. The frame is scaled up first and cropped at whole output pixels, so a pan
moves in 0.56 px steps of the source. "fit" shows a shot whole instead: the 16:9 frame across the middle, over a blurred,
darkened fill of itself. Video only: export.py lays the cut's lossless soundtrack on at the end.

  uv run --project ../.. --group analysis python crop.py          # assets/plate.mp4
  uv run --project ../.. --group analysis python crop.py sheet    # ../../renders/promo/creed-vertical/crops.jpg, the crops for review
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = ROOT / "media" / "full" / "cuts" / "generative-video.mp4"
PARTS = SRC.with_suffix(".txt")  # the concat list full.py joined it from: one conformed part per shot, in order
PLATE = HERE / "assets" / "plate.mp4"
REVIEW = ROOT / "renders" / "promo" / "creed-vertical"
FPS = 30000 / 1001
W, H = 1080, 1920
SCALED = 3414  # the 1920x1080 frame scaled to 1920 px tall (3413.3, rounded to even)
HALF = W / (SCALED / 1920) / 2  # half the window, in source px (the window is 607.5 wide)

# Each shot's window centre in source px (0-1920), as keyframes (seconds into the shot, x); one keyframe holds still.
# The speaker sits mid-frame; numbers are read off frame strips of the cut.
CROPS: dict[str, list[tuple[float, float]] | str] = {
  "S07": [(0, 990)],  # the DI's face (the McGurk vertical's window)
  "S08": [(0, 1380)],  # Matt on the bunk: his head and the hands on the keyboard
  "S09": [(0, 304)],  # the featured recruit: steipete at the frame's left edge (the lobster stays out of frame)
  "S10": [(0, 1460)],  # Matt's close-up
  "S11": [(0, 600)],  # swyx
  # the DI walks in from the left, settles, then steps in and to the right before "Ready!"
  "S12": [(0, 728), (0.6, 735), (1.95, 1160), (3.2, 1160), (4.4, 1255)],
  "S13": [(0, 304)],  # same angle as S09
  # "Auto-merge!" on his face, then the window eases right as his hand finds the light switch
  "S14": [(0, 1250), (1.75, 1250), (2.5, 1440)],
  "S15-1": [(0, 1400)],  # lights out: his silhouette at the switch, where S14 left him
  # he walks off down the hall; the window follows him, then settles with the fire watch in frame for his line
  "S15-2": [(0, 1400), (0.8, 1390), (2.6, 740), (4.0, 480)],
}
# the other treatment for the wide shots, shown beside the pick on the review sheet: the whole frame, lobster included
OPTIONS = {"S09": "fit", "S13": "fit"}
# the whole 16:9 frame across the middle, over a blurred, darkened fill of itself
FIT = (f"split[bg][fg];[bg]scale={SCALED}:{H}:flags=bicubic,crop={W}:{H},gblur=sigma=36,eq=brightness=-0.12:saturation=0.85[b];"
       f"[fg]scale={W}:-2:flags=lanczos[f];[b][f]overlay=0:(H-h)/2")


def ff(*args: str) -> None:
  subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def shots() -> list[tuple[str, int, int]]:
  """(shot, first frame, end frame) of each part of the source, in order."""
  out, n = [], 0
  for line in PARTS.read_text().splitlines():
    path = line.removeprefix("file '").removesuffix("'")
    sid = re.match(r"generative-(S\d+(?:-\d)?)-", Path(path).name).group(1)
    k = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                            "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout)
    out.append((sid, n, n + k))
    n += k
  return out


def track(keys: list[tuple[float, float]], t: np.ndarray) -> np.ndarray:
  """Monotone cubic (Fritsch-Carlson) through the keyframes, held flat before the first and after the last."""
  if len(keys) == 1:
    return np.full_like(t, keys[0][1])
  kt, kx = (np.array(v, float) for v in zip(*keys))
  d = np.diff(kx) / np.diff(kt)
  m = np.zeros_like(kx)  # slopes at the keys: zero at the ends and where the direction turns or holds
  for i in range(1, len(kx) - 1):
    if d[i - 1] * d[i] > 0:
      m[i] = 2 / (1 / d[i - 1] + 1 / d[i])
  tc = np.clip(t, kt[0], kt[-1])
  i = np.clip(np.searchsorted(kt, tc, side="right") - 1, 0, len(kt) - 2)
  h = kt[i + 1] - kt[i]
  u = (tc - kt[i]) / h
  return ((2 * u**3 - 3 * u**2 + 1) * kx[i] + (u**3 - 2 * u**2 + u) * h * m[i]
          + (-2 * u**3 + 3 * u**2) * kx[i + 1] + (u**3 - u**2) * h * m[i + 1])


def window_x(sid: str, frames: int) -> np.ndarray:
  """The crop's left edge in output px (the scaled frame), per frame of the shot."""
  cx = track(CROPS[sid], np.arange(frames) / FPS)
  scale = SCALED / 1920
  return np.clip(np.round((cx - HALF) * scale), 0, SCALED - W).astype(int)


def build(dest: Path = PLATE) -> Path:
  dest.parent.mkdir(parents=True, exist_ok=True)
  tmp = Path(tempfile.mkdtemp(prefix="creed-crop-"))
  chains, labels = [], []
  for k, (sid, a, b) in enumerate(shots()):
    head = f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS"
    if CROPS[sid] == "fit":
      fit = FIT.replace("[bg]", f"[bg{k}]").replace("[fg]", f"[fg{k}]").replace("[b]", f"[b{k}]").replace("[f]", f"[f{k}]")
      chains.append(f"{head},{fit},format=yuv420p[v{k}]")
    else:
      xs = window_x(sid, b - a)
      cmds = tmp / f"{k}.cmd"
      cmds.write_text("".join(f"{i / FPS:.6f} crop@c{k} x {x};\n" for i, x in enumerate(xs)))
      chains.append(f"{head},scale={SCALED}:{H}:flags=lanczos,format=yuv444p,sendcmd=f={cmds},"
                    f"crop@c{k}={W}:{H}:{xs[0]}:0:exact=1,format=yuv420p[v{k}]")
    labels.append(f"[v{k}]")
  graph = ";".join(chains) + f";{''.join(labels)}concat=n={len(labels)}:v=1:a=0,setsar=1[v]"
  ff("-i", str(SRC), "-filter_complex", graph, "-map", "[v]", "-r", "30000/1001", "-c:v", "libx264", "-preset", "slow",
     "-crf", "10", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
     "-color_range", "tv", "-movflags", "+faststart", str(dest))
  print(dest)
  return dest


def sheet(plate: Path = PLATE) -> Path:
  """Every shot's crop, sampled across the shot (the pans show as a strip), with the phone safe area outlined; a shot
  with another option (OPTIONS) gets a second row showing it."""
  from PIL import Image, ImageDraw, ImageFont

  REVIEW.mkdir(parents=True, exist_ok=True)
  font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
  tw, th, per = 216, 384, 6
  rows = []
  todo = [(sid, a, b, None) for sid, a, b in shots()]
  todo = [r for t in todo for r in ([t] + ([(t[0], t[1], t[2], OPTIONS[t[0]])] if t[0] in OPTIONS else []))]
  for sid, a, b, option in todo:
    picks = np.linspace(a, b - 1, per).round().astype(int)
    sel = "+".join(f"eq(n\\,{n})" for n in picks)
    # the plate as built, or the option applied to the source on the fly
    src, vf = (plate, f"select='{sel}'") if option is None else (SRC, f"select='{sel}',{FIT}")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-filter_complex", f"{vf},scale={tw}:{th}:flags=area",
                          "-fps_mode", "vfr", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, th, tw, 3)
    row = Image.new("RGB", (160 + per * (tw + 8), th + 8), (18, 18, 18) if option is None else (40, 28, 12))
    d = ImageDraw.Draw(row)
    d.text((12, 12), sid, font=font, fill=(255, 210, 90))
    if option:
      mode = f"option:\n{option}"
    else:
      mode = "fit" if CROPS[sid] == "fit" else ("pan" if len(CROPS[sid]) > 1 else "hold")
    d.multiline_text((12, 48), mode, font=font, fill=(200, 200, 200))
    for j, (fr, n) in enumerate(zip(frames, picks)):
      im = Image.fromarray(fr)
      g = ImageDraw.Draw(im)
      s = tw / W
      g.rectangle([100 * s, 260 * s, 900 * s, 1360 * s], outline=(90, 200, 255), width=1)  # the phone safe area
      g.text((6, th - 24), f"{(n - a) / FPS:.1f}s", font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18),
             fill="white", stroke_width=2, stroke_fill="black")
      row.paste(im, (160 + j * (tw + 8), 4))
    rows.append(row)
  out = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)), (18, 18, 18))
  y = 0
  for r in rows:
    out.paste(r, (0, y))
    y += r.height
  dest = REVIEW / "crops.jpg"
  out.save(dest, quality=88)
  print(dest)
  return dest


if __name__ == "__main__":
  {"sheet": sheet}.get(sys.argv[1] if len(sys.argv) > 1 else "", build)()
