"""Review-support extract (Gate 6 session 5, Task 9): one small JSON per branch, readable whole, so a review never has to
parse a megabyte packet.

  python scripts/sjn_recovery/extract.py                     # every packet in recovery-packets/ -> recovery-packets/extracts/
  python scripts/sjn_recovery/extract.py --branch Baptist

Written automatically by packets.build_branch_packet every time a packet is written (from session 5 on).

Contents — no prose beyond the refusal line the card itself shows, no chunk text, no rubric narrative:
  branch totals   the packet header's counts, partial / cap_state, rows_without_text, branch_ran_on, rows NO TEXT on cards,
                  rows built on an unratified URL, and the speaks_for slot distribution
  per cell        queue_id, predicate, status, candidate / rejection counts, the empty option (rendered_state, offered,
                  why_not_offered, review_incomplete) and each standards_reviewed entry (registry_id / status / supplied / of / share)
  per candidate   candidate_id, registry_id, speaks_for_group, slot (card position), verification_slot, found_in_exhaustion,
                  verdict, floor_final, floor_by_model, floor_disagreement, lower_floor_applied, route, second_rubric_role,
                  hazard_flags per model
                  parallel_witnesses (session 6, R6-4: [candidate_id, registry_id, rule] recorded on the seated entry)
  per rejection   candidate_id, registry_id, speaks_for_group, stage, reason_code, floor_final"""
import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(HERE))
    from sjn_recovery.config import PACKETS_DIR  # noqa: E402
else:
    from .config import PACKETS_DIR  # noqa: E402

HEADER_KEYS = ("branch", "run_id", "built_at", "app_master_version", "partial", "cap_state", "cells", "cells_with_candidates", "cells_empty",
               "cells_empty_reviewed_offered", "cells_empty_review_incomplete", "cells_not_finished", "cells_all_rejected",
               "cells_exhaustion_entered", "cells_exhaustion_changed_outcome", "cards_with_exhaustion_sourced_candidates",
               "exhaustion_sourced_candidates_on_cards", "candidates_lower_floor_applied", "rejections_kept", "candidate_cap",
               "branch_ran_on", "cells_ran_on", "rows_with_text", "rows_no_text_on_cards")
STAGE_CODES = {"verifier": None, "tier allocation": "TIER_ALLOCATION", "fallback-tier guard": "FALLBACK_TIER_GUARD",
               "witness-only guard": "WITNESS_ONLY_GUARD", "translation pairing": "TRANSLATION_PAIRING", "packet re-assertion": "PACKET_REASSERTION"}
MODELS = ("sonnet", "opus")


def _stage_code(stage):
    if stage in STAGE_CODES:
        return STAGE_CODES[stage]
    if stage.startswith("locator guard"):
        return "LOCATOR_GUARD"
    if stage.startswith("not slotted"):
        return "NOT_SLOTTED_FOR_VERIFICATION"
    return stage.upper().replace(" ", "_")


def _candidate(e, pos):
    fv = e.get("final_verdict") or {}
    rub = e.get("verifier_rubrics") or {}
    return {"candidate_id": e.get("candidate_id"), "registry_id": e.get("registry_id"), "speaks_for_group": e.get("speaks_for_group"),
            "slot": pos, "verification_slot": e.get("slot"), "role": e.get("role"), "found_in_exhaustion": bool(e.get("found_in_exhaustion")),
            "verdict": fv.get("verdict"), "floor_final": fv.get("floor_final"), "floor_by_model": fv.get("floor_by_model"),
            "floor_disagreement": fv.get("floor_disagreement"), "lower_floor_applied": fv.get("lower_floor_applied"),
            "route": fv.get("route"), "second_rubric_role": fv.get("second_rubric_role"),
            "hazard_flags": {m: (rub.get(m) or {}).get("hazard_flags") for m in MODELS if m in rub},
            "reverified": bool(e.get("superseded_rubrics")), "on_unslotted_prior": None,
            "parallel_witnesses": [[w.get("candidate_id"), w.get("registry_id"), w.get("rule")] for w in e.get("same_text_parallel_witnesses") or []]}


def _rejection(r):
    stage = r.get("stage") or ""
    cand = r.get("candidate") if isinstance(r.get("candidate"), dict) else {}
    fv = r.get("final_verdict") or {}
    return {"candidate_id": r.get("candidate_id"), "registry_id": r.get("registry_id") or cand.get("registry_id"),
            "speaks_for_group": r.get("speaks_for_group"), "stage": stage,
            "reason_code": r.get("reason_code") or fv.get("reason_code_final") or _stage_code(stage), "floor_final": fv.get("floor_final")}


