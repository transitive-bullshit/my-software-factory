"""Final exports of The AI Engineer's Creed (the captioned generative cut) for YouTube and X, and the X cut's copy on R2.

Made from the near-lossless master (renders/full/generative-captioned.mp4) and the lossless soundtrack
(renders/full/generative-soundtrack.wav) into renders/final/, with the McGurk demo's settings (promo/mcgurk/export.py):

  YouTube:  Google's recommended upload settings: H.264 High, 2 consecutive B-frames, closed GOP of half the frame rate,
            CABAC, VBR (crf 16), AAC-LC 384 kbps 48 kHz stereo, moov at the front, no edit lists (so the soundtrack is
            padded to stay in sync, see YT_PAD). Its thumbnail is the title frame as a 1280x720 JPEG.
  X:        H.264 High 4.1, 1080p at 29.97, capped VBR (crf 18, max 10 Mbps, 16 Mb buffer), keyframe every 2 s, AAC-LC
            192 kbps 48 kHz, moov at the front (+faststart) so it streams before it has fully downloaded.

The X cut is the share copy: `upload` puts it on R2, content-addressed (<sha256>.mp4) under ai-engineers-creed/, and
records its public URL in data/release.json.

  uv run --group analysis python scripts/release.py export
  uv run python scripts/release.py upload --env <file with S3_* keys>
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup import env, load_env, public_size, put, sha256  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NAME = "ai-engineers-creed"
FINAL = ROOT / "renders" / "final"
MASTER = ROOT / "renders" / "full" / "generative-captioned.mp4"
SOUNDTRACK = ROOT / "renders" / "full" / "generative-soundtrack.wav"
TITLE = ROOT / "renders" / "full" / "title.png"
MANIFEST = ROOT / "data" / "release.json"
SR = 48000
FPS = 30000 / 1001
# YouTube wants no edit lists, so nothing trims the encoder delays on playback: the first picture shows after x264's
# B-frame reorder delay (2 frames with -bf 2) and the audio starts with ffmpeg's AAC priming (1024 samples). Pad the
# soundtrack by the difference so its content starts with the first picture, and start its timestamps that much early.
YT_PAD = round(2 / FPS * SR) - 1024


def ff(*args: str) -> None:
  subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def export() -> None:
  FINAL.mkdir(parents=True, exist_ok=True)
  video = ["-map", "0:v", "-map", "1:a", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow"]
  x = FINAL / f"{NAME}-x.mp4"
  ff("-i", str(MASTER), "-i", str(SOUNDTRACK), *video,
     "-level", "4.1", "-crf", "18", "-maxrate", "10M", "-bufsize", "16M", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
     "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart", str(x))
  padded = FINAL / "soundtrack-yt.wav"
  audio, sr = sf.read(SOUNDTRACK, dtype="float32")
  assert sr == SR, f"the soundtrack is {sr} Hz"
  sf.write(padded, np.concatenate([np.zeros((YT_PAD, audio.shape[1]), np.float32), audio]), SR, subtype="PCM_24")
  yt = FINAL / f"{NAME}-youtube.mp4"
  ff("-i", str(MASTER), "-itsoffset", f"{-YT_PAD / SR:.6f}", "-i", str(padded), *video,
     "-crf", "16", "-bf", "2", "-g", "15", "-flags", "+cgop", "-coder", "cabac",
     "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "384k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart", "-use_editlist", "0",
     str(yt))
  padded.unlink()
  thumb = FINAL / f"{NAME}-thumbnail.jpg"
  ff("-i", str(TITLE), "-vf", "scale=1280:720:flags=lanczos", "-q:v", "2", str(thumb))
  for f in (yt, x, thumb):
    print(f.relative_to(ROOT), f"{f.stat().st_size / 1e6:.1f} MB")


def upload() -> None:
  path = FINAL / f"{NAME}-x.mp4"
  digest, size = sha256(path), path.stat().st_size
  url = f"{env('S3_PUBLIC_URL').rstrip('/')}/{NAME}/{digest}.mp4"
  if public_size(url) != size:
    put(f"{NAME}/{digest}.mp4", path, digest)
    if public_size(url, tries=4) != size:
      sys.exit(f"{url}: the public copy doesn't match the {size} bytes uploaded")
  MANIFEST.write_text(json.dumps({"x": {"file": path.relative_to(ROOT).as_posix(), "url": url, "bytes": size, "sha256": digest}},
                                 indent=1) + "\n")
  print(url)


if __name__ == "__main__":
  args = sys.argv[1:]
  if "--env" in args:
    load_env(args[args.index("--env") + 1])
  {"export": export, "upload": upload}[args[0]]()
