"""Live end-to-end demonstration: AVOI-GRC acquiring evidence from the RUNNING Docker testbed.

For the scenarios whose realms were kept alive by testbed/run_testbed.py (--keep-realms), the agent invokes the real
evidence collectors (Keycloak Admin API, evidence repository, Linux host) at acquisition time. The evidence model and
cost model are fitted on all OTHER scenarios' stored evidence (the live scenarios are excluded from training). The
outcome returned live for every acquired action is compared with the outcome stored in the evidence store that the
replay experiments used (consistency check). Live evidence for the host action depends on the current app-host state,
which is only guaranteed for the last scenario applied; mismatches are reported, not hidden.
"""
from __future__ import annotations

import json
import time

import numpy as np
import yaml

from common import ROOT

from avoi.actions import EvidenceEnvironment, EvidenceObservation
from avoi.agent import PolicyConfig, SequentialAssuranceAgent
from avoi.bayes_risk import LossMatrix
from avoi.costs import CostModel
from avoi.datasets.iam import load_iam
from avoi.evaluation.labels import load_labels
from avoi.models.tan import DiscreteBayesNet
from testbed.evidence_collectors.collectors import IAMCollectors
from testbed.keycloak.kc import KeycloakAdmin

LIVE = ["scn-0318", "scn-0319"]

if __name__ == "__main__":
    params = yaml.safe_load((ROOT / "config" / "assurance_objectives.yaml").read_text(encoding="utf-8"))["assessment_parameters"]
    lcfg = yaml.safe_load((ROOT / "config" / "loss_matrix.yaml").read_text(encoding="utf-8"))
    w = lcfg["preference_weights"]
    loss = LossMatrix()
    kc = KeycloakAdmin()
    objs = load_iam()
    report = {"scenarios": LIVE, "episodes": [], "consistency": {"checked": 0, "mismatch": 0, "mismatches": []}}
    for scn in LIVE:
        store = json.loads((ROOT / "data" / "processed" / "iam" / "evidence_store" / f"{scn}.json").read_text(encoding="utf-8"))
        cred = json.loads((ROOT / "testbed" / "state" / "assessor" / scn / "test_credentials.json").read_text(encoding="utf-8"))
        # live assessment time: now on the testbed clock is later than the stored T0; keep the stored T0 so that the
        # assessment window matches the collected evidence (events after T0 are excluded by all collectors)
        col = IAMCollectors(scn, store["assessment_time_ms"], params, kc, test_password=cred["password"])
        for oid, data in objs.items():
            y = load_labels("iam", data.episode_ids)
            train = np.array([i for i, e in enumerate(data.episode_ids) if not e.startswith(scn) and e.split("|")[0] not in LIVE])
            i_live = int(np.flatnonzero(data.episode_ids == f"{scn}|{oid}")[0])
            model = DiscreteBayesNet([len(a.outcomes) for a in data.actions], alpha=1.0).fit(data.values[train], y[train])
            cost = CostModel.fit(data.records[train], data.bytes_[train], data.seconds[train], data.n_categories()[train], "B")

            def fetch(a, data=data):
                spec = data.actions[a]
                t = time.perf_counter()
                ob = col.collect(spec.action_id)
                secs = time.perf_counter() - t
                stored = store["observations"][spec.action_id]["outcome"]
                report["consistency"]["checked"] += 1
                if ob["outcome"] != stored:
                    report["consistency"]["mismatch"] += 1
                    report["consistency"]["mismatches"].append({"scenario": scn, "action": spec.action_id, "live": ob["outcome"], "stored": stored})
                return EvidenceObservation(spec.action_id, oid, "controlled-iam-testbed (LIVE)", ob["outcome"], spec.outcomes.index(ob["outcome"]),
                                           time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), f"realm:{scn}",
                                           {"realm": scn, "mode": "live", "collector": ob["parser"]}, f"live:{scn}:{spec.action_id}",
                                           ob["parser"], secs, ob["records"], ob["bytes_read"], ob["privacy_categories"],
                                           cost.realized_cost(ob["records"], ob["bytes_read"], a), len(ob["privacy_categories"]) / 10,
                                           cost.realized_delay(secs))

            env = EvidenceEnvironment(f"{scn}|{oid}", data.actions, fetch)
            cfg = PolicyConfig("AVOI-GRC", "avoi", loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"], "risk", tau=0.1)
            trace = SequentialAssuranceAgent(cfg, model, cost, oid).run(env)
            trace["y_oracle"] = int(y[i_live])
            trace["realized_loss"] = loss.realized_loss(trace["final_decision"], int(y[i_live]))
            report["episodes"].append(trace)
            print(f"{scn} {oid:22s} acquisitions={trace['n_acquisitions']} decision={trace['final_decision']:12s} "
                  f"oracle_Y={y[i_live]} loss={trace['realized_loss']}", flush=True)
    out = ROOT / "results" / "traces" / "live_demo"
    out.mkdir(parents=True, exist_ok=True)
    (out / "live_agent_traces.json").write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print("consistency:", {k: v for k, v in report["consistency"].items() if k != "mismatches"}, report["consistency"]["mismatches"])
