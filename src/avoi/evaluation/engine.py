"""Nested evaluation engine shared by all experiments.

For one (domain, objective, outer fold):
  1. fit discretiser (numeric evidence), cost/delay/privacy normalisers and evidence models on the OUTER TRAINING
     episodes only; evidence-model hyperparameters chosen by inner-CV masked log loss;
  2. for every inner fold, refit everything on the inner-training part and generate FULL trajectories (no threshold)
     for every method on the inner-validation part; choose each method's threshold by the pre-declared tuning
     objective J = loss + lambda*cost + mu*privacy + nu*delay (primary loss);
  3. generate full trajectories on the held-out outer TEST episodes and evaluate operating points (tuned threshold,
     threshold grid, acquisition budgets, starting-state and shift conditions).
Labels enter only through (a) model fitting on training episodes, (b) threshold tuning on inner-validation
episodes (inside the training fold), (c) scoring of held-out decisions.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold

from avoi.agent import PolicyConfig, SequentialAssuranceAgent, truncate
from avoi.bayes_risk import SYMMETRIC_01, LossMatrix
from avoi.costs import CostModel
from avoi.datasets.common import Discretizer, ObjectiveData, codes_for, make_environment
from avoi.models.discriminative import CalibratedLogisticModel
from avoi.models.tan import DiscreteBayesNet, FixedReliabilityModel


def stable_seed(*keys) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, keys)).encode()).digest()[:8], "little") % (2**32)


# ====================================================================== method suite
@dataclass
class MethodSpec:
    name: str
    cfg: PolicyConfig
    model_kind: str            # tan | nb | lr | fixedrel
    threshold: str | None      # risk | confidence | symmetric | None
    group: str                 # baseline | proposed | ablation


def method_suite(loss: LossMatrix, lam: float, mu: float, nu: float, ig_eps: float, n_random: int,
                 model_kind: str = "tan", which: str = "main", sym_loss: LossMatrix | None = None) -> list[MethodSpec]:
    no_esc = replace(loss, allow_escalation=False)
    m = model_kind
    avoi = MethodSpec("AVOI-GRC", PolicyConfig("AVOI-GRC", "avoi", loss, lam, mu, nu, "risk"), m, "risk", "proposed")
    main = [
        avoi,
        MethodSpec("B0-AllEvidence", PolicyConfig("B0-AllEvidence", "all", loss, stop_rule="none", value_stop=False,
                                                  decision_rule="bayes_argmin"), m, None, "baseline"),
        MethodSpec("B1-FixedChecklist", PolicyConfig("B1-FixedChecklist", "fixed", loss, stop_rule="risk", value_stop=False), m, "risk", "baseline"),
        MethodSpec("B3-CheapestFirst", PolicyConfig("B3-CheapestFirst", "cheapest", loss, stop_rule="risk", value_stop=False), m, "risk", "baseline"),
        MethodSpec("B4-InformationGain", PolicyConfig("B4-InformationGain", "entropy", loss, 0.0, 0.0, 0.0, "risk",
                                                      value_eps=ig_eps), m, "risk", "baseline"),
        MethodSpec("B5-GenericVOI", PolicyConfig("B5-GenericVOI", "generic_voi", SYMMETRIC_01, lam, 0.0, 0.0, "risk",
                                                 decision_rule="argmax"), m, "symmetric", "baseline"),
        MethodSpec("B6-ConfidenceThreshold", PolicyConfig("B6-ConfidenceThreshold", "fixed", loss, stop_rule="confidence",
                                                          value_stop=False, decision_rule="confidence_hr"), m, "confidence", "baseline"),
        MethodSpec("B7-MyopicCostSensitiveVOI", PolicyConfig("B7-MyopicCostSensitiveVOI", "myopic_cs", no_esc, lam, 0.0, 0.0,
                                                             "none", decision_rule="autonomous_argmin"), m, None, "baseline"),
        MethodSpec("B7b-Lookahead2VOI", PolicyConfig("B7b-Lookahead2VOI", "lookahead2", loss, lam, mu, nu, "risk"), m, "risk", "baseline"),
    ]
    main += [MethodSpec(f"B2-Random[s{s}]", PolicyConfig(f"B2-Random[s{s}]", "random", loss, stop_rule="risk", value_stop=False, seed=s),
                        m, "risk", "baseline") for s in range(n_random)]
    if which == "main":
        return main
    sym = sym_loss or LossMatrix(2.0, 2.0, 1.0)
    abl = [
        avoi,
        MethodSpec("A1-NoAsymmetricLoss", PolicyConfig("A1-NoAsymmetricLoss", "avoi", sym, lam, mu, nu, "risk"), m, "risk", "ablation"),
        MethodSpec("A2-NoLearnedReliability", PolicyConfig("A2-NoLearnedReliability", "avoi", loss, lam, mu, nu, "risk"), "fixedrel", "risk", "ablation"),
        MethodSpec("A3-NoCost", PolicyConfig("A3-NoCost", "avoi", loss, 0.0, mu, nu, "risk"), m, "risk", "ablation"),
        MethodSpec("A4-NoPrivacy", PolicyConfig("A4-NoPrivacy", "avoi", loss, lam, 0.0, nu, "risk"), m, "risk", "ablation"),
        MethodSpec("A5-NoDelay", PolicyConfig("A5-NoDelay", "avoi", loss, lam, mu, 0.0, "risk"), m, "risk", "ablation"),
        MethodSpec("A6-NoEscalation", PolicyConfig("A6-NoEscalation", "avoi", no_esc, lam, mu, nu, "risk"), m, "risk", "ablation"),
        MethodSpec("A7-EntropyInsteadOfRisk", PolicyConfig("A7-EntropyInsteadOfRisk", "entropy", loss, lam, mu, nu, "risk"), m, "risk", "ablation"),
        MethodSpec("A8-NaiveBayesModel", PolicyConfig("A8-NaiveBayesModel", "avoi", loss, lam, mu, nu, "risk"), "nb", "risk", "ablation"),
    ]
    return abl


# ====================================================================== splits
def outer_folds(domain: str, data: ObjectiveData, y_by_unit: np.ndarray, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    idx = np.arange(data.n)
    if domain == "ait":
        return [(idx[data.groups != tb], idx[data.groups == tb]) for tb in sorted(set(data.groups))]
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    return [(tr, te) for tr, te in sgkf.split(idx, y_by_unit, data.groups)]


def inner_folds(domain: str, data: ObjectiveData, train_idx: np.ndarray, y: np.ndarray, seed: int):
    if domain == "ait":
        w0 = data.strata["w0"][train_idx]
        blocks = np.digitize(w0, np.quantile(w0, [1 / 3, 2 / 3]))  # 3 contiguous time blocks
        return [(train_idx[blocks != b], train_idx[blocks == b]) for b in sorted(set(blocks))]
    g = data.groups[train_idx]
    if domain == "iam":
        gkf = GroupKFold(n_splits=3)
        return [(train_idx[a], train_idx[b]) for a, b in gkf.split(train_idx, y[train_idx], g)]
    sgkf = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
    return [(train_idx[a], train_idx[b]) for a, b in sgkf.split(train_idx, data.strata["insider"][train_idx], g)]


# ====================================================================== models
def build_model(kind: str, K: list[int], hp: dict, polarity=None, seed: int = 0):
    if kind == "tan":
        return DiscreteBayesNet(K, alpha=hp.get("alpha", 1.0), tree=True)
    if kind == "nb":
        return DiscreteBayesNet(K, alpha=hp.get("alpha", 1.0), tree=False)
    if kind == "lr":
        return CalibratedLogisticModel(K, C=hp.get("C", 1.0), n_masks=hp.get("n_masks", 12), seed=seed,
                                       isotonic_min_rows=hp.get("isotonic_min_rows", 1000))
    if kind == "fixedrel":
        return FixedReliabilityModel(K, polarity)
    raise ValueError(kind)


def masked_log_loss(model, codes: np.ndarray, y: np.ndarray, n_masks: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    ll = []
    for i in range(len(y)):
        for _ in range(n_masks):
            keep = rng.uniform()
            ev = tuple((j, int(codes[i, j])) for j in range(codes.shape[1]) if rng.uniform() < keep)
            p = min(max(model.posterior(ev), 1e-6), 1 - 1e-6)
            ll.append(-(y[i] * math.log(p) + (1 - y[i]) * math.log(1 - p)))
    return float(np.mean(ll))


def select_hyperparameters(kind: str, grid: dict, data: ObjectiveData, y, folds, K, polarity, n_masks, seed) -> dict:
    if kind == "fixedrel":
        return {}
    keys = [k for k in grid if isinstance(grid[k], list)]
    fixed = {k: v for k, v in grid.items() if not isinstance(v, list)}
    combos = [dict(zip(keys, vals)) for vals in np.array(np.meshgrid(*[grid[k] for k in keys])).T.reshape(-1, len(keys))]
    best, best_score = None, np.inf
    for c in combos:
        hp = {**fixed, **{k: float(v) for k, v in c.items()}}
        scores = []
        for tr, va in folds:
            if len(set(y[tr])) < 2:
                continue
            # discretiser refitted on the inner-training part (strict nesting)
            codes = codes_for(data, Discretizer().fit(data.values[tr]) if data.kind == "numeric" else None)
            mdl = build_model(kind, K, hp, polarity, seed).fit(codes[tr], y[tr])
            scores.append(masked_log_loss(mdl, codes[va], y[va], n_masks, seed))
        s = float(np.mean(scores)) if scores else np.inf
        if s < best_score:
            best, best_score = hp, s
    return {**(best or fixed), "_inner_masked_log_loss": best_score}


# ====================================================================== fold context
@dataclass
class FoldContext:
    data: ObjectiveData
    codes: np.ndarray
    K: list[int]
    cost: CostModel
    models: dict
    hps: dict
    train_idx: np.ndarray
    mi_rank: list[int]


def mutual_information_rank(codes, y, K) -> list[int]:
    mis = []
    for j in range(codes.shape[1]):
        joint = np.zeros((2, K[j])) + 1e-9
        np.add.at(joint, (y, codes[:, j]), 1.0)
        joint /= joint.sum()
        py, px = joint.sum(1, keepdims=True), joint.sum(0, keepdims=True)
        mis.append(float((joint * np.log(joint / (py * px))).sum()))
    return list(np.argsort(mis)[::-1])


def make_context(data: ObjectiveData, y: np.ndarray, train_idx: np.ndarray, model_kinds: list[str], grids: dict,
                 regime: str, inner: list | None, n_masks: int, seed: int, hps: dict | None = None) -> FoldContext:
    disc = Discretizer().fit(data.values[train_idx]) if data.kind == "numeric" else None
    codes = codes_for(data, disc)
    K = [len(a.outcomes) for a in data.actions]
    cost = CostModel.fit(data.records[train_idx], data.bytes_[train_idx], data.seconds[train_idx],
                         data.n_categories()[train_idx], regime)
    polarity = [list(a.polarity) for a in data.actions]
    hps = dict(hps or {})
    models = {}
    for kind in model_kinds:
        if kind not in hps:
            grid = grids.get({"tan": "tan", "nb": "naive_bayes", "lr": "calibrated_logistic"}.get(kind, ""), {})
            hps[kind] = select_hyperparameters(kind, grid, data, y, inner, K, polarity, n_masks, seed) if (inner and grid) else {}
        models[kind] = build_model(kind, K, hps[kind], polarity, seed).fit(codes[train_idx], y[train_idx])
    return FoldContext(data, codes, K, cost, models, hps, train_idx, mutual_information_rank(codes[train_idx], y[train_idx], K))


# ====================================================================== starting states and shifts
def initial_sets(ctx: FoldContext, idx: np.ndarray, level: float, mode: str, seed: int) -> list[set]:
    """level = fraction of actions NOT yet acquired at t=0 (1.0 = cold start)."""
    m = ctx.data.m
    n_missing = int(round(level * m))
    n_pre = m - n_missing
    out = []
    if n_pre <= 0:
        return [set() for _ in idx]
    for i in idx:
        rng = np.random.default_rng(stable_seed(seed, mode, level, ctx.data.episode_ids[i]))
        if mode == "mcar":
            pre = set(rng.choice(m, size=n_pre, replace=False).tolist())
        elif mode == "block":
            types = sorted({a.source_type for a in ctx.data.actions})
            rng.shuffle(types)
            hidden = []
            for t in types:
                hidden += [j for j, a in enumerate(ctx.data.actions) if a.source_type == t]
                if len(hidden) >= n_missing:
                    break
            hidden = hidden[:n_missing]
            pre = set(range(m)) - set(hidden)
        elif mode == "adversarial":
            pre = set(range(m)) - set(ctx.mi_rank[:n_missing])
        else:
            raise ValueError(mode)
        out.append(pre)
    return out


def degradation_overrides(ctx: FoldContext, idx: np.ndarray, source_type: str, rate: float, seed: int) -> list[dict]:
    tr = ctx.train_idx
    marg = [np.bincount(ctx.codes[tr, j], minlength=ctx.K[j]) / len(tr) for j in range(ctx.data.m)]
    targets = [j for j, a in enumerate(ctx.data.actions) if a.source_type == source_type]
    out = []
    for i in idx:
        rng = np.random.default_rng(stable_seed(seed, "degrade", source_type, ctx.data.episode_ids[i]))
        ov = {}
        for j in targets:
            if rng.uniform() < rate:
                ov[j] = int(rng.choice(ctx.K[j], p=marg[j]))
        out.append(ov)
    return out


# ====================================================================== trajectories & operating points
def run_trajectories(ctx: FoldContext, spec: MethodSpec, idx: np.ndarray, starts: list[set] | None = None,
                     overrides: list[dict] | None = None, record: bool = False, cost: CostModel | None = None,
                     model=None) -> list[dict]:
    cost = cost or ctx.cost
    model = model or ctx.models[spec.model_kind]
    cfg = replace(spec.cfg, tau=None)
    agent = SequentialAssuranceAgent(cfg, model, cost, ctx.data.objective_id, record_candidates=record)
    out = []
    for k, i in enumerate(idx):
        env = make_environment(ctx.data, i, ctx.codes[i], cost, starts[k] if starts else set(),
                               overrides[k] if overrides else None)
        tr = agent.run(env)
        if not record:
            tr.pop("final_candidates", None)
        out.append(tr)
    return out


def points(traces: list[dict], spec: MethodSpec, idx: np.ndarray, y: np.ndarray, eval_loss: LossMatrix,
           taus: list, budget: int | None = None) -> list[dict]:
    rows = []
    for tau in taus:
        for tr, i in zip(traces, idx):
            op = truncate(tr, spec.cfg, tau, budget)
            rows.append({"episode_index": int(i), "tau": tau, "y": int(y[i]), "decision": op["decision"],
                         "belief": op["belief"], "n_acq": op["n_acquisitions"], "cost": op["cost"], "delay": op["delay"],
                         "seconds": op["seconds"], "records": op["records"], "bytes": op["bytes"],
                         "privacy": len(op["privacy_categories"]) / 10.0, "reason": op["reason"],
                         "loss": eval_loss.realized_loss(op["decision"], int(y[i])), "budget": budget})
    return rows


def tau_grid(spec: MethodSpec, grids: dict) -> list:
    return {"risk": grids["risk_tau"], "confidence": grids["confidence_theta"], "symmetric": grids["symmetric_tau"],
            None: [None]}[spec.threshold]


def objective_J(df: pd.DataFrame, lam, mu, nu) -> float:
    return float(df["loss"].mean() + lam * df["cost"].mean() + mu * df["privacy"].mean() + nu * df["delay"].mean())

