"""Acquisition cost, delay and privacy normalisation (all fitted on TRAINING episodes only).

Regime A (uniform):   every non-human evidence action costs 1 (normalised cost 1).
Regime B (empirical): computational acquisition cost from measured records accessed and bytes read:
                      C_B(a) = 0.5 * mean_train(records_a)/max_b mean_train(records_b)
                             + 0.5 * mean_train(bytes_a)/max_b mean_train(bytes_b)
Delay D(a):           mean_train(wall-clock acquisition seconds_a) / max_b mean_train(seconds_b)
Privacy P(a):         mean_train(|sensitive categories revealed by a|) / |defined categories|
Measured milliseconds/bytes are testbed/replay measurements; they are NOT organisational audit costs.
Realised per-episode quantities use the same training normalisers applied to the per-episode measurements.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

N_SENSITIVE_CATEGORIES = 10


@dataclass
class CostModel:
    regime: str
    C: np.ndarray          # expected normalised cost per action (planner)
    D: np.ndarray          # expected normalised delay per action (planner)
    P: np.ndarray          # expected privacy exposure per action (planner)
    rec_max: float
    byte_max: float
    sec_max: float

    @classmethod
    def fit(cls, records: np.ndarray, bytes_: np.ndarray, seconds: np.ndarray, n_cats: np.ndarray,
            regime: str = "B") -> "CostModel":
        mr, mb, ms = records.mean(0), bytes_.mean(0), seconds.mean(0)
        rec_max, byte_max, sec_max = max(mr.max(), 1e-9), max(mb.max(), 1e-9), max(ms.max(), 1e-9)
        if regime == "A":
            C = np.ones(records.shape[1])
        else:
            C = 0.5 * mr / rec_max + 0.5 * mb / byte_max
        return cls(regime, C, ms / sec_max, n_cats.mean(0) / N_SENSITIVE_CATEGORIES, rec_max, byte_max, sec_max)

    mult: np.ndarray | None = None   # per-action cost multiplier (Layer C cost-change experiments)

    def realized_cost(self, records: float, bytes_: float, a: int | None = None) -> float:
        base = 1.0 if self.regime == "A" else 0.5 * records / self.rec_max + 0.5 * bytes_ / self.byte_max
        return base * (float(self.mult[a]) if (self.mult is not None and a is not None) else 1.0)

    def realized_delay(self, seconds: float) -> float:
        return seconds / self.sec_max

    def with_multiplier(self, mult: np.ndarray) -> "CostModel":
        return CostModel(self.regime, self.C * mult, self.D, self.P, self.rec_max, self.byte_max, self.sec_max, np.asarray(mult))


def privacy_exposure(categories: set[str] | list[str]) -> float:
    """Episode/acquisition exposure = |distinct sensitive categories revealed| / |defined categories| (proxy)."""
    return len(set(categories)) / N_SENSITIVE_CATEGORIES
