"""The vertical (9:16) export for YouTube Shorts, Instagram Reels and TikTok: one file for all three, from a high-quality
HyperFrames master.

The soundtrack is rebuilt losslessly from the S07 mix, as for the locked wide cut (../mcgurk/export.py): HyperFrames
encodes its audio at ~94 kbps AAC. Same timeline, so it matches the wide soundtrack sample for sample.

  1080x1920 30 fps, H.264 High 4.1, 2 consecutive B-frames, closed GOP of 15 frames, CABAC, VBR (crf 17) capped at
  20 Mbps (Instagram's ceiling is 25), AAC-LC 256 kbps 48 kHz stereo, moov at the front, no edit lists (YouTube and
  Instagram both ask for none, so the soundtrack is padded to stay in sync, see PAD).

  npx hyperframes render -o ../../renders/promo/final/mcgurk-vertical-master.mp4 --fps 30 --crf 12
  uv run --project ../.. --group analysis python export.py
"""

import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FINAL = ROOT / "renders" / "promo" / "final"
MASTER = FINAL / "mcgurk-vertical-master.mp4"
OUT = FINAL / "mcgurk-vertical.mp4"
S07 = ROOT / "media" / "full" / "shots-gen" / "S07-mix.wav"  # the audio both S07 clips carry (identical)
SR = 48000
FPS = 30
REWIND = {"speed": 3, "gain": 0.45}  # assets/rewind.mp4: the before clip reversed at 3x, tape-style (pitch up)
# With no edit lists nothing trims the encoder delays on playback: the first picture shows after x264's B-frame reorder
# delay (2 frames with -bf 2) and the audio starts with ffmpeg's AAC priming (1024 samples). Pad the soundtrack by the
# difference so its content starts with the first picture, and start its timestamps that much early so the muxer begins
# the track at 0 without stretching the first packet. Without this the audio leads by 45 ms.
PAD = round(2 / FPS * SR) - 1024


def ff(*args: str) -> None:
  subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def soundtrack(dest: Path) -> Path:
  page = (HERE / "index.html").read_text()
  total = float(re.search(r'id="root"[^>]*data-duration="([0-9.]+)"', page).group(1))
  clips = re.findall(r'<video id="[^"]+" class="clip" src="assets/(after|before|rewind)\.mp4".*?data-start="([0-9.]+)" data-duration="([0-9.]+)"',
                     page, flags=re.S)
  tmp = FINAL / "s07-48k.wav"
  ff("-i", str(S07), "-ar", str(SR), "-ac", "2", str(tmp))
  s07 = sf.read(tmp, dtype="float32")[0]
  rew = FINAL / "rewind-48k.wav"
  ff("-i", str(S07), "-af", f"areverse,asetrate={44100 * REWIND['speed']},aresample={SR},volume={REWIND['gain']}", "-ac", "2", str(rew))
  rewind = sf.read(rew, dtype="float32")[0]
  out = np.zeros((int(round((total + 0.05) * SR)), 2), np.float32)
  for name, at, dur in clips:
    src = rewind if name == "rewind" else s07
    i, n = int(round(float(at) * SR)), int(round(float(dur) * SR))
    seg = src[:n]
    out[i:i + len(seg)] += seg
  out = out[: int(round(total * SR))]
  sf.write(dest, out, SR, subtype="PCM_24")
  tmp.unlink()
  rew.unlink()
  return dest


def main() -> None:
  wav = soundtrack(FINAL / "mcgurk-vertical-soundtrack.wav")
  padded = FINAL / "soundtrack-vertical-padded.wav"
  audio, _ = sf.read(wav, dtype="float32")
  sf.write(padded, np.concatenate([np.zeros((PAD, 2), np.float32), audio]), SR, subtype="PCM_24")
  ff("-i", str(MASTER), "-itsoffset", f"{-PAD / SR:.6f}", "-i", str(padded), "-map", "0:v", "-map", "1:a",
     "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "slow",
     "-crf", "17", "-maxrate", "20M", "-bufsize", "30M", "-bf", "2", "-g", "15", "-flags", "+cgop", "-coder", "cabac",
     "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "256k", "-ar", str(SR), "-ac", "2",
     "-movflags", "+faststart", "-use_editlist", "0", str(OUT))
  padded.unlink()
  print(OUT)


if __name__ == "__main__":
  main()
