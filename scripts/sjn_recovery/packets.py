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

from .config import (PACKETS_DIR, EMPTY_RESULT, EMPTY_RESULT_INCOMPLETE, MAX_CANDIDATES, ROUTE_CAVEATED_ACCEPT, ROUTE_CAVEAT_SAMPLE,
                     CAVEAT_SAMPLE_SHARE, LOWER_FLOOR_RULE, HAZARD_IDIOM_OR_FORMULA, CONSULTATION_LADDERS)
from .registry import tier_rank
from .allocation import allocate, translation_pairs, translation_pair_evidence, speaks_for_groups
from . import guards, store, rulings

ACCEPTS = ("ACCEPT", "ACCEPT_WITH_CAVEAT")
ORDERING = ("authority tier descending on the effective tier (creed_tier_resolution); the cap filled tier by tier; lower-tier "
            "survivors kept and marked corroborating. WITHIN a tier (ratified 2026-09-13, session 4): candidates are grouped by "
            "the body the row speaks for (speaks_for, resolved — see speaks_for_groups) and no group takes a SECOND slot until "
            "every group with a surviving verified candidate has taken a FIRST; groups are ranked for their first slot by the "
            "existing keys — non-witness before witness (1a), then the locator's floor claim (FULL before PARTIAL) — and only as "
            "the last resort by registry row order, which orders presentation but never decides which body is heard; then each "
            "group's second candidate in the same group order")
VERDICT_RULE = {"rule": LOWER_FLOOR_RULE,
                "2a": "where two models returned different floors for one candidate the LOWER floor is final (never averaged, never the adjudicator's); the verdict is recomputed at that floor",
                "2b": "opus adjudicates lines 1–3 on the reject-all and slice routes as before (a rescue for subject or speech act stands; a rescue by a higher floor does not)",
                "2c": f"caveated accepts are not routed for adjudication; a deterministic sample of at most {int(CAVEAT_SAMPLE_SHARE * 100)}% is sent for disclosure (route {ROUTE_CAVEAT_SAMPLE}), shown on the card, floor-lowering only",
                "3": f"hazard {HAZARD_IDIOM_OR_FORMULA} (verifier gate6-v1.2) caps the floor at WORD_ONLY unless the passage asserts the predicate outside the formula; applied to verifier calls made from session 4 onward, not to stored verdicts"}
WITNESS_FIELDS = ("candidate_id", "registry_id", "standard_title", "authority_tier", "effective_tier", "reception_scope",
                  "reception_note", "locator", "phrase", "locator_rationale", "locator_floor_claim", "chunk_context",
                  "recut_from", "source_url", "verifier_rubrics", "final_verdict", "build_reassertion")
PARALLEL_FIELDS = ("candidate_id", "registry_id", "standard_title", "speaks_for", "speaks_for_group", "authority_tier", "locator", "phrase",
                   "source_url", "final_verdict")
COMPLETE_COVERAGE = ("FULL", "EXHAUSTED")


def _slug(branch):
    return branch.casefold().replace(" / ", "-").replace(" ", "-")


def _stopped_by(partial):
    """What stopped a partial branch, in the card's words (session 5: a run failure is not a cost cap)."""
    if (partial or {}).get("stopped_by") == "RUN_FAILED":
        return f"a run failure (exit {partial.get('exit_code')}): {str(partial.get('reason') or '')[:160]}"
    return "its cost cap"


def _stage_for(reason):
    if reason.startswith("fallback-tier"):
        return "fallback-tier guard"
    if reason.startswith("WITNESS_ONLY"):
        return "witness-only guard"
    if reason.startswith("paired"):
        return "translation pairing"
    if reason.startswith("SAME_TEXT"):
        return "same-text guard"
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


