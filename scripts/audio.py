"""Shared audio helpers: decoding, Whisper word timings, finding a script line in a take, Rubber Band warping, and
the small barracks room model the DI lines sit in."""

import difflib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media" / "source.mp4"
BED = ROOT / "media" / "work" / "stems" / "bed.wav"
SR = 44100
END_HOLD = 1.5  # seconds the last frame is held at the end, so the final line can finish


def ff(*args: str) -> None:
  subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def decode(path: Path) -> np.ndarray:
  """Mono 44.1 kHz float samples (cached next to the source as .wav)."""
  wav = path.with_suffix(".wav") if path.suffix != ".wav" else path
  if not wav.exists():
    ff("-i", str(path), "-ac", "1", "-ar", str(SR), str(wav))
  y = sf.read(wav, dtype="float32")[0]
  return y.mean(1) if y.ndim > 1 else y


def whisper_words(audio: Path) -> list[dict]:
  """Whisper word timestamps (cached next to the audio). MLX runs in its own process, apart from torch."""
  cache = audio.with_suffix(".words.json")
  if not cache.exists():
    code = f"""
import json, mlx_whisper
r = mlx_whisper.transcribe({str(audio)!r}, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en",
                           word_timestamps=True, condition_on_previous_text=False)
open({str(cache)!r}, "w").write(json.dumps([w for s in r["segments"] for w in s["words"]]))
"""
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
  return json.loads(cache.read_text())


def norm(w: str) -> str:
  return "".join(c for c in w.lower() if c.isalnum())


def find_line(words: list[dict], text: str, start: int = 0, lookahead: int = 40) -> tuple[int, int, float] | None:
  """Indices (first, last) of the Whisper words that say `text`, searching from `start`, plus a match score.

  Matches on joined letters first (Whisper may split "Auto-merge" or merge "A-S-I"), then falls back to the most
  similar window, since a generated take can slur or swap a word."""
  want = "".join(norm(w) for w in text.split())
  for s0 in range(start, len(words)):
    acc = ""
    for s1 in range(s0, len(words)):
      acc += norm(words[s1]["word"])
      if not want.startswith(acc):
        break
      if acc == want:
        return s0, s1, 1.0
  n = len(text.split())
  best = None
  for s0 in range(start, min(len(words), start + lookahead)):
    for size in range(max(1, n - 2), n + 3):
      s1 = s0 + size - 1
      if s1 >= len(words):
        break
      got = "".join(norm(w["word"]) for w in words[s0 : s1 + 1])
      score = difflib.SequenceMatcher(None, want, got).ratio()
      if best is None or score > best[2]:
        best = (s0, s1, score)
  return best if best and best[2] >= 0.75 else None


def warp(y: np.ndarray, src: list[float], dst: list[float], semis: float, work: Path) -> np.ndarray:
  """Rubber Band R3: map source anchor times onto destination anchor times (both already segment-relative)."""
  with tempfile.TemporaryDirectory(dir=work) as tmp:
    t = Path(tmp)
    sf.write(t / "in.wav", y, SR)
    (t / "map.txt").write_text("".join(f"{int(s * SR)} {int(d * SR)}\n" for s, d in zip(src[1:-1], dst[1:-1])))
    cmd = ["rubberband", "-3", "-q", "-D", f"{dst[-1]:.5f}", "-M", str(t / "map.txt")]
    if abs(semis) > 1e-3:
      cmd += ["-F", "-p", f"{semis:.3f}"]
    subprocess.run([*cmd, str(t / "in.wav"), str(t / "out.wav")], check=True, capture_output=True)
    return sf.read(t / "out.wav", dtype="float32")[0]


