"""Scenario reproducibility and testbed data integrity (no live Docker required)."""
import json
from pathlib import Path

import pytest
import yaml

from testbed.scenarios.generator import generate_spec, load_cfg

ROOT = Path(__file__).resolve().parents[1]


def test_scenario_generation_is_deterministic():
    cfg = load_cfg()
    for i in (0, 7, 123, 319):
        assert json.dumps(generate_spec(i, cfg), sort_keys=True) == json.dumps(generate_spec(i, cfg), sort_keys=True)
    assert generate_spec(1, cfg)["seed"] != generate_spec(2, cfg)["seed"]


def test_scenario_family_assignment():
    cfg = load_cfg()
    spf = cfg["scenarios_per_family"]
    assert generate_spec(spf - 1, cfg)["family_id"] == 0 and generate_spec(spf, cfg)["family_id"] == 1


def test_objectives_config_has_at_least_six_objectives_and_declared_outcomes():
    cfg = yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))
    cat = yaml.safe_load((ROOT / "config" / "evidence_actions.yaml").read_text(encoding="utf-8"))["iam_actions"]
    assert len(cfg["objectives"]) >= 6
    for o in cfg["objectives"]:
        assert o["framework_refs"] and o["operational_predicate"] and o["ground_truth_source"]
        for a in o["actions"]:
            assert a["id"] in cat and len(a["outcomes"]) >= 2
            assert set(a["outcomes"].values()) <= {"supports_satisfied", "supports_violated", "neutral"}


def test_collected_outcomes_are_declared_and_evidence_store_has_no_labels():
    store = ROOT / "data" / "processed" / "iam" / "evidence_store"
    files = sorted(store.glob("scn-*.json"))[:25]
    if not files:
        pytest.skip("testbed evidence not collected")
    cfg = yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))
    declared = {a["id"]: set(a["outcomes"]) for o in cfg["objectives"] for a in o["actions"]}
    for f in files:
        st = json.loads(f.read_text(encoding="utf-8"))
        assert "labels" not in st and "detail" not in st
        for aid, ob in st["observations"].items():
            assert ob["outcome"] in declared[aid]
            for key in ("timestamp_utc", "objective_id", "scope", "provenance", "raw_artifact_ref", "parser",
                        "acquisition_seconds", "records", "bytes_read", "privacy_categories", "source"):
                assert key in ob
