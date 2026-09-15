"""CERT Insider Threat Test Dataset r4.2 importer: user-week assurance micro-claims (replay validation).

Micro-claim CERT-INSIDER: "the activity of user u during week w contains no insider-threat scenario activity
(no answer-key observable events)". Y = 1 claim holds, Y = 0 refuted. NOT a compliance label.

Episode sampling (predefined, seeded, documented in docs/DATASETS.md):
  * all (insider, week) pairs containing >= 1 answer-key observable event            -> label source: answer key
  * 2 random active weeks per insider without observable events
  * 2 random active weeks for each of 250 randomly selected non-insider users
  Only weeks with >= 4 prior weeks (for novelty baselines) are eligible. Active = >= 1 logon event.
Evidence (label-free): per-source SQLite stores with (user, week) index built from the raw CSVs. Each action's
statistic is computed by a timed query of that source for (user, weeks w-4..w).
The answer key is read ONLY by build_labels(); it is never written to the evidence stores.
"""
from __future__ import annotations

import csv
import json
import sqlite3
import tarfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

from avoi.actions import ActionSpec
from avoi.datasets.common import NUMERIC_OUTCOMES, ObjectiveData

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "cert"
SRC = RAW / "r4.2_extracted" / "r4.2"
OUT = ROOT / "data" / "processed" / "cert"
EPOCH = pd.Timestamp("2010-01-04")   # first Monday of the dataset period; week index = floor((date - EPOCH)/7d)
SEED = 20260914
CLAIM = "CERT-INSIDER"
ANSWER_PREFIX = "answers/r4.2-"
RELEASE = "r4.2"


def configure(release: str = "r4.2", out_dir: str | None = None, seed: int | None = None) -> None:
    """Select the CERT release (Stage 1: r4.2 -> data/processed/cert; Stage 2: r5.2 -> data/processed/cert_stage2)."""
    global SRC, OUT, SEED, ANSWER_PREFIX, RELEASE
    RELEASE = release
    SRC = RAW / f"{release}_extracted" / release
    OUT = ROOT / (out_dir or ("data/processed/cert" if release == "r4.2" else "data/processed/cert_stage2"))
    SEED = seed if seed is not None else (20260914 if release == "r4.2" else 20261103)
    ANSWER_PREFIX = f"answers/{release}-"

ACTIONS = [  # (action_id, source table, source_type, privacy categories)
    ("cert_logon_afterhours", "logon", "authentication_log", ["user_identifier", "host_device_identifier", "authentication_event"]),
    ("cert_logon_pc_novelty", "logon", "authentication_log", ["user_identifier", "host_device_identifier", "authentication_event"]),
    ("cert_device_connects", "device", "device_activity", ["user_identifier", "host_device_identifier"]),
    ("cert_file_copies", "file", "file_activity", ["user_identifier", "host_device_identifier", "file_activity"]),
    ("cert_http_volume", "http", "network_observation", ["user_identifier", "host_device_identifier"]),
    ("cert_http_domain_novelty", "http", "network_observation", ["user_identifier", "host_device_identifier"]),
    ("cert_email_external", "email", "communication_record", ["user_identifier", "email_address", "communication_content"]),
    ("cert_email_attachments", "email", "communication_record", ["user_identifier", "email_address", "communication_content"]),
    ("cert_ldap_role_change", "ldap", "hr_record", ["user_identifier", "email_address", "role_group_membership", "hr_employment_record"]),
    ("cert_psychometric_neuroticism", "psychometric", "hr_record", ["user_identifier", "hr_employment_record"]),
]


