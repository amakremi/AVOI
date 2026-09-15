"""STAGE 2 pipeline: evidence-model adequacy as a safety condition for autonomous AVOI + confirmation evaluation.

Logical order per domain / objective (see docs/MODEL_ADEQUACY.md):
  DEVELOPMENT (Stage-1 data)   -> group-aware cross-fitting: model/alpha selection and calibrator selection on
                                  out-of-fold predictions; final model + calibrator fitted on development data
  ADEQUACY VALIDATION (new)    -> metrics + group bootstrap CIs -> VALIDATED / RESTRICTED / UNSUPPORTED
                                  (+ threshold tuning of every acquisition policy on the same partition)
  FREEZE                        -> results/stage2/ADEQUACY_DECISIONS.json (hashed) before confirmation
  CONFIRMATION (new)            -> raw (ungated) acquisition-policy results; enforced results = same trajectories
                                  with the frozen gate applied identically to every model-based method
Confirmation labels are used only to score held-out decisions.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import GroupKFold

from avoi import adequacy as AQ
from avoi.agent import PolicyConfig, SequentialAssuranceAgent, threshold_met, truncate
from avoi.bayes_risk import HUMAN_REVIEW, SYMMETRIC_01, LossMatrix, entropy
from avoi.costs import CostModel
from avoi.datasets.common import Discretizer, ObjectiveData, codes_for, make_environment
from avoi.evaluation import engine as E
from avoi.evaluation.labels import load_labels
from avoi.models.tan import DiscreteBayesNet, FixedReliabilityModel

ROOT = Path(__file__).resolve().parents[3]
S2 = ROOT / "results" / "stage2"
PROPOSED = "AVOI"
_CACHE: dict = {}


def cfg() -> dict:
    return {"hp": yaml.safe_load((ROOT / "config" / "hyperparameters.yaml").read_text(encoding="utf-8")),
            "loss": yaml.safe_load((ROOT / "config" / "loss_matrix.yaml").read_text(encoding="utf-8")),
            "adequacy": AQ.load_policy(),
            "s2": yaml.safe_load((ROOT / "config" / "stage2.yaml").read_text(encoding="utf-8"))}


# ====================================================================================== partitions
def domain_partitions(domain: str) -> dict:
    """Returns {objective: {"dev": (data, y), "val": (data, y, groups), "conf": (data, y, groups)}}."""
    if domain in _CACHE:
        return _CACHE[domain]
    s2 = cfg()["s2"]["partitions"][domain]
    out = {}
    if domain == "iam":
        from avoi.datasets.iam import load_iam
        dev, new = load_iam(), load_iam("data/processed/iam_stage2/evidence_store", "iam_stage2")
        for oid in dev:
            d, n = dev[oid], new[oid]
            yd, yn = load_labels("iam", d.episode_ids), load_labels("iam_stage2", n.episode_ids)
            val = np.flatnonzero(n.groups < s2["validation_families_below"])
            conf = np.flatnonzero(n.groups >= s2["validation_families_below"])
            out[oid] = {"dev": (d, yd, d.groups), "val": (n.subset(val), yn[val], n.groups[val]),
                        "conf": (n.subset(conf), yn[conf], n.groups[conf])}
    elif domain == "ait":
        from avoi.datasets.ait_episodes import load_ait
        dev, new = load_ait(), load_ait("data/processed/ait_stage2", "ait_stage2")
        for oid in dev:
            d, n = dev[oid], new[oid]
            yd, yn = load_labels("ait", d.episode_ids), load_labels("ait_stage2", n.episode_ids)
            blocks = np.array([f"{tb}|{int(w) // 3600}" for tb, w in zip(n.strata["testbed"], n.strata["w0"])])
            val = np.flatnonzero(np.isin(n.strata["testbed"], s2["validation_testbeds"]))
            conf = np.flatnonzero(np.isin(n.strata["testbed"], s2["confirmation_testbeds"]))
            out[oid] = {"dev": (d, yd, d.groups), "val": (n.subset(val), yn[val], blocks[val]),
                        "conf": (n.subset(conf), yn[conf], blocks[conf])}
    elif domain == "cert":
        from avoi.datasets.cert import load_cert
        dev, new = load_cert(), load_cert("data/processed/cert_stage2")
        for oid in dev:
            d, n = dev[oid], new[oid]
            yd = load_labels("cert", d.episode_ids)
            yn = load_labels("cert_stage2", n.episode_ids)
            users = np.array(sorted(set(n.groups)))
            rng = np.random.default_rng(s2["user_split_seed"])
            val_users = set(rng.choice(users, size=int(round(s2["validation_user_fraction"] * len(users))), replace=False))
            val = np.flatnonzero([u in val_users for u in n.groups])
            conf = np.flatnonzero([u not in val_users for u in n.groups])
            out[oid] = {"dev": (d, yd, d.groups), "val": (n.subset(val), yn[val], n.groups[val]),
                        "conf": (n.subset(conf), yn[conf], n.groups[conf])}
    _CACHE[domain] = out
    return out


def dev_folds(domain: str, data: ObjectiveData) -> list[tuple[np.ndarray, np.ndarray]]:
    idx = np.arange(data.n)
    if domain == "ait":
        return [(idx[data.groups != tb], idx[data.groups == tb]) for tb in sorted(set(data.groups))]
    return [(idx[a], idx[b]) for a, b in GroupKFold(n_splits=5).split(idx, groups=data.groups)]


# ====================================================================================== model development
def build_base(kind: str, K: list[int], alpha: float, polarity=None):
    if kind == "tan":
        return DiscreteBayesNet(K, alpha=alpha, tree=True)
    if kind == "nb":
        return DiscreteBayesNet(K, alpha=alpha, tree=False)
    if kind == "fixedrel":
        return FixedReliabilityModel(K, polarity)
    raise ValueError(kind)


def _states(codes_row: np.ndarray, rng, n_masks: int) -> list[tuple]:
    m = len(codes_row)
    full = tuple((j, int(codes_row[j])) for j in range(m))
    out = [full]
    for _ in range(n_masks):
        keep = rng.uniform()
        out.append(tuple((j, int(codes_row[j])) for j in range(m) if rng.uniform() < keep))
    return out


def oof_predictions(domain, data, y, kind, alpha, n_masks, seed) -> pd.DataFrame:
    rows = []
    K = [len(a.outcomes) for a in data.actions]
    pol = [list(a.polarity) for a in data.actions]
    for k, (tr, te) in enumerate(dev_folds(domain, data)):
        disc = Discretizer().fit(data.values[tr]) if data.kind == "numeric" else None
        codes = codes_for(data, disc)
        mdl = build_base(kind, K, alpha, pol).fit(codes[tr], y[tr])
        rng = np.random.default_rng(E.stable_seed(seed, "oof", data.objective_id, kind, alpha, k))
        for i in te:
            for s, ev in enumerate(_states(codes[i], rng, n_masks)):
                rows.append({"episode_index": int(i), "group": str(data.groups[i]), "y": int(y[i]), "state": "full" if s == 0 else f"mask{s}",
                             "p": mdl.posterior(ev)})
    return pd.DataFrame(rows)


def logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def develop(domain: str, oid: str, C: dict) -> dict:
    """Model selection, calibrator selection, final fit - DEVELOPMENT data only."""
    parts = domain_partitions(domain)[oid]
    data, y, _ = parts["dev"]
    pol = C["adequacy"]
    seed = pol["bootstrap"]["seed"]
    cands = []
    for kind, key in (("tan", "tan"), ("nb", "naive_bayes")):
        for alpha in pol["model_candidates"][key]["alpha"]:
            oof = oof_predictions(domain, data, y, kind, alpha, pol["oof_random_masks"], seed)
            cands.append({"kind": kind, "alpha": alpha, "oof_log_loss": logloss(oof["y"].to_numpy(), oof["p"].to_numpy()), "oof": oof})
    best = min(cands, key=lambda c: (round(c["oof_log_loss"], 10), c["kind"] != "tan", c["alpha"]))
    oof = best["oof"]
    cal_name, cal_scores = AQ.select_calibrator(oof["p"].to_numpy(), oof["y"].to_numpy(), oof["group"].to_numpy(),
                                                pol["calibration_candidates"], seed=seed)
    cal = AQ.Calibrator(cal_name).fit(oof["p"].to_numpy(), oof["y"].to_numpy())
    disc = Discretizer().fit(data.values) if data.kind == "numeric" else None
    codes = codes_for(data, disc)
    K = [len(a.outcomes) for a in data.actions]
    polarity = [list(a.polarity) for a in data.actions]
    base = build_base(best["kind"], K, best["alpha"]).fit(codes, y)
    model_id = f"{domain}:{oid}:{best['kind']}(alpha={best['alpha']})+{cal_name}"
    primary = AQ.CalibratedEvidenceModel(base, cal, model_id)
    # simpler-model ablation (Naive Bayes) with its own development-only calibrator
    nb_alpha = min((c for c in cands if c["kind"] == "nb"), key=lambda c: c["oof_log_loss"])
    nb_cal_name, _ = AQ.select_calibrator(nb_alpha["oof"]["p"].to_numpy(), nb_alpha["oof"]["y"].to_numpy(),
                                          nb_alpha["oof"]["group"].to_numpy(), pol["calibration_candidates"], seed=seed)
    nb_model = AQ.CalibratedEvidenceModel(build_base("nb", K, nb_alpha["alpha"]).fit(codes, y),
                                          AQ.Calibrator(nb_cal_name).fit(nb_alpha["oof"]["p"].to_numpy(), nb_alpha["oof"]["y"].to_numpy()),
                                          f"{domain}:{oid}:nb(alpha={nb_alpha['alpha']})+{nb_cal_name}")
    fixed = FixedReliabilityModel(K, polarity).fit(codes, y)
    cost = CostModel.fit(data.records, data.bytes_, data.seconds, data.n_categories(), "B")
    uncal = AQ.CalibratedEvidenceModel(base, AQ.Calibrator("none").fit(np.array([0.5]), np.array([1])), model_id + "[uncalibrated]")
    return {"disc": disc, "base": base, "primary": primary, "uncalibrated": uncal, "nb": nb_model, "fixedrel": fixed, "cost": cost,
            "mi_rank": E.mutual_information_rank(codes, y, K), "prevalence_satisfied_dev": float(np.mean(y)),
            "selection": {"model_candidates": [{k: v for k, v in c.items() if k != "oof"} for c in cands],
                          "selected_model": {"kind": best["kind"], "alpha": best["alpha"]}, "calibrator_cv_log_loss": cal_scores,
                          "selected_calibrator": cal_name, "calibrator_params": cal.params,
                          "oof_metrics_uncalibrated": AQ.point_metrics(oof.loc[oof.state == "full", "y"], oof.loc[oof.state == "full", "p"], float(np.mean(y))),
                          "oof_metrics_calibrated": AQ.point_metrics(oof.loc[oof.state == "full", "y"],
                                                                     cal.transform(oof.loc[oof.state == "full", "p"].to_numpy()), float(np.mean(y))),
                          "model_structure": base.describe()},
            "oof": oof}


# ====================================================================================== adequacy validation
def partition_context(dev: dict, data: ObjectiveData) -> E.FoldContext:
    codes = codes_for(data, dev["disc"])
    K = [len(a.outcomes) for a in data.actions]
    models = {"primary": dev["primary"], "nb": dev["nb"], "fixedrel": dev["fixedrel"], "uncalibrated": dev["uncalibrated"]}
    return E.FoldContext(data, codes, K, dev["cost"], models, {}, np.arange(0), dev["mi_rank"])


def validate(domain: str, oid: str, dev: dict, C: dict) -> dict:
    data, y, groups = domain_partitions(domain)[oid]["val"]
    ctx = partition_context(dev, data)
    pol = C["adequacy"]
    ref = dev["prevalence_satisfied_dev"]
    out = {}
    for which in ("primary", "uncalibrated"):
        mdl = ctx.models[which]
        p = np.array([mdl.posterior(tuple((j, int(ctx.codes[i, j])) for j in range(data.m))) for i in range(data.n)])
        m = AQ.point_metrics(y, p, ref, pol["ece_bins"])
        boot = AQ.group_bootstrap(y, p, groups, ref, pol["bootstrap"]["n_resamples"], pol["bootstrap"]["seed"],
                                  pol["bootstrap"]["confidence"], pol["ece_bins"])
        out[which] = {"metrics": m, "bootstrap": boot, "predictions": p}
    gwv = int(len(set(groups[y == 0])))
    rng = np.random.default_rng(E.stable_seed(pol["bootstrap"]["seed"], "val-mask", oid))
    pm, ym = [], []
    for i in range(data.n):
        for ev in _states(ctx.codes[i], rng, pol["oof_random_masks"])[1:]:
            pm.append(ctx.models["primary"].posterior(ev)); ym.append(int(y[i]))
    out["masked_diagnostic_metrics"] = AQ.point_metrics(np.array(ym), np.array(pm), ref, pol["ece_bins"])
    dec = AQ.decide(dev["primary"].model_id, out["primary"]["metrics"], out["primary"]["bootstrap"], pol,
                    dev["selection"]["selected_calibrator"], groups_with_violation=gwv)
    out["decision"] = dec
    out["groups_with_violation"] = gwv
    out["groups"] = groups
    out["y"] = y
    return out


# ====================================================================================== trajectories and rows
def suite(C: dict, loss: LossMatrix, lam: float, mu: float, nu: float, which: str = "main", n_random: int = 20) -> list[E.MethodSpec]:
    sym = LossMatrix(**C["loss"]["symmetric_ablation"])
    specs = E.method_suite(loss, lam, mu, nu, C["hp"]["policy_thresholds"]["information_gain_eps_bits"], n_random, "primary", which, sym)
    out = []
    for s in specs:
        name = s.name.replace("AVOI-GRC", PROPOSED)
        out.append(E.MethodSpec(name, replace(s.cfg, name=name), s.model_kind if s.model_kind in ("nb", "fixedrel") else "primary",
                                s.threshold, s.group))
    return out


def trajectories(ctx: E.FoldContext, spec: E.MethodSpec, idx: np.ndarray, decision: AQ.AdequacyDecision | None,
                 starts=None, record=False, mode="diagnostic") -> list[dict]:
    agent = SequentialAssuranceAgent(replace(spec.cfg, tau=None), ctx.models[spec.model_kind], ctx.cost, ctx.data.objective_id, record)
    out = []
    for k, i in enumerate(idx):
        env = make_environment(ctx.data, i, ctx.codes[i], ctx.cost, starts[k] if starts else set())
        tr = agent.run(env, adequacy=decision, adequacy_mode=mode)
        if not record:
            tr.pop("final_candidates", None)
        out.append(tr)
    return out


def rows_at(trs, spec, idx, y, groups, loss, taus, budget=None, extra=None) -> list[dict]:
    rows = []
    conflict = CONFLICT.get("flags")
    for tau in taus:
        c = replace(spec.cfg, tau=tau)
        for tr, i in zip(trs, idx):
            op = truncate(tr, spec.cfg, tau, budget)
            b0 = tr["initial_belief"]
            rows.append({"episode_index": int(i), "episode_id": tr["episode_id"], "group": str(groups[i]), "tau": tau, "y": int(y[i]),
                         "decision": op["decision"], "belief": op["belief"], "initial_belief": b0, "initial_risk": loss.risk(b0),
                         "initial_entropy": float(entropy(b0)), "acquisition_required": bool(not threshold_met(c, b0)) if tau is not None else True,
                         "n_acq": op["n_acquisitions"], "cost": op["cost"], "delay": op["delay"], "seconds": op["seconds"],
                         "records": op["records"], "bytes": op["bytes"], "privacy": len(op["privacy_categories"]) / 10.0,
                         "reason": op["reason"], "loss": loss.realized_loss(op["decision"], int(y[i])), "budget": budget,
                         "method": spec.name, "group_type": spec.group,
                         "conflict": bool(conflict[i]) if conflict is not None else False, **(extra or {})})
    return rows


CONFLICT: dict = {}


def objective_J(df, lam, mu, nu):
    return float(df["loss"].mean() + lam * df["cost"].mean() + mu * df["privacy"].mean() + nu * df["delay"].mean())


def tune(ctx, specs, y, groups, loss, lam, mu, nu, C) -> tuple[dict, dict, list[dict]]:
    """Threshold selection on the ADEQUACY-VALIDATION partition (never on confirmation)."""
    grids = C["hp"]["policy_thresholds"]
    s2 = C["s2"]
    idx = np.arange(ctx.data.n)
    chosen, targets, table = {}, {}, []
    pooled_random = {}
    for s in specs:
        trs = trajectories(ctx, s, idx, None)
        df = pd.DataFrame(rows_at(trs, s, idx, y, groups, loss, E.tau_grid(s, grids)))
        stats = {}
        for tau, g in df.groupby("tau", dropna=False):
            key = None if (isinstance(tau, float) and math.isnan(tau)) else tau
            nv = int((g["y"] == 0).sum())
            stats[key] = {"J": objective_J(g, lam, mu, nu), "uar": float(((g["decision"] == "Assured") & (g["y"] == 0)).sum() / max(nv, 1)),
                          "coverage": float((g["decision"] != HUMAN_REVIEW).mean()), "cost": float(g["cost"].mean())}
            table.append({"method": s.name, "tau": key, **stats[key]})
        if s.name.startswith("B2-Random"):
            for k, v in stats.items():
                pooled_random.setdefault(k, []).append(v["J"])
        else:
            chosen[s.name] = min(stats, key=lambda t: (stats[t]["J"], -(t if t is not None else 0)))
        for gam in s2["coverage_targets"]:
            best = min(stats, key=lambda t: abs(stats[t]["coverage"] - gam))
            targets[(s.name, f"target:coverage={gam}")] = best if abs(stats[best]["coverage"] - gam) <= 0.05 else "not_achieved"
        for eta in s2["safety_targets"]:
            for gam in s2["coverage_targets"]:
                ok = [t for t in stats if stats[t]["uar"] <= eta and stats[t]["coverage"] >= gam]
                targets[(s.name, f"target:uar<={eta}&coverage>={gam}")] = min(ok, key=lambda t: (stats[t]["cost"], -stats[t]["coverage"])) if ok else "not_achieved"
    if pooled_random:
        best = min(pooled_random, key=lambda t: (np.mean(pooled_random[t]), -(t if t is not None else 0)))
        for s in specs:
            if s.name.startswith("B2-Random"):
                chosen[s.name] = best
    return chosen, targets, table


def gate_rows(rows: list[dict], decision: AQ.AdequacyDecision, loss: LossMatrix) -> list[dict]:
    """ENFORCED view: identical eligibility rule for every model-based method (all methods here use the evidence model)."""
    if decision.autonomous_allowed:
        return [{**r, "adequacy_mode": "enforced", "adequacy_status": decision.status, "adequacy_reason": decision.reason} for r in rows]
    out = []
    for r in rows:
        out.append({**r, "decision": HUMAN_REVIEW, "reason": decision.gate_reason, "n_acq": 0, "cost": 0.0, "delay": 0.0, "seconds": 0.0,
                    "records": 0, "bytes": 0, "privacy": 0.0, "loss": loss.realized_loss(HUMAN_REVIEW, r["y"]),
                    "adequacy_mode": "enforced", "adequacy_status": decision.status, "adequacy_reason": decision.reason,
                    "ungated_decision": r["decision"], "ungated_loss": r["loss"], "ungated_n_acq": r["n_acq"]})
    return out


def write(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip" if path.suffix == ".gz" else None)


def curve_counts(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["assured"] = df["decision"] == "Assured"
    df["hr"] = df["decision"] == HUMAN_REVIEW
    df["unsafe"] = df["assured"] & (df["y"] == 0)
    df["correct_auto"] = ((df["decision"] == "Assured") & (df["y"] == 1)) | ((df["decision"] == "NotAssured") & (df["y"] == 0))
    return df.groupby(["method", "tau"], dropna=False).agg(
        n=("y", "size"), n_viol=("y", lambda s: int((s == 0).sum())), n_assured=("assured", "sum"), n_hr=("hr", "sum"),
        n_unsafe=("unsafe", "sum"), n_correct_auto=("correct_auto", "sum"), loss_sum=("loss", "sum"), cost_sum=("cost", "sum"),
        privacy_sum=("privacy", "sum"), delay_sum=("delay", "sum"), nacq_sum=("n_acq", "sum")).reset_index()


# ====================================================================================== task
def run_domain_objective(task: dict) -> dict:
    t0 = time.time()
    domain, oid, phase = task["domain"], task["objective"], task["phase"]
    C = cfg()
    lcfg = C["loss"]
    w = lcfg["preference_weights"]
    lam, mu, nu = w["lambda_cost"], w["mu_privacy"], w["nu_delay"]
    loss = LossMatrix(lcfg["primary"]["false_assurance"], lcfg["primary"]["false_non_assurance"], lcfg["primary"]["human_review"])
    raw = S2 / "raw"
    tag = f"{domain}_{oid}"
    dev = develop(domain, oid, C)
    val = validate(domain, oid, dev, C)
    if phase == "adequacy":
        dec = val["decision"]
        rec = {"domain": domain, "objective": oid, "model_id": dec.model_id, "decision": {k: v for k, v in asdict(dec).items()},
               "selection": dev["selection"], "validation_uncalibrated": {"metrics": val["uncalibrated"]["metrics"], "ci": val["uncalibrated"]["bootstrap"]},
               "validation_primary": {"metrics": val["primary"]["metrics"], "bootstrap": val["primary"]["bootstrap"]},
               "masked_diagnostic_metrics": val["masked_diagnostic_metrics"], "groups_with_violation": val["groups_with_violation"],
               "prevalence_satisfied_dev": dev["prevalence_satisfied_dev"]}
        (S2 / "adequacy").mkdir(parents=True, exist_ok=True)
        (S2 / "adequacy" / f"{tag}.json").write_text(json.dumps(rec, indent=1, default=float), encoding="utf-8")
        vd, vy, vg = domain_partitions(domain)[oid]["val"]
        write(pd.DataFrame({"episode_id": vd.episode_ids, "group": vg, "y": vy, "p_calibrated": val["primary"]["predictions"],
                            "p_uncalibrated": val["uncalibrated"]["predictions"]}), S2 / "adequacy" / f"val_predictions_{tag}.csv.gz")
        oof = dev["oof"]
        write(oof.assign(p_calibrated=dev["primary"].cal.transform(oof["p"].to_numpy())), S2 / "adequacy" / f"dev_oof_{tag}.csv.gz")
        return {"domain": domain, "objective": oid, "phase": phase, "status": dec.status, "seconds": round(time.time() - t0, 1)}

    # ---------------------------------------------------------------- confirmation (requires frozen decisions)
    frozen = json.loads((S2 / "ADEQUACY_DECISIONS.json").read_text(encoding="utf-8"))
    fd = frozen["decisions"][f"{domain}|{oid}"]
    if fd["model_id"] != dev["primary"].model_id:
        raise RuntimeError(f"model id changed after freeze: {fd['model_id']} vs {dev['primary'].model_id}")
    decision = AQ.AdequacyDecision(**{k: fd[k] for k in ("model_id", "status", "reason", "discrimination_pass", "calibration_pass",
                                                         "support_pass", "failed_conditions", "metrics", "ci", "calibrator", "policy_version")})
    vdata, vy, vg = domain_partitions(domain)[oid]["val"]
    cdata, cy, cg = domain_partitions(domain)[oid]["conf"]
    vctx, cctx = partition_context(dev, vdata), partition_context(dev, cdata)
    cidx = np.arange(cdata.n)
    CONFLICT["flags"] = cdata.strata.get("conflict")   # label-free IAM conflicting-evidence flag (confirmation rows)
    grids = C["hp"]["policy_thresholds"]
    s2 = C["s2"]
    rows_raw, curve_rows, budget_rows, tuning_all = [], [], [], []

    def run_block(exp: str, specs, loss_b, L, M, N, cond, with_curves=False, with_budgets=False, with_targets=False,
                  with_missing=False, record=False):
        chosen, targets, tab = tune(vctx, specs, vy, vg, loss_b, L, M, N, C)
        tuning_all.extend([{**t, "experiment": exp, "condition": cond} for t in tab] +
                          [{"experiment": exp, "condition": cond, "method": m, "tau": t, "chosen": True} for m, t in chosen.items()] +
                          [{"experiment": exp, "condition": cond, "method": m, "target": g, "tau": None if t == "not_achieved" else t,
                            "target_achieved_validation": t != "not_achieved"} for (m, g), t in targets.items()])
        out = []
        by = {s.name: s for s in specs}
        for s in specs:
            trs = trajectories(cctx, s, cidx, decision, record=record and s.name in s2["trace_methods"])
            base = {"experiment": exp, "condition": cond, "start": "cold", "missing_level": 1.0, "missing_mode": "none", "shift": "none"}
            out += rows_at(trs, s, cidx, cy, cg, loss_b, [chosen[s.name]], extra=base)
            if with_targets:
                for (m, g), t in targets.items():
                    if m == s.name and t != "not_achieved":
                        out += rows_at(trs, s, cidx, cy, cg, loss_b, [t], extra={**base, "shift": g})
            if with_curves:
                curve_rows.append(curve_counts(rows_at(trs, s, cidx, cy, cg, loss_b, _dense(s, grids))).assign(experiment=exp, condition=cond))
            if with_budgets:
                for bud in range(0, cdata.m + 1):
                    budget_rows.extend(rows_at(trs, s, cidx, cy, cg, loss_b, [chosen[s.name]], budget=bud, extra={**base, "shift": f"budget<={bud}"}))
            if record and s.name in s2["trace_methods"]:
                p = S2 / "traces" / domain / s.name / f"{oid}.jsonl.gz"
                p.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(p, "wt", encoding="utf-8") as fh:
                    for tr, i in zip(trs, cidx):
                        op = truncate(tr, s.cfg, chosen[s.name])
                        fh.write(json.dumps({**tr, "tuned_threshold": chosen[s.name], "operating_point": op, "y": int(cy[i]),
                                             "group": str(cg[i]), "final_loss": loss_b.realized_loss(op["decision"], int(cy[i]))}, default=float) + "\n")
        if with_missing:
            for level in s2["missing_levels"]:
                for mode in s2["missing_modes"]:
                    starts = E.initial_sets(cctx, cidx, level, mode, C["hp"]["master_seed"])
                    for name in s2["condition_methods"]:
                        s = by[name]
                        trs = trajectories(cctx, s, cidx, decision, starts=starts)
                        out += rows_at(trs, s, cidx, cy, cg, loss_b, [chosen[name]],
                                       extra={"experiment": exp, "condition": cond, "start": "partial", "missing_level": level,
                                              "missing_mode": mode, "shift": "none"})
        return out

    primary_cond = f"fa={loss.false_assurance}|lam={lam}|mu={mu}|nu={nu}"
    # main comparison (raw acquisition policies) + curves + budgets + targets + missingness + traces
    rows_raw += run_block("primary", suite(C, loss, lam, mu, nu, "main", C["hp"]["random_baseline_seeds"]), loss, lam, mu, nu, primary_cond,
                          with_curves=True, with_budgets=True, with_targets=True, with_missing=True, record=True)
    # ablations (incl. asymmetric-loss ablation A1); "AVOI without adequacy gate" = raw AVOI
    rows_raw += run_block("ablation", suite(C, loss, lam, mu, nu, "ablation", 0), loss, lam, mu, nu, primary_cond, with_curves=True)
    # privacy weight sweep (actual mu values)
    for mu_v in s2["privacy_mu_values"]:
        sp = [s for s in suite(C, loss, lam, mu_v, nu, "main", 0) if s.name == PROPOSED]
        rows_raw += run_block("privacy", sp, loss, lam, mu_v, nu, f"fa={loss.false_assurance}|lam={lam}|mu={mu_v}|nu={nu}")
    # false-assurance penalty sweep
    for fa in s2["false_assurance_values"]:
        lf = LossMatrix(fa, lcfg["primary"]["false_non_assurance"], lcfg["primary"]["human_review"])
        sp = [s for s in suite(C, lf, lam, mu, nu, "main", 0) if s.name in s2["fa_methods"]]
        rows_raw += run_block("fa_sensitivity", sp, lf, lam, mu, nu, f"fa={fa}|lam={lam}|mu={mu}|nu={nu}", with_curves=True)

    enforced = gate_rows(rows_raw, decision, loss)
    for mode, rows in (("raw", rows_raw), ("enforced", enforced)):
        df = pd.DataFrame(rows).assign(domain=domain, objective=oid, fold=0, adequacy_status=decision.status, adequacy_mode=mode)
        write(df, raw / mode / f"episodes_{tag}.csv.gz")
    if budget_rows:
        write(pd.DataFrame(budget_rows).assign(domain=domain, objective=oid, fold=0), raw / "raw" / f"budget_{tag}.csv.gz")
    if curve_rows:
        cur = pd.concat(curve_rows).assign(domain=domain, objective=oid)
        write(cur, raw / "raw" / f"curves_{tag}.csv.gz")
        # enforced curves: gate applied to every threshold
        ce = cur.copy()
        if not decision.autonomous_allowed:
            ce["n_hr"] = ce["n"]; ce["n_assured"] = 0; ce["n_unsafe"] = 0; ce["n_correct_auto"] = 0
            ce["loss_sum"] = ce["n"] * loss.human_review; ce["cost_sum"] = 0.0; ce["privacy_sum"] = 0.0; ce["delay_sum"] = 0.0; ce["nacq_sum"] = 0
        write(ce, raw / "enforced" / f"curves_{tag}.csv.gz")
    write(pd.DataFrame(tuning_all).assign(domain=domain, objective=oid), raw / "tuning" / f"tuning_{tag}.csv.gz")
    # agent-level enforcement traces (audit): AVOI run with the gate enforced on the first 25 confirmation episodes
    spec = [s for s in suite(C, loss, lam, mu, nu, "main", 0) if s.name == PROPOSED][0]
    enf = trajectories(cctx, spec, cidx[:25], decision, record=False, mode="enforced")
    p = S2 / "traces" / domain / "AVOI_enforced_audit" / f"{oid}.jsonl.gz"
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        for tr in enf:
            fh.write(json.dumps(tr, default=float) + "\n")
    return {"domain": domain, "objective": oid, "phase": phase, "status": decision.status, "rows": len(rows_raw),
            "seconds": round(time.time() - t0, 1)}


def _dense(spec, grids):
    if spec.threshold == "risk":
        return list(np.round(np.linspace(0, 1, 81), 4))
    if spec.threshold == "confidence":
        return list(np.round(np.linspace(0.5, 1.0, 41), 4)) + [1.01]
    if spec.threshold == "symmetric":
        return list(np.round(np.linspace(0, 0.5, 41), 4))
    return [None]
