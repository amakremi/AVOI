"""Stopping rule, no repeated acquisition, cost/privacy accounting, trace completeness, truncation exactness, seeding."""
from dataclasses import replace

import numpy as np
import pytest

from avoi.agent import PolicyConfig, SequentialAssuranceAgent, truncate
from avoi.bayes_risk import HUMAN_REVIEW, LossMatrix
from avoi.costs import CostModel
from avoi.datasets.common import make_environment
from avoi.evaluation import engine as E
from avoi.models.tan import DiscreteBayesNet

REQUIRED_TRACE_KEYS = {"initial_belief", "steps", "final_decision", "final_risk", "total_cost", "privacy_categories",
                       "total_delay", "stop_reason", "n_acquisitions", "states"}
REQUIRED_STEP_KEYS = {"selected_action", "observed_outcome", "updated_belief", "updated_risk", "cost", "delay",
                      "privacy_categories", "provenance", "raw_artifact_ref", "candidates"}


def setup(synth, regime="B"):
    data, y = synth
    tr = np.arange(160)
    ctx = E.make_context(data, y, tr, ["tan", "nb"], {}, regime, None, 0, 0, hps={"tan": {"alpha": 1.0}, "nb": {"alpha": 1.0}})
    return data, y, ctx


def test_trace_completeness_and_no_repeats(synth):
    data, y, ctx = setup(synth)
    cfg = PolicyConfig("AVOI", "avoi", LossMatrix(), 0.05, 0.02, 0.02, "risk", tau=0.05)
    agent = SequentialAssuranceAgent(cfg, ctx.models["tan"], ctx.cost, "OBJ")
    for i in range(160, 200):
        env = make_environment(data, i, ctx.codes[i], ctx.cost)
        tr = agent.run(env)
        assert REQUIRED_TRACE_KEYS <= set(tr)
        acts = [s["selected_action"] for s in tr["steps"]]
        assert len(acts) == len(set(acts))
        for s in tr["steps"]:
            assert REQUIRED_STEP_KEYS <= set(s)
            for c in s["candidates"]:
                assert {"outcome_probs", "outcome_posteriors", "value", "expected_next_risk"} <= set(c)
        # cost & privacy accounting
        exp_cost = sum(ctx.cost.realized_cost(data.records[i, s["action_index"]], data.bytes_[i, s["action_index"]], s["action_index"])
                       for s in tr["steps"])
        assert tr["total_cost"] == pytest.approx(exp_cost)
        cats = set().union(*[set(data.privacy[i][s["action_index"]]) for s in tr["steps"]]) if tr["steps"] else set()
        assert set(tr["privacy_categories"]) == cats


def test_stopping_rules(synth):
    data, y, ctx = setup(synth)
    L = LossMatrix()
    # tau >= max risk -> stop immediately with an autonomous decision
    agent = SequentialAssuranceAgent(PolicyConfig("A", "avoi", L, 0.05, 0.02, 0.02, "risk", tau=1.0), ctx.models["tan"], ctx.cost, "OBJ")
    tr = agent.run(make_environment(data, 170, ctx.codes[170], ctx.cost))
    assert tr["n_acquisitions"] == 0 and tr["stop_reason"] == "threshold" and tr["final_decision"] != HUMAN_REVIEW
    # prohibitive acquisition costs -> no positive AVOI -> HumanReview when risk exceeds tau
    agent = SequentialAssuranceAgent(PolicyConfig("A", "avoi", L, 1e6, 0, 0, "risk", tau=0.0), ctx.models["tan"], ctx.cost, "OBJ")
    tr = agent.run(make_environment(data, 170, ctx.codes[170], ctx.cost))
    if tr["initial_risk"] > 0:
        assert tr["n_acquisitions"] == 0 and tr["stop_reason"] == "no_positive_value" and tr["final_decision"] == HUMAN_REVIEW
    # never forced: without escalation the decision is autonomous
    agent = SequentialAssuranceAgent(PolicyConfig("A", "avoi", replace(L, allow_escalation=False), 1e6, 0, 0, "risk", tau=0.0),
                                     ctx.models["tan"], ctx.cost, "OBJ")
    assert agent.run(make_environment(data, 170, ctx.codes[170], ctx.cost))["final_decision"] != HUMAN_REVIEW


