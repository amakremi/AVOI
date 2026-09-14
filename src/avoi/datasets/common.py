"""Dataset-agnostic containers.

ObjectiveData holds, for one assessment objective / micro-claim, the evidence that each action WOULD return in each
episode (the case state), measured acquisition costs and exposed privacy categories. It contains NO labels.
Labels live in data/processed/<domain>/ground_truth and are loaded only by avoi.evaluation.labels.

Numeric evidence (public replay) is converted to discrete outcomes by a Discretizer fitted on training episodes only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from avoi.actions import ActionSpec, EvidenceEnvironment, EvidenceObservation

NUMERIC_OUTCOMES = ("no_data", "low", "elevated", "high")


@dataclass
class ObjectiveData:
    domain: str
    objective_id: str
    actions: list[ActionSpec]
    episode_ids: np.ndarray            # (n,)
    groups: np.ndarray                 # (n,) grouping unit for cross-validation
    strata: dict                       # name -> (n,) array (label-free descriptors, e.g. testbed, week)
    kind: str                          # categorical | numeric
    values: np.ndarray                 # categorical: int codes (n, m); numeric: float stats with NaN = no data
    seconds: np.ndarray                # (n, m)
    records: np.ndarray                # (n, m)
    bytes_: np.ndarray                 # (n, m)
    privacy: list                      # n lists of m lists of category names
    provenance: list | None = None     # optional n x m provenance dicts
    source_name: str = ""

    @property
    def n(self) -> int:
        return len(self.episode_ids)

    @property
    def m(self) -> int:
        return len(self.actions)

    def n_categories(self) -> np.ndarray:
        return np.array([[len(c) for c in row] for row in self.privacy])

    def subset(self, idx: np.ndarray) -> "ObjectiveData":
        idx = np.asarray(idx)
        return ObjectiveData(self.domain, self.objective_id, self.actions, self.episode_ids[idx], self.groups[idx],
                             {k: v[idx] for k, v in self.strata.items()}, self.kind, self.values[idx],
                             self.seconds[idx], self.records[idx], self.bytes_[idx], [self.privacy[i] for i in idx],
                             [self.provenance[i] for i in idx] if self.provenance else None, self.source_name)


class Discretizer:
    """Per-action thresholds (training 50th and 90th percentile of observed statistics); NaN -> no_data."""

    def fit(self, values: np.ndarray) -> "Discretizer":
        self.t = []
        for j in range(values.shape[1]):
            v = values[:, j]
            v = v[~np.isnan(v)]
            if len(v) == 0:
                self.t.append((0.0, 0.0))
            else:
                self.t.append((float(np.quantile(v, 0.5)), float(np.quantile(v, 0.9))))
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        codes = np.zeros(values.shape, dtype=int)
        for j, (t1, t2) in enumerate(self.t):
            v = values[:, j]
            c = np.where(v <= t1, 1, np.where(v <= t2, 2, 3))
            codes[:, j] = np.where(np.isnan(v), 0, c)
        return codes


def codes_for(data: ObjectiveData, discretizer: Discretizer | None) -> np.ndarray:
    if data.kind == "categorical":
        return data.values.astype(int)
    return discretizer.transform(data.values)


def make_environment(data: ObjectiveData, i: int, codes_row: np.ndarray, cost_model, initially: set[int] = frozenset(),
                     outcome_override: dict[int, int] | None = None) -> EvidenceEnvironment:
    """Access-controlled environment for episode i. The closure is the only path to unacquired evidence."""
    eid = str(data.episode_ids[i])

    def fetch(a: int) -> EvidenceObservation:
        o = int(outcome_override[a]) if outcome_override and a in outcome_override else int(codes_row[a])
        spec = data.actions[a]
        prov = data.provenance[i][a] if data.provenance else {}
        cats = list(data.privacy[i][a])
        return EvidenceObservation(
            action_id=spec.action_id, objective_id=data.objective_id, source=data.source_name, outcome=spec.outcomes[o],
            outcome_index=o, timestamp=str(prov.get("timestamp_utc", "")), scope=str(prov.get("scope", eid)),
            provenance=prov, raw_artifact_ref=str(prov.get("raw_artifact_ref", "")), parser=str(prov.get("parser", "")),
            acquisition_seconds=float(data.seconds[i, a]), records_accessed=int(data.records[i, a]),
            bytes_read=int(data.bytes_[i, a]), privacy_fields_exposed=cats,
            cost_normalized=float(cost_model.realized_cost(data.records[i, a], data.bytes_[i, a], a)),
            privacy_exposure=len(cats) / 10.0, delay_normalized=float(cost_model.realized_delay(data.seconds[i, a])))

    pre = {a: fetch(a) for a in initially}
    return EvidenceEnvironment(eid, data.actions, fetch, pre)
