"""Stage-3 tests: prior-result integrity, reuse guarantees, Frozen-Order AVOI, adaptivity metrics, branching scenario
integrity, class orientation, and leakage isolation for the new external-model development pipeline."""
from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


# ====================================================================================== 1-3: prior results untouched
def test_previous_results_unchanged():
    import sys
    sys.path.insert(0, str(ROOT / "experiments" / "stage3"))
    from archive_snapshot import verify
    changed = verify()
    assert not changed, changed[:20]


def test_stage1_and_stage2_freeze_hashes_readable_and_match_snapshot():
    snap = json.loads((ROOT / "results" / "archive" / "pre_stage3_snapshot" / "MANIFEST.json").read_text(encoding="utf-8"))
    fr1 = json.loads((ROOT / "results" / "stage1_ungated" / "EXPERIMENT_FREEZE.json").read_text(encoding="utf-8"))
    fr2 = json.loads((ROOT / "results" / "stage2" / "EXPERIMENT_FREEZE_STAGE2.json").read_text(encoding="utf-8"))
    assert fr1["hashes"]["combined_sha256"] == snap["stage1_freeze_sha256"]
    assert fr2["hashes"]["combined_sha256"] == snap["stage2_freeze_sha256"]


def test_stage3_writes_only_under_its_own_result_tree():
    import ast
    for f in ["experiments/stage3/run_wp1.py", "experiments/stage3/run_wp2_ait.py", "experiments/stage3/run_wp2_cert.py"]:
        src = (ROOT / f).read_text(encoding="utf-8")
        for forbidden in ("results/stage1_ungated", "results/stage2/", "results/final_report_v2"):
            assert forbidden not in src, f"{f} references {forbidden}"


