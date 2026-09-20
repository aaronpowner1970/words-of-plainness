"""Session 14, phase 2: how many EXISTING accepts would enter the author review queue under Codex C3(a) / R6-54.

Codex C3(a): "Before the queue is switched on, the run reports how many existing accepts would enter it." This is that
report. It counts, by branch, over every stored live-1 cell state — no model calls, no network, nothing written but this
script's own JSON.

Doubt as C3(a) defines it has two limbs:

  DISSENTING_VOTE                 any replicate whose verdict class differs from the majority's.
  ACCEPT_WITH_CAVEAT_AT_PARTIAL   the final verdict is ACCEPT_WITH_CAVEAT and the final floor is PARTIAL.

Every stored verdict was given by a SINGLE call per model, so the first limb cannot fire on any of them: there is no
vote to dissent from. That is a fact about the instrument, not about the citations, and it is the reason R6-54 makes the
harness vote before anything else is run. Two further readings are counted beside the literal one, so the author can see
what the number would be if "dissent" were read more widely:

  A (literal, C3(a))  ACCEPT_WITH_CAVEAT at PARTIAL only. Weakness: it counts no vote at all, because none was taken.
  B (two models)      A, plus accepts where the two stored models returned different verdict classes. Weakness: a
                      two-model disagreement is rule 2a/2b, which the harness already resolves; calling it dissent
                      double-counts a rule that has already run.
  C (any second look) B, plus accepts where the two models returned different FLOORS. Weakness: widest of the three; a
                      floor disagreement that 2a already resolved downward is not doubt about the outcome.

  python data-sources/sjn/recovery-runs/session14/queue_volume.py   writes session14/queue-volume.json
"""
import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.abspath(os.path.join(RUNS, "..", "..", "..", "scripts")))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery.agents import ACCEPTS  # noqa: E402
from sjn_recovery import review_queue  # noqa: E402

PACKETS = os.path.abspath(os.path.join(RUNS, "..", "recovery-packets"))


def seated_ids():
    """{candidate_id: queue_id} for every candidate seated on a committed packet card — the accepts that actually
    reach the author, as distinct from every accept stored in a cell state."""
    out = {}
    for f in sorted(glob.glob(os.path.join(PACKETS, "*.json"))):
        pk = json.load(open(f, encoding="utf-8"))
        for c in pk.get("cards", []):
            for e in c.get("candidates", []):
                out[e["candidate_id"]] = c["queue_id"]
    return out


def main():
    seated = seated_ids()
    rows, by_branch = [], {}
    for f in sorted(glob.glob(os.path.join(RUNS, "live-1", "cells", "*.json"))):
        st = json.load(open(f, encoding="utf-8"))
        br = st.get("branch")
        b = by_branch.setdefault(br, Counter())
        for cid, v in (st.get("verifications") or {}).items():
            fin = v.get("final") or {}
            if fin.get("verdict") not in ACCEPTS:
                continue
            b["accepts"] += 1
            if cid in seated:
                b["accepts_seated"] += 1
            rubrics = {m: r for m, r in v.items()
                       if isinstance(r, dict) and m not in ("final", "_route", "final_at_run", "superseded_rubrics", "reverified")
                       and r.get("status") == "DONE"}
            classes = {m: r.get("verdict") for m, r in rubrics.items()}
            floors = {m: r.get("floor") for m, r in rubrics.items()}
            reasons = []
            if fin.get("verdict") == "ACCEPT_WITH_CAVEAT" and fin.get("floor_final") == "PARTIAL":
                reasons.append(review_queue.REASON_CAVEAT_AT_PARTIAL)
            two_model_class = len(set(classes.values())) > 1
            two_model_floor = len({x for x in floors.values() if x}) > 1
            if reasons:
                b["A"] += 1
                b["A_seated"] += 1 if cid in seated else 0
            if reasons or two_model_class:
                b["B"] += 1
                b["B_seated"] += 1 if cid in seated else 0
            if reasons or two_model_class or two_model_floor:
                b["C"] += 1
                b["C_seated"] += 1 if cid in seated else 0
            if reasons or two_model_class or two_model_floor:
                rows.append({"branch": br, "queue_id": st["queue_id"], "candidate_id": cid, "seated": cid in seated,
                             "verdict": fin.get("verdict"), "floor_final": fin.get("floor_final"),
                             "route": fin.get("route"), "models": sorted(rubrics),
                             "verdict_by_model": classes, "floor_by_model": floors,
                             "reading_A": bool(reasons), "reading_B": bool(reasons or two_model_class),
                             "reading_C": True, "reasons_literal": reasons})
            # every stored rubric was one call: record the instrument, so the "no dissent is possible" claim is checkable
            for r in rubrics.values():
                b["stored_rubrics"] += 1
                if r.get("instrument"):
                    b["stored_rubrics_with_instrument"] += 1
    out = {
        "what": "Codex C3(a) / R6-54: how many EXISTING accepts would enter the author review queue, by branch",
        "instrument": "live-1 cell states (stored verdicts) + the committed recovery-packets cards (what is seated); "
                      "no model call, no network",
        "readings": {
            "A": "literal C3(a): ACCEPT_WITH_CAVEAT at a PARTIAL final floor. The DISSENTING_VOTE limb cannot fire on a "
                 "stored verdict: every one was a single call per model, so there is no vote to dissent from",
            "B": "A, plus accepts whose two stored models returned different verdict classes",
            "C": "B, plus accepts whose two stored models returned different floors"},
        "by_branch": {br: dict(c) for br, c in sorted(by_branch.items())},
        "totals": {k: sum(c[k] for c in by_branch.values())
                   for k in ("accepts", "accepts_seated", "A", "A_seated", "B", "B_seated", "C", "C_seated",
                             "stored_rubrics", "stored_rubrics_with_instrument")},
        "items": sorted(rows, key=lambda r: (r["branch"], r["queue_id"], r["candidate_id"])),
    }
    with open(os.path.join(HERE, "queue-volume.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(json.dumps({"by_branch": out["by_branch"], "totals": out["totals"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
