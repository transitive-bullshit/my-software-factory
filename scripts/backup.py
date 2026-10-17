"""Back up the paid generated clips the final cuts are built from to R2, and restore them on a fresh clone.

Only the approved clip each shot of a backed-up cut actually uses (scripts/full.py sources) is kept: content-addressed
(<sha256>.mp4) under my-software-factory/ in the S3_BUCKET_NAME bucket, served from S3_PUBLIC_URL. The manifest,
data/backup.json, is committed: it maps each local path to its URL, size and hash, so restoring needs no keys.

Only the fully generative cut is backed up. The lip sync cut's clips are the film's own footage, which stays off
public hosting, like everything copyrighted in this project.

  uv run --group analysis --group voice --group gen python scripts/backup.py upload --env <file with S3_* keys>
  uv run python scripts/backup.py restore        # download any backed-up clip missing locally, checking its hash
"""

import datetime
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "backup.json"
PREFIX = "my-software-factory"
CUTS = ("generative",)
UA = {"user-agent": "my-software-factory-backup/1.0"}  # the CDN turns away Python's default user agent


def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def load_env(path: str) -> None:
  for line in Path(path).expanduser().read_text().splitlines():
    name, sep, value = line.strip().removeprefix("export ").partition("=")
    if sep and name.startswith("S3_"):
      os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def env(name: str) -> str:
  value = os.environ.get(name, "").strip()
  if not value:
    sys.exit(f"{name} is not set (pass --env <file>)")
  return value


def put(key: str, path: Path, digest: str) -> None:
  """S3 PUT signed with AWS Signature V4 (R2 speaks S3), stdlib only."""
  endpoint, bucket = env("S3_API_ENDPOINT").rstrip("/"), env("S3_BUCKET_NAME")
  region = os.environ.get("S3_REGION", "").strip() or "auto"
  now = datetime.datetime.now(datetime.UTC)
  stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
  url_path = f"/{bucket}/{quote(key)}"
  headers = {
    "cache-control": "public, max-age=31536000, immutable",  # content-addressed: a key never changes
    "content-type": "video/mp4",
    "host": urlparse(endpoint).netloc,
    "x-amz-content-sha256": digest,
    "x-amz-date": stamp,
  }
  signed = ";".join(sorted(headers))
  canonical = "\n".join(["PUT", url_path, "", *(f"{k}:{headers[k]}" for k in sorted(headers)), "", signed, digest])
  scope = f"{day}/{region}/s3/aws4_request"
  to_sign = "\n".join(["AWS4-HMAC-SHA256", stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
  k = f"AWS4{env('S3_SECRET_ACCESS_KEY')}".encode()
  for part in (day, region, "s3", "aws4_request"):
    k = hmac.new(k, part.encode(), hashlib.sha256).digest()
  signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
  headers["authorization"] = (f"AWS4-HMAC-SHA256 Credential={env('S3_ACCESS_KEY_ID')}/{scope}, "
                              f"SignedHeaders={signed}, Signature={signature}")
  req = urllib.request.Request(endpoint + url_path, data=path.read_bytes(), method="PUT", headers=headers)
  with urllib.request.urlopen(req, timeout=300) as res:
    if res.status != 200:
      sys.exit(f"{key}: upload failed ({res.status})")


def public_size(url: str, tries: int = 1) -> int | None:
  """Size of the public copy, or None; the query keeps a cached 404 from before the upload out of the answer."""
  for attempt in range(tries):
    try:
      req = urllib.request.Request(f"{url}?check={time.time_ns()}", method="HEAD", headers=UA)
      with urllib.request.urlopen(req, timeout=60) as res:
        return int(res.headers.get("content-length", -1))
    except urllib.error.HTTPError:
      time.sleep(2 * (attempt + 1))
  return None


def upload() -> None:
  sys.path.insert(0, str(ROOT / "scripts"))
  import full

  base = env("S3_PUBLIC_URL").rstrip("/")
  manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
  for cut in CUTS:
    for shot, path in full.sources(cut).items():
      rel = path.relative_to(ROOT).as_posix()
      digest, size = sha256(path), path.stat().st_size
      url = f"{base}/{PREFIX}/{digest}{path.suffix}"
      if public_size(url) != size:
        put(f"{PREFIX}/{digest}{path.suffix}", path, digest)
        if public_size(url, tries=4) != size:
          sys.exit(f"{url}: the public copy doesn't match the {size} bytes uploaded")
        print(f"uploaded {rel} -> {url}")
      else:
        print(f"already there: {rel}")
      manifest[rel] = {"cut": cut, "shot": shot, "url": url, "bytes": size, "sha256": digest}
  MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=1) + "\n")
  print(f"{len(manifest)} clips in {MANIFEST.relative_to(ROOT)}")


def restore() -> None:
  for rel, entry in json.loads(MANIFEST.read_text()).items():
    dest = ROOT / rel
    if dest.exists() and dest.stat().st_size == entry["bytes"]:
      continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")  # written aside, so an interrupted run never leaves a partial clip
    with urllib.request.urlopen(urllib.request.Request(entry["url"], headers=UA), timeout=300) as res:
      part.write_bytes(res.read())
    if sha256(part) != entry["sha256"]:
      part.unlink()
      sys.exit(f"{rel}: download doesn't match its hash")
    part.rename(dest)
    print(f"restored {rel}")


if __name__ == "__main__":
  args = sys.argv[1:]
  if "--env" in args:
    load_env(args[args.index("--env") + 1])
  {"upload": upload, "restore": restore}[args[0] if args else "restore"]()
