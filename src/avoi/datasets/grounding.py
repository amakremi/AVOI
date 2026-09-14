"""Extract requirement-grounding material (NIST SP 800-53A, SCF, NCA ECC) into processed files.

Outputs (data/processed/grounding/):
  nist_800_53a_selected.csv   assessment objectives + examine/interview/test methods for selected controls
  scf_iac_controls.csv        SCF IAC controls: identifiers, ERL ids, 800-53 and NCA ECC mappings (identifiers only)
  scf_erl_iac.csv             SCF Evidence Request List entries mapped to selected IAC controls (id, area, artifact name)
  nca_ecc_2_2_excerpt.txt     text of ECC-2:2024 sub-domain 2-2 (IAM) for local interpretation (not redistributed)

This material grounds objectives and the evidence-action vocabulary. It is NEVER used as a label source.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "grounding"

NIST_CONTROLS = ["AC-02", "AC-02(02)", "AC-02(03)", "AC-06(05)", "AC-06(07)", "IA-02(01)", "PS-04", "AU-06"]
SCF_CONTROLS = ["IAC-06", "IAC-06.1", "IAC-07", "IAC-07.1", "IAC-07.2", "IAC-15", "IAC-15.1", "IAC-15.2", "IAC-15.3",
                "IAC-16", "IAC-16.1", "IAC-17", "IAC-20", "IAC-21", "IAC-21.3", "HRS-09", "MON-01.8"]


def nist_800_53a() -> list[dict]:
    rows, current = [], None
    with (RAW / "nist" / "sp800-53ar5-assessment-procedures.csv").open(encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ident = r["identifier"].strip()
            base = re.match(r"^([A-Z]{2}-\d{2}(\(\d{2}\))?)", ident)
            if not base:
                continue
            ctrl = base.group(1)
            if ctrl in NIST_CONTROLS:
                rows.append({"control": ctrl, "identifier": ident, "control_name": r["control-name"],
                             "assessment_objective": r["assessment-objective"], "examine": r["EXAMINE"],
                             "interview": r["INTERVIEW"], "test": r["TEST"]})
    return rows


def scf() -> tuple[list[dict], list[dict]]:
    wb = openpyxl.load_workbook(RAW / "scf" / "secure-controls-framework-scf-2026-2.xlsx", read_only=True)
    ws = wb["SCF 2026.2"]
    it = ws.iter_rows(values_only=True)
    header = [str(h) if h is not None else "" for h in next(it)]
    idx = {h: i for i, h in enumerate(header)}
    nist_col = next(i for h, i in idx.items() if h.startswith("NIST\n800-53\nR5") and "(moderate)" not in h and "(low)" not in h and "(high)" not in h and "(privacy)" not in h and "NOC" not in h)
    nca_cols = [i for h, i in idx.items() if "Saudi Arabia" in h and "ECC" in h]  # SCF 2026.2 maps ECC-1:2018 only
    controls = []
    for row in it:
        sid = row[idx["SCF #"]]
        if sid in SCF_CONTROLS:
            controls.append({
                "scf_id": sid, "scf_control_name": row[idx["SCF Control"]],
                "erl_ids": " ".join(str(row[idx["Evidence Request List (ERL) #"]] or "").split()),
                "nist_800_53r5": " ".join(str(row[nist_col] or "").split()),
                "nca_ecc_mappings": " | ".join(f"{header[c].replace(chr(10), ' ')}: {' '.join(str(row[c] or '').split())}" for c in nca_cols),
            })
    erl_ws = wb["Evidence Request List 2026.2"]
    it = erl_ws.iter_rows(values_only=True)
    eh = [str(h) for h in next(it)]
    erl = []
    for row in it:
        if not row or row[1] is None:
            continue
        maps = str(row[eh.index("SCF Control Mappings")] or "").split()
        if any(m in SCF_CONTROLS for m in maps):
            erl.append({"erl_id": row[1], "area_of_focus": row[2], "documentation_artifact": row[3],
                        "scf_control_mappings": " ".join(maps)})
    return controls, erl


def nca_excerpt() -> str:
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(RAW / "nca" / "ECC-2-2024-EN.pdf").pages)
    # the controls section (not the table of contents) is the occurrence followed by "Objective"
    m = re.search(r"2-2\s*Identity and Access Management\s*\n?\s*Objective", text)
    if not m:
        return ""
    end = re.search(r"\n\s*2-3\s*Information System", text[m.end():])
    return text[m.start(): m.end() + (end.start() if end else 5000)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in [("nist_800_53a_selected.csv", nist_800_53a())] + list(zip(["scf_iac_controls.csv", "scf_erl_iac.csv"], scf())):
        with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(name, len(rows))
    (OUT / "nca_ecc_2_2_excerpt.txt").write_text(nca_excerpt(), encoding="utf-8")


if __name__ == "__main__":
    main()

