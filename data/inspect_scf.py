"""Exploratory helper: show ECC-2:2024 1-9 (HR) clauses and the extracted SCF ERL entries."""
import csv
import re
from pathlib import Path
from pypdf import PdfReader

root = Path(__file__).resolve().parent
text = "\n".join(p.extract_text() or "" for p in PdfReader(root / "raw" / "nca" / "ECC-2-2024-EN.pdf").pages)
m = re.search(r"1-9\s*Cybersecurity in Human Resources\s*\n?\s*Objective", text)
print(text[m.start(): m.start() + 1800] if m else "1-9 not found")
for r in csv.DictReader(open(root / "processed" / "grounding" / "scf_erl_iac.csv", encoding="utf-8")):
    print(r)
