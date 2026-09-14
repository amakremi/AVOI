"""Secondary (discriminative) evidence model: calibrated logistic regression under missing evidence.

- Posterior P(Y=1 | E): logistic regression on one-hot observed outcomes + per-variable missingness indicators,
  trained on TRAINING episodes augmented with random evidence masks (so it is defined for any evidence subset),
  calibrated with CalibratedClassifierCV (isotonic when the training fold is large enough, otherwise sigmoid/Platt).
  Calibration folds are grouped by training episode, so augmented copies of one episode never straddle folds.
- Predictive P(O_a | E): one calibrated multinomial logistic regression per evidence variable a, trained on masked
  training rows in which variable a itself is always hidden.
Only training data are ever used for fitting or calibration.
"""
from __future__ import annotations

import warnings

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold


class CalibratedLogisticModel:
    def __init__(self, n_outcomes: list[int], C: float = 1.0, n_masks: int = 12, seed: int = 0,
                 isotonic_min_rows: int = 1000):
        self.K = list(n_outcomes)
        self.m = len(n_outcomes)
        self.C, self.n_masks, self.seed, self.iso_min = C, n_masks, seed, isotonic_min_rows
        self.offsets = np.concatenate([[0], np.cumsum(self.K)])
        self.dim = int(self.offsets[-1]) + self.m
        self._cache_post: dict = {}
        self._cache_pred: dict = {}

    def _encode(self, X: np.ndarray, mask: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        F = np.zeros((n, self.dim), dtype=np.float32)
        rows = np.arange(n)
        for i in range(self.m):
            obs = mask[:, i]
            F[rows[obs], self.offsets[i] + X[obs, i]] = 1.0
            F[rows[~obs], self.offsets[-1] + i] = 1.0
        return F

    def _encode_evidence(self, evidence: tuple) -> np.ndarray:
        x = np.zeros((1, self.m), dtype=int)
        mask = np.zeros((1, self.m), dtype=bool)
        for i, v in evidence:
            x[0, i], mask[0, i] = v, True
        return self._encode(x, mask)

    def _calibrated(self, n_rows: int, groups: np.ndarray, y: np.ndarray, multiclass: bool):
        base = LogisticRegression(C=self.C, max_iter=2000)
        n_groups = len(np.unique(groups))
        cv = list(GroupKFold(n_splits=min(3, n_groups)).split(np.zeros(n_rows), y, groups))
        method = "isotonic" if (n_rows >= self.iso_min and not multiclass) else "sigmoid"
        return CalibratedClassifierCV(base, method=method, cv=cv), method

    def fit(self, X: np.ndarray, y: np.ndarray) -> "CalibratedLogisticModel":
        X, y = np.asarray(X, int), np.asarray(y, int)
        rng = np.random.default_rng(self.seed)
        n = len(y)
        reps = self.n_masks
        Xr = np.repeat(X, reps, axis=0)
        yr = np.repeat(y, reps)
        groups = np.repeat(np.arange(n), reps)
        keep = rng.uniform(0, 1, size=(n * reps, 1))
        mask = rng.uniform(0, 1, size=(n * reps, self.m)) < keep
        mask[::reps] = True  # one fully observed copy per episode
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            self.post_model, self.calibration_method = self._calibrated(len(yr), groups, yr, False)
            self.post_model.fit(self._encode(Xr, mask), yr)
            self.pred_models = []
            for a in range(self.m):
                ma = mask.copy()
                ma[:, a] = False
                target = Xr[:, a]
                classes = np.unique(target)
                if len(classes) < 2:
                    self.pred_models.append(("constant", int(classes[0])))
                    continue
                mdl, _ = self._calibrated(len(target), groups, target, True)
                try:
                    mdl.fit(self._encode(Xr, ma), target)
                    self.pred_models.append(("model", mdl))
                except ValueError:  # a class too rare for grouped calibration folds -> uncalibrated LR
                    lr = LogisticRegression(C=self.C, max_iter=2000).fit(self._encode(Xr, ma), target)
                    self.pred_models.append(("model", lr))
        self._cache_post, self._cache_pred = {}, {}
        return self

    def posterior(self, evidence: tuple) -> float:
        hit = self._cache_post.get(evidence)
        if hit is None:
            hit = float(self.post_model.predict_proba(self._encode_evidence(evidence))[0, 1])
            self._cache_post[evidence] = hit
        return hit

    def predictive(self, evidence: tuple, var: int):
        key = (evidence, var)
        hit = self._cache_pred.get(key)
        if hit is None:
            kind, mdl = self.pred_models[var]
            probs = np.zeros(self.K[var])
            if kind == "constant":
                probs[mdl] = 1.0
            else:
                p = mdl.predict_proba(self._encode_evidence(tuple(e for e in evidence if e[0] != var)))[0]
                probs[mdl.classes_] = p
            probs = probs / probs.sum()
            posts = np.array([self.posterior(tuple(sorted(evidence + ((var, o),)))) for o in range(self.K[var])])
            hit = (probs, posts)
            self._cache_pred[key] = hit
        return hit

    def describe(self) -> dict:
        return {"type": "CalibratedLogistic", "C": self.C, "calibration": self.calibration_method}
