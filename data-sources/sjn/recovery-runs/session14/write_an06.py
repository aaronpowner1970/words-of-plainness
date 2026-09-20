"""Session 14, phase 4: the operative blocks the AN-04 / AN-06 corpus repair needs — R6-48's new BSR-AN-06 row, its
adoption, R6-50's named same-text pair and R6-51's AN-04 extent. Idempotent.

Codex F.10: "Repair: split at p. 862/863; AN-04 = pp. 844-862 (R6-51); AN-06 = pp. 863-865."

The one field no ruling names is BSR-AN-06's authority_tier, so it is set HERE, on the ruling, where the author can
change one value and re-run. The value below is the fail-closed one. Three readings, ranked, with each one's weakness:

  1. OFFICIAL_EXPOSITION (witness; ...)   CHOSEN. B1(c) says a creed- or definition-genre text resolves at its genre's
     tier only where the church CONFESSES it, and "absent the marks, the text stays a witness (fail closed)". The book
     is adopted (B2), so the row is not unadopted; OFFICIAL_EXPOSITION is the tier B1/B2 give an adopted text that does
     not reach its genre's tier, and it is what R6-42 gave the adopted-but-non-creedal ABCUSA statement.
     WEAKNESS: it ranks the Chalcedonian Definition below a catechism (AN-02, AN-04 at CATECHETICAL) for this church,
     which reads oddly beside the text's standing everywhere else in the corpus.
  2. CONCILIAR (witness; ...) / CONFESSIONAL (witness; ...): the genre's own tier, with the witness flag doing all the
     work. WEAKNESS: it is exactly the tier B1(c) fails closed AGAINST; the witness flag stops the row seating ALONE,
     but within a tier it would outrank every other Anglican row on any cell where a non-witness candidate exists.
  3. CATECHETICAL, following BSR-AN-04, the row it was split out of. WEAKNESS: neither document is a catechism; the
     tier would be a bookkeeping artefact of the split, and B1 says tier follows what a document IS.

Whichever reading the author takes, the witness flag and R6-50's same-text pair govern the seating outcome on every
cell where AN-03 is also a candidate, so reading 2 changes nothing there. The report measures the difference.

  python data-sources/sjn/recovery-runs/session14/write_an06.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")

# "witness" in the tier is what registry.is_witness_row reads (BSR-EO-11's "CONCILIAR (witness; translation)"), so the
# witness treatment R6-47 ruled is carried by the row's own tier and cannot be lost by a later edit that misses a flag.
AN06_TIER = "OFFICIAL_EXPOSITION (witness; adopted historical document, not confessed)"


def main():
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    R = d["rulings"]

    # ---------------------------------------------------------------- R6-48: the row
    r = R["R6-48_an06_historical_documents_row"]
    r["add_row"] = True
    r["new_row"] = {
        "registry_id": "BSR-AN-06",
        "branch": "Anglican",
        "standard_title": "The Episcopal Church BCP 1979, \"Historical Documents of the Church\" (the Chalcedonian "
                          "Definition; the Quicunque Vult)",
        "authority_tier": AN06_TIER,
        "authority_tier_note": ("R6-47 / Codex B1(c): adopted within the Book of Common Prayer (1979-A133) but not "
                                "confessed by The Episcopal Church — no liturgical appointment, and the BCP's own "
                                "Catechism (p. 852) calls the Athanasian Creed 'an ancient document'. Fail closed: a "
                                "witness, below its genre's tier. Positive evidence of confession reopens it. The tier "
                                "VALUE is Code's reading of B1(c), not an author ruling; see session14/write_an06.py "
                                "for the three ranked readings"),
        "speaks_for": "The Episcopal Church (certified Standard Book; printed as a historical document, not confessed)",
        "reception_scope": "JURISDICTIONAL",
        "publisher_domain": "episcopalchurch.org",
        "canonical_url": "https://www.episcopalchurch.org/wp-content/uploads/2023/06/book_of_common_prayer.pdf",
        "fetch_mode": "PDF",
        "scope_caveat": ("The Episcopal Church adopted the Book of Common Prayer 1979, which prints the Chalcedonian "
                         "Definition and the Quicunque Vult among its Historical Documents of the Church. The Church "
                         "neither appoints them in its liturgy nor names them in a confessional subscription, and its "
                         "own Catechism calls the Athanasian Creed an ancient document. They are cited here as texts "
                         "the Church adopted within its Prayer Book and preserves as historical documents, never as "
                         "creeds the Church confesses."),
        "reception_note": "Historical Documents of the Church, BCP 1979 pp. 863-865",
        "draft_recommendation": "INCLUDE AS WITNESS (cite the PDF; never as a confessed creed of this Church)",
    }
    r["adoption"] = {
        "adoption_status": "ADOPTED",
        "adoption_body_scope": "ONE_CHURCH",
        "adopting_body": "General Convention of The Episcopal Church",
        "adoption_act": ("General Convention 1979 (Denver), Resolution 1979-A133, second reading: the Book of Common "
                         "Prayer adopted and declared the Book of Common Prayer of this Church under Constitution "
                         "Art. X (Journal 1979, p. C-8 per the Archives; the 1985 note's C-9 is UNRECONCILED, R6-52). "
                         "The Historical Documents are covered as integral texts of the adopted book (B2(b)). "
                         "Adoption is not confession (R6-47 / B1(c))"),
        "adoption_verified": ("Carried from BSR-AN-04's R6-40 record, the same adopting act for the same book: "
                              "episcopalarchives.org Acts of Convention 1979-A133 (WebFetch + Claude Browser) and "
                              "1979-A121 (WebFetch); the stored PDF carries the Standard Book certificate (Jan 2007). "
                              "Both publishers are arms of TEC: independence is by instrument, not by publisher. NOT "
                              "confessed: no liturgical appointment found, and BCP p. 852 calls the Athanasian Creed "
                              "'an ancient document' (R6-47). Article VIII of the 1801 Articles of Religion "
                              "corroborates only. The TEC glossary and Brief Dictionary are context only (R6-53)"),
        "disclosure_wording": ("The Episcopal Church adopted the Book of Common Prayer that prints this text among its "
                               "Historical Documents. It is not appointed in the Church's liturgy and not named in a "
                               "confessional subscription: it is shown as a witness, never as a creed this Church "
                               "confesses."),
    }
    r["chunking_guards"] = {
        "extent": "BCP pp. 863-865 only",
        "title_page": "BCP p. 863, stored with its own locator as the title page of the section",
        "documents": {"Chalcedonian Definition": "BCP p. 864",
                      "Quicunque Vult": "BCP pp. 864-865, JOINED — the creed runs across the page break and must not be "
                                        "stored cut at 'one Almighty.' (the session 12/13 defect)"},
        "never_fetched": ["the Preface, The First Book of Common Prayer (1549), BCP p. 866 on",
                          "the Articles of Religion (1801), BCP p. 867 on (R6-49)",
                          "the Chicago-Lambeth Quadrilateral"],
        "last_sentence": "This is the Catholic Faith, which except a man believe faithfully, he cannot be saved.",
    }
    r["registered_sections"] = "none (R6-47: witness sections)"

    # ---------------------------------------------------------------- R6-50: the named same-text pair
    R["R6-50_an06_an03_same_text_pair"]["same_text_rows"]["BSR-AN-06"]["same_text_as"] = "BSR-AN-03"

    # ---------------------------------------------------------------- R6-51: AN-04's extent
    R["R6-51_an04_extent_and_p844_rubric"]["chunking_guards"] = {
        "extent": "BCP pp. 844-862 only; the Outline stops at the 'Historical Documents of the Church' title page (p. 863)",
        "p844_rubric": {"locator": "Outline of the Faith (BCP p. 844) — Concerning the Catechism (rubric)",
                        "division": "rubric (integral text)",
                        "registered": False,
                        "why": "integral text of the adopted book (B2(b)); it is a rubric about the catechism, not the "
                               "catechism, and it is not a creed or definition, so it is not a registered section"},
        "moved_out": "the Historical Documents chunks (BCP pp. 863 on) move to BSR-AN-06 under R6-48",
    }

    out = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if out != raw:
        with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        print("written")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
