"""Session 14, phase 2: production majority voting and the author review queue (R6-54; Codex C1(a), C3(a)).

  C1(a)  a branch run makes three gate6-v1.3 calls per candidate and takes the majority over verdict class; the floor
         is the lowest floor among the majority, so rule 2a stands; opus routes are voted the same way; every verdict
         records its instrument; no seated verdict reaches public certification on anything but a v1.3 majority verdict.
  C3(a)  doubt is any dissenting vote, or ACCEPT_WITH_CAVEAT at PARTIAL; the queue is a committed file; both the packet
         builder and the emit step refuse to pass a queued item until the author has ruled on it."""
import glob
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import review_queue, prompts  # noqa: E402
from sjn_recovery.config import RUNS_DIR  # noqa: E402
from sjn_recovery.agents import (CellRunner, VOTES_PER_CANDIDATE, VOTING_MAJORITY, VOTING_SINGLE_CALL,  # noqa: E402
                                 instrument, is_voted_v13, vote)


def _reply(floor, verdict="ACCEPT", subj="Y", act="Y", code="OK", **extra):
    return json.dumps(dict({"phrase_verbatim": "Y", "subject_is_required": subj, "grammatical_subject": "God",
                            "speech_act_is_assertion": act, "floor": floor, "floor_reason": "r", "hazard_flags": [],
                            "verdict": verdict, "reason_code": code, "reason": "r"}, **extra))


def _draw(verdict, floor, version="gate6-v1.3"):
    return {"status": "DONE", "verdict": verdict, "floor": floor, "phrase_verbatim": "Y", "subject_is_required": "Y",
            "speech_act_is_assertion": "Y", "prompt_version": version, "verdict_model": verdict}


class _Llm:
    """Replies popped in call order per model; every (model, attempt) is recorded so replicate identities are visible."""
    REPLICATE_STRIDE = 100

    def __init__(self, replies):
        self.replies = {m: list(v) for m, v in replies.items()}
        self.calls = []
        self.run_id = "t"

    def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
        self.calls.append({"role": role, "model": model, "attempt": attempt, "meta": meta})
        return self.replies[model].pop(0), {"call_id": f"{model}-a{attempt}"}


class _Reg:
    verifier_routing = "PRIMARY_ONLY"
    fallback_ids = set()

    def __init__(self):
        self.by_id = {"BSR-LU-01": {"branch": "Lutheran", "authority_tier": "CONFESSIONAL"}}

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return False

    def is_fallback(self, rid):
        return False

    def is_witness(self, rid):
        return False

    def for_branch(self, branch, include_fallback=True, citable_only=True):
        return [dict(r, registry_id=k) for k, r in self.by_id.items()]

    def public(self, rid):
        return {"standard_title": rid, "authority_tier": "CONFESSIONAL", "scope_caveat": "", "reception_scope": "JURISDICTIONAL",
                "witness_only": False, "speaks_for": "Lutheran churches"}

    def citation_refusal(self, rid):
        return None


_PRED = {"F": {"family_id": "F", "predicate": "Creator", "definition": "d", "floor_note": "f", "subject_scope": "GOD",
               "family_code": "A", "lexical_floor": False, "mode": "m"}}
_CAND = {"candidate_id": "Q-900-p1-BSR-LU-01-1", "pass": 1, "registry_id": "BSR-LU-01", "locator": "L",
         "phrase": "maker of heaven and earth", "rationale": "r", "floor_claim": "FULL",
         "chunk_text": "the Father almighty, maker of heaven and earth", "chunk_hash": "h", "division": "d",
         "fallback_tier": False, "witness": False, "effective_tier": "CONFESSIONAL", "locator_rank": 1}


def _run_one(tmp_path, sonnet_replies, qid="Q-900"):
    llm = _Llm({"sonnet": list(sonnet_replies)})
    r = CellRunner(llm, _Reg(), _PRED, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)
    cid = f"{qid}-p1-BSR-LU-01-1"
    st = {"queue_id": qid, "branch": "Lutheran", "family_id": "F", "predicate": "Creator", "coding": {}, "phase": "verify-1",
          "passes": {"1": {"status": "DONE", "standards": ["BSR-LU-01"], "candidates": [dict(_CAND, candidate_id=cid)],
                           "dropped": [], "unslotted": []}},
          "verifications": {}, "routing": "PRIMARY_ONLY", "primary": "sonnet", "adjudicator": None, "slice_rows": []}
    cell = {"queue_id": qid, "branch": "Lutheran", "family_id": "F", "predicate": "Creator"}
    assert r._verify_pass(cell, st, "1") is False
    return llm, st, st["verifications"][cid]


