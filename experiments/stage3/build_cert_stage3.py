"""Stage 3: sequentially extract, build, and clean up the four untouched CERT releases (r4.1, r5.1, r6.1, r6.2).

Extracts one release at a time (bz2 decompression is disk-hungry and single-threaded); deletes the raw extracted
directory immediately after the evidence store is built to bound peak disk usage. Reuses avoi.datasets.cert.configure
and .build unchanged. Verifies the official published MD5 before extracting.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

RAW = ROOT / "data" / "raw" / "cert"
RELEASES = {
    "r4.1": "d2fbed1684dd09a6e44072bf05248912",
    "r5.1": "26b6bda75ffd50c0e8adf3e30fe18746",
    "r6.1": "e52c8e4134624bb8cbb6ee773a592044",
    "r6.2": "2f99ec7dfa3e17a29691cbf80c8a662b",
}
SEED = 20270404   # config/stage3.yaml wp2.cert.episode_sampling


def md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def main():
    from avoi.datasets import cert
    for rel, expected_md5 in RELEASES.items():
        out_dir = ROOT / "data" / "processed" / f"cert_stage3_{rel.replace('.', '_')}"
        if (out_dir / "evidence_store.json").exists():
            print(rel, "store already built, skipping", flush=True)
            continue
        archive = RAW / f"{rel}.tar.bz2"
        extracted = RAW / f"{rel}_extracted"
        t0 = time.time()
        if not extracted.exists():
            print(rel, "verifying MD5...", flush=True)
            actual = md5(archive)
            if actual != expected_md5:
                raise SystemExit(f"{rel}: MD5 mismatch, expected {expected_md5} got {actual}")
            print(rel, "MD5 verified, extracting...", flush=True)
            extracted.mkdir(parents=True, exist_ok=True)
            subprocess.run(["tar", "-xjf", str(archive), "-C", str(extracted)], check=True)
            print(rel, "extracted in", round(time.time() - t0), "s", flush=True)
        cert.configure(release=rel, out_dir=str(out_dir.relative_to(ROOT)).replace("\\", "/"), seed=SEED)
        t1 = time.time()
        cert.build()
        print(rel, "store built in", round(time.time() - t1), "s ->", out_dir, flush=True)
        shutil.rmtree(extracted, ignore_errors=True)
        print(rel, "raw extracted directory removed (evidence store retained)", flush=True)
    print("all CERT Stage-3 releases processed", flush=True)


if __name__ == "__main__":
    main()
