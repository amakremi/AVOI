"""Assurance loss model and Bayes decision risk.

Decisions: ASSURED, NOT_ASSURED, HUMAN_REVIEW.  y = 1 objective satisfied, y = 0 violated.
The loss values are EXPERIMENTAL UTILITY PARAMETERS (normalised relative losses), not financial or regulatory values.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ASSURED, NOT_ASSURED, HUMAN_REVIEW = "Assured", "NotAssured", "HumanReview"
DECISIONS = (ASSURED, NOT_ASSURED, HUMAN_REVIEW)


@dataclass(frozen=True)
class LossMatrix:
    false_assurance: float = 10.0      # L(Assured, y=0)
    false_non_assurance: float = 2.0   # L(NotAssured, y=1)
    human_review: float = 1.0          # L(HumanReview, y) for both y
    allow_escalation: bool = True

    def table(self) -> dict[str, tuple[float, float]]:
        """decision -> (loss if y=0, loss if y=1)"""
        t = {ASSURED: (self.false_assurance, 0.0), NOT_ASSURED: (0.0, self.false_non_assurance)}
        if self.allow_escalation:
            t[HUMAN_REVIEW] = (self.human_review, self.human_review)
        return t

    def expected_losses(self, b: float) -> dict[str, float]:
        return {d: (1.0 - b) * l0 + b * l1 for d, (l0, l1) in self.table().items()}

    def risk(self, b: float) -> float:
        """Bayes decision risk R(b) = min_d sum_y L(d, y) P(y)."""
        r = min(self.false_assurance * (1.0 - b), self.false_non_assurance * b)
        return min(r, self.human_review) if self.allow_escalation else r

    def risk_vec(self, b: np.ndarray) -> np.ndarray:
        r = np.minimum(self.false_assurance * (1.0 - b), self.false_non_assurance * b)
        return np.minimum(r, self.human_review) if self.allow_escalation else r

    def bayes_decision(self, b: float) -> str:
        el = self.expected_losses(b)
        return min(el, key=lambda d: (el[d], DECISIONS.index(d)))

    def autonomous_decision(self, b: float) -> str:
        """Best decision among {Assured, NotAssured} only."""
        return ASSURED if self.false_assurance * (1.0 - b) <= self.false_non_assurance * b else NOT_ASSURED

    def realized_loss(self, decision: str, y: int) -> float:
        if decision == HUMAN_REVIEW:
            return self.human_review
        l0, l1 = self.table()[decision] if decision in self.table() else (None, None)
        return l1 if y == 1 else l0


SYMMETRIC_01 = LossMatrix(false_assurance=1.0, false_non_assurance=1.0, human_review=1.0, allow_escalation=False)


def entropy(b: float | np.ndarray) -> float | np.ndarray:
    p = np.clip(b, 1e-12, 1 - 1e-12)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
