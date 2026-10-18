"""The vertical (9:16) cut of The AI Engineer's Creed for YouTube Shorts, Instagram Reels and TikTok: one file for all three.

The plate (crop.py) with the HyperFrames layer laid over it (the title on frame 0, the captions, the credits card:
overlay.mov, transparent ProRes 4444), and the 16:9 cut's lossless soundtrack (renders/full/generative-soundtrack.wav)
untouched: the same timeline, so it lines up sample for sample. The audio is encoded exactly as the YouTube export
(scripts/release.py: AAC-LC 384 kbps, padded by YT_PAD), so its stream comes out identical to that file's.

  1080x1920 29.97 fps, H.264 High 4.1, 2 consecutive B-frames, closed GOP of 15 frames, CABAC, VBR (crf 17) capped at
  20 Mbps (Instagram's ceiling is 25), AAC-LC 384 kbps 48 kHz stereo, moov at the front, no edit lists. The thumbnail
  (the post's cover) is frame 0, the title frame, as a 1080x1920 JPEG.

  uv run --project ../.. --group analysis python crop.py    # assets/plate.mp4
  npm run overlay                                           # ../../renders/promo/creed-vertical/overlay.mov
  uv run --project ../.. --group analysis python export.py draft   # ../../renders/promo/creed-vertical/draft.mp4, for review
  uv run --project ../.. --group analysis python export.py         # ../../renders/promo/final/, then the checks
  uv run --project ../.. --group analysis python export.py clip    # the creed's opening alone, same settings

The clip (ai-engineers-creed-clip-vertical.mp4) is the vertical twin of scripts/release.py's wide one: the cut's first
8.15 s (the title frame, "Prompt!", then C01 and C02, cut in the gap before C03), faded out on picture and sound.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NAME = "ai-engineers-creed-vertical"
PLATE = HERE / "assets" / "plate.mp4"
WORK = ROOT / "renders" / "promo" / "creed-vertical"
OVERLAY = WORK / "overlay.mov"
FINAL = ROOT / "renders" / "promo" / "final"
OUT = FINAL / f"{NAME}.mp4"
THUMB = FINAL / f"{NAME}-thumbnail.jpg"
CLIP_OUT = FINAL / "ai-engineers-creed-clip-vertical.mp4"
CLIP, CLIP_FADE = 8.15, 0.25  # as scripts/release.py: "mine." ends at 7.70 s and C03 starts at 8.20 s
SOUNDTRACK = ROOT / "renders" / "full" / "generative-soundtrack.wav"
WIDE = ROOT / "renders" / "full" / "generative.mp4"  # the 16:9 cut (uncaptioned master)
YOUTUBE = ROOT / "renders" / "final" / "ai-engineers-creed-youtube.mp4"  # the published 16:9 file
SR = 48000
FPS = 30000 / 1001
# as scripts/release.py: with no edit lists nothing trims the encoder delays on playback, so pad the soundtrack by x264's
# B-frame reorder delay (2 frames with -bf 2) less the AAC priming (1024 samples) and start its timestamps that early
PAD = round(2 / FPS * SR) - 1024


def ff(*args: str) -> None:
  subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def probe(path: Path, stream: str, entries: str) -> str:
  return subprocess.run(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", entries, "-of", "csv=p=0", str(path)],
                        capture_output=True, text=True, check=True).stdout.strip()


def composite(dest: Path, video: list[str], audio: list[str], clip: float | None = None) -> Path:
  """The plate (held on its last frame under the credits) with the layer over it, and the padded soundtrack; with
  `clip`, only its first `clip` seconds, faded out over the last CLIP_FADE (ffmpeg's fade and afade, as the wide clip)."""
  dest.parent.mkdir(parents=True, exist_ok=True)
  padded = WORK / "soundtrack-padded.wav"
  src = SOUNDTRACK
  if clip:
    src = WORK / "soundtrack-clip.wav"
    ff("-i", str(SOUNDTRACK), "-t", f"{clip:.3f}", "-af", f"afade=t=out:st={clip - CLIP_FADE:.3f}:d={CLIP_FADE}", "-c:a", "pcm_s24le", str(src))
  sound, sr = sf.read(src, dtype="float32")
  assert sr == SR, f"the soundtrack is {sr} Hz"
  sf.write(padded, np.concatenate([np.zeros((PAD, sound.shape[1]), np.float32), sound]), SR, subtype="PCM_24")
  tail = f",trim=end={clip:.3f},fade=t=out:st={clip - CLIP_FADE:.3f}:d={CLIP_FADE}" if clip else ""
  ff("-i", str(PLATE), "-i", str(OVERLAY), "-itsoffset", f"{-PAD / SR:.6f}", "-i", str(padded), "-filter_complex",
     f"[0:v]tpad=stop_mode=clone:stop_duration=15[p];[p][1:v]overlay=0:0:format=auto:shortest=1{tail},format=yuv420p[v]",
     "-map", "[v]", "-map", "2:a", "-fps_mode", "passthrough", *video, "-colorspace", "bt709", "-color_primaries", "bt709",
     "-color_trc", "bt709", "-color_range", "tv", *audio, "-ar", str(SR), "-ac", "2", "-movflags", "+faststart",
     "-use_editlist", "0", str(dest))
  padded.unlink()
  if clip:
    src.unlink()
  return dest


def draft() -> None:
  out = composite(WORK / "draft.mp4", ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-bf", "2"],
                  ["-c:a", "aac", "-b:a", "192k"])
  print(out)


# the social settings (see the top)
VIDEO = ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-preset", "slow", "-crf", "17",
         "-maxrate", "20M", "-bufsize", "30M", "-bf", "2", "-g", "15", "-flags", "+cgop", "-coder", "cabac"]
