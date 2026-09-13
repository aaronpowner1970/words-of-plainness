"""Supplementary single-standard pass (Gate 6 session 5, 2026-09-13) — NOT a branch re-run.

  python scripts/sjn_recovery/supplement.py --run-id live-1 --branch Baptist --registry-id BSR-BA-02 --prepare
  python scripts/sjn_recovery/branch_loop.py --run-id live-1 --branch Baptist --branch-cost-cap-usd <spent + allowance> --key-file <.env>
  python scripts/sjn_recovery/supplement.py --run-id live-1 --branch Baptist --registry-id BSR-BA-02 --report

A branch that ran while one of its ratified rows had no corpus (BSR-BA-02: the www redirect; BSR-LU-02: the viewer wrapper)
is completed for THAT standard only. --prepare re-opens pass 1 on every DONE open cell of the branch by removing only that
row's NO_CORPUS locator entry; every other locator entry, rubric, coder proposal and exhaustion record stays and is served
from the stored state. The ordinary loop then issues exactly one new locator call per cell (the standard's own retrieval),
verifies what it finds under the current rules (verifier gate6-v1.2, the lower-floor rule, opus on the reject-all and slice
routes only, the 2c disclosure sample), exhausts the standard where a cell would otherwise stay empty, codes what reaches the
card, and RE-RUNS the slot allocation over all survivors (never appends). A candidate already slotted and verified is never
un-slotted (agents.locate), and earlier exhaustion survivors stay in the running (agents.all_survivors).

--prepare records, per cell, `supplements[]`: the registry id, when, and the card as it stood (kept candidates, lead,
speaks_for groups, empty, REVIEWED offer) so --report can say what moved. Refuses a cell that is not DONE, and a row that
has no chunks now. Nothing writes to the workbook."""
import argparse
import json
import os
import sys
import time
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import RUNS_DIR, PACKETS_DIR  # noqa: E402
from sjn_recovery.registry import Registry, load_queue, open_cells, assert_gate6_scope  # noqa: E402
from sjn_recovery.allocation import speaks_for_groups  # noqa: E402
from sjn_recovery import store  # noqa: E402


def slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def card_snapshot(card, groups):
    kept = [e["candidate_id"] for e in card.get("candidates", [])]
    return {"kept": kept, "lead": kept[0] if kept else None,
            "lead_registry_id": card["candidates"][0]["registry_id"] if kept else None,
            "groups": [(groups.get(e["registry_id"]) or {}).get("group") for e in card.get("candidates", [])],
            "status": card.get("status"), "reviewed_offered": card["empty_result_option"]["offered"]}


def prepare(a, reg, cells, packet):
    groups = speaks_for_groups(reg, a.branch)
    cards = {c["queue_id"]: c for c in packet["cards"]}
    state_dir = os.path.join(RUNS_DIR, a.run_id, "cells")
    reopened, skipped = [], []
    for c in cells:
        p = os.path.join(state_dir, f"{c['queue_id']}.json")
        with open(p, encoding="utf-8") as fh:
            st = json.load(fh)
        if st.get("phase") != "DONE":
            raise SystemExit(f"{c['queue_id']} is not DONE (phase {st.get('phase')}): a supplementary pass starts only from a finished branch")
        p1 = st["passes"]["1"]
        e = (p1.get("per_standard") or {}).get(a.registry_id)
        if e and e.get("status") in ("DONE", "EMPTY"):
            skipped.append(c["queue_id"]); continue
        prior = card_snapshot(cards[c["queue_id"]], groups)
        st.setdefault("supplements", []).append({
            "registry_id": a.registry_id, "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": a.reason, "prior_locator_entry": (e or {}).get("status") or "ABSENT", "prior_card": prior,
            "prior_passes": sorted(st["passes"]), "prior_exhaustion": st.get("exhaustion")})
        (p1.get("per_standard") or {}).pop(a.registry_id, None)
        p1["status"] = "PENDING"
        st["phase"] = "supplement-locate-1"
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
        reopened.append(c["queue_id"])
    print(f"== {a.branch} / {a.registry_id}: pass 1 re-opened on {len(reopened)} cell(s); already supplemented {len(skipped)}")
    return 0


