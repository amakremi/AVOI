"""Download authoritative datasets listed in data/manifests/dataset_sources.json.

- resumable HTTP downloads (Range requests)
- verifies the source-published checksum when available
- computes SHA-256 of every file
- writes data/DATASET_MANIFEST.json and data/DATASET_MANIFEST.csv
- never bypasses authentication/forms: entries marked 'blocked' are recorded only

Usage:
    python data/download_datasets.py [--only id1,id2] [--skip-large]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
SOURCES = DATA_DIR / "manifests" / "dataset_sources.json"
MANIFEST_JSON = DATA_DIR / "DATASET_MANIFEST.json"
MANIFEST_CSV = DATA_DIR / "DATASET_MANIFEST.csv"
LARGE_BYTES = 1_000_000_000
UA = {"User-Agent": "AVOI-GRC-research-downloader/1.0 (academic reproducibility)"}


def file_hashes(path: Path) -> dict[str, str]:
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 << 20), b""):
            sha.update(chunk)
            md5.update(chunk)
    return {"sha256": sha.hexdigest(), "md5": md5.hexdigest()}


def download(url: str, dest: Path, retries: int = 8) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        have = part.stat().st_size if part.exists() else 0
        headers = dict(UA)
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60, allow_redirects=True) as r:
                if r.status_code == 416:  # already complete
                    break
                r.raise_for_status()
                mode = "ab" if (have and r.status_code == 206) else "wb"
                total = r.headers.get("Content-Length")
                total = int(total) + (have if mode == "ab" else 0) if total else None
                done = have if mode == "ab" else 0
                last = time.time()
                with part.open(mode) as fh:
                    for chunk in r.iter_content(chunk_size=4 << 20):
                        fh.write(chunk)
                        done += len(chunk)
                        if time.time() - last > 30:
                            pct = f"{100 * done / total:.1f}%" if total else "?"
                            print(f"    {dest.name}: {done / 1e6:.0f} MB ({pct})", flush=True)
                            last = time.time()
                if total is None or done >= total:
                    break
        except (requests.RequestException, OSError) as exc:
            print(f"    attempt {attempt + 1} failed: {exc}", flush=True)
            time.sleep(min(60, 5 * (attempt + 1)))
    else:
        raise RuntimeError(f"download failed after {retries} attempts: {url}")
    part.replace(dest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated source ids")
    ap.add_argument("--skip-large", action="store_true")
    args = ap.parse_args()
    only = {s for s in args.only.split(",") if s}

    registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    previous = {}
    if MANIFEST_JSON.exists():
        previous = {e["id"]: e for e in json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))["entries"]}

    entries = []
    for src in registry["sources"]:
        sid = src["id"]
        if only and sid not in only:
            if sid in previous:
                entries.append(previous[sid])
            continue
        entry = {k: src.get(k) for k in ("id", "dataset", "version", "organization", "source_page", "url",
                                         "doi", "license", "published_checksum", "role")}
        entry["retrieval_date"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        if src.get("blocked"):
            entry.update(status="blocked", blocker=src["blocked"], local_path=None, size_bytes=None, sha256=None,
                         checksum_verified=None)
            print(f"[BLOCKED] {sid}: {src['blocked']}")
            entries.append(entry)
            continue
        dest = RAW_DIR / src["filename"]
        try:
            if not dest.exists():
                if args.skip_large:
                    head = requests.head(src["url"], headers=UA, allow_redirects=True, timeout=60)
                    if int(head.headers.get("Content-Length", 0)) > LARGE_BYTES:
                        entry.update(status="skipped_large", local_path=None, size_bytes=None, sha256=None,
                                      checksum_verified=None)
                        entries.append(entry)
                        continue
                print(f"[DOWNLOAD] {sid} <- {src['url']}", flush=True)
                download(src["url"], dest)
            else:
                print(f"[PRESENT] {sid}", flush=True)
            if sid in previous and previous[sid].get("size_bytes") == dest.stat().st_size and previous[sid].get("sha256"):
                hashes = {"sha256": previous[sid]["sha256"], "md5": previous[sid].get("md5")}
                entry["retrieval_date"] = previous[sid]["retrieval_date"]
            else:
                hashes = file_hashes(dest)
            verified = None
            if src.get("published_checksum"):
                algo, value = src["published_checksum"].split(":", 1)
                verified = hashes.get(algo) == value.lower()
            # content-type sanity (e.g. HTML error page instead of CSV)
            with dest.open("rb") as fh:
                looks_html = fh.read(512).lstrip().lower().startswith((b"<!doctype html", b"<html"))
            entry.update(status="downloaded" if not looks_html else "error_html_payload",
                         local_path=dest.relative_to(DATA_DIR.parent).as_posix(),
                         size_bytes=dest.stat().st_size, sha256=hashes["sha256"], md5=hashes.get("md5"),
                         checksum_verified=verified)
            flag = {True: "checksum OK", False: "CHECKSUM MISMATCH", None: "no published checksum"}[verified]
            print(f"    {dest.stat().st_size} bytes sha256={hashes['sha256'][:16]}... {flag}", flush=True)
        except Exception as exc:  # record and continue with other datasets
            entry.update(status="failed", blocker=repr(exc), local_path=None, size_bytes=None, sha256=None,
                         checksum_verified=None)
            print(f"[FAILED] {sid}: {exc}", flush=True)
        entries.append(entry)

    manifest = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "selection_rationale": registry.get("selection_rationale"), "entries": entries}
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    cols = ["id", "dataset", "version", "organization", "source_page", "url", "doi", "license", "retrieval_date",
            "status", "local_path", "size_bytes", "sha256", "md5", "published_checksum", "checksum_verified", "blocker"]
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for e in entries:
            w.writerow(e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
