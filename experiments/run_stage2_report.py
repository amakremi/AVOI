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
    lines += ["## A. Can high initial uncertainty be resolved by acquisition? (raw AVOI, confirmation)", "",
              "High initial uncertainty = acquisition-required episodes (initial evidence insufficient for autonomous termination at the",
              "validation-tuned threshold; predefined). 'Resolved' = AVOI terminates autonomously after acquiring evidence.", "",
              "| domain | objective | status | acquisition-required episodes | mean initial Bayes risk | resolved autonomously | error among resolved | mean acquisitions | realized loss |",
              "|---|---|---|---|---|---|---|---|---|"]
    loss = T.LOSS
    base = T.cold(raw)
    for (dom, o), g in base[base["method"] == "AVOI"].groupby(["domain", "objective"]):
        req = g[g["acquisition_required"] == True]
        if req.empty:
            continue
        auto = req[req["decision"] != "HumanReview"]
        err = ((auto["decision"] == "Assured") & (auto["y"] == 0)) | ((auto["decision"] == "NotAssured") & (auto["y"] == 1))
        lines.append(f"| {dom} | {o} | {T.status_of(dom, o)} | {len(req)} | {req['initial_risk'].mean():.3f} | {len(auto) / len(req):.3f} | "
                     f"{(err.mean() if len(auto) else float('nan')):.3f} | {req['n_acq'].mean():.2f} | {req['loss'].mean():.3f} |")
    lines += ["", "## B. Is inadequacy a model-level property that more evidence does not repair?", "",
              "Predicted vs realized loss of autonomous decisions: predicted = expected loss of the chosen decision under the model's",
              "own (calibrated) posterior; realized = loss against confirmation labels. A trustworthy model has a small gap; the gap is",
              "shown for AVOI and for All Evidence (every source acquired).", "",
              "| domain | objective | status | method | autonomous decisions | predicted loss | realized loss | realized - predicted | autonomous error rate |",
              "|---|---|---|---|---|---|---|---|---|"]
    for (dom, o), g in base.groupby(["domain", "objective"]):
        for m in ("AVOI", "B0-AllEvidence"):
            x = g[(g["method"] == m) & (g["decision"] != "HumanReview")]
            if x.empty:
                continue
            b = x["belief"].to_numpy(float)
            pred = np.where(x["decision"] == "Assured", loss.false_assurance * (1 - b), loss.false_non_assurance * b)
            err = ((x["decision"] == "Assured") & (x["y"] == 0)) | ((x["decision"] == "NotAssured") & (x["y"] == 1))
            lines.append(f"| {dom} | {o} | {T.status_of(dom, o)} | {T.DISPLAY[m]} | {len(x)} | {pred.mean():.3f} | {x['loss'].mean():.3f} | "
                         f"{x['loss'].mean() - pred.mean():+.3f} | {err.mean():.3f} |")
    lines += ["", "Interpretation rule (fixed before inspection): episode-level uncertainty is resolvable when acquisition-required episodes",
              "of VALIDATED models terminate autonomously with low error; model inadequacy is indicated when the realized-minus-predicted",
              "gap stays large even with all evidence acquired.", ""]
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
