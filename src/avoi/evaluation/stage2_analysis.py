"""Stage-2 analysis utilities (metrics with group-aware bootstrap, action-selection statistics, gate effects)."""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from avoi.bayes_risk import HUMAN_REVIEW, LossMatrix


# ---------------------------------------------------------------------------------------------- core rates
def uar_counts(df: pd.DataFrame) -> dict:
    """UAR numerator/denominator. Denominator = ALL evaluated episodes with Y=0 (HumanReview included)."""
    viol = df["y"] == 0
    assured = df["decision"] == "Assured"
    return {"unsafe": int((assured & viol).sum()), "n_violated": int(viol.sum()), "n_assured": int(assured.sum()),
            "n": int(len(df)), "n_autonomous": int((df["decision"] != HUMAN_REVIEW).sum())}


def rates(df: pd.DataFrame) -> dict:
    c = uar_counts(df)
    return {"UAR": c["unsafe"] / c["n_violated"] if c["n_violated"] else np.nan,
            "FAA": c["unsafe"] / c["n_assured"] if c["n_assured"] else np.nan,
            "coverage": c["n_autonomous"] / c["n"] if c["n"] else np.nan,
            "human_review_rate": 1 - c["n_autonomous"] / c["n"] if c["n"] else np.nan, **c}


def group_bootstrap_ci(df: pd.DataFrame, fn, group_col: str = "group", n: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Point estimate and percentile CI of fn(df) resampling GROUPS (scenario family / user / time block) with replacement."""
    groups = df[group_col].astype(str).to_numpy()
    ug = np.unique(groups)
    idx_by = {g: np.flatnonzero(groups == g) for g in ug}
    rng = np.random.default_rng(seed)
    est = fn(df)
    vals = []
    for _ in range(n):
        pick = rng.choice(ug, size=len(ug), replace=True)
        sub = df.iloc[np.concatenate([idx_by[g] for g in pick])]
        v = fn(sub)
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            vals.append(v)
    if not vals:
        return est, np.nan, np.nan
    return est, float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def paired_group_bootstrap(df_a: pd.DataFrame, df_b: pd.DataFrame, col: str, n: int = 2000, seed: int = 0, ratio_den: str | None = None):
    """Mean (or ratio) difference a-b on identical episodes, group bootstrap."""
    m = df_a.merge(df_b, on=["objective", "episode_id", "y", "group"], suffixes=("_a", "_b"))
    if ratio_den is None:
        fn = lambda d: float((d[f"{col}_a"] - d[f"{col}_b"]).mean())
    else:
        fn = lambda d: float(d[f"{col}_a"].sum() / max(d[ratio_den].sum(), 1) - d[f"{col}_b"].sum() / max(d[ratio_den].sum(), 1))
    return group_bootstrap_ci(m, fn, "group", n, seed), m


# ---------------------------------------------------------------------------------------------- action statistics
def action_frequency(traces: list[dict]) -> dict:
    """P(A_t = a | N_acq >= t): per objective and step, action counts divided by the number of episodes reaching step t."""
    counts = defaultdict(Counter)
    reach = Counter()
    for tr in traces:
        k = tr["operating_point"]["n_acquisitions"] if "operating_point" in tr else tr["n_acquisitions"]
        for s in tr["steps"][:k]:
            counts[(tr["objective_id"], s["t"])][s["selected_action"]] += 1
            reach[(tr["objective_id"], s["t"])] += 1
    return {key: {"n_t": reach[key], "freq": {a: c / reach[key] for a, c in cnt.items()}} for key, cnt in counts.items()}


def single_action_objectives(traces: list[dict], admissible: dict[str, int] | None = None) -> set[str]:
    """Objectives in which only one action is ever selected (or only one is admissible)."""
    used = defaultdict(set)
    for tr in traces:
        k = tr["operating_point"]["n_acquisitions"] if "operating_point" in tr else tr["n_acquisitions"]
        for s in tr["steps"][:k]:
            used[tr["objective_id"]].add(s["selected_action"])
    out = {o for o, a in used.items() if len(a) == 1}
    if admissible:
        out |= {o for o, n in admissible.items() if n == 1}
    return out


# ---------------------------------------------------------------------------------------------- escalation / gate effects
def escalation_breakdown(raw: pd.DataFrame, loss: LossMatrix) -> dict:
    """Evidence-uncertainty escalation in RAW results: HumanReview decisions not caused by the adequacy gate."""
    hr = raw[raw["decision"] == HUMAN_REVIEW]
    auto = hr["belief"].map(loss.autonomous_decision)
    return {"escalations": int(len(hr)), "Y0": int((hr["y"] == 0).sum()), "Y1": int((hr["y"] == 1).sum()),
            "false_assurances_prevented": int(((auto == "Assured") & (hr["y"] == 0)).sum()),
            "false_non_assurances_prevented": int(((auto == "NotAssured") & (hr["y"] == 1)).sum()),
            "correct_autonomous_withheld": int((((auto == "Assured") & (hr["y"] == 1)) | ((auto == "NotAssured") & (hr["y"] == 0))).sum()),
            "coverage_lost": float(len(hr) / len(raw)) if len(raw) else np.nan}


def gate_breakdown(raw: pd.DataFrame, enforced: pd.DataFrame) -> dict:
    """Model-adequacy escalation: episodes whose RAW decision was autonomous but the gate converted to HumanReview."""
    m = raw.merge(enforced, on=["objective", "episode_id", "method", "y", "group"], suffixes=("_raw", "_enf"))
    changed = m[(m["decision_raw"] != HUMAN_REVIEW) & (m["decision_enf"] == HUMAN_REVIEW)]
    return {"gated_episodes": int((m["reason_enf"].astype(str).str.startswith("MODEL_ADEQUACY")).sum()),
            "decisions_changed": int(len(changed)), "Y0": int((changed["y"] == 0).sum()), "Y1": int((changed["y"] == 1).sum()),
            "false_assurances_prevented": int(((changed["decision_raw"] == "Assured") & (changed["y"] == 0)).sum()),
            "false_non_assurances_prevented": int(((changed["decision_raw"] == "NotAssured") & (changed["y"] == 1)).sum()),
            "correct_autonomous_withheld": int((((changed["decision_raw"] == "Assured") & (changed["y"] == 1)) |
                                                ((changed["decision_raw"] == "NotAssured") & (changed["y"] == 0))).sum()),
            "coverage_raw": float((m["decision_raw"] != HUMAN_REVIEW).mean()) if len(m) else np.nan,
            "coverage_enforced": float((m["decision_enf"] != HUMAN_REVIEW).mean()) if len(m) else np.nan}
