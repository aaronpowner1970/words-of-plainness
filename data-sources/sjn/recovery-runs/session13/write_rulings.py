"""Session 13 (2026-09-17), phase 1: write the author's rulings R6-43, R6-44, R6-45 and R6-46 into
author-rulings-pending-workbook.json. Idempotent: running it twice leaves the file as after the first run.

The operative blocks each ruling needs (R6-43's registered-sections file, R6-44's registry override, R6-45's scope marker,
R6-46.1's narrowed guard) are added by the phase that implements them; `as_implemented` is updated there too.

  python data-sources/sjn/recovery-runs/session13/write_rulings.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")

SOURCE = ("Code session 13 prompt, 'SJN GATE 6 -- SESSION 13: SECTION REGISTRATION, CONFESSED CATECHISMS, CORPUS REPAIR RESUMED, NEW "
          "BAPTIST ROW (rulings R6-43 to R6-46; 17 Sep 2026)', ratified 2026-09-17 in Chat on the session 12 report; Comparison Principles "
          "Codex v0.6 (B1(a), B1(b), Part E)")
PENDING = "pending: session 13 phase {}"


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

    put("R6-43_registration_by_section", {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": ("Codex B1(a), registration is by section: a chunk counts as a registered creed or definition text only if it is that creed "
                 "or definition itself, never a catechism's, confession's or commentary's treatment of it, whatever the row's tier. "
                 "Registered sections are kept as an explicit, reviewable list per row. The R6-27 test extends from rows to sections. For "
                 "BSR-LU-01, the registered creed texts are its 'Ecumenical Creeds' sections; its Small Catechism and Large Catechism "
                 "'Creed' sections are not registered texts."),
        "codex": "B1(a) (Comparison Principles Codex v0.6)",
        "resolves": "the session 12 phase 3e stop (recovery-runs/session12/WoP_SJN_Gate6_Session12_Report_20260917.md section 1)",
        "rows_named": {"BSR-LU-01": {"registered": "Ecumenical Creeds sections",
                                     "not_registered": ["Small Catechism: II. The Creed", "Large Catechism: The Apostles' Creed"]}},
        "as_implemented": PENDING.format(2), "test": PENDING.format(2),
        "supersede_with": "none (a registration rule; the list is a reviewable harness record, not a workbook value)"})

    put("R6-44_confessed_catechisms", {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": ("Codex B1(b), confessed catechisms: a catechism that a church's confessional subscription names as a doctrinal standard is "
                 "CONFESSIONAL; a catechism adopted for instruction is CATECHETICAL; under B2(d) the status carries to translations. "
                 "BSR-LU-03 moves to CONFESSIONAL (LCMS Constitution Art. II names 'the Small Catechism of Luther'); it keeps its "
                 "translation disclosure and its apparatus guard. No other row moves in this session."),
        "codex": "B1(b), B2(d) (Comparison Principles Codex v0.6)",
        "rows_moved": ["BSR-LU-03"],
        "keeps": ["R6-37 translation_disclosure", "R6-37 apparatus guard"],
        "report_required": "every registry row whose document is a catechism, across all branches, with its tier and whether a confessional "
                           "subscription or adopting act on record names it as a doctrinal standard; no other row is moved",
        "as_implemented": PENDING.format(3), "test": PENDING.format(3),
        "supersede_with": "Branch Source Registry, BSR-LU-03: authority_tier CONFESSIONAL"})

    put("R6-45_an04_historical_documents_scope", {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": ("The BSR-AN-04 text after the Outline (BCP p. 863 onward: the Historical Documents title page, the Chalcedonian Definition, "
                 "the Quicunque Vult) is to become its own registry row after Cowork verification. Until that row is ratified, its chunks "
                 "keep correct locators, carry a marker that they await a scope ruling, and are not themselves registered creed or "
                 "definition texts."),
        "codex": "B1, B2(b) (Comparison Principles Codex v0.6)",
        "registry_id": "BSR-AN-04",
        "awaits": "Cowork verification, then a ratified registry row for the BCP Historical Documents",
        "as_implemented": PENDING.format(4), "test": PENDING.format(4),
        "supersede_with": "a new Branch Source Registry row for the BCP Historical Documents (not yet proposed)"})

    put("R6-46_session12_confirmations", {
        "ruled": "2026-09-17", "source": SOURCE, "status": "RATIFIED",
        "rule": "Confirmations of session 12's open items (1-5 below)",
        "codex": "B2(b), B3(a) (Comparison Principles Codex v0.6)",
        "items": {
            "1_an05_guard": ("AN-05: the apparatus guard covers ONLY the front-matter chunk before 'Part I' (drafting guidelines, Committee "
                             "sign-off, Scripture-references note, collect). The Part I introductory chunk is integral text and is NOT guarded."),
            "2_rp05_notes": "RP-05: separate and guard the CRC editorial notes on Q&A 77, 80 and 119, as session 12 built.",
            "3_r6_41_interpretations": ("'candidate' means a verifier-accepted candidate that reaches allocation; 'registered text' means the "
                                        "registered section, implemented as the chunk. If a registered section is found to span more than "
                                        "one chunk, report it."),
            "4_phase2_seat_effects": ("The phase 2 seating effects (Q-317 and Q-373 at two seats; Q-301 all Church of England; the Episcopal "
                                      "Church reprint as a parallel witness) are accepted."),
            "5_in_scope": "In scope this session: the corpus-builder fix (phase 4) and the row-added-by-ruling path (phase 5)."},
        "confirms": {"R6-41_interpretations": "session 12 report section 3.1", "an05_candidate": "session 12 report section 4.3 candidate 2",
                     "rp05_scope": "session 12 report section 4.4 (Q&A 77, 80, 119)"},
        "as_implemented": {"1_an05_guard": PENDING.format(4), "2_rp05_notes": PENDING.format(4),
                           "3_r6_41_interpretations": "allocation.py step 5a (session 12), unchanged; span report: " + PENDING.format(2),
                           "4_phase2_seat_effects": "accepted; no code change",
                           "5_in_scope": "corpus builder: " + PENDING.format(4) + "; row-added-by-ruling path: " + PENDING.format(5)},
        "test": PENDING.format("4-5"),
        "supersede_with": "none"})

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
