"""Privacy-exposure proxy.

PrivacyExposure(a) = (number of sensitive categories revealed by acquisition a) / (number of defined categories).
The categories are declared in config/evidence_actions.yaml. This is an EXPERIMENTAL EXPOSURE PROXY, not a universal
privacy-risk valuation and not a monetary price.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from avoi.costs import N_SENSITIVE_CATEGORIES, privacy_exposure

ROOT = Path(__file__).resolve().parents[2]


def sensitive_categories() -> list[str]:
    cfg = yaml.safe_load((ROOT / "config" / "evidence_actions.yaml").read_text(encoding="utf-8"))
    cats = cfg["sensitive_categories"]
    assert len(cats) == N_SENSITIVE_CATEGORIES
    return cats


def episode_exposure(observations) -> float:
    cats = set()
    for o in observations:
        cats |= set(o.privacy_fields_exposed)
    return privacy_exposure(cats)


__all__ = ["sensitive_categories", "episode_exposure", "privacy_exposure"]
