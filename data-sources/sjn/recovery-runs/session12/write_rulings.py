"""Session 12 (2026-09-17), phase 1: write the author's rulings R6-36 completion, R6-38 completion, R6-41 and R6-42 into
author-rulings-pending-workbook.json. Idempotent: running it twice leaves the file as after the first run.

  python data-sources/sjn/recovery-runs/session12/write_rulings.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")

SOURCE = ("Code session 12 prompt, 'SJN GATE 6 -- CORPUS REPAIR, SEATING RULE, NEW BAPTIST ROW (rulings R6-36 completion, R6-38 "
          "completion, R6-41, R6-42; 17 Sep 2026)', ratified 2026-09-17 in Chat; Comparison Principles Codex v0.5 (B2(a)-(e), B3(a), "
          "Part E, Part F items 8-10)")

AN05_APPEND = ("Competence checked 17 Sep 2026 (Cowork, Claude Browser pdf.js text layer): ACNA Constitution and Canons, June 2017 "
               "edition (effective 27 Sep 2017; congregation-hosted copy at livingwordrec.ca, dated by title page, PDF metadata and "
               "signature field; catechism and Art. X wording corroborated by the 2014 diocesan and 2026 ACNA editions), read in full "
               "with enumerated term search: no provision assigns catechism or text approval to any body; Art. V gives the Provincial "
               "Council canon-making power over Faith and Order and Common Worship, never exercised for texts. A special Provincial "
               "Assembly between June 2017 and June 2019 was not specifically searched.")

BA04_SCOPE_CAVEAT = ("American Baptist Churches USA holds no binding creed. This statement, 'We Are American Baptists' (revised 1998), is "
                     "one its cooperating churches affirm as descriptive of American Baptist faith and practice. It is cited here as a "
                     "shared description of belief, not as a confession binding on any church or believer.")
BA04_DISCLOSURE = ("American Baptist Churches USA holds no binding creed. Its cooperating churches affirm this statement as descriptive "
                   "of American Baptist faith and practice.")


def main():
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    R = d["rulings"]
    rows = R["R6-6_adoption_field"]["rows"]

    # ---- R6-38 completion: the author accepts session 11's LU-01 values
    cbv = rows["BSR-LU-01"]["amended"]["completed_by_verification"]
    cbv["author_accepted"] = {"date": "2026-09-17", "ruling": "R6-38 completion",
                              "accepted": "ONE_CHURCH; The Lutheran Church-Missouri Synod; LCMS Constitution Art. II",
                              "source": SOURCE}
    rows["BSR-LU-01"]["amended"]["status"] = "RATIFIED (amended; completed by verification, author-accepted 2026-09-17)"
    R["R6-38_adoption_scope_reach"]["completion"] = {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": "The author ACCEPTS session 11's LU-01 values: ONE_CHURCH; The Lutheran Church-Missouri Synod; LCMS Constitution Art. II",
        "as_implemented": "R6-6_adoption_field.rows BSR-LU-01.amended.completed_by_verification.author_accepted (values unchanged)",
        "test": "test_session12.test_lu01_completion_is_author_accepted_and_values_unchanged"}

    # ---- R6-36 completion: AN-05 stays ADOPTED, ONE_CHURCH; no card-disclosure change
    av = rows["BSR-AN-05"]["adoption_verified"]
    if AN05_APPEND not in av:
        rows["BSR-AN-05"]["adoption_verified"] = av.rstrip() + " " + AN05_APPEND
    R["R6-36_an05_adoption"]["completion"] = {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": "AN-05 stays ADOPTED, ONE_CHURCH; no card-disclosure change. The QA-track condition (a 2017-18 canon assigning the act "
                "elsewhere) is not triggered: the June 2017 Constitution and Canons, in force Jan 2018, read in full, assign catechism or "
                "text approval to no body. The unexercised Council power and the unsearched special-Assembly question are recorded in "
                "adoption_verified, not on the card",
        "qa_track_discharged": True,
        "as_implemented": "R6-6_adoption_field.rows BSR-AN-05.adoption_verified (appended); adoption_status / scope / body / disclosure unchanged",
        "test": "test_session12.test_an05_completion_appended_and_disclosure_unchanged"}

    # ---- R6-41: B3(a), the original holds the seat
    R["R6-41_original_holds_the_seat"] = {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": ("B3(a), the original holds the seat: when phrase-level resolution (R6-5/R6-10) raises a candidate because its phrase is "
                 "verbatim in a registered text that is itself a candidate for the same cell, the registered text takes the seat and the "
                 "lead, and the quoting or reprinting candidate is recorded as a parallel witness. Where the registered text is not a "
                 "candidate for that cell, the quoting candidate keeps its seat at the raised tier. This extends the same-text guard."),
        "codex": "B3(a) (Comparison Principles Codex v0.4)",
        "precedents": {"Q-195": "session 11's outcome is the correct pattern",
                       "Q-205": "reversed by the rule (AN-02's quotation of the Athanasian Creed displaced AN-03's creed text)",
                       "Q-317": "the lead is reversed by the rule (AN-04's reprint over AN-03)",
                       "Q-297": "the lead is re-decided once the original is identified"},
        "as_implemented": "scripts/sjn_recovery/allocation.py allocate (step 5a, rule ORIGINAL_HOLDS_SEAT); packets.py passes each "
                          "candidate's registered-text hits (Registry.registered_phrase_hits)",
        "test": "test_session12 (seating rule tests)",
        "supersede_with": "none (an allocation rule, not a workbook value)"}

    # ---- R6-42: a new Baptist registry row, "We Are American Baptists"
    R["R6-42_ba04_identity_statement"] = {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": ("A new Baptist registry row for 'We Are American Baptists' (the ABCUSA Identity Statement): OFFICIAL_EXPOSITION (interim, "
                 "pending Codex F.8); ADOPTED, ONE_CHURCH, by the Board of General Ministries through Standing Rules Addendum #1 and Rule "
                 "5.1.1 (a governing-rules incorporation is a church body's act). 'The covenanting partners' is a class, not a named body. "
                 "Short card disclosure; full text in scope_caveat. Verified under its own cost cap"),
        "codex": "B1, B2(a), B2(e); F.8 interim",
        "new_row": {
            "registry_id": "BSR-BA-04 (confirmed as the next free Baptist id in phase 4)",
            "branch": "(the workbook's exact Baptist branch spelling, confirmed in phase 4)",
            "standard_title": "\"We Are American Baptists\" (ABCUSA Identity Statement, revised 19 June 1998; Standing Rules Addendum #1)",
            "authority_tier": "OFFICIAL_EXPOSITION",
            "authority_tier_note": "interim, pending Codex F.8",
            "speaks_for": "American Baptist Churches USA (descriptive statement its Cooperating Churches affirm; non-binding by its own terms)",
            "reception_scope": "JURISDICTIONAL",
            "publisher_domain": "abc-usa.org",
            "canonical_url": "https://www.abc-usa.org/we-are-american-baptists",
            "fetch_mode": "HTML",
            "scope_caveat": BA04_SCOPE_CAVEAT,
        },
        "adoption": {
            "adoption_status": "ADOPTED", "adoption_body_scope": "ONE_CHURCH",
            "adopting_body": "Board of General Ministries, American Baptist Churches USA (Standing Rules, under Bylaws Art. XIX section 2)",
            "adoption_act": ("Incorporated in the ABCUSA Standing Rules as Addendum #1 (text 'revised June 19, 1998'); Rule 5.1.1 requires "
                             "Cooperating Churches to affirm it 'as descriptive of American Baptist faith and practice'. ABCUSA states it was "
                             "'adopted by the covenanting partners of American Baptist Churches in the U.S.A., 6/19/98'."),
            "adoption_verified": ("Text: abc-usa.org HTML page (Claude Browser + WebFetch), print-ready PDF and Standing Rules 2021 PDF pp. "
                                  "48-50 (Claude Browser, pdf.js text layer); letter-identical across all three. Rule 5.1.1 and the "
                                  "Introductory Note read in the Standing Rules PDF. 1998 act not found: ABCUSA names no body beyond "
                                  "'covenanting partners'; Bylaws, June 1998 General Board minutes and ABHS records not searched."),
            "disclosure_wording": BA04_DISCLOSURE,
        },
        "chunking_guards": {
            "first_sentence_starts": "American Baptists worship the triune God",
            "last_sentence": "That Jesus shall reign for ever and ever.",
            "exclude": "the page head note, links and site chrome",
            "keep": "the 'A Redeemed People / A Biblical People ...' lists (integral, B2(b))"},
        "awaits": "a workbook Branch Source Registry row (the workbook is not written from Code); applied in memory until then",
        "as_implemented": ("NOT YET IMPLEMENTED: session 12 stopped at phase 3 (a stop condition held; see "
                           "recovery-runs/session12/WoP_SJN_Gate6_Session12_Report_20260917.md); the row is recorded here only"),
        "test": "none yet",
        "supersede_with": "Branch Source Registry: a new BSR-BA-04 row carrying these values and the four adoption_* columns"}

    d["source"] = d["source"] if SOURCE in d["source"] else d["source"] + "; " + SOURCE
    out = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if out != raw:
        with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        print("written")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
