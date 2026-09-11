"""Execute pending batch jobs against the Anthropic API (Gate 6 backend `anthropic`).

The harness (calibrate.py / run.py) writes one job file per model call under
.cache/sjn-recovery/jobs/<run>/pending/. This executor answers them directly through the
Anthropic SDK — no Claude Code subagent overhead — and writes done/<call_id>.json carrying the
output plus REAL metered token usage and cost, which llm.py then records in the audit log.

  python scripts/sjn_recovery/api_executor.py --run-id cal-1 [--role locator] [--model sonnet]
         [--workers 4] [--max-cost-usd 8] [--limit N] [--dry-run]

Cost control: the run stops as soon as the accumulated metered cost would exceed --max-cost-usd,
and prints the running total. Nothing here writes to the workbook.

The key is read from ANTHROPIC_API_KEY (or --key-file, a file whose ANTHROPIC_API_KEY=... line is
used). The key value is never printed or logged."""
import argparse
import concurrent.futures as cf
import json
import os
import random
import re
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import JOBS_DIR, MODEL_IDS  # noqa: E402
from sjn_recovery.llm import LIST_PRICES  # noqa: E402

_lock = threading.Lock()
_state = {"cost": 0.0, "calls": 0, "in": 0, "out": 0, "stopped": False, "errors": 0}


def load_key(key_file):
    if key_file:
        with open(key_file, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"^\s*ANTHROPIC_API_KEY\s*=\s*(.+?)\s*$", line)
                if m:
                    return m.group(1).strip().strip('"').strip("'")
        raise SystemExit(f"no ANTHROPIC_API_KEY=... line in {key_file}")
    k = os.environ.get("ANTHROPIC_API_KEY")
    if not k:
        raise SystemExit("ANTHROPIC_API_KEY is not set and no --key-file was given")
    return k


def cost_of(model_id, usage):
    p = LIST_PRICES.get(model_id)
    if not p:
        return 0.0
    return round((usage.get("input_tokens", 0) * p[0] + usage.get("output_tokens", 0) * p[1]) / 1e6, 6)


def pending_jobs(run_id, role=None, model=None):
    d = os.path.join(JOBS_DIR, run_id)
    pend, done = os.path.join(d, "pending"), os.path.join(d, "done")
    out = []
    for f in sorted(os.listdir(pend)):
        if not f.endswith(".json"):
            continue
        cid = f[:-5]
        if os.path.exists(os.path.join(done, cid + ".json")) or os.path.exists(os.path.join(done, cid + ".txt")):
            continue
        with open(os.path.join(pend, f), encoding="utf-8") as fh:
            j = json.load(fh)
        if role and j["role"] != role:
            continue
        if model and j["model"] != model:
            continue
        out.append(j)
    return out


def call_one(client, job, done_dir, max_cost, log):
    cid = job["call_id"]
    model_id = job.get("model_id") or MODEL_IDS.get(job["model"], job["model"])
    last = ""
    for attempt in range(1, 7):
        with _lock:
            if _state["stopped"]:
                return None
            if max_cost and _state["cost"] >= max_cost:
                _state["stopped"] = True
                log(f"!! budget cap {max_cost} USD reached; stopping (spent {_state['cost']:.2f})")
                return None
        try:
            r = client.messages.create(
                model=model_id, max_tokens=job.get("max_tokens", 1200),
                system=job["system"], messages=[{"role": "user", "content": job["user"]}])
            text = "".join(getattr(b, "text", "") for b in r.content)
            if not text.strip():
                # The reply carried no text block: the token ceiling was consumed before any output was
                # emitted. Recording this as a success would bank an empty answer the harness scores as
                # a forced REJECT, so retry with more room instead.
                raise RuntimeError(f"empty text block (stop_reason={getattr(r, 'stop_reason', None)}, "
                                   f"output_tokens={r.usage.output_tokens})")
            usage = {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
            c = cost_of(model_id, usage)
            rec = {"call_id": cid, "output": text, "model": job["model"], "model_id": model_id,
                   "executor": "anthropic-api", "usage": usage, "cost_usd": c,
                   "cost_basis": "metered input/output tokens at list prices",
                   "answered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            tmp = os.path.join(done_dir, cid + ".json.tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, ensure_ascii=False)
            os.replace(tmp, os.path.join(done_dir, cid + ".json"))
            with _lock:
                _state["cost"] += c; _state["calls"] += 1
                _state["in"] += usage["input_tokens"]; _state["out"] += usage["output_tokens"]
                n, tot = _state["calls"], _state["cost"]
            log(f"  ok  {cid} {job['role']:<8} {job['model']:<7} in={usage['input_tokens']:>6} out={usage['output_tokens']:>5} "
                f"${c:.4f}  [{n} calls, ${tot:.2f} total]")
            return rec
        except Exception as e:
            name = type(e).__name__
            last = f"{name}: {str(e)[:160]}"
            status = getattr(e, "status_code", None)
            fatal = name in ("AuthenticationError", "PermissionDeniedError", "BadRequestError", "NotFoundError")
            if fatal:
                with _lock:
                    _state["stopped"] = True; _state["errors"] += 1
                log(f"  FATAL {cid}: {last}")
                return None
            if status == 429 and "spend limit" in str(e).lower():
                with _lock:
                    _state["stopped"] = True; _state["errors"] += 1
                log(f"  SPEND LIMIT reached: {last}")
                return None
            if "empty text block" in last:
                job["max_tokens"] = min(8000, int(job.get("max_tokens", 1200) * 2))
                log(f"  empty reply {cid}: retrying with max_tokens={job['max_tokens']}")
            sleep = min(60, (2 ** attempt) + random.uniform(0, 1.5))
            log(f"  retry {attempt}/6 {cid} in {sleep:.1f}s ({last})")
            time.sleep(sleep)
    with _lock:
        _state["errors"] += 1
    log(f"  FAILED {cid} after retries: {last}")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--role")
    ap.add_argument("--model")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-cost-usd", type=float, default=10.0)
    ap.add_argument("--key-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    jobs = pending_jobs(a.run_id, a.role, a.model)
    if a.limit:
        jobs = jobs[:a.limit]
    by = {}
    est_in = 0
    for j in jobs:
        by[(j["role"], j["model"])] = by.get((j["role"], j["model"]), 0) + 1
        est_in += (len(j["system"]) + len(j["user"])) / 3.6
    print(f"== {len(jobs)} pending job(s): " + ", ".join(f"{r}/{m}={n}" for (r, m), n in sorted(by.items())))
    print(f"   estimated input tokens {int(est_in):,}; budget cap ${a.max_cost_usd:.2f}; {a.workers} workers")
    if a.dry_run or not jobs:
        return 0

    key = load_key(a.key_file)
    import anthropic
    client = anthropic.Anthropic(api_key=key, max_retries=0, timeout=180.0)
    done_dir = os.path.join(JOBS_DIR, a.run_id, "done")
    os.makedirs(done_dir, exist_ok=True)

    def log(m):
        print(m, flush=True)

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(lambda j: call_one(client, j, done_dir, a.max_cost_usd, log), jobs))
    el = time.time() - t0
    print(f"== answered {_state['calls']} call(s) in {el / 60:.1f} min; tokens in={_state['in']:,} out={_state['out']:,}; "
          f"metered cost ${_state['cost']:.2f}; errors {_state['errors']}"
          + ("; STOPPED EARLY" if _state["stopped"] else ""))
    return 1 if _state["stopped"] else 0


if __name__ == "__main__":
    sys.exit(main())
