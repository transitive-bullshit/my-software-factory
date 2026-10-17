"""Final exports of the McGurk demo, for X and YouTube, from a high-quality HyperFrames master.

HyperFrames encodes its audio at ~94 kbps AAC, so the soundtrack is rebuilt losslessly here instead: every timed
<video> in index.html plays the S07 mix (after/before) or its rewind, placed at its data-start, from the original WAV.

  X:        H.264 High 4.1, 1080p30, capped VBR (crf 18, max 10 Mbps, 16 Mb buffer), keyframe every 2 s, AAC-LC
            192 kbps 48 kHz, moov at the front (+faststart) so it streams before it has fully downloaded.
  YouTube:  Google's recommended upload settings: H.264 High, 2 consecutive B-frames, closed GOP of half the frame
            rate, CABAC, VBR (crf 16), AAC-LC 384 kbps 48 kHz stereo, moov at the front, no edit lists (so the
            soundtrack is padded to stay in sync, see YT_PAD).

  npx hyperframes render -o ../../renders/promo/final/mcgurk-master.mp4 --fps 30 --crf 12
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
MASTER = FINAL / "mcgurk-master.mp4"
S07 = ROOT / "media" / "full" / "shots-gen" / "S07-mix.wav"  # the audio both S07 clips carry (identical)
SR = 48000
FPS = 30
REWIND = {"speed": 3, "gain": 0.45}  # assets/rewind.mp4: the before clip reversed at 3x, tape-style (pitch up)
# YouTube wants no edit lists, so nothing trims the encoder delays on playback: the first picture shows after x264's
# B-frame reorder delay (2 frames with -bf 2) and the audio starts with ffmpeg's AAC priming (1024 samples). Pad the
# soundtrack by the difference so its content starts with the first picture, and start its timestamps that much early
# so the muxer begins the track at 0 without stretching the first packet. Without this the audio leads by 45 ms.
YT_PAD = round(2 / FPS * SR) - 1024


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
  wav = soundtrack(FINAL / "mcgurk-soundtrack.wav")
  video = ["-map", "0:v", "-map", "1:a", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:v", "libx264", "-profile:v", "high", "-preset", "slow"]
  ff("-i", str(MASTER), "-i", str(wav), *video, "-shortest",
     "-level", "4.1", "-crf", "18", "-maxrate", "10M", "-bufsize", "16M", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
     "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart",
     str(FINAL / "mcgurk-x.mp4"))
  padded = FINAL / "soundtrack-yt.wav"
  audio, _ = sf.read(wav, dtype="float32")
  sf.write(padded, np.concatenate([np.zeros((YT_PAD, 2), np.float32), audio]), SR, subtype="PCM_24")
  ff("-i", str(MASTER), "-itsoffset", f"{-YT_PAD / SR:.6f}", "-i", str(padded), *video,
     "-crf", "16", "-bf", "2", "-g", "15", "-flags", "+cgop", "-coder", "cabac",
     "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "384k", "-ar", str(SR), "-ac", "2", "-movflags", "+faststart", "-use_editlist", "0",
     str(FINAL / "mcgurk-youtube.mp4"))
  padded.unlink()
  for f in ("mcgurk-x.mp4", "mcgurk-youtube.mp4"):
    print(FINAL / f)


if __name__ == "__main__":
  main()
