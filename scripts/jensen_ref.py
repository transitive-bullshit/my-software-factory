"""Clean Jensen-only reference audio from a long two-person interview (cached; outputs stay in the ignored /reference).

1. Whisper segments on the 16 kHz span (reference/jensen/work/span16k.wav)
2. ECAPA speaker embedding per segment, two clusters; Jensen is the one with more talk time and fewer questions
3. Confident Jensen segments, cut from the 48 kHz span:
   jensen-clean.wav   everything confident (for local cloning or training)
   jensen-3min.wav    the clearest ~3 min (ElevenLabs instant clone, Fish Audio)
   jensen-30s.wav     the clearest ~30 s (zero-shot models)
   jensen-segments.json  times and text of every kept segment

Run: uv run --group analysis --group voice python scripts/jensen_ref.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference" / "jensen"
WORK = REF / "work"
SPAN_OFFSET = 180.0  # span16k/48k start 3:00 into the episode, after the intro


def whisper() -> list[dict]:
  out = WORK / "whisper.json"
  if not out.exists():
    code = f"""
import json, mlx_whisper
r = mlx_whisper.transcribe({str(WORK / "span16k.wav")!r}, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                           language="en", condition_on_previous_text=False)
open({str(out)!r}, "w").write(json.dumps([{{"start": s["start"], "end": s["end"], "text": s["text"].strip()}} for s in r["segments"]]))
"""
    subprocess.run([sys.executable, "-c", code], check=True)  # MLX in its own process, apart from torch
  return json.loads(out.read_text())


def embed(segs: list[dict], y16: np.ndarray) -> np.ndarray:
  import torch
  from speechbrain.inference.speaker import EncoderClassifier

  enc = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir=str(ROOT / ".cache" / "ecapa"))
  vecs = []
  with torch.no_grad():
    for s in segs:
      clip = torch.tensor(y16[int(s["start"] * 16000) : int(s["end"] * 16000)]).float().unsqueeze(0)
      vecs.append(enc.encode_batch(clip).squeeze().cpu().numpy())
  v = np.stack(vecs)
  return v / np.linalg.norm(v, axis=1, keepdims=True)


def main() -> None:
  segs = [s for s in whisper() if s["end"] - s["start"] >= 1.5 and s["text"]]
  y16, _ = sf.read(WORK / "span16k.wav", dtype="float32")
  y48, _ = sf.read(WORK / "span48k.wav", dtype="float32")
  from sklearn.cluster import KMeans

  emb = embed(segs, y16)
  labels = KMeans(2, n_init=10, random_state=0).fit_predict(emb)
  stats = []
  for k in (0, 1):
    idx = labels == k
    dur = sum(s["end"] - s["start"] for s, m in zip(segs, idx) if m)
    q = np.mean([s["text"].endswith("?") for s, m in zip(segs, idx) if m])
    stats.append((dur, q))
    print(f"cluster {k}: {dur / 60:5.1f} min, {q:.0%} of segments end in '?'")
  jensen = int(np.argmax([d for d, _ in stats]))
  if stats[jensen][1] > stats[1 - jensen][1]:
    sys.exit("talk-time and question heuristics disagree; check the clusters by ear")
  c = np.stack([emb[labels == k].mean(0) for k in (0, 1)])
  c /= np.linalg.norm(c, axis=1, keepdims=True)
  margin = emb @ c[jensen] - emb @ c[1 - jensen]

  kept = []
  for s, lab, m in zip(segs, labels, margin):
    if lab == jensen and m > 0.3 and not s["text"].endswith("?"):
      a, b = int(s["start"] * 48000), int(s["end"] * 48000)
      clip = y48[a:b]
      kept.append({**s, "margin": float(m), "rms": float(np.sqrt(np.mean(clip**2))), "episode_time": round(s["start"] + SPAN_OFFSET, 2)})
  print(f"kept {len(kept)} Jensen segments, {sum(s['end'] - s['start'] for s in kept) / 60:.1f} min")

  gap = np.zeros(int(0.3 * 48000), np.float32)

  def render(sel: list[dict], name: str) -> None:
    parts = []
    for s in sorted(sel, key=lambda s: s["start"]):
      parts += [y48[int(s["start"] * 48000) : int(s["end"] * 48000)], gap]
    audio = np.concatenate(parts)
    audio *= 10 ** (-1 / 20) / (np.abs(audio).max() + 1e-9)
    sf.write(REF / name, audio, 48000, subtype="PCM_16")
    print(f"{(REF / name).relative_to(ROOT)}  {len(audio) / 48000 / 60:.1f} min")

  render(kept, "jensen-clean.wav")
  best = sorted([s for s in kept if 4 <= s["end"] - s["start"] <= 20], key=lambda s: -s["margin"])
  pick, total = [], 0.0
  for s in best:
    if total >= 180:
      break
    pick.append(s)
    total += s["end"] - s["start"]
  render(pick, "jensen-3min.wav")
  pick30, total = [], 0.0
  for s in best:
    if total >= 30:
      break
    pick30.append(s)
    total += s["end"] - s["start"]
  render(pick30, "jensen-30s.wav")
  (REF / "jensen-segments.json").write_text(json.dumps(kept, indent=1))


if __name__ == "__main__":
  main()