AUDIO = ["-c:a", "aac", "-profile:a", "aac_low", "-b:a", "384k"]


def final() -> None:
  composite(OUT, VIDEO, AUDIO)
  ff("-i", str(OUT), "-frames:v", "1", "-q:v", "2", str(THUMB))
  for f in (OUT, THUMB):
    print(f.relative_to(ROOT), f"{f.stat().st_size / 1e6:.1f} MB")
  check()


def clip() -> None:
  """The clip, then its checks: its length, the audio starting with the first picture and matching the soundtrack up to
  the fade, the title on frame 0 and black at the end."""
  from scipy.signal import correlate

  composite(CLIP_OUT, VIDEO, AUDIO, CLIP)
  print(CLIP_OUT.relative_to(ROOT), f"{CLIP_OUT.stat().st_size / 1e6:.1f} MB")
  frames = int(probe(CLIP_OUT, "v:0", "stream=nb_frames"))
  print(f"video: {probe(CLIP_OUT, 'v:0', 'stream=width,height')}, {frames} frames ({frames / FPS:.3f} s)")
  assert frames == int(np.ceil(CLIP * FPS))
  ours, ref = pcm(CLIP_OUT), sf.read(SOUNDTRACK, dtype="float32")[0]
  body = int((CLIP - CLIP_FADE) * SR)
  c = correlate(ours[:body, 0], ref[:body - 4 * SR, 0], mode="valid", method="fft")
  lag = int(np.argmax(c))
  picture = float(probe(CLIP_OUT, "v:0", "stream=start_time"))
  err = ours[lag:lag + body] - ref[:body]
  snr = 10 * np.log10(np.sum(ref[:body] ** 2) / np.sum(err**2))
  tail = np.abs(ours[lag + int(CLIP * SR) - 480:lag + int(CLIP * SR)]).max()
  print(f"audio: starts {lag} samples in (the first picture at {picture * SR:.0f}), SNR {snr:.1f} dB before the fade, "
        f"peak {tail:.4f} in its last 10 ms, {len(ours) - lag} samples of content ({(len(ours) - lag) / SR:.3f} s)")
  assert abs(lag - picture * SR) < 1 and snr > 30
  raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(CLIP_OUT), "-an", "-fps_mode", "passthrough", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
  v = np.frombuffer(raw, np.uint8).reshape(frames, -1).astype(int)
  print(f"title frame: frame 0 differs from frame 1 by {np.abs(v[0] - v[1]).mean():.1f}; last frame mean {v[-1].mean():.1f} "
        f"(0 is black), one before {v[-2].mean():.1f}")


def pcm(path: Path) -> np.ndarray:
  raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
  return np.frombuffer(raw, np.float32).reshape(-1, 2)


def check() -> None:
  """The length matches the 16:9 cut frame for frame, the audio is the 16:9 cut's sample for sample (and starts with the
  first picture), and the title is on frame 0 alone."""
  from scipy.signal import correlate

  frames = int(probe(OUT, "v:0", "stream=nb_frames"))
  wide = int(probe(WIDE, "v:0", "stream=nb_frames"))
  size = probe(OUT, "v:0", "stream=width,height")
  print(f"video: {size}, {frames} frames ({frames / FPS:.3f} s); the 16:9 cut: {wide} frames ({wide / FPS:.3f} s)")
  assert frames == wide and size == "1080,1920"
  # the audio stream, packet for packet, against the published 16:9 YouTube file
  md5 = lambda p: subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:a", "-c", "copy", "-f", "md5", "-"],
                                 capture_output=True, text=True, check=True).stdout.strip()
  print(f"audio stream identical to {YOUTUBE.relative_to(ROOT)}: {md5(OUT) == md5(YOUTUBE)}")
  # decoded, against the lossless soundtrack: its content starts with the first picture, and differs only by the codec's
  # own error (with no edit list the decoder keeps the AAC priming, so the lead-in is the pad plus the priming)
  ours, ref = pcm(OUT), sf.read(SOUNDTRACK, dtype="float32")[0]
  head = 8 * SR
  c = correlate(ours[:head + SR, 0], ref[:head, 0], mode="valid", method="fft")
  lag = int(np.argmax(c))
  picture = float(probe(OUT, "v:0", "stream=start_time"))
  err = ours[lag:lag + len(ref)] - ref[:len(ours) - lag]
  snr = 10 * np.log10(np.sum(ref**2) / np.sum(err**2))
  print(f"audio vs the lossless soundtrack: starts {lag} samples in ({lag / SR * 1000:.2f} ms; the first picture at "
        f"{picture * 1000:.2f} ms), SNR {snr:.1f} dB over the whole cut")
  assert abs(lag - picture * SR) < 1 and snr > 30
  if YOUTUBE.exists():
    print(f"decoded audio identical to the YouTube file's: {np.array_equal(pcm(YOUTUBE), ours)}")
  # frame 0 is the title, frame 1 the footage (passthrough: no frames repeated to fill the B-frame delay)
  raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(OUT), "-an", "-fps_mode", "passthrough", "-frames:v", "2", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
  f0, f1 = np.frombuffer(raw, np.uint8).reshape(2, -1).astype(int)
  print(f"title frame: frame 0 differs from frame 1 by {np.abs(f0 - f1).mean():.1f} (mean, 0-255)")
  print("sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__ == "__main__":
  {"draft": draft, "check": check, "clip": clip}.get(sys.argv[1] if len(sys.argv) > 1 else "", final)()
