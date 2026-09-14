"""Automated leakage controls (see docs/LEAKAGE_CONTROLS.md)."""
import ast
import builtins
import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from avoi.actions import EvidenceEnvironment
from avoi.agent import PolicyConfig, SequentialAssuranceAgent
from avoi.bayes_risk import LossMatrix
from avoi.datasets.common import Discretizer, make_environment
from avoi.evaluation import engine as E
from avoi.models.discriminative import CalibratedLogisticModel

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "avoi"


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


# ------------------------------------------------------------------ static isolation
PLANNER_MODULES = ["agent.py", "avoi.py", "actions.py", "bayes_risk.py", "costs.py", "privacy.py", "models/tan.py",
                   "models/discriminative.py", "datasets/common.py", "datasets/iam.py", "datasets/ait_episodes.py",
                   "datasets/cert.py", "baselines/llm_planner.py"]


@pytest.mark.parametrize("mod", PLANNER_MODULES)
def test_planner_and_evidence_modules_never_import_labels(mod):
    p = SRC / mod
    if not p.exists():
        pytest.skip(f"{mod} not present")
    assert "avoi.evaluation.labels" not in imports_of(p)
    text = p.read_text(encoding="utf-8")
    assert "episode_labels.csv" not in text or mod == "datasets/ait_episodes.py" or mod == "datasets/cert.py"


def test_collectors_never_read_hidden_state_or_database():
    tree = ast.parse((ROOT / "testbed" / "evidence_collectors" / "collectors.py").read_text(encoding="utf-8"))
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant))]
    src = ast.unparse(tree)                               # code only (module docstring and comments removed)
    assert "hidden" not in src and "systems_of_record" not in src
    assert "db()" not in src and "pg8000" not in src and "ground_truth" not in src
    assert "testbed.oracle" not in imports_of(ROOT / "testbed" / "evidence_collectors" / "collectors.py")


def test_label_writers_are_separate_from_evidence_stores():
    for dom in ("iam", "ait", "cert"):
        store = ROOT / "data" / "processed" / dom
        if not store.exists():
            continue
        gt = store / "ground_truth"
        for f in store.rglob("*"):
            if f.is_file() and "ground_truth" not in f.parts:
                assert "labels" not in f.name or f.suffix == ".py"


