"""STAGE 3 / WP1 runner.

  python experiments/stage3/run_wp1.py devcheck   development data only (held-out Stage-3 development families)
  python experiments/stage3/run_wp1.py adequacy   fit on development, adequacy on validation (no confirmation data loaded)
  python experiments/stage3/run_wp1.py confirm    requires EXPERIMENT_FREEZE_STAGE3.json + ADEQUACY_DECISIONS_STAGE3.json
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "stage3"))

from avoi import adequacy as AQ  # noqa: E402
from avoi.evaluation import stage2 as S  # noqa: E402
from avoi.evaluation import stage3 as S3M  # noqa: E402
from avoi.evaluation import stage3_wp1 as W  # noqa: E402
from avoi.evaluation.stage3 import S3  # noqa: E402


def fixed_horizon_block(ctx, data, y, groups, idx, C, loss, lam, mu, nu, tag, out_dir, record_rank=True):
    avoi, frozen = W.avoi_specs(C, loss, lam, mu, nu)
    ks = S3M.cfg3()["wp1"]["fixed_horizons"]
    res, rows, traces = {}, [], {}
    ids = [a.action_id for a in data.actions]
    ymap = {str(data.episode_ids[i]): int(y[i]) for i in idx}
    for spec in (avoi, frozen):
        fh = W.fixed_horizon_cfg(spec, max(ks))
        trs = W.run_traces(ctx, fh, idx, max_steps=max(ks), record=True)
        traces[spec.name] = trs
        for k in ks:
            r = S.rows_at(trs, fh, idx, y, groups, loss, [None], budget=k, extra={"objective": data.objective_id, "horizon": k})
            rows += r
            assert all(x["n_acq"] == min(k, data.m) for x in r), "fixed horizon must acquire exactly k"
        W.write_traces(trs, out_dir / f"fixed_horizon_{spec.name.replace(' ', '_')}_{tag}.jsonl.gz")
    summ, per_step = W.adaptivity_metrics(traces[avoi.name], ids)
    summ_frozen, _ = W.adaptivity_metrics(traces[frozen.name], ids)
    gmap = {str(data.episode_ids[i]): str(groups[i]) for i in idx}
    perm = W.history_permutation_test(traces[avoi.name], gmap, seed=S3M.cfg3()["seeds"]["permutation"])
    perm_frozen = W.history_permutation_test(traces[frozen.name], gmap, n_perm=2000, seed=S3M.cfg3()["seeds"]["permutation"])
    rank_rows = W.ranking_trace_rows(traces[avoi.name], avoi.name, ids, ymap) + W.ranking_trace_rows(traces[frozen.name], frozen.name, ids, ymap)
    return {"adaptive": summ, "frozen": summ_frozen, "permutation": perm, "permutation_frozen_control": perm_frozen,
            "per_step": per_step.assign(objective=data.objective_id)}, rows, rank_rows


def devcheck():
    C, c3, loss, lam, mu, nu = W.settings()
    parts = S3M.iam_partitions(include_confirmation=False)
    out = S3 / "development" / "wp1_devcheck"
    summary = {}
    all_rows, all_rank = [], []
    for oid, p in parts.items():
        data, y, g = p["dev"]
        hold = np.array([str(x).startswith("s3dev:") and int(str(x).split(":")[1]) % 5 == 0 for x in g])
        S._CACHE["iam_s3_devcheck"] = S._CACHE.get("iam_s3_devcheck", {})
        S._CACHE["iam_s3_devcheck"][oid] = {"dev": (data.subset(np.flatnonzero(~hold)), y[~hold], g[~hold]),
                                           "val": (data.subset(np.flatnonzero(hold)), y[hold], g[hold])}
        dev = S3M.develop("iam_s3_devcheck", oid, C)
        hd, hy, hg = S._CACHE["iam_s3_devcheck"][oid]["val"]
        ctx = S.partition_context(dev, hd)
        S.CONFLICT["flags"] = hd.strata.get("conflict")
        res, rows, rank_rows = fixed_horizon_block(ctx, hd, hy, hg, np.arange(hd.n), C, loss, lam, mu, nu, oid, out / "traces")
        summary[oid] = {"model": dev["primary"].model_id, "n_heldout": int(hd.n), **{k: v for k, v in res.items() if k != "per_step"}}
        all_rows += rows
        all_rank += rank_rows
        print(oid, json.dumps(summary[oid], default=float)[:900], flush=True)
    df = pd.DataFrame(all_rows)
    piv = df.groupby(["objective", "horizon", "method"])["loss"].mean().unstack("method")
    print(piv.round(4).to_string())
    S3M.save_json({"summary": summary, "loss_by_objective_horizon": piv.reset_index().to_dict(orient="records")}, out / "devcheck_summary.json")


def adequacy_phase():
    C, c3, loss, lam, mu, nu = W.settings()
    parts = S3M.iam_partitions(include_confirmation=False)
    recs = {}
    for oid in parts:
        dev = S3M.develop(W.DOMAIN, oid, C)
        val = S.validate(W.DOMAIN, oid, dev, C)
        dec = val["decision"]
        rec = {"work_package": "WP1", "domain": "iam", "objective": oid, "model_id": dec.model_id, "decision": asdict(dec),
               "selection": dev["selection"], "validation_primary": {"metrics": val["primary"]["metrics"], "bootstrap": val["primary"]["bootstrap"]},
               "validation_uncalibrated": {"metrics": val["uncalibrated"]["metrics"], "bootstrap": val["uncalibrated"]["bootstrap"]},
               "groups_with_violation": val["groups_with_violation"], "prevalence_satisfied_dev": dev["prevalence_satisfied_dev"],
               "development_sources": sorted(set(str(x).split(":")[0] for x in parts[oid]["dev"][2]))}
        S3M.save_json(rec, S3 / "validation" / f"wp1_{oid}.json")
        recs[oid] = rec
        print(oid, dec.status, dec.reason, flush=True)
    return recs


def confirm():
    from run_stage3 import verify_freeze, load_decisions
    verify_freeze()
    decisions = load_decisions()
    C, c3, loss, lam, mu, nu = W.settings()
    parts = S3M.iam_partitions(include_confirmation=True)
    out = S3 / "confirmation" / "wp1"
    adapt_summary, fh_rows, rank_rows, per_step, normal_rows, enforced_rows, budget_rows, tuning = {}, [], [], [], [], [], [], []
    for oid, p in parts.items():
        t0 = time.time()
        dev = S3M.develop(W.DOMAIN, oid, C)
        fd = decisions[f"iam|{oid}"]
        if fd["model_id"] != dev["primary"].model_id:
            raise RuntimeError(f"model id changed after freeze: {fd['model_id']} vs {dev['primary'].model_id}")
        decision = AQ.AdequacyDecision(**{k: fd[k] for k in ("model_id", "status", "reason", "discrimination_pass", "calibration_pass",
                                                             "support_pass", "failed_conditions", "metrics", "ci", "calibrator", "policy_version")})
        vdata, vy, vg = p["val"]
        cdata, cy, cg = p["conf"]
        vctx, cctx = S.partition_context(dev, vdata), S.partition_context(dev, cdata)
        S.CONFLICT["flags"] = cdata.strata.get("conflict")
        cidx = np.arange(cdata.n)
        # ---------------- fixed horizon (primary A1/A2 evidence)
        res, rows, rr = fixed_horizon_block(cctx, cdata, cy, cg, cidx, C, loss, lam, mu, nu, oid, S3 / "traces" / "wp1")
        adapt_summary[oid] = {k: v for k, v in res.items() if k != "per_step"} | {"model_id": dev["primary"].model_id, "adequacy_status": decision.status}
        fh_rows += rows
        rank_rows += rr
        per_step.append(res["per_step"])
        # ---------------- normal operation (secondary): validation-tuned thresholds, at-most-k budgets, raw + enforced
        specs = S.suite(C, loss, lam, mu, nu, "main", c3["wp1"]["random_seeds"])
        avoi, frozen = W.avoi_specs(C, loss, lam, mu, nu)
        specs = specs + [frozen]
        chosen, targets, tab = S.tune(vctx, specs, vy, vg, loss, lam, mu, nu, C)
        tuning += [{**t, "objective": oid} for t in tab] + [{"objective": oid, "method": m, "tau": t, "chosen": True} for m, t in chosen.items()]
        base = {"experiment": "normal_operation", "objective": oid}
        for s in specs:
            trs = S.trajectories(cctx, s, cidx, decision, record=False)
            r = S.rows_at(trs, s, cidx, cy, cg, loss, [chosen[s.name]], extra=base)
            normal_rows += r
            enforced_rows += S.gate_rows(r, decision, loss)
            if s.name in (S.PROPOSED, W.FROZEN, "B0-AllEvidence", "B1-FixedChecklist", "B4-InformationGain"):
                for bud in range(0, cdata.m + 1):
                    budget_rows += S.rows_at(trs, s, cidx, cy, cg, loss, [chosen[s.name]], budget=bud, extra={**base, "experiment": "budget"})
        print(oid, decision.status, "seconds", round(time.time() - t0, 1), flush=True)
    raw = S3 / "raw" / "wp1"
    S.write(pd.DataFrame(fh_rows), raw / "fixed_horizon_rows.csv.gz")
    S.write(pd.DataFrame(normal_rows), raw / "normal_operation_raw.csv.gz")
    S.write(pd.DataFrame(enforced_rows), raw / "normal_operation_enforced.csv.gz")
    S.write(pd.DataFrame(budget_rows), raw / "budget_rows.csv.gz")
    S.write(pd.DataFrame(tuning), raw / "tuning.csv.gz")
    S.write(pd.concat(per_step), raw / "adaptivity_per_step.csv.gz")
    rank = pd.DataFrame(rank_rows)
    (S3 / "traces").mkdir(parents=True, exist_ok=True)
    rank.to_parquet(S3 / "traces" / "adaptive_action_rankings.parquet", engine="fastparquet", index=False)
    rank.drop(columns=["outcome_predictions", "hypothetical_posteriors", "expected_post_action_risk", "burdens", "avoi_values"]).to_csv(
        S3 / "traces" / "adaptive_action_rankings_summary.csv", index=False)
    S3M.save_json(adapt_summary, out / "adaptivity_summary.json")


if __name__ == "__main__":
    phase = sys.argv[1]
    {"devcheck": devcheck, "adequacy": adequacy_phase, "confirm": confirm}[phase]()