def ladder_tier(registry, rid):
    """The consultation-ladder tier of a row (R6-5 moved BSR-EO-01 from A to B), or None where the branch runs flat.

    Read from the row's `eo_ladder_tier` field first — the workbook's once it carries it, the author ruling's until then
    (registry.registry_overrides) — and otherwise from config.CONSULTATION_LADDERS, the ladder the author ruled in the
    EO launch prompt. A branch with no ladder has None everywhere and the ladder rules below do nothing."""
    row = (getattr(registry, "by_id", {}) or {}).get(rid) or {}
    t = str(row.get("eo_ladder_tier") or "").strip().upper()
    if t:
        return t
    return (CONSULTATION_LADDERS.get(row.get("branch")) or {}).get(rid)


def no_text_rows(st, branch_rows, registry, manifest, card_empty, ladder_entered=None):
    """Session 5 (2026-09-13, after the Baptist packet review): the ratified rows this CELL ran without. Read from the
    cell's own record, never from today's chunk store — a row whose corpus is built after the cell ran is still a row
    the cell never saw. A row is NO TEXT on a card when it is a citable ratified row of the branch and the cell's
    coverage has no entry for it: either the locator recorded NO_CORPUS for it, or it was not in the branch when the
    cell ran. A fallback-only row is consulted only when pass one leaves the cell empty, so it counts on an empty card
    (or wherever pass two ran), never on a filled one.

    Session 7, Task 6 (the EO prompt's defect 1b), returning (no_text, not_consulted): a row the ladder never sent to the
    locator was never a row that "supplied no text" — it was a row the cell had no occasion to open. Confirmed by a direct
    call on a synthetic empty EO card: BSR-EO-11 and BSR-EO-13 (Tier C, witness and lineage rows) came back NO TEXT and
    refused REVIEWED on every EO empty. So:
      * a row not consulted BECAUSE OF ITS LADDER TIER is recorded "NOT CONSULTED (ladder tier X)", not NO TEXT;
      * Tier C rows are excluded from the REVIEWED test altogether;
      * a Tier B row that was DUE — the card is empty after Tier A, so the ladder entered Tier B — and was not consulted
        still blocks REVIEWED, as NO TEXT. BSR-EO-01 is a Tier B row from R6-5, and is included on that footing.
    `ladder_entered`: the ladder tiers this card actually entered (e.g. {"A"} on a Tier-A-filled card, {"A","B"} on an
    empty one). None means the branch runs flat and every row is due, which is every branch before Eastern Orthodox."""
    coverage_final = (st or {}).get("coverage_final") or (_legacy_coverage(st) if st else {})
    passes = (st or {}).get("passes") or {}
    out, not_consulted = [], []
    for r in branch_rows:
        rid = r["registry_id"]
        if rid in coverage_final:
            continue
        tier = ladder_tier(registry, rid)
        if tier and (tier == "C" or (ladder_entered is not None and tier not in ladder_entered)):
            not_consulted.append({"registry_id": rid, "ladder_tier": tier,
                                  "status": f"NOT CONSULTED (ladder tier {tier})",
                                  "reason": (f"ladder tier {tier}: not consulted on open cells at all" if tier == "C" else
                                             f"ladder tier {tier}: the card was resolved at tier(s) "
                                             f"{', '.join(sorted(ladder_entered or []))} and never entered tier {tier}"),
                                  "blocks_reviewed": False})
            continue
        if registry.is_fallback(rid) and not card_empty and "2" not in passes:
            continue
        m = manifest.get(rid) or {}
        recorded = [pk for pk, p in passes.items() if ((p.get("per_standard") or {}).get(rid) or {}).get("status") == "NO_CORPUS"]
        if not st:
            how = "the cell has not run"
        elif recorded:
            how = f"the locator had no corpus for this standard when the cell ran (pass {', '.join(sorted(recorded))}: NO_CORPUS)"
        else:
            how = "the cell ran before this standard had a corpus in the branch; it was never supplied to the locator"
        note = (m.get("notes") or [""])[0]
        out.append({"registry_id": rid, "manifest_status": m.get("status") or "NO MANIFEST ENTRY", "ladder_tier": tier,
                    "reason": how + (f"; manifest now: {m.get('status')}" if m.get("status") else "")
                              + (f" — {note[:160]}" if note and not m.get("text_hash") else "")})
    return out, not_consulted