# ---------------------------------------------------------------- C1(a): three calls, one majority
def test_a_branch_run_makes_three_v13_calls_per_candidate_under_distinct_identities(tmp_path):
    llm, st, v = _run_one(tmp_path, [_reply("FULL")] * 3)
    verifier_calls = [c for c in llm.calls if c["role"] == "verifier"]
    assert len(verifier_calls) == VOTES_PER_CANDIDATE == 3
    # Each draw has its own identity: replicate r takes attempt base 100*r, so the audit log's duplicate suppression
    # cannot serve one answer back as three. Replicate 0 keeps attempt 0 — every pre-session-14 identity is unchanged.
    assert [c["attempt"] for c in verifier_calls] == [0, 100, 200]
    assert [c["meta"]["replicate"] for c in verifier_calls] == [0, 1, 2]
    inst = v["sonnet"]["instrument"]
    assert inst["prompt_version"] == "gate6-v1.3" and inst["call_count"] == 3 and inst["voting"] == VOTING_MAJORITY
    assert len(v["sonnet"]["replicates"]) == 3


def test_the_majority_is_over_verdict_class_and_a_single_dissent_does_not_carry_the_verdict(tmp_path):
    reject = _reply("FULL", verdict="REJECT", subj="N", code="WRONG_SUBJECT")
    llm, st, v = _run_one(tmp_path, [_reply("FULL"), _reply("FULL"), reject])
    inst = v["sonnet"]["instrument"]
    assert inst["majority_class"] == "ACCEPT" and inst["majority_share"] == "2/3"
    assert inst["vote_split"] == {"ACCEPT": 2, "REJECT": 1} and inst["dissent"] is True
    assert v["final"]["verdict"] == "ACCEPT"
    llm, st, v = _run_one(tmp_path, [reject, reject, _reply("FULL")], qid="Q-902")
    assert v["sonnet"]["instrument"]["majority_class"] == "REJECT" and v["final"]["verdict"] == "REJECT"


def test_the_floor_is_the_lowest_floor_among_the_majority_so_rule_2a_stands(tmp_path):
    # three draws of one class (ACCEPT_WITH_CAVEAT) at FULL, PARTIAL, FULL: the whole vote is the majority, and the
    # floor is the LOWEST among it — 2a's rule, inside one model's vote rather than across two models
    caveat = lambda f: _reply(f, verdict="ACCEPT_WITH_CAVEAT")
    llm, st, v = _run_one(tmp_path, [caveat("FULL"), caveat("PARTIAL"), caveat("FULL")])
    assert v["sonnet"]["instrument"]["majority_share"] == "3/3"
    assert v["sonnet"]["floor"] == "PARTIAL" and v["sonnet"]["instrument"]["floor_by_replicate"] == ["FULL", "PARTIAL", "FULL"]
    assert v["sonnet"]["instrument"]["floor_rule"].startswith("LOWEST_FLOOR_AMONG_THE_MAJORITY")
    assert v["final"]["floor_final"] == "PARTIAL" and v["final"]["verdict"] == "ACCEPT_WITH_CAVEAT"
    # a DISSENTING draw's floor is not in the majority, so it cannot lower the merged floor — "among the majority",
    # not "among the draws". A WORD_ONLY reject beside two FULL accepts leaves the accept at FULL.
    voted = vote([_draw("ACCEPT", "FULL"), _draw("ACCEPT", "FULL"), _draw("REJECT", "WORD_ONLY")])
    assert voted["floor"] == "FULL" and voted["verdict"] == "ACCEPT" and voted["instrument"]["dissent"] is True


def test_a_majority_whose_lowest_floor_is_word_only_refuses_below_floor(tmp_path):
    llm, st, v = _run_one(tmp_path, [_reply("PARTIAL", verdict="ACCEPT_WITH_CAVEAT"),
                                     _reply("WORD_ONLY", verdict="ACCEPT_WITH_CAVEAT"),
                                     _reply("FULL", verdict="REJECT", subj="N", code="WRONG_SUBJECT")])
    assert v["sonnet"]["floor"] == "WORD_ONLY"
    assert v["final"]["verdict"] == "REJECT" and v["final"]["reason_code_final"] == "BELOW_FLOOR"


