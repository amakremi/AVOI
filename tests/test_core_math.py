"""Bayes risk, posterior normalisation, exact TAN inference and AVOI calculation."""
import itertools

import numpy as np
import pytest

from avoi.avoi import evaluate_candidates
from avoi.bayes_risk import ASSURED, HUMAN_REVIEW, NOT_ASSURED, SYMMETRIC_01, LossMatrix, entropy
from avoi.models.discriminative import CalibratedLogisticModel
from avoi.models.tan import DiscreteBayesNet, FixedReliabilityModel


def test_bayes_risk_values():
    L = LossMatrix(10, 2, 1)
    assert L.risk(1.0) == 0.0 and L.risk(0.0) == 0.0
    assert L.risk(0.95) == pytest.approx(min(10 * 0.05, 2 * 0.95, 1.0))
    assert L.risk(0.7) == pytest.approx(1.0)          # human review is optimal in the middle
    assert L.bayes_decision(0.7) == HUMAN_REVIEW
    assert L.bayes_decision(0.99) == ASSURED
    assert L.bayes_decision(0.2) == NOT_ASSURED
    assert L.realized_loss(ASSURED, 0) == 10 and L.realized_loss(NOT_ASSURED, 1) == 2
    assert L.realized_loss(HUMAN_REVIEW, 0) == 1 and L.realized_loss(ASSURED, 1) == 0
    noesc = LossMatrix(10, 2, 1, allow_escalation=False)
    assert noesc.risk(0.7) == pytest.approx(min(3.0, 1.4))
    assert SYMMETRIC_01.risk(0.3) == pytest.approx(0.3)
    assert entropy(0.5) == pytest.approx(1.0)


def brute_force_posterior(model, evidence, K):
    obs = dict(evidence)
    lik = np.zeros(2)
    for full in itertools.product(*[range(k) for k in K]):
        if any(full[i] != v for i, v in obs.items()):
            continue
        for y in (0, 1):
            p = model.prior[y]
            for i in range(len(K)):
                par = model.parent[i]
                p *= model.cpt[i][y, full[par] if par >= 0 else 0, full[i]]
            lik[y] += p
    return lik[1] / lik.sum()


@pytest.mark.parametrize("tree", [True, False])
def test_tan_exact_inference_matches_enumeration(synth, tree):
    data, y = synth
    K = [len(a.outcomes) for a in data.actions]
    m = DiscreteBayesNet(K, alpha=1.0, tree=tree).fit(data.values, y)
    rng = np.random.default_rng(1)
    for _ in range(30):
        ev = tuple((j, int(rng.integers(K[j]))) for j in range(len(K)) if rng.uniform() < 0.5)
        assert m.posterior(ev) == pytest.approx(brute_force_posterior(m, ev, K), rel=1e-9)


@pytest.mark.parametrize("kind", ["tan", "nb", "lr", "fixed"])
def test_posterior_and_predictive_normalised(synth, kind):
    data, y = synth
    K = [len(a.outcomes) for a in data.actions]
    if kind == "lr":
        m = CalibratedLogisticModel(K, n_masks=4).fit(data.values, y)
    elif kind == "fixed":
        m = FixedReliabilityModel(K, [list(a.polarity) for a in data.actions]).fit(data.values, y)
    else:
        m = DiscreteBayesNet(K, tree=(kind == "tan")).fit(data.values, y)
    for ev in [(), ((0, 1),), ((0, 0), (2, 2))]:
        b = m.posterior(ev)
        assert 0.0 <= b <= 1.0
        for a in range(len(K)):
            if a in dict(ev):
                continue
            probs, posts = m.predictive(ev, a)
            assert probs.sum() == pytest.approx(1.0)
            assert np.all((posts >= 0) & (posts <= 1))
            if kind in ("tan", "nb", "fixed"):   # law of total probability holds exactly for the generative models
                assert float(np.dot(probs, posts)) == pytest.approx(b, abs=1e-9)


def test_avoi_value_manual_and_nonnegative_risk_reduction(synth):
    data, y = synth
    K = [len(a.outcomes) for a in data.actions]
    m = DiscreteBayesNet(K).fit(data.values, y)
    L = LossMatrix(10, 2, 1)
    C, P, D = np.array([0.1, 0.2, 0.3, 0.4]), np.array([0.1, 0, 0.1, 0]), np.array([0.5, 0.1, 0.2, 0.3])
    b, cands = evaluate_candidates(m, (), [0, 1, 2, 3], L, C, P, D, 0.05, 0.02, 0.02)
    for c in cands:
        probs, posts = m.predictive((), c.action)
        exp_r = sum(p * L.risk(q) for p, q in zip(probs, posts))
        assert c.expected_next_risk == pytest.approx(exp_r)
        assert c.risk_reduction == pytest.approx(L.risk(b) - exp_r)
        assert c.value == pytest.approx(L.risk(b) - exp_r - 0.05 * C[c.action] - 0.02 * P[c.action] - 0.02 * D[c.action])
        assert c.risk_reduction >= -1e-12        # Bayes risk is concave => expected information never hurts