def build_extract(packet):
    cells, slots, leads = [], Counter(), Counter()
    for c in packet.get("cards", []):
        e = c.get("empty_result_option") or {}
        cands = [_candidate(x, i + 1) for i, x in enumerate(c.get("candidates") or [])]
        for x in cands:
            x.pop("on_unslotted_prior", None)
            slots[x["speaks_for_group"]] += 1
        if cands:
            leads[cands[0]["registry_id"]] += 1
        cells.append({
            "queue_id": c.get("queue_id"), "predicate": c.get("predicate"), "status": c.get("status"),
            "candidates_n": len(cands), "rejections_n": len(c.get("rejections") or []),
            "empty_option": {"rendered_state": e.get("rendered_state"), "offered": e.get("offered"), "why_not_offered": e.get("why_not_offered"),
                             "review_incomplete": e.get("review_incomplete"),
                             "standards_reviewed": [{"registry_id": s.get("registry_id"), "status": s.get("status"), "supplied": s.get("supplied"),
                                                     "of": s.get("of"), "share": s.get("share")} for s in e.get("standards_reviewed") or []]},
            "candidates": cands,
            "rejections": [_rejection(r) for r in c.get("rejections") or []],
            # session 14 (R6-54 / Codex C3(a)): accepts the author review queue holds. Listed by id and reason only,
            # never as a citation — the extract is a review aid and a held item is not yet reviewable as evidence.
            "review_queue_held": [{"candidate_id": x.get("candidate_id"), "registry_id": x.get("registry_id"),
                                   "state": (x.get("review_queue") or {}).get("state"),
                                   "reasons": (x.get("review_queue") or {}).get("reasons")}
                                  for x in c.get("review_queue_held") or []],
        })
    header = {k: packet.get(k) for k in HEADER_KEYS if k in packet}
    header["rows_without_text"] = [{"registry_id": x.get("registry_id"), "manifest_status": x.get("manifest_status")} for x in packet.get("rows_without_text") or []]
    header["rows_on_unratified_url"] = [{"registry_id": x.get("registry_id"), "file": x.get("file"), "status": x.get("status")}
                                        for x in packet.get("rows_on_unratified_url") or []]
    header["caveat_slice"] = {k: (packet.get("caveat_slice") or {}).get(k) for k in ("candidates", "overturned", "lower_floor_applied")}
    header["caveat_sample"] = packet.get("caveat_sample")
    header["dropped_at_build"] = len(packet.get("dropped_at_build") or [])
    header["rebuilt_at"] = (packet.get("rebuilt_from") or {}).get("at")
    header["slots_by_speaks_for"] = dict(slots)
    header["leads_by_registry_id"] = dict(leads)
    header["failure_record_only"] = packet.get("failure_record_only")
    stg = packet.get("same_text_guard") or {}
    header["same_text_guard"] = {k: stg.get(k) for k in ("cards", "parallel_witnesses", "declared_same_text_rows")}
    header["author_review_queue"] = {k: (packet.get("author_review_queue") or {}).get(k)
                                     for k in ("file", "items", "held", "admitted", "refused", "held_on_this_branch")}
    header["author_rulings_applied"] = {k: (packet.get("author_rulings_applied") or {}).get(k) for k in ("file", "required_subject_retyped", "registry_retired", "refused_candidates")}
    return {"schema": "sjn-gate6-extract/1", "source_packet": f"recovery-packets/{_slug(packet.get('branch') or '')}.json", "totals": header, "cells": cells}


def _slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def write_extract(packet, packets_dir=None):
    d = os.path.join(packets_dir or PACKETS_DIR, "extracts")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{_slug(packet['branch'])}-extract.json")
    ex = build_extract(packet)
    compact = {"separators": (",", ":"), "ensure_ascii": False}
    # readable whole: the totals indented, then ONE compact line per cell (valid JSON throughout)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('{"schema":' + json.dumps(ex["schema"]) + ',\n"source_packet":' + json.dumps(ex["source_packet"]) + ',\n"totals":'
                 + json.dumps(ex["totals"], ensure_ascii=False, indent=1) + ',\n"cells":[\n')
        fh.write(",\n".join(json.dumps(c, **compact) for c in ex["cells"]))
        fh.write("\n]}\n")
    return path


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch")
    a = ap.parse_args()
    for fn in sorted(os.listdir(PACKETS_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(PACKETS_DIR, fn), encoding="utf-8") as fh:
            pk = json.load(fh)
        if a.branch and pk.get("branch") != a.branch:
            continue
        p = write_extract(pk)
        print(f"{pk['branch']}: {p} ({os.path.getsize(p):,} bytes; packet {os.path.getsize(os.path.join(PACKETS_DIR, fn)):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
