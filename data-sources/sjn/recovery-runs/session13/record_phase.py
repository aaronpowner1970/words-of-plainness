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
