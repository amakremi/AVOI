"""AIT-LDS v2.0 replay episodes: window-level assurance micro-claims.

Unit: 10-minute window W of a testbed. Micro-claims (defined from label TYPES before any acquisition method was run;
see docs/DATASETS.md):
  AIT-EXFIL      "no labelled DNS-exfiltration activity (dnsteal / exfiltration-service labels) is present in W"
  AIT-INTRUSION  "no labelled multi-step intrusion activity (all other AIT attack-step labels) is present in W"
Y = 1 claim holds (no such labelled activity), Y = 0 claim refuted. These are NOT compliance labels.

Evidence actions = querying one evidence-source family for W in the label-free SQLite evidence index. The statistic
returned by each query is a generic, label-free count/level (see STAT_SQL). Wall-clock query time, rows and bytes
are measured at build time and stored as the acquisition cost of that action for that episode.
"""
from __future__ import annotations

import csv
import json
import sqlite3
import time
from pathlib import Path

import numpy as np

from avoi.actions import ActionSpec
from avoi.datasets.ait import FAMILIES, OUT, TESTBEDS
from avoi.datasets.common import NUMERIC_OUTCOMES, ObjectiveData

WINDOW_S = 600
SOURCE_TYPE = {"vpn": "authentication_log", "dns": "network_observation", "web_access": "network_observation",
               "web_error": "system_log", "auth": "authentication_log", "audit": "audit_log", "ids": "network_observation",
               "mail": "communication_record", "syslog": "system_log", "monitoring": "host_state"}
STAT_SQL = {  # label-free statistic per source family
    "vpn": "SUM(f1)", "dns": "SUM(f1)", "web_access": "SUM(f1)", "web_error": "COUNT(*)", "auth": "SUM(f1) + SUM(f2)",
    "audit": "SUM(f1) + SUM(f2)", "ids": "SUM(f1)", "mail": "COUNT(*)", "syslog": "COUNT(*)", "monitoring": "MAX(f1)",
}
EXFIL_LABELS = {"dnsteal", "dnsteal-received", "dnsteal-dropped", "exfiltration-service"}
GENERIC_LABELS = {"attacker"}
CLAIMS = ("AIT-EXFIL", "AIT-INTRUSION")
FAM_ORDER = list(FAMILIES)  # checklist order


def build() -> None:
    (OUT / "ground_truth").mkdir(parents=True, exist_ok=True)
    rows_ev, rows_lab = [], []
    for tb in TESTBEDS:
        meta = json.loads((OUT / f"{tb}_index_meta.json").read_text(encoding="utf-8"))
        con = sqlite3.connect(OUT / f"{tb}_evidence.sqlite")
        windows = list(range(meta["start"], meta["end"], WINDOW_S))
        for w0 in windows:
            rec = {"testbed": tb, "w0": w0}
            for fam in FAM_ORDER:
                t = time.perf_counter()
                cnt, nbytes, stat = con.execute(
                    f"SELECT COUNT(*), COALESCE(SUM(nbytes),0), {STAT_SQL[fam]} FROM {fam} WHERE ts >= ? AND ts < ?",
                    (w0, w0 + WINDOW_S)).fetchone()
                rec[fam] = {"stat": (float(stat) if cnt else None), "rows": int(cnt), "bytes": int(nbytes),
                            "seconds": time.perf_counter() - t}
            rows_ev.append(rec)
        con.close()
        # ground truth (restricted): window -> claim labels
        exfil, intr = set(), set()
        with (OUT / "ground_truth" / f"{tb}_labeled_lines.csv").open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if not r["ts"]:
                    continue
                w = meta["start"] + (int(r["ts"]) - meta["start"]) // WINDOW_S * WINDOW_S
                labs = set(r["labels"].split("|"))
                if labs & EXFIL_LABELS:
                    exfil.add(w)
                if labs - EXFIL_LABELS - GENERIC_LABELS:
                    intr.add(w)
        for w0 in windows:
            rows_lab.append((f"ait|{tb}|{w0}|AIT-EXFIL", int(w0 not in exfil)))
            rows_lab.append((f"ait|{tb}|{w0}|AIT-INTRUSION", int(w0 not in intr)))
    (OUT / "evidence_store.json").write_text(json.dumps(rows_ev), encoding="utf-8")
    with (OUT / "ground_truth" / "episode_labels.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["episode_id", "y"])
        w.writerows(rows_lab)


def load_ait() -> dict[str, ObjectiveData]:
    recs = json.loads((OUT / "evidence_store.json").read_text(encoding="utf-8"))
    out = {}
    for claim in CLAIMS:
        specs = [ActionSpec(f"ait_query_{fam}", claim, SOURCE_TYPE[fam], NUMERIC_OUTCOMES, (0, 1, 0, -1),
                            tuple(FAMILIES[fam][1])) for fam in FAM_ORDER]
        n, m = len(recs), len(FAM_ORDER)
        vals, sec, rows, byt = np.full((n, m), np.nan), np.zeros((n, m)), np.zeros((n, m)), np.zeros((n, m))
        priv, prov = [], []
        for i, r in enumerate(recs):
            prow, vrow = [], []
            for j, fam in enumerate(FAM_ORDER):
                e = r[fam]
                if e["stat"] is not None:
                    vals[i, j] = e["stat"]
                sec[i, j], rows[i, j], byt[i, j] = e["seconds"], e["rows"], e["bytes"]
                prow.append(list(FAMILIES[fam][1]) if e["rows"] > 0 else [])
                vrow.append({"scope": f"{r['testbed']}:[{r['w0']},{r['w0'] + WINDOW_S})", "parser": f"ait-index/1.0:{fam}",
                             "raw_artifact_ref": f"data/processed/ait/{r['testbed']}_evidence.sqlite#{fam}",
                             "timestamp_utc": r["w0"]})
            priv.append(prow)
            prov.append(vrow)
        ids = np.array([f"ait|{r['testbed']}|{r['w0']}|{claim}" for r in recs])
        tbs = np.array([r["testbed"] for r in recs])
        out[claim] = ObjectiveData("ait", claim, specs, ids, tbs, {"testbed": tbs, "w0": np.array([r["w0"] for r in recs])},
                                   "numeric", vals, sec, rows, byt, priv, prov, "AIT-LDS-v2.0")
    return out


if __name__ == "__main__":
    build()
    for k, d in load_ait().items():
        print(k, d.n, d.m)
