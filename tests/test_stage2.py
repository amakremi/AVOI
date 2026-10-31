"""Stage-2 tests: adequacy isolation, gate behaviour, UAR/coverage/budget definitions, action statistics, archive integrity."""
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from avoi import adequacy as AQ
from avoi.agent import PolicyConfig, SequentialAssuranceAgent, truncate
from avoi.bayes_risk import HUMAN_REVIEW, LossMatrix
from avoi.datasets.common import make_environment
from avoi.evaluation import engine as E
from avoi.evaluation import stage2 as S
from avoi.evaluation import stage2_analysis as SA

ROOT = Path(__file__).resolve().parents[1]


def fake_partitions(synth, scramble_conf=False, scramble_val=False):
    data, y = synth
    n = data.n
    dev, val, conf = np.arange(0, 120), np.arange(120, 180), np.arange(180, n)
    yv, yc = y[val].copy(), y[conf].copy()
    if scramble_val:
        yv = 1 - yv
    if scramble_conf:
        yc = 1 - yc
    return {"OBJ": {"dev": (data.subset(dev), y[dev], data.groups[dev]), "val": (data.subset(val), yv, data.groups[val]),
                    "conf": (data.subset(conf), yc, data.groups[conf])}}


@pytest.fixture
def small_cfg(monkeypatch):
    C = S.cfg()
    C["adequacy"]["bootstrap"]["n_resamples"] = 60
    C["adequacy"]["primary"]["support"].update(min_violated_cases=5, min_satisfied_cases=5, min_groups=3, min_groups_with_violation=2)
    monkeypatch.setattr(S, "cfg", lambda: C)
    monkeypatch.setattr(S, "dev_folds", lambda domain, data: [(np.flatnonzero(data.groups % 3 != k), np.flatnonzero(data.groups % 3 == k)) for k in range(3)])
    return C


def develop_validate(synth, C, **kw):
    S._CACHE["synthetic"] = fake_partitions(synth, **kw)
    dev = S.develop("synthetic", "OBJ", C)
    val = S.validate("synthetic", "OBJ", dev, C)
    return dev, val


def test_final_test_labels_cannot_influence_adequacy_or_calibration(synth, small_cfg):
    d1, v1 = develop_validate(synth, small_cfg)
    d2, v2 = develop_validate(synth, small_cfg, scramble_conf=True)
    assert v1["decision"].status == v2["decision"].status
    assert v1["primary"]["metrics"] == v2["primary"]["metrics"]
    assert d1["selection"]["selected_calibrator"] == d2["selection"]["selected_calibrator"]
    assert d1["selection"]["calibrator_params"] == d2["selection"]["calibrator_params"]
    # validation labels DO drive adequacy (sanity: the gate reads the validation partition)
    _, v3 = develop_validate(synth, small_cfg, scramble_val=True)
    assert v3["primary"]["metrics"]["AUROC"] != v1["primary"]["metrics"]["AUROC"]
    # calibration selection uses development data only: scrambling validation labels leaves it unchanged
    d4, _ = develop_validate(synth, small_cfg, scramble_val=True)
    assert d4["selection"]["calibrator_params"] == d1["selection"]["calibrator_params"]


def test_gate_thresholds_come_from_config():
    pol = AQ.load_policy()
    m = {"n_violated": 50, "n_satisfied": 50, "BSS": 0.2, "ECE": 0.08, "calibration_slope": 1.0}
    boot = {"ci": {"AUROC": (0.7, 0.8), "PR_skill": (0.1, 0.3)}, "n_groups": 30}
    assert AQ.decide("m", m, boot, pol, "none").status == AQ.VALIDATED
    strict = copy.deepcopy(pol)
    strict["primary"]["calibration"]["ece_le"] = 0.05
    assert AQ.decide("m", m, boot, strict, "none").status == AQ.RESTRICTED
    assert AQ.decide("m", m, {**boot, "ci": {"AUROC": (0.45, 0.6), "PR_skill": (0.1, 0.3)}}, pol, "none").status == AQ.UNSUPPORTED
    few = {**m, "n_violated": pol["primary"]["support"]["min_violated_cases"] - 1}
    d = AQ.decide("m", few, boot, pol, "none")
    assert d.status == AQ.RESTRICTED and d.reason == AQ.SUPPORT_REASON
    src = (ROOT / "src" / "avoi" / "adequacy.py").read_text(encoding="utf-8")
    assert "0.10" not in src and "ece_le\"] =" not in src   # thresholds are not hard-coded in the module