def place(dry: np.ndarray, dist: float, lateral: float, reflections: bool = True, damp: bool = True) -> tuple[np.ndarray, np.ndarray]:
  """A voice in the barracks: stereo direct + early reflections, and a mono send for the shared tail. Without
  `reflections` only the direct sound goes out: the floor, ceiling and wall copies (3.6–18 ms late) comb-filter a voice,
  which blurs consonants."""
  c, width, height, mic_h, src_h = 343.0, 8.0, 3.5, 1.2, 0.8
  fc = max(2500.0, 14000.0 / (1 + dist / 10))
  damped = lfilter(*butter(1, fc / (SR / 2)), dry).astype(np.float32) if damp else dry.astype(np.float32)  # air absorption
  paths = [(math.hypot(dist, lateral), lateral, 1.0)]  # direct
  if reflections:
    paths += [(math.hypot(dist, lateral, mic_h + src_h), lateral, 0.55)]  # floor
    paths += [(math.hypot(dist, lateral, 2 * height - mic_h - src_h), lateral, 0.5)]  # ceiling
    for wall in (width / 2, -width / 2):  # side walls
      y_img = 2 * wall - lateral
      paths += [(math.hypot(dist, y_img), y_img, 0.45)]
  near = paths[0][0]
  n = len(dry) + int(0.08 * SR)
  out = np.zeros((n, 2), np.float32)
  for length, y_pos, refl in paths:
    delay = int((length - 2.0) / c * SR)
    g = refl * 2.0 / length
    pan = max(-0.9, min(0.9, math.sin(math.atan2(y_pos, dist))))
    seg = damped * g
    end = min(n, delay + len(seg))
    out[delay:end, 0] += seg[: end - delay] * math.sqrt((1 - pan) / 2)
    out[delay:end, 1] += seg[: end - delay] * math.sqrt((1 + pan) / 2)
  send = np.zeros(n, np.float32)
  d0 = int((near - 2.0) / c * SR)
  send[d0 : d0 + len(dry)] = damped * (0.15 + 0.6 * min(1.0, dist / 20)) * 2.0 / near
  return out, send


def tail_ir(rt_low: float = 1.4, rt_high: float = 0.7, predelay: float = 0.025, seed: int = 5) -> np.ndarray:
  """Synthetic stereo barracks tail: lows ring longer than highs."""
  rng = np.random.default_rng(seed)
  n = int(rt_low * SR)
  t = np.arange(n) / SR
  noise = rng.standard_normal((n, 2)).astype(np.float32)
  b_lo, a_lo = butter(2, 2000 / (SR / 2))
  lo = lfilter(b_lo, a_lo, noise, axis=0)
  hi = noise - lo
  ir = lo * (10 ** (-3 * t / rt_low))[:, None] + hi * (10 ** (-3 * t / rt_high))[:, None]
  ir = np.vstack([np.zeros((int(predelay * SR), 2)), ir])
  return (ir / np.sqrt((ir**2).sum(0)).max()).astype(np.float32)


def render_pass(name: str = "full-pass", solo: Path | None = None) -> Path:
  """Review render: the placed chorus (data/chorus.json) and the DI track over the picture. No room bed."""
  script = json.loads((ROOT / "data" / "script.json").read_text())
  w0, w1 = script["window"]["start"], script["window"]["end"]
  n = int((w1 - w0 + END_HOLD) * SR)
  tracks = []
  meta = ROOT / "data" / "chorus.json"
  if meta.exists():
    tracks.append(ROOT / "media" / "voices" / "chorus-music" / json.loads(meta.read_text())["variant"] / "track.wav")
  tracks.append(solo or ROOT / "media" / "voices" / "di" / "di.wav")
  mix = np.zeros((n, 2), np.float32)
  for t in tracks:
    if t.exists():
      y = sf.read(t, dtype="float32")[0]
      y = y if y.ndim == 2 else np.stack([y, y], 1)
      m = min(n, len(y))
      mix[:m] += y[:m] / (np.abs(y).max() + 1e-9)  # chorus and DI at the same peak level
  mix *= 0.95 / (np.abs(mix).max() + 1e-9)
  wav = ROOT / "media" / "voices" / f"{name}.wav"
  sf.write(wav, mix, SR)
  out = ROOT / "renders" / "proto" / f"{name}.mp4"
  out.parent.mkdir(parents=True, exist_ok=True)
  ff("-ss", f"{w0:.3f}", "-to", f"{w1:.3f}", "-i", str(SRC), "-i", str(wav), "-map", "0:v", "-map", "1:a",
     "-vf", f"tpad=stop_mode=clone:stop_duration={END_HOLD}", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
     "-c:a", "aac", "-b:a", "192k", "-shortest", str(out))
  return out