def empty_result_option(coverage_final, rationales, exhaustion=None, no_text=None, not_consulted=None):
    """2a/2b/2d, pure: the empty-result option for a card. The REVIEWED state is offered only when every
    consulted standard is FULL or EXHAUSTED; a sampled standard blocks the claim and the honest state is named.
    Session 5: a ratified row that supplied the cell NO TEXT is carried in standards_reviewed with status NO TEXT
    and its reason, and blocks the claim exactly as a sampled standard does; a card that consulted nothing offers nothing.
    Session 7 (Task 6): a row the ladder never sent to the locator is carried with status NOT CONSULTED (ladder tier X)
    and its tier, and does NOT block the claim — it is disclosure, not an unread standard."""
    reviewed = []
    incomplete = []
    for nc in not_consulted or []:
        reviewed.append({"registry_id": nc["registry_id"], "coverage": None, "supplied": 0, "of": None, "share": None,
                         "status": nc["status"], "ladder_tier": nc.get("ladder_tier"), "reason": nc.get("reason"),
                         "silence_rationale": nc.get("reason")})
    for nt in no_text or []:
        reviewed.append({"registry_id": nt["registry_id"], "coverage": None, "supplied": 0, "of": None, "share": None,
                         "status": "NO TEXT", "manifest_status": nt.get("manifest_status"), "reason": nt.get("reason"),
                         "silence_rationale": f"NO TEXT: {nt.get('reason')}"})
        incomplete.append(nt["registry_id"])
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
    complete = not incomplete and bool(coverage_final)
    reasons = ([f"{r['registry_id']} supplied no text ({r['manifest_status']}): {r['reason']}" for r in reviewed if r["status"] == "NO TEXT"]
               + [f"{r['registry_id']} was sampled ({r['supplied']} of {r['of']} chunks, {int((r['share'] or 0) * 100)}%)" for r in reviewed if r["status"] == "SAMPLED"])
    if not coverage_final and not reasons:
        reasons = ["no standard was consulted for this cell"]
    return {
        "rendered_state": EMPTY_RESULT if complete else None,
        "offered": complete,
        "honest_state_if_not_offered": None if complete else EMPTY_RESULT_INCOMPLETE,
        "why_not_offered": None if complete else ("'REVIEWED' may not be claimed: " + "; ".join(reasons)),
        "review_incomplete": incomplete,
        "always_available": True,
        "standards_reviewed": reviewed,
        "not_consulted_by_ladder": [{"registry_id": n["registry_id"], "ladder_tier": n.get("ladder_tier")} for n in not_consulted or []],
        "locator_rationale": rationales,
        "exhaustion": exhaustion,
    }


