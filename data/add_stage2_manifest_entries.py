"""Adds the Stage-2 AIT-LDS v2.0 range-request subsets to data/DATASET_MANIFEST.{json,csv} (idempotent)."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "data" / "DATASET_MANIFEST.json"


def md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    man = json.loads(MAN.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in json.loads((ROOT / "data" / "manifests" / "dataset_sources.json").read_text(encoding="utf-8"))["sources"]}
    subsets = json.loads((ROOT / "data" / "manifests" / "ait_stage2_subsets.json").read_text(encoding="utf-8"))
    ids = {e["id"] for e in man["entries"]}
    for tb, s in subsets.items():
        eid = f"ait_lds_v2_{tb}"
        if eid in ids:
            continue
        src = sources[eid]
        p = ROOT / s["subset_zip"]
        man["entries"].append({
            "id": eid, "dataset": src.get("dataset"), "version": src.get("version"), "organization": src.get("organization"),
            "source_page": src.get("source_page"), "url": s["source_url"], "doi": src.get("doi"), "license": src.get("license"),
            "published_checksum": src.get("published_checksum"),
            "role": "Stage-2 adequacy validation (fox) / confirmation (harrison, wardbeck); replay evidence + official labels",
            "retrieval_date": s["retrieved_utc"], "status": "partial_subset_downloaded", "local_path": s["subset_zip"],
            "size_bytes": p.stat().st_size, "sha256": s["subset_sha256"], "md5": md5(p), "checksum_verified": False,
            "blocker": (f"Official whole-archive MD5 not verifiable for a partial copy: {s['n_members']} members "
                        f"({s['bytes_fetched']} of {s['official_archive_bytes']} bytes) fetched by HTTP range requests, "
                        "each member CRC-32-verified against the official ZIP central directory (data/manifests/ait_stage2_subsets.json)."),
        })
    man["selection_rationale"]["ait_stage2"] = ("Stage 2: the three smallest unused AIT-LDS v2.0 testbeds by archive size (fox, harrison, wardbeck); "
                                                "smallest -> adequacy validation. Selected by size only.")
    man["selection_rationale"]["cert_stage2"] = ("Stage 2: r5.2, the only other CERT release with multiple instances per scenario in the "
                                                 "official answer key; used only for validation/confirmation.")
    MAN.write_text(json.dumps(man, indent=1), encoding="utf-8")
    cols = ["id", "dataset", "version", "organization", "source_page", "url", "doi", "license", "retrieval_date", "status", "local_path",
            "size_bytes", "sha256", "md5", "published_checksum", "checksum_verified", "blocker"]
    with (ROOT / "data" / "DATASET_MANIFEST.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for e in man["entries"]:
            w.writerow(e)
    print(len(man["entries"]), "entries")
