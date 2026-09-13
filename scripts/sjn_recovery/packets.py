"""Packet builder (spec §4, script not agent): per-cell cards for the Decision Console.

Re-asserts every phrase against the stored chunk and DROPS failures before the author sees them.
Keeps every rejected candidate with its rubric, chunk context and reason code (spec §8) in the
`rejections` list of the card — never discarded. The empty-result option is always present.

v2.25 additions: every entry carries the row's reception_scope / reception_note; a candidate on a
witness row (TRANSLATION_WITNESS reception, or a tier qualified as a witness — BSR-EO-11) is flagged
WITNESS and a cell may not rest on such candidates alone: where no non-witness candidate survives,
the witness candidates are kept on the card as `witness_only_candidates` and the cell renders EMPTY.
A DIALOGUE_ONLY row never reaches the locator, and is refused again here by name if one somehow did.

Packet-shape fixes adopted 2026-09-12 after the Roman Catholic packet (allocation.py is the single
allocator, shared with the cell runner so the coder is spent only on what reaches the card):
  1a  within an authority tier, witness rows sort after every non-witness row;
  1b  a witness row that is the English translation of a controlling row on the same document is
      shown ON the controlling candidate's entry as `english_witness`, the controlling phrase named
      CONTROLLING — it never competes for a slot and is never coded separately;
  1c  the coder ran only on allocated candidates (the card records `coder_skipped`);
  1d  a branch stopped by its cost cap still gets a packet, marked `partial` with the cap state.

An empty must be auditable (2026-09-13, after the Anglican packet review):
  2a  `empty_result_option.standards_reviewed` carries each standard's coverage — FULL, EXHAUSTED, or
      RETRIEVED supplied-of-total — never a bare list of ids;
  2b  the rendered state NOT LOCATED — CURRENT STANDARD REVIEWED is OFFERED only when every consulted
      standard was read whole (FULL) or exhausted; otherwise the card says which standard was only
      sampled and names the honest state (NOT LOCATED — NOT YET RECOVERED);
  2c  the cell runner exhausts a sampled standard before an empty is declared; the card carries the
      exhaustion record (batches, whether a candidate turned up);
  2d  every empty carries a one-line locator rationale per standard for the silence."""
import json
import os
import time

from .config import PACKETS_DIR, EMPTY_RESULT, EMPTY_RESULT_INCOMPLETE, MAX_CANDIDATES, ROUTE_CAVEATED_ACCEPT
from .registry import tier_rank
from .allocation import allocate, translation_pairs, translation_pair_evidence
from . import guards, store

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
ORDERING = ("authority tier descending on the effective tier (creed_tier_resolution); within a tier every non-witness row "
            "before any witness row (1a); the cap filled tier by tier; lower-tier survivors kept and marked corroborating. "
            "Residual tie-break within a tier and witness class (the whole ordering where every row shares one tier): the "
            "slotting order — each standard's guaranteed (best) candidate in registry row order, then the extra slots by "
            "locator floor claim and locator rank")
WITNESS_FIELDS = ("candidate_id", "registry_id", "standard_title", "authority_tier", "effective_tier", "reception_scope",
                  "reception_note", "locator", "phrase", "locator_rationale", "locator_floor_claim", "chunk_context",
                  "recut_from", "source_url", "verifier_rubrics", "final_verdict", "build_reassertion")
COMPLETE_COVERAGE = ("FULL", "EXHAUSTED")


def _slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def _stage_for(reason):
    if reason.startswith("fallback-tier"):
        return "fallback-tier guard"
    if reason.startswith("WITNESS_ONLY"):
        return "witness-only guard"
    if reason.startswith("paired"):
        return "translation pairing"
    return "tier allocation"


def _legacy_coverage(st):
    """coverage_final for a cell state written before 2026-09-13 (no exhaustion record)."""
    out = {}
    for pk in ("1", "2"):
        for rid, cov in ((st.get("passes") or {}).get(pk) or {}).get("coverage", {}).items():
            if cov:
                out[rid] = {"coverage": cov.get("coverage"), "supplied": cov.get("supplied"), "of": cov.get("of"), "pass": pk}
    return out


