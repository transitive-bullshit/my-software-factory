"""Small ElevenLabs client for the voice work. Reads ELEVENLABS_API_KEY from the environment or ~/.env; never
prints it. Outputs land in the ignored /media/voices.

  uv run python scripts/eleven.py account                 plan tier and character budget
  uv run python scripts/eleven.py voices                  stock (premade) voices -> media/voices/stock.json + preview mp3s
  uv run python scripts/eleven.py design NAME FILE.json   Voice Design previews from a spec -> media/voices/design/NAME/
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "media" / "voices"
API = "https://api.elevenlabs.io"


def api_key() -> str:
  key = os.environ.get("ELEVENLABS_API_KEY")
  if not key:
    env = Path.home() / ".env"
    if env.exists():
      for line in env.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip().removeprefix("export ").strip() == "ELEVENLABS_API_KEY":
          key = value.strip().strip("'\"")
  if not key:
    sys.exit("ELEVENLABS_API_KEY not found in the environment or ~/.env")
  return key


def call(method: str, path: str, body: dict | None = None, retries: int = 6) -> dict:
  for attempt in range(retries):
    req = urllib.request.Request(
      API + path,
      method=method,
      data=json.dumps(body).encode() if body is not None else None,
      headers={"xi-api-key": api_key(), "content-type": "application/json", "accept": "application/json"},
    )
    try:
      with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
      if e.code in (429, 503) and attempt < retries - 1:  # concurrency or rate limit: back off and retry
        time.sleep(2 * (attempt + 1))
        continue
      sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
  raise RuntimeError("unreachable")


def tts(voice_id: str, text: str, dest: Path, model_id: str = "eleven_v3", seed: int = 7) -> Path:
  """Text to speech -> mp3 (cached by path)."""
  if not dest.exists():
    req = urllib.request.Request(
      f"{API}/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
      method="POST",
      data=json.dumps({"text": text, "model_id": model_id, "seed": seed}).encode(),
      headers={"xi-api-key": api_key(), "content-type": "application/json", "accept": "audio/mpeg"},
    )
    try:
      with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
      sys.exit(f"TTS {voice_id} -> HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
  return dest


def tts_timed(voice_id: str, text: str, dest: Path, model_id: str = "eleven_v4", seed: int = 7) -> dict:
  """Text to speech with character timestamps -> mp3 at `dest` plus its alignment (both cached)."""
  meta = dest.with_suffix(".json")
  if not meta.exists():
    res = call("POST", f"/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
               {"text": text, "model_id": model_id, "seed": seed})
    dest.write_bytes(base64.b64decode(res["audio_base64"]))
    meta.write_text(json.dumps({"text": text, "alignment": res.get("alignment") or res.get("normalized_alignment")}))
  return json.loads(meta.read_text())


def compose(plan: dict, dest: Path, model_id: str = "music_v2_5", seed: int | None = None) -> Path:
  """Eleven Music from a composition plan -> audio file (cached by path)."""
  if not dest.exists():
    body = {"composition_plan": plan, "model_id": model_id}
    if seed is not None:
      body["seed"] = seed
    for attempt in range(6):
      req = urllib.request.Request(
        f"{API}/v1/music?output_format=mp3_48000_192", method="POST", data=json.dumps(body).encode(),
        headers={"xi-api-key": api_key(), "content-type": "application/json"},
      )
      try:
        with urllib.request.urlopen(req, timeout=600) as r:
          dest.write_bytes(r.read())
        break
      except urllib.error.HTTPError as e:
        if e.code in (429, 503) and attempt < 5:
          time.sleep(3 * (attempt + 1))
          continue
        sys.exit(f"music -> HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")
  return dest


def sts(voice_id: str, audio: Path, dest: Path, model_id: str = "eleven_english_sts_v2", seed: int = 7) -> Path:
  """Voice Changer (speech to speech) -> mp3 (cached by path)."""
  if not dest.exists():
    boundary = "----msf" + os.urandom(8).hex()
    fields = {"model_id": model_id, "seed": str(seed), "remove_background_noise": "false"}
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts.append(
      f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="{audio.name}"\r\n'
      f"Content-Type: application/octet-stream\r\n\r\n".encode() + audio.read_bytes() + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
      f"{API}/v1/speech-to-speech/{voice_id}?output_format=mp3_44100_128",
      method="POST",
      data=b"".join(parts),
      headers={"xi-api-key": api_key(), "content-type": f"multipart/form-data; boundary={boundary}", "accept": "audio/mpeg"},
    )
    try:
      with urllib.request.urlopen(req, timeout=300) as r:
        dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
      sys.exit(f"STS {voice_id} -> HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
  return dest


def clone(name: str, files: list[Path], description: str = "") -> str:
  """Instant voice clone from local audio files -> voice_id."""
  boundary = "----msf" + os.urandom(8).hex()
  fields = {"name": name, "description": description, "remove_background_noise": "false"}
  parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
  for f in files:
    parts.append(
      f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{f.name}"\r\n'
      f"Content-Type: audio/wav\r\n\r\n".encode() + f.read_bytes() + b"\r\n"
    )
  parts.append(f"--{boundary}--\r\n".encode())
  req = urllib.request.Request(
    f"{API}/v1/voices/add", method="POST", data=b"".join(parts),
    headers={"xi-api-key": api_key(), "content-type": f"multipart/form-data; boundary={boundary}", "accept": "application/json"},
  )
  try:
    with urllib.request.urlopen(req, timeout=300) as r:
      return json.loads(r.read())["voice_id"]
  except urllib.error.HTTPError as e:
    sys.exit(f"clone -> HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")


def download(url: str, dest: Path) -> None:
  if not dest.exists():
    with urllib.request.urlopen(url, timeout=60) as r:
      dest.write_bytes(r.read())


def account() -> None:
  s = call("GET", "/v1/user/subscription")
  used, limit = s.get("character_count", 0), s.get("character_limit", 0)
  print(f"tier: {s.get('tier')}  characters: {used:,} / {limit:,} used ({limit - used:,} left)")
  print(f"voice slots: {s.get('voice_slots_used', '?')} / {s.get('voice_limit', '?')}  resets: {s.get('next_character_count_reset_unix')}")


def voices() -> None:
  out = OUT / "stock"
  out.mkdir(parents=True, exist_ok=True)
  data = call("GET", "/v1/voices")["voices"]
  stock = []
  for v in data:
    if v.get("category") != "premade":
      continue
    labels = v.get("labels") or {}
    row = {
      "voice_id": v["voice_id"],
      "name": v["name"],
      "gender": labels.get("gender"),
      "age": labels.get("age"),
      "accent": labels.get("accent"),
      "description": labels.get("description") or labels.get("descriptive"),
      "use_case": labels.get("use_case") or labels.get("use case"),
    }
    stock.append(row)
    if v.get("preview_url"):
      download(v["preview_url"], out / f"{v['name'].split()[0].lower()}-{v['voice_id'][:6]}.mp3")
  stock.sort(key=lambda r: (r["gender"] or "", r["age"] or "", r["name"]))
  (OUT / "stock.json").write_text(json.dumps(stock, indent=2) + "\n")
  for r in stock:
    print(f"{r['name'][:22]:22} {r['gender'] or '-':7} {r['age'] or '-':12} {r['accent'] or '-':14} {r['description'] or '-':18} {r['use_case'] or '-'}")


def design(name: str, spec_path: str) -> None:
  spec = json.loads(Path(spec_path).read_text())
  out = OUT / "design" / name
  out.mkdir(parents=True, exist_ok=True)
  res = call("POST", "/v1/text-to-voice/design?output_format=mp3_44100_128", spec)
  meta = {"spec": spec, "text": res.get("text"), "previews": []}
  for i, p in enumerate(res["previews"], 1):
    f = out / f"preview-{i}.mp3"
    f.write_bytes(base64.b64decode(p["audio_base_64"]))
    meta["previews"].append({"file": f.name, "generated_voice_id": p["generated_voice_id"], "duration_secs": p.get("duration_secs")})
    print(f"{f.relative_to(ROOT)}  {p.get('duration_secs', 0):.1f}s")
  (out / "previews.json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
  cmd = sys.argv[1] if len(sys.argv) > 1 else ""
  if cmd == "account":
    account()
  elif cmd == "voices":
    voices()
  elif cmd == "design" and len(sys.argv) == 4:
    design(sys.argv[2], sys.argv[3])
  else:
    sys.exit(__doc__)