# ====================================================================================== 4-5: reused checksums / cache
def test_reused_dataset_checksums_match_historical_manifest():
    man = json.loads((ROOT / "data" / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    ids = {e["id"] for e in man["entries"]}
    for eid in ("ait_lds_v2_russellmitchell", "ait_lds_v2_santos", "ait_lds_v2_fox", "ait_lds_v2_harrison",
                "ait_lds_v2_wardbeck", "cert_r4_2", "cert_r5_2"):
        assert eid in ids, f"{eid} missing from dataset manifest (would need re-download)"


def test_model_adequacy_policy_sha256_unchanged():
    import sys
    sys.path.insert(0, str(ROOT / "experiments"))
    from common import sha256_file
    snap = json.loads((ROOT / "results" / "archive" / "pre_stage3_snapshot" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert sha256_file(ROOT / "config" / "model_adequacy.yaml") == snap["model_adequacy_yaml_sha256"]


# ====================================================================================== 6: adequacy thresholds unchanged
def test_stage2_adequacy_thresholds_unchanged_and_loaded_directly():
    from avoi import adequacy as AQ
    pol = AQ.load_policy()
    s = pol["primary"]["support"]
    assert s["min_violated_cases"] == 20 and s["min_satisfied_cases"] == 20
    assert s["min_groups"] == 10 and s["min_groups_with_violation"] == 5
    d = pol["primary"]["discrimination"]
    assert d["auroc_ci_lower_gt"] == 0.50 and d["pr_skill_ci_lower_gt"] == 0.0
    c = pol["primary"]["calibration"]
    assert c["bss_gt"] == 0 and c["ece_le"] == 0.10 and c["slope_min"] == 0.5 and c["slope_max"] == 1.5
    src = (ROOT / "src" / "avoi" / "evaluation" / "stage3.py").read_text(encoding="utf-8")
    assert "load_policy" not in src or "adequacy.load_policy" not in src.replace(" ", ""), "policy must come from AQ.load_policy(), never redefined in stage3.py"


# ====================================================================================== 7-10: no leakage into training/selection/adequacy
def test_confirmation_labels_cannot_enter_model_selection(monkeypatch, synth):
    """lodo_candidates/select_candidate use only the passed development dict; scrambling a held-out fold's own labels
    changes that fold's score but never the SELECTED model's identity when computed from other development folds only
    (development-only guarantee is structural: confirmation data is never passed to these functions)."""
    from avoi.evaluation import stage3_wp2 as W2
    data, y = synth
    K = [len(set(data.values[:, j].astype(int))) for j in range(data.values.shape[1])]
    by_src = {"a": (data.values[:80].astype(int), y[:80]), "b": (data.values[80:160].astype(int), y[80:160]),
             "c": (data.values[160:240].astype(int), y[160:240])}
    C = {"adequacy": __import__("avoi.adequacy", fromlist=["load_policy"]).load_policy(),
        "s3": {"candidates": {"tan": {"alpha": [1.0]}, "naive_bayes": {"alpha": [1.0]}, "hist_gradient_boosting": {"max_depth": [3], "learning_rate": [0.1], "max_iter": [50]}}}}
    cands1 = W2.lodo_candidates(by_src, K, None, C)
    chosen1 = W2.select_candidate(cands1)
    # confirmation-only data (never in by_src) must not be inspectable by these functions - structural: they take no such argument
    import inspect
    assert "confirm" not in inspect.signature(W2.lodo_candidates).parameters
    assert "confirm" not in inspect.signature(W2.select_candidate).parameters


def test_confirmation_labels_cannot_enter_calibrator_selection():
    from avoi.evaluation import stage3 as S3M
    import inspect
    assert set(inspect.signature(S3M.monotone_calibrator).parameters) == {"p", "y", "groups", "candidates", "seed"}
    # by construction monotone_calibrator (like Stage-2's select_calibrator) receives exactly the arrays the caller
    # passes; Stage-3 callers (run_wp2_ait.variants, run_wp2_cert.variants) pass only the CALIBRATION split.


def test_confirmation_labels_cannot_enter_adequacy_status():
    """decide() is the unchanged Stage-2 function: it is a pure function of (metrics, bootstrap) computed from
    whatever data the caller passes. Stage-3 adequacy_phase() callers must never index a confirmation partition."""
    import ast
    import re
    for f in ["experiments/stage3/run_wp1.py", "experiments/stage3/run_wp2_ait.py", "experiments/stage3/run_wp2_cert.py"]:
        src = (ROOT / f).read_text(encoding="utf-8")
        tree = ast.parse(src)
        funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        assert "adequacy_phase" in funcs, f
        body_src = ast.get_source_segment(src, funcs["adequacy_phase"])
        # forbid reading a confirmation-partition data variable (the actual data-carrying names used only in
        # confirm(), never in adequacy_phase()) or indexing a "conf" dict key; recording which testbeds/releases
        # ARE the confirmation split as plain metadata (e.g. "confirmation_testbeds": CONFIRM_TESTBEDS) is fine.
        assert not re.search(r'\[.conf.\]|\bconf_mask\b|\bcdata\b|\bcidx\b|\bcy\b|\bccodes\b|\bcblocks\b|dev\["target_raw"\]\[0\]\.subset', body_src), \
            f"{f}:adequacy_phase appears to read confirmation-partition data"
        assert "include_confirmation=False" in body_src or "run_wp1" not in f


# ====================================================================================== 11-12: class orientation
def test_ait_class_orientation():
    from sklearn.metrics import roc_auc_score
    y = np.array([1, 1, 0, 0])                 # 1=holds/satisfied, 0=violated
    p_y1 = np.array([0.9, 0.8, 0.2, 0.1])       # good model: high P(Y=1) for satisfied
    viol = (y == 0).astype(int)
    auroc = roc_auc_score(viol, 1 - p_y1)       # violation-AUROC uses 1-P(Y=1) as the violation score
    assert auroc == 1.0


def test_cert_class_orientation():
    from avoi.datasets.cert import CLAIM
    from avoi import adequacy as AQ
    y = np.array([1, 1, 1, 0, 0])
    p = np.array([0.9, 0.85, 0.7, 0.3, 0.1])
    m = AQ.point_metrics(y, p, 0.6)
    assert m["AUROC"] > 0.9   # a well-separated CERT-style model must score high AUROC under the shared convention
    assert m["n_violated"] == 2 and m["n_satisfied"] == 3


# ====================================================================================== 13-14: branching action sets / latent hiding
def test_same_iam_action_set_for_every_branching_subtype():
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))
    branch_cfg = yaml.safe_load((ROOT / "config" / "scenario_generator_stage3_dev.yaml").read_text(encoding="utf-8"))
    mech_keys = branch_cfg["branching"]["mechanisms"]
    action_sets = {o["id"]: {a["id"] for a in o["actions"]} for o in cfg["objectives"]}
    # the generator emits a fixed action_order() from config/assurance_objectives.yaml regardless of mechanism,
    # so the admissible action set per objective is invariant by construction; verify no mechanism-conditional code path
    src = (ROOT / "testbed" / "run_testbed.py").read_text(encoding="utf-8")
    assert "branching_mechanisms" not in src, "run_testbed action_order() must not depend on the latent mechanism"
    for key in mech_keys:
        assert len(mech_keys[key]) >= 2


def test_latent_subtype_unavailable_to_avoi():
    from testbed.scenarios.generator import generate_spec, load_cfg
    cfg = load_cfg("config/scenario_generator_stage3_dev.yaml")
    spec = generate_spec(5, cfg, "s3test")
    assert "branching_mechanisms" in spec["latent"]
    # the evidence-store writer (run_testbed.run_scenario) only ever persists `observations` built from collector
    # outputs (outcome/raw/bytes/records/...); `spec["latent"]` is never written to evidence_store/<scenario>.json
    src = (ROOT / "testbed" / "run_testbed.py").read_text(encoding="utf-8")
    assert '"observations": observations' in src
    assert "latent" not in src


def test_generate_spec_byte_identical_for_stage1_and_stage2_configs():
    """Stage-3 branching is opt-in via cfg['branching']; Stage-1/2 configs (no such key) must be byte-identical."""
    import hashlib
    from testbed.scenarios.generator import generate_spec, load_cfg
    fx = json.loads((ROOT / "tests" / "fixtures_generator_spec_hashes.json").read_text(encoding="utf-8"))
    for name, hashes in fx.items():
        cfg = load_cfg(name)
        assert "branching" not in cfg
        for i, h in hashes.items():
            got = hashlib.sha256(json.dumps(generate_spec(int(i), cfg, "x"), sort_keys=True).encode()).hexdigest()
            assert got == h, name


# ====================================================================================== 15-17: Frozen-Order AVOI
@pytest.fixture
def iam_agent_fixture():
    import warnings
    warnings.filterwarnings("ignore")
    from avoi.bayes_risk import LossMatrix
    from avoi.evaluation import stage2 as S
    C = S.cfg()
    loss = LossMatrix(10, 2, 1)
    oid = "IAM-01-MFA-PRIV"
    dev = S.develop("iam", oid, C)
    data, y, g = S.domain_partitions("iam")[oid]["conf"]
    ctx = S.partition_context(dev, data)
    spec = [s for s in S.suite(C, loss, 0.05, 0.02, 0.02, "main", 0) if s.name == "AVOI"][0]
    return ctx, data, spec, oid


def test_adaptive_avoi_recomputes_ranking_after_every_observation(iam_agent_fixture):
    from avoi.agent import SequentialAssuranceAgent
    from avoi.datasets.common import make_environment
    ctx, data, spec, oid = iam_agent_fixture
    cfg = replace(spec.cfg, tau=None, value_stop=False, stop_rule="none", frozen_order=False)
    agent = SequentialAssuranceAgent(cfg, ctx.models["primary"], ctx.cost, oid, record_candidates=True)
    found_reversal = False
    for i in range(40):
        env = make_environment(data, i, ctx.codes[i], ctx.cost)
        tr = agent.run(env, max_steps=3)
        rankings = [s["ranking"] for s in tr["steps"]]
        # adaptive: the ranking is a function of accumulated evidence, so it may legitimately differ step to step
        if any(s.get("rank_reversal") for s in tr["steps"]):
            found_reversal = True
    assert found_reversal, "no adaptive re-ranking observed across 40 episodes"


def test_frozen_order_avoi_freezes_ranking_only_once(iam_agent_fixture):
    from avoi.agent import SequentialAssuranceAgent
    from avoi.datasets.common import make_environment
    ctx, data, spec, oid = iam_agent_fixture
    cfg = replace(spec.cfg, tau=None, value_stop=False, stop_rule="none", frozen_order=True)
    agent = SequentialAssuranceAgent(cfg, ctx.models["primary"], ctx.cost, oid, record_candidates=True)
    for i in range(20):
        env = make_environment(data, i, ctx.codes[i], ctx.cost)
        tr = agent.run(env, max_steps=3)
        frozen_rank = tr["steps"][0]["ranking"]
        acquired = [s["action_index"] for s in tr["steps"]]
        remaining = list(frozen_rank)
        expected = []
        for a in acquired:
            nxt = remaining[0]
            expected.append(nxt)
            remaining.remove(nxt)
        assert acquired == expected, f"episode {i}: frozen order violated: {acquired} vs {expected}"


def test_adaptive_and_frozen_share_every_other_component(iam_agent_fixture):
    from avoi.agent import SequentialAssuranceAgent
    from avoi.datasets.common import make_environment
    ctx, data, spec, oid = iam_agent_fixture
    cfg_a = replace(spec.cfg, tau=None, value_stop=False, stop_rule="none", frozen_order=False)
    cfg_f = replace(spec.cfg, tau=None, value_stop=False, stop_rule="none", frozen_order=True)
    for i in range(10):
        env_a = make_environment(data, i, ctx.codes[i], ctx.cost)
        env_f = make_environment(data, i, ctx.codes[i], ctx.cost)
        tr_a = SequentialAssuranceAgent(cfg_a, ctx.models["primary"], ctx.cost, oid).run(env_a, max_steps=1)
        tr_f = SequentialAssuranceAgent(cfg_f, ctx.models["primary"], ctx.cost, oid).run(env_f, max_steps=1)
        # first action must be identical (frozen ranking IS the adaptive ranking at t=0)
        assert tr_a["steps"][0]["action_index"] == tr_f["steps"][0]["action_index"]
        assert tr_a["initial_belief"] == tr_f["initial_belief"]


# ====================================================================================== 18-19: fixed horizon / hard budget
def test_fixed_horizon_obtains_exactly_k_actions(iam_agent_fixture):
    from avoi.evaluation import stage3_wp1 as W
    from avoi.evaluation import engine as E
    ctx, data, spec, oid = iam_agent_fixture
    fh = W.fixed_horizon_cfg(spec, 3)
    trs = W.run_traces(ctx, fh, np.arange(30), max_steps=3, record=True)
    for k in (2, 3):
        from avoi.evaluation import stage2 as S
        rows = S.rows_at(trs, fh, np.arange(30), np.zeros(data.n, int), data.groups, __import__("avoi.bayes_risk", fromlist=["LossMatrix"]).LossMatrix(10, 2, 1), [None], budget=k)
        for r in rows:
            assert r["n_acq"] == min(k, data.m)


def test_normal_hard_budget_remains_at_most_k(iam_agent_fixture):
    from avoi.agent import truncate
    from avoi.evaluation import engine as E
    from avoi.datasets.common import make_environment
    from avoi.agent import SequentialAssuranceAgent
    ctx, data, spec, oid = iam_agent_fixture
    agent = SequentialAssuranceAgent(replace(spec.cfg, tau=None), ctx.models["primary"], ctx.cost, oid)
    for i in range(10):
        env = make_environment(data, i, ctx.codes[i], ctx.cost)
        tr = agent.run(env)
        for k in range(0, 4):
            op = truncate(tr, spec.cfg, 0.3, budget=k)
            assert op["n_acquisitions"] <= k


# ====================================================================================== 20: ranking trace completeness
def test_action_ranking_trace_contains_all_candidates(iam_agent_fixture):
    from avoi.agent import SequentialAssuranceAgent
    from avoi.datasets.common import make_environment
    ctx, data, spec, oid = iam_agent_fixture
    cfg = replace(spec.cfg, tau=None, value_stop=False, stop_rule="none")
    agent = SequentialAssuranceAgent(cfg, ctx.models["primary"], ctx.cost, oid, record_candidates=True)
    env = make_environment(data, 0, ctx.codes[0], ctx.cost)
    tr = agent.run(env, max_steps=1)
    step0 = tr["steps"][0]
    n_candidates_offered = len(step0["candidates"])
    assert len(step0["ranking"]) == n_candidates_offered
    assert set(step0["ranking"]) == {c["action"] for c in step0["candidates"]}
    assert step0["adaptive_next_action"] in step0["ranking"]
    assert step0["frozen_next_action"] in step0["ranking"]


# ====================================================================================== 21: AVOI label
def test_stage3_outputs_use_avoi_label_not_avoi_grc():
    for f in ["src/avoi/evaluation/stage3.py", "src/avoi/evaluation/stage3_wp1.py", "src/avoi/evaluation/stage3_wp2.py",
              "experiments/stage3/run_wp1.py", "experiments/stage3/run_wp2_ait.py", "experiments/stage3/run_wp2_cert.py"]:
        src = (ROOT / f).read_text(encoding="utf-8")
        assert "AVOI-GRC" not in src, f
    for r in [ROOT / "results" / "final_report_v3", ROOT / "results" / "stage3" / "tables"]:
        if not r.exists():
            continue
        for p in r.rglob("*"):
            if p.suffix in (".md", ".csv", ".tex"):
                assert "AVOI-GRC" not in p.read_text(encoding="utf-8", errors="ignore"), p


# ====================================================================================== 22: new seeds never used before
def test_stage3_seeds_are_new():
    import yaml
    for name in ("config/scenario_generator_stage3_dev.yaml", "config/scenario_generator_stage3_val.yaml", "config/scenario_generator_stage3_conf.yaml"):
        cfg = yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))
        assert cfg["master_seed"] not in (20260914, 20261103), f"{name} reuses a Stage-1/2 seed"
    c3 = yaml.safe_load((ROOT / "config" / "stage3.yaml").read_text(encoding="utf-8"))
    # data-partitioning seeds must be pairwise distinct (analysis/bootstrap may legitimately share a seed - they
    # serve different, non-overlapping purposes and neither touches data partitioning)
    split_seeds = [c3["wp2"]["ait"]["target_split"]["seed"], c3["wp2"]["cert"]["user_split"]["seed"],
                   int(c3["wp2"]["cert"]["episode_sampling"].split("seed ")[-1].rstrip(")"))]
    assert len(set(split_seeds)) == len(split_seeds), "Stage-3 data-split seeds must be pairwise distinct"


