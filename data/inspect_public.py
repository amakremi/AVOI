"""Exploratory helper: AIT formats for vpn / monitoring / webserver / apache; list of files per included family."""
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent / "raw"
z = zipfile.ZipFile(root / "ait" / "russellmitchell.zip")
want = ("vpn/logs", "monitoring/logs", "webserver/logs", "intranet_server/logs/apache2", "cloud_share/logs/apache2",
        "internal_share/logs/audit", "mail/logs/exim4")
for info in z.infolist():
    f = info.filename
    if info.is_dir() or not f.startswith("gather/") or not any(w in f for w in want):
        continue
    with z.open(f) as fh:
        head = fh.read(400).decode(errors="replace").splitlines()[:1]
    print(f"{f} ({info.file_size / 1e6:.2f} MB) | {head[0][:200] if head else ''}")