def test_a_vote_with_no_majority_fails_closed_to_the_most_conservative_class():
    voted = vote([_draw("ACCEPT", "FULL"), _draw("ACCEPT_WITH_CAVEAT", "PARTIAL"), _draw("REJECT", "FULL")])
    assert voted["instrument"]["no_majority"] is True
    assert voted["instrument"]["majority_class"] == "REJECT"          # never a plurality of one


def test_opus_routes_are_voted_the_same_way(tmp_path):
    reject = _reply("FULL", verdict="REJECT", subj="N", code="WRONG_SUBJECT")
    llm = _Llm({"sonnet": [reject] * 3, "opus": [_reply("FULL")] * 3})
    reg = _Reg()
    reg.verifier_routing = "SECONDARY_ALL"
    r = CellRunner(llm, reg, _PRED, {}, str(tmp_path), "sonnet", ["sonnet", "opus"], log=lambda m: None, run_coder=False)
    cid = "Q-901-p1-BSR-LU-01-1"
    st = {"queue_id": "Q-901", "branch": "Lutheran", "family_id": "F", "predicate": "Creator", "coding": {}, "phase": "verify-1",
          "passes": {"1": {"status": "DONE", "standards": ["BSR-LU-01"], "candidates": [dict(_CAND, candidate_id=cid)],
                           "dropped": [], "unslotted": []}},
          "verifications": {}, "routing": "SECONDARY_ALL", "primary": "sonnet", "adjudicator": "opus", "slice_rows": []}
    cell = {"queue_id": "Q-901", "branch": "Lutheran", "family_id": "F", "predicate": "Creator"}
    assert r._verify_pass(cell, st, "1") is False
    v = st["verifications"][cid]
    assert sum(1 for c in llm.calls if c["model"] == "opus") == VOTES_PER_CANDIDATE
    assert v["opus"]["instrument"]["voting"] == VOTING_MAJORITY and v["opus"]["instrument"]["call_count"] == 3
    assert is_voted_v13(v["sonnet"]) and is_voted_v13(v["opus"])
    assert v["final"]["instrument"].keys() == {"sonnet", "opus"}


def test_all_three_draws_are_issued_before_a_vote_is_taken(tmp_path):
    """A pending draw never becomes a two-call majority: verify_voted returns PENDING with every call issued."""
    class _Pending(_Llm):
        def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
            self.calls.append({"role": role, "model": model, "attempt": attempt, "meta": meta})
            if attempt >= 200:
                return None, {"call_id": f"{model}-a{attempt}"}
            return self.replies[model].pop(0), {"call_id": f"{model}-a{attempt}"}

    llm = _Pending({"sonnet": [_reply("FULL")] * 2})
    r = CellRunner(llm, _Reg(), _PRED, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)
    cell = {"queue_id": "Q-903", "branch": "Lutheran", "family_id": "F", "predicate": "Creator"}
    out = r.verify_voted(cell, dict(_CAND), "sonnet")
    assert out["status"] == "PENDING" and out["voting"]["answered"] == 2 and out["voting"]["pending"] == 1
    assert len([c for c in llm.calls if c["role"] == "verifier"]) == 3


# ---------------------------------------------------------------- C1(a): instrument on every verdict
def test_a_stored_verdict_is_labelled_with_its_actual_instrument_never_relabelled_as_a_majority():
    stored = {"status": "DONE", "verdict": "ACCEPT", "floor": "FULL", "prompt_version": "gate6-v1.1", "call_id": "x"}
    inst = instrument(stored)
    assert inst["call_count"] == 1 and inst["voting"] == VOTING_SINGLE_CALL and inst["vote_split"] is None
    assert inst["prompt_version"] == "gate6-v1.1"
    assert is_voted_v13(stored) is False
    assert is_voted_v13(dict(stored, prompt_version="gate6-v1.3")) is False      # a v1.3 SINGLE call is not a majority


def test_no_seated_verdict_reaches_public_certification_on_anything_but_a_v13_majority_verdict(tmp_path):
    llm, st, v = _run_one(tmp_path, [_reply("FULL")] * 3)
    assert v["final"]["v13_majority"] is True and v["final"]["public_certification_eligible"] is True
    # a majority at another version is not eligible either
    voted = vote([_draw("ACCEPT", "FULL", "gate6-v1.2")] * 3)
    assert is_voted_v13(voted) is False
    # and every verdict the seven finished branches actually carry is a SINGLE call: not one is eligible
    seen = 0
    for f in sorted(glob.glob(os.path.join(RUNS_DIR, "live-1", "cells", "*.json")))[:40]:
        state = json.load(open(f, encoding="utf-8"))
        for cid, ver in (state.get("verifications") or {}).items():
            for m, rub in ver.items():
                if isinstance(rub, dict) and m not in ("final", "_route", "final_at_run", "superseded_rubrics", "reverified"):
                    seen += 1
                    assert instrument(rub)["voting"] == VOTING_SINGLE_CALL, (f, cid, m)
                    assert is_voted_v13(rub) is False, (f, cid, m)
    assert seen > 100, "the test binds only if it read real stored rubrics"


