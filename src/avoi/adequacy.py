"""Evidence-model adequacy: a SAFETY / APPLICABILITY CONDITION for autonomous AVOI (Stage 2).

AVOI values evidence through P(Y|E) and P(O_a|E). This module decides - on data that is independent of model fitting,
calibration and final confirmation testing - whether a frozen evidence model is adequate for autonomous
assurance-value reasoning. It does NOT change the AVOI formula; it only determines whether autonomous operation is
permitted (VALIDATED) or withheld (RESTRICTED / UNSUPPORTED -> HumanReview).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
EPS = 1e-6
VALIDATED, RESTRICTED, UNSUPPORTED = "VALIDATED", "RESTRICTED", "UNSUPPORTED"
REASON = {RESTRICTED: "MODEL_ADEQUACY_RESTRICTED", UNSUPPORTED: "MODEL_ADEQUACY_UNSUPPORTED"}
SUPPORT_REASON = "INSUFFICIENT_ADEQUACY_SAMPLE_SUPPORT"


def load_policy(path: str = "config/model_adequacy.yaml") -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


# ====================================================================================== calibrators
def _logit(p):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _fit_logistic(X: np.ndarray, y: np.ndarray, iters: int = 50, ridge: float = 1e-6) -> np.ndarray:
    """Newton-Raphson logistic regression with intercept (X without intercept column)."""
    Xd = np.column_stack([np.ones(len(X)), X])
    w = np.zeros(Xd.shape[1])
    for _ in range(iters):
        z = np.clip(Xd @ w, -35, 35)
        p = 1 / (1 + np.exp(-z))
        g = Xd.T @ (y - p)
        H = (Xd * (p * (1 - p))[:, None]).T @ Xd + ridge * np.eye(Xd.shape[1])
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
        w += step
        if np.max(np.abs(step)) < 1e-8:
            break
    return w


class Calibrator:
    def __init__(self, method: str):
        self.method = method
        self.params: dict = {}

    def fit(self, p: np.ndarray, y: np.ndarray) -> "Calibrator":
        p, y = np.clip(np.asarray(p, float), EPS, 1 - EPS), np.asarray(y, float)
        if self.method == "sigmoid":
            w = _fit_logistic(_logit(p)[:, None], y)
            self.params = {"a_intercept": float(w[0]), "b_slope": float(w[1])}
        elif self.method == "beta":
            w = _fit_logistic(np.column_stack([np.log(p), -np.log(1 - p)]), y)
            self.params = {"c_intercept": float(w[0]), "a_logp": float(w[1]), "b_log1mp": float(w[2])}
        elif self.method == "isotonic":
            self._iso = IsotonicRegression(y_min=EPS, y_max=1 - EPS, out_of_bounds="clip").fit(p, y)
            self.params = {"x_thresholds": self._iso.X_thresholds_.tolist(), "y_thresholds": self._iso.y_thresholds_.tolist()}
        elif self.method != "none":
            raise ValueError(self.method)
        return self

    def transform(self, p):
        scalar = np.isscalar(p)
        p = np.clip(np.atleast_1d(np.asarray(p, float)), EPS, 1 - EPS)
        if self.method == "none":
            out = p
        elif self.method == "sigmoid":
            out = 1 / (1 + np.exp(-(self.params["a_intercept"] + self.params["b_slope"] * _logit(p))))
        elif self.method == "beta":
            z = self.params["c_intercept"] + self.params["a_logp"] * np.log(p) + self.params["b_log1mp"] * (-np.log(1 - p))
            out = 1 / (1 + np.exp(-np.clip(z, -35, 35)))
        else:
            out = np.interp(p, self.params["x_thresholds"], self.params["y_thresholds"])
        out = np.clip(out, EPS, 1 - EPS)
        return float(out[0]) if scalar else out


def select_calibrator(p: np.ndarray, y: np.ndarray, groups: np.ndarray, candidates: list[str], n_folds: int = 5,
                      seed: int = 0) -> tuple[str, dict]:
    """Group cross-validated log loss of each calibrator on DEVELOPMENT out-of-fold predictions only."""
    ug = np.unique(groups)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(ug)
    fold_of = {g: i % min(n_folds, len(ug)) for i, g in enumerate(perm)}
    f = np.array([fold_of[g] for g in groups])
    scores = {}
    for m in candidates:
        ll = []
        for k in range(f.max() + 1):
            tr, te = f != k, f == k
            if te.sum() == 0 or len(np.unique(y[tr])) < 2:
                continue
            q = Calibrator(m).fit(p[tr], y[tr]).transform(p[te])
            ll.append(float(-np.mean(y[te] * np.log(q) + (1 - y[te]) * np.log(1 - q))))
        scores[m] = float(np.mean(ll)) if ll else np.inf
    best = min(candidates, key=lambda m: (round(scores[m], 10), candidates.index(m)))
    return best, scores


class CalibratedEvidenceModel:
    """Wraps an evidence model: calibrated P(Y=1|E) = g(P_model(Y=1|E)); predictive outcome probabilities unchanged,
    post-outcome posteriors mapped through the same frozen calibrator g."""

    def __init__(self, base, calibrator: Calibrator, model_id: str):
        self.base, self.cal, self.model_id = base, calibrator, model_id
        self.K = base.K
        self._post: dict = {}

    def posterior(self, evidence: tuple) -> float:
        v = self._post.get(evidence)
        if v is None:
            v = float(self.cal.transform(self.base.posterior(evidence)))
            self._post[evidence] = v
        return v

    def predictive(self, evidence: tuple, var: int):
        probs, posts = self.base.predictive(evidence, var)
        return probs, self.cal.transform(np.asarray(posts))

    def describe(self) -> dict:
        return {**self.base.describe(), "calibrator": self.cal.method, "calibrator_params": self.cal.params, "model_id": self.model_id}


# ====================================================================================== metrics
def point_metrics(y: np.ndarray, p: np.ndarray, reference_prevalence_satisfied: float, bins: int = 10) -> dict:
    """y: 1 satisfied / 0 violated; p: P(Y=1|E). Discrimination uses violation as the positive class."""
    y = np.asarray(y, int)
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    viol = (y == 0).astype(int)
    prev = float(viol.mean())
    out = {"n": int(len(y)), "n_violated": int(viol.sum()), "n_satisfied": int((y == 1).sum()), "prevalence_violated": prev}
    if 0 < viol.sum() < len(y):
        out["AUROC"] = float(roc_auc_score(viol, 1 - p))
        out["AUPRC"] = float(average_precision_score(viol, 1 - p))
        out["PR_skill"] = float((out["AUPRC"] - prev) / (1 - prev)) if prev < 1 else float("nan")
    else:
        out["AUROC"] = out["AUPRC"] = out["PR_skill"] = float("nan")
    pred_viol = p < 0.5
    tp = int((pred_viol & (viol == 1)).sum()); fn = int((~pred_viol & (viol == 1)).sum())
    tn = int((~pred_viol & (viol == 0)).sum()); fp = int((pred_viol & (viol == 0)).sum())
    sens = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    den = math.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    out.update({"sensitivity_violated": sens, "specificity": spec, "balanced_accuracy": float(np.nanmean([sens, spec])),
                "MCC": float((tp * tn - fp * fn) / den) if den > 0 else 0.0})
    brier = float(np.mean((p - y) ** 2))
    ref = float(np.mean((reference_prevalence_satisfied - y) ** 2))
    out.update({"Brier": brier, "Brier_reference": ref, "BSS": float(1 - brier / ref) if ref > 0 else float("nan"),
                "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))})
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    out["ECE"] = float(sum(abs(p[idx == k].mean() - y[idx == k].mean()) * (idx == k).mean() for k in range(bins) if (idx == k).any()))
    if 0 < y.sum() < len(y):
        w = _fit_logistic(_logit(p)[:, None], y.astype(float))
        out["calibration_intercept"], out["calibration_slope"] = float(w[0]), float(w[1])
    else:
        out["calibration_intercept"] = out["calibration_slope"] = float("nan")
    return out


CI_METRICS = ["AUROC", "AUPRC", "PR_skill", "MCC", "Brier", "BSS", "ECE", "calibration_slope", "calibration_intercept"]


def group_bootstrap(y, p, groups, reference_prevalence_satisfied: float, n: int, seed: int, confidence: float = 0.95,
                    bins: int = 10) -> dict:
    y, p, groups = np.asarray(y, int), np.asarray(p, float), np.asarray(groups)
    ug = np.unique(groups)
    members = [np.flatnonzero(groups == g) for g in ug]
    rng = np.random.default_rng(seed)
    vals = {m: [] for m in CI_METRICS}
    skipped = 0
    for _ in range(n):
        pick = rng.integers(0, len(ug), len(ug))
        idx = np.concatenate([members[i] for i in pick])
        yy, pp = y[idx], p[idx]
        if len(np.unique(yy)) < 2:
            skipped += 1
            continue
        m = point_metrics(yy, pp, reference_prevalence_satisfied, bins)
        for k in CI_METRICS:
            if not np.isnan(m[k]):
                vals[k].append(m[k])
    a = (1 - confidence) / 2
    ci = {k: ((float(np.quantile(v, a)), float(np.quantile(v, 1 - a))) if len(v) else (float("nan"), float("nan"))) for k, v in vals.items()}
    return {"ci": ci, "n_resamples": n, "skipped_single_class": skipped, "n_groups": int(len(ug))}


# ====================================================================================== policy
@dataclass
class AdequacyDecision:
    model_id: str
    status: str
    reason: str
    discrimination_pass: bool
    calibration_pass: bool
    support_pass: bool
    failed_conditions: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    ci: dict = field(default_factory=dict)
    calibrator: str = "none"
    policy_version: str = ""

    @property
    def autonomous_allowed(self) -> bool:
        return self.status == VALIDATED

    @property
    def gate_reason(self) -> str | None:
        return None if self.autonomous_allowed else REASON[self.status]

    def compact(self) -> dict:
        keys = ["AUROC", "PR_skill", "BSS", "ECE", "calibration_slope", "n_violated", "n_satisfied"]
        return {k: self.metrics.get(k) for k in keys} | {"AUROC_CI_low": self.ci.get("AUROC", [None])[0],
                                                          "PR_skill_CI_low": self.ci.get("PR_skill", [None])[0]}


def decide(model_id: str, metrics: dict, boot: dict, policy: dict, calibrator: str, overrides: dict | None = None,
           groups_with_violation: int | None = None) -> AdequacyDecision:
    pr = {k: dict(v) for k, v in policy["primary"].items()}
    for (sec, key), val in (overrides or {}).items():
        pr[sec][key] = val
    d, c, s = pr["discrimination"], pr["calibration"], pr["support"]
    ci = boot["ci"]
    failed = []
    support_ok = (metrics["n_violated"] >= s["min_violated_cases"] and metrics["n_satisfied"] >= s["min_satisfied_cases"]
                  and boot["n_groups"] >= s["min_groups"]
                  and (groups_with_violation is None or groups_with_violation >= s["min_groups_with_violation"]))
    if not support_ok:
        failed.append("sample_support")
    auc_lo, prs_lo = ci["AUROC"][0], ci["PR_skill"][0]
    disc_ok = (not np.isnan(auc_lo) and auc_lo > d["auroc_ci_lower_gt"]) and (not np.isnan(prs_lo) and prs_lo > d["pr_skill_ci_lower_gt"])
    if not disc_ok:
        failed.append("discrimination")
    slope = metrics["calibration_slope"]
    cal_ok = (metrics["BSS"] > c["bss_gt"] and metrics["ECE"] <= c["ece_le"] and not np.isnan(slope)
              and c["slope_min"] <= slope <= c["slope_max"])
    if not cal_ok:
        failed.append("calibration")
    if not support_ok:
        status, reason = RESTRICTED, SUPPORT_REASON
    elif not disc_ok:
        status, reason = UNSUPPORTED, REASON[UNSUPPORTED]
    elif not cal_ok:
        status, reason = RESTRICTED, REASON[RESTRICTED]
    else:
        status, reason = VALIDATED, "ALL_PRIMARY_ADEQUACY_CONDITIONS_MET"
    return AdequacyDecision(model_id, status, reason, disc_ok, cal_ok, support_ok, failed, metrics, ci, calibrator,
                            policy["policy_version"])


class AdequacyGate:
    """Frozen gate: model_id -> AdequacyDecision. Determined before confirmation testing and never updated from it."""

    def __init__(self, decisions: dict[str, AdequacyDecision], mode: str = "enforced"):
        if mode not in ("enforced", "diagnostic"):
            raise ValueError(mode)
        self.decisions, self.mode = decisions, mode

    def decision(self, model_id: str) -> AdequacyDecision:
        return self.decisions[model_id]

    def status(self, model_id: str) -> str:
        return self.decisions[model_id].status