@pytest.mark.parametrize("name", ["AVOI-GRC", "B1-FixedChecklist", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold",
                                  "B2-Random[s3]", "B3-CheapestFirst", "B7b-Lookahead2VOI"])
def test_truncation_equals_direct_threshold_run(synth, name):
    data, y, ctx = setup(synth)
    suite = {s.name: s for s in E.method_suite(LossMatrix(), 0.05, 0.02, 0.02, 1e-3, 5)}
    spec = suite[name]
    grid = {"risk": [0.0, 0.1, 0.3, 0.7], "confidence": [0.6, 0.8, 0.95, 1.01], "symmetric": [0.0, 0.1, 0.3]}[spec.threshold]
    idx = np.arange(160, 240)
    full = E.run_trajectories(ctx, spec, idx)
    for tau in grid:
        agent = SequentialAssuranceAgent(replace(spec.cfg, tau=tau), ctx.models["tan"], ctx.cost, "OBJ", False)
        for tr, i in zip(full, idx):
            direct = agent.run(make_environment(data, i, ctx.codes[i], ctx.cost))
            op = truncate(tr, spec.cfg, tau)
            assert direct["final_decision"] == op["decision"]
            assert direct["n_acquisitions"] == op["n_acquisitions"]
            assert direct["total_cost"] == pytest.approx(op["cost"])
    # budget truncation equals a direct run with max_steps
    agent = SequentialAssuranceAgent(replace(spec.cfg, tau=grid[1]), ctx.models["tan"], ctx.cost, "OBJ", False)
    for tr, i in zip(full, idx):
        direct = agent.run(make_environment(data, i, ctx.codes[i], ctx.cost), max_steps=1)
        op = truncate(tr, spec.cfg, grid[1], budget=1)
        assert direct["final_decision"] == op["decision"] and direct["n_acquisitions"] == op["n_acquisitions"]


def test_random_policy_seeding_deterministic(synth):
    data, y, ctx = setup(synth)
    s = {m.name: m for m in E.method_suite(LossMatrix(), 0.05, 0.02, 0.02, 1e-3, 3)}
    a = [t["steps"] and [x["selected_action"] for x in t["steps"]] for t in E.run_trajectories(ctx, s["B2-Random[s1]"], np.arange(160, 200))]
    b = [t["steps"] and [x["selected_action"] for x in t["steps"]] for t in E.run_trajectories(ctx, s["B2-Random[s1]"], np.arange(160, 200))]
    c = [t["steps"] and [x["selected_action"] for x in t["steps"]] for t in E.run_trajectories(ctx, s["B2-Random[s2]"], np.arange(160, 200))]
    assert a == b and a != c


def test_cost_regimes(synth):
    data, y = synth
    tr = np.arange(160)
    a = CostModel.fit(data.records[tr], data.bytes_[tr], data.seconds[tr], data.n_categories()[tr], "A")
    b = CostModel.fit(data.records[tr], data.bytes_[tr], data.seconds[tr], data.n_categories()[tr], "B")
    assert np.all(a.C == 1.0) and a.realized_cost(10, 10) == 1.0
    assert np.all((b.C > 0) & (b.C <= 1.0)) and b.C.max() <= 1.0
    assert np.all(b.P == pytest.approx(data.n_categories()[tr].mean(0) / 10))


def test_initial_availability_modes(synth):
    data, y, ctx = setup(synth)
    idx = np.arange(160, 200)
    for mode in ("mcar", "block", "adversarial"):
        for level in (0.2, 0.4, 0.6, 0.8, 1.0):
            sets = E.initial_sets(ctx, idx, level, mode, 7)
            assert all(len(s) == data.m - int(round(level * data.m)) for s in sets)
            assert sets == E.initial_sets(ctx, idx, level, mode, 7)   # identical starting states for every method
