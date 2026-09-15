"""Stage-2 tables, figures and numeric digest (inputs for results/final_report_v2). Reads saved raw outputs only."""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd

from common import ROOT

sys.path.insert(0, str(ROOT / "experiments"))
from run_stage2 import verify  # noqa: E402

from avoi.evaluation import stage2_figures as FG  # noqa: E402
from avoi.evaluation import stage2_tables as T  # noqa: E402


def model_vs_decision_uncertainty(raw, enf) -> str:
    esc = T.escalation_table(raw, enf)
    lines = ["# Model uncertainty vs decision uncertainty (Stage 2)", "",
             "*Decision uncertainty*: the evidence model is VALIDATED but the acquired evidence leaves the Bayes risk above the",
             "threshold, or no remaining action has positive assurance value -> AVOI acquires more evidence or escalates",
             "(stop reasons `no_positive_value`, `exhausted`, `budget`).", "",
             "*Model inadequacy*: the evidence model failed discrimination, calibration or sample-support conditions on the",
             "adequacy-validation partition -> autonomous AVOI is withheld for the whole model (reason `MODEL_ADEQUACY_RESTRICTED`",
             "or `MODEL_ADEQUACY_UNSUPPORTED`). More evidence is not assumed to repair this, and it is never converted to NotAssured.", "",
             "Counts on the confirmation partition (AVOI, cold start, validation-tuned threshold):", "",
             "| domain | objective | adequacy status | escalation type | escalations | Y=0 | Y=1 | false assurances prevented | false non-assurances prevented | correct autonomous decisions withheld | coverage lost |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in esc.itertuples():
        lines.append(f"| {r.domain} | {r.objective} | {r.adequacy_status} | {r.type} | {r.escalations} | {r.Y0} | {r.Y1} | {r.false_assurances_prevented} | "
                     f"{r.false_non_assurances_prevented} | {r.correct_autonomous_withheld} | {r.coverage_lost:.3f} |")
    lines += ["", "For model-adequacy escalations, 'escalations' counts gated episodes; the prevented/withheld counts refer to episodes whose",
              "raw AVOI decision was autonomous (episodes already escalated for evidence uncertainty are not double-counted).", ""]
    return "\n".join(lines)


def digest(out: dict, figs: dict, raw, enf) -> dict:
    d = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "tables": out, "figures": figs, "decisions": T.decisions()}
    d["n_confirmation_episodes"] = {dom: int(T.cold(raw[(raw["domain"] == dom) & (raw["method"] == "AVOI")]).shape[0]) for dom in T.DOMAINS}
    return d


if __name__ == "__main__":
    verify()
    raw, enf = T.episodes("raw"), T.episodes("enforced")
    out = T.build_all()
    (T.S2 / "model_vs_decision_uncertainty.md").write_text(model_vs_decision_uncertainty(raw, enf), encoding="utf-8")
    figs = FG.all_figures()
    dg = digest(out, figs, raw, enf)
    (T.S2 / "report_digest.json").write_text(json.dumps(dg, indent=1, default=str), encoding="utf-8")
    failed = {k: v for k, v in figs.items() if str(v[0]).startswith("FAILED")}
    print(json.dumps({"tables": len(out), "figures": len(figs), "failed_figures": failed}, indent=1))
