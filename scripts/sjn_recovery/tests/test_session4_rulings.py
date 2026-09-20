"""Session 4 (2026-09-13, after the Lutheran / Reformed packet review): the author's rulings, unit-tested.
Run: python -m pytest scripts/sjn_recovery/tests -q

  Task 1  candidate-slot diversity: within a tier no speaks_for group takes a second slot until every group with
          a surviving candidate has a first; "as above" resolves to the previous body; row order is the last resort
  Task 2  the lower floor is final on a model disagreement (2a); opus still rescues on lines 1–3 (2b); the caveat
          sample is disclosure only and bounded at 20% (2c)
  Task 3  IDIOM_OR_FORMULA caps the floor at WORD_ONLY unless the passage asserts the predicate outside the formula
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sjn_recovery.allocation import allocate, speaks_for_groups, normalize_body  # noqa: E402
from sjn_recovery.agents import (CellRunner, lower_floor, verdict_from_rubric, sample_bucket, FLOOR_ORDER,  # noqa: E402
                                 VOTES_PER_CANDIDATE)
from sjn_recovery.config import ROUTE_CAVEAT_SAMPLE, CAVEAT_SAMPLE_SHARE  # noqa: E402


def _c(cid, rid, tier="CONFESSIONAL", floor="FULL", witness=False, reception="JURISDICTIONAL"):
    return {"candidate_id": cid, "registry_id": rid, "authority_tier": tier, "effective_tier": tier, "witness": witness,
            "reception_scope": reception, "locator": "", "fallback_tier": False, "floor_claim": floor}


RP_GROUPS = {"BSR-RP-01": "opc and westminster churches", "BSR-RP-02": "opc and westminster churches", "BSR-RP-03": "opc and westminster churches",
             "BSR-RP-04": "pc(usa)", "BSR-RP-05": "crcna and rca", "BSR-RP-06": "crcna and rca"}


# ---------------------------------------------------------------- Task 1
def test_no_group_takes_a_second_slot_before_every_group_has_a_first():
    # the Reformed defect: three Westminster rows in registry order filled every slot; Heidelberg / Belgic / the Book of Confessions were cut
    cands = [_c("wcf", "BSR-RP-01"), _c("wsc", "BSR-RP-02"), _c("wlc", "BSR-RP-03"), _c("boc", "BSR-RP-04"), _c("heid", "BSR-RP-05"), _c("belg", "BSR-RP-06")]
    a = allocate(cands, groups=RP_GROUPS)
    assert a["kept"] == ["wcf", "boc", "heid"], a["kept"]           # one slot per body; Westminster's second and third wait
    assert "already holds a slot" in a["dropped"]["wsc"] and "already holds a slot" in a["dropped"]["belg"]


def test_groups_rank_by_floor_claim_before_row_order_and_row_order_never_silences_a_body():
    cands = [_c("wcf", "BSR-RP-01", floor="PARTIAL"), _c("wsc", "BSR-RP-02", floor="FULL"), _c("boc", "BSR-RP-04", floor="FULL"), _c("heid", "BSR-RP-05", floor="PARTIAL")]
    a = allocate(cands, groups=RP_GROUPS)
    # group firsts: Westminster's best is wsc (FULL), Book of Confessions boc (FULL), Three Forms heid (PARTIAL)
    assert a["kept"] == ["wsc", "boc", "heid"], a["kept"]
    # with the cap at 2, the third body is cut — but only after every body was ranked, never because of its row position alone
    b = allocate(cands, groups=RP_GROUPS, cap=2)
    assert b["kept"] == ["wsc", "boc"] and "heid" in b["dropped"] and "wcf" in b["dropped"]


def test_second_slots_follow_the_same_group_order_and_single_group_branches_are_unchanged():
    cands = [_c("a1", "BSR-RP-01"), _c("a2", "BSR-RP-02"), _c("b1", "BSR-RP-04")]
    assert allocate(cands, groups=RP_GROUPS)["kept"] == ["a1", "b1", "a2"]
    # Lutheran-shaped: every survivor from one body — the rule has nothing to diversify; floor claim then row order decide
    lu = [_c("x", "BSR-LU-01", floor="PARTIAL"), _c("y", "BSR-LU-01", floor="FULL"), _c("z", "BSR-LU-01", floor="FULL")]
    assert allocate(lu, groups={"BSR-LU-01": "lutheran churches subscribing the book of concord"})["kept"] == ["y", "z", "x"]


def test_tier_still_governs_before_the_group_rule_and_witness_groups_take_their_first_slot_last():
    hi = _c("hi", "BSR-EO-01", tier="CONCILIAR"); hi2 = _c("hi2", "BSR-EO-06", tier="CONCILIAR")
    lo = _c("lo", "BSR-EO-02", tier="CATECHETICAL")
    w = _c("w", "BSR-EO-11", tier="CONCILIAR (witness; translation)", witness=True)
    g = {"BSR-EO-01": "all orthodox", "BSR-EO-06": "all orthodox", "BSR-EO-02": "oca", "BSR-EO-11": "BSR-EO-11"}
    a = allocate([w, hi, hi2, lo], groups=g)
    # tier by tier: CONCILIAR first (hi), then the lower tier's first (lo), then the next CONCILIAR slot — the witness group's
    # FIRST slot precedes 'all orthodox''s SECOND (hi2), which the cap cuts
    assert a["kept"] == ["hi", "w", "lo"], a["kept"]
    assert a["dropped"]["hi2"].startswith("candidate cap")


class _Reg:
    def __init__(self, rows):
        self.rows = rows

    def for_branch(self, branch, include_fallback=True, citable_only=True):
        return [dict(r) for r in self.rows]

    def is_witness(self, rid):
        return next(r for r in self.rows if r["registry_id"] == rid).get("witness", False)


def test_speaks_for_groups_resolve_as_above_semicolons_parentheticals_and_witness_rows():
    rows = [{"registry_id": "BSR-RP-01", "speaks_for": "OPC and Westminster churches"},
            {"registry_id": "BSR-RP-02", "speaks_for": "as above"},
            {"registry_id": "BSR-RP-03", "speaks_for": "as above"},
            {"registry_id": "BSR-RP-04", "speaks_for": 'PC(USA); "subordinate standards" affirmed at ordination'},
            {"registry_id": "BSR-RP-05", "speaks_for": "CRCNA and RCA"},
            {"registry_id": "BSR-RP-06", "speaks_for": "CRCNA and RCA; Dort required subscription"},
            {"registry_id": "BSR-RC-03", "speaks_for": "—", "witness": True},
            {"registry_id": "BSR-AN-03", "speaks_for": "Church of England (appointed in the BCP)"},
            {"registry_id": "BSR-RC-02", "speaks_for": "Universal Church", "standard_title": "Vatican I, *Dei Filius* (Latin, official)"},
            {"registry_id": "BSR-RC-05", "speaks_for": "—", "witness": True, "standard_title": "*Dei Filius* English (EWTN)"}]
    g = speaks_for_groups(_Reg(rows), "x")
    # a translation witness with a derivable controlling row speaks for that row's body; one without is its own group
    assert g["BSR-RC-05"]["group"] == "universal church" and g["BSR-RC-05"]["rule"] == "WITNESS_OF_CONTROLLING_ROW" and g["BSR-RC-05"]["controlling"] == "BSR-RC-02"
    assert g["BSR-RP-02"] == {"raw": "as above", "group": "opc and westminster churches", "rule": "AS_ABOVE_PREVIOUS_ROW"}
    assert g["BSR-RP-03"]["group"] == "opc and westminster churches"
    assert g["BSR-RP-04"]["group"] == "pc(usa)" and g["BSR-RP-04"]["rule"] == "BODY_BEFORE_SEMICOLON"
    assert g["BSR-RP-05"]["group"] == g["BSR-RP-06"]["group"] == "crcna and rca"
    assert g["BSR-RC-03"] == {"raw": "—", "group": "BSR-RC-03", "rule": "WITNESS_ROW_OWN_GROUP"}
    assert g["BSR-AN-03"]["group"] == "church of england" and g["BSR-AN-03"]["rule"] == "PARENTHETICAL_STRIPPED"
    assert normalize_body("Universal Church; published by the Holy See's Dicastery for Communication") == "universal church"


# ---------------------------------------------------------------- Task 2
def _rub(model, floor, verdict=None, subj="Y", act="Y", hazards=None, code=None):
    v = verdict or ("REJECT" if floor == "WORD_ONLY" else ("ACCEPT_WITH_CAVEAT" if floor == "PARTIAL" or hazards else "ACCEPT"))
    return {"model": model, "status": "DONE", "phrase_verbatim": "Y", "subject_is_required": subj, "speech_act_is_assertion": act,
            "floor": floor, "hazard_flags": hazards or [], "verdict_model": v, "verdict": v,
            "reason_code_final": code or ("BELOW_FLOOR" if floor == "WORD_ONLY" else ("WRONG_SUBJECT" if subj == "N" else "OK"))}


def test_lower_floor_is_final_on_a_disagreement_never_the_adjudicators():
    assert lower_floor("FULL", "PARTIAL") == "PARTIAL" and lower_floor("WORD_ONLY", "PARTIAL") == "WORD_ONLY" and lower_floor(None, "FULL") == "FULL"
    # Q-403: sonnet WORD_ONLY (REJECT), opus PARTIAL (ACCEPT_WITH_CAVEAT) on the reject-all route — opus's floor no longer carries it
    v = {"_route": "PRIMARY_REJECTED_ALL", "sonnet": _rub("sonnet", "WORD_ONLY"), "opus": _rub("opus", "PARTIAL")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "REJECT" and fin["reason_code_final"] == "BELOW_FLOOR" and fin["floor_final"] == "WORD_ONLY"
    assert fin["floor_disagreement"] and fin["lower_floor_applied"] and not fin["overturned"] and fin["direction"] is None
    # a caveated accept where opus upgraded to FULL: the final floor is sonnet's PARTIAL and the verdict stays caveated
    v = {"_route": "CAVEATED_ACCEPT", "sonnet": _rub("sonnet", "PARTIAL"), "opus": _rub("opus", "FULL")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "ACCEPT_WITH_CAVEAT" and fin["floor_final"] == "PARTIAL" and fin["adjudicated_by"] == "sonnet" \
        and fin["second_rubric_role"] == "DISCLOSURE_FLOOR_ONLY"
    # sonnet FULL, opus PARTIAL on the retired route: the lower floor applies here too
    v = {"_route": "CAVEATED_ACCEPT", "sonnet": _rub("sonnet", "FULL"), "opus": _rub("opus", "PARTIAL")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "ACCEPT_WITH_CAVEAT" and fin["floor_final"] == "PARTIAL" and fin["lower_floor_applied"]


def test_opus_still_rescues_on_lines_one_to_three_but_not_by_a_higher_floor():
    # 2b: the primary refused for WRONG_SUBJECT at floor FULL; opus reads the subject as required at FULL — the rescue stands
    v = {"_route": "PRIMARY_REJECTED_ALL", "sonnet": _rub("sonnet", "FULL", verdict="REJECT", subj="N"), "opus": _rub("opus", "FULL")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "ACCEPT" and fin["overturned"] and fin["direction"] == "RESCUED" and fin["adjudicated_by"] == "opus"
    # the same rescue with the primary at PARTIAL: it stands, at PARTIAL
    v = {"_route": "PRIMARY_REJECTED_ALL", "sonnet": _rub("sonnet", "PARTIAL", verdict="REJECT", subj="N"), "opus": _rub("opus", "FULL")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "ACCEPT_WITH_CAVEAT" and fin["floor_final"] == "PARTIAL" and fin["direction"] == "RESCUED"
    # opus overrules an accept: still final
    v = {"_route": "SLICE_ROW", "sonnet": _rub("sonnet", "FULL"), "opus": _rub("opus", "FULL", verdict="REJECT", act="N", code="NOT_ASSERTION")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "REJECT" and fin["direction"] == "OVERRULED"
    # no second rubric: the primary alone
    v = {"_route": None, "sonnet": _rub("sonnet", "PARTIAL")}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "ACCEPT_WITH_CAVEAT" and fin["second_rubric"] is None and not fin["floor_disagreement"]


def test_verdict_from_rubric_reproduces_the_verifier_rule():
    assert verdict_from_rubric(_rub("s", "FULL"), "FULL") == ("ACCEPT", "OK")
    assert verdict_from_rubric(_rub("s", "FULL"), "PARTIAL") == ("ACCEPT_WITH_CAVEAT", "OK")
    assert verdict_from_rubric(_rub("s", "FULL"), "WORD_ONLY") == ("REJECT", "BELOW_FLOOR")
    assert verdict_from_rubric(_rub("s", "FULL", subj="N"), "FULL") == ("REJECT", "WRONG_SUBJECT")
    assert verdict_from_rubric({"status": "UNPARSEABLE"}, "FULL") == ("REJECT", "UNPARSEABLE")
    assert verdict_from_rubric(dict(_rub("s", "FULL"), phrase_verbatim_code="N"), "FULL") == ("REJECT", "NOT_VERBATIM")


class _Llm:
    """Replies by model (a list per model, popped in call order) or a flat list popped in call order."""
    def __init__(self, replies):
        self.replies = {m: list(v) for m, v in replies.items()} if isinstance(replies, dict) else list(replies)
        self.calls = []; self.pending = []; self._cache = {}; self.run_id = "t"

    def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
        self.calls.append((role, model, meta))
        q = self.replies[model] if isinstance(self.replies, dict) else self.replies
        return q.pop(0), {"call_id": f"c{len(self.calls)}"}


class _SliceReg:
    verifier_routing = "SONNET_WITH_OPUS_SLICE"
    fallback_ids = set()

    def __init__(self, rows):
        self.by_id = rows

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return True

    def is_fallback(self, rid):
        return False

    def is_witness(self, rid):
        return False

    def for_branch(self, branch, include_fallback=True, citable_only=True):
        return [dict(r, registry_id=k) for k, r in self.by_id.items()]

    def public(self, rid):
        r = self.by_id[rid]
        return {"standard_title": rid, "authority_tier": r["authority_tier"], "scope_caveat": "", "reception_scope": "JURISDICTIONAL",
                "witness_only": False, "speaks_for": r.get("speaks_for", rid)}

    def citation_refusal(self, rid):
        return None


def _cand(cid, rid="BSR-LU-01"):
    return {"candidate_id": cid, "pass": 1, "registry_id": rid, "locator": "L", "phrase": "maker of heaven and earth",
            "rationale": "r", "floor_claim": "PARTIAL", "chunk_text": "the Father almighty, maker of heaven and earth", "chunk_hash": "h",
            "division": "d", "fallback_tier": False, "witness": False, "effective_tier": "CONFESSIONAL", "locator_rank": 1}


def test_caveat_sample_is_disclosure_only_and_bounded_at_twenty_percent(tmp_path):
    rows = {"BSR-LU-01": {"branch": "Lutheran", "authority_tier": "CONFESSIONAL", "standard_title": "BoC", "speaks_for": "Lutheran churches"}}
    preds = {"F": {"family_id": "F", "predicate": "Creator", "definition": "d", "floor_note": "f", "subject_scope": "GOD", "family_code": "A", "lexical_floor": False, "mode": "m"}}
    sonnet_partial = json.dumps({"phrase_verbatim": "Y", "subject_is_required": "Y", "grammatical_subject": "God", "speech_act_is_assertion": "Y",
                                 "floor": "PARTIAL", "floor_reason": "narrower", "hazard_flags": [], "verdict": "ACCEPT_WITH_CAVEAT", "reason_code": "OK", "reason": "r"})
    opus_word_only = json.dumps({"phrase_verbatim": "Y", "subject_is_required": "Y", "grammatical_subject": "God", "speech_act_is_assertion": "Y",
                                 "floor": "WORD_ONLY", "floor_reason": "mention", "hazard_flags": [], "verdict": "REJECT", "reason_code": "BELOW_FLOOR", "reason": "r"})
    # ten one-candidate cells on one branch: every candidate is a caveated accept on its card, so every one is ELIGIBLE;
    # the running share must never exceed 20%, however the hash buckets fall
    # session 14 (R6-54): _verify_pass now takes VOTES_PER_CANDIDATE draws per candidate per model, so ten cells need
    # ten x 3 replies per model. The 2c sample's subject — the 20% bound and disclosure-only role — is unchanged.
    llm = _Llm({"sonnet": [sonnet_partial] * 30, "opus": [opus_word_only] * 30})
    r = CellRunner(llm, _SliceReg(rows), preds, {}, str(tmp_path), "sonnet", ["sonnet", "opus"], log=lambda m: None, run_coder=False)
    sampled = 0
    for i in range(10):
        qid = f"Q-{i:03d}"
        st = {"queue_id": qid, "branch": "Lutheran", "family_id": "F", "predicate": "Creator", "coding": {}, "phase": "verify-1",
              "passes": {"1": {"status": "DONE", "standards": ["BSR-LU-01"], "candidates": [_cand(f"{qid}-p1-BSR-LU-01-1")], "dropped": [], "unslotted": []}},
              "verifications": {}, "routing": "SONNET_WITH_OPUS_SLICE", "primary": "sonnet", "adjudicator": "opus", "slice_rows": []}
        cell = {"queue_id": qid, "branch": "Lutheran", "family_id": "F", "predicate": "Creator"}
        assert r._verify_pass(cell, st, "1") is False
        r.save(st)
        rec = st["caveat_sample"][f"{qid}-p1-BSR-LU-01-1"]
        v = st["verifications"][f"{qid}-p1-BSR-LU-01-1"]
        if rec["sampled"]:
            sampled += 1
            assert v["_route"] == ROUTE_CAVEAT_SAMPLE and v["final"]["second_rubric_role"] == "DISCLOSURE_FLOOR_ONLY"
            # 2a on the sample: opus's WORD_ONLY lowers the floor and the candidate is refused — the sample can lower, never raise
            assert v["final"]["verdict"] == "REJECT" and v["final"]["floor_final"] == "WORD_ONLY" and v["final"]["adjudicated_by"] == "sonnet"
        else:
            assert "opus" not in v and v["final"]["verdict"] == "ACCEPT_WITH_CAVEAT"
        eligible, taken = r.sample_quota("Lutheran")
        assert taken <= CAVEAT_SAMPLE_SHARE * eligible + 1e-9, (eligible, taken)
    assert sampled * VOTES_PER_CANDIDATE == sum(1 for role, m, meta in llm.calls if m == "opus")
    assert sampled <= 2                                   # at most 20% of 10
    assert all(0 <= sample_bucket(f"Q-{i:03d}-p1-BSR-LU-01-1") < 100 for i in range(10))


# ---------------------------------------------------------------- Task 3
def test_idiom_or_formula_caps_the_floor_at_word_only_unless_asserted_outside_the_formula():
    rows = {"BSR-LU-01": {"branch": "Lutheran", "authority_tier": "CONFESSIONAL", "standard_title": "BoC", "speaks_for": "Lutheran churches"}}
    preds = {"F": {"family_id": "F", "predicate": "Living", "definition": "d", "floor_note": "f", "subject_scope": "GOD", "family_code": "A", "lexical_floor": False, "mode": "m"}}
    oath = json.dumps({"phrase_verbatim": "Y", "subject_is_required": "Y", "grammatical_subject": "the Lord God", "speech_act_is_assertion": "Y",
                       "floor": "PARTIAL", "floor_reason": "oath formula", "hazard_flags": ["IDIOM_OR_FORMULA", "SLOGAN_COMPRESSION"],
                       "asserted_outside_formula": "N", "verdict": "ACCEPT_WITH_CAVEAT", "reason_code": "OK", "reason": "r"})
    oath_plus = json.dumps({"phrase_verbatim": "Y", "subject_is_required": "Y", "grammatical_subject": "God", "speech_act_is_assertion": "Y",
                            "floor": "FULL", "floor_reason": "the passage also says God is the living God", "hazard_flags": ["IDIOM_OR_FORMULA"],
                            "asserted_outside_formula": "Y", "verdict": "ACCEPT_WITH_CAVEAT", "reason_code": "OK", "reason": "r"})
    llm = _Llm([oath, oath_plus])
    r = CellRunner(llm, _SliceReg(rows), preds, {}, "unused-dir", "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)
    cell = {"queue_id": "Q-003", "branch": "Lutheran", "family_id": "F", "predicate": "Living"}
    a = r.verify(cell, _cand("Q-003-x"), "sonnet")
    assert a["floor"] == "WORD_ONLY" and a["floor_model"] == "PARTIAL" and a["floor_capped_by"] == "IDIOM_OR_FORMULA"
    assert a["verdict"] == "REJECT" and a["reason_code_final"] == "BELOW_FLOOR"
    b = r.verify(cell, _cand("Q-003-y"), "sonnet")
    assert b["floor"] == "FULL" and "floor_capped_by" not in b and b["verdict"] == "ACCEPT_WITH_CAVEAT"
    assert "IDIOM_OR_FORMULA" in __import__("sjn_recovery.prompts", fromlist=["HAZARD_TYPES"]).HAZARD_TYPES
