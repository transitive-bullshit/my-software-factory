"""Build a clean, single-speaker reference set of Jensen Huang's voice for voice cloning.

Sources are 30-minute sections of studio-mic'd podcast interviews (see SOURCES), fetched with yt-dlp into
reference/voice/jensen/raw/. Pipeline (cached; everything stays in the ignored /reference):

1. Whisper segments + word timestamps for each source (separate process: MLX and torch don't mix).
2. ECAPA speaker embeddings on 1.5 s windows of speech; per-source k-means; Jensen is the cluster that matches
   across all sources (the hosts differ, he doesn't).
3. Keep phrase-aligned chunks where every window is Jensen, nobody else is talking, Whisper is confident and
   nothing is clipped; rank by similarity to his voice print; pick ~TARGET seconds balanced across sources.
4. Export loudness-normalized 44.1 kHz mono clips, one concatenated file, and a manifest with source links.

Run: uv run --group analysis --group voice python scripts/voice_ref.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "reference" / "voice" / "jensen"
RAW, WORK, CLIPS = BASE / "raw", BASE / "work", BASE / "clips"
TARGET = 600.0
UPLOAD = 150.0  # ElevenLabs Instant Voice Cloning: 1-2 min ideal, little gain past 3 min
WIN, HOP = 1.5, 0.75
MIN_CHUNK, MAX_CHUNK = 5.0, 20.0
# (source, whole seconds into the episode) of chunks a stem-split check flagged for background sound
EXCLUDE = {("ezraklein", 1556)}

SOURCES = [
  {"name": "lex494", "url": "https://www.youtube.com/watch?v=vif8NQcjVf0", "offset": 8 * 60,
   "title": "Lex Fridman Podcast #494"},
  {"name": "jre2422", "url": "https://www.youtube.com/watch?v=3hptKYix4X8", "offset": 5 * 60,
   "title": "Joe Rogan Experience #2422", "pick": False},  # anchors the voice print; mic bleed and room, so no clips
  {"name": "ezraklein", "url": "https://www.youtube.com/watch?v=HjurAWAr_nY", "offset": 5 * 60,
   "title": "The Ezra Klein Show"},
]


def decode(src: Path, out: Path, rate: int) -> None:
  if not out.exists():
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", str(rate), str(out)], check=True)


def transcribe(wav: Path, out: Path) -> dict:
  if not out.exists():
    code = f"""