def _entry_status(per_standard, rid):
    """(status, silence_rationale, n_candidates) of one standard's locator entry, across passes."""
    e = per_standard.get(rid)
    if not e:
        return None, None, 0
    return e.get("status"), e.get("silence_rationale"), len(e.get("candidates") or [])


def silence_rationales(st, runner, coverage_final, manifest_status):
    """2d: one line per consulted standard saying why the cell has nothing from it."""
    out = {}
    passes = st.get("passes") or {}
    verdict_by_rid = {}
    for pk, p in passes.items():
        for cand in p.get("candidates", []):
            fin = (st.get("verifications", {}).get(cand["candidate_id"]) or {}).get("final") or {}
            v = runner.final_verdict(st, cand["candidate_id"])
            verdict_by_rid.setdefault(cand["registry_id"], []).append(f"{v or '?'}/{fin.get('reason_code_final') or '?'}")
    for rid, cov in coverage_final.items():
        parts = []
        if verdict_by_rid.get(rid):
            n = len(verdict_by_rid[rid])
            parts.append(f"{n} candidate(s) located and verified: " + ", ".join(verdict_by_rid[rid]))
        for pk in ("1", "2"):
            status, rationale, n_c = _entry_status((passes.get(pk) or {}).get("per_standard") or {}, rid)
            if status == "EMPTY":
                parts.append(f"pass {pk} locator: " + (rationale or "NOT LOCATED, no rationale (locator prompt before gate6-v1.4)"))
            elif status == "NO_CORPUS":
                parts.append(f"pass {pk}: no corpus ({manifest_status.get(rid, 'no manifest entry')})")
            elif status == "DONE" and n_c == 0:
                parts.append(f"pass {pk} locator: every candidate failed a code guard (see rejections)")
        p3 = passes.get("3") or {}
        rs = (p3.get("silence_rationale") or {}).get(rid) or []
        prog = (p3.get("progress") or {}).get(rid)
        if prog:
            head = (f"exhaustion: {prog.get('batches_done')} of {prog.get('batches_total')} further batch(es) read"
                    + (" (stopped early: a candidate survived)" if prog.get("stopped_early") else (" — standard exhausted" if prog.get("exhausted") else " — incomplete")))
            if rs:
                head += "; last silence: " + rs[-1]
            parts.append(head)
        if not parts:
            parts.append("no locator record for this standard")
        out[rid] = " | ".join(parts)
    return out


def empty_result_option(coverage_final, rationales, exhaustion=None):
    """2a/2b/2d, pure: the empty-result option for a card. The REVIEWED state is offered only when every
    consulted standard is FULL or EXHAUSTED; a sampled standard blocks the claim and the honest state is named."""
    reviewed = []
    incomplete = []
    for rid in sorted(coverage_final):
        cov = coverage_final[rid] or {}
        rec = {"registry_id": rid, "coverage": cov.get("coverage"), "supplied": cov.get("supplied"), "of": cov.get("of"),
               "share": (round(cov["supplied"] / cov["of"], 3) if cov.get("of") else None),
               "status": "REVIEWED WHOLE" if cov.get("coverage") == "FULL" else ("EXHAUSTED" if cov.get("coverage") == "EXHAUSTED" else "SAMPLED"),
               "silence_rationale": rationales.get(rid)}
        if cov.get("exhaustion"):
            rec["exhaustion"] = cov["exhaustion"]
        if rec["status"] == "SAMPLED":
            incomplete.append(rid)
        reviewed.append(rec)
    complete = not incomplete
    return {
        "rendered_state": EMPTY_RESULT if complete else None,
        "offered": complete,
        "honest_state_if_not_offered": None if complete else EMPTY_RESULT_INCOMPLETE,
        "why_not_offered": None if complete else ("'REVIEWED' may not be claimed: " + "; ".join(
            f"{r['registry_id']} was sampled ({r['supplied']} of {r['of']} chunks, {int((r['share'] or 0) * 100)}%)" for r in reviewed if r["status"] == "SAMPLED")),
        "review_incomplete": incomplete,
        "always_available": True,
        "standards_reviewed": reviewed,
        "locator_rationale": rationales,
        "exhaustion": exhaustion,
    }


