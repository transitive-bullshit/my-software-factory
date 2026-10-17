"""Run one fal endpoint: upload local inputs, wait for the result, save outputs, log the call.

    uv run --group gen python scripts/fal_run.py ENDPOINT JOB.json OUT_PREFIX [--est-cost USD]

Or from Python: fal_run.run(endpoint, args, out_prefix, est_cost).

String values in JOB.json that start with "@" are project-relative paths, uploaded to fal
storage first. Every file in the result is saved next to OUT_PREFIX, the raw result goes to
OUT_PREFIX.json, and each call is appended to data/fal-log.jsonl.
"""

import argparse
import json
import re
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "fal-log.jsonl"


def load_key():
    if os.environ.get("FAL_KEY"):
        return
    env = Path.home() / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("FAL_KEY="):
            os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip("\"'")
            return
    sys.exit("FAL_KEY not found in the environment or ~/.env")


def upload_inputs(value, fal_client):
    if isinstance(value, str) and value.startswith("@"):
        return fal_client.upload_file(str(ROOT / value[1:]))
    if isinstance(value, list):
        return [upload_inputs(v, fal_client) for v in value]
    if isinstance(value, dict):
        return {k: upload_inputs(v, fal_client) for k, v in value.items()}
    return value


def find_files(value, path=""):
    if isinstance(value, dict):
        if isinstance(value.get("url"), str) and value["url"].startswith("http"):
            yield path, value
            return
        for k, v in value.items():
            yield from find_files(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from find_files(v, f"{path}[{i}]")


def run(endpoint: str, args: dict, out: Path, est_cost: float | None = None, job: str = "") -> list[str]:
    """Submit one request (uploading "@path" inputs), wait, save every output file next to `out`, log the call.
    Cached: if out.json already exists, return the files saved last time."""
    out = out.resolve()
    meta = out.with_suffix(".json")
    if meta.exists():
        own = re.compile(re.escape(out.name) + r"(-\d+)?")
        return [str(p.relative_to(ROOT)) for p in sorted(out.parent.glob(out.name + "*"))
                if p.suffix != ".json" and own.fullmatch(p.stem)]
    load_key()
    import fal_client

    started = time.time()
    handle = fal_client.submit(endpoint, arguments=upload_inputs(args, fal_client))
    print(f"submitted {endpoint} request_id={handle.request_id}", flush=True)
    result = handle.get()
    elapsed = round(time.time() - started, 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, (key, f) in enumerate(find_files(result)):
        ext = Path(f.get("file_name") or f["url"].split("?")[0]).suffix or ".bin"
        dest = out.with_name(out.name + ("" if i == 0 else f"-{i}") + ext)
        with urllib.request.urlopen(f["url"], timeout=120) as r:  # a stalled download fails instead of hanging
            dest.write_bytes(r.read())
        saved.append(str(dest.relative_to(ROOT)))
        print(f"saved {key} -> {dest.relative_to(ROOT)}", flush=True)
    meta.write_text(json.dumps(result, indent=2))  # the cache marker: only once every output is on disk
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as log:
        log.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "endpoint": endpoint, "request_id": handle.request_id,
                              "job": job, "args": args, "outputs": saved, "elapsed_s": elapsed, "est_cost_usd": est_cost}) + "\n")
    print(f"done in {elapsed}s", flush=True)
    return saved


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("endpoint")
    p.add_argument("job", type=Path)
    p.add_argument("out", type=Path, help="output path prefix, without extension")
    p.add_argument("--est-cost", type=float, help="estimated USD, recorded in the log")
    a = p.parse_args()
    a.out = a.out.resolve()

    load_key()
    import fal_client

    raw = json.loads(a.job.read_text())
    args = upload_inputs(raw, fal_client)

    started = time.time()
    handle = fal_client.submit(a.endpoint, arguments=args)
    print(f"submitted {a.endpoint} request_id={handle.request_id}", flush=True)
    result = handle.get()
    elapsed = round(time.time() - started, 1)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix(".json").write_text(json.dumps(result, indent=2))
    saved = []
    for i, (key, f) in enumerate(find_files(result)):
        ext = Path(f.get("file_name") or f["url"].split("?")[0]).suffix or ".bin"
        dest = a.out.with_name(a.out.name + ("" if i == 0 else f"-{i}") + ext)
        urllib.request.urlretrieve(f["url"], dest)
        saved.append(str(dest.relative_to(ROOT)))
        print(f"saved {key} -> {dest.relative_to(ROOT)}", flush=True)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as log:
        log.write(json.dumps({
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "endpoint": a.endpoint,
            "request_id": handle.request_id,
            "job": str(a.job),
            "args": raw,
            "outputs": saved,
            "elapsed_s": elapsed,
            "est_cost_usd": a.est_cost,
        }) + "\n")
    print(f"done in {elapsed}s", flush=True)


if __name__ == "__main__":
    main()
