"""Secondary experiment: B8 LLM-only planner vs AVOI-GRC on a predefined subset.

Subset (predefined): controlled IAM testbed, outer fold 0, all six objectives, all held-out episodes.
Evidence model, cost model and decision layer are identical for both planners (TAN fitted on the outer training fold
with the same inner-CV hyperparameter selection as the primary experiment). Terminal decision for both: Bayes decision
with escalation option (bayes_argmin) at the planner's stop; AVOI is additionally reported at its primary tuned threshold.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import yaml

from common import ROOT, verify_freeze

from avoi.agent import PolicyConfig, truncate
from avoi.baselines.llm_planner import LLMPlanner
from avoi.bayes_risk import LossMatrix
from avoi.evaluation import engine as E
from avoi.evaluation.runner import cfg_all, load_domain, unit_strata

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="llama3.1:8b")
    ap.add_argument("--fold", type=int, default=0)
    args = ap.parse_args()
    verify_freeze()
    C = cfg_all()
    hp, lcfg = C["hp"], C["loss"]
    w = lcfg["preference_weights"]
    loss = LossMatrix(**{k: lcfg["primary"][k] for k in ("false_assurance", "false_non_assurance", "human_review")})
    objs, labels = load_domain("iam")
    ocfg = {o["id"]: {"title": o["title"], "predicate": " ".join(o["operational_predicate"].split())}
            for o in yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))["objectives"]}
    planner = LLMPlanner(args.model, ocfg, seed=0)
    rows, traces = [], []
    for oid, data in objs.items():
        y = labels[oid]
        folds = E.outer_folds("iam", data, unit_strata("iam", objs, labels), hp["master_seed"])
        train, test = folds[args.fold]
        inner = E.inner_folds("iam", data, train, y, hp["master_seed"])
        ctx = E.make_context(data, y, train, ["tan"], hp["evidence_models"], "B", inner, hp["evidence_models"]["masked_eval_masks"], hp["master_seed"])
        tuning = pd.read_csv(ROOT / "results" / "raw" / "primary" / "iam" / f"tuning_{oid}_f{args.fold}.csv")
        tau_avoi = float(tuning[(tuning["method"] == "AVOI-GRC") & (tuning.get("chosen") == True)]["tau"].iloc[0])
        llm_spec = E.MethodSpec("B8-LLMPlanner", PolicyConfig("B8-LLMPlanner", "external", loss, stop_rule="none", value_stop=False,
                                                              decision_rule="bayes_argmin", external_selector=planner), "tan", None, "baseline")
        avoi_spec = E.method_suite(loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"], 1e-3, 0)[0]
        avoi_valuestop = E.MethodSpec("AVOI-GRC(value-stop,bayes)", replace(avoi_spec.cfg, decision_rule="bayes_argmin", stop_rule="none"),
                                      "tan", None, "proposed")
        for spec, tau in ((llm_spec, None), (avoi_spec, tau_avoi), (avoi_valuestop, None)):
            trs = E.run_trajectories(ctx, spec, test, record=spec.name.startswith("B8"))
            for r in E.points(trs, spec, test, y, loss, [tau]):
                r.update(method=spec.name, objective=oid, fold=args.fold, episode_id=str(data.episode_ids[r["episode_index"]]))
                rows.append(r)
            if spec.name.startswith("B8"):
                for tr, i in zip(trs, test):
                    traces.append({**tr, "y": int(y[i])})
        print(oid, "llm calls so far", planner.calls, "invalid", planner.invalid, flush=True)
    out = ROOT / "results" / "raw" / "llm_planner"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "episodes_llm_planner.csv.gz", index=False)
    with (out / "traces_llm_planner.jsonl").open("w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, default=float) + "\n")
    (out / "run_info.json").write_text(json.dumps({"model": args.model, "fold": args.fold, "new_llm_calls": planner.calls,
                                                   "invalid_responses": planner.invalid, "temperature": 0, "seed": 0}, indent=1))
