"""Loading and aggregation of raw experiment outputs for CSV analysis."""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "results" / "raw"
TRACES = ROOT / "results" / "traces"
DOMAINS = ["iam", "ait", "cert"]
DOMAIN_LABEL = {"iam": "Controlled IAM testbed (Layer A)", "ait": "AIT-LDS v2.0 replay (Layer B)", "cert": "CERT r4.2 replay (Layer B)"}
MAIN_METHODS = ["AVOI-GRC", "B0-AllEvidence", "B1-FixedChecklist", "B2-Random", "B3-CheapestFirst", "B4-InformationGain",
                "B5-GenericVOI", "B6-ConfidenceThreshold", "B7-MyopicCostSensitiveVOI", "B7b-Lookahead2VOI"]
ABLATIONS = ["AVOI-GRC", "A1-NoAsymmetricLoss", "A2-NoLearnedReliability", "A3-NoCost", "A4-NoPrivacy", "A5-NoDelay",
             "A6-NoEscalation", "A7-EntropyInsteadOfRisk", "A8-NaiveBayesModel"]
PRIMARY_COND = "fa=10.0|lam=1.0|mu=1.0|nu=1.0"


@lru_cache(maxsize=None)
def episodes(experiment: str, domain: str) -> pd.DataFrame:
    files = sorted((RAW / experiment / domain).glob("episodes_*.csv.gz"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df["method_family"] = df["method"].str.replace(r"\[s\d+\]", "", regex=True)
    return df


@lru_cache(maxsize=None)
def table(experiment: str, domain: str, kind: str) -> pd.DataFrame:
    files = sorted((RAW / experiment / domain).glob(f"{kind}_*.csv*"))
    return pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True) if files else pd.DataFrame()


def tuned(experiment: str, domain: str, condition: str = PRIMARY_COND) -> pd.DataFrame:
    """Held-out operating points at the inner-tuned thresholds, cold start, no shift."""
    df = episodes(experiment, domain)
    if df.empty:
        return df
    m = (df["start"] == "cold") & (df["shift"] == "none") & (df["condition"] == condition)
    return df[m].copy()


def random_average(df: pd.DataFrame) -> pd.DataFrame:
    """Average the B2 random baseline over seeds per episode (fractional decision indicators)."""
    r = df[df["method_family"] == "B2-Random"].copy()
    if r.empty:
        return r
    r["assured_f"] = (r["decision"] == "Assured").astype(float)
    r["hr_f"] = (r["decision"] == "HumanReview").astype(float)
    r["unsafe_frac"] = r["assured_f"] * (r["y"] == 0)
    keys = ["experiment", "domain", "objective", "fold", "episode_id", "y"]
    g = r.groupby(keys, as_index=False).agg(belief=("belief", "mean"), loss=("loss", "mean"), n_acq=("n_acq", "mean"),
                                           cost=("cost", "mean"), delay=("delay", "mean"), seconds=("seconds", "mean"),
                                           privacy=("privacy", "mean"), assured_f=("assured_f", "mean"), hr_f=("hr_f", "mean"),
                                           unsafe_frac=("unsafe_frac", "mean"))
    g["method"] = g["method_family"] = "B2-Random"
    g["decision"] = "mixed(random seeds)"   # decisions are summarised by assured_f / hr_f / unsafe_frac
    return g


def per_method(df: pd.DataFrame, method: str) -> pd.DataFrame:
    if method == "B2-Random":
        return random_average(df)
    return df[df["method"] == method].sort_values(["objective", "fold", "episode_id"])


def paired_frame(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Align two methods on identical held-out episodes."""
    x, z = per_method(df, a), per_method(df, b)
    keys = ["objective", "fold", "episode_id", "y"]
    return x.merge(z, on=keys, suffixes=("_a", "_b"))


def load_traces(domain: str, method: str) -> list[dict]:
    out = []
    for p in sorted((TRACES / domain / method).glob("*.jsonl.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                out.append(json.loads(line))
    return out


def curves(experiment: str, domain: str) -> pd.DataFrame:
    c = table(experiment, domain, "curves")
    if c.empty:
        return c
    c["method_family"] = c["method"].str.replace(r"\[s\d+\]", "", regex=True)
    return c


def pooled_curve(c: pd.DataFrame, method_family: str, condition: str = PRIMARY_COND) -> pd.DataFrame:
    """Pool held-out counts over objectives and folds per threshold (random baseline additionally over seeds)."""
    s = c[(c["method_family"] == method_family) & (c["condition"] == condition)]
    if s.empty:
        return s
    g = s.groupby("tau", dropna=False)[["n", "n_viol", "n_assured", "n_hr", "n_unsafe", "n_correct_auto", "loss_sum",
                                         "cost_sum", "privacy_sum", "delay_sum", "nacq_sum"]].sum().reset_index()
    g["coverage"] = 1 - g["n_hr"] / g["n"]
    g["UAR"] = g["n_unsafe"] / g["n_viol"].replace(0, np.nan)
    auto = g["n"] - g["n_hr"]
    g["selective_risk"] = (auto - g["n_correct_auto"]) / auto.replace(0, np.nan)
    g["expected_loss"] = g["loss_sum"] / g["n"]
    g["cost"] = g["cost_sum"] / g["n"]
    g["privacy"] = g["privacy_sum"] / g["n"]
    g["acquisitions"] = g["nacq_sum"] / g["n"]
    return g


def aurc(curve: pd.DataFrame, y: str = "UAR") -> float:
    """Area under the risk-coverage curve over the achieved coverage range, normalised by that range."""
    c = curve.dropna(subset=[y]).sort_values("coverage")
    c = c.groupby("coverage", as_index=False)[y].min()
    if len(c) < 2 or c["coverage"].max() - c["coverage"].min() <= 0:
        return float(c[y].iloc[0]) if len(c) else np.nan
    return float(np.trapezoid(c[y], c["coverage"]) / (c["coverage"].max() - c["coverage"].min()))
