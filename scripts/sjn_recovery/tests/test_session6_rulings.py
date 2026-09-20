"""Session 6 (2026-09-13): the author's four rulings — required_subject (R6-1), the hedged-PARTIAL floor rule (R6-2),
BSR-EO-03 retired (R6-3), one text one slot (R6-4)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.allocation import allocate, same_text_key  # noqa: E402
from sjn_recovery import rulings  # noqa: E402
from sjn_recovery.registry import load_predicates  # noqa: E402
from sjn_recovery.agents import CellRunner, verdict_from_rubric  # noqa: E402
from sjn_recovery import prompts  # noqa: E402


def _c(cid, rid, phrase, tier="CONFESSIONAL", floor="FULL"):
    return {"candidate_id": cid, "registry_id": rid, "phrase": phrase, "effective_tier": tier, "authority_tier": tier,
            "floor_claim": floor, "locator": "L", "fallback_tier": False, "witness": False}


AUGSBURG = "that there is one Divine Essence which is called and which is God"


# ---------------------------------------------------------------- R6-4 one text, one slot
def test_same_text_key_folds_case_whitespace_and_punctuation_only():
    assert same_text_key("Who of God is made unto us  wisdom,") == same_text_key("who of God is made unto us wisdom")
    assert same_text_key("“begotten, not made”") == same_text_key("begotten not made")
    assert same_text_key("begotten, not made") != same_text_key("begotten and not made")        # a different word is a different text
    assert same_text_key("beyond comprehension") != same_text_key("incomprehensible")


def test_identical_sentence_on_two_hosts_takes_one_slot_and_frees_the_other():
    """Q-179 / Q-227 / Q-235: LU-01 and LU-02 carry the same Augsburg sentence in two speaks_for groups."""
    groups = {"BSR-LU-01": "book of concord", "BSR-LU-02": "lcms"}
    cands = [_c("lu01-1", "BSR-LU-01", AUGSBURG), _c("lu01-2", "BSR-LU-01", "eternal, without body, without parts"),
             _c("lu02-1", "BSR-LU-02", AUGSBURG.upper() + ".")]
    a = allocate(cands, groups=groups, same_text_rows={})
    assert a["kept"] == ["lu01-1", "lu01-2"], a                # LCMS's identical sentence took no slot; BoC's second passage has it
    assert a["parallel_witnesses"] == {"lu01-1": [{"candidate_id": "lu02-1", "registry_id": "BSR-LU-02", "rule": "SAME_TEXT"}]}
    assert a["dropped"]["lu02-1"].startswith("SAME_TEXT parallel witness of lu01-1")


def test_one_row_duplicating_itself_is_caught_textually():
    """Q-243: BSR-LU-01 alone carries the same phrase twice (a GUARANTEED and an EXTRA slot) — a group-keyed guard misses it."""
    p = "who of God is made unto us wisdom and righteousness and sanctification and redemption"
    cands = [_c("g", "BSR-LU-01", p), _c("x", "BSR-LU-01", p), _c("y", "BSR-LU-03", "the wisdom of God")]
    a = allocate(cands, groups={}, same_text_rows={})
    assert a["kept"] == ["g", "y"] and [w["candidate_id"] for w in a["parallel_witnesses"]["g"]] == ["x"]


def test_parallel_witness_of_a_seated_phrase_is_recorded_even_after_the_cap_fills():
    cands = [_c("a", "R1", "one"), _c("b", "R2", "two"), _c("c", "R3", "three"), _c("d", "R4", "One.")]
    a = allocate(cands, groups={}, same_text_rows={})
    assert a["kept"] == ["a", "b", "c"] and a["parallel_witnesses"]["a"][0]["candidate_id"] == "d"


def test_declared_same_text_row_yields_the_slot_whatever_the_wording_and_order():
    """EO-07 (ACROD) and EO-14 (Canada): one rite, different wording; EO-14 sorts first here on its FULL floor claim."""
    cands = [_c("eo14", "BSR-EO-14", "beyond comprehension", floor="FULL"), _c("eo07", "BSR-EO-07", "inconceivable", floor="PARTIAL"),
             _c("eo08", "BSR-EO-08", "unseen")]
    declared = {"BSR-EO-14": "BSR-EO-07"}
    a = allocate(cands, groups={}, same_text_rows=declared)
    assert "eo14" not in a["kept"] and set(a["kept"]) == {"eo07", "eo08"}
    assert a["parallel_witnesses"]["eo07"][0] == {"candidate_id": "eo14", "registry_id": "BSR-EO-14", "rule": "SAME_TEXT_ROW", "same_text_as": "BSR-EO-07"}
    b = allocate(cands, groups={}, same_text_rows={})               # undeclared, the textual guard alone does not see them
    assert set(b["kept"]) == {"eo07", "eo08", "eo14"}


def test_declared_alternate_competes_normally_when_the_declared_row_has_nothing():
    cands = [_c("eo14", "BSR-EO-14", "beyond comprehension"), _c("eo08", "BSR-EO-08", "unseen")]
    a = allocate(cands, groups={}, same_text_rows={"BSR-EO-14": "BSR-EO-07"})
    assert set(a["kept"]) == {"eo14", "eo08"} and not a["parallel_witnesses"]


def test_rulings_file_declares_the_eo_pair_and_the_refusals():
    r = rulings.load()
    # session 14 (R6-50): a declared same-text pair lives on the ruling that declared it, so BSR-AN-06 -> BSR-AN-03
    # (the Quicunque Vult in two printings) joins the session-6 EO pair
    assert rulings.same_text_rows(r) == {"BSR-EO-14": "BSR-EO-07", "BSR-AN-06": "BSR-AN-03"}
    assert set(rulings.refused_candidates(r)) == {"Q-382-p1-BSR-BA-02-1", "Q-382-p1-BSR-BA-02-2", "Q-390-p1-BSR-BA-02-1",
                                                   "Q-390-p1-BSR-BA-02-2", "Q-454-p1-BSR-BA-02-1"}
    assert set(rulings.retirements(r)) == {"BSR-EO-03"} and rulings.retirements(r)["BSR-EO-03"]["reason_code"] == "HOST_RETIRED"


# ---------------------------------------------------------------- R6-1 required_subject
class _WB:
    def __init__(self, rows):
        self.rows = rows

    def table(self, sheet, key):
        return None, self.rows, None


def _pred_row(pid, name, definition, mode="Kataphatic", **extra):
    return dict({"Predicate ID": pid, "Normalized predicate family": name, "Historical source-report definition": definition,
                 "Original mode": mode, "__row": 1}, **extra)


def test_five_families_admit_the_son_or_the_spirit_as_divine_and_the_rest_are_unchanged():
    rows = [_pred_row("RNR-H06", "Lord", "Affirms authority and sovereignty."), _pred_row("RNR-H21", "Life-giving", "Affirms communication of life."),
            _pred_row("RNR-H26", "Judge", "Affirms divine judgment."), _pred_row("RNR-H27", "Savior", "Affirms redemptive action."),
            _pred_row("RNR-H38", "Not made", "Denies creaturehood.", mode="Negative delimiter"),
            _pred_row("RNR-H07", "Almighty / omnipotent", "Affirms supreme power."),
            _pred_row("RNR-H35", "Eternal power and might", "Affirms the Holy Spirit's divine power.")]
    p = load_predicates(_WB(rows))
    for pid in ("RNR-H06", "RNR-H21", "RNR-H26", "RNR-H27", "RNR-H38"):
        assert p[pid]["subject_scope"].startswith("GOD (the one God: the Father, or the Son or the Holy Spirit"), pid
        assert "as divine" in p[pid]["subject_scope"] and "not Christ's human nature" in p[pid]["subject_scope"]
        assert p[pid]["subject_scope_source"].startswith("AUTHOR_RULING_R6-1")
    assert "begotten, not made" in p["RNR-H38"]["subject_scope"] and "the Lord, the giver of life" in p["RNR-H21"]["subject_scope"]
    assert p["RNR-H07"]["subject_scope"].startswith("GOD (the one God, or the Father;") and p["RNR-H07"]["subject_scope_source"].startswith("HARNESS")
    assert p["RNR-H35"]["subject_scope"] == "THE HOLY SPIRIT"


def test_a_workbook_required_subject_column_must_agree_with_the_ruling():
    ruled = rulings.required_subjects()["RNR-H26"]
    assert load_predicates(_WB([_pred_row("RNR-H26", "Judge", "d", **{"Required subject": ruled})]))["RNR-H26"]["subject_scope_source"] == "WORKBOOK"
    try:
        load_predicates(_WB([_pred_row("RNR-H26", "Judge", "d", **{"Required subject": "GOD (the Father only)"})]))
    except SystemExit as e:
        assert "disagrees with author ruling R6-1" in str(e)
    else:
        raise AssertionError("a disagreeing workbook column must fail loudly")


# ---------------------------------------------------------------- R6-2 hedged PARTIAL, verifier gate6-v1.3
class _LLM:
    def __init__(self, replies):
        self.replies = list(replies); self.calls = []; self.pending = []; self._cache = {}; self.run_id = "t"

    def complete(self, role, system, user, model=None, max_tokens=1200, meta=None, attempt=0):
        self.calls.append((role, attempt, max_tokens, system))
        return self.replies.pop(0), {"call_id": f"c{len(self.calls)}"}


class _R:
    verifier_routing = "PRIMARY_ONLY"
    fallback_ids = set()

    def opus_slice_rows(self):
        return set()

    def routing_is_slice(self):
        return False


PRED = {"RNR-H48": {"family_id": "RNR-H48", "predicate": "Ineffable", "definition": "Denies exhaustive linguistic expression.", "floor_note": "",
                    "subject_scope": "GOD", "family_code": "Q", "lexical_floor": False, "mode": "Apophatic proper"}}
CAND = {"candidate_id": "x", "registry_id": "BSR-BA-02", "locator": "ch 2", "phrase": "whose essence cannot be comprehended by any but Himself",
        "chunk_text": "God, whose essence cannot be comprehended by any but Himself.", "floor_claim": "PARTIAL"}
CELL = {"queue_id": "Q-382", "family_id": "RNR-H48", "branch": "Baptist"}


def _reply(**kw):
    import json
    base = {"phrase_verbatim": "Y", "subject_is_required": "Y", "grammatical_subject": "God", "speech_act_is_assertion": "Y", "speech_act_note": "",
            "floor": "PARTIAL", "floor_reason": "r", "partial_asserts_predicate": "Y", "hazard_flags": [], "asserted_outside_formula": "NA",
            "verdict": "ACCEPT_WITH_CAVEAT", "reason_code": "OK", "reason": "r"}
    base.update(kw)
    return json.dumps(base)


def _runner(replies, tmp_path):
    return CellRunner(_LLM(replies), _R(), PRED, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)


def test_v13_is_the_verifier_in_force_and_states_the_rule():
    assert prompts.prompt_version("verifier") == "gate6-v1.3" and prompts.verifier_system() is prompts.VERIFIER_SYSTEM_V13
    s = prompts.VERIFIER_SYSTEM_V13
    assert "A NEIGHBOURING proposition is never PARTIAL" in s and '"partial_asserts_predicate": "Y|N|NA"' in s
    assert "narrower or adjacent" not in prompts.LOCATOR_SYSTEM and "is not PARTIAL and is not a candidate" in prompts.LOCATOR_SYSTEM
    for name in ("Ineffable", "Inscrutable", "incomprehensible"):          # no family is named in the rule (the audit sample is not steered)
        assert name not in s.split("4. floor")[1].split("5. hazard_flags")[0]


def test_partial_marked_neighbouring_is_capped_at_word_only_and_rejected(tmp_path):
    r = _runner([_reply(partial_asserts_predicate="N")], tmp_path)
    rub = r.verify(CELL, CAND, "sonnet")
    assert rub["floor_model"] == "PARTIAL" and rub["floor"] == "WORD_ONLY" and rub["floor_capped_by"] == "NEIGHBOURING_PROPOSITION"
    assert rub["verdict"] == "REJECT" and rub["reason_code_final"] == "BELOW_FLOOR"
    r2 = _runner([_reply(partial_asserts_predicate="Y")], tmp_path)
    assert r2.verify(CELL, CAND, "sonnet")["verdict"] == "ACCEPT_WITH_CAVEAT"


def test_a_truncated_reply_missing_its_floor_is_retried_never_accepted(tmp_path):
    cut = _reply()[: _reply().index('"floor"')].rstrip(", ") + "}"         # salvageable JSON with no floor line
    r = _runner([cut, _reply(floor="FULL", partial_asserts_predicate="NA", verdict="ACCEPT")], tmp_path)
    rub = r.verify(CELL, CAND, "sonnet")
    assert [c[1] for c in r.llm.calls] == [0, 1] and rub["floor"] == "FULL" and rub["verdict"] == "ACCEPT"
    r2 = _runner([cut, cut], tmp_path)
    rub2 = r2.verify(CELL, CAND, "sonnet")
    assert rub2["status"] == "UNPARSEABLE" and rub2["verdict"] == "REJECT"
    assert verdict_from_rubric({"status": "DONE", "phrase_verbatim": "Y", "subject_is_required": "Y", "speech_act_is_assertion": "Y",
                                "verdict_model": "ACCEPT"}, None) == ("REJECT", "UNPARSEABLE")


def test_a_floor_ruling_lowers_the_final_floor_on_every_rebuild_and_is_not_an_overturn():
    rub = {"status": "DONE", "phrase_verbatim": "Y", "subject_is_required": "Y", "speech_act_is_assertion": "Y", "floor": "PARTIAL",
           "verdict_model": "ACCEPT_WITH_CAVEAT", "verdict": "ACCEPT_WITH_CAVEAT", "hazard_flags": []}
    v = {"sonnet": dict(rub), "opus": dict(rub, model="opus"), "_route": "CAVEATED_ACCEPT_SAMPLE",
         "floor_rulings": [{"by": rulings.AUTHOR_RULING_FLOOR_CAP, "floor_cap": "WORD_ONLY"}]}
    fin = CellRunner.finalize(v, "sonnet", "opus")
    assert fin["verdict"] == "REJECT" and fin["floor_final"] == "WORD_ONLY" and fin["floor_before_rulings"] == "PARTIAL"
    assert fin["floor_capped_by_ruling"] is True and fin["floor_rulings_applied"] == [rulings.AUTHOR_RULING_FLOOR_CAP] and fin["overturned"] is False


def test_the_packet_entry_carries_floor_claim_so_builder_and_runner_allocate_alike():
    """Anglican Q-285 at session 6: without floor_claim the builder ordered on registry row alone (8 of 247 cards disagreed)."""
    import inspect
    from sjn_recovery import packets
    assert '"floor_claim": cand["floor_claim"]' in inspect.getsource(packets.build_branch_packet)
    full = _c("full", "R-B", "one text", floor="FULL")
    part = _c("part", "R-A", "another text", floor="PARTIAL")
    groups = {"R-A": "same body", "R-B": "same body"}
    assert allocate([part, full], groups=groups, cap=1, same_text_rows={})["kept"] == ["full"]
    stripped = [{k: v for k, v in x.items() if k != "floor_claim"} for x in (part, full)]
    assert allocate(stripped, groups=groups, cap=1, same_text_rows={})["kept"] == ["part"]      # the defect: row order decided it
