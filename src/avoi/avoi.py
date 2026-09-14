"""Assurance value of information (AVOI) and related acquisition-value criteria.

For evidence E_t and available action a with outcomes o in O_a:
  E[R_{t+1} | a] = sum_o P(o | E_t, a) * R(P(Y | E_t, o, a))
  dR(a)          = R(b_t) - E[R_{t+1} | a]
  AVOI(a)        = dR(a) - lambda*C(a) - mu*P(a) - nu*D(a)
Evidence reliability enters through the learned likelihood model (P(o | E, a) and the posterior update), not as
an additive bonus.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from avoi.bayes_risk import LossMatrix, entropy


@dataclass
class CandidateValue:
    action: int
    outcome_probs: list[float]
    outcome_posteriors: list[float]
    expected_next_risk: float
    risk_reduction: float
    cost_term: float
    privacy_term: float
    delay_term: float
    value: float


def evaluate_candidates(model, evidence: tuple, available: list[int], loss: LossMatrix, C, P, D,
                        lam: float, mu: float, nu: float, criterion: str = "bayes_risk") -> tuple[float, list[CandidateValue]]:
    """criterion: 'bayes_risk' (AVOI), 'entropy' (information gain), 'risk_no_terms' uses the given loss but no penalties."""
    b = model.posterior(evidence)
    base = loss.risk(b) if criterion == "bayes_risk" else float(entropy(b))
    out = []
    for a in available:
        probs, posts = model.predictive(evidence, a)
        if criterion == "bayes_risk":
            nxt = float(np.dot(probs, loss.risk_vec(np.asarray(posts))))
        else:
            nxt = float(np.dot(probs, entropy(np.asarray(posts))))
        red = base - nxt
        ct, pt, dt = lam * C[a], mu * P[a], nu * D[a]
        out.append(CandidateValue(a, [float(x) for x in probs], [float(x) for x in posts], nxt, red, ct, pt, dt,
                                  red - ct - pt - dt))
    return b, out


def lookahead2_values(model, evidence: tuple, available: list[int], loss: LossMatrix, C, P, D, lam, mu, nu):
    """Non-myopic two-step lookahead: value of acquiring a now and then optimally (myopically) one more action or
    stopping. Used by the approximate POMDP-style baseline."""
    b = model.posterior(evidence)
    R0 = loss.risk(b)
    vals = {}
    for a in available:
        probs, posts = model.predictive(evidence, a)
        exp_best = 0.0
        for o, po in enumerate(probs):
            if po <= 0:
                continue
            ev1 = tuple(sorted(evidence + ((a, o),)))
            r1 = loss.risk(posts[o])
            best = r1
            for a2 in available:
                if a2 == a:
                    continue
                p2, q2 = model.predictive(ev1, a2)
                cand = float(np.dot(p2, loss.risk_vec(np.asarray(q2)))) + lam * C[a2] + mu * P[a2] + nu * D[a2]
                best = min(best, cand)
            exp_best += po * best
        vals[a] = R0 - exp_best - (lam * C[a] + mu * P[a] + nu * D[a])
    return b, vals
