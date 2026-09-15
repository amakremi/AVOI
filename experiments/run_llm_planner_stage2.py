"""Stage-2 secondary experiment: B8 LLM-only planner (gemma4:e4b) vs AVOI on a predefined confirmation subset.

Subset (fixed in config/stage2.yaml before confirmation): controlled IAM, confirmation scenario families 16-23, all six
objectives. Evidence model, calibrator, cost model and decision layer are the frozen Stage-2 development objects for both
planners; AVOI uses the threshold tuned on the adequacy-validation partition. The LLM sees no labels and no posteriors
and does not decide. Both raw and adequacy-enforced rows are written. Requires the Stage-2 confirmation run.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace

import numpy as np
import pandas as pd
import yaml

from common import ROOT

from avoi.agent import PolicyConfig
from avoi.baselines.llm_planner import LLMPlanner
from avoi.bayes_risk import LossMatrix
from avoi.evaluation import engine as E
from avoi.evaluation import stage2 as S

sys.path.insert(0, str(ROOT / "experiments"))
from run_stage2 import verify  # noqa: E402

if __name__ == "__main__":
    verify()
    C = S.cfg()
    lc = C["s2"]["llm_planner"]
    lcfg = C["loss"]
    w = lcfg["preference_weights"]
    lam, mu, nu = w["lambda_cost"], w["mu_privacy"], w["nu_delay"]
    loss = LossMatrix(lcfg["primary"]["false_assurance"], lcfg["primary"]["false_non_assurance"], lcfg["primary"]["human_review"])
    frozen = json.loads((S.S2 / "ADEQUACY_DECISIONS.json").read_text(encoding="utf-8"))["decisions"]
    ocfg = {o["id"]: {"title": o["title"], "predicate": " ".join(o["operational_predicate"].split())}
            for o in yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))["objectives"]}
    out = S.S2 / "raw" / "llm_planner"
    planner = LLMPlanner(lc["model"], ocfg, seed=lc["seed"], cache_path=out / "cache_gemma4_e4b.jsonl")
    lo, hi = lc["families"]
    rows, traces = [], []
    for oid in sorted(S.domain_partitions("iam")):
        dev = S.develop("iam", oid, C)
        fd = frozen[f"iam|{oid}"]
        assert fd["model_id"] == dev["primary"].model_id
        from avoi import adequacy as AQ
        decision = AQ.AdequacyDecision(**{k: fd[k] for k in ("model_id", "status", "reason", "discrimination_pass", "calibration_pass",
                                                             "support_pass", "failed_conditions", "metrics", "ci", "calibrator", "policy_version")})
        cdata, cy, cg = S.domain_partitions("iam")[oid]["conf"]
        idx = np.flatnonzero((cg >= lo) & (cg <= hi))
        ctx = S.partition_context(dev, cdata)
        tuning = pd.read_csv(S.S2 / "raw" / "tuning" / f"tuning_iam_{oid}.csv.gz")
        ch = tuning[(tuning["experiment"] == "primary") & (tuning["method"] == S.PROPOSED) & (tuning["chosen"] == True)]
        tau = float(ch["tau"].iloc[0])
        llm = E.MethodSpec("B8-LLMPlanner(gemma4:e4b)", PolicyConfig("B8-LLMPlanner(gemma4:e4b)", "external", loss, stop_rule="none",
                                                                     value_stop=False, decision_rule="bayes_argmin", external_selector=planner),
                           "primary", None, "baseline")
        avoi = [s for s in S.suite(C, loss, lam, mu, nu, "main", 0) if s.name == S.PROPOSED][0]
        avoi_vs = E.MethodSpec("AVOI(value-stop,bayes)", replace(avoi.cfg, name="AVOI(value-stop,bayes)", decision_rule="bayes_argmin", stop_rule="none"),
                               "primary", None, "proposed")
        for spec, t in ((llm, None), (avoi, tau), (avoi_vs, None)):
            trs = S.trajectories(ctx, spec, idx, decision, record=spec.name.startswith("B8"))
            r = S.rows_at(trs, spec, idx, cy, cg, loss, [t], extra={"objective": oid})
            rows += [{**x, "adequacy_mode": "raw"} for x in r]
            rows += S.gate_rows(r, decision, loss)
            if spec.name.startswith("B8"):
                traces += [{**tr, "y": int(cy[i])} for tr, i in zip(trs, idx)]
        print(oid, decision.status, "episodes", len(idx), "llm calls", planner.calls, "invalid", planner.invalid, flush=True)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df["domain"] = "iam"
    df.to_csv(out / "episodes_llm_planner.csv.gz", index=False)
    with (out / "traces_llm_planner.jsonl").open("w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, default=float) + "\n")
    (out / "run_info.json").write_text(json.dumps({"model": lc["model"], "subset": f"IAM confirmation families {lo}-{hi}, 6 objectives",
                                                   "episodes_per_method": int(((df["adequacy_mode"] == "raw") & (df["method"] == S.PROPOSED)).sum()), "new_llm_calls": planner.calls,
                                                   "invalid_responses": planner.invalid, "temperature": lc["temperature"], "seed": lc["seed"],
                                                   "think": False}, indent=1))
