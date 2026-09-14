"""Task runner: executes one (experiment, domain, objective, outer fold) task and writes its raw outputs.

Raw outputs (results/raw/<experiment>/<domain>/):
  episodes_<objective>_f<k>.csv.gz   per-episode operating points (tuned thresholds; conditions)
  curves_<objective>_f<k>.csv.gz     aggregated counts per (method, threshold) on the held-out fold (curves)
  budget_<objective>_f<k>.csv.gz     per-episode results under acquisition budgets
  tuning_<objective>_f<k>.csv        inner-validation objective J per (method, threshold) and chosen thresholds
  models_<objective>_f<k>.json       evidence-model hyperparameters/structures, cost normalisers
  calib_<objective>_f<k>.csv.gz      posterior beliefs for calibration analysis
results/traces/<domain>/<method>/<objective>_f<k>.jsonl.gz   complete per-episode JSON traces (primary experiment)
"""
from __future__ import annotations

import gzip
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from avoi.bayes_risk import LossMatrix
from avoi.evaluation import engine as E
from avoi.evaluation.labels import load_labels

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "results" / "raw"
TRACES = ROOT / "results" / "traces"
_CACHE: dict = {}

TRACE_METHODS = {"AVOI-GRC", "B0-AllEvidence", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
                 "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI", "B8-LLMPlanner"}
CONDITION_METHODS = ["AVOI-GRC", "B1-FixedChecklist", "B3-CheapestFirst", "B4-InformationGain", "B5-GenericVOI",
                     "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI"]


def cfg_all() -> dict:
    return {"hp": yaml.safe_load((ROOT / "config" / "hyperparameters.yaml").read_text(encoding="utf-8")),
            "loss": yaml.safe_load((ROOT / "config" / "loss_matrix.yaml").read_text(encoding="utf-8")),
            "exp": yaml.safe_load((ROOT / "config" / "experiments.yaml").read_text(encoding="utf-8"))}


def load_domain(domain: str):
    if domain not in _CACHE:
        if domain == "iam":
            from avoi.datasets.iam import load_iam
            objs = load_iam()
        elif domain == "ait":
            from avoi.datasets.ait_episodes import load_ait
            objs = load_ait()
        elif domain == "cert":
            from avoi.datasets.cert import load_cert
            objs = load_cert()
        else:
            raise ValueError(domain)
        _CACHE[domain] = (objs, {k: load_labels(domain, v.episode_ids) for k, v in objs.items()})
    return _CACHE[domain]


def unit_strata(domain: str, objs: dict, labels: dict) -> np.ndarray:
    """Label-derived stratification variable for the OUTER split (identical across objectives of a domain)."""
    first = next(iter(objs))
    if domain == "iam":
        viol = sum(1 - labels[k] for k in objs)
        return (viol >= 3).astype(int)
    if domain == "cert":
        return objs[first].strata["insider"].astype(int)
    return labels[first]


def _write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip" if path.suffix == ".gz" else None)


def curve_aggregate(rows: list[dict], method: str) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["assured"] = df["decision"] == "Assured"
    df["hr"] = df["decision"] == "HumanReview"
    df["unsafe"] = df["assured"] & (df["y"] == 0)
    df["correct_auto"] = ((df["decision"] == "Assured") & (df["y"] == 1)) | ((df["decision"] == "NotAssured") & (df["y"] == 0))
    g = df.groupby("tau", dropna=False).agg(n=("y", "size"), n_viol=("y", lambda s: int((s == 0).sum())),
                                             n_assured=("assured", "sum"), n_hr=("hr", "sum"), n_unsafe=("unsafe", "sum"),
                                             n_correct_auto=("correct_auto", "sum"), loss_sum=("loss", "sum"),
                                             cost_sum=("cost", "sum"), privacy_sum=("privacy", "sum"),
                                             delay_sum=("delay", "sum"), nacq_sum=("n_acq", "sum")).reset_index()
    g.insert(0, "method", method)
    return g


