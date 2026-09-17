"""Session 13: record, in author-rulings-pending-workbook.json, how each ruling was implemented once its phase passes its tests.
Idempotent.   python record_phase.py <phase>"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")


def phase2(R):
    r = R["R6-43_registration_by_section"]
    r["registered_sections_file"] = "data-sources/sjn/recovery-runs/registered-sections.json"
    r["as_implemented"] = ("rulings.registered_sections() reads recovery-runs/registered-sections.json (62 sections: 29 creed, 33 definition; 13 "
                           "row-level registrations left out, each with its reason); Registry._registered_sections builds "
                           "registered_creed_texts / registered_definition_texts from it only, keeps the row gates as loud checks "
                           "(creed-carrying tier, CONCILIAR for definitions, never CATECHETICAL, never a canon or anathema), and ends a "
                           "section's key after `text_through` where a stored chunk carries more than the creed (RP-04 1.3 and 2.3, "
                           "LU-01 Apostles' Creed, AN-03); chunk-level creed resolution (R6-5 allowed rows) also requires a listed section. "
                           "Before/after: recovery-runs/session13/registration-before-after.md")
    r["test"] = ("test_session13_rulings: test_r6_27_extends_to_sections_no_registered_section_is_a_catechism_or_commentary_section, "
                 "test_lu01_small_and_large_catechism_creed_sections_are_not_registered, test_lu01_ecumenical_creeds_sections_are_registered, "
                 "test_every_listed_section_is_stored_and_the_list_is_the_only_registration_path, test_sections_spanning_several_chunks_are_reported")
    R["R6-46_session12_confirmations"]["as_implemented"]["3_r6_41_interpretations"] = (
        "allocation.py step 5a (session 12), unchanged. Sections found to span more than one chunk (reported, R6-46.3): BSR-RC-04 "
        "Constitution 1 (4 chunks); BSR-RP-04 Nicene Creed 1.1-1.3 and Apostles' Creed 2.1-2.3 (3 chunks each); BSR-EO-12 Symbol of "
        "Faith (12 chunks); BSR-EO-06 Chalcedon Definition (9) and Constantinople III Definition (10); BSR-EO-13 Constantinople III "
        "Definition (10). Recorded per entry in registered-sections.json (section_spans_chunks)")


def phase3(R):
    r = R["R6-44_confessed_catechisms"]
    r["registry_id"] = "BSR-LU-03"
    r["overrides"] = {"authority_tier": "CONFESSIONAL"}
    r["overrides_why"] = ("R6-44 / Codex B1(b): LCMS Constitution Art. II, the confessional subscription, names the Small Catechism of Luther "
                          "among the symbolical books it accepts without reservation (on record: R6-6 rows BSR-LU-03 adoption_act, LCMS "
                          "Handbook 2023 Update Edition, one publisher); the CPH translation carries the status under B2(d). The workbook "
                          "value CATECHETICAL is recorded beside the ruled value by Registry (_author_ruling_override.applied)")
    r["as_implemented"] = ("rulings.registry_overrides: the R6-44 override block above re-types BSR-LU-03 authority_tier in memory; the hook now "
                           "COMBINES several rulings on one row (R6-37 draft_recommendation + R6-44 authority_tier), each field naming its "
                           "ruling (field_rulings), and fails loudly when two rulings set one field to different values. The R6-37 "
                           "translation_disclosure and apparatus guard are unchanged. Catechism-row enumeration: "
                           "recovery-runs/session13/catechism-rows.md")
    r["test"] = ("test_session13_rulings: test_lu03_is_confessional_with_the_workbook_value_recorded_and_keeps_disclosure_and_guard, "
                 "test_several_rulings_on_one_row_combine_and_a_conflict_fails_loudly")


def phase4(R):
    g = R["R6-36_an05_adoption"]["guard"]
    g["why"] = ("The drafting guidelines, the Committee for Catechesis sign-off, the note on Scripture references and the collect, the front "
                "matter before 'Part I', are publisher/editor apparatus (B2(b)): they do not inherit the College of Bishops' adoption and "
                "resolve to OFFICIAL_EXPOSITION. Part I's introductory matter is integral text and is not guarded (R6-46.1)")
    g["reading"] = ("a chunk of the row whose division (or text or locator) carries the marker is apparatus. The chunker "
                    "(sources.acna_to_be_a_christian) gives that division ONLY to the text before 'Part I'; Part I's introductory chunk "
                    "carries division 'Part I introductory matter (integral text)' (sources.ACNA_PART_I_INTRO). There is no fail-closed "
                    "integral-text pattern on this row, so no question chunk can be demoted")
    g["narrowed"] = "2026-09-17, session 13 phase 4, by R6-46.1 (session 12 had guarded Part I's introduction too)"
    R["R6-40_rc07_an04_rp05_adoption"]["guard"]["confirmed"] = "2026-09-17, R6-46.2: the CRC editorial notes on Q&A 77, 80 and 119"
    r = R["R6-45_an04_historical_documents_scope"]
    r["scope_marker"] = {"registry_id": "BSR-AN-04", "locator_prefix": "Historical Documents of the Church", "marker": "AWAITING_SCOPE_RULING",
                         "text": ("BCP 1979 Historical Documents (p. 863 onward), held in the Outline of the Faith row: awaits a scope ruling "
                                  "(R6-45); to become its own registry row after Cowork verification; not a registered creed or definition text")}
    r["as_implemented"] = ("sources.tec_outline_of_faith (session 12 fix, applied in session 13) chunks the text after the Outline title page as "
                           "'Historical Documents of the Church (BCP p. N) — <heading>'; rulings.scope_markers reads the scope_marker above; "
                           "Registry.scope_marker marks every such chunk and tier_resolution / packets carry it on each entry as "
                           "awaits_scope_ruling (packet header: awaiting_scope_ruling); Registry._registered_sections refuses to register a "
                           "marked section, and none is listed in registered-sections.json. Tiers and locators otherwise unchanged")
    r["test"] = "test_session13_rulings: test_an04_historical_documents_chunks_carry_the_scope_marker_and_are_never_registered"
    ai = R["R6-46_session12_confirmations"]["as_implemented"]
    ai["1_an05_guard"] = ("sources.acna_to_be_a_christian: division ACNA_FRONT_MATTER only on the chunk before 'Part I'; Part I's introductory "
                          "chunk has division ACNA_PART_I_INTRO and locator 'To Be a Christian, Part I, Beginning with Christ — introductory "
                          "matter before Q.1'; the R6-36 guard (marker unchanged) therefore guards exactly the front-matter chunk")
    ai["2_rp05_notes"] = ("sources.heidelberg_crcna (session 12 fix, applied in session 13): the CRC notes on Q&A 77, 80 and 119 are their own "
                          "chunks, division 'publisher apparatus (CRC editorial note)', guarded by the R6-40 guard")
    ai["5_in_scope"] = ("corpus builder: corpus.keep_unyielded_entries keeps, on a --only build, the manifest entries of rows the registry no "
                        "longer yields (BSR-EO-03), in manifest order; row-added-by-ruling path: pending: session 13 phase 5")
    R["R6-46_session12_confirmations"]["test"] = ("test_session12_corpus_repair (AN-05 tests updated for R6-46.1; every stored chunk is guarded "
                                                  "exactly when it is the front matter before Part I); "
                                                  "test_session13_rulings.test_an05_guard_covers_only_the_front_matter_before_part_i, "
                                                  "test_a_only_build_keeps_the_manifest_entries_of_rows_the_registry_filters_out; phase 5: pending")


def main():
    phase = sys.argv[1]
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    globals()[f"phase{phase}"](d["rulings"])
    out = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if out != raw:
        open(PATH, "w", encoding="utf-8", newline="\n").write(out)
        print("written")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
