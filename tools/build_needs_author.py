"""
Builds Aaron's list of arrangements whose recordings need his sheet correction (tier C).

Reads tools/reports/lyric_triage_<date>.json and writes
C:\\Users\\aaron\\Documents\\wop-scratch\\LyricReview\\WoP_Lyrics_NeedsAuthor_<date>.md

Plain markdown, no tables or HTML. Proposes nothing: it shows what the recording sings next to the
current sheet; Aaron supplies the corrected sheet (author ruling R3).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = Path(r"C:\Users\aaron\Documents\wop-scratch\LyricReview")
MEDIA = "https://media.wordsofplainness.org/web/"


def mmss(t):
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{int(t % 60):02d}"


def main():
    tpath = sorted((REPO / "tools" / "reports").glob("lyric_triage_2*[0-9].json"))[-1]
    d = json.loads(tpath.read_text(encoding="utf-8"))
    date = d["date"]
    held = {h["stem"] for h in json.loads((REPO / "src" / "_data" / "lyricsHold.json").read_text(encoding="utf-8"))["holds"]}
    rows = [r for r in d["rows"] if r["tier"] == "C"]
    rows.sort(key=lambda r: -(r["new"] + len(r["unsung"])))
    L = [f"# Lyrics that need your sheet - {date}", "",
         "1. Correct the sheet for each song below in the musical testimony project.",
         "2. Save it as <stem>.VALIDATED.txt (one sung line per line) in C:\\Users\\aaron\\Documents\\wop-scratch\\LyricReview\\",
         "3. Run python tools\\wop_lyrics_apply_validated.py in the repo (or ask Code to). Nothing here changes the site.", "",
         f"{len(rows)} arrangements, worst first. 'Heard' text is speech recognition and may be wrong; "
         "listen at the time given.", ""]
    for r in rows:
        title = f"{r['title']} - {r['label']}"
        L += ["---", "", f"{title}" + ("   [on the hold list: shown as static lyrics]" if r["stem"] in held else ""),
              f"stem: {r['stem']}", f"listen: {MEDIA}{r['file']}", ""]
        new = [x for x in r["runs"] if x["kind"] == "NEW"]
        for x in new:
            near = r["sheet"][min(max(x["near_line"], 1), len(r["sheet"])) - 1]
            L.append(f"at {mmss(x['start'])} the recording sings: {x['heard']}   (nearest sheet line {x['near_line']}: {near})")
        for u in r["unsung"]:
            when = f"expected about {mmss(u['expected'])}" if u["expected"] is not None else "time unknown"
            L.append(f"sheet line {u['line']} may not be sung: {u['text']}   ({when})")
        if not new and not r["unsung"]:
            L.append("(no specific findings)")
        L += ["", "current sheet:"]
        L += [f"{i}. {t}" for i, t in enumerate(r["sheet"], 1)]
        L.append("")
    out = OUT_DIR / f"WoP_Lyrics_NeedsAuthor_{date}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} arrangements)")


if __name__ == "__main__":
    main()