def week_of(dates: pd.Series) -> np.ndarray:
    return ((dates - EPOCH).dt.days // 7).to_numpy()


# ------------------------------------------------------------------------------------------------ ground truth
def answer_events() -> pd.DataFrame:
    """(user, week) pairs with answer-key observable events for release 4.2. GROUND TRUTH ONLY."""
    rows = []
    with tarfile.open(RAW / "answers.tar.bz2") as t:
        for m in t.getmembers():
            if m.isfile() and m.name.startswith(ANSWER_PREFIX) and m.name.endswith(".csv"):
                for line in t.extractfile(m).read().decode(errors="replace").splitlines():
                    parts = line.split(",")
                    if len(parts) >= 4:
                        rows.append((parts[3], parts[2], m.name.split("/")[1]))
    df = pd.DataFrame(rows, columns=["user", "date", "scenario_dir"])
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y %H:%M:%S")
    df["week"] = week_of(df["date"])
    return df


# ------------------------------------------------------------------------------------------------ sampling
def sample_episodes() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    logon = pd.read_csv(SRC / "logon.csv", usecols=["date", "user", "activity"])
    logon["date"] = pd.to_datetime(logon["date"], format="%m/%d/%Y %H:%M:%S")
    logon["week"] = week_of(logon["date"])
    active = logon[logon["activity"] == "Logon"].groupby("user")["week"].apply(lambda s: sorted(set(s)))
    ans = answer_events()
    insiders = sorted(set(ans["user"]))
    pos = ans.groupby("user")["week"].apply(lambda s: sorted(set(s)))
    eps = []
    for u in insiders:
        for w in pos[u]:
            if w >= 4:
                eps.append((u, int(w), True))
        clean = [w for w in active.get(u, []) if w >= 4 and w not in set(pos[u])]
        for w in rng.choice(clean, size=min(2, len(clean)), replace=False):
            eps.append((u, int(w), True))
    others = sorted(set(active.index) - set(insiders))
    for u in rng.choice(others, size=250, replace=False):
        weeks = [w for w in active[u] if w >= 4]
        for w in rng.choice(weeks, size=min(2, len(weeks)), replace=False):
            eps.append((str(u), int(w), False))
    df = pd.DataFrame(eps, columns=["user", "week", "insider"]).drop_duplicates(["user", "week"]).reset_index(drop=True)
    df["episode_id"] = [f"cert|{u}|{w}|{CLAIM}" for u, w in zip(df["user"], df["week"])]
    return df


# ------------------------------------------------------------------------------------------------ evidence stores
def build_stores(episodes: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db_path = OUT / "cert_evidence.sqlite"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    need = {(u, w) for u, w0 in zip(episodes["user"], episodes["week"]) for w in range(w0 - 4, w0 + 1)}
    users = set(episodes["user"])

    def keep(df):
        df = df[df["user"].isin(users)].copy()
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y %H:%M:%S")
        df["week"] = week_of(df["date"])
        key = pd.MultiIndex.from_arrays([df["user"], df["week"]])
        return df[key.isin(list(need))]

    def store(name, df, cols):
        df = df[["user", "week"] + cols].copy()
        df["nbytes"] = sum(df[c].astype(str).str.len() for c in cols) if len(df) else []
        df.to_sql(name, con, if_exists="append", index=False)

    t = time.time()
    lg = keep(pd.read_csv(SRC / "logon.csv"))
    lg["hour"], lg["dow"] = lg["date"].dt.hour, lg["date"].dt.dayofweek
    store("logon", lg, ["pc", "activity", "hour", "dow"])
    dv = keep(pd.read_csv(SRC / "device.csv"))
    store("device", dv, ["pc", "activity"])
    file_cols = pd.read_csv(SRC / "file.csv", nrows=0).columns
    fcols = ["date", "user", "pc", "filename"] + (["to_removable_media"] if "to_removable_media" in file_cols else [])
    for chunk in pd.read_csv(SRC / "file.csv", usecols=fcols, chunksize=500_000):
        c = keep(chunk)
        if "to_removable_media" in c:   # releases >= r5 log all file activity; r4.2 file.csv = copies to removable media
            c = c[c["to_removable_media"].astype(str).str.lower() == "true"]
        store("file", c, ["pc", "filename"])
    email_cols = pd.read_csv(SRC / "email.csv", nrows=0).columns
    ecols = ["date", "user", "pc", "to", "cc", "bcc", "from", "size", "attachments"] + (["activity"] if "activity" in email_cols else [])
    for chunk in pd.read_csv(SRC / "email.csv", usecols=ecols, chunksize=500_000):
        c = keep(chunk)
        if "activity" in c:   # releases >= r5 also log viewed e-mails; keep sent e-mails as in r4.2
            c = c[c["activity"].astype(str).str.lower() == "send"]
        rcpt = (c["to"].fillna("") + ";" + c["cc"].fillna("") + ";" + c["bcc"].fillna(""))
        c["external"] = rcpt.apply(lambda s: int(any(x and not x.endswith("@dtaa.com") for x in s.split(";"))))
        if not pd.api.types.is_numeric_dtype(c["attachments"]):   # r5+: "name(size);name(size)" replaces attachment_count
            c["attachments"] = c["attachments"].fillna("").astype(str).map(lambda s: sum(1 for x in s.split(";") if x.strip()))
        store("email", c, ["pc", "from", "external", "size", "attachments"])
    print("logon/device/file/email stored", round(time.time() - t), flush=True)
    with (SRC / "http.csv").open(encoding="utf-8", errors="replace") as fh:
        has_header = fh.readline().lower().startswith("id,")
    http_kw = dict(usecols=["date", "user", "pc", "url"], chunksize=2_000_000, on_bad_lines="skip")
    if not has_header:
        http_kw.update(header=None, names=["id", "date", "user", "pc", "url", "content"])
    for k, chunk in enumerate(pd.read_csv(SRC / "http.csv", **http_kw)):
        c = keep(chunk)
        c["domain"] = c["url"].str.extract(r"^(?:https?://)?([^/]+)", expand=False)
        store("http", c, ["pc", "domain"])
        if k % 5 == 0:
            print("http chunk", k, round(time.time() - t), flush=True)
    ldap = []
    for f in sorted((SRC / "LDAP").glob("*.csv")):
        d = pd.read_csv(f)
        d["month"] = f.stem
        ldap.append(d)
    ldap = pd.concat(ldap)
    ldap = ldap[ldap["user_id"].isin(users)].rename(columns={"user_id": "user"})
    ldap["nbytes"] = sum(ldap[c].astype(str).str.len() for c in ldap.columns)
    ldap.to_sql("ldap", con, index=False)
    ps = pd.read_csv(SRC / "psychometric.csv")
    ps = ps[ps["user_id"].isin(users)].rename(columns={"user_id": "user"})
    ps["nbytes"] = sum(ps[c].astype(str).str.len() for c in ps.columns)
    ps.to_sql("psychometric", con, index=False)
    for tbl in ("logon", "device", "file", "email", "http"):
        con.execute(f"CREATE INDEX idx_{tbl} ON {tbl}(user, week)")
    con.execute("CREATE INDEX idx_ldap ON ldap(user, month)")
    con.execute("CREATE INDEX idx_psy ON psychometric(user)")
    con.commit()
    con.close()


def _month_of_week(w: int) -> tuple[str, str]:
    d = EPOCH + pd.Timedelta(days=7 * w)
    prev = d - pd.DateOffset(months=1)
    return d.strftime("%Y-%m"), prev.strftime("%Y-%m")


def query_action(con, action: str, user: str, w: int):
    """Executes one evidence action. Returns (statistic or None, rows, bytes)."""
    cur = con.cursor()
    if action in ("cert_logon_afterhours", "cert_logon_pc_novelty"):
        rows = cur.execute("SELECT week, pc, activity, hour, dow, nbytes FROM logon WHERE user=? AND week BETWEEN ? AND ?",
                           (user, w - 4 if action.endswith("novelty") else w, w)).fetchall()
        cur_rows = [r for r in rows if r[0] == w and r[2] == "Logon"]
        if not cur_rows:
            return None, len(rows), sum(r[5] for r in rows)
        if action == "cert_logon_afterhours":
            stat = sum(1 for r in cur_rows if r[3] < 7 or r[3] >= 19 or r[4] >= 5)
        else:
            prior = {r[1] for r in rows if r[0] < w}
            stat = len({r[1] for r in cur_rows} - prior)
        return float(stat), len(rows), sum(r[5] for r in rows)
    if action == "cert_device_connects":
        rows = cur.execute("SELECT activity, nbytes FROM device WHERE user=? AND week=?", (user, w)).fetchall()
        return (float(sum(1 for r in rows if r[0] == "Connect")) if rows else None), len(rows), sum(r[1] for r in rows)
    if action == "cert_file_copies":
        rows = cur.execute("SELECT nbytes FROM file WHERE user=? AND week=?", (user, w)).fetchall()
        return (float(len(rows)) if rows else None), len(rows), sum(r[0] for r in rows)
    if action in ("cert_http_volume", "cert_http_domain_novelty"):
        rows = cur.execute("SELECT week, domain, nbytes FROM http WHERE user=? AND week BETWEEN ? AND ?",
                           (user, w - 4 if action.endswith("novelty") else w, w)).fetchall()
        cur_rows = [r for r in rows if r[0] == w]
        if not cur_rows:
            return None, len(rows), sum(r[2] for r in rows)
        if action == "cert_http_volume":
            stat = len(cur_rows)
        else:
            stat = len({r[1] for r in cur_rows} - {r[1] for r in rows if r[0] < w})
        return float(stat), len(rows), sum(r[2] for r in rows)
    if action in ("cert_email_external", "cert_email_attachments"):
        rows = cur.execute("SELECT external, attachments, nbytes FROM email WHERE user=? AND week=?", (user, w)).fetchall()
        if not rows:
            return None, 0, 0
        stat = sum(r[0] for r in rows) if action == "cert_email_external" else sum(int(r[1] or 0) for r in rows)
        return float(stat), len(rows), sum(r[2] for r in rows)
    if action == "cert_ldap_role_change":
        m, pm = _month_of_week(w)
        rows = cur.execute('SELECT month, role, business_unit, functional_unit, department, team, supervisor, nbytes FROM ldap '
                           'WHERE user=? AND month IN (?, ?)', (user, m, pm)).fetchall()
        cur_r = [r for r in rows if r[0] == m]
        prev_r = [r for r in rows if r[0] == pm]
        if not cur_r or not prev_r:
            return None, len(rows), sum(r[7] for r in rows)
        return float(cur_r[0][1:7] != prev_r[0][1:7]), len(rows), sum(r[7] for r in rows)
    if action == "cert_psychometric_neuroticism":
        rows = cur.execute("SELECT N, nbytes FROM psychometric WHERE user=?", (user,)).fetchall()
        return (float(rows[0][0]) if rows else None), len(rows), sum(r[1] for r in rows)
    raise ValueError(action)


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ground_truth").mkdir(parents=True, exist_ok=True)
    eps = sample_episodes()
    # insider flag is answer-key derived: used ONLY for stratified splitting, never passed to policies/environments
    eps[["episode_id", "user", "week", "insider"]].to_csv(OUT / "episodes.csv", index=False)
    build_stores(eps)
    con = sqlite3.connect(OUT / "cert_evidence.sqlite")
    recs = []
    for e in eps.itertuples():
        rec = {"episode_id": e.episode_id, "user": e.user, "week": int(e.week), "insider": bool(e.insider)}
        for aid, *_ in ACTIONS:
            t = time.perf_counter()
            stat, rows, nbytes = query_action(con, aid, e.user, int(e.week))
            rec[aid] = {"stat": stat, "rows": rows, "bytes": nbytes, "seconds": time.perf_counter() - t}
        recs.append(rec)
    con.close()
    (OUT / "evidence_store.json").write_text(json.dumps(recs), encoding="utf-8")
    # ground truth (restricted)
    ans = answer_events()
    positive = set(zip(ans["user"], ans["week"]))
    with (OUT / "ground_truth" / "episode_labels.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["episode_id", "y"])
        for e in eps.itertuples():
            w.writerow([e.episode_id, int((e.user, int(e.week)) not in positive)])


def load_cert(out_dir: str | None = None) -> dict[str, ObjectiveData]:
    base = ROOT / out_dir if out_dir else OUT
    recs = json.loads((base / "evidence_store.json").read_text(encoding="utf-8"))
    specs = [ActionSpec(aid, CLAIM, stype, NUMERIC_OUTCOMES, (0, 1, 0, -1), tuple(priv)) for aid, _, stype, priv in ACTIONS]
    n, m = len(recs), len(ACTIONS)
    vals, sec, rows, byt = np.full((n, m), np.nan), np.zeros((n, m)), np.zeros((n, m)), np.zeros((n, m))
    priv, prov = [], []
    for i, r in enumerate(recs):
        prow, vrow = [], []
        for j, (aid, table, _, pcats) in enumerate(ACTIONS):
            e = r[aid]
            if e["stat"] is not None:
                vals[i, j] = e["stat"]
            sec[i, j], rows[i, j], byt[i, j] = e["seconds"], e["rows"], e["bytes"]
            prow.append(list(pcats) if e["rows"] > 0 else [])
            vrow.append({"scope": f"user={r['user']};week={r['week']}", "parser": f"cert-store/1.0:{aid}",
                         "raw_artifact_ref": f"{base.relative_to(ROOT).as_posix()}/cert_evidence.sqlite#{table}", "timestamp_utc": r["week"]})
        priv.append(prow)
        prov.append(vrow)
    users = np.array([r["user"] for r in recs])
    return {CLAIM: ObjectiveData("cert", CLAIM, specs, np.array([r["episode_id"] for r in recs]), users,
                                 {"insider": np.array([r["insider"] for r in recs]), "week": np.array([r["week"] for r in recs])},
                                 "numeric", vals, sec, rows, byt, priv, prov, "CERT-r5.2" if base.name == "cert_stage2" else "CERT-r4.2")}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        configure(sys.argv[1])
    build()
    d = load_cert()[CLAIM]
    print(d.n, d.m)