# ---------------------------------------------------------------- C3(a): doubt, and the queue
def test_doubt_is_any_dissenting_vote_or_accept_with_caveat_at_partial(tmp_path):
    reject = _reply("FULL", verdict="REJECT", subj="N", code="WRONG_SUBJECT")
    _, _, v = _run_one(tmp_path, [_reply("FULL"), _reply("FULL"), reject])
    assert v["final"]["review_queue_reasons"] == [review_queue.REASON_DISSENT]
    _, _, v = _run_one(tmp_path, [_reply("PARTIAL", verdict="ACCEPT_WITH_CAVEAT")] * 3, qid="Q-904")
    assert v["final"]["review_queue_reasons"] == [review_queue.REASON_CAVEAT_AT_PARTIAL]
    _, _, v = _run_one(tmp_path, [_reply("FULL")] * 3, qid="Q-905")
    assert v["final"]["review_queue_reasons"] == []
    _, _, v = _run_one(tmp_path, [reject] * 3, qid="Q-906")          # the queue is for doubtful ACCEPTS only
    assert v["final"]["verdict"] == "REJECT" and v["final"]["review_queue_reasons"] == []


def test_no_code_path_refuses_on_a_model_self_report_at_the_version_in_force(tmp_path):
    """Codex C3's own test: 'Does any code path refuse on a model self-report?' The one guard that ever did (R6-18's
    asserted_outside_formula, which refused TP-045 / Chalcedon) is scoped to gate6-v1.6, not the version in force.
    Doubt QUEUES; it never refuses."""
    assert prompts.prompt_version("verifier") == "gate6-v1.3"
    assert "gate6-v1.3" not in prompts.OUTSIDE_FORMULA_GUARDED_VERSIONS
    _, _, v = _run_one(tmp_path, [_reply("FULL", asserted_outside_formula="Y")] * 3)
    assert v["final"]["verdict"] == "ACCEPT" and "refused_by" not in v["sonnet"]
    assert v["final"]["review_queue_reasons"] == []


def test_the_queue_is_a_committed_file_with_the_shape_r6_54_ruled():
    q = review_queue.load()
    assert q["schema"] == review_queue.SCHEMA
    assert q.get("_missing") is not True, "the queue file is committed; a missing file is not the ruled state"
    assert os.path.exists(review_queue.QUEUE_PATH)
    assert set(q["doubt"]) == set(review_queue.REASONS)


def test_an_item_is_held_until_the_author_rules_and_an_unknown_decision_fails_closed(tmp_path, monkeypatch):
    p = tmp_path / "q.json"
    base = {"schema": review_queue.SCHEMA, "what": "t", "ruling": review_queue.RULING, "items": [
        {"queue_id": "Q-001", "candidate_id": "C-held", "reasons": [review_queue.REASON_DISSENT]},
        {"queue_id": "Q-002", "candidate_id": "C-admit", "reasons": [review_queue.REASON_DISSENT],
         "author_ruling": {"decision": "ADMIT", "ruled": "2026-09-19", "why": "read it"}},
        {"queue_id": "Q-003", "candidate_id": "C-refuse", "reasons": [review_queue.REASON_CAVEAT_AT_PARTIAL],
         "author_ruling": {"decision": "REFUSE", "ruled": "2026-09-19", "why": "not the assertion"}},
    ]}
    p.write_text(json.dumps(base), encoding="utf-8")
    monkeypatch.setattr(review_queue, "QUEUE_PATH", str(p))
    assert review_queue.hold("C-held")["state"] == "AWAITING_AUTHOR_RULING"
    assert review_queue.hold("C-admit") is None
    assert review_queue.hold("C-refuse")["state"] == "REFUSED_BY_AUTHOR"
    assert review_queue.hold("C-not-queued") is None
    assert sorted(review_queue.held_candidates()) == ["C-held", "C-refuse"]
    assert review_queue.held_queue_ids() == ["Q-001", "Q-003"]
    # fail closed: a decision outside the vocabulary is a hard stop, never a silent pass
    bad = dict(base)
    bad["items"] = [dict(base["items"][0], author_ruling={"decision": "PROBABLY", "ruled": "2026-09-19"})]
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SystemExit):
        review_queue.load()


