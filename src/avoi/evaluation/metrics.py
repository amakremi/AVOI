"""Evaluation metrics and statistical procedures.

Safety:      UAR = #(Assured & Y=0)/#(Y=0);  FAR_A = #(Assured & Y=0)/#(Assured);  expected decision loss.
Utility:     acquisitions (mean/median), normalised cost, delay, retrieval seconds, privacy exposure, escalation rate,
             autonomous coverage, acquisitions to correct autonomous determination.
Predictive:  on the final posterior belief b (predict 'satisfied' iff b >= 0.5); the POSITIVE class for precision,
             recall, F1 is VIOLATION (Y=0); specificity is recall of the satisfied class; AUROC/AUPRC use 1-b as the
             violation score. Macro F1 averages the F1 of both classes.
Calibration: Brier, log loss, ECE (10 equal-width bins), calibration slope/intercept (logistic recalibration).
Uncertainty: stratified (by Y) bootstrap percentile CIs, >= 5,000 resamples.
Paired tests: Wilcoxon signed-rank (+ rank-biserial effect), exact McNemar, sign-flip permutation, Holm, Friedman.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

N_BOOT = 5000


# ---------------------------------------------------------------------------------------------- point metrics
def decision_metrics(df: pd.DataFrame) -> dict:
    y = df["y"].to_numpy()
    d = df["decision"].to_numpy()
    b = df["belief"].to_numpy(dtype=float)
    viol = y == 0
    assured = d == "Assured"
    unsafe = assured & viol
    auto = d != "HumanReview"
    pred_sat = b >= 0.5
    tp = int((~pred_sat & viol).sum()); fn = int((pred_sat & viol).sum())
    tn = int((pred_sat & ~viol).sum()); fp = int((~pred_sat & ~viol).sum())
    prec = tp / (tp + fp) if tp + fp else np.nan
    rec = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    f1_v = 2 * prec * rec / (prec + rec) if (prec and rec and not np.isnan(prec) and not np.isnan(rec)) else 0.0
    prec_s = tn / (tn + fn) if tn + fn else np.nan
    f1_s = 2 * prec_s * spec / (prec_s + spec) if (prec_s and spec and not np.isnan(prec_s) and not np.isnan(spec)) else 0.0
    den = np.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    mcc = (tp * tn - fp * fn) / den if den > 0 else 0.0
    correct_auto = ((d == "Assured") & ~viol) | ((d == "NotAssured") & viol)
    out = {
        "n": len(y), "n_violated": int(viol.sum()), "prevalence_violated": float(viol.mean()),
        "UAR": unsafe.sum() / viol.sum() if viol.sum() else np.nan,
        "FAR_A": unsafe.sum() / assured.sum() if assured.sum() else np.nan,
        "false_non_assurance_rate": ((d == "NotAssured") & ~viol).sum() / (~viol).sum() if (~viol).sum() else np.nan,
        "expected_loss": float(df["loss"].mean()),
        "coverage": float(auto.mean()), "escalation_rate": float((d == "HumanReview").mean()),
        "autonomous_error_rate": float((auto & ~correct_auto).sum() / auto.sum()) if auto.sum() else np.nan,
        "mean_acquisitions": float(df["n_acq"].mean()), "median_acquisitions": float(df["n_acq"].median()),
        "total_acquisitions": int(df["n_acq"].sum()),
        "normalized_cost": float(df["cost"].mean()), "delay": float(df["delay"].mean()),
        "retrieval_seconds": float(df["seconds"].mean()), "privacy_exposure": float(df["privacy"].mean()),
        "acq_to_correct_determination": float(df.loc[correct_auto, "n_acq"].mean()) if correct_auto.any() else np.nan,
        "balanced_accuracy": np.nanmean([rec, spec]), "macro_f1": (f1_v + f1_s) / 2, "precision_violation": prec,
        "recall_violation": rec, "specificity": spec, "MCC": mcc,
    }
    if len(set(y)) == 2:
        out["AUROC"] = roc_auc_score(viol.astype(int), 1 - b)
        out["AUPRC"] = average_precision_score(viol.astype(int), 1 - b)
    else:
        out["AUROC"] = out["AUPRC"] = np.nan
    out.update(calibration_metrics(y, b))
    return out


def calibration_metrics(y: np.ndarray, p: np.ndarray, bins: int = 10) -> dict:
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, int)
    brier = float(np.mean((p - y) ** 2))
    ll = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    ece = float(sum(abs(p[idx == k].mean() - y[idx == k].mean()) * (idx == k).mean() for k in range(bins) if (idx == k).any()))
    slope = intercept = np.nan
    if len(set(y)) == 2:
        logit = np.log(p / (1 - p)).reshape(-1, 1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit, y)
        slope, intercept = float(lr.coef_[0, 0]), float(lr.intercept_[0])
    return {"Brier": brier, "log_loss": ll, "ECE": ece, "calibration_slope": slope, "calibration_intercept": intercept}


def reliability_table(y, p, bins: int = 10, n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    p, y = np.asarray(p, float), np.asarray(y, int)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(bins):
        m = idx == k
        if not m.any():
            continue
        yk = y[m]
        boots = rng.choice(yk, size=(n_boot, len(yk))).mean(1)
        rows.append({"bin": k, "mean_predicted": p[m].mean(), "observed": yk.mean(), "n": int(m.sum()),
                     "ci_low": np.quantile(boots, 0.025), "ci_high": np.quantile(boots, 0.975)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- bootstrap
def stratified_indices(strata: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(strata)
    out = np.empty((n_boot, n), dtype=np.int64)
    pos = 0
    for s in np.unique(strata):
        members = np.flatnonzero(strata == s)
        k = len(members)
        out[:, pos:pos + k] = members[rng.integers(0, k, size=(n_boot, k))]
        pos += k
    return out


FAST = {  # metric -> function(arrays, index matrix) vectorised over bootstrap rows
    "UAR": lambda a, I: _ratio(a["unsafe"][I], a["viol"][I]),
    "FAR_A": lambda a, I: _ratio(a["unsafe"][I], a["assured"][I]),
    "expected_loss": lambda a, I: a["loss"][I].mean(1),
    "coverage": lambda a, I: a["auto"][I].mean(1),
    "escalation_rate": lambda a, I: a["hr"][I].mean(1),
    "mean_acquisitions": lambda a, I: a["n_acq"][I].mean(1),
    "normalized_cost": lambda a, I: a["cost"][I].mean(1),
    "privacy_exposure": lambda a, I: a["privacy"][I].mean(1),
    "delay": lambda a, I: a["delay"][I].mean(1),
    "Brier": lambda a, I: ((a["belief"][I] - a["y"][I]) ** 2).mean(1),
    "balanced_accuracy": lambda a, I: 0.5 * (_ratio(a["tp"][I], a["viol"][I]) + _ratio(a["tn"][I], 1 - a["viol"][I])),
}


def _ratio(num, den):
    s = den.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(s > 0, num.sum(1) / np.where(s > 0, s, 1), np.nan)


def arrays(df: pd.DataFrame) -> dict:
    y = df["y"].to_numpy()
    d = df["decision"].to_numpy()
    b = df["belief"].to_numpy(float)
    viol = (y == 0).astype(float)
    a = {"y": y.astype(float), "viol": viol, "belief": b, "loss": df["loss"].to_numpy(float),
         "assured": (d == "Assured").astype(float), "hr": (d == "HumanReview").astype(float),
         "auto": (d != "HumanReview").astype(float), "n_acq": df["n_acq"].to_numpy(float),
         "cost": df["cost"].to_numpy(float), "privacy": df["privacy"].to_numpy(float), "delay": df["delay"].to_numpy(float),
         "tp": ((b < 0.5) & (y == 0)).astype(float), "tn": ((b >= 0.5) & (y == 1)).astype(float)}
    if "unsafe_frac" in df:
        a["unsafe"] = df["unsafe_frac"].to_numpy(float)
    else:
        a["unsafe"] = a["assured"] * viol
    return a


def bootstrap_ci(df: pd.DataFrame, metrics: list[str], n_boot: int = N_BOOT, seed: int = 0, strata=None) -> dict:
    a = arrays(df)
    strata = df["y"].to_numpy() if strata is None else strata
    I = stratified_indices(np.asarray(strata), n_boot, seed)
    out = {}
    for m in metrics:
        vals = FAST[m](a, I)
        vals = vals[~np.isnan(vals)]
        out[m] = (float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))) if len(vals) else (np.nan, np.nan)
    return out


def paired_bootstrap_diff(x: np.ndarray, z: np.ndarray, strata: np.ndarray, n_boot: int = N_BOOT, seed: int = 0,
                          denom: np.ndarray | None = None) -> tuple[float, float, float]:
    """Mean (or ratio when denom given) difference x - z with stratified paired bootstrap CI."""
    I = stratified_indices(strata, n_boot, seed)
    if denom is None:
        diffs = (x[I] - z[I]).mean(1)
        est = float((x - z).mean())
    else:
        diffs = _ratio(x[I], denom[I]) - _ratio(z[I], denom[I])
        est = float(x.sum() / denom.sum() - z.sum() / denom.sum())
    diffs = diffs[~np.isnan(diffs)]
    return est, float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))


# ---------------------------------------------------------------------------------------------- tests
def wilcoxon_paired(x: np.ndarray, z: np.ndarray) -> dict:
    d = np.asarray(x, float) - np.asarray(z, float)
    nz = d[d != 0]
    if len(nz) == 0:
        return {"test": "wilcoxon", "statistic": 0.0, "p": 1.0, "effect_rank_biserial": 0.0, "n_nonzero": 0}
    res = stats.wilcoxon(nz, zero_method="wilcox", alternative="two-sided", method="auto")
    ranks = stats.rankdata(np.abs(nz))
    w_pos, w_neg = ranks[nz > 0].sum(), ranks[nz < 0].sum()
    return {"test": "wilcoxon", "statistic": float(res.statistic), "p": float(res.pvalue),
            "effect_rank_biserial": float((w_pos - w_neg) / (w_pos + w_neg)), "n_nonzero": int(len(nz))}


def mcnemar_exact(a_err: np.ndarray, b_err: np.ndarray) -> dict:
    a_err, b_err = np.asarray(a_err, bool), np.asarray(b_err, bool)
    b = int((a_err & ~b_err).sum())
    c = int((~a_err & b_err).sum())
    p = float(stats.binomtest(b, b + c, 0.5).pvalue) if b + c > 0 else 1.0
    # effect: odds ratio of discordant pairs with Haldane correction
    return {"test": "mcnemar_exact", "statistic": float(min(b, c)), "p": p, "discordant_method_only": b,
            "discordant_comparator_only": c, "effect_discordant_odds_ratio": (b + 0.5) / (c + 0.5)}


def signflip_permutation(x: np.ndarray, z: np.ndarray, n_perm: int = 20000, seed: int = 0) -> dict:
    d = np.asarray(x, float) - np.asarray(z, float)
    rng = np.random.default_rng(seed)
    obs = abs(d.mean())
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    null = np.abs((signs * d).mean(1))
    p = float((np.sum(null >= obs - 1e-12) + 1) / (n_perm + 1))
    return {"test": "signflip_permutation", "statistic": float(d.mean()), "p": p,
            "effect_mean_difference": float(d.mean())}


def holm(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def friedman(block_table: pd.DataFrame) -> dict:
    """block_table: rows = blocks (e.g. objective x fold), columns = methods, values = metric."""
    t = block_table.dropna(axis=0)
    if t.shape[0] < 2 or t.shape[1] < 3:
        return {"test": "friedman", "statistic": np.nan, "p": np.nan, "n_blocks": int(t.shape[0]), "k": int(t.shape[1])}
    res = stats.friedmanchisquare(*[t[c].to_numpy() for c in t.columns])
    n, k = t.shape
    kendall_w = float(res.statistic / (n * (k - 1)))
    return {"test": "friedman", "statistic": float(res.statistic), "p": float(res.pvalue), "n_blocks": int(n), "k": int(k),
            "effect_kendall_w": kendall_w}


def random_effects_meta(effects: list[float], variances: list[float]) -> dict:
    """DerSimonian-Laird random-effects pooled estimate with heterogeneity (tau^2, I^2)."""
    e, v = np.asarray(effects, float), np.asarray(variances, float)
    w = 1 / v
    fixed = (w * e).sum() / w.sum()
    Q = float((w * (e - fixed) ** 2).sum())
    df = len(e) - 1
    c = w.sum() - (w ** 2).sum() / w.sum()
    tau2 = max(0.0, (Q - df) / c) if c > 0 else 0.0
    wr = 1 / (v + tau2)
    pooled = float((wr * e).sum() / wr.sum())
    se = float(np.sqrt(1 / wr.sum()))
    return {"pooled": pooled, "ci_low": pooled - 1.96 * se, "ci_high": pooled + 1.96 * se, "tau2": tau2, "Q": Q,
            "I2": max(0.0, (Q - df) / Q) if Q > 0 else 0.0, "k": len(e)}
