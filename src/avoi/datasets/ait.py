"""AIT Log Data Set V2.0 importer (replay validation of evidence acquisition).

Step 1  index(testbed):   stream log files from the official zip, parse timestamps and generic per-line fields, and store
                          them in data/processed/ait/<testbed>_evidence.sqlite (one table per evidence source family).
                          The evidence index contains NO label information and NO line numbers.
Step 2  ground truth:     labels/ files (AIT line-level labels) are resolved to timestamps and written to
                          data/processed/ait/ground_truth/<testbed>_labeled_lines.csv. Used ONLY to derive Y.
Excluded as evidence: attacker host logs (attacker_0: attacks.log, dnsteal captures), user-simulation logs
(internal/remote employees, ext users: sm.log, downloads), pcaps, binary systemd journals, Suricata stats/eve.json.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "ait"
OUT = ROOT / "data" / "processed" / "ait"
TESTBEDS = ["russellmitchell", "santos"]
MON = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

EXCLUDED_HOST_PREFIXES = ("attacker", "ext_user", "internal_employee", "remote_employee")

# source family -> (path regex, privacy categories revealed when rows are accessed)
FAMILIES = {
    "vpn":        (r"/vpn/logs/openvpn\.log", ["ip_address", "user_identifier", "authentication_event"]),
    "dns":        (r"/logs/dnsmasq\.log", ["ip_address", "host_device_identifier"]),
    "web_access": (r"/logs/(apache2/.*access\.log|horde/horde-access\.log)", ["ip_address"]),
    "web_error":  (r"/logs/(apache2/.*error\.log|horde/horde-error\.log)", ["ip_address"]),
    "auth":       (r"/logs/auth\.log", ["user_identifier", "host_device_identifier", "authentication_event"]),
    "audit":      (r"/logs/audit/audit\.log", ["user_identifier", "host_device_identifier"]),
    "ids":        (r"/logs/suricata/fast\.log", ["ip_address", "security_incident_information"]),
    "mail":       (r"/logs/(exim4/mainlog|mail\.log)", ["email_address", "user_identifier", "ip_address"]),
    "syslog":     (r"/logs/(syslog|messages|kern\.log)", ["host_device_identifier"]),
    "monitoring": (r"/monitoring/logs/logstash/.*system\.cpu\.log", ["host_device_identifier"]),
}

RX_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})")
RX_APACHE_ACC = re.compile(r"\[(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})")
RX_APACHE_ERR = re.compile(r"^\[\w{3} (\w{3}) (\d{2}) (\d{2}):(\d{2}):(\d{2})\.\d+ (\d{4})\]")
RX_SYSLOG = re.compile(r"^(\w{3})\s+(\d{1,2}) (\d{2}):(\d{2}):(\d{2})")
RX_CTIME = re.compile(r"^\w{3} (\w{3})\s+(\d{1,2}) (\d{2}):(\d{2}):(\d{2}) (\d{4})")
RX_AUDIT = re.compile(r"msg=audit\((\d+)\.")
RX_FAST = re.compile(r"^(\d{2})/(\d{2})/(\d{4})-(\d{2}):(\d{2}):(\d{2})")


def _epoch(y, mo, d, h, mi, s) -> int:
    return int(datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), tzinfo=timezone.utc).timestamp())


def parse_ts(family: str, line: str, year: int) -> int | None:
    if family == "audit":
        m = RX_AUDIT.search(line)
        return int(m.group(1)) if m else None
    if family == "ids":
        m = RX_FAST.match(line)
        return _epoch(m.group(3), m.group(1), m.group(2), m.group(4), m.group(5), m.group(6)) if m else None
    if family == "web_access":
        m = RX_APACHE_ACC.search(line)
        return _epoch(m.group(3), MON[m.group(2)], m.group(1), m.group(4), m.group(5), m.group(6)) if m else None
    if family == "web_error":
        m = RX_APACHE_ERR.match(line)
        return _epoch(m.group(6), MON[m.group(1)], m.group(2), m.group(3), m.group(4), m.group(5)) if m else None
    if family == "monitoring":
        try:
            ts = json.loads(line).get("@timestamp", "")
        except json.JSONDecodeError:
            return None
        m = RX_ISO.search(ts)
        return _epoch(*m.groups()) if m else None
    m = RX_CTIME.match(line)
    if m:
        return _epoch(m.group(6), MON[m.group(1)], m.group(2), m.group(3), m.group(4), m.group(5))
    m = RX_SYSLOG.match(line)
    if m and m.group(1) in MON:
        return _epoch(year, MON[m.group(1)], m.group(2), m.group(3), m.group(4), m.group(5))
    m = RX_ISO.search(line[:40])
    return _epoch(*m.groups()) if m else None


def derive(family: str, line: str) -> tuple[float, float]:
    """Generic, label-free per-line fields (f1 = notable-event indicator/value, f2 = secondary)."""
    if family == "vpn":
        return float("Peer Connection Initiated" in line or "TLS: Initial packet" in line), float("AUTH_FAILED" in line)
    if family == "dns":
        m = re.search(r"query\[\w+\] (\S+)", line)
        return (float(len(m.group(1)) > 60) if m else 0.0), float(bool(m))
    if family == "web_access":
        m = re.search(r'" (\d{3}) ', line)
        st = int(m.group(1)) if m else 0
        return float(st >= 400), float(st >= 500)
    if family == "web_error":
        return 1.0, float("[:error]" in line or ":error]" in line)
    if family == "auth":
        return float(" su:" in line or " su[" in line or "sudo:" in line), float("Failed password" in line or "authentication failure" in line)
    if family == "audit":
        return float("type=EXECVE" in line or "type=USER_CMD" in line), float("res=failed" in line)
    if family == "ids":
        m = re.search(r"\[Priority: (\d)\]", line)
        return float(bool(m) and int(m.group(1)) <= 2), 1.0
    if family == "mail":
        return float(" <= " in line), float("Login:" in line)
    if family == "syslog":
        return 1.0, float("error" in line.lower())
    if family == "monitoring":
        try:
            v = json.loads(line)["system"]["cpu"]["total"]["norm"]["pct"]
        except (KeyError, TypeError, json.JSONDecodeError):
            v = 0.0
        return float(v), 0.0
    return 0.0, 0.0


def classify(path: str) -> str | None:
    if not path.startswith("gather/"):
        return None
    host = path.split("/")[1]
    if host.startswith(EXCLUDED_HOST_PREFIXES):
        return None
    for fam, (rx, _) in FAMILIES.items():
        if re.search(rx, path):
            return fam
    return None


def index(testbed: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ground_truth").mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(RAW / f"{testbed}.zip")
    meta = yaml.safe_load(z.read("dataset.yaml"))
    start = int(datetime.fromisoformat(meta["start"]).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(meta["end"]).replace(tzinfo=timezone.utc).timestamp())
    year = datetime.fromtimestamp(start, tz=timezone.utc).year
    db_path = OUT / f"{testbed}_evidence.sqlite"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    for fam in FAMILIES:
        con.execute(f"CREATE TABLE {fam} (ts INTEGER, host TEXT, nbytes INTEGER, f1 REAL, f2 REAL)")
    label_files = {i.filename[len("labels/"):]: i.filename for i in z.infolist() if i.filename.startswith("labels/") and not i.is_dir()}
    stats = defaultdict(int)
    labeled_rows = []
    t_start = time.time()
    for info in z.infolist():
        if info.is_dir():
            continue
        fam = classify(info.filename)
        rel = info.filename[len("gather/"):]
        has_labels = rel in label_files
        if fam is None and not has_labels:
            continue
        host = info.filename.split("/")[1]
        line_ts: dict[int, int] = {}
        batch = []
        last_ts = None
        with z.open(info.filename) as fh:
            for ln, raw in enumerate(fh, start=1):
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                ts = parse_ts(fam or "syslog", line, year)
                if ts is None:
                    ts = last_ts
                last_ts = ts
                if has_labels:
                    line_ts[ln] = ts
                if fam is None or ts is None:
                    continue
                f1, f2 = derive(fam, line)
                batch.append((ts, host, len(raw), f1, f2))
                if len(batch) >= 50000:
                    con.executemany(f"INSERT INTO {fam} VALUES (?,?,?,?,?)", batch)
                    stats[fam] += len(batch)
                    batch = []
        if batch:
            con.executemany(f"INSERT INTO {fam} VALUES (?,?,?,?,?)", batch)
            stats[fam] += len(batch)
        if has_labels:
            with z.open(label_files[rel]) as lf:
                for raw in lf:
                    rec = json.loads(raw)
                    ts = line_ts.get(rec["line"])
                    labeled_rows.append((rel, fam or "unindexed", ts, "|".join(sorted(rec["labels"]))))
    for fam in FAMILIES:
        con.execute(f"CREATE INDEX idx_{fam}_ts ON {fam}(ts)")
    con.commit()
    con.close()
    with (OUT / "ground_truth" / f"{testbed}_labeled_lines.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "family", "ts", "labels"])
        w.writerows(labeled_rows)
    info = {"testbed": testbed, "start": start, "end": end, "rows": dict(stats), "labeled_lines": len(labeled_rows),
            "index_seconds": round(time.time() - t_start, 1)}
    (OUT / f"{testbed}_index_meta.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


def label_timeline(testbed: str, window_s: int = 600) -> list[tuple]:
    """Summary used to define micro-claims: per label, first/last timestamp and number of windows touched."""
    per = defaultdict(set)
    with (OUT / "ground_truth" / f"{testbed}_labeled_lines.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["ts"]:
                continue
            for lab in r["labels"].split("|"):
                per[lab].add(int(r["ts"]) // window_s)
    return sorted((lab, len(w), min(w) * window_s, max(w) * window_s) for lab, w in per.items())


if __name__ == "__main__":
    import sys
    for tb in (sys.argv[1:] or TESTBEDS):
        print(index(tb))
        for lab, nwin, first, last in label_timeline(tb):
            print(f"  {lab:28s} windows={nwin:4d} first={datetime.fromtimestamp(first, tz=timezone.utc)} last={datetime.fromtimestamp(last, tz=timezone.utc)}")