def test_a_queued_item_cannot_reach_src_data_sjn_or_any_publishable_output(tmp_path, monkeypatch):
    from sjn_pipeline import emit
    p = tmp_path / "q.json"
    p.write_text(json.dumps({"schema": review_queue.SCHEMA, "what": "t", "ruling": review_queue.RULING, "items": [
        {"queue_id": "Q-237", "candidate_id": "Q-237-p1-BSR-AN-04-1", "reasons": [review_queue.REASON_DISSENT]}]}),
        encoding="utf-8")
    monkeypatch.setattr(review_queue, "QUEUE_PATH", str(p))
    # (a) the candidate id anywhere in a payload about to be written
    payload = {"cells.json": {"cells": [{"id": "Q-101", "certified": True,
                                         "evidence": {"source_note": "Q-237-p1-BSR-AN-04-1"}}]}}
    with pytest.raises(review_queue.QueuedItemWouldPublish):
        emit.assert_review_queue_clear(payload)
    # (b) a CERTIFIED cell whose id carries a held item, even with no candidate id in sight
    with pytest.raises(review_queue.QueuedItemWouldPublish):
        emit.assert_review_queue_clear({"cells.json": {"cells": [{"id": "Q-237", "certified": True, "evidence": {}}]}})
    # (c) the same cell NOT certified passes: the bar is on publication, not on the workbench
    emit.assert_review_queue_clear({"cells.json": {"cells": [{"id": "Q-237", "certified": False, "evidence": None}]}})
    # (d) once the author rules ADMIT, it passes
    p.write_text(json.dumps({"schema": review_queue.SCHEMA, "what": "t", "ruling": review_queue.RULING, "items": [
        {"queue_id": "Q-237", "candidate_id": "Q-237-p1-BSR-AN-04-1", "reasons": [review_queue.REASON_DISSENT],
         "author_ruling": {"decision": "ADMIT", "ruled": "2026-09-19", "why": "read"}}]}), encoding="utf-8")
    emit.assert_review_queue_clear({"cells.json": {"cells": [{"id": "Q-237", "certified": True,
                                                              "evidence": {"source_note": "Q-237-p1-BSR-AN-04-1"}}]}})


def test_the_emit_step_calls_the_bar_before_it_writes_any_file():
    """The bar is worthless if it runs after the first dump(). Checked on the build script's own source."""
    src = open(os.path.join(os.path.dirname(RUNS_DIR), "..", "..", "scripts", "sjn-build-data.py"), encoding="utf-8").read() \
        if False else open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                        "sjn-build-data.py"), encoding="utf-8").read()
    bar = src.index("assert_review_queue_clear")
    write = src.index("for name, obj in files.items():")
    assert bar < write, "the review-queue bar must run before the first file is written"


def test_the_packet_builder_refuses_to_seat_a_queued_item():
    """packets.build_branch_packet's half of the bar, read on its own source and on the card contract: a held candidate
    never reaches `accepted` (so the allocator cannot seat it, lead with it, or record it as a parallel witness), it is
    kept under review_queue_held, and it withdraws the card's REVIEWED offer."""
    import inspect
    from sjn_recovery import packets as pk
    src = inspect.getsource(pk.build_branch_packet)
    i_hold = src.index("review_queue.hold(cand[\"candidate_id\"]")
    i_accept = src.index("accepted.append(entry)")
    assert i_hold < i_accept, "the hold must be tested before the entry is accepted"
    assert "card[\"review_queue_held\"].append(entry)" in src
    # and the REVIEWED offer is withdrawn while anything is held
    opt = pk.empty_result_option({"BSR-X": {"coverage": "FULL", "supplied": 3, "of": 3}}, {"BSR-X": "none"})
    assert opt["offered"] is True
    opt = pk.empty_result_option({"BSR-X": {"coverage": "FULL", "supplied": 3, "of": 3}}, {"BSR-X": "none"},
                                 review_queue_held=[{"candidate_id": "C-1", "reasons": [review_queue.REASON_DISSENT],
                                                     "state": "AWAITING_AUTHOR_RULING"}])
    assert opt["offered"] is False and opt["review_queue_held"] == ["C-1"]
    assert "author review queue" in opt["why_not_offered"]
