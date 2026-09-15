"""Sequential assurance agent (AVOI-GRC) and the shared executor used by all acquisition policies.

Loop per episode (see docs/METHODOLOGY.md):
  1 receive objective  2 receive acquired evidence  3 enumerate legal actions  4 posterior belief
  5 Bayes risk  6 value of every action  7 select  8 invoke evidence tool  9 append observation + provenance
 10 update belief  11 acquire again / Assured / NotAssured / HumanReview  12 write trace

All policies (AVOI and baselines) are PolicyConfig instances executed by the same code, so they differ only in
selection criterion, stopping rule and decision rule.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

import numpy as np

from avoi.actions import EvidenceEnvironment
from avoi.avoi import evaluate_candidates, lookahead2_values
from avoi.bayes_risk import ASSURED, HUMAN_REVIEW, NOT_ASSURED, LossMatrix, entropy


@dataclass
class PolicyConfig:
    name: str
    selector: str                       # avoi | entropy | fixed | random | cheapest | generic_voi | myopic_cs | lookahead2 | all | external
    loss: LossMatrix                    # loss used for selection / stopping / decision
    lam: float = 0.0
    mu: float = 0.0
    nu: float = 0.0
    stop_rule: str = "risk"             # risk | confidence | none
    tau: float | None = None            # risk threshold (risk rule) or confidence threshold (confidence rule)
    value_stop: bool = True             # stop when best value <= eps
    value_eps: float = 0.0
    decision_rule: str = "bayes_hr"     # bayes_hr | bayes_argmin | argmax | confidence_hr | autonomous_argmin
    seed: int = 0
    external_selector: object = None    # callable(state) -> action index or None (e.g. LLM planner)
    frozen_order: bool = False          # Stage 3 ablation (selector 'avoi' only): rank once at the first decision point,
                                        # then acquire the highest-ranked REMAINING action of that frozen ranking; values,
                                        # stopping, decisions and HumanReview are identical to adaptive AVOI

    def describe(self) -> dict:
        d = asdict(self)
        d["loss"] = asdict(self.loss)
        d.pop("external_selector", None)
        return d


def _order(cfg: PolicyConfig, env: EvidenceEnvironment, cost) -> list[int]:
    m = len(env.actions)
    if cfg.selector in ("fixed", "all"):
        return list(range(m))
    if cfg.selector == "random":
        h = hashlib.sha256(f"{cfg.seed}|{env.episode_id}".encode()).digest()
        return list(np.random.default_rng(int.from_bytes(h[:8], "little")).permutation(m))
    if cfg.selector == "cheapest":
        return sorted(range(m), key=lambda a: (round(float(cost.C[a]), 12), float(cost.D[a]), float(cost.P[a]), a))
    raise ValueError(cfg.selector)


def threshold_met(cfg: PolicyConfig, b: float) -> bool:
    if cfg.tau is None or cfg.stop_rule == "none":
        return False
    if cfg.stop_rule == "risk":
        return cfg.loss.risk(b) <= cfg.tau
    if cfg.stop_rule == "confidence":
        return max(b, 1.0 - b) >= cfg.tau
    raise ValueError(cfg.stop_rule)


def terminal_decision(cfg: PolicyConfig, b: float, reason: str) -> str:
    if reason == "threshold":
        if cfg.decision_rule in ("argmax", "confidence_hr"):
            return ASSURED if b >= 0.5 else NOT_ASSURED
        return cfg.loss.autonomous_decision(b)
    if cfg.decision_rule == "bayes_hr":
        return HUMAN_REVIEW if cfg.loss.allow_escalation else cfg.loss.autonomous_decision(b)
    if cfg.decision_rule == "bayes_argmin":
        return cfg.loss.bayes_decision(b)
    if cfg.decision_rule == "argmax":
        return ASSURED if b >= 0.5 else NOT_ASSURED
    if cfg.decision_rule == "confidence_hr":
        return HUMAN_REVIEW
    if cfg.decision_rule == "autonomous_argmin":
        return cfg.loss.autonomous_decision(b)
    raise ValueError(cfg.decision_rule)


class SequentialAssuranceAgent:
    def __init__(self, cfg: PolicyConfig, model, cost_model, objective_id: str, record_candidates: bool = True):
        self.cfg, self.model, self.cost, self.objective_id = cfg, model, cost_model, objective_id
        self.record_candidates = record_candidates

    def run(self, env: EvidenceEnvironment, max_steps: int | None = None, adequacy=None, adequacy_mode: str = "diagnostic") -> dict:
        """adequacy: optional avoi.adequacy.AdequacyDecision for the evidence model (Stage 2).
        adequacy_mode 'enforced': a non-VALIDATED model yields HumanReview (MODEL_ADEQUACY_RESTRICTED/UNSUPPORTED) without
        autonomous acquisition; 'diagnostic': the ungated AVOI process runs and the adequacy status is only recorded."""
        cfg, cost = self.cfg, self.cost
        evidence = env.observed()                                   # (2) evidence already in hand
        b = self.model.posterior(evidence)                          # (4)
        trace = {"episode_id": env.episode_id, "objective_id": self.objective_id, "policy": cfg.name,
                 "pre_acquired": sorted(env.actions[i].action_id for i in env.pre_acquired()),
                 "initial_belief": b, "initial_risk": cfg.loss.risk(b), "steps": [], "states": [
                     {"t": 0, "belief": b, "risk": cfg.loss.risk(b), "evidence": [list(e) for e in evidence]}]}
        if adequacy is not None:
            trace.update({"model_id": adequacy.model_id, "calibrator": adequacy.calibrator,
                          "adequacy_status": adequacy.status, "adequacy_metrics": adequacy.compact(),
                          "adequacy_policy_version": adequacy.policy_version, "adequacy_mode": adequacy_mode,
                          "autonomous_allowed": adequacy.autonomous_allowed, "gate_reason": adequacy.gate_reason,
                          "adequacy_reason": adequacy.reason, "adequacy_failed_conditions": list(adequacy.failed_conditions)})
            if adequacy_mode == "enforced" and not adequacy.autonomous_allowed:
                trace.update({"stop_reason": adequacy.gate_reason, "stopping_reason": adequacy.gate_reason,
                              "final_belief": b, "final_risk": cfg.loss.risk(b), "final_decision": HUMAN_REVIEW,
                              "n_acquisitions": 0, "total_cost": 0.0, "total_delay": 0.0, "privacy_categories": []})
                return trace
        order = _order(cfg, env, cost) if cfg.selector in ("fixed", "random", "cheapest", "all") else None
        reason = None
        t = 0
        frozen_rank = None                                          # initial AVOI ranking (Stage-3 ranking trace / frozen order)
        while True:
            if cfg.selector != "all" and threshold_met(cfg, b):
                reason = "threshold"
                break
            available = env.available_actions()                     # (3)
            if not available:
                reason = "exhausted"
                break
            if max_steps is not None and t >= max_steps:
                reason = "budget"
                break
            candidates = []
            if order is not None:                                   # order-based policies
                a_star = next(a for a in order if a in available)
            elif cfg.selector in ("avoi", "myopic_cs", "generic_voi", "entropy"):
                crit = "entropy" if cfg.selector == "entropy" else "bayes_risk"
                _, cands = evaluate_candidates(self.model, evidence, available, cfg.loss, cost.C, cost.P, cost.D,
                                               cfg.lam, cfg.mu, cfg.nu, criterion=crit)   # (5)(6)
                best = max(cands, key=lambda c: (c.value, -c.action))
                candidates = cands
                ranking = [c.action for c in sorted(cands, key=lambda c: (-c.value, c.action))]
                if frozen_rank is None:
                    frozen_rank = ranking
                if cfg.value_stop and best.value <= cfg.value_eps:
                    reason = "no_positive_value"
                    if self.record_candidates:
                        trace["final_candidates"] = [asdict(c) for c in cands]
                    break
                frozen_next = next(a for a in frozen_rank if a in available)
                a_star = frozen_next if (cfg.frozen_order and cfg.selector == "avoi") else best.action   # (7)
                rank_info = {"ranking": [int(a) for a in ranking], "adaptive_next_action": int(best.action),
                             "frozen_next_action": int(frozen_next), "rank_reversal": bool(best.action != frozen_next),
                             "history": [list(e) for e in evidence]}
            elif cfg.selector == "lookahead2":
                _, vals = lookahead2_values(self.model, evidence, available, cfg.loss, cost.C, cost.P, cost.D,
                                            cfg.lam, cfg.mu, cfg.nu)
                a_star = max(vals, key=lambda a: (vals[a], -a))
                candidates = [{"action": a, "value": v} for a, v in vals.items()]
                if cfg.value_stop and vals[a_star] <= cfg.value_eps:
                    reason = "no_positive_value"
                    break
            elif cfg.selector == "external":
                a_star = cfg.external_selector({"objective_id": self.objective_id, "evidence": evidence,
                                                "available": available, "env": env, "cost": cost})
                if a_star is None:
                    reason = "planner_stop"
                    break
            else:
                raise ValueError(cfg.selector)
            obs = env.acquire(a_star)                               # (8)(9)
            evidence = env.observed()
            b_new = self.model.posterior(evidence)                  # (10)
            t += 1
            step = {"t": t, "selected_action": env.actions[a_star].action_id, "action_index": int(a_star),
                    "observed_outcome": obs.outcome, "updated_belief": b_new, "updated_risk": cfg.loss.risk(b_new),
                    "cost": obs.cost_normalized, "delay": obs.delay_normalized, "privacy_categories": obs.privacy_fields_exposed,
                    "records": obs.records_accessed, "bytes": obs.bytes_read, "seconds": obs.acquisition_seconds,
                    "provenance": obs.provenance, "raw_artifact_ref": obs.raw_artifact_ref, "parser": obs.parser}
            if self.record_candidates and candidates:
                step["candidates"] = [asdict(c) if hasattr(c, "__dataclass_fields__") else c for c in candidates]
            if cfg.selector in ("avoi", "myopic_cs", "generic_voi", "entropy") and candidates:
                step.update(rank_info)
            trace["steps"].append(step)
            trace["states"].append({"t": t, "belief": b_new, "risk": cfg.loss.risk(b_new)})
            b = b_new
        decision = terminal_decision(cfg, b, reason)                # (11)
        trace.update({"stop_reason": reason, "final_belief": b, "final_risk": cfg.loss.risk(b), "final_decision": decision,
                      "n_acquisitions": t, "total_cost": float(sum(s["cost"] for s in trace["steps"])),
                      "total_delay": float(sum(s["delay"] for s in trace["steps"])),
                      "privacy_categories": sorted({c for s in trace["steps"] for c in s["privacy_categories"]})})
        return trace                                                # (12)


def truncate(trace: dict, cfg: PolicyConfig, tau: float | None, budget: int | None = None) -> dict:
    """Operating point of a policy with threshold tau (and optional acquisition budget) from its FULL trajectory
    (run with tau=None). Exact because selection does not depend on tau; verified in tests/test_agent.py."""
    c = PolicyConfig(**{**cfg.__dict__, "tau": tau})
    states = trace["states"]
    T = len(trace["steps"])
    stop_t, reason = None, None
    for s in states:
        if cfg.selector != "all" and threshold_met(c, s["belief"]):
            stop_t, reason = s["t"], "threshold"
            break
        if budget is not None and s["t"] >= budget and s["t"] < T:
            stop_t, reason = s["t"], "budget"
            break
    if stop_t is None:
        stop_t, reason = T, trace["stop_reason"]
        if budget is not None and T > budget:
            stop_t, reason = budget, "budget"
    b = states[stop_t]["belief"]
    steps = trace["steps"][:stop_t]
    return {"decision": terminal_decision(c, b, reason), "belief": b, "n_acquisitions": stop_t, "reason": reason,
            "cost": float(sum(s["cost"] for s in steps)), "delay": float(sum(s["delay"] for s in steps)),
            "seconds": float(sum(s["seconds"] for s in steps)), "records": int(sum(s["records"] for s in steps)),
            "bytes": int(sum(s["bytes"] for s in steps)),
            "privacy_categories": sorted({x for s in steps for x in s["privacy_categories"]})}
