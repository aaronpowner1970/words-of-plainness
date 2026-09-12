"""Model-call backends and the audit log.

Every call is logged with role, model, prompt hash (system prompt + version), input hash, output,
usage and cost, appended as JSON lines under data-sources/sjn/recovery-runs/<run_id>/calls.jsonl.

Backends
  anthropic   Anthropic Python SDK; needs ANTHROPIC_API_KEY. Cost from token usage at list prices.
  claude-cli  `claude -p` headless (the user's Claude Code login); cost from the CLI's own result JSON.
  ollama      local Ollama model (OpenAI-compatible chat endpoint); cost 0 (local compute).
  batch       file exchange: the harness writes a job file per call and returns PENDING; a separate
              executor (Claude Code subagents in this build) writes the response file; re-running the
              same command ingests it. Deterministic job ids make the exchange idempotent and give
              duplicate suppression for identical calls. Cost is estimated from character counts and
              marked as an estimate — the subagent path is not metered per call.

A call's identity = sha256(role | model | prompt_version | system | user). The same identity is never
sent twice: the audit log is consulted first (idempotent re-runs, exact duplicate suppression)."""
import hashlib
import json
import os
import subprocess
import time

import requests

from .config import JOBS_DIR, RUNS_DIR, MODEL_IDS
from .prompts import PROMPT_VERSION, prompt_version

