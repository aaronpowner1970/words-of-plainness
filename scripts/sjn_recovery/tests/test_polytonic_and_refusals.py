"""BSR-EO-12 polytonic integrity and the R001 extensions (DIALOGUE_ONLY, the 1848 Encyclical, witness rows)."""
import os
import sys
import unicodedata

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from sjn_recovery import guards, store  # noqa: E402
from sjn_recovery.textutil import nfc, has_polytonic, normalize, strip_foreign_parentheticals  # noqa: E402
from sjn_pipeline.registry import (refusal_reason, citation_refusal, is_witness_row, is_dialogue_only,  # noqa: E402
                                   is_translation_witness)

ARTICLE_1 = "Πιστεύω εἰς ἕνα Θεόν, Πατέρα, Παντοκράτορα, ποιητὴν οὐρανοῦ καὶ γῆς, ὁρατῶν τε πάντων καὶ ἀοράτων."


def test_nfc_once_keeps_polytonic_and_phrase_check_passes():
    decomposed = unicodedata.normalize("NFD", ARTICLE_1)
    stored = nfc(decomposed)
    assert stored == unicodedata.normalize("NFC", ARTICLE_1)
    assert has_polytonic(stored)
    # a phrase cut from the stored text passes the verbatim check, and so does the same phrase typed in NFD
    ok, why = guards.check_phrase("ποιητὴν οὐρανοῦ καὶ γῆς", stored)
    assert ok, why
    ok, why = guards.check_phrase(unicodedata.normalize("NFD", "ποιητὴν οὐρανοῦ καὶ γῆς"), stored)
    assert ok, why
    assert normalize(stored) == normalize(decomposed)


def test_built_greek_creed_if_present():
    chunks = store.load_chunks("BSR-EO-12")
    if not chunks:
        pytest.skip("BSR-EO-12 corpus not built")
    assert len(chunks) == 12
    for c in chunks:
        assert c["language"] == "el"
        assert unicodedata.normalize("NFC", c["text"]) == c["text"], f"{c['locator']} is not NFC"
        assert has_polytonic(c["text"]), f"{c['locator']} lost its polytonic accents"
    ok, why = guards.check_phrase("ποιητὴν οὐρανοῦ καὶ γῆς", chunks[0]["text"])
    assert ok, why


def test_foreign_parentheticals_are_moved_out():
    s = ("to be acknowledged in two natures, inconfusedly, unchangeably, indivisibly, inseparably; "
         "(ἐν δύο φύσεσιν ἀσυγχύτως, ἀτρέπτως, ἀδιαιρέτως, ἀχωρίστως – in duabus naturis inconfuse, immutabiliter, indivise, inseparabiliter). "
         "Not parted or divided into two persons, but one and the same Son, and only begotten God (μονογενῆ Θεόν), the Word.")
    eng, removed = strip_foreign_parentheticals(s)
    assert len(removed) == 2
    assert "φύσεσιν" not in eng and "duabus" not in eng and "μονογενῆ" not in eng
    assert "inconfusedly, unchangeably, indivisibly, inseparably" in eng


def test_1848_encyclical_is_refused_by_name():
    assert refusal_reason("Encyclical of the Eastern Patriarchs, 1848", "§5")
    assert refusal_reason("Reply of the Orthodox Patriarchs to Pope Pius IX (1848)")
    assert refusal_reason(None, "https://example.org/1848-encyclical-eastern-patriarchs.html")
    assert "ENCYCLICAL_1848_NOT_CITABLE" in refusal_reason("The 1848 Encyclical of the Eastern Patriarchs")
    assert refusal_reason("Confession of Dositheus", "Decree 1") is None
    assert refusal_reason("Nicene Creed") is None


def test_dialogue_only_row_is_refused_and_witness_rows_are_flagged():
    dialogue = {"registry_id": "BSR-XX-99", "reception_scope": "DIALOGUE_ONLY", "authority_tier": "OFFICIAL_EXPOSITION",
                "standard_title": "Agreed statement", "canonical_url": "https://example.org/x"}
    assert is_dialogue_only(dialogue)
    assert "DIALOGUE_ONLY_NEVER_CITED" in citation_refusal(dialogue)
    rc03 = {"registry_id": "BSR-RC-03", "reception_scope": "TRANSLATION_WITNESS", "authority_tier": "CONCILIAR (translation)"}
    eo11 = {"registry_id": "BSR-EO-11", "reception_scope": "UNIVERSAL", "authority_tier": "CONCILIAR (witness; translation)"}
    eo06 = {"registry_id": "BSR-EO-06", "reception_scope": "UNIVERSAL", "authority_tier": "CONCILIAR"}
    assert is_translation_witness(rc03) and is_witness_row(rc03)
    assert is_witness_row(eo11) and not is_translation_witness(eo11)
    assert not is_witness_row(eo06)
    assert citation_refusal(rc03) is None


def test_registry_excludes_dialogue_only_from_locator_supply():
    from sjn_recovery.registry import Registry
    try:
        reg = Registry()
    except Exception as e:      # no workbook in this checkout
        pytest.skip(str(e))
    fake = {"registry_id": "BSR-EO-99", "branch": "Eastern Orthodox", "status": "AUTHOR_RATIFIED", "standard_title": "Dialogue text",
            "authority_tier": "OFFICIAL_EXPOSITION", "reception_scope": "DIALOGUE_ONLY", "speaks_for": "-", "scope_caveat": "-",
            "publisher_domain": "example.org", "canonical_url": "https://example.org/d", "fetch_mode": "HTML"}
    reg.rows.append(fake); reg.by_id[fake["registry_id"]] = fake
    supplied = {r["registry_id"] for r in reg.for_branch("Eastern Orthodox")}
    assert "BSR-EO-99" not in supplied
    assert "BSR-EO-99" in {r["registry_id"] for r in reg.for_branch("Eastern Orthodox", citable_only=False)}
    assert "DIALOGUE_ONLY_NEVER_CITED" in reg.citation_refusal("BSR-EO-99")
    assert reg.gate_metric == "SAME_STANDARD"
    assert reg.tier_rank_list[0] == "CONCILIAR"
    assert reg.opus_slice_rows() >= {"BSR-EO-04", "BSR-EO-05", "BSR-EO-09", "BSR-AN-05"}
    assert reg.is_witness("BSR-RC-03") and reg.is_witness("BSR-EO-11") and not reg.is_witness("BSR-EO-06")
