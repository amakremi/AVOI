"""Manuscript-facing copies of Stage-1 artefacts with the display label 'AVOI' (label change only; numbers untouched).

Source: results/stage1_ungated/ (archived, hashed). Output: results/stage1_ungated/manuscript/.
Tables/reports: textual replacement of the display name. Figures: regenerated from the ARCHIVED raw outputs with the
corrected display labels (method shown as AVOI; exact axis names; no Pareto-share annotation; actual mu values;
action frequency conditional on reaching the step). Verifies afterwards that the archive manifest is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from common import ROOT

ARCH = ROOT / "results" / "stage1_ungated"
OUT = ARCH / "manuscript"
NOTE = ("Stage 1 (original ungated experiment). Manuscript-facing copy: the method display name is AVOI "
        "(the historical label is retained only in the archived files); all numbers identical to the archived artefact.")


def relabel(text: str) -> str:
    return text.replace("AVOI-GRC(value-stop,bayes)", "AVOI(value-stop,bayes)").replace("AVOI-GRC", "AVOI")


if __name__ == "__main__":
    before = json.loads((ARCH / "MANIFEST.json").read_text(encoding="utf-8"))
    for sub in ("tables", "final_report"):
        for p in (ARCH / sub).glob("*"):
            if p.suffix in (".csv", ".md", ".tex", ".json"):
                d = OUT / sub / p.name
                d.parent.mkdir(parents=True, exist_ok=True)
                txt = relabel(p.read_text(encoding="utf-8"))
                if p.suffix == ".md":
                    txt = f"> {NOTE}\n\n" + txt
                elif p.suffix == ".tex":
                    txt = f"% {NOTE}\n" + txt
                d.write_text(txt, encoding="utf-8")
    from avoi.evaluation import analysis_data as AD
    from avoi.evaluation import figures as FG
    AD.RAW, AD.TRACES = ARCH / "raw", ARCH / "traces"
    AD.episodes.cache_clear(); AD.table.cache_clear()
    FG.FIG = OUT / "figures"
    res = FG.all_figures()
    # integrity: archived files unchanged
    changed = [f["path"] for f in before["files"]
               if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]]
    (OUT / "README.md").write_text(f"# Stage-1 manuscript copies\n\n{NOTE}\n\nArchive integrity after generation: "
                                   f"{'UNCHANGED' if not changed else 'CHANGED: ' + str(changed)}\n", encoding="utf-8")
    print("figures:", sum(len(v) for v in res.values()), "archive unchanged:", not changed)
    if changed:
        sys.exit(1)
