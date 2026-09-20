"""Session 14 (2026-09-19), phase 1: write the author's rulings R6-47 to R6-57 into
author-rulings-pending-workbook.json. Idempotent: running it twice leaves the file as after the first run.

Their text is taken from Comparison Principles Codex v0.8 — Part E (the precedent table) and the refinements
B1(c), B1(d), B1(e), C1(a) and C3(a). The codex is NOT edited by this session.

The operative blocks each ruling needs (R6-54's queue file and voting record, R6-57's registered-section extents,
R6-48's new AN-06 row, R6-50's same-text pair, R6-51's AN-04 extent) are added by the phase that implements them;
`as_implemented` and `test` are updated there too, through session14/record_phase.py.

  python data-sources/sjn/recovery-runs/session14/write_rulings.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")

SOURCE = ("Code session 14 prompt, 'SESSION: CODE-SJN-16 ... SJN Gate 6, session 14' (19 Sep 2026), which records the author's "
          "rulings R6-47 to R6-57 as RATIFIED in Comparison Principles Codex v0.8 (17 Sep 2026): Part E precedents R6-47 to R6-57 "
          "and the refinements B1(c), B1(d), B1(e), C1(a) and C3(a). The codex file on disk was read in full and its header line "
          "'Draft v0.8' confirmed before any ruling below was written")
CODEX = "Comparison Principles Codex v0.8"
PENDING = "pending: session 14 phase {}"


def main():
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    R = d["rulings"]

    def put(key, value):
        """Write a ruling, keeping any operative blocks or as_implemented text a later phase has already written."""
        old = R.get(key) or {}
        for k, v in old.items():
            if k not in value or (k in ("as_implemented", "test") and not str(v).startswith("pending")):
                value[k] = v
        R[key] = value

    base = {"ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED"}

    # ---------------------------------------------------------------- v0.7 set (TEC Historical Documents), R6-47 to R6-53
    put("R6-47_adoption_is_not_confession", dict(base, **{
        "rule": ("Codex B1(c), adoption is not confession: a creed- or definition-genre text resolves at its genre's tier for a "
                 "church only where that church CONFESSES it — its confessional subscription names it, its liturgy appoints it, or "
                 "its adopted catechism presents it as a creed of the church. A text a church adopts within a book but presents as "
                 "a historical document, with none of these marks, is a WITNESS: its adoption stands under B2, but it is not a "
                 "registered section and it cannot seat a cell alone. How the church presents the text is judged from the church's "
                 "adopted text only; publisher references and press glossaries are context. Absent the marks the text stays a "
                 "witness (fail closed); positive evidence of confession reopens it. Applied to the TEC BCP 1979 Historical "
                 "Documents: the Chalcedonian Definition and the Quicunque Vult are ADOPTED (General Convention 1979-A133) but not "
                 "confessed — no liturgical appointment, and the BCP's own Catechism (p. 852) calls the Athanasian Creed 'an "
                 "ancient document'. Article VIII of the 1801 Articles of Religion corroborates only."),
        "codex": f"B1(c), B2 ({CODEX})",
        "author_assent": ("the author explicitly assented to the fail-closed treatment of the Chalcedonian Definition (Codex v0.7 "
                          "change log)"),
        "registry_ids": ["BSR-AN-06"],
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "none (a tier and registration principle; the row it governs is BSR-AN-06, added by R6-48)"}))

    put("R6-48_an06_historical_documents_row", dict(base, **{
        "rule": ("BSR-AN-06 is the TEC BCP 1979 'Historical Documents of the Church' as SJN holds it: the Chalcedonian Definition "
                 "and the Quicunque Vult, BCP pp. 863-865. Its registered sections are NONE (R6-47: witness sections). The 1549 "
                 "Preface (p. 866 on), the Articles of Religion (p. 867 on) and the Chicago-Lambeth Quadrilateral are NOT fetched "
                 "for SJN. There is no AN-07 id: one row holds both documents."),
        "codex": f"B1(a) ({CODEX})",
        "registry_id": "BSR-AN-06",
        "extent": {"from": "BCP p. 863 (the 'Historical Documents of the Church' title page)", "to": "BCP p. 865",
                   "documents": ["Definition of the Union of the Divine and Human Natures in the Person of Christ, "
                                 "Council of Chalcedon, 451 A.D., Act V (BCP p. 864)",
                                 "Quicunque Vult, commonly called The Creed of Saint Athanasius (BCP pp. 864-865)"],
                   "not_fetched": ["the Preface, The First Book of Common Prayer (1549), BCP p. 866 on",
                                   "the Articles of Religion (1801), BCP p. 867 on — held by R6-49",
                                   "the Chicago-Lambeth Quadrilateral"]},
        "registered_sections": "none",
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "Branch Source Registry: a new BSR-AN-06 row carrying these values and the four adoption_* columns"}))

    put("R6-49_tec_articles_of_religion_held", dict(base, **{
        "rule": ("The TEC Articles of Religion (1801) are HELD for the adoption QA track (Codex F.9). They are not fetched and not "
                 "added as a registry row in this session or in any session before that QA reports. Open items: the 1801 "
                 "Convention act; when Art. X dropped 'Articles of Religion'; when Canon II.3.1 dropped 'Historical Documents of "
                 "the Church'; the effect of the failed reaffirmations (1994-D089, 2003-B001); the overlap with BSR-AN-01 under "
                 "R6-4."),
        "codex": f"B2; F.9 ({CODEX})",
        "held": "TEC Articles of Religion (1801), BCP 1979 pp. 867-876",
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "none until the F.9 adoption QA reports"}))

    put("R6-50_an06_an03_same_text_pair", dict(base, **{
        "rule": ("Named same-text pair under the R6-4 same-text guard: BSR-AN-06's Quicunque Vult section and BSR-AN-03 (the "
                 "Church of England BCP Athanasian Creed) are ONE TEXT. BSR-AN-03 holds the slot; BSR-AN-06 takes none beside it "
                 "and is recorded as a parallel witness. The 'both God and Lord' source question (the two printings differ in that "
                 "line) is recorded, not pursued."),
        "codex": f"B3 (R6-4), B2(d) ({CODEX})",
        "same_text_rows": {"BSR-AN-06": {"same_text_as": "BSR-AN-03",
                                         "what": "the Quicunque Vult / Creed of Saint Athanasius, one text in two printings "
                                                 "(TEC BCP 1979 Historical Documents; Church of England BCP)",
                                         "recorded_not_pursued": "the two printings differ at 'to acknowledge every Person by "
                                                                 "himself to be both God and Lord'; the source question is "
                                                                 "recorded and not pursued (R6-50)"}},
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "Branch Source Registry: a same-text / same-work note on BSR-AN-06 naming BSR-AN-03"}))

    put("R6-51_an04_extent_and_p844_rubric", dict(base, **{
        "rule": ("BSR-AN-04 is the Outline of the Faith as the BCP 1979 prints it, BCP pp. 844-862. The p. 844 rubric "
                 "('Concerning the Catechism') is INTEGRAL TEXT of the adopted book (B2(b)): it is stored with its own locator and "
                 "is NOT a registered section. It is recorded as CATECHETICAL support. The R6-40 verification note is closed "
                 "(pdf.js text layer, one publisher)."),
        "codex": f"B2(b), B1(b) ({CODEX})",
        "registry_id": "BSR-AN-04",
        "extent": {"from": "BCP p. 844 (the rubric 'Concerning the Catechism')", "to": "BCP p. 862",
                   "p844_rubric": {"integral_text": True, "registered": False, "recorded_as": "CATECHETICAL support"}},
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "none (an extent ruling; BSR-AN-04's workbook row is unchanged)"}))

    put("R6-52_1979_a133_citation", dict(base, **{
        "rule": ("General Convention resolution 1979-A133 is cited at Journal p. C-8, per the Archives of the Episcopal Church. "
                 "The 1985 note's citation to p. C-9 is recorded as UNRECONCILED; it is not silently corrected and it is not "
                 "treated as a second instrument."),
        "codex": f"D1 ({CODEX})",
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "none (a citation record; it travels with BSR-AN-06's adoption_verified)"}))

    put("R6-53_tec_glossary_context_only", dict(base, **{
        "rule": ("The Episcopal Church glossary (a Church Publishing adaptation) and the Brief Dictionary (a 2011 press page) are "
                 "CONTEXT ONLY. Neither is evidence of adoption or of confession, and neither is a publisher independent of the "
                 "church's own adopted text (B2(b): a publisher's or editor's matter never inherits the adoption)."),
        "codex": f"B2, B2(b) ({CODEX})",
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "none"}))

    # ---------------------------------------------------------------- v0.8 set (session 13 report), R6-54 to R6-57
    put("R6-54_production_voting_and_review_queue", dict(base, **{
        "rule": ("Production voting and the author review queue are BUILT AND TESTED BEFORE ANY PAID RUN. "
                 "Codex C1(a), production voting shape: a branch run makes THREE gate6-v1.3 calls per candidate and takes the "
                 "MAJORITY over verdict class. The floor is the LOWEST FLOOR AMONG THE MAJORITY, so rule 2a stands. Opus routes "
                 "are voted the same way. Every verdict records its INSTRUMENT: prompt version, call count and vote split. No "
                 "seated verdict reaches public certification on anything but a v1.3 majority verdict. "
                 "Codex C3(a), queue shape and the publication bar: DOUBT is any dissenting vote, or ACCEPT_WITH_CAVEAT at "
                 "PARTIAL. The queue is a COMMITTED FILE, and both the packet builder and the emit step refuse to pass a queued "
                 "item until the author has ruled on it. Before the queue is switched on, the run reports how many existing "
                 "accepts would enter it."),
        "codex": f"C1(a), C3(a) ({CODEX})",
        "voting": {"calls_per_candidate": 3, "prompt_version": "gate6-v1.3", "majority_over": "verdict class",
                   "floor": "the lowest floor among the majority (rule 2a stands)",
                   "opus_routes": "voted the same way",
                   "instrument_recorded": ["prompt_version", "call_count", "vote_split"],
                   "public_certification": "only a gate6-v1.3 MAJORITY verdict may carry a seated citation to public certification"},
        "doubt": ["any dissenting vote", "ACCEPT_WITH_CAVEAT at a PARTIAL floor"],
        "queue": {"committed_file": True, "bars": ["the packet builder", "the emit step"],
                  "released_by": "an author ruling on the queued item, recorded in the queue file",
                  "volume_reported_before_use": True},
        "existing_verdicts": ("stored verdicts are labelled with their ACTUAL instrument (their own prompt version, call count 1, "
                              "no vote split). They are never relabelled as majority verdicts"),
        "as_implemented": PENDING.format(2), "test": PENDING.format(2),
        "supersede_with": "none (a measurement rule; the queue file is a reviewable harness record, not a workbook value)"}))

    put("R6-55_allocation_across_speaks_for_groups", dict(base, **{
        "rule": ("Allocation across speaks_for groups is ACCEPTED AS IT STANDS and flagged as its own gap (Codex F.11): within a "
                 "tier, speaks_for groups take slots round by round, and strength of match ranks candidates only INSIDE a group, "
                 "so a group's second candidate can outrank a stronger candidate from another group. Q-195's third Lutheran seat "
                 "holds at Q-195-p1-BSR-LU-01-2 (PARTIAL, Large Catechism) over Q-195-p1-BSR-LU-03-1 (FULL, Small Catechism); the "
                 "LCMS confessional slot is held by Q-195-p1-BSR-LU-02-1, the Augsburg Confession, before and after. No allocation "
                 "change is made in this session."),
        "codex": f"B3; F.11 ({CODEX})",
        "queue_id": "Q-195",
        "holds": {"Q-195_seats": ["Q-195-p1-BSR-LU-01-1", "Q-195-p1-BSR-LU-02-1", "Q-195-p1-BSR-LU-01-2"]},
        "as_implemented": PENDING.format(3), "test": PENDING.format(3),
        "supersede_with": "none until Codex F.11 is settled (it re-orders seats on every card with more than one group and is run "
                          "on its own)"}))

    put("R6-56_evidence_bar_for_a_tier_move", dict(base, **{
        "rule": ("Codex B1(d), the evidence bar for a tier move: a tier move is a load-bearing finding, so no row moves tier until "
                 "the act relied on has been read through TWO INSTRUMENTS and TWO PUBLISHERS, and the reading is reported with "
                 "three ranked readings and their weaknesses. A row on the line WAITS AT ITS PRESENT TIER while that verification "
                 "runs; it is not moved provisionally. Applied: BSR-AN-02 (BCP 1662 Catechism) and BSR-RC-01 (Catechism of the "
                 "Catholic Church) hold at their present tier pending Cowork verification (Canon A5 and the canons around it; the "
                 "text of Fidei Depositum itself). NO TIER MOVES IN THIS SESSION."),
        "codex": f"B1(d), B1(b) ({CODEX})",
        "rows_held": {"BSR-AN-02": "CATECHETICAL (workbook value); awaiting Canon A5 through a second instrument and a second publisher",
                      "BSR-RC-01": "CATECHETICAL (workbook value); awaiting the text of Fidei Depositum itself"},
        "as_implemented": PENDING.format(3), "test": PENDING.format(3),
        "supersede_with": "none until the Cowork verification reports"}))

    put("R6-57_registered_section_extents", dict(base, **{
        "rule": ("Codex B1(e), the extent of a registered section: a registered section runs as far as the CREED OR DEFINITION "
                 "ITSELF runs, not as far as the stored block runs. Where a block carries creed text and other matter together, "
                 "only the creed portion is registered and its extent is RECORDED. Liturgical matter printed alongside a creed is "
                 "not part of it, and a council's acts narrative is not part of its definition. The three session 13 section 3.3 "
                 "extent judgments are RATIFIED: (1) the creed portion of a mixed block is registered and its extent recorded; "
                 "(2) the Gloria Patri after BSR-AN-03's Athanasian Creed is left out as liturgical matter; (3) BSR-EO-06's "
                 "Chalcedon paragraph 10 is left out as acts narrative."),
        "codex": f"B1(e), B1(a) ({CODEX})",
        "ratifies": {
            "1_mixed_block_extent": ("the creed portion of a mixed block is registered and its extent recorded "
                                     "(registered-sections.json `text_through`): BSR-RP-04 1.3 and 2.3, BSR-LU-01 Ecumenical "
                                     "Creeds: The Apostles' Creed, BSR-AN-03"),
            "2_gloria_patri_left_out": ("BSR-AN-03's registered extent ends at 'he cannot be saved.'; the Gloria Patri the BCP "
                                        "appoints after the creed at Morning Prayer is liturgical matter and is outside it"),
            "3_eo06_chalcedon_para_10_left_out": ("BSR-EO-06 'Definition of Faith, Council of Chalcedon (451), paragraph 10' is "
                                                  "the acts' record of the bishops' acclamation after the reading, not the "
                                                  "definition; it stays in registered-sections.json `not_registered`")},
        "as_implemented": PENDING.format(3), "test": PENDING.format(3),
        "supersede_with": "none (a registration rule; the extents are a reviewable harness record, not a workbook value)"}))

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
