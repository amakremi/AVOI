"""Stage-2 AIT-LDS acquisition by HTTP range requests (official Zenodo archive, no mirror).

Downloading full 16-17 GB archives was bandwidth-prohibitive; nearly all of their volume is pcaps / Suricata eve.json /
binary journals that the pipeline never uses. This tool reads the ZIP central directory of the OFFICIAL archive
remotely and copies only the members the importer uses (dataset.yaml, labels/*, and gather/* files of the evidence
source families defined in src/avoi/datasets/ait.py) into a local subset ZIP with identical member paths.

Integrity: every copied member is decompressed and checked against the CRC-32 stored in the official central directory
(zipfile raises on mismatch). The published whole-archive MD5 cannot be verified for a partial copy; the SHA-256 of the
subset ZIP, the list of copied members and their CRC-32 values are recorded in data/manifests/ait_stage2_subsets.json.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from avoi.datasets.ait import classify  # noqa: E402

URL = "https://zenodo.org/records/5789064/files/{tb}.zip?download=1"


class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url: str, block: int = 8 << 20):
        self.url, self.block, self.pos = url, block, 0
        self.s = requests.Session()
        r = self.s.head(url, allow_redirects=True, timeout=60)
        self.url = r.url
        self.size = int(r.headers["Content-Length"])
        self.cache: dict[int, bytes] = {}
        self.bytes_fetched = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def _block(self, k: int) -> bytes:
        if k not in self.cache:
            a = k * self.block
            b = min(self.size, a + self.block) - 1
            for attempt in range(10):
                try:
                    r = self.s.get(self.url, headers={"Range": f"bytes={a}-{b}"}, timeout=120)
                    if r.status_code == 206 and len(r.content) == b - a + 1:
                        break
                except requests.RequestException:
                    pass
                time.sleep(5 * (attempt + 1))
            else:
                raise IOError(f"range fetch failed {a}-{b}")
            if len(self.cache) > 64:
                self.cache.pop(next(iter(self.cache)))
            self.cache[k] = r.content
            self.bytes_fetched += len(r.content)
        return self.cache[k]

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        out = bytearray()
        while n > 0 and self.pos < self.size:
            k, off = divmod(self.pos, self.block)
            chunk = self._block(k)[off: off + n]
            out += chunk
            self.pos += len(chunk)
            n -= len(chunk)
        return bytes(out)

    def readinto(self, b):
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)


def subset(tb: str) -> dict:
    remote = HTTPRangeFile(URL.format(tb=tb))
    src = zipfile.ZipFile(io.BufferedReader(remote, buffer_size=1 << 20))
    dest = ROOT / "data" / "raw" / "ait" / f"{tb}_subset.zip"
    members = []
    t = time.time()
    labelled = {i.filename[len("labels/"):] for i in src.infolist() if i.filename.startswith("labels/") and not i.is_dir()}
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for info in src.infolist():
            f = info.filename
            want = (f == "dataset.yaml") or (f.startswith("labels/") and not info.is_dir()) or \
                   (not info.is_dir() and (classify(f) is not None or (f.startswith("gather/") and f[len("gather/"):] in labelled)))
            if not want:
                continue
            data = src.read(f)                      # CRC-32 verified by zipfile against the official central directory
            out.writestr(f, data)
            members.append({"path": f, "size": info.file_size, "crc32": f"{info.CRC:08x}"})
    h = hashlib.sha256(dest.read_bytes()).hexdigest()
    return {"testbed": tb, "source_url": URL.format(tb=tb), "official_archive_bytes": remote.size, "bytes_fetched": remote.bytes_fetched,
            "n_members": len(members), "subset_zip": dest.relative_to(ROOT).as_posix(), "subset_sha256": h,
            "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "seconds": round(time.time() - t),
            "members": members}


if __name__ == "__main__":
    args = sys.argv[1:]
    man_name = "ait_stage2_subsets.json"
    if args and args[0].startswith("--manifest="):          # Stage 3: separate manifest for untouched testbeds
        man_name, args = args[0].split("=", 1)[1], args[1:]
    man_path = ROOT / "data" / "manifests" / man_name
    man = json.loads(man_path.read_text()) if man_path.exists() else {}
    for tb in args or ["fox", "harrison", "wardbeck"]:
        if tb in man:
            print("present", tb)
            continue
        rec = subset(tb)
        man[tb] = rec
        man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
        print(tb, rec["n_members"], "members", round(rec["bytes_fetched"] / 1e6), "MB fetched", rec["seconds"], "s", flush=True)
