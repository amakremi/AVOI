"""STAGE 3 / WP1 - adaptive next-evidence selection on branching IAM scenarios.

Reuses: Stage-2 development/validation (evidence-model selection, calibrator selection, adequacy gate), the AVOI agent
(adaptive and Frozen-Order via PolicyConfig.frozen_order), Stage-2 tuning/rows/gating helpers and statistics.
"""
from __future__ import annotations

import gzip
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, replace

import numpy as np
import pandas as pd

from avoi import adequacy as AQ
from avoi.agent import SequentialAssuranceAgent
from avoi.bayes_risk import HUMAN_REVIEW, LossMatrix
from avoi.datasets.common import make_environment
from avoi.evaluation import engine as E
from avoi.evaluation import stage2 as S
from avoi.evaluation import stage3 as S3M
from avoi.evaluation.stage3 import S3

DOMAIN = "iam_s3"
FROZEN = "Frozen-Order AVOI"


def settings():
    C = S.cfg()
    c3 = S3M.cfg3()
    L = c3["loss"]
    w = c3["weights"]
    loss = LossMatrix(L["false_assurance"], L["false_non_assurance"], L["human_review"])
    return C, c3, loss, w["lambda_cost"], w["mu_privacy"], w["nu_delay"]


def avoi_specs(C, loss, lam, mu, nu):
    avoi = [s for s in S.suite(C, loss, lam, mu, nu, "main", 0) if s.name == S.PROPOSED][0]
    frozen = E.MethodSpec(FROZEN, replace(avoi.cfg, name=FROZEN, frozen_order=True), avoi.model_kind, avoi.threshold, "ablation")
    return avoi, frozen


def fixed_horizon_cfg(spec, k_max):
    """Exactly-k horizon: no threshold stop, no value stop, Bayes decision with HumanReview option at the horizon."""
    return E.MethodSpec(spec.name, replace(spec.cfg, tau=None, stop_rule="none", value_stop=False, decision_rule="bayes_argmin"),
                        spec.model_kind, None, spec.group)


def run_traces(ctx, spec, idx, max_steps=None, record=True):
    agent = SequentialAssuranceAgent(replace(spec.cfg, tau=None), ctx.models[spec.model_kind], ctx.cost, ctx.data.objective_id, record)
    out = []
    for i in idx:
        env = make_environment(ctx.data, i, ctx.codes[i], ctx.cost)
        out.append(agent.run(env, max_steps=max_steps))
    return out


# ====================================================================================== adaptivity metrics
def _entropy_bits(counter: Counter) -> float:
    n = sum(counter.values())
    return float(-sum((c / n) * math.log2(c / n) for c in counter.values() if c)) if n else float("nan")


def history_key(step_index: int, trace: dict) -> str:
    return json.dumps([[s["selected_action"], s["observed_outcome"]] for s in trace["steps"][:step_index]])


def adaptivity_metrics(traces: list[dict], action_ids: list[str]) -> tuple[dict, pd.DataFrame]:
    """Per objective and step: distinct actions, P(A_t = a | reach t), entropy, ranking-change, rank-reversal and switching."""
    per_step = defaultdict(Counter)
    rows = []
    rank_change, reversal = [], []
    for tr in traces:
        prev_rank = None
        for k, s in enumerate(tr["steps"]):
            t = s["t"]
            per_step[t][s["selected_action"]] += 1
            reversal.append(bool(s.get("rank_reversal", False)))
            rank = s.get("ranking")
            if prev_rank is not None and rank is not None:
                remaining = [a for a in prev_rank if a in rank]
                rank_change.append(remaining != [a for a in rank if a in prev_rank])
            prev_rank = rank
    modal = {t: c.most_common(1)[0][0] for t, c in per_step.items()}
    switching = defaultdict(list)
    for tr in traces:
        for s in tr["steps"]:
            switching[s["t"]].append(s["selected_action"] != modal[s["t"]])
    for t, c in sorted(per_step.items()):
        n_t = sum(c.values())
        rows.append({"step": t, "n_t": n_t, "distinct_actions": len(c), "action_entropy_bits": _entropy_bits(c),
                     "switching_rate": float(np.mean(switching[t])),
                     **{f"P(A_t={a})": c.get(a, 0) / n_t for a in action_ids}})
    summary = {"distinct_actions_by_step": {int(t): len(c) for t, c in per_step.items()},
               "ranking_change_rate": float(np.mean(rank_change)) if rank_change else float("nan"),
               "rank_reversal_rate": float(np.mean(reversal)) if reversal else float("nan"),
               "mean_action_entropy_bits_t_ge_2": float(np.nanmean([_entropy_bits(c) for t, c in per_step.items() if t >= 2])),
               "switching_rate_t_ge_2": float(np.mean([x for t, v in switching.items() if t >= 2 for x in v]))}
    return summary, pd.DataFrame(rows)


