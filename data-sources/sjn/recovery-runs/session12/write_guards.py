"""Session 12 (2026-09-17), phase 3c/3d: the apparatus-guard entries for BSR-AN-05 (front matter) and BSR-RP-05 (CRC editorial notes),
in the session 11 style (a `guard` object on the ruling that ratified the row's adoption; rulings.adoption_guards reads it). Idempotent.

  python data-sources/sjn/recovery-runs/session12/write_guards.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "author-rulings-pending-workbook.json")
SOURCE = ("Code session 12 prompt (17 Sep 2026), phase 3c / 3d: 'Under B2(b) the front matter is publisher/editor apparatus: apply the "
          "session 11 apparatus guard to it' / 'the CRC editorial footnotes ... are publisher matter; separate them ... and apply the "
          "apparatus guard to them'")

GUARDS = {
    "R6-36_an05_adoption": {
        "registry_id": "BSR-AN-05", "kind": "PUBLISHER_APPARATUS",
        "apparatus_markers": ["front matter (publisher/editor apparatus)"],
        "resolves_to": "OFFICIAL_EXPOSITION",
        "why": ("The drafting guidelines, the Committee for Catechesis sign-off, the note on Scripture references, the collect and the "
                "introductory matter before Q.1 are publisher/editor apparatus (B2(b)): they do not inherit the College of Bishops' "
                "adoption and resolve to OFFICIAL_EXPOSITION"),
        "reading": ("a chunk of the row whose division (or text or locator) carries the marker is apparatus. The chunker "
                    "(sources.acna_to_be_a_christian) gives that division to the text the store held before the first question, and "
                    "to nothing else; there is no fail-closed integral-text pattern on this row, so no question chunk can be demoted"),
        "added": "2026-09-17, session 12 (phase 3c)", "source": SOURCE},
    "R6-40_rc07_an04_rp05_adoption": {
        "registry_id": "BSR-RP-05", "kind": "PUBLISHER_APPARATUS",
        "apparatus_markers": ["publisher apparatus (CRC editorial note)"],
        "resolves_to": "OFFICIAL_EXPOSITION",
        "why": ("The CRC's editorial footnotes (Q&A 80's edition note and the Synod 2004/2006 bracket note; the notes on Q&A 77 and "
                "Q&A 119) are publisher matter (B2(b)): they do not inherit the Synods' adoption of the catechism and resolve to "
                "OFFICIAL_EXPOSITION"),
        "reading": ("a chunk of the row whose division (or text or locator) carries the marker is apparatus. The chunker "
                    "(sources.heidelberg_crcna) gives that division to the paragraphs opening '*' / '**' and what follows them before the "
                    "next Q&A, and to nothing else; there is no fail-closed integral-text pattern on this row"),
        "added": "2026-09-17, session 12 (phase 3d)", "source": SOURCE},
}


def main():
    raw = open(PATH, encoding="utf-8").read()
    d = json.loads(raw)
    for key, g in GUARDS.items():
        ru = d["rulings"][key]
        if ru.get("guard") and ru["guard"].get("registry_id") != g["registry_id"]:
            raise SystemExit(f"{key} already carries a guard for {ru['guard'].get('registry_id')}")
        ru["guard"] = g
    out = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if out != raw:
        with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        print("written")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
