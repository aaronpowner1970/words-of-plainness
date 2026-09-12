"""Per-branch spend that SURVIVES invocations (packet-shape fix 1d, adopted 2026-09-12).

The Roman Catholic branch showed that `api_executor.py --max-cost-usd` resets on every invocation,
so the $25 branch cap was advisory. The counter now lives in a state file keyed by run id and
branch:

    data-sources/sjn/recovery-runs/<run_id>/cost-state.json
    {
      "run_id": "live-1",
      "updated_at": "2026-09-12T18:00:00Z",
      "branches": {
        "Anglican": {
          "cap_usd": 25.0,               # the author's per-branch cap (run.py --branch-cost-cap-usd)
          "spent_usd": 12.3456,          # metered USD, every priced call, across every invocation
          "calls": 210,
          "status": "RUNNING" | "CAP_HIT" | "DONE",
          "cells": 43,
          "queue_ids": ["Q-021", ...],   # how the executor maps a job (meta.queue_id) to its branch
          "invocations": [               # one entry per executor invocation that priced a call
            {"started_at": "...", "resumed_from_usd": 0.0, "answered": 120, "spent_usd": 7.1, "ended_at": "..."}
          ],
          "cap_hit_at": null
        }
      },
      "unassigned": {"spent_usd": 0.0, "calls": 0}   # calls whose meta names no branch cell (planted items)
    }

  * run.py registers the branch (cap, cells) before its first cell runs and reconciles spent_usd
    against the audit log after every pass (max of the two, never lower).
  * api_executor.py loads the file at start, credits every priced call to its branch and writes the
    file after EVERY priced call (atomic replace), so a killed process loses at most the call in flight.
    A branch at or over its cap has its remaining jobs SKIPPED, not answered; other branches continue.
  * run.py sees CAP_HIT, runs no further cells for that branch, writes the PARTIAL packet and says so.

Nothing here writes to the workbook."""
import json
import os
import time

from .config import RUNS_DIR

FILENAME = "cost-state.json"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def path_for(run_id):
    return os.path.join(RUNS_DIR, run_id, FILENAME)


def load(run_id):
    p = path_for(run_id)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    return {"run_id": run_id, "updated_at": None, "branches": {}, "unassigned": {"spent_usd": 0.0, "calls": 0}}


def save(state):
    p = path_for(state["run_id"])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    state["updated_at"] = _now()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    # Windows: a file-sync client or the indexer can hold the target for a moment and os.replace raises
    # PermissionError (seen twice on the Anglican run, 2026-09-12). Retry briefly; the temp-file write is complete.
    for attempt in range(6):
        try:
            os.replace(tmp, p)
            return p
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.2 * (attempt + 1))
    return p


def register_branch(state, branch, cap_usd, queue_ids):
    b = state["branches"].setdefault(branch, {"cap_usd": None, "spent_usd": 0.0, "calls": 0, "status": "RUNNING",
                                              "cells": 0, "queue_ids": [], "invocations": [], "cap_hit_at": None})
    if cap_usd is not None:
        b["cap_usd"] = float(cap_usd)
    b["cells"] = len(queue_ids)
    b["queue_ids"] = sorted(set(b["queue_ids"]) | set(queue_ids))
    if b["status"] == "CAP_HIT" and (b["cap_usd"] is None or b["spent_usd"] < b["cap_usd"]):
        b["status"] = "RUNNING"          # the author raised the cap: the branch may continue
    return b


def branch_of(state, queue_id):
    for name, b in state["branches"].items():
        if queue_id in b.get("queue_ids", []):
            return name
    return None


def over_cap(b):
    return b.get("cap_usd") is not None and b.get("spent_usd", 0.0) >= b["cap_usd"]


def credit(state, branch, cost_usd):
    """Add one priced call. Returns the branch record (or the unassigned bucket)."""
    if branch and branch in state["branches"]:
        b = state["branches"][branch]
        b["spent_usd"] = round(b.get("spent_usd", 0.0) + (cost_usd or 0.0), 6)
        b["calls"] = b.get("calls", 0) + 1
        if over_cap(b) and b["status"] != "CAP_HIT":
            b["status"] = "CAP_HIT"; b["cap_hit_at"] = _now()
        return b
    u = state.setdefault("unassigned", {"spent_usd": 0.0, "calls": 0})
    u["spent_usd"] = round(u["spent_usd"] + (cost_usd or 0.0), 6); u["calls"] += 1
    return u


def reconcile(state, branch, audit_spent_usd, audit_calls):
    """run.py: the audit log (ingested done files) can only confirm spend the executor already recorded;
    take the larger figure so an executor crash between write and ingest never lowers the counter."""
    b = state["branches"].get(branch)
    if not b:
        return None
    if audit_spent_usd > b.get("spent_usd", 0.0):
        b["spent_usd"] = round(audit_spent_usd, 6)
    if audit_calls > b.get("calls", 0):
        b["calls"] = audit_calls
    if over_cap(b) and b["status"] != "CAP_HIT":
        b["status"] = "CAP_HIT"; b["cap_hit_at"] = b.get("cap_hit_at") or _now()
    return b