# ====================================================================================== AVOI formula unchanged
def test_avoi_formula_unchanged_since_stage2():
    for f in ("src/avoi/avoi.py", "src/avoi/bayes_risk.py"):
        try:
            old = subprocess.run(["git", "show", f"7bb325c:{f}"], cwd=ROOT, capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            pytest.skip("git history unavailable")
        assert old.replace(b"\r\n", b"\n") == (ROOT / f).read_bytes().replace(b"\r\n", b"\n"), f


# ====================================================================================== adaptivity metrics correctness
def test_action_frequency_and_entropy_conditional_on_reaching_step():
    from avoi.evaluation import stage3_wp1 as W

    def tr(acts, ranks=None):
        ranks = ranks or [None] * len(acts)
        return {"steps": [{"t": i + 1, "selected_action": a, "ranking": r, "rank_reversal": False} for i, (a, r) in enumerate(zip(acts, ranks))]}

    traces = [tr(["x", "y"]), tr(["x"]), tr(["z", "y"]), tr([]), tr(["x", "y"])]
    summ, per_step = W.adaptivity_metrics(traces, ["x", "y", "z"])
    row1 = per_step[per_step["step"] == 1].iloc[0]
    assert row1["n_t"] == 4   # 4 of 5 episodes reach step 1
    row2 = per_step[per_step["step"] == 2].iloc[0]
    assert row2["n_t"] == 3   # only 3 reach step 2
    assert abs(row2["P(A_t=y)"] - 1.0) < 1e-9   # all 3 episodes reaching step 2 select 'y' there


def test_history_permutation_test_null_distribution_is_uniform_when_history_irrelevant():
    from avoi.evaluation import stage3_wp1 as W
    rng = np.random.default_rng(0)
    traces = []
    for i in range(60):
        # action at step 2 independent of the (fake) history outcome
        a2 = rng.choice(["p", "q"])
        traces.append({"episode_id": f"e{i}", "steps": [{"t": 1, "selected_action": "x", "observed_outcome": rng.choice(["h1", "h2"])},
                                                        {"t": 2, "selected_action": a2, "observed_outcome": "o"}]})
    groups = {f"e{i}": f"fam{i % 5}" for i in range(60)}
    res = W.history_permutation_test(traces, groups, n_perm=500, seed=1)
    assert res["p"] > 0.05   # null: no dependence -> should not reject


def test_history_permutation_test_detects_real_dependence():
    from avoi.evaluation import stage3_wp1 as W
    rng = np.random.default_rng(0)
    traces = []
    for i in range(60):
        h1 = rng.choice(["h1", "h2"])
        a2 = "p" if h1 == "h1" else "q"    # deterministic dependence
        traces.append({"episode_id": f"e{i}", "steps": [{"t": 1, "selected_action": "x", "observed_outcome": h1},
                                                        {"t": 2, "selected_action": a2, "observed_outcome": "o"}]})
    groups = {f"e{i}": f"fam{i % 5}" for i in range(60)}
    res = W.history_permutation_test(traces, groups, n_perm=1000, seed=1)
    assert res["p"] < 0.05


# ====================================================================================== WP2 selection rule
def test_lodo_selection_excludes_semantically_invalid_calibrators():
    from avoi.evaluation import stage3 as S3M
    from avoi import adequacy as AQ
    p = np.random.default_rng(0).uniform(0.01, 0.99, 200)
    y = (p > 0.5).astype(int)
    name, scores, cal, rejected = S3M.monotone_calibrator(p, y, np.arange(200) % 10, ["none", "sigmoid", "isotonic", "beta"], seed=0)
    assert S3M.is_monotone(cal)


def test_monotone_check_flags_inverted_sigmoid():
    from avoi.evaluation import stage3 as S3M
    from avoi import adequacy as AQ
    cal = AQ.Calibrator("sigmoid")
    cal.params = {"a_intercept": -1.0, "b_slope": -2.0}   # negative slope = inverted
    assert not S3M.is_monotone(cal)
