"""Pre-freeze readiness check: verifies every Stage-3 data source exists and loads before the official freeze."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "stage3"))


def check():
    ok = True

    def report(name, cond, detail=""):
        nonlocal ok
        print(("OK  " if cond else "FAIL"), name, detail)
        ok = ok and cond

    for d, n in [("iam_stage3_dev", 512), ("iam_stage3_val", 256), ("iam_stage3_conf", 256)]:
        p = ROOT / "data" / "processed" / d / "ground_truth"
        n_have = len(list(p.glob("*.json"))) if p.exists() else 0
        report(f"IAM {d}", n_have >= n, f"{n_have}/{n}")

    from avoi.evaluation import stage3 as S3M
    parts = S3M.iam_partitions(include_confirmation=True)
    for oid, p in parts.items():
        report(f"iam_partitions[{oid}]", "val" in p and "conf" in p and p["dev"][0].n > 900,
              f"dev={p['dev'][0].n} val={p['val'][0].n if 'val' in p else '?'} conf={p['conf'][0].n if 'conf' in p else '?'}")

    for tb in ("shaw", "wheeler", "wilson"):
        p = ROOT / "data" / "processed" / "ait" / f"{tb}_evidence.sqlite"
        report(f"AIT {tb} index", p.exists(), str(p))
    report("AIT stage3 episode store", (ROOT / "data" / "processed" / "ait_stage3" / "evidence_store.json").exists())

    for rel, d in [("r4.1", "cert_stage3_r4_1"), ("r5.1", "cert_stage3_r5_1")]:
        p = ROOT / "data" / "processed" / d / "evidence_store.json"
        report(f"CERT {rel} store", p.exists())

    print()
    print("READY FOR OFFICIAL FREEZE" if ok else "NOT READY")
    return ok


if __name__ == "__main__":
    sys.exit(0 if check() else 1)