import json, mlx_whisper
r = mlx_whisper.transcribe({str(wav)!r}, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                           language="en", word_timestamps=True, condition_on_previous_text=False)
open({str(out)!r}, "w").write(json.dumps(r))
"""
    subprocess.run([sys.executable, "-c", code], check=True)
  return json.loads(out.read_text())


def embed_windows(audio: np.ndarray, spans: list[tuple[float, float]], encoder) -> tuple[np.ndarray, np.ndarray]:
  import torch

  starts = []
  for a, b in spans:
    t = a
    while t + WIN <= b + 1e-6:
      starts.append(t)
      t += HOP
  starts = np.array(starts)
  embs = []
  for i in range(0, len(starts), 64):
    batch = np.stack([audio[int(s * 16000) : int(s * 16000) + int(WIN * 16000)] for s in starts[i : i + 64]])
    with torch.no_grad():
      e = encoder.encode_batch(torch.from_numpy(batch).float()).squeeze(1).numpy()
    embs.append(e)
  embs = np.concatenate(embs)
  return starts, embs / np.linalg.norm(embs, axis=1, keepdims=True)


def main() -> None:
  from sklearn.cluster import KMeans
  from speechbrain.inference.speaker import EncoderClassifier

  WORK.mkdir(parents=True, exist_ok=True)
  CLIPS.mkdir(parents=True, exist_ok=True)
  encoder = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb", savedir=str(ROOT / ".cache" / "ecapa"), run_opts={"device": "cpu"}
  )

  data = []
  for src in SOURCES:
    raw = next(RAW.glob(f"{src['name']}.*"))
    w16, w44 = WORK / f"{src['name']}-16k.wav", WORK / f"{src['name']}-44k.wav"
    decode(raw, w16, 16000)
    decode(raw, w44, 44100)
    whisper = transcribe(w16, WORK / f"{src['name']}.whisper.json")
    segs = [s for s in whisper["segments"] if s.get("words")]
    audio16, _ = sf.read(w16, dtype="float32")
    cache = WORK / f"{src['name']}.windows.npz"
    if cache.exists():
      z = np.load(cache)
      starts, embs = z["starts"], z["embs"]
    else:
      starts, embs = embed_windows(audio16, [(s["start"], s["end"]) for s in segs], encoder)
      np.savez(cache, starts=starts, embs=embs)
    km = KMeans(n_clusters=3, n_init=10, random_state=0).fit(embs)
    cents = np.stack([embs[km.labels_ == k].mean(0) for k in range(3)])
    cents /= np.linalg.norm(cents, axis=1, keepdims=True)
    data.append({**src, "w44": w44, "w16": w16, "segs": segs, "starts": starts, "embs": embs, "labels": km.labels_, "cents": cents})
    print(f"{src['name']}: {len(segs)} segments, {len(starts)} windows, cluster sizes {np.bincount(km.labels_)}")

  # Jensen = the one cluster per source that best matches across all sources
  best, best_score = None, -9.0
  for a in range(3):
    for b in range(3):
      for c in range(3):
        cs = [data[0]["cents"][a], data[1]["cents"][b], data[2]["cents"][c]]
        score = sum(float(cs[i] @ cs[j]) for i in range(3) for j in range(i + 1, 3))
        if score > best_score:
          best, best_score = (a, b, c), score
  print(f"seed clusters {best}, mean cross-source similarity {best_score / 3:.3f}")
  seed = np.mean([d["cents"][k] for d, k in zip(data, best)], axis=0)
  seed /= np.linalg.norm(seed)
  # his voice often splits into two clusters (calm vs animated): every cluster near the seed is him, the rest are hosts
  for d in data:
    d["jensen_ks"] = [k for k in range(3) if float(d["cents"][k] @ seed) > 0.6]
    d["host_ks"] = [k for k in range(3) if k not in d["jensen_ks"]]
    print(f"{d['name']}: jensen clusters {d['jensen_ks']}, host clusters {d['host_ks']}")
  voiceprint = np.concatenate([d["embs"][np.isin(d["labels"], d["jensen_ks"])] for d in data]).mean(0)
  voiceprint /= np.linalg.norm(voiceprint)

  candidates = []
  for d in data:
    sims = d["embs"] @ voiceprint
    host_sims = np.max(np.stack([d["embs"] @ d["cents"][j] for j in d["host_ks"]]), axis=0)
    is_jensen = np.isin(d["labels"], d["jensen_ks"]) & (sims - host_sims > 0.15)
    # merge consecutive Whisper segments into phrase-aligned chunks of only-Jensen speech
    chunk = []

    def flush():
      if not chunk:
        return
      a, b = chunk[0]["start"], chunk[-1]["end"]
      if b - a >= MIN_CHUNK:
        m = (d["starts"] >= a - 0.1) & (d["starts"] + WIN <= b + 0.1)
        words = [w for s in chunk for w in s["words"]]
        text = "".join(s["text"] for s in chunk).strip()
        candidates.append({
          "source": d["name"], "title": d["title"], "url": d["url"], "offset": d["offset"],
          "start": a, "end": b, "dur": b - a, "text": text,
          "sim": float(sims[m].mean()), "min_sim": float(sims[m].min()),
          "prob": float(np.mean([w.get("probability", 1) for w in words])),
          "w44": d["w44"], "w16": d["w16"],
        })
      chunk.clear()

    for s in d["segs"]:
      m = (d["starts"] >= s["start"] - 0.1) & (d["starts"] + WIN <= s["end"] + 0.1)
      ok = m.any() and bool(is_jensen[m].all()) and s.get("no_speech_prob", 0) < 0.3
      noisy = any(tag in s["text"].lower() for tag in ("[", "(laugh", "music", "applause"))
      contiguous = not chunk or s["start"] - chunk[-1]["end"] < 0.6
      if ok and not noisy and contiguous and (not chunk or s["end"] - chunk[0]["start"] <= MAX_CHUNK):
        chunk.append(s)
      else:
        flush()
        if ok and not noisy:
          chunk.append(s)
    flush()

  # quality gates, then rank and balance across sources
  import torch

  hosts = np.stack([d["cents"][j] for d in data for j in d["host_ks"]])
  picks = {s["name"] for s in SOURCES if s.get("pick", True)}
  good = []
  for c in candidates:
    if c["source"] not in picks or (c["source"], int(c["offset"] + c["start"])) in EXCLUDE:
      continue
    a16, _ = sf.read(c["w16"], start=int(c["start"] * 16000), stop=int(c["end"] * 16000), dtype="float32")
    with torch.no_grad():
      e = encoder.encode_batch(torch.from_numpy(a16[None]).float()).squeeze().numpy()
    e /= np.linalg.norm(e)
    c["sim"], c["margin"] = float(e @ voiceprint), float(e @ voiceprint - (hosts @ e).max())
    if c["sim"] < 0.6 or c["margin"] < 0.2:
      continue
    audio, sr = sf.read(c["w44"], start=int(c["start"] * 44100), stop=int(c["end"] * 44100), dtype="float32")
    peak, rms = float(np.max(np.abs(audio))), float(np.sqrt(np.mean(audio**2)))
    c.update(peak=peak, rms_db=20 * np.log10(rms + 1e-9))
    if c["sim"] > 0.5 and c["min_sim"] > 0.3 and c["prob"] > 0.7 and peak < 0.99 and c["rms_db"] > -40 and "?" not in c["text"]:
      good.append(c)
  pools = {n: sorted([c for c in good if c["source"] == n], key=lambda c: -c["sim"]) for n in sorted(picks)}
  picked, total = [], 0.0
  while total < TARGET and any(pools.values()):
    for name in pools:
      if pools[name] and total < TARGET:
        c = pools[name].pop(0)
        picked.append(c)
        total += c["dur"]
  picked.sort(key=lambda c: (c["source"], c["start"]))
  print(f"{len(candidates)} candidate chunks, {len(good)} pass the gates, picked {len(picked)} = {total / 60:.1f} min")

  # export
  for f in CLIPS.glob("*.wav"):
    f.unlink()
  manifest, parts = [], []
  for i, c in enumerate(picked, 1):
    abs_start = c["offset"] + c["start"]
    name = f"{i:02d}-{c['source']}-{int(abs_start // 60):02d}m{int(abs_start % 60):02d}s.wav"
    out = CLIPS / name
    subprocess.run(
      ["ffmpeg", "-v", "error", "-y", "-ss", f"{c['start']:.3f}", "-to", f"{c['end'] + 0.15:.3f}", "-i", str(c["w44"]),
       "-af", "afade=t=in:d=0.03,loudnorm=I=-20:TP=-3:LRA=11,aresample=44100", "-ac", "1", "-ar", "44100", str(out)],
      check=True,
    )
    parts.append(out)
    manifest.append({
      "file": f"clips/{name}", "source": c["title"], "url": f"{c['url']}&t={int(abs_start)}s",
      "start": round(abs_start, 2), "duration": round(c["dur"], 2), "voice_match": round(c["sim"], 3),
      "host_margin": round(c["margin"], 3), "text": c["text"],
    })
    c["out"] = out
  listfile = WORK / "concat.txt"
  silence = WORK / "gap.wav"
  subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.4", str(silence)], check=True)
  listfile.write_text("".join(f"file '{p}'\nfile '{silence}'\n" for p in parts))
  subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c:a", "pcm_s16le", str(BASE / "jensen-reference.wav")], check=True)
  # upload pack: the strongest matches from one source, for consistent recording quality
  best_src = max(picks, key=lambda n: np.mean([c["sim"] for c in picked if c["source"] == n]))
  upload, up_total = [], 0.0
  for c in sorted([c for c in picked if c["source"] == best_src], key=lambda c: -c["sim"]):
    if up_total + c["dur"] <= UPLOAD + 10:
      upload.append(c)
      up_total += c["dur"]
  upload.sort(key=lambda c: c["start"])
  listfile.write_text("".join(f"file '{c['out']}'\nfile '{silence}'\n" for c in upload))
  subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c:a", "libmp3lame",
                  "-b:a", "192k", str(BASE / "jensen-elevenlabs-upload.mp3")], check=True)
  (BASE / "manifest.json").write_text(json.dumps({
    "total_seconds": round(total, 1), "upload": {"file": "jensen-elevenlabs-upload.mp3", "source": best_src,
    "seconds": round(up_total, 1), "clips": [c["out"].name for c in upload]}, "clips": manifest}, indent=2) + "\n")
  print(f"upload pack: {len(upload)} clips from {best_src}, {up_total:.0f} s")
  print(f"wrote {BASE.relative_to(ROOT)}/jensen-reference.wav and manifest.json")


if __name__ == "__main__":
  main()