def report(a, reg, cells, packet):
    groups = speaks_for_groups(reg, a.branch)
    state_dir = os.path.join(RUNS_DIR, a.run_id, "cells")
    rows = []
    before_slots, after_slots = Counter(), Counter()
    for card in packet["cards"]:
        with open(os.path.join(state_dir, f"{card['queue_id']}.json"), encoding="utf-8") as fh:
            st = json.load(fh)
        sup = [s for s in st.get("supplements") or [] if s["registry_id"] == a.registry_id]
        if not sup:
            continue
        prior = sup[-1]["prior_card"]
        now = card_snapshot(card, groups)
        before_slots.update(g for g in prior["groups"] if g)
        after_slots.update(g for g in now["groups"] if g)
        new_ids = [cid for cid in now["kept"] if a.registry_id in cid]
        e = ((st["passes"].get("1") or {}).get("per_standard") or {}).get(a.registry_id) or {}
        verdicts = {}
        for pk, pp in st["passes"].items():
            for cand in pp.get("candidates", []):
                if cand["registry_id"] == a.registry_id:
                    verdicts[cand["candidate_id"]] = ((st["verifications"].get(cand["candidate_id"]) or {}).get("final") or {}).get("verdict")
        rows.append({"queue_id": card["queue_id"], "predicate": card["predicate"],
                     "before": prior, "after": now,
                     "empty_to_filled": (not prior["kept"]) and bool(now["kept"]),
                     "filled_to_empty": bool(prior["kept"]) and not now["kept"],
                     "lead_changed": prior["lead"] != now["lead"] and bool(prior["kept"]) and bool(now["kept"]),
                     "lost_slot": [cid for cid in prior["kept"] if cid not in now["kept"]],
                     "new_standard_on_card": new_ids,
                     "new_standard_locator": e.get("status"), "new_standard_coverage": (e.get("coverage") or {}).get("coverage"),
                     "new_standard_candidates": verdicts,
                     "reviewed_offered_before": prior["reviewed_offered"], "reviewed_offered_after": now["reviewed_offered"]})
    out = {"run_id": a.run_id, "branch": a.branch, "registry_id": a.registry_id, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "cells": len(rows),
           "empty_to_filled": [r["queue_id"] for r in rows if r["empty_to_filled"]],
           "filled_to_empty": [r["queue_id"] for r in rows if r["filled_to_empty"]],
           "still_empty": [r["queue_id"] for r in rows if not r["after"]["kept"]],
           "lead_changed": [{"queue_id": r["queue_id"], "from": r["before"]["lead"], "to": r["after"]["lead"]} for r in rows if r["lead_changed"]],
           "lost_slot": [{"queue_id": r["queue_id"], "candidates": r["lost_slot"]} for r in rows if r["lost_slot"]],
           "cards_carrying_the_standard": sum(1 for r in rows if r["new_standard_on_card"]),
           "new_standard_candidates_verified": sum(len(r["new_standard_candidates"]) for r in rows),
           "new_standard_candidates_accepted": sum(1 for r in rows for v in r["new_standard_candidates"].values() if v in ("ACCEPT", "ACCEPT_WITH_CAVEAT")),
           "slots_by_speaks_for_before": dict(before_slots), "slots_by_speaks_for_after": dict(after_slots),
           "reviewed_offered_before": sum(1 for r in rows if r["reviewed_offered_before"] and not r["before"]["kept"]),
           "reviewed_offered_after": sum(1 for r in rows if r["reviewed_offered_after"] and not r["after"]["kept"]),
           "per_cell": rows}
    path = os.path.join(RUNS_DIR, a.run_id, f"supplement-{slug(a.branch)}-{a.registry_id}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_cell"}, ensure_ascii=False, indent=1))
    print(f"-> {path}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--registry-id", required=True)
    ap.add_argument("--reason", default="the row had no corpus when the branch ran; recovered in session 5 (2026-09-13)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--report", action="store_true")
    a = ap.parse_args()
    reg = Registry()
    queue = load_queue(reg.wb)
    assert_gate6_scope(reg, queue, print)
    if a.registry_id not in {r["registry_id"] for r in reg.for_branch(a.branch)}:
        raise SystemExit(f"{a.registry_id} is not a citable ratified row of {a.branch}")
    if not store.load_chunks(a.registry_id):
        raise SystemExit(f"{a.registry_id} has no chunks: build its corpus first")
    cells = [c for c in open_cells(queue) if c["branch"] == a.branch]
    with open(os.path.join(PACKETS_DIR, f"{slug(a.branch)}.json"), encoding="utf-8") as fh:
        packet = json.load(fh)
    return prepare(a, reg, cells, packet) if a.prepare else report(a, reg, cells, packet)


if __name__ == "__main__":
    sys.exit(main())
