"""Session 8 (2026-09-16, second set): the author's rulings R6-13 to R6-16.

  R6-13  verifier gate6-v1.5: v1.4 minus one JOINT PREDICATION sentence, and JOINT PREDICATION / AGENCY scoped to Spirit
         families in the harness
  R6-14  the seven Spirit-family agency tags, ratified, read from spirit-family-agency-tags.json (H27 = ATTRIBUTE)
  R6-15  highest-tier precedence among matching registered texts

The scoping and agency tests read the real workbook's predicates: the scope is a property of the required_subject the
verifier is actually sent, and a stub would only test the stub."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery.registry import Registry, load_predicates  # noqa: E402
from sjn_recovery import prompts, rulings, store  # noqa: E402

SPIRIT_FAMILIES = {"RNR-H06", "RNR-H21", "RNR-H26", "RNR-H27", "RNR-H34", "RNR-H35", "RNR-H38"}


@pytest.fixture(scope="module")
def reg():
    try:
        r = Registry()
    except Exception as e:                                             # no workbook in this checkout
        pytest.skip(f"registry unavailable: {e}")
    return r


@pytest.fixture(scope="module")
def preds(reg):
    return load_predicates(reg.wb)


@pytest.fixture
def v15():
    before = prompts.PROMPT_VERSIONS["verifier"]
    prompts.set_verifier_version("gate6-v1.5")
    yield
    prompts.PROMPT_VERSIONS["verifier"] = before


def _eo_store(reg):
    if not store.load_chunks("BSR-EO-07") or not store.load_chunks("BSR-EO-09"):
        pytest.skip("chunk store (.cache/sjn-recovery/chunks) is not built in this checkout")


# ---------------------------------------------------------------- R6-13: the v1.5 text and its scope
def test_v15_spirit_variant_is_v14_minus_the_one_sentence_byte_for_byte():
    s14, s15 = prompts.VERIFIER_SYSTEM_V14, prompts.VERIFIER_SYSTEM_V15_SPIRIT
    sentence = "A doxology naming the three persons remains a fixed formula under line 4."
    assert sentence in s14 and sentence not in s15
    assert s15 == s14.replace(" " + sentence, "")
    assert len(s14) - len(s15) == len(" " + sentence)


def test_v15_base_variant_is_v13_plus_the_creed_lines_and_neither_spirit_line():
    base = prompts.VERIFIER_SYSTEM_V15_BASE
    assert "JOINT PREDICATION" not in base and "AGENCY." not in base
    assert "A CREED IS NOT A FIXED FORMULA IN THIS SENSE." in base
    assert "Do NOT raise IDIOM_OR_FORMULA for a creedal clause" in base
    assert prompts.CREEDAL_SILENCE_LINE in base
    assert "A NEIGHBOURING proposition is never PARTIAL" in base      # everything v1.3 said, it still says
    # base + the two Spirit lines is exactly the spirit variant
    assert prompts.VERIFIER_SYSTEM_V15_SPIRIT == base.replace(
        prompts.CREEDAL_SILENCE_LINE, "\n\n".join([prompts.CREEDAL_SILENCE_LINE, prompts.JOINT_PREDICATION_LINE_V15,
                                                   prompts.AGENCY_LINE]))


def test_versions_stay_linear():
    # session 9 (R6-18) appends gate6-v1.6; test_session9_rulings pins the full list
    assert list(prompts.VERIFIER_SYSTEMS)[:4] == ["gate6-v1.2", "gate6-v1.3", "gate6-v1.4", "gate6-v1.5"]


def test_a_son_family_prompt_carries_neither_spirit_line(preds, v15):
    s = prompts.verifier_system(preds["RNR-H05"])
    assert "JOINT PREDICATION" not in s and "AGENCY." not in s
    assert prompts.verifier_variant(preds["RNR-H05"]) == "gate6-v1.5/base"


def test_the_h35_prompt_carries_both(preds, v15):
    s = prompts.verifier_system(preds["RNR-H35"])
    assert "JOINT PREDICATION" in s and "AGENCY." in s
    assert prompts.verifier_variant(preds["RNR-H35"]) == "gate6-v1.5/spirit"


def test_the_h06_prompt_admitting_the_spirit_carries_both(preds, v15):
    s = prompts.verifier_system(preds["RNR-H06"])
    assert "JOINT PREDICATION" in s and "AGENCY." in s
    assert prompts.verifier_variant(preds["RNR-H06"]) == "gate6-v1.5/spirit"


def test_the_scope_is_exactly_the_seven_tagged_families(preds):
    assert {f for f, p in preds.items() if prompts.subject_includes_the_spirit(p)} == SPIRIT_FAMILIES


def test_no_family_means_the_base_variant_and_unscoped_versions_are_unchanged(preds):
    before = prompts.PROMPT_VERSIONS["verifier"]
    try:
        prompts.set_verifier_version("gate6-v1.5")
        assert prompts.verifier_system() is prompts.VERIFIER_SYSTEM_V15_BASE
        prompts.set_verifier_version("gate6-v1.3")
        assert prompts.verifier_system(preds["RNR-H35"]) is prompts.VERIFIER_SYSTEM_V13
        assert prompts.verifier_variant(preds["RNR-H35"]) == "gate6-v1.3"
    finally:
        prompts.PROMPT_VERSIONS["verifier"] = before


def test_the_variant_is_recorded_on_the_rubric_and_the_call(preds, v15, tmp_path):
    from sjn_recovery.agents import CellRunner

    class _LLM:
        def __init__(self):
            self.seen = []

        def complete(self, role, system, user, model=None, max_tokens=0, meta=None, attempt=0):
            self.seen.append((system, meta))
            return None, {"call_id": "x"}

    class _Reg:
        verifier_routing = "PRIMARY_ONLY"
        fallback_ids = set()

    llm = _LLM()
    runner = CellRunner(llm, _Reg(), preds, {}, str(tmp_path), "sonnet", ["sonnet"], log=lambda m: None, run_coder=False)
    cand = {"candidate_id": "c", "registry_id": "R", "locator": "L", "phrase": "p", "floor_claim": "FULL", "chunk_text": "p"}
    for fam, variant in (("RNR-H05", "gate6-v1.5/base"), ("RNR-H27", "gate6-v1.5/spirit")):
        r = runner.verify({"queue_id": "Q", "family_id": fam, "branch": "B"}, cand, "sonnet")
        assert r["prompt_variant"] == variant and llm.seen[-1][1]["verifier_variant"] == variant


# ---------------------------------------------------------------- R6-14: the ratified agency tags
def test_the_seven_tags_are_ratified_as_ruled():
    assert rulings.agency_tags() == {"RNR-H34": "ACTION", "RNR-H35": "ATTRIBUTE", "RNR-H06": "ATTRIBUTE",
                                     "RNR-H21": "ACTION", "RNR-H26": "ACTION", "RNR-H27": "ATTRIBUTE",
                                     "RNR-H38": "ATTRIBUTE"}
    d = json.load(open(rulings.AGENCY_TAGS_PATH, encoding="utf-8"))
    assert all(e["ratified"] is True and e["ratified_at"] == "2026-09-16" for e in d["families"].values())
    assert rulings.agency_blocks_eo() is False


def test_h27_is_sent_attribute(preds):
    assert preds["RNR-H27"]["agency_class"] == "ATTRIBUTE"
    cand = {"registry_id": "R", "locator": "L", "phrase": "p", "floor_claim": "FULL"}
    assert json.loads(prompts.verifier_user(preds["RNR-H27"], cand, {}))["agency_class"] == "ATTRIBUTE"


def test_an_unknown_spirit_family_is_sent_no_class(reg, tmp_path, monkeypatch):
    d = json.load(open(rulings.AGENCY_TAGS_PATH, encoding="utf-8"))
    del d["families"]["RNR-H34"]                                         # a Spirit family the file does not list
    p = tmp_path / "tags.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setattr(rulings, "AGENCY_TAGS_PATH", str(p))
    preds = load_predicates(reg.wb)
    assert prompts.subject_includes_the_spirit(preds["RNR-H34"])
    assert "agency_class" not in preds["RNR-H34"]
    cand = {"registry_id": "R", "locator": "L", "phrase": "p", "floor_claim": "FULL"}
    assert "agency_class" not in json.loads(prompts.verifier_user(preds["RNR-H34"], cand, {}))
    assert preds["RNR-H35"]["agency_class"] == "ATTRIBUTE"


def test_an_unratified_entry_or_a_disagreeing_tag_is_not_carried(tmp_path):
    d = json.load(open(rulings.AGENCY_TAGS_PATH, encoding="utf-8"))
    d["families"]["RNR-H21"]["ratified"] = False
    p = tmp_path / "tags.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    assert "RNR-H21" not in rulings.agency_tags(path=str(p))
    d["families"]["RNR-H27"]["agency_class"] = "ACTION"                 # the proposal, not the ruling
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SystemExit):
        rulings.agency_tags(path=str(p))


# ---------------------------------------------------------------- R6-15: highest-tier precedence
def test_a_phrase_in_eo09_and_eo07_resolves_conciliar(reg):
    _eo_store(reg)
    hit = reg.resolve_registered_phrase("Eastern Orthodox", "begotten, not made")
    assert hit["tier"] == "CONCILIAR" and hit["registry_id"] == "BSR-EO-07"
    assert reg.effective_tier("BSR-EO-01", phrase="begotten, not made") == "CONCILIAR"


def test_precedence_does_not_depend_on_the_order_or_length_of_the_matches(reg):
    _eo_store(reg)
    texts = reg.registered_creed_texts("Eastern Orthodox")
    try:
        reg._creed_index["Eastern Orthodox"] = sorted(texts, key=lambda t: t["registry_id"] != "BSR-EO-09")   # EO-09 first
        assert reg.resolve_registered_phrase("Eastern Orthodox", "begotten, not made")["tier"] == "CONCILIAR"
        # and a phrase only EO-09 carries still resolves to EO-09's own tier, whatever the order
        assert reg.resolve_registered_phrase("Eastern Orthodox", "light from light, true God from true God")["tier"] == "CONFESSIONAL"
    finally:
        reg._creed_index["Eastern Orthodox"] = texts


def test_a_phrase_only_in_eo09_resolves_confessional(reg):
    _eo_store(reg)
    for phrase in ("the Lord, the giver of life", "light from light, true God from true God"):
        hit = reg.resolve_registered_phrase("Eastern Orthodox", phrase)
        assert hit["registry_id"] == "BSR-EO-09" and hit["tier"] == "CONFESSIONAL", phrase
        assert reg.effective_tier("BSR-EO-01", phrase=phrase) == "CONFESSIONAL"


def test_rc06_and_rc08_are_unchanged(reg):
    if not store.load_chunks("BSR-RC-06"):
        pytest.skip("chunk store is not built")
    for rid in ("BSR-RC-06", "BSR-RC-08"):
        ch = next(c for c in store.load_chunks(rid) if "nicene" in (c["locator"] or "").casefold())
        assert reg.effective_tier(rid, ch, None) == "CONCILIAR"
    hit = reg.resolve_registered_phrase("Roman Catholic", "begotten, not made")
    assert hit and hit["tier"] == "CONCILIAR" and hit["registry_id"] in ("BSR-RC-06", "BSR-RC-08")