def test_ait_evidence_index_has_no_labels_and_excludes_attacker_hosts():
    db = ROOT / "data" / "processed" / "ait" / "russellmitchell_evidence.sqlite"
    if not db.exists():
        pytest.skip("AIT index not built")
    con = sqlite3.connect(db)
    for (tbl,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({tbl})")]
        assert cols == ["ts", "host", "nbytes", "f1", "f2"], cols
        hosts = {h for (h,) in con.execute(f"SELECT DISTINCT host FROM {tbl}")}
        assert not any(h.startswith(("attacker", "ext_user", "internal_employee", "remote_employee")) for h in hosts)
    store = json.loads((ROOT / "data" / "processed" / "ait" / "evidence_store.json").read_text()[:20000] + "]" if False else
                       (ROOT / "data" / "processed" / "ait" / "evidence_store.json").read_text())
    assert all(set(r) - {"testbed", "w0"} <= {"vpn", "dns", "web_access", "web_error", "auth", "audit", "ids", "mail", "syslog", "monitoring"}
               for r in store[:50])


def test_cert_store_contains_no_answer_key():
    db = ROOT / "data" / "processed" / "cert" / "cert_evidence.sqlite"
    if not db.exists():
        pytest.skip("CERT store not built")
    con = sqlite3.connect(db)
    tables = {t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"logon", "device", "file", "email", "http", "ldap", "psychometric"}
    for t in tables:
        cols = {r[1].lower() for r in con.execute(f"PRAGMA table_info({t})")}
        assert not cols & {"y", "label", "insider", "scenario", "answer", "malicious"}


def test_evidence_loaders_do_not_open_ground_truth(monkeypatch):
    real_open = builtins.open
    real_read = Path.read_text

    def guard_open(file, *a, **k):
        assert "ground_truth" not in str(file) and "hidden" not in str(file), f"evidence loader opened {file}"
        return real_open(file, *a, **k)

    def guard_read(self, *a, **k):
        assert "ground_truth" not in str(self) and "hidden" not in str(self), f"evidence loader read {self}"
        return real_read(self, *a, **k)

    monkeypatch.setattr(builtins, "open", guard_open)
    monkeypatch.setattr(Path, "read_text", guard_read)
    loaded = 0
    for mod, fn, marker in [("avoi.datasets.iam", "load_iam", ROOT / "data/processed/iam/evidence_store"),
                            ("avoi.datasets.ait_episodes", "load_ait", ROOT / "data/processed/ait/evidence_store.json"),
                            ("avoi.datasets.cert", "load_cert", ROOT / "data/processed/cert/evidence_store.json")]:
        if marker.exists():
            objs = getattr(__import__(mod, fromlist=[fn]), fn)()
            for d in objs.values():
                assert not hasattr(d, "y") and not hasattr(d, "labels")
            loaded += 1
    if loaded == 0:
        pytest.skip("no evidence stores built")


# ------------------------------------------------------------------ dynamic isolation
def test_test_labels_cannot_influence_planner(synth):
    """Given the same trained model, planner traces on test episodes are invariant to the test labels."""
    data, y = synth
    tr = np.arange(160)
    ctx = E.make_context(data, y, tr, ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    y2 = y.copy()
    y2[160:] = 1 - y2[160:]                               # scramble TEST labels only
    ctx2 = E.make_context(data, y2, tr, ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    suite = {s.name: s for s in E.method_suite(LossMatrix(), 0.05, 0.02, 0.02, 1e-3, 1)}
    for name in ("AVOI-GRC", "B4-InformationGain", "B6-ConfidenceThreshold"):
        a = E.run_trajectories(ctx, suite[name], np.arange(160, 240))
        b = E.run_trajectories(ctx2, suite[name], np.arange(160, 240))
        assert [t["steps"] for t in a] == [t["steps"] for t in b]
        assert [t["final_decision"] for t in a] == [t["final_decision"] for t in b]


def test_preprocessing_fitted_on_training_fold_only(synth):
    data, y = synth
    tr = np.arange(160)
    num = data.subset(np.arange(data.n))
    num.kind = "numeric"
    num.values = np.random.default_rng(0).gamma(2.0, 3.0, size=data.values.shape)
    num.actions = [a.__class__(a.action_id, a.objective_id, a.source_type, ("no_data", "low", "elevated", "high"), (0, 1, 0, -1), a.privacy_schema)
                   for a in data.actions]
    ctx = E.make_context(num, y, tr, ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    corrupted = num.subset(np.arange(num.n))
    corrupted.values = num.values.copy()
    corrupted.values[160:] *= 1000.0                      # change TEST evidence only
    corrupted.records = num.records.copy()
    corrupted.records[160:] *= 1000.0
    ctx2 = E.make_context(corrupted, y, tr, ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    assert np.allclose(ctx.cost.C, ctx2.cost.C)
    assert np.array_equal(ctx.codes[tr], ctx2.codes[tr])
    for c1, c2 in zip(ctx.models["tan"].cpt, ctx2.models["tan"].cpt):
        assert np.allclose(c1, c2)
    d1 = Discretizer().fit(num.values[tr])
    d2 = Discretizer().fit(corrupted.values[tr])
    assert d1.t == d2.t


def test_calibration_isolated_from_test_data(synth):
    data, y = synth
    tr = np.arange(160)
    K = [len(a.outcomes) for a in data.actions]
    m1 = CalibratedLogisticModel(K, n_masks=4, seed=3).fit(data.values[tr], y[tr])
    y2 = y.copy()
    y2[160:] = 1 - y2[160:]
    m2 = CalibratedLogisticModel(K, n_masks=4, seed=3).fit(data.values[tr], y2[tr])
    for ev in [(), ((0, 1),), ((1, 0), (2, 2))]:
        assert m1.posterior(ev) == pytest.approx(m2.posterior(ev))


def test_hidden_evidence_unreadable_until_acquired(synth):
    data, y = synth
    tr = np.arange(160)
    ctx = E.make_context(data, y, tr, ["tan"], {}, "B", None, 0, 0, hps={"tan": {"alpha": 1.0}})
    env = make_environment(data, 170, ctx.codes[170], ctx.cost, initially={1})
    assert env.observed() == ((1, int(ctx.codes[170][1])),)
    assert set(env.available_actions()) == {0, 2, 3}
    public = {n for n in dir(env) if not n.startswith("_")}
    assert public == {"acquire", "actions", "available_actions", "episode_id", "log", "observed", "pre_acquired"}
    assert not any(isinstance(getattr(env, n), np.ndarray) for n in public)
    obs = env.acquire(2)
    assert obs.outcome_index == int(ctx.codes[170][2])
    assert (2, obs.outcome_index) in env.observed()
    with pytest.raises(ValueError):
        env.acquire(2)


def test_outer_and_inner_splits_are_grouped():
    from avoi.evaluation.runner import load_domain, unit_strata
    for dom in ("iam", "ait", "cert"):
        try:
            objs, labels = load_domain(dom)
        except FileNotFoundError:
            continue
        d = next(iter(objs.values()))
        y = labels[d.objective_id]
        folds = E.outer_folds(dom, d, unit_strata(dom, objs, labels), 20260914)
        covered = np.concatenate([te for _, te in folds])
        assert sorted(covered) == list(range(d.n))
        for tr, te in folds:
            assert not set(d.groups[tr]) & set(d.groups[te])
            for itr, iva in E.inner_folds(dom, d, tr, y, 20260914):
                assert set(itr) | set(iva) <= set(tr)
                if dom != "ait":
                    assert not set(d.groups[itr]) & set(d.groups[iva])