def _cond_mi(actions: np.ndarray, hist: np.ndarray, steps: np.ndarray) -> float:
    """sum_t (n_t/N) * I(A_t ; H_t) with plug-in entropies (nats)."""
    total, N = 0.0, len(actions)
    for t in np.unique(steps):
        m = steps == t
        a, h = actions[m], hist[m]
        n = m.sum()
        joint = Counter(zip(a, h))
        pa, ph = Counter(a), Counter(h)
        mi = sum((c / n) * math.log((c / n) / ((pa[x] / n) * (ph[y] / n))) for (x, y), c in joint.items())
        total += (n / N) * mi
    return float(total)


def history_permutation_test(traces: list[dict], groups: dict[str, str], n_perm: int = 10_000, seed: int = 0) -> dict:
    """H0: next action is independent of the observed evidence history (given objective and step).
    Group-aware null: history labels are permuted among episodes of the same scenario family and step."""
    A, H, T, G = [], [], [], []
    for tr in traces:
        for k, s in enumerate(tr["steps"]):
            if s["t"] < 2:
                continue
            A.append(s["selected_action"]); H.append(history_key(k, tr)); T.append(s["t"]); G.append(groups[tr["episode_id"]])
    if not A:
        return {"statistic": float("nan"), "p": float("nan"), "n": 0}
    A, H, T, G = map(np.array, (A, H, T, G))
    obs = _cond_mi(A, H, T)
    rng = np.random.default_rng(seed)
    blocks = [np.flatnonzero((G == g) & (T == t)) for g in np.unique(G) for t in np.unique(T)]
    blocks = [b for b in blocks if len(b) > 1]
    ge = 0
    for _ in range(n_perm):
        Hp = H.copy()
        for b in blocks:
            Hp[b] = H[rng.permutation(b)]
        ge += _cond_mi(A, Hp, T) >= obs - 1e-12
    return {"statistic_conditional_MI_nats": obs, "p": (ge + 1) / (n_perm + 1), "n_steps": int(len(A)), "n_blocks": len(blocks)}


def ranking_trace_rows(traces: list[dict], policy: str, action_ids: list[str], y: dict) -> list[dict]:
    rows = []
    for tr in traces:
        for k, s in enumerate(tr["steps"]):
            cands = s.get("candidates", [])
            rows.append({"episode_id": tr["episode_id"], "objective": tr["objective_id"], "policy": policy, "step": s["t"],
                         "observed_history": json.dumps([[x["selected_action"], x["observed_outcome"]] for x in tr["steps"][:k]]),
                         "candidate_actions": json.dumps([action_ids[c["action"]] for c in cands]),
                         "outcome_predictions": json.dumps({action_ids[c["action"]]: c["outcome_probs"] for c in cands}),
                         "hypothetical_posteriors": json.dumps({action_ids[c["action"]]: c["outcome_posteriors"] for c in cands}),
                         "expected_post_action_risk": json.dumps({action_ids[c["action"]]: c["expected_next_risk"] for c in cands}),
                         "burdens": json.dumps({action_ids[c["action"]]: c["cost_term"] + c["privacy_term"] + c["delay_term"] for c in cands}),
                         "avoi_values": json.dumps({action_ids[c["action"]]: c["value"] for c in cands}),
                         "ranking": json.dumps([action_ids[a] for a in s.get("ranking", [])]),
                         "selected_action": s["selected_action"], "adaptive_next_action": action_ids[s["adaptive_next_action"]],
                         "frozen_next_action": action_ids[s["frozen_next_action"]], "rank_reversal": bool(s["rank_reversal"]),
                         "acquired_observation": s["observed_outcome"], "belief_after": s["updated_belief"], "y_evaluation_only": y[tr["episode_id"]]})
    return rows


# ====================================================================================== statistics
def group_signflip(diff_by_group: pd.Series, n_perm: int = 10_000, seed: int = 0) -> float:
    """Paired sign-flip permutation test on group-summed differences (two-sided)."""
    d = diff_by_group.to_numpy(float)
    obs = abs(d.sum())
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    return float((np.sum(np.abs(signs @ d) >= obs - 1e-12) + 1) / (n_perm + 1))


def write_traces(traces, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for tr in traces:
            fh.write(json.dumps(tr, default=float) + "\n")