def build_branch_packet(branch, cells, runner, registry, predicates, comparators, run_id, log=print, partial=None, rebuilt_from=None):
    """partial: None for a complete branch; otherwise the cost-cap state dict that stopped it (fix 1d) — the
    packet is still written, every cell carries its phase, and the header says so. rebuilt_from: a note when the
    packet is rebuilt from stored cell states with no new model calls (the Roman Catholic rebuild, 2026-09-13)."""
    pairs = translation_pairs(registry, branch)
    groups = speaks_for_groups(registry, branch)
    manifest = store.load_manifest().get("standards", {})
    manifest_status = {rid: (r.get("status") or "") for rid, r in manifest.items()}
    cards, dropped_at_build, n_rej, repaired_chunks = [], [], 0, []
    chunk_index = {}
    rows_without_text = []
    for r in registry.for_branch(branch, citable_only=False):
        chunks = store.load_chunks(r["registry_id"])
        for c in chunks:
            chunk_index[(c["registry_id"], c["locator"])] = c
        if not chunks:
            m = manifest.get(r["registry_id"]) or {}
            rows_without_text.append({"registry_id": r["registry_id"], "standard_title": registry.public(r["registry_id"])["standard_title"],
                                      "manifest_status": m.get("status") or "NO MANIFEST ENTRY", "fetch_mode": r.get("fetch_mode"),
                                      "notes": m.get("notes") or [], "refused": registry.citation_refusal(r["registry_id"]),
                                      "effect": "no chunks: the locator never saw this standard; every cell of the branch ran without it"})
    caveat_slice, caveat_sample, exhaustion_cells, same_text_cards = [], [], [], []
    citable_rows = registry.for_branch(branch, include_fallback=True, citable_only=True)
    no_text_on_cards = {}
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
            "empty_result_option": None,          # set once the card's status is known (a fallback row counts only on an empty card)
            "fallback_used": bool(st and st.get("fallback_used")),
            "coverage": {k: p.get("coverage") for k, p in (st or {}).get("passes", {}).items()},
            "coverage_final": coverage_final,
            "exhaustion": (st or {}).get("exhaustion"),
            "routing": (st or {}).get("routing"),
            "verdict_rule": (st or {}).get("refinalized", {}).get("rule") if st else None,
            "caveat_slice": runner.caveat_slice_stats(st) if st else [],
            "caveat_sample": runner.caveat_sample_stats(st) if st else [],
            "coder_skipped": (st or {}).get("coder_skipped") or {},
            "exhaustion_sourced_candidates": [],
        }
        if st and st.get("exhaustion"):
            exhaustion_cells.append(cell["queue_id"])
        caveat_slice.extend(card["caveat_slice"])
        caveat_sample.extend(card["caveat_sample"])
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
                    repaired = None
                    if chunk and chunk["text_hash"] != cand.get("chunk_hash"):
                        # The chunk store changed after the locator ran. Where the change is the audited extraction repair
                        # (pdf-audit, 2026-09-13: BSR-AN-04 / BSR-AN-05 / BSR-RP-04 re-chunked) the phrase must still stand
                        # verbatim BOTH in the text the verifier judged and in the repaired chunk; then the candidate is kept
                        # with the disclosure below. Otherwise it is dropped as before — never repaired.
                        ok_then, _ = guards.check_phrase(cand["phrase"], cand.get("chunk_text") or "")
                        if ok and ok_then:
                            repaired = {"chunk_repaired_after_run": True, "hash_at_run": cand.get("chunk_hash"), "hash_now": chunk["text_hash"],
                                        "note": "the row was re-chunked by the extraction repair after this cell ran; the phrase is verbatim in both "
                                                "the chunk the verifier judged and the repaired chunk (recovery-runs/pdf-audit.md)"}
                            why = "verbatim (chunk repaired after the run; phrase verbatim in both texts)"
                        else:
                            ok, why = False, "chunk text changed since the locator ran (hash mismatch) and the phrase is not verbatim in both texts"
                    refusal = registry.citation_refusal(cand["registry_id"])
                    if refusal:
                        ok, why = False, refusal
                    vers = st["verifications"].get(cand["candidate_id"], {})
                    std = registry.public(cand["registry_id"])
                    final = vers.get("final") or {}
                    # Session 7 (R6-5 clause 1, R6-10, R6-6/R6-9): the effective tier is RE-RESOLVED at build time from the
                    # phrase, so a packet always states the tier the rules in force give. The value the cell runner stored
                    # is kept beside it when the two differ, so the change is visible rather than silent.
                    res = registry.tier_resolution(cand["registry_id"], chunk, cand["phrase"])
                    entry = {
                        "candidate_id": cand["candidate_id"], "pass": cand["pass"], "registry_id": cand["registry_id"],
                        "standard_title": std["standard_title"], "authority_tier": std["authority_tier"],
                        "effective_tier": res["effective_tier"], "effective_tier_why": res["why"],
                        "effective_tier_at_run": cand.get("effective_tier"),
                        "effective_tier_changed_since_run": bool(cand.get("effective_tier")) and cand.get("effective_tier") != res["effective_tier"],
                        "registered_phrase_hit": res["registered_phrase_hit"],
                        "adoption": {k: registry.adoption(cand["registry_id"]).get(k) for k in ("adoption_status", "adoption_body_scope", "adoption_act", "source")},
                        "adoption_disclosure": res["adoption_disclosure"], "speaks_for": std["speaks_for"],
                        "reception_scope": std["reception_scope"], "reception_note": std["reception_note"],
                        "scope_caveat": std["scope_caveat"], "fallback_tier": cand["fallback_tier"],
                        "witness": bool(cand.get("witness") or std.get("witness_only")), "slot": cand.get("slot"),
                        "speaks_for_group": (groups.get(cand["registry_id"]) or {}).get("group"),
                        "exhaustion_batch": cand.get("exhaustion_batch"),
                        "found_in_exhaustion": bool(cand.get("exhaustion_batch") is not None or str(cand.get("pass")) == "3"),
                        "locator": cand["locator"], "phrase": cand["phrase"], "locator_rationale": cand["rationale"],
                        "locator_floor_claim": cand["floor_claim"], "chunk_context": cand["chunk_text"],
                        # session 6: the allocator reads `floor_claim` (FULL before PARTIAL within a group); without it every packet
                        # ordered on registry row alone and disagreed with the cell runner's (coder's) allocation on 8 of 247 cards
                        "floor_claim": cand["floor_claim"], "locator_rank": cand.get("locator_rank"),
                        "recut_from": cand.get("recut_from"),
                        "source_url": chunk["source_url"] if chunk else None,
                        "parallel_witness": chunk.get("parallel_witness") if chunk else None,
                        "verifier_rubrics": {m: {k: v.get(k) for k in ("phrase_verbatim", "subject_is_required", "grammatical_subject",
                                                                     "speech_act_is_assertion", "speech_act_note", "floor", "floor_reason",
                                                                     "hazard_flags", "verdict", "reason_code_final", "reason")}
                                             for m, v in vers.items() if isinstance(v, dict) and m not in ("final", "_route", "final_at_run", "superseded_rubrics", "reverified")},
                        "superseded_rubrics": vers.get("superseded_rubrics"),
                        "final_verdict": final,
                        "adjudication_route": vers.get("_route"),
                        "second_rubric_disclosure_only": vers.get("_route") in (ROUTE_CAVEAT_SAMPLE, ROUTE_CAVEATED_ACCEPT),
                        "build_reassertion": {"ok": ok, "detail": why},
                    }
                    if entry["found_in_exhaustion"]:
                        prog = (((st.get("passes") or {}).get("3") or {}).get("progress") or {}).get(cand["registry_id"]) or {}
                        entry["exhaustion_note"] = (f"FOUND IN EXHAUSTION: located in batch {cand.get('exhaustion_batch')} of "
                                                    f"{prog.get('batches_total', '?')} over the chunks of {cand['registry_id']} that the sampled retrieval "
                                                    f"did not supply; passes 1–2 found nothing surviving in this cell")
                    if repaired:
                        entry.update(repaired); repaired_chunks.append((cell["queue_id"], cand["candidate_id"]))
                    if not ok:
                        entry["dropped_reason"] = f"packet build re-assertion failed: {why}"
                        dropped_at_build.append((cell["queue_id"], cand["candidate_id"], why))
                        card["rejections"].append({"stage": "packet re-assertion", **entry})
                    elif runner.final_verdict(st, cand["candidate_id"]) in ACCEPTS:
                        accepted.append(entry)
                    else:
                        n_rej += 1
                        card["rejections"].append({"stage": "verifier", "reason_code": final.get("reason_code_final"), **entry})
            # ---- allocation (allocation.py: fallback guard → translation pairing → witness-only guard → tier order with the
            # speaks_for group rule inside a tier → cap)
            alloc = allocate(accepted, pairs, groups=groups)
            by_id = {e["candidate_id"]: e for e in accepted}
            for cid, reason in alloc["dropped"].items():
                e = by_id[cid]
                e["dropped_reason"] = reason
                stage = _stage_for(reason)
                if stage == "witness-only guard":
                    card["witness_only_candidates"].append(e)
                elif stage == "translation pairing" and cid in alloc["english_witness"].values():
                    continue                      # shown on its controlling entry below, not as a rejection
                elif stage == "same-text guard" and any(w["candidate_id"] == cid for ws in alloc["parallel_witnesses"].values() for w in ws):
                    continue                      # R6-4: shown on the seated entry below as a parallel witness, not as a rejection
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
                pws = alloc["parallel_witnesses"].get(cid) or []
                if pws:
                    e["same_text_parallel_witnesses"] = [
                        dict({k: by_id[w["candidate_id"]].get(k) for k in PARALLEL_FIELDS}, rule=w["rule"], same_text_as=w.get("same_text_as"),
                             note=(f"{w['registry_id']} ({by_id[w['candidate_id']].get('speaks_for')}) publishes this same sentence; one text takes one slot (R6-4)"
                                   if w["rule"] == "SAME_TEXT" else
                                   f"{w['registry_id']} publishes the same text as {w.get('same_text_as')} in different wording; it takes no slot beside it (R6-4, declared row)"))
                        for w in pws]
                    same_text_cards.append({"queue_id": cell["queue_id"], "seated": cid, "seated_registry_id": e["registry_id"],
                                            "parallel": [(w["candidate_id"], w["registry_id"], w["rule"]) for w in pws]})
                e["coder_proposal"] = st.get("coding", {}).get(cid)
                if e["coder_proposal"] is None:
                    e["coder_note"] = ("not coded: this candidate was not allocated when the coder ran (the allocator has since changed, "
                                       "or a higher candidate was dropped at build-time re-assertion) — re-running the branch would code it")
                if e.get("found_in_exhaustion"):
                    card["exhaustion_sourced_candidates"].append(cid)
                card["candidates"].append(e)
            if st.get("phase") == "DONE" and not card["candidates"]:
                card["status"] = "EMPTY_WITNESS_ONLY" if card["witness_only_candidates"] else "EMPTY"
            elif st.get("phase") != "DONE" and partial:
                card["status"] = f"NOT_FINISHED ({st.get('phase')}): branch stopped by {_stopped_by(partial)}"
            else:
                card["status"] = st.get("phase")
        elif partial:
            card["status"] = f"NOT_RUN: branch stopped by {_stopped_by(partial)}"
        # Task 6: the ladder tiers this card actually entered. Read from the cell's own record (the ladder writes it),
        # else derived from the rows the card consulted; None where the branch runs flat and every row is due.
        entered = (st or {}).get("ladder_entered")
        if entered is None and any(ladder_tier(registry, r["registry_id"]) for r in citable_rows):
            entered = sorted({ladder_tier(registry, rid) for rid in coverage_final if ladder_tier(registry, rid)}) or None
        nt, not_consulted = no_text_rows(st, citable_rows, registry, manifest, card_empty=not card["candidates"],
                                         ladder_entered=set(entered) if entered else None)
        card["ladder_entered"] = sorted(entered) if entered else None
        card["not_consulted_by_ladder"] = not_consulted
        card["empty_result_option"] = empty_result_option(coverage_final, rationales, (st or {}).get("exhaustion"),
                                                          no_text=nt, not_consulted=not_consulted)
        for x in nt:
            no_text_on_cards.setdefault(x["registry_id"], {"cards": 0, "empty_cards": 0, "manifest_status": x["manifest_status"]})
            no_text_on_cards[x["registry_id"]]["cards"] += 1
            no_text_on_cards[x["registry_id"]]["empty_cards"] += 0 if card["candidates"] else 1
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
        "rows_without_text": rows_without_text,
        "rows_with_text": [r["registry_id"] for r in registry.for_branch(branch, citable_only=False) if r["registry_id"] not in {x["registry_id"] for x in rows_without_text}],
        "branch_ran_on": f"{len(registry.for_branch(branch, citable_only=False)) - len(rows_without_text)} of {len(registry.for_branch(branch, citable_only=False))} ratified rows have text in the corpus now"
                         + (": " + ", ".join(f"{x['registry_id']} had no text ({x['manifest_status']})" for x in rows_without_text) if rows_without_text else "")
                         + (f" — BUT the cells did not all run on them: " + "; ".join(
                             f"{rid} supplied no text to {v['cards']} of {len(cells)} card(s)" for rid, v in sorted(no_text_on_cards.items()))
                            if no_text_on_cards else ""),
        # session 5: rows_without_text reads today's chunk store; this reads the cells. A row listed here is on those cards
        # as NO TEXT and blocks the REVIEWED offer there, whatever the store holds now.
        "rows_no_text_on_cards": no_text_on_cards,
        # session 5: a corpus built on a draft registry URL (pending the author's ratification) says so on the packet's face
        "rows_on_unratified_url": [{"registry_id": r["registry_id"], **(manifest.get(r["registry_id"]) or {}).get("registry_delta", {})}
                                   for r in registry.for_branch(branch, citable_only=False)
                                   if (manifest.get(r["registry_id"]) or {}).get("registry_delta")],
        "cells_ran_on": (f"every card consulted every ratified row it should have" if not no_text_on_cards else
                         "; ".join(f"{rid} supplied no text to {v['cards']} of {len(cells)} card(s) ({v['empty_cards']} empty; manifest {v['manifest_status']})"
                                   for rid, v in sorted(no_text_on_cards.items()))),
        # session 6: the author rulings applied in memory (rulings.py), and what the one-text-one-slot guard did on this branch
        "author_rulings_applied": dict(rulings.summary(), registry_rows_retired_in_memory=getattr(registry, "rulings_applied", []),
                                       required_subject_by_family={pid: {"predicate": p["predicate"], "source": p.get("subject_scope_source")}
                                                                   for pid, p in predicates.items()
                                                                   if str(p.get("subject_scope_source") or "").startswith(("AUTHOR", "WORKBOOK"))}),
        "same_text_guard": {"rule": "R6-4 one text, one slot: a phrase textually identical (casefold, whitespace and punctuation normalised) to a seated "
                                    "phrase takes no slot and is a parallel witness; a declared same-text row (different wording) likewise",
                            "cards": len(same_text_cards), "parallel_witnesses": sum(len(x["parallel"]) for x in same_text_cards),
                            "declared_same_text_rows": {k: v for k, v in rulings.same_text_rows().items()
                                                        if k in {r["registry_id"] for r in registry.for_branch(branch, citable_only=False)}},
                            "items": same_text_cards},
        "translation_pairs": pairs, "translation_pairs_evidence": translation_pair_evidence(registry, branch),
        "speaks_for_groups": groups,
        "verdict_rule": VERDICT_RULE,
        "ordering": ORDERING, "candidate_cap": MAX_CANDIDATES,
        "cells": len(cards), "cells_with_candidates": sum(1 for c in cards if c["candidates"]),
        "cells_empty": len(empties),
        "cells_empty_reviewed_offered": sum(1 for c in empties if c["empty_result_option"]["offered"]),
        "cells_empty_review_incomplete": sum(1 for c in empties if not c["empty_result_option"]["offered"]),
        "cells_not_finished": sum(1 for c in cards if str(c["status"]).startswith(("NOT_FINISHED", "NOT_RUN"))),
        "cells_all_rejected": sum(1 for c in cards if c["status"] == "EMPTY" and any(r["stage"] == "verifier" for r in c["rejections"])),
        "cells_exhaustion_entered": len(exhaustion_cells),
        "cells_exhaustion_changed_outcome": sum(1 for c in cards if (c.get("exhaustion") or {}).get("changed_outcome")),
        "cards_with_exhaustion_sourced_candidates": sum(1 for c in cards if c["exhaustion_sourced_candidates"]),
        "exhaustion_sourced_candidates_on_cards": sum(len(c["exhaustion_sourced_candidates"]) for c in cards),
        "caveat_slice": {"candidates": len(caveat_slice), "overturned": sum(1 for x in caveat_slice if x.get("overturned")),
                         "lower_floor_applied": sum(1 for x in caveat_slice if x.get("lower_floor_applied")),
                         "routes": sorted({x.get("route") for x in caveat_slice}),
                         "note": f"{ROUTE_CAVEATED_ACCEPT} = the retired session-3 adjudication (stored branches); {ROUTE_CAVEAT_SAMPLE} = the session-4 disclosure sample"},
        "caveat_sample": {"eligible": len(caveat_sample), "sampled": sum(1 for x in caveat_sample if x.get("sampled")),
                          "share_cap": CAVEAT_SAMPLE_SHARE,
                          "share_actual": (round(sum(1 for x in caveat_sample if x.get("sampled")) / len(caveat_sample), 3) if caveat_sample else None)},
        "candidates_lower_floor_applied": sum(1 for c in cards for e in c["candidates"] if (e.get("final_verdict") or {}).get("lower_floor_applied")),
        "chunk_repaired_after_run": repaired_chunks,
        "rejections_kept": sum(len(c["rejections"]) for c in cards),
        "dropped_at_build": dropped_at_build, "no_ranking": "counts are workbench totals for the author; never learner-facing",
        "cards": cards,
    }
    os.makedirs(PACKETS_DIR, exist_ok=True)
    path = os.path.join(PACKETS_DIR, f"{_slug(branch)}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(packet, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    from .extract import write_extract                  # session 5, Task 9: the review extract travels with every packet
    extract_path = write_extract(packet, os.path.dirname(path))
    log(f"   packet {path}{(' (PARTIAL — ' + ('RUN FAILED' if partial.get('stopped_by') == 'RUN_FAILED' else 'cost cap') + ')') if partial else ''}: {packet['cells']} cells, {packet['cells_with_candidates']} with candidates, "
        f"{packet['cells_empty']} empty ({packet['cells_all_rejected']} all-rejected; REVIEWED offered on {packet['cells_empty_reviewed_offered']}, "
        f"review incomplete on {packet['cells_empty_review_incomplete']}), {packet['cells_not_finished']} not finished, "
        f"{packet['rejections_kept']} rejections kept, {len(dropped_at_build)} dropped at build; exhaustion entered on "
        f"{packet['cells_exhaustion_entered']} cell(s), changed {packet['cells_exhaustion_changed_outcome']}, "
        f"{packet['exhaustion_sourced_candidates_on_cards']} exhaustion-sourced candidate(s) on {packet['cards_with_exhaustion_sourced_candidates']} card(s); "
        f"caveat second rubrics {packet['caveat_slice']['candidates']} ({packet['caveat_slice']['lower_floor_applied']} lower-floor applied); "
        f"2c sample {packet['caveat_sample']['sampled']} of {packet['caveat_sample']['eligible']} eligible; "
        f"{len(repaired_chunks)} candidate(s) on chunks repaired after the run"
        + (f"; ROWS WITHOUT TEXT: {[x['registry_id'] for x in rows_without_text]}" if rows_without_text else "")
        + f"; extract {extract_path}")
    return packet
