"""Evidence actions, observations and the access-controlled evidence environment.

The acquisition policy interacts with an assessment episode ONLY through EvidenceEnvironment:
  - available_actions(): actions not yet acquired
  - observed():          evidence acquired so far (including evidence already in hand at t = 0)
  - acquire(a):          executes action a and returns its EvidenceObservation
Unacquired outcomes are held in a private closure and cannot be read through the public interface.
Ground-truth labels are never given to the environment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    objective_id: str
    source_type: str
    outcomes: tuple[str, ...]
    polarity: tuple[int, ...]                 # nominal reading per outcome (+1 / -1 / 0); ablation only
    privacy_schema: tuple[str, ...] = ()


@dataclass
class EvidenceObservation:
    action_id: str
    objective_id: str
    source: str
    outcome: str
    outcome_index: int
    timestamp: str
    scope: str
    provenance: dict
    raw_artifact_ref: str
    parser: str
    acquisition_seconds: float
    records_accessed: int
    bytes_read: int
    privacy_fields_exposed: list[str]
    cost_normalized: float = 0.0
    privacy_exposure: float = 0.0
    delay_normalized: float = 0.0


class EvidenceAction:
    """Common interface: an action that acquires one piece of evidence for an objective from a case state."""

    def __init__(self, spec: ActionSpec, acquire_fn: Callable[[object], EvidenceObservation]):
        self.spec = spec
        self.action_id = spec.action_id
        self.source_type = spec.source_type
        self.objective_ids = [spec.objective_id]
        self._fn = acquire_fn

    def acquire(self, case_state) -> EvidenceObservation:
        return self._fn(case_state)


class EvidenceEnvironment:
    def __init__(self, episode_id: str, actions: list[ActionSpec], fetch: Callable[[int], EvidenceObservation],
                 initially_available: dict[int, EvidenceObservation] | None = None):
        self.episode_id = episode_id
        self.actions = actions
        self._fetch = fetch                       # private accessor to the case state
        self._acquired: dict[int, EvidenceObservation] = dict(initially_available or {})
        self._pre = set(self._acquired)
        self.log: list[int] = []

    def available_actions(self) -> list[int]:
        return [i for i in range(len(self.actions)) if i not in self._acquired]

    def observed(self) -> tuple:
        return tuple(sorted((i, o.outcome_index) for i, o in self._acquired.items()))

    def pre_acquired(self) -> set[int]:
        return set(self._pre)

    def acquire(self, a: int) -> EvidenceObservation:
        if a in self._acquired:
            raise ValueError(f"action {self.actions[a].action_id} already acquired in episode {self.episode_id}")
        obs = self._fetch(a)
        self._acquired[a] = obs
        self.log.append(a)
        return obs
