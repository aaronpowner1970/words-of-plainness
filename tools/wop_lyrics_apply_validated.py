"""
Apply author-validated sheets in one command.

For every <stem>.VALIDATED.txt in C:\\Users\\aaron\\Documents\\wop-scratch\\LyricReview\\ (one sung
line per line, UTF-8; precedent 09_02, 07_02) that DIFFERS from the arrangement's current sheet:

  1. write it into that arrangement's OWN lyrics frontmatter (ministryMusic.json for ministry
     songs). Never the shared primary sheet unless the stem IS the primary; if it is a primary
     that other arrangements inherit, they first get an explicit copy of the old sheet.
     Paragraph structure (section labels, verse/chorus) is kept where lines are unchanged.
     Em dashes and punctuation are exactly as in the file.
  2. align a VTT (wop_align_song's alignment on cached whisper words: base, then small, then
     medium, first with >= 90% of lines matched directly),
  3. validate (G4) and attach on pass; on failure the old VTT is restored, the candidate is
     kept in tools/lyrics_candidates/ and the problem is reported.

Re-running with nothing new changes nothing.

Usage:
    python tools/wop_lyrics_apply_validated.py [--dir PATH] [--dry-run]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wop_ship as S  # noqa: E402
import wop_sheet_edit as SE  # noqa: E402
from wop_lyrics_extract import extract_lines  # noqa: E402

DEFAULT_DIR = Path(r"C:\Users\aaron\Documents\wop-scratch\LyricReview")


def read_validated(p):
    raw = p.read_bytes()
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return [l.rstrip() for l in text.split("\n") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DEFAULT_DIR))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    files = sorted(Path(args.dir).glob("*.VALIDATED.txt"))
    if not files:
        print("no *.VALIDATED.txt files found")
        return
    changed = 0
    for f in files:
        stem = f.name[: -len(".VALIDATED.txt")]
        try:
            arr = S.arrangement(stem)
        except KeyError:
            print(f"{stem}: no such arrangement - skipped")
            continue
        new_lines = read_validated(f)
        cur = extract_lines(arr["html"])
        if cur == new_lines:
            print(f"{stem}: unchanged ({len(cur)} lines)")
            continue
        print(f"{stem}: sheet differs ({len(cur)} -> {len(new_lines)} lines)")
        if args.dry_run:
            continue
        if not cur:
            html = '<p class="verse">' + "<br>\n".join(SE._esc(l) for l in new_lines) + "</p>\n"
        else:
            html = SE.apply_lines(arr["html"], new_lines)
        S.save_own_sheet(arr, html)
        res = S.align_attach(S.arrangement(stem), new_lines)
        changed += 1
        state = "attached" if res["attached"] else "NOT attached (candidate saved to tools/lyrics_candidates/)"
        print(f"  {res['model']} direct {res['direct_pct']}%  validator {res['status']}  "
              f"{res['cues']}/{res['sheet_lines']} cues  {state}")
        for p in res["problems"]:
            print("   -", p)
    print(f"done: {changed} arrangement(s) changed")


if __name__ == "__main__":
    main()