@pytest.mark.parametrize("status", [AQ.RESTRICTED, AQ.UNSUPPORTED])
def test_inadequate_models_never_decide_autonomously(synth, status):
    data, y = synth
    ctx = E.make_context(data, y, np.arange(160), ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    dec = AQ.AdequacyDecision("m", status, AQ.REASON[status], status != AQ.UNSUPPORTED, False, True, ["calibration"], {}, {"AUROC": (0.4, 0.6), "PR_skill": (-0.1, 0.1)})
    cfg = PolicyConfig("AVOI", "avoi", LossMatrix(), 0.05, 0.02, 0.02, "risk", tau=1.0)   # tau=1 would stop immediately with an autonomous decision
    agent = SequentialAssuranceAgent(cfg, ctx.models["tan"], ctx.cost, "OBJ")
    for i in range(160, 240):
        env = make_environment(data, i, ctx.codes[i], ctx.cost)
        tr = agent.run(env, adequacy=dec, adequacy_mode="enforced")
        assert tr["final_decision"] == HUMAN_REVIEW
        assert tr["stop_reason"] == AQ.REASON[status] and tr["gate_reason"] == AQ.REASON[status]
        assert tr["n_acquisitions"] == 0 and tr["autonomous_allowed"] is False
        for key in ("model_id", "calibrator", "adequacy_status", "adequacy_metrics", "adequacy_policy_version", "autonomous_allowed", "gate_reason"):
            assert key in tr
    rows = [{"decision": "Assured", "y": 0, "loss": 10.0, "n_acq": 2, "cost": 1.0, "privacy": 0.2, "delay": 0.1, "reason": "threshold",
             "seconds": 0.1, "records": 3, "bytes": 5},
            {"decision": "NotAssured", "y": 1, "loss": 2.0, "n_acq": 1, "cost": 0.5, "privacy": 0.1, "delay": 0.1, "reason": "threshold",
             "seconds": 0.1, "records": 3, "bytes": 5}]
    g = S.gate_rows(rows, dec, LossMatrix())
    assert all(r["decision"] == HUMAN_REVIEW and r["reason"] == AQ.REASON[status] for r in g)


def test_diagnostic_mode_equals_ungated_and_does_not_affect_enforced(synth):
    data, y = synth
    ctx = E.make_context(data, y, np.arange(160), ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    dec = AQ.AdequacyDecision("m", AQ.RESTRICTED, AQ.REASON[AQ.RESTRICTED], True, False, True, [], {}, {"AUROC": (0.6, 0.7), "PR_skill": (0.1, 0.2)})
    ok = replace(dec, status=AQ.VALIDATED, reason="ALL")
    cfg = PolicyConfig("AVOI", "avoi", LossMatrix(), 0.05, 0.02, 0.02, "risk", tau=0.2)
    agent = SequentialAssuranceAgent(cfg, ctx.models["tan"], ctx.cost, "OBJ", record_candidates=False)
    for i in range(160, 200):
        base = agent.run(make_environment(data, i, ctx.codes[i], ctx.cost))
        diag = agent.run(make_environment(data, i, ctx.codes[i], ctx.cost), adequacy=dec, adequacy_mode="diagnostic")
        enf = agent.run(make_environment(data, i, ctx.codes[i], ctx.cost), adequacy=dec, adequacy_mode="enforced")
        val = agent.run(make_environment(data, i, ctx.codes[i], ctx.cost), adequacy=ok, adequacy_mode="enforced")
        assert diag["steps"] == base["steps"] and diag["final_decision"] == base["final_decision"]
        assert enf["final_decision"] == HUMAN_REVIEW
        assert val["steps"] == base["steps"] and val["final_decision"] == base["final_decision"]


def test_uar_denominator_constant_across_thresholds(synth):
    data, y = synth
    ctx = E.make_context(data, y, np.arange(160), ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    spec = E.method_suite(LossMatrix(), 0.05, 0.02, 0.02, 1e-3, 0)[0]
    idx = np.arange(160, 240)
    trs = E.run_trajectories(ctx, spec, idx)
    cur = S.curve_counts(S.rows_at(trs, spec, idx, y, data.groups, LossMatrix(), list(np.linspace(0, 1, 21))))
    assert cur["n_viol"].nunique() == 1 and int(cur["n_viol"].iloc[0]) == int((y[idx] == 0).sum())
    assert (cur["n_unsafe"] <= cur["n_viol"]).all() and (cur["n_unsafe"] <= cur["n_assured"]).all()
    assert cur["n"].nunique() == 1
    # coverage uses all episodes; UAR keeps HumanReview Y=0 episodes in the denominator
    df = pd.DataFrame([{"decision": "HumanReview", "y": 0}, {"decision": "Assured", "y": 0}, {"decision": "NotAssured", "y": 1},
                       {"decision": "Assured", "y": 1}])
    r = SA.rates(df)
    assert r["UAR"] == 0.5 and r["FAA"] == 0.5 and r["coverage"] == 0.75
    # no special terminal rule at coverage = 1: tau=1 operating point uses the same counting
    full = cur[np.isclose(cur["tau"].astype(float), 1.0)].iloc[0]
    assert full["n_viol"] == cur["n_viol"].iloc[0]


def test_hard_budget_is_at_most_k(synth):
    data, y = synth
    ctx = E.make_context(data, y, np.arange(160), ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    spec = E.method_suite(LossMatrix(), 0.05, 0.02, 0.02, 1e-3, 0)[0]
    trs = E.run_trajectories(ctx, spec, np.arange(160, 240))
    early = 0
    for tr in trs:
        full = truncate(tr, spec.cfg, 0.3)
        for k in range(0, 5):
            op = truncate(tr, spec.cfg, 0.3, budget=k)
            assert op["n_acquisitions"] <= k
            if full["n_acquisitions"] < k:
                assert op["n_acquisitions"] == full["n_acquisitions"] and op["decision"] == full["decision"]
                early += 1
    assert early > 0


def test_action_frequency_conditional_and_single_action_flag():
    def tr(obj, acts):
        return {"objective_id": obj, "n_acquisitions": len(acts), "steps": [{"t": i + 1, "selected_action": a} for i, a in enumerate(acts)]}
    traces = [tr("A", ["x", "y"]), tr("A", ["x"]), tr("A", ["z", "y"]), tr("A", []), tr("B", ["only"]), tr("B", ["only"])]
    f = SA.action_frequency(traces)
    assert f[("A", 1)]["n_t"] == 3 and f[("A", 2)]["n_t"] == 2
    assert f[("A", 2)]["freq"]["y"] == 1.0                     # conditional on reaching step 2 (not / 4 episodes)
    assert abs(f[("A", 1)]["freq"]["x"] - 2 / 3) < 1e-12
    assert SA.single_action_objectives(traces) == {"B"}


def test_stage1_archive_unchanged_and_freeze_hash_preserved():
    man_p = ROOT / "results" / "stage1_ungated" / "MANIFEST.json"
    if not man_p.exists():
        pytest.skip("Stage-1 archive not created")
    man = json.loads(man_p.read_text(encoding="utf-8"))
    for f in man["files"]:
        assert hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]
    fr = json.loads((ROOT / "results" / "stage1_ungated" / "EXPERIMENT_FREEZE.json").read_text(encoding="utf-8"))
    assert fr["hashes"]["combined_sha256"].startswith("4370311e")
    assert man["original_freeze_combined_sha256"] == fr["hashes"]["combined_sha256"]


def test_confirmation_requires_frozen_adequacy_decisions(tmp_path, monkeypatch, synth, small_cfg):
    S._CACHE["synthetic"] = fake_partitions(synth)
    monkeypatch.setattr(S, "S2", tmp_path)
    with pytest.raises(FileNotFoundError):
        S.run_domain_objective({"domain": "synthetic", "objective": "OBJ", "phase": "confirm"})


def test_enforced_view_applies_identical_rule_to_every_model_based_method():
    methods = ["AVOI", "B0-AllEvidence", "B1-FixedChecklist", "B4-InformationGain", "B5-GenericVOI", "B6-ConfidenceThreshold", "B2-Random[s3]"]
    rows = [{"method": m, "decision": d, "y": y, "loss": 1.0, "n_acq": 2, "cost": 0.3, "privacy": 0.1, "delay": 0.1, "reason": "threshold",
             "seconds": 0.1, "records": 1, "bytes": 1} for m in methods for d, y in (("Assured", 0), ("NotAssured", 0), ("HumanReview", 1))]
    bad = AQ.AdequacyDecision("m", AQ.UNSUPPORTED, AQ.REASON[AQ.UNSUPPORTED], False, True, True)
    g = S.gate_rows(rows, bad, LossMatrix())
    assert {r["method"] for r in g} == set(methods)
    assert all(r["decision"] == HUMAN_REVIEW and r["n_acq"] == 0 and r["adequacy_reason"] == AQ.REASON[AQ.UNSUPPORTED] for r in g)
    assert all(r["ungated_decision"] == o["decision"] for r, o in zip(g, rows))
    ok = replace(bad, status=AQ.VALIDATED, reason="ALL_PRIMARY_ADEQUACY_CONDITIONS_MET")
    assert [r["decision"] for r in S.gate_rows(rows, ok, LossMatrix())] == [r["decision"] for r in rows]
    # model inadequacy never produces NotAssured
    assert not any(r["decision"] == "NotAssured" for r in g)


def test_adequacy_sensitivity_overrides_do_not_mutate_primary_policy():
    pol = AQ.load_policy()
    before = copy.deepcopy(pol)
    m = {"n_violated": 50, "n_satisfied": 50, "BSS": 0.2, "ECE": 0.08, "calibration_slope": 1.0}
    boot = {"ci": {"AUROC": (0.7, 0.8), "PR_skill": (0.1, 0.3)}, "n_groups": 30}
    assert AQ.decide("m", m, boot, pol, "none", overrides={("calibration", "ece_le"): 0.05}).status == AQ.RESTRICTED
    assert pol == before
    assert AQ.decide("m", m, boot, pol, "none").status == AQ.VALIDATED


def test_asymmetric_loss_ablation_changes_only_the_loss():
    C = S.cfg()
    loss = LossMatrix(C["loss"]["primary"]["false_assurance"], C["loss"]["primary"]["false_non_assurance"], C["loss"]["primary"]["human_review"])
    abl = {s.name: s for s in S.suite(C, loss, 0.05, 0.02, 0.02, "ablation", 0)}
    a, s = abl["AVOI"].cfg, abl["A1-NoAsymmetricLoss"].cfg
    assert s.loss.false_assurance == s.loss.false_non_assurance and a.loss.false_assurance > a.loss.false_non_assurance
    assert replace(s, name="AVOI", loss=a.loss) == a
    assert abl["AVOI"].model_kind == abl["A1-NoAsymmetricLoss"].model_kind == "primary"


def test_avoi_formula_unchanged_since_stage1():
    import subprocess
    for f in ("src/avoi/avoi.py", "src/avoi/bayes_risk.py"):
        try:
            old = subprocess.run(["git", "show", f"7bb325c:{f}"], cwd=ROOT, capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            pytest.skip("git history unavailable")
        assert old.replace(b"\r\n", b"\n") == (ROOT / f).read_bytes().replace(b"\r\n", b"\n"), f


def _fake_episode_frame():
    rng = np.random.default_rng(0)
    rows = []
    for dom in ("iam",):
        for m in ("AVOI", "B1-FixedChecklist"):
            for mm, lvl in (("none", 1.0), ("mcar", 0.4)):
                for i in range(40):
                    y = int(rng.uniform() < 0.6)
                    d = ["Assured", "NotAssured", HUMAN_REVIEW][rng.integers(0, 3)]
                    rows.append({"domain": dom, "objective": "O", "episode_id": f"e{i}", "group": f"g{i % 8}", "y": y, "method": m,
                                 "decision": d, "belief": rng.uniform(), "loss": LossMatrix().realized_loss(d, y), "n_acq": int(rng.integers(0, 4)),
                                 "cost": rng.uniform(), "privacy": rng.uniform(), "delay": 0.0, "seconds": 0.0, "initial_entropy": 1.0,
                                 "acquisition_required": bool(rng.uniform() < 0.8), "experiment": "primary", "condition": "fa=10.0|lam=0.05|mu=0.02|nu=0.02",
                                 "start": "cold" if mm == "none" else "partial", "shift": "none", "missing_mode": mm, "missing_level": lvl,
                                 "reason": "threshold"})
    return pd.DataFrame(rows)


def test_stage2_tables_include_uar_coverage_and_group_bootstrap():
    from avoi.evaluation import stage2_tables as T
    df = _fake_episode_frame()
    mt = T.missingness_table(df, df.assign(adequacy_mode="enforced"))
    for col in ("UAR", "FAA", "coverage", "human_review_rate", "mean_acquisitions", "cost", "privacy", "expected_loss"):
        assert col in mt.columns
    cold = df[(df["start"] == "cold") & (df["method"] == "AVOI")]
    s = T.boot_summary(cold, n_boot=200)
    r = SA.rates(cold)
    assert abs(s["point"]["UAR"] - r["UAR"]) < 1e-12 and abs(s["point"]["coverage"] - r["coverage"]) < 1e-12
    assert s["ci"]["UAR"][0] <= r["UAR"] <= s["ci"]["UAR"][1]
    assert s["n_groups"] == 8
    z = T.zero_acq_table(df.assign(experiment="primary"))
    assert {"P(N_acq=0)", "E[N_acq | N_acq>0]", "acq_required_UAR", "acq_required_coverage"} <= set(z.columns)