def build_branch_packet(branch, cells, runner, registry, predicates, comparators, run_id, log=print, partial=None, rebuilt_from=None):
    """partial: None for a complete branch; otherwise the cost-cap state dict that stopped it (fix 1d) — the
    packet is still written, every cell carries its phase, and the header says so. rebuilt_from: a note when the
    packet is rebuilt from stored cell states with no new model calls (the Roman Catholic rebuild, 2026-09-13)."""
    pairs = translation_pairs(registry, branch)
    manifest_status = {rid: (r.get("status") or "") for rid, r in store.load_manifest().get("standards", {}).items()}
    cards, dropped_at_build, n_rej = [], [], 0
    chunk_index = {}
    for r in registry.for_branch(branch, citable_only=False):
        for c in store.load_chunks(r["registry_id"]):
            chunk_index[(c["registry_id"], c["locator"])] = c
    caveat_slice, exhaustion_cells = [], []
    for cell in cells:
        st = runner.load(cell["queue_id"])
        pred = predicates[cell["family_id"]]
        comp = comparators.get(cell["family_id"], {})
        coverage_final = (st or {}).get("coverage_final") or (_legacy_coverage(st) if st else {})
        rationales = silence_rationales(st, runner, coverage_final, manifest_status) if st else {}
        card = {
            "queue_id": cell["queue_id"], "branch": branch, "family_id": cell["family_id"], "predicate": pred["predicate"],
            "family_code": pred["family_code"], "definition": pred["definition"], "semantic_floor_note": pred["floor_note"],
            "required_subject": pred["subject_scope"],
            "restoration_comparator": {k: comp.get(k) for k in ("label", "source", "locator", "phrase", "url", "scope_note")},
            "current_rendered_state": cell["rendered_state"],
            "status": "NOT_RUN" if not st else st.get("phase"),
            "candidates": [], "rejections": [], "witness_only_candidates": [],
            "empty_result_option": empty_result_option(coverage_final, rationales, (st or {}).get("exhaustion")),
            "fallback_used": bool(st and st.get("fallback_used")),
            "coverage": {k: p.get("coverage") for k, p in (st or {}).get("passes", {}).items()},
            "coverage_final": coverage_final,
            "exhaustion": (st or {}).get("exhaustion"),
            "routing": (st or {}).get("routing"),
            "caveat_slice": runner.caveat_slice_stats(st) if st else [],
            "coder_skipped": (st or {}).get("coder_skipped") or {},
        }
        if st and st.get("exhaustion"):
            exhaustion_cells.append(cell["queue_id"])
        caveat_slice.extend(card["caveat_slice"])
        if st:
            accepted = []
            for pk, p in st["passes"].items():
                for d in p.get("dropped", []):
                    card["rejections"].append({"stage": f"locator guard (pass {pk})", "candidate": d["candidate"], "reason": d["reason"]})
                for cand in p.get("unslotted", []):
                    card["rejections"].append({"stage": f"not slotted for verification (pass {pk})", "candidate": {k: cand.get(k) for k in ("registry_id", "locator", "phrase", "floor_claim")},
                                               "reason": "beyond the guaranteed per-standard slot and the extra slots; kept for the author, never verified"})
                for cand in p.get("candidates", []):
                    chunk = chunk_index.get((cand["registry_id"], cand["locator"]))
                    ok, why = guards.check_phrase(cand["phrase"], chunk["text"] if chunk else "")
                    if ok and chunk:
                        ok, why = guards.check_noncitable(cand["phrase"], chunk)
                    if chunk and chunk["text_hash"] != cand.get("chunk_hash"):
                        ok, why = False, "chunk text changed since the locator ran (hash mismatch)"
                    refusal = registry.citation_refusal(cand["registry_id"])
                    if refusal:
                        ok, why = False, refusal
                    vers = st["verifications"].get(cand["candidate_id"], {})
                    std = registry.public(cand["registry_id"])
                    final = vers.get("final") or {}
                    entry = {
                        "candidate_id": cand["candidate_id"], "pass": cand["pass"], "registry_id": cand["registry_id"],
                        "standard_title": std["standard_title"], "authority_tier": std["authority_tier"],
                        "effective_tier": cand.get("effective_tier") or std["authority_tier"], "speaks_for": std["speaks_for"],
                        "reception_scope": std["reception_scope"], "reception_note": std["reception_note"],
                        "scope_caveat": std["scope_caveat"], "fallback_tier": cand["fallback_tier"],
                        "witness": bool(cand.get("witness") or std.get("witness_only")), "slot": cand.get("slot"),
                        "exhaustion_batch": cand.get("exhaustion_batch"),
                        "locator": cand["locator"], "phrase": cand["phrase"], "locator_rationale": cand["rationale"],
                        "locator_floor_claim": cand["floor_claim"], "chunk_context": cand["chunk_text"],
                        "recut_from": cand.get("recut_from"),
                        "source_url": chunk["source_url"] if chunk else None,
                        "parallel_witness": chunk.get("parallel_witness") if chunk else None,
                        "verifier_rubrics": {m: {k: v.get(k) for k in ("phrase_verbatim", "subject_is_required", "grammatical_subject",
                                                                     "speech_act_is_assertion", "speech_act_note", "floor", "floor_reason",
                                                                     "hazard_flags", "verdict", "reason_code_final", "reason")}
                                             for m, v in vers.items() if isinstance(v, dict) and m not in ("final", "_route")},
                        "final_verdict": final,
                        "adjudication_route": vers.get("_route"),
                        "build_reassertion": {"ok": ok, "detail": why},
                    }
                    if not ok:
                        entry["dropped_reason"] = f"packet build re-assertion failed: {why}"
                        dropped_at_build.append((cell["queue_id"], cand["candidate_id"], why))
                        card["rejections"].append({"stage": "packet re-assertion", **entry})
                    elif runner.final_verdict(st, cand["candidate_id"]) in ACCEPTS:
                        accepted.append(entry)
                    else:
                        n_rej += 1
                        card["rejections"].append({"stage": "verifier", "reason_code": final.get("reason_code_final"), **entry})
            # ---- allocation (allocation.py: fallback guard → translation pairing → witness-only guard → tier order, witness last → cap)
            alloc = allocate(accepted, pairs)
            by_id = {e["candidate_id"]: e for e in accepted}
            for cid, reason in alloc["dropped"].items():
                e = by_id[cid]
                e["dropped_reason"] = reason
                stage = _stage_for(reason)
                if stage == "witness-only guard":
                    card["witness_only_candidates"].append(e)
                elif stage == "translation pairing" and cid in alloc["english_witness"].values():
                    continue                      # shown on its controlling entry below, not as a rejection
                else:
                    card["rejections"].append({"stage": stage, **e})
            for cid in alloc["kept"]:
                e = by_id[cid]
                e["authority_tier_rank"] = tier_rank(e["effective_tier"])
                e["role"] = alloc["roles"][cid]
                e["corroborating_lower_tier"] = alloc["corroborating_lower_tier"][cid]
                wid = alloc["english_witness"].get(cid)
                if wid:
                    w = by_id[wid]
                    e["controls"] = True
                    e["english_witness"] = {k: w.get(k) for k in WITNESS_FIELDS}
                    e["english_witness"]["note"] = (f"{w['registry_id']} is the English witness of {e['registry_id']}; the "
                                                    f"{e['registry_id']} phrase controls, the witness is shown for reading only")
                e["coder_proposal"] = st.get("coding", {}).get(cid)
                if e["coder_proposal"] is None:
                    e["coder_note"] = ("not coded: this candidate was not allocated when the coder ran (a higher candidate was "
                                       "dropped at build-time re-assertion) — re-run the branch to code it")
                card["candidates"].append(e)
            if st.get("phase") == "DONE" and not card["candidates"]:
                card["status"] = "EMPTY_WITNESS_ONLY" if card["witness_only_candidates"] else "EMPTY"
            elif st.get("phase") != "DONE" and partial:
                card["status"] = f"NOT_FINISHED ({st.get('phase')}): branch stopped by its cost cap"
            else:
                card["status"] = st.get("phase")
        elif partial:
            card["status"] = "NOT_RUN: branch stopped by its cost cap"
        cards.append(card)
    empties = [c for c in cards if c["status"] in ("EMPTY", "EMPTY_WITNESS_ONLY")]
    packet = {
        "branch": branch, "run_id": run_id, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "app_master_version": registry.app_master_version,
        "rebuilt_from": rebuilt_from,
        "partial": bool(partial), "cap_state": partial,
        "registry_rows": [registry.public(r["registry_id"]) for r in registry.for_branch(branch, citable_only=False)],
        "refused_rows": [{"registry_id": r["registry_id"], "reason": registry.citation_refusal(r["registry_id"])}
                         for r in registry.for_branch(branch, citable_only=False) if registry.citation_refusal(r["registry_id"])],
        "corpus_text_hash": {r["registry_id"]: (store.load_manifest().get("standards", {}).get(r["registry_id"]) or {}).get("text_hash")
                             for r in registry.for_branch(branch, citable_only=False)},
        "translation_pairs": pairs, "translation_pairs_evidence": translation_pair_evidence(registry, branch),
        "ordering": ORDERING, "candidate_cap": MAX_CANDIDATES,
        "cells": len(cards), "cells_with_candidates": sum(1 for c in cards if c["candidates"]),
        "cells_empty": len(empties),
        "cells_empty_reviewed_offered": sum(1 for c in empties if c["empty_result_option"]["offered"]),
        "cells_empty_review_incomplete": sum(1 for c in empties if not c["empty_result_option"]["offered"]),
        "cells_not_finished": sum(1 for c in cards if str(c["status"]).startswith(("NOT_FINISHED", "NOT_RUN"))),
        "cells_all_rejected": sum(1 for c in cards if c["status"] == "EMPTY" and any(r["stage"] == "verifier" for r in c["rejections"])),
        "cells_exhaustion_entered": len(exhaustion_cells),
        "cells_exhaustion_changed_outcome": sum(1 for c in cards if (c.get("exhaustion") or {}).get("changed_outcome")),
        "caveat_slice": {"candidates": len(caveat_slice), "overturned": sum(1 for x in caveat_slice if x.get("overturned")),
                         "route": ROUTE_CAVEATED_ACCEPT},
        "rejections_kept": sum(len(c["rejections"]) for c in cards),
        "dropped_at_build": dropped_at_build, "no_ranking": "counts are workbench totals for the author; never learner-facing",
        "cards": cards,
    }
    os.makedirs(PACKETS_DIR, exist_ok=True)
    path = os.path.join(PACKETS_DIR, f"{_slug(branch)}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(packet, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    log(f"   packet {path}{' (PARTIAL — cost cap)' if partial else ''}: {packet['cells']} cells, {packet['cells_with_candidates']} with candidates, "
        f"{packet['cells_empty']} empty ({packet['cells_all_rejected']} all-rejected; REVIEWED offered on {packet['cells_empty_reviewed_offered']}, "
        f"review incomplete on {packet['cells_empty_review_incomplete']}), {packet['cells_not_finished']} not finished, "
        f"{packet['rejections_kept']} rejections kept, {len(dropped_at_build)} dropped at build; exhaustion entered on "
        f"{packet['cells_exhaustion_entered']} cell(s), changed {packet['cells_exhaustion_changed_outcome']}; caveat slice "
        f"{packet['caveat_slice']['candidates']} candidate(s), {packet['caveat_slice']['overturned']} overturned")
    return packet
