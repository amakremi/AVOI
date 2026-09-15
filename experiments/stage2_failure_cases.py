"""Trace-derived Stage-2 failure cases (results/stage2/failure_cases.md). Reads saved traces/episodes only."""
from __future__ import annotations

import gzip
import json
import sys
import warnings

import numpy as np
import pandas as pd

from common import ROOT

warnings.filterwarnings("ignore")
from avoi.bayes_risk import LossMatrix  # noqa: E402
from avoi.evaluation import stage2_tables as T  # noqa: E402

LOSS = LossMatrix()


def traces(dom, method):
    out = []
    for f in sorted((T.S2 / "traces" / dom / method).glob("*.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            out += [json.loads(l) for l in fh]
    return out


def fmt_trace(tr, max_steps=6):
    op = tr["operating_point"]
    k = op["n_acquisitions"]
    lines = [f"- `{tr['episode_id']}` — true Y={tr['y']} — decision **{op['decision']}** after {k} acquisitions "
             f"(stop: {op['reason']}; τ={tr['tuned_threshold']}); initial belief {tr['initial_belief']:.3f}; "
             f"adequacy {tr.get('adequacy_status')}"]
    for s, st in zip(tr["steps"][:min(k, max_steps)], tr["states"][1:min(k, max_steps) + 1]):
        lines.append(f"  - t={s['t']}: `{s['selected_action']}` → `{s.get('outcome', s.get('observed_outcome', '?'))}`; "
                     f"belief {st['belief']:.3f}, Bayes risk {LOSS.risk(st['belief']):.3f}")
    return lines


def main():
    raw = T.cold(T.episodes("raw"))
    out = ["# Stage-2 failure cases (generated from confirmation traces and episode records)", "",
           "AVOI at its validation-tuned threshold, raw (ungated) policy, confirmation partition, unless stated otherwise.", ""]
    for dom in T.DOMAINS:
        trs = traces(dom, "AVOI")
        if not trs:
            continue
        out += [f"## {T.DOM_LABEL[dom]}", ""]
        fa = [t for t in trs if t["operating_point"]["decision"] == "Assured" and t["y"] == 0]
        conf = [t for t in fa if raw[(raw["method"] == "AVOI") & (raw["episode_id"] == t["episode_id"])]["conflict"].astype(bool).any()]
        over = [t for t in fa if t["operating_point"]["belief"] >= 0.95]
        out += [f"### False assurances: {len(fa)} (terminal belief ≥ 0.95: {len(over)}; with conflicting evidence flag: {len(conf)})", ""]
        by = pd.Series([t["objective_id"] for t in fa]).value_counts().to_dict() if fa else {}
        out.append(f"By objective: {by}" if by else "None.")
        out.append("")
        for t in fa[:4]:
            out += fmt_trace(t)
        out.append("")
        # harmful/noisy acquisitions: an acquisition that moves the belief away from the truth by > 0.3
        harm = []
        for t in trs:
            k = t["operating_point"]["n_acquisitions"]
            b = [s["belief"] for s in t["states"][:k + 1]]
            for i in range(1, len(b)):
                d = (b[i] - b[i - 1]) * (1 if t["y"] == 1 else -1)
                if d < -0.3:
                    harm.append((d, t, i))
                    break
        out += [f"### Harmful / misleading acquisitions: {len(harm)} episodes contain an acquisition moving P(Y=1|E) away from the true label by > 0.3", ""]
        for d, t, i in sorted(harm, key=lambda x: x[0])[:3]:
            out += fmt_trace(t)
        out.append("")
        hr = [t for t in trs if t["operating_point"]["decision"] == "HumanReview"]
        out += [f"### Escalations: {len(hr)} (Y=0: {sum(t['y'] == 0 for t in hr)}, Y=1: {sum(t['y'] == 1 for t in hr)})", ""]
        for t in hr[:2]:
            out += fmt_trace(t)
        out.append("")
    # method-level comparisons on validated models
    val = raw[[T._safe_status(d, o) == "VALIDATED" for d, o in zip(raw["domain"], raw["objective"])]]
    keys = ["domain", "objective", "episode_id"]
    a = val[val["method"] == "AVOI"].set_index(keys)
    out += ["## Paired episode comparisons on VALIDATED IAM models", ""]
    for comp in ("B4-InformationGain", "B0-AllEvidence", "B3-CheapestFirst", "B2-Random[s0]"):
        c = val[val["method"] == comp].set_index(keys).reindex(a.index)
        worse = (a["loss"] > c["loss"]).sum()
        better = (a["loss"] < c["loss"]).sum()
        fa_a = ((a["decision"] == "Assured") & (a["y"] == 0)).sum()
        fa_c = ((c["decision"] == "Assured") & (c["y"] == 0)).sum()
        fewer_worse = ((a["n_acq"] < c["n_acq"]) & (a["loss"] > c["loss"])).sum()
        out.append(f"- AVOI vs {comp}: AVOI loss higher in {worse} episodes, lower in {better}; unsafe assurances AVOI {fa_a} vs {fa_c}; "
                   f"episodes where AVOI acquired less AND incurred higher loss: {fewer_worse}")
    out.append("")
    per_obj = val.groupby(["objective", "method"]).apply(lambda g: pd.Series({"UAR": ((g.decision == "Assured") & (g.y == 0)).sum() / max((g.y == 0).sum(), 1),
                                                                             "loss": g["loss"].mean(), "acq": g["n_acq"].mean()})).reset_index()
    per_obj = per_obj[per_obj["method"].isin(["AVOI", "B4-InformationGain", "B0-AllEvidence", "B3-CheapestFirst", "B2-Random[s0]", "B1-FixedChecklist"])]
    out += ["Per-objective UAR / loss / acquisitions (VALIDATED models):", "", "| objective | method | UAR | expected loss | acquisitions |", "|---|---|---|---|---|"]
    for r in per_obj.itertuples():
        out.append(f"| {r.objective} | {r.method} | {r.UAR:.4f} | {r.loss:.3f} | {r.acq:.2f} |")
    out.append("")
    (T.S2 / "failure_cases.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
