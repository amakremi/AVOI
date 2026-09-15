"""STAGE 3 / WP2 - external-domain (AIT, CERT) evidence-model development and adequacy.

Reuses Stage-2's develop/validate/adequacy machinery unchanged, adding only:
  * multi-source development pooling with leave-one-development-source-out (LODO) robustness ranking,
  * a target testbed/release split into calibration vs adequacy-validation (label-blind hash),
  * zero-shot vs target-calibrated variants,
  * a HistGradientBoosting candidate (only new model class added; still not a large neural model),
  * a feature-stability diagnostic.
The unchanged adequacy gate (config/model_adequacy.yaml) makes the final VALIDATED/RESTRICTED/UNSUPPORTED call.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from avoi import adequacy as AQ
from avoi.costs import CostModel
from avoi.datasets.common import Discretizer, codes_for
from avoi.evaluation import engine as E
from avoi.evaluation import stage2 as S
from avoi.evaluation import stage3 as S3M
from avoi.models.tan import DiscreteBayesNet


# ====================================================================================== HGB wrapper (posterior/predictive API)
class HGBEvidenceModel:
    """Thin wrapper giving a scikit HistGradientBoostingClassifier the same posterior/predictive(evidence, var) interface
    as DiscreteBayesNet, so it can be dropped into the reused agent/adequacy code unchanged. Missing evidence -> NaN
    feature (HGB's native missing-value support); predictive P(O_a|E) marginalises over training rows with matching
    partial evidence (nearest available: empirical outcome frequency conditional on the other observed variables)."""

    def __init__(self, m: int, K: list[int], **hgb_kwargs):
        self.m, self.K = m, K
        self.clf = HistGradientBoostingClassifier(**hgb_kwargs)
        self._cache: dict = {}

    def fit(self, X: np.ndarray, y: np.ndarray) -> "HGBEvidenceModel":
        self.clf.fit(X.astype(float), y)
        self._X, self._y = X, y
        self._cache = {}
        return self

    def _row(self, evidence: tuple) -> np.ndarray:
        row = np.full(self.m, np.nan)
        for i, v in evidence:
            row[i] = v
        return row

    def posterior(self, evidence: tuple) -> float:
        hit = self._cache.get(evidence)
        if hit is not None:
            return hit
        p = float(self.clf.predict_proba(self._row(evidence).reshape(1, -1))[0, 1])
        self._cache[evidence] = p
        return p

    def predictive(self, evidence: tuple, var: int):
        """Empirical P(O_var | other observed E) from training rows matching the observed subset (excluding var);
        falls back to the marginal distribution of var when no exact match exists."""
        obs = {i: v for i, v in evidence if i != var}
        mask = np.ones(len(self._y), bool)
        for i, v in obs.items():
            mask &= self._X[:, i] == v
        col = self._X[mask, var] if mask.any() else self._X[:, var]
        probs = np.bincount(col.astype(int), minlength=self.K[var]).astype(float)
        probs = probs / probs.sum() if probs.sum() else np.full(self.K[var], 1 / self.K[var])
        posts = np.array([self.posterior(tuple(sorted(evidence + ((var, o),)))) for o in range(self.K[var])])
        return probs, posts

    def describe(self) -> dict:
        return {"type": "HistGradientBoosting", "n_iter": self.clf.n_iter_}


# ====================================================================================== development (LODO robustness)
def lodo_candidates(datas: dict[str, tuple], K: list[int], polarity, C: dict) -> list[dict]:
    """datas: {source_name: (codes, y)} for every development source. For each candidate, fit on all-but-one source,
    evaluate AUROC (violation) on the held-out source; rank by worst held-out AUROC (robustness), require positive
    median PR skill, tie-break by mean log loss / Brier / ECE. Selection uses ONLY development data."""
    sources = list(datas)
    pol = C["adequacy"]
    cands = []

    def build(kind, alpha):
        if kind == "tan":
            return DiscreteBayesNet(K, alpha=alpha, tree=True)
        if kind == "nb":
            return DiscreteBayesNet(K, alpha=alpha, tree=False)
        raise ValueError(kind)

    specs = ([("tan", a) for a in C["s3"]["candidates"]["tan"]["alpha"]] +
             [("nb", a) for a in C["s3"]["candidates"]["naive_bayes"]["alpha"]] +
             [("hgb", None)])
    for kind, alpha in specs:
        fold_metrics = []
        for held in sources:
            tr_X = np.concatenate([datas[s][0] for s in sources if s != held])
            tr_y = np.concatenate([datas[s][1] for s in sources if s != held])
            te_X, te_y = datas[held]
            if len(set(te_y)) < 2:
                continue
            if kind == "hgb":
                mdl = HGBEvidenceModel(len(K), K, max_depth=C["s3"]["candidates"]["hist_gradient_boosting"]["max_depth"][0],
                                       learning_rate=C["s3"]["candidates"]["hist_gradient_boosting"]["learning_rate"][0],
                                       max_iter=C["s3"]["candidates"]["hist_gradient_boosting"]["max_iter"][0]).fit(tr_X, tr_y)
                p = np.array([mdl.posterior(tuple((j, int(te_X[i, j])) for j in range(te_X.shape[1]))) for i in range(len(te_y))])
            else:
                mdl = build(kind, alpha).fit(tr_X, tr_y)
                p = np.array([mdl.posterior(tuple((j, int(te_X[i, j])) for j in range(te_X.shape[1]))) for i in range(len(te_y))])
            m = AQ.point_metrics(te_y, p, float(np.mean(tr_y)), pol["ece_bins"])
            fold_metrics.append({"held_out": held, **m})
        if not fold_metrics:
            continue
        aurocs = [f["AUROC"] for f in fold_metrics if not np.isnan(f["AUROC"])]
        pr_skills = [f["PR_skill"] for f in fold_metrics if not np.isnan(f["PR_skill"])]
        if not aurocs:
            continue
        cands.append({"kind": kind, "alpha": alpha, "worst_fold_AUROC": min(aurocs), "median_PR_skill": float(np.median(pr_skills)) if pr_skills else float("nan"),
                     "mean_log_loss": float(np.mean([f["log_loss"] for f in fold_metrics])), "mean_Brier": float(np.mean([f["Brier"] for f in fold_metrics])),
                     "mean_ECE": float(np.mean([f["ECE"] for f in fold_metrics])), "fold_metrics": fold_metrics})
    return cands


def select_candidate(cands: list[dict]) -> dict:
    """config/stage3.yaml wp2.selection_rule: exclude invalid -> rank by worst-fold AUROC -> require median PR skill > 0
    -> tie-break within 0.01 worst-fold AUROC by log loss, then Brier, then ECE. Development data only."""
    valid = [c for c in cands if np.isfinite(c["worst_fold_AUROC"]) and c["median_PR_skill"] > 0]
    pool = valid or cands   # if none pass PR-skill>0, keep the ranking transparent (still development-only) but flagged
    best_auroc = max(c["worst_fold_AUROC"] for c in pool)
    tied = [c for c in pool if best_auroc - c["worst_fold_AUROC"] <= 0.01]
    tied.sort(key=lambda c: (c["mean_log_loss"], c["mean_Brier"], c["mean_ECE"]))
    chosen = tied[0]
    chosen["passed_pr_skill_filter"] = bool(valid)
    return chosen


def fit_final(kind, alpha, K, X, y, C):
    if kind == "hgb":
        hgb = C["s3"]["candidates"]["hist_gradient_boosting"]
        return HGBEvidenceModel(len(K), K, max_depth=hgb["max_depth"][0], learning_rate=hgb["learning_rate"][0], max_iter=hgb["max_iter"][0]).fit(X, y)
    return DiscreteBayesNet(K, alpha=alpha, tree=(kind == "tan")).fit(X, y)


# ====================================================================================== feature stability
def feature_stability(datas: dict[str, tuple], action_ids: list[str]) -> pd.DataFrame:
    """Development-only: per source (evidence action), violation-AUROC of the RAW discretised statistic per development
    partition; flags an action whose association direction reverses (both AUROC>0.6 and AUROC<0.4 observed)."""
    rows = []
    for j, aid in enumerate(action_ids):
        aurocs = {}
        for name, (X, y) in datas.items():
            x, yy = X[:, j], y
            if len(set(yy)) < 2 or len(set(x)) < 2:
                continue
            from sklearn.metrics import roc_auc_score
            aurocs[name] = float(roc_auc_score((yy == 0).astype(int), x))
        flips = bool(aurocs) and (max(aurocs.values()) - 0.5 >= 0.1) and (0.5 - min(aurocs.values()) >= 0.1)
        rows.append({"action_id": aid, **{f"AUROC_{k}": v for k, v in aurocs.items()}, "direction_reverses": flips})
    return pd.DataFrame(rows)


def build_target_split(episode_ids: np.ndarray, groups: np.ndarray, seed: int, cal_pct: int) -> np.ndarray:
    """Label-blind: True = calibration, False = adequacy_validation."""
    return np.array([S3M.hash_fraction(seed, g) < cal_pct for g in groups])
