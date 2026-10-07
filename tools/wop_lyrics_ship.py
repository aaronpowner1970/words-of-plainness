"""
Ship tier A and tier B arrangements from the lyric triage (Run 3b).

Reads tools/reports/lyric_triage_<date>.json (from wop_triage_lyrics.py) and:

  Tier B  (only REPEAT runs): insert the repeated sheet lines into THAT arrangement's own sheet at
          the place they are sung (author ruling R1). Lines are exact copies of lines already in the
          sheet; nothing is taken from the transcript. A primary that other arrangements inherit
          first gives them an explicit copy of the old sheet. The edited sheet is re-audited against
          the same recording; if any NEW/REPEAT run or unsung line remains, nothing is written and
          the arrangement drops to tier C.
  Tier A + B: if the arrangement has no attached VTT, or its VTT fails G4, or the sheet changed,
          align (base -> small -> medium, >= 90% direct), validate (G4) and attach on pass.
          An existing attached VTT that already passes G4 is left alone when the sheet is unchanged.
  Hold list: a stem in src/_data/lyricsHold.json is never touched; it is listed as
          "held - would pass".

Writes tools/reports/lyric_ship_<date>.json (what shipped / held / skipped).

Usage: python tools/wop_lyrics_ship.py [--triage PATH] [--dry-run]
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wop_ship as S  # noqa: E402
import wop_sheet_edit as SE  # noqa: E402
import wop_triage_lyrics as T  # noqa: E402
import wop_validate_lyrics as V  # noqa: E402
from wop_lyrics_extract import extract_lines  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def load_holds():
    d = json.loads((REPO / "src" / "_data" / "lyricsHold.json").read_text(encoding="utf-8"))
    return {h["stem"]: h for h in d.get("holds", [])}


def plan_repeats(row):
    """-> list of (after_idx, [src line idx]) or None if a repeat cannot be placed."""
    plans, seen = [], set()
    for r in row["runs"]:
        if r["kind"] != "REPEAT":
            continue
        if r["after"] < 0:
            return None
        key = (r["after"], tuple(r["lines"]))
        if key in seen:
            continue
        seen.add(key)
        plans.append((r["after"], list(r["lines"])))
    return plans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triage")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    tpath = args.triage or sorted((REPO / "tools" / "reports").glob("lyric_triage_2*.json"))[-1]
    rows = json.loads(Path(tpath).read_text(encoding="utf-8"))["rows"]
    holds = load_holds()
    out = dict(shipped=[], repeats=[], held_would_pass=[], left_alone=[], demoted_to_C=[], failed_attach=[])

    for row in rows:
        stem, tier = row["stem"], row["tier"]
        if tier == "C":
            continue
        arr = S.arrangement(stem)
        lines = extract_lines(arr["html"])
        if stem in holds:
            out["held_would_pass"].append(dict(stem=stem, tier=tier, hold_date=holds[stem]["date"]))
            continue
        sheet_changed = False
        if tier == "B" and lines != row["sheet"]:
            out["left_alone"].append(dict(stem=stem, tier=tier, note="sheet already differs from the triage snapshot (repeats already applied)"))
            continue
        if tier == "B":
            plans = plan_repeats(row)
            if plans is None or "chapter_path" not in arr:
                out["demoted_to_C"].append(dict(stem=stem, reason="repeat cannot be placed automatically"))
                continue
            new_html = SE.insert_repeats(arr["html"], plans)
            new_lines = extract_lines(new_html)
            assert set(new_lines) <= set(lines), "R1 violation: a line not already on the sheet"
            # re-audit the edited sheet against the same recording
            words = T.best_cached_words(stem)
            chk = T.triage_one(dict(arr, html=new_html), new_lines, words=words)
            if chk["tier"] != "A":
                out["demoted_to_C"].append(dict(stem=stem, reason=f"after inserting repeats the audit still shows: {chk['reason']}"))
                continue
            if not args.dry_run:
                S.save_own_sheet(arr, new_html)
            sheet_changed = True
            for after, src in plans:
                out["repeats"].append(dict(stem=stem, after_line=after + 1, after_text=lines[after],
                                           inserted=[lines[i] for i in src]))
            lines = new_lines
        if args.dry_run:
            continue
        arr = S.arrangement(stem)
        vtt_ok = False
        if arr["lyrics_url"] and not sheet_changed:
            vtt_ok = V.validate(arr)["status"] in ("ok", "warn")
        if vtt_ok:
            out["left_alone"].append(dict(stem=stem, tier=tier))
            continue
        res = S.align_attach(arr, lines)
        (out["shipped"] if res["attached"] else out["failed_attach"]).append(dict(tier=tier, **res))
        state = "attached" if res["attached"] else "NOT attached"
        print(f"{stem[:50]} tier {tier}: {res['model']} direct {res['direct_pct']}% validator {res['status']} {state}", flush=True)

    date = datetime.date.today().strftime("%Y%m%d")
    (REPO / "tools" / "reports" / f"lyric_ship_{date}.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main()
