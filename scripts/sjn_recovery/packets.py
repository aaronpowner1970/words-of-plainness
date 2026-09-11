"""Packet builder (spec §4, script not agent): per-cell cards for the Decision Console.

Re-asserts every phrase against the stored chunk and DROPS failures before the author sees them.
Keeps every rejected candidate with its rubric, chunk context and reason code (spec §8) in the
`rejections` list of the card — never discarded. The empty-result option is always present."""
import json
import os
import time

from .config import PACKETS_DIR, EMPTY_RESULT
from . import guards, store


def _slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def build_branch_packet(branch, cells, runner, registry, predicates, comparators, run_id, log=print):
    cards, dropped_at_build, n_rej = [], [], 0
    chunk_index = {}
    for r in registry.for_branch(branch):
        for c in store.load_chunks(r["registry_id"]):
            chunk_index[(c["registry_id"], c["locator"])] = c
    for cell in cells:
        st = runner.load(cell["queue_id"])
        pred = predicates[cell["family_id"]]
        comp = comparators.get(cell["family_id"], {})
        card = {
            "queue_id": cell["queue_id"], "branch": branch, "family_id": cell["family_id"], "predicate": pred["predicate"],
            "family_code": pred["family_code"], "definition": pred["definition"], "semantic_floor_note": pred["floor_note"],
            "required_subject": pred["subject_scope"],
            "restoration_comparator": {k: comp.get(k) for k in ("label", "source", "locator", "phrase", "url", "scope_note")},
            "current_rendered_state": cell["rendered_state"],
            "status": "NOT_RUN" if not st else st.get("phase"),
            "candidates": [], "rejections": [],
            "empty_result_option": {"rendered_state": EMPTY_RESULT, "always_available": True,
                                    "standards_reviewed": sorted({rid for p in (st or {}).get("passes", {}).values() for rid in p.get("standards", [])}) if st else []},
            "fallback_used": bool(st and st.get("fallback_used")),
            "coverage": {k: p.get("coverage") for k, p in (st or {}).get("passes", {}).items()},
        }
        if st:
            for pk, p in st["passes"].items():
                for d in p.get("dropped", []):
                    card["rejections"].append({"stage": f"locator guard (pass {pk})", "candidate": d["candidate"], "reason": d["reason"]})
                for cand in p.get("candidates", []):
                    chunk = chunk_index.get((cand["registry_id"], cand["locator"]))
                    ok, why = guards.check_phrase(cand["phrase"], chunk["text"] if chunk else "")
                    if chunk and chunk["text_hash"] != cand.get("chunk_hash"):
                        ok, why = False, "chunk text changed since the locator ran (hash mismatch)"
                    vers = st["verifications"].get(cand["candidate_id"], {})
                    std = registry.public(cand["registry_id"])
                    entry = {
                        "candidate_id": cand["candidate_id"], "pass": cand["pass"], "registry_id": cand["registry_id"],
                        "standard_title": std["standard_title"], "authority_tier": std["authority_tier"], "speaks_for": std["speaks_for"],
                        "scope_caveat": std["scope_caveat"], "fallback_tier": cand["fallback_tier"],
                        "locator": cand["locator"], "phrase": cand["phrase"], "locator_rationale": cand["rationale"],
                        "locator_floor_claim": cand["floor_claim"], "chunk_context": cand["chunk_text"],
                        "source_url": chunk["source_url"] if chunk else None,
                        "verifier_rubrics": {m: {k: v.get(k) for k in ("phrase_verbatim", "subject_is_required", "grammatical_subject",
                                                                     "speech_act_is_assertion", "speech_act_note", "floor", "floor_reason",
                                                                     "hazard_flags", "verdict", "reason_code_final", "reason")}
                                             for m, v in vers.items()},
                        "build_reassertion": {"ok": ok, "detail": why},
                    }
                    primary = runner.primary_rubric(st, cand["candidate_id"])
                    if not ok:
                        entry["dropped_reason"] = f"packet build re-assertion failed: {why}"
                        dropped_at_build.append((cell["queue_id"], cand["candidate_id"], why))
                        card["rejections"].append({"stage": "packet re-assertion", **entry})
                    elif primary.get("verdict") in ("ACCEPT", "ACCEPT_WITH_CAVEAT"):
                        entry["coder_proposal"] = st.get("coding", {}).get(cand["candidate_id"])
                        card["candidates"].append(entry)
                    else:
                        n_rej += 1
                        card["rejections"].append({"stage": "verifier", "reason_code": primary.get("reason_code_final"), **entry})
            # fallback guard: a fallback citation never renders alongside a non-fallback witness
            if any(not c["fallback_tier"] for c in card["candidates"]):
                moved = [c for c in card["candidates"] if c["fallback_tier"]]
                for c in moved:
                    c["dropped_reason"] = "fallback-tier witness suppressed: a non-fallback standard yielded a candidate"
                    card["rejections"].append({"stage": "fallback-tier guard", **c})
                card["candidates"] = [c for c in card["candidates"] if not c["fallback_tier"]]
            card["candidates"] = card["candidates"][:3]
            card["status"] = "EMPTY" if (st.get("phase") == "DONE" and not card["candidates"]) else st.get("phase")
        cards.append(card)
    packet = {
        "branch": branch, "run_id": run_id, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "app_master_version": registry.app_master_version, "registry_rows": [registry.public(r["registry_id"]) for r in registry.for_branch(branch)],
        "cells": len(cards), "cells_with_candidates": sum(1 for c in cards if c["candidates"]),
        "cells_empty": sum(1 for c in cards if c["status"] == "EMPTY"), "rejections_kept": sum(len(c["rejections"]) for c in cards),
        "dropped_at_build": dropped_at_build, "no_ranking": "counts are workbench totals for the author; never learner-facing",
        "cards": cards,
    }
    os.makedirs(PACKETS_DIR, exist_ok=True)
    path = os.path.join(PACKETS_DIR, f"{_slug(branch)}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(packet, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    log(f"   packet {path}: {packet['cells']} cells, {packet['cells_with_candidates']} with candidates, {packet['cells_empty']} empty, "
        f"{packet['rejections_kept']} rejections kept, {len(dropped_at_build)} dropped at build")
    return packet
