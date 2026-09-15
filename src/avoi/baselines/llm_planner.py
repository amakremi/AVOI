"""B8 — LLM-only acquisition planner (secondary baseline, local Ollama model).

Rules: temperature 0 and fixed seed; JSON-schema-constrained output restricted to available action ids or STOP;
the model receives the objective, acquired evidence, action names/descriptions and normalised costs only — no labels,
no posterior probabilities; it does not set P(Y) and does not make the assurance decision (the shared Bayes decision
layer does). Every prompt/response is cached in results/raw/llm_planner/cache.jsonl for reproducibility.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "results" / "raw" / "llm_planner" / "cache.jsonl"
OLLAMA = "http://127.0.0.1:11434/api/chat"


class LLMPlanner:
    def __init__(self, model: str, objective_text: dict[str, dict], seed: int = 0, max_steps: int | None = None,
                 cache_path: Path | None = None):
        self.model, self.seed, self.objective_text, self.max_steps = model, seed, objective_text, max_steps
        self.cache_path = cache_path or CACHE
        self.cache: dict[str, dict] = {}
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                self.cache[rec["key"]] = rec
        self.calls = 0
        self.invalid = 0

    def prompt(self, state: dict) -> tuple[str, list[str]]:
        env, cost, oid = state["env"], state["cost"], state["objective_id"]
        acts = env.actions
        obj = self.objective_text[oid]
        acquired = [f"- {acts[i].action_id} ({acts[i].source_type}) -> outcome: {acts[i].outcomes[o]}" for i, o in state["evidence"]]
        avail = [f"- {acts[a].action_id}: source={acts[a].source_type}; possible outcomes={list(acts[a].outcomes)}; "
                 f"normalised_cost={cost.C[a]:.3f}; privacy_exposure={cost.P[a]:.2f}; delay={cost.D[a]:.3f}"
                 for a in state["available"]]
        text = (
            "You are planning evidence collection for a cybersecurity assurance assessment.\n"
            f"Assessment objective: {obj['title']}\nOperational definition: {obj['predicate']}\n\n"
            "Evidence already acquired:\n" + ("\n".join(acquired) if acquired else "- none") + "\n\n"
            "Evidence actions still available:\n" + "\n".join(avail) + "\n\n"
            "Choose the single next evidence action that is most useful for deciding whether the objective is satisfied, "
            "considering reliability, cost, privacy exposure and delay. Choose STOP if the acquired evidence is already "
            "sufficient or further evidence is not worth acquiring. You do not make the final assurance decision.\n"
            'Reply only with JSON: {"action": "<action id or STOP>", "reason": "<short reason>"}')
        return text, [acts[a].action_id for a in state["available"]]

    def __call__(self, state: dict):
        if self.max_steps is not None and len(state["env"].log) >= self.max_steps:
            return None
        text, ids = self.prompt(state)
        schema = {"type": "object", "properties": {"action": {"type": "string", "enum": ids + ["STOP"]},
                                                   "reason": {"type": "string"}}, "required": ["action"]}
        key = hashlib.sha256(json.dumps([self.model, self.seed, text, schema], sort_keys=True).encode()).hexdigest()
        rec = self.cache.get(key)
        if rec is None:
            body = {"model": self.model, "stream": False, "format": schema, "think": False,
                    "options": {"temperature": 0, "seed": self.seed, "num_ctx": 8192},
                    "messages": [{"role": "user", "content": text}]}
            r = requests.post(OLLAMA, json=body, timeout=600)
            r.raise_for_status()
            content = r.json()["message"]["content"]
            rec = {"key": key, "model": self.model, "prompt": text, "schema": schema, "response": content}
            self.cache[key] = rec
            with self.cache_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            self.calls += 1
        try:
            choice = json.loads(rec["response"])["action"]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.invalid += 1
            return None
        if choice == "STOP":
            return None
        if choice not in ids:
            self.invalid += 1
            return None
        return state["available"][ids.index(choice)]
