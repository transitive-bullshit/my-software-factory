"""Small Fish Audio client. Reads FISH_AUDIO_API_KEY (or FISH_API_KEY) from the environment or ~/.env; never
prints it. API usage is billed separately from the web app subscription.

  python3 scripts/fish.py tts MODEL_ID "text" out.mp3 [drama-3]
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.fish.audio"
NAMES = ("FISH_AUDIO_API_KEY", "FISH_API_KEY")


def api_key() -> str:
  for name in NAMES:
    if os.environ.get(name):
      return os.environ[name]
  env = Path.home() / ".env"
  if env.exists():
    for line in env.read_text().splitlines():
      k, _, v = line.partition("=")
      if k.strip().removeprefix("export ").strip() in NAMES and v.strip():
        return v.strip().strip("'\"")
  sys.exit("FISH_AUDIO_API_KEY not found in the environment or ~/.env")


def tts(reference_id: str, text: str, dest: Path, model: str = "drama-3") -> Path:
  if not dest.exists():
    req = urllib.request.Request(
      f"{API}/v1/tts", method="POST",
      data=json.dumps({"text": text, "reference_id": reference_id, "format": "mp3", "mp3_bitrate": 192}).encode(),
      headers={"authorization": f"Bearer {api_key()}", "content-type": "application/json", "model": model},
    )
    try:
      with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
      sys.exit(f"fish tts -> HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")
  return dest


if __name__ == "__main__":
  if len(sys.argv) >= 5 and sys.argv[1] == "tts":
    print(tts(sys.argv[2], sys.argv[3], Path(sys.argv[4]), *(sys.argv[5:6] or [])))
  else:
    sys.exit(__doc__)