def dense_grid(spec: E.MethodSpec, n: int) -> list:
    if spec.threshold == "risk":
        return list(np.round(np.linspace(0, 1, n), 4))
    if spec.threshold == "confidence":
        return list(np.round(np.linspace(0.5, 1.0, (n + 1) // 2), 4)) + [1.01]
    if spec.threshold == "symmetric":
        return list(np.round(np.linspace(0, 0.5, (n + 1) // 2), 4))
    return [None]


def run_task(task: dict) -> dict:
    t_start = time.time()
    C = cfg_all()
    hp, lcfg, ecfg = C["hp"], C["loss"], C["exp"]
    exp, domain, oid, fold = task["experiment"], task["domain"], task["objective"], task["fold"]
    objs, labels = load_domain(domain)
    data, y = objs[oid], labels[oid]
    seed = hp["master_seed"]
    w = lcfg["preference_weights"]
    lam, mu, nu = w["lambda_cost"], w["mu_privacy"], w["nu_delay"]
    grids = hp["policy_thresholds"]
    exp_cfg = ecfg["experiments"][exp]
    if exp_cfg.get("outer") == "lofo":          # leave-one-scenario-family-out robustness (IAM)
        idx_all = np.arange(data.n)
        fams = sorted(set(data.groups))
        folds = [(idx_all[data.groups != g], idx_all[data.groups == g]) for g in fams]
    else:
        folds = E.outer_folds(domain, data, unit_strata(domain, objs, labels), seed)
    train, test = folds[fold]
    inner = E.inner_folds(domain, data, train, y, seed)
    regime = exp_cfg.get("cost_regime", "B")
    model_kind = exp_cfg.get("model", "tan")
    fa_values = exp_cfg.get("false_assurance", [lcfg["primary"]["false_assurance"]])
    out_dir = RAW / exp / domain
    tag = f"{oid}_f{fold}"
    ep_rows, curve_frames, budget_rows, tuning_rows, calib_rows = [], [], [], [], []
    model_info = {}
    n_random = hp["random_baseline_seeds"] if exp_cfg.get("random_baseline", True) else 0

    for fa in fa_values:
        loss = LossMatrix(fa, lcfg["primary"]["false_non_assurance"], lcfg["primary"]["human_review"])
        weight_sets = exp_cfg.get("weight_multipliers", [{"lam": 1.0, "mu": 1.0, "nu": 1.0}])
        for wm in weight_sets:
            L, M, N = lam * wm["lam"], mu * wm["mu"], nu * wm["nu"]
            suite = E.method_suite(loss, L, M, N, grids["information_gain_eps_bits"], n_random, model_kind,
                                   which=exp_cfg.get("suite", "main"),
                                   sym_loss=LossMatrix(**lcfg["symmetric_ablation"]))
            include = exp_cfg.get("methods")
            if include:
                suite = [s for s in suite if s.name in include or any(s.name.startswith(p) for p in include)]
            kinds = sorted({s.model_kind for s in suite})
            cond_tag = f"fa={fa}|lam={wm['lam']}|mu={wm['mu']}|nu={wm['nu']}"
            # ---------------------------------------------------------------- outer context
            ctx = E.make_context(data, y, train, kinds, hp["evidence_models"], regime, inner,
                                 hp["evidence_models"]["masked_eval_masks"], seed)
            model_info[cond_tag] = {"hyperparameters": ctx.hps, "cost_C": ctx.cost.C.tolist(), "delay_D": ctx.cost.D.tolist(),
                                    "privacy_P": ctx.cost.P.tolist(), "mi_rank": [data.actions[j].action_id for j in ctx.mi_rank],
                                    "structures": {k: m.describe() for k, m in ctx.models.items()}}
            # ---------------------------------------------------------------- inner tuning
            J = {s.name: {} for s in suite}
            AGG = {s.name: {} for s in suite}   # pooled inner counts per threshold for target-matched selection
            for k_in, (itr, iva) in enumerate(inner):
                if len(set(y[itr])) < 2:
                    continue
                ictx = E.make_context(data, y, itr, kinds, hp["evidence_models"], regime, None, 0, seed, hps=ctx.hps)
                for s in suite:
                    grid = E.tau_grid(s, grids)
                    trs = E.run_trajectories(ictx, s, iva)
                    df = pd.DataFrame(E.points(trs, s, iva, y, loss, grid))
                    for tau, g in df.groupby("tau", dropna=False):
                        key = None if (isinstance(tau, float) and np.isnan(tau)) else tau
                        J[s.name].setdefault(key, []).append(E.objective_J(g, L, M, N))
                        a = AGG[s.name].setdefault(key, np.zeros(4))
                        a += [int((g["y"] == 0).sum()), int(((g["decision"] == "Assured") & (g["y"] == 0)).sum()),
                              int((g["decision"] != "HumanReview").sum()), float(g["cost"].sum())]
                        AGG[s.name][key] = a
                        AGG[s.name].setdefault(("n", key), 0)
                        AGG[s.name][("n", key)] += len(g)
            chosen = {}
            random_group = [s.name for s in suite if s.name.startswith("B2-Random")]
            for s in suite:
                scores = {tau: float(np.mean(v)) for tau, v in J[s.name].items()}
                for tau, v in scores.items():
                    tuning_rows.append({"condition": cond_tag, "method": s.name, "tau": tau, "inner_J": v})
                if s.name in random_group:
                    continue
                chosen[s.name] = min(scores, key=lambda t: (scores[t], -(t if t is not None else 0))) if scores else None
            if random_group:
                pooled = {}
                for name in random_group:
                    for tau, v in J[name].items():
                        pooled.setdefault(tau, []).append(np.mean(v))
                best = min(pooled, key=lambda t: (np.mean(pooled[t]), -(t if t is not None else 0)))
                for name in random_group:
                    chosen[name] = best
            for name, tau in chosen.items():
                tuning_rows.append({"condition": cond_tag, "method": name, "tau": tau, "inner_J": None, "chosen": True})
            # target-matched thresholds selected on INNER validation (never on test)
            targets = {}
            for s in suite:
                taus = [k for k in AGG[s.name] if not isinstance(k, tuple)]
                stats = {}
                for tau in taus:
                    nv, nu_, na, cs = AGG[s.name][tau]
                    n_all = AGG[s.name][("n", tau)]
                    stats[tau] = {"uar": nu_ / max(nv, 1), "coverage": na / max(n_all, 1), "cost": cs / max(n_all, 1)}
                for t_uar in exp_cfg.get("safety_targets", []):
                    ok = [t for t in taus if stats[t]["uar"] <= t_uar]
                    sel = min(ok, key=lambda t: (stats[t]["cost"], -stats[t]["coverage"])) if ok else "not_achieved"
                    targets[(s.name, f"target:uar<={t_uar}")] = sel
                for t_cov in exp_cfg.get("coverage_targets", []):
                    best = min(taus, key=lambda t: abs(stats[t]["coverage"] - t_cov)) if taus else None
                    sel = best if (best is not None and abs(stats[best]["coverage"] - t_cov) <= 0.05) else "not_achieved"
                    targets[(s.name, f"target:coverage={t_cov}")] = sel
                for tau in taus:
                    tuning_rows.append({"condition": cond_tag, "method": s.name, "tau": tau, "inner_uar": stats[tau]["uar"],
                                        "inner_coverage": stats[tau]["coverage"], "inner_cost": stats[tau]["cost"]})
            for (name, tgt), sel in targets.items():
                tuning_rows.append({"condition": cond_tag, "method": name, "target": tgt, "tau": None if sel == "not_achieved" else sel,
                                    "target_achieved_inner": sel != "not_achieved"})
            # ---------------------------------------------------------------- held-out test
            full_traces = {}
            for s in suite:
                record = exp_cfg.get("traces", False) and s.name in TRACE_METHODS
                trs = E.run_trajectories(ctx, s, test, record=record)
                full_traces[s.name] = trs
                for r in E.points(trs, s, test, y, loss, [chosen[s.name]]):
                    r.update(method=s.name, group=s.group, condition=cond_tag, start="cold", missing_level=1.0,
                             missing_mode="none", shift="none", episode_id=str(data.episode_ids[r["episode_index"]]),
                             conflict=bool(data.strata["conflict"][r["episode_index"]]) if "conflict" in data.strata else False)
                    ep_rows.append(r)
                for (name, tgt), sel in targets.items():
                    if name != s.name or sel == "not_achieved":
                        continue
                    for r in E.points(trs, s, test, y, loss, [sel]):
                        r.update(method=s.name, group=s.group, condition=cond_tag, start="cold", missing_level=1.0,
                                 missing_mode="none", shift=tgt, episode_id=str(data.episode_ids[r["episode_index"]]),
                                 conflict=bool(data.strata["conflict"][r["episode_index"]]) if "conflict" in data.strata else False)
                        ep_rows.append(r)
                if exp_cfg.get("curves", False):
                    curve_frames.append(curve_aggregate(E.points(trs, s, test, y, loss, dense_grid(s, grids["curve_tau_points"])), s.name)
                                        .assign(condition=cond_tag))
                if exp_cfg.get("budgets", False):
                    for bud in range(0, data.m + 1):
                        for r in E.points(trs, s, test, y, loss, [chosen[s.name]], budget=bud):
                            r.update(method=s.name, condition=cond_tag)
                            budget_rows.append(r)
                if record:
                    p = TRACES / domain / s.name / f"{tag}.jsonl.gz"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with gzip.open(p, "wt", encoding="utf-8") as fh:
                        for tr, i in zip(trs, test):
                            op = E.truncate(tr, s.cfg, chosen[s.name])
                            fh.write(json.dumps({**tr, "tuned_threshold": chosen[s.name], "operating_point": op,
                                                 "final_loss": loss.realized_loss(op["decision"], int(y[i])), "y": int(y[i])},
                                                default=float) + "\n")
            if exp_cfg.get("calibration", False):
                for s_name in ("B0-AllEvidence", "AVOI-GRC"):
                    if s_name in full_traces:
                        for tr, i in zip(full_traces[s_name], test):
                            calib_rows.append({"method": s_name, "episode_index": int(i), "y": int(y[i]),
                                               "belief_full": tr["final_belief"], "belief_initial": tr["initial_belief"],
                                               "model": model_kind})
                # masked-evidence calibration (random subsets, label-free masks)
                rng = np.random.default_rng(E.stable_seed(seed, "calib", oid, fold))
                mdl = ctx.models[model_kind]
                for i in test:
                    keep = rng.uniform()
                    ev = tuple((j, int(ctx.codes[i, j])) for j in range(data.m) if rng.uniform() < keep)
                    calib_rows.append({"method": "masked_random", "episode_index": int(i), "y": int(y[i]),
                                       "belief_full": mdl.posterior(ev), "belief_initial": None, "model": model_kind})
            # ---------------------------------------------------------------- starting-state conditions
            suite_by = {s.name: s for s in suite}
            cond_methods = [m for m in exp_cfg.get("condition_methods", CONDITION_METHODS) if m in suite_by]
            for level in exp_cfg.get("missing_levels", []):
                for mode in exp_cfg.get("missing_modes", []):
                    starts = E.initial_sets(ctx, test, level, mode, seed)
                    for name in cond_methods:
                        s = suite_by[name]
                        trs = E.run_trajectories(ctx, s, test, starts=starts)
                        for r in E.points(trs, s, test, y, loss, [chosen[name]]):
                            r.update(method=name, group=s.group, condition=cond_tag, start="partial", missing_level=level,
                                     missing_mode=mode, shift="none", episode_id=str(data.episode_ids[r["episode_index"]]))
                            ep_rows.append(r)
            # ---------------------------------------------------------------- reliability degradation (distribution shift)
            for rate in exp_cfg.get("degradation_rates", []):
                for stype in sorted({a.source_type for a in data.actions}):
                    ov = E.degradation_overrides(ctx, test, stype, rate, seed)
                    for name in cond_methods:
                        s = suite_by[name]
                        trs = E.run_trajectories(ctx, s, test, overrides=ov)
                        for r in E.points(trs, s, test, y, loss, [chosen[name]]):
                            r.update(method=name, group=s.group, condition=cond_tag, start="cold", missing_level=1.0,
                                     missing_mode="none", shift=f"degrade:{stype}:{rate}",
                                     episode_id=str(data.episode_ids[r["episode_index"]]))
                            ep_rows.append(r)
            # ---------------------------------------------------------------- action-cost change (Layer C)
            for mult in exp_cfg.get("cost_shift_multipliers", []):
                for stype in sorted({a.source_type for a in data.actions}):
                    mv = np.array([mult if a.source_type == stype else 1.0 for a in data.actions])
                    shifted = ctx.cost.with_multiplier(mv)
                    for name in cond_methods:
                        s = suite_by[name]
                        trs = E.run_trajectories(ctx, s, test, cost=shifted)
                        for r in E.points(trs, s, test, y, loss, [chosen[name]]):
                            r.update(method=name, group=s.group, condition=cond_tag, start="cold", missing_level=1.0,
                                     missing_mode="none", shift=f"cost:{stype}:x{mult}",
                                     episode_id=str(data.episode_ids[r["episode_index"]]))
                            ep_rows.append(r)

    base = {"experiment": exp, "domain": domain, "objective": oid, "fold": fold}
    _write_csv(pd.DataFrame(ep_rows).assign(**base), out_dir / f"episodes_{tag}.csv.gz")
    pd.DataFrame(tuning_rows).assign(**base).to_csv(out_dir / f"tuning_{tag}.csv", index=False)
    if curve_frames:
        _write_csv(pd.concat(curve_frames).assign(**base), out_dir / f"curves_{tag}.csv.gz")
    if budget_rows:
        _write_csv(pd.DataFrame(budget_rows).assign(**base), out_dir / f"budget_{tag}.csv.gz")
    if calib_rows:
        _write_csv(pd.DataFrame(calib_rows).assign(**base), out_dir / f"calib_{tag}.csv.gz")
    (out_dir / f"models_{tag}.json").write_text(json.dumps({**base, "n_train": int(len(train)), "n_test": int(len(test)),
                                                             "n_inner": len(inner), "models": model_info}, indent=1, default=str),
                                                encoding="utf-8")
    return {**base, "seconds": round(time.time() - t_start, 1), "n_rows": len(ep_rows)}