# USD per million tokens (input, output) — list prices used only for cost accounting.
LIST_PRICES = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5": (15.00, 75.00),
    "claude-fable-5-1": (15.00, 75.00),
}


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class LLM:
    def __init__(self, run_id, backend="batch", model="sonnet", log=print):
        self.run_id = run_id
        self.backend = backend
        self.model = model
        self.model_id = MODEL_IDS.get(model, model)
        self.log = log
        self.run_dir = os.path.join(RUNS_DIR, run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.audit_path = os.path.join(self.run_dir, "calls.jsonl")
        self.jobs_dir = os.path.join(JOBS_DIR, run_id)
        os.makedirs(os.path.join(self.jobs_dir, "pending"), exist_ok=True)
        os.makedirs(os.path.join(self.jobs_dir, "done"), exist_ok=True)
        self._cache = {}
        if os.path.exists(self.audit_path):
            with open(self.audit_path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        self._cache[rec["call_id"]] = rec
                    except Exception:
                        pass
        self.pending = []
        self.calls_made = 0

    # ---------------------------------------------------------------- identity / audit
    def call_id(self, role, system, user, model=None, attempt=0):
        """Identity = sha256(role | model | the ROLE's prompt version | system | user [| attempt]).
        Versioning per role means a locator prompt revision never invalidates answered verifier calls.
        `attempt` > 0 is the retry of a reply that hit its token ceiling before the JSON was complete:
        the same call re-sent with a larger ceiling under its own identity, so the truncated answer
        stays in the audit log and is never mistaken for the final one."""
        parts = [role, model or self.model_id, prompt_version(role), system, user]
        if attempt:
            parts.append(f"attempt={attempt}")
        return _sha("|".join(parts))[:24]

    def seed_from(self, other_run_id, log=None):
        """Load another run's answered calls into this run's cache so identical calls (same role,
        model, prompt version, system and user text) are not sent again. The records keep their
        original run_id, so cost accounting can separate reused from newly metered calls."""
        p = os.path.join(RUNS_DIR, other_run_id, "calls.jsonl")
        if not os.path.exists(p):
            return 0
        n = 0
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("output") is not None and rec["call_id"] not in self._cache:
                    self._cache[rec["call_id"]] = rec
                    n += 1
        if log:
            log(f"   seeded {n} answered call(s) from {other_run_id}")
        return n

    def _record(self, rec):
        with open(self.audit_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._cache[rec["call_id"]] = rec

    def _cost(self, model_id, usage, estimated=False):
        p = LIST_PRICES.get(model_id)
        if not p or not usage:
            return None
        return round((usage.get("input_tokens", 0) * p[0] + usage.get("output_tokens", 0) * p[1]) / 1e6, 6)

    # ---------------------------------------------------------------- public
    def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
        """Return (output_text, record) or (None, record) when pending (batch backend)."""
        model = model or self.model
        model_id = MODEL_IDS.get(model, model)
        cid = self.call_id(role, system, user, model_id, attempt)
        if cid in self._cache and self._cache[cid].get("output") is not None:
            return self._cache[cid]["output"], self._cache[cid]
        rec = {"call_id": cid, "run_id": self.run_id, "role": role, "backend": self.backend, "model": model,
               "model_id": model_id, "prompt_version": prompt_version(role), "prompt_sha256": _sha(system),
               "input_sha256": _sha(user), "input_chars": len(user), "meta": dict(meta or {}, attempt=attempt),
               "max_tokens": max_tokens, "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if self.backend == "batch":
            out = self._batch(cid, role, system, user, model, max_tokens, rec)
            if out is None:
                return None, rec
            rec["output"] = out
            if not rec.pop("_metered", False):
                rec["usage"] = {"input_tokens": int((len(system) + len(user)) / 3.6), "output_tokens": int(len(out) / 3.6), "estimated": True}
                rec["cost_usd"] = self._cost(model_id, rec["usage"], estimated=True)
                rec["cost_basis"] = "ESTIMATE: Claude Code subagent calls are not metered per call; tokens ≈ chars/3.6 at list prices"
        elif self.backend == "anthropic":
            out, usage = self._anthropic(system, user, model_id, max_tokens)
            rec["output"], rec["usage"] = out, usage
            rec["cost_usd"] = self._cost(model_id, usage)
            rec["cost_basis"] = "metered tokens at list prices"
        elif self.backend == "claude-cli":
            out, usage, cost = self._claude_cli(system, user, model, max_tokens)
            rec["output"], rec["usage"], rec["cost_usd"] = out, usage, cost
            rec["cost_basis"] = "claude -p result JSON total_cost_usd"
        elif self.backend == "ollama":
            out, usage = self._ollama(system, user, model, max_tokens)
            rec["output"], rec["usage"], rec["cost_usd"] = out, usage, 0.0
            rec["cost_basis"] = "local model; no API cost"
        else:
            raise ValueError(f"unknown backend {self.backend}")
        rec["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._record(rec)
        self.calls_made += 1
        return rec["output"], rec

    # ---------------------------------------------------------------- backends
    def _batch(self, cid, role, system, user, model, max_tokens, rec):
        done = os.path.join(self.jobs_dir, "done", f"{cid}.json")
        done_txt = os.path.join(self.jobs_dir, "done", f"{cid}.txt")
        if os.path.exists(done):
            with open(done, encoding="utf-8") as fh:
                resp = json.load(fh)
            rec["executor"] = resp.get("executor", "claude-code-subagent")
            rec["executor_model"] = resp.get("model", model)
            if resp.get("usage") and resp.get("cost_usd") is not None:
                # answered through the Anthropic API (api_executor.py): real metered usage and cost
                rec["usage"] = resp["usage"]
                rec["cost_usd"] = resp["cost_usd"]
                rec["cost_basis"] = resp.get("cost_basis", "metered tokens at list prices")
                rec["_metered"] = True
            return resp.get("output", "")
        if os.path.exists(done_txt):
            # raw reply written by an isolated Claude Code subagent session (model alias as requested)
            with open(done_txt, encoding="utf-8-sig") as fh:
                out = fh.read().strip()
            if not out:
                return None
            rec["executor"] = "claude-code-subagent"
            rec["executor_model"] = model
            return out
        pending = os.path.join(self.jobs_dir, "pending", f"{cid}.json")
        if not os.path.exists(pending):
            with open(pending, "w", encoding="utf-8") as fh:
                json.dump({"call_id": cid, "role": role, "model": model, "model_id": MODEL_IDS.get(model, model),
                           "max_tokens": max_tokens, "system": system, "user": user, "meta": rec.get("meta", {})},
                          fh, ensure_ascii=False, indent=1)
        self.pending.append(cid)
        return None

    def _anthropic(self, system, user, model_id, max_tokens):
        import anthropic
        client = anthropic.Anthropic()
        # `temperature` is deprecated on the Claude 5 family; the API default is used.
        r = client.messages.create(model=model_id, max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": user}])
        text = "".join(getattr(b, "text", "") for b in r.content)
        return text, {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}

    def _claude_cli(self, system, user, model, max_tokens):
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        cmd = ["claude", "-p", "--output-format", "json", "--max-turns", "1", "--model", model,
               "--system-prompt", system, user]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env, timeout=600)
        data = json.loads(p.stdout)
        if data.get("is_error"):
            raise RuntimeError(data.get("result"))
        usage = data.get("usage", {})
        return data.get("result", ""), {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}, data.get("total_cost_usd")

    def _ollama(self, system, user, model, max_tokens):
        from .config import OLLAMA_URL
        r = requests.post(f"{OLLAMA_URL}/api/chat", json={"model": model, "stream": False, "options": {"temperature": 0, "num_predict": max_tokens},
                                                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=600)
        r.raise_for_status()
        d = r.json()
        return d["message"]["content"], {"input_tokens": d.get("prompt_eval_count", 0), "output_tokens": d.get("eval_count", 0)}

    # ---------------------------------------------------------------- batch helpers
    def pending_jobs(self):
        d = os.path.join(self.jobs_dir, "pending")
        return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))

    def summary(self, only_run=None):
        """Call/cost totals. `by_model` covers every record in the cache (including calls seeded from
        earlier runs); `this_run` covers only records answered under this run id, by model and by role,
        which is the run's own metered spend."""
        recs = list(self._cache.values())

        def tally(records):
            out = {}
            for r in records:
                k = r.get("executor_model") or r.get("model")
                b = out.setdefault(k, {"calls": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "estimated": False})
                b["calls"] += 1
                b["cost_usd"] += r.get("cost_usd") or 0.0
                u = r.get("usage") or {}
                b["input_tokens"] += u.get("input_tokens", 0); b["output_tokens"] += u.get("output_tokens", 0)
                b["estimated"] = b["estimated"] or bool(u.get("estimated"))
            return out

        mine = [r for r in recs if r.get("run_id") == (only_run or self.run_id)]
        by_role = {}
        for r in mine:
            k = (r.get("role"), r.get("executor_model") or r.get("model"))
            b = by_role.setdefault(f"{k[0]}/{k[1]}", {"calls": 0, "cost_usd": 0.0})
            b["calls"] += 1; b["cost_usd"] += r.get("cost_usd") or 0.0
        return {"calls": len(recs), "by_model": tally(recs),
                "this_run": {"run_id": only_run or self.run_id, "calls": len(mine), "by_model": tally(mine), "by_role": by_role,
                             "cost_usd": sum(r.get("cost_usd") or 0.0 for r in mine),
                             "reused_calls": len(recs) - len(mine)}}
