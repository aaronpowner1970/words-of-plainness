"""
WoP Lyric Validator — G4 of the Musical Testimony Lyric-Sync Standard.

For every arrangement (primary and each alternate) that has a lyricsUrl, this
extracts the arrangement's sung lines from its own lyric sheet (resolving
lyricsSameAs), parses its WebVTT timing file, and checks:

    count     cue count == sung-line count
    text      cue text == sheet line, line for line (normalized quotes,
              dashes, whitespace, case)
    numbering cue ids are 1..N, sequential
    duration  no cue shorter than 1.0 s
    order     no overlap, and end > start for every cue
    gaps      any gap between cues longer than 20 s is listed

Statuses:
    ok        every check passed
    warn      count + text pass; numbering/duration/order failed or a gap
              needs a label (still highlighted)
    fail      count or text failed. The VTT is NOT attached: the build
              drops lyricsUrl for that arrangement, which then shows static
              lyrics with no highlight (standard section 3 item 7)
    no-vtt    arrangement has no lyricsUrl (static lyrics or none)

Outputs:
    stdout                              table
    tools/reports/lyric_validation_<YYYYMMDD>.md
    src/_data/lyricsValidation.json     read by .eleventy.js (musicCatalog)

Modes:
    default     warn-only: always exits 0
    --strict    (or env LYRICS_STRICT=1) exits 1 if any arrangement is not
                ok / no-vtt. Strict mode is switched on in Run 3, after the
                catalog is clean.
    --build     quiet; writes the JSON, prints a one-paragraph summary,
                skips the markdown report (used by `npm run build`).

Usage:
    python tools/wop_validate_lyrics.py [--strict] [--build] [--no-report]
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wop_lyrics_extract import (  # noqa: E402  (reuse the denylist extractor)
    CHAPTERS_DIR, MINISTRY_PATH, extract_lines, load_frontmatter,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
LYRICS_DIR = REPO_ROOT / "src" / "assets" / "lyrics"
REPORT_DIR = REPO_ROOT / "tools" / "reports"
JSON_OUT = REPO_ROOT / "src" / "_data" / "lyricsValidation.json"

MIN_CUE = 1.0
MAX_GAP = 20.0

TS_RE = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})")


def ts_seconds(s):
    m = TS_RE.fullmatch(s.strip())
    if not m:
        raise ValueError(f"bad timestamp {s!r}")
    h, mi, se, ms = m.groups()
    return int(h or 0) * 3600 + int(mi) * 60 + int(se) + int(ms) / 1000.0


def fmt(t):
    return f"{int(t // 60)}:{t % 60:06.3f}"


def norm(s):
    s = html.unescape(s)
    s = (s.replace("‘", "'").replace("’", "'")
          .replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-").replace("―", "-"))
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s


def parse_vtt(path):
    """Return list of dicts {id, start, end, text}. id is the cue identifier
    line as a string (or None)."""
    raw = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\r?\n+", raw.strip())
    cues = []
    for b in blocks:
        lines = [l for l in b.splitlines()]
        if not lines or lines[0].startswith("WEBVTT"):
            continue
        ident = None
        if "-->" not in lines[0]:
            ident = lines[0].strip()
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        a, b2 = lines[0].split("-->")
        b2 = b2.strip().split()[0]
        cues.append({
            "id": ident,
            "start": ts_seconds(a),
            "end": ts_seconds(b2),
            "text": " ".join(l.strip() for l in lines[1:]).strip(),
        })
    return cues


def collect_arrangements():
    """Every arrangement with its resolved lyric HTML.

    Yields dicts: file, stem, source, primary_stem, is_alt, lyrics_url,
    own_html (this arrangement's own lyrics block or None), same_as,
    html (resolved sheet HTML), lyrics_source, lyrics_verified.
    """
    out = []

    # ministryMusic.json
    data = json.loads(MINISTRY_PATH.read_text(encoding="utf-8"))
    anthem_fallback = data.get("anthemLyrics", "")
    for item in data.get("collection", []):
        page_html = item.get("lyrics") or (anthem_fallback if item.get("hasLyrics") else "")
        pstem = Path(item["file"]).stem
        out.append(dict(file=item["file"], stem=pstem, source=f'Ministry - {item.get("title")}',
                        title=item.get("title"), label=item.get("label"),
                        primary_stem=pstem, is_alt=False,
                        lyrics_url=item.get("lyricsUrl"), own_html=page_html or None,
                        same_as=None, lyrics_source=item.get("lyricsSource"),
                        lyrics_verified=item.get("lyricsVerified")))
        for alt in item.get("alternates", []) or []:
            out.append(dict(file=alt["file"], stem=Path(alt["file"]).stem,
                            source=f'Ministry - {item.get("title")} (alt)',
                            title=item.get("title"), label=alt.get("label"),
                            primary_stem=pstem, is_alt=True,
                            lyrics_url=alt.get("lyricsUrl"), own_html=alt.get("lyrics"),
                            same_as=alt.get("lyricsSameAs"),
                            lyrics_source=alt.get("lyricsSource"),
                            lyrics_verified=alt.get("lyricsVerified")))

    # chapter frontmatter
    for path in sorted(CHAPTERS_DIR.glob("*.md")) + sorted(CHAPTERS_DIR.glob("*.njk")):
        if path.name.startswith("_"):
            continue
        fm = load_frontmatter(path)
        if not fm:
            continue
        t = (fm.get("audio") or {}).get("testimony") or {}
        if not t.get("file"):
            continue
        pstem = Path(t["file"]).stem
        label = f'Ch {fm.get("chapter", "?")} - {t.get("title", path.stem)}'
        out.append(dict(file=t["file"], stem=pstem, source=label, primary_stem=pstem,
                        title=t.get("title"), label=t.get("label"),
                        chapter_path=str(path),
                        is_alt=False, lyrics_url=t.get("lyricsUrl"),
                        own_html=fm.get("lyrics") or None, same_as=None,
                        lyrics_source=t.get("lyricsSource"),
                        lyrics_verified=t.get("lyricsVerified")))
        for alt in t.get("alternates", []) or []:
            out.append(dict(file=alt["file"], stem=Path(alt["file"]).stem,
                            source=f"{label} (alt)", primary_stem=pstem, is_alt=True,
                            title=t.get("title"), label=alt.get("label"),
                            chapter_path=str(path),
                            lyrics_url=alt.get("lyricsUrl"), own_html=alt.get("lyrics"),
                            same_as=alt.get("lyricsSameAs"),
                            lyrics_source=alt.get("lyricsSource"),
                            lyrics_verified=alt.get("lyricsVerified")))

    by_stem = {a["stem"]: a for a in out}

    def resolve(a, seen=()):
        if a["own_html"]:
            return a["own_html"], None
        if a["same_as"]:
            if a["same_as"] in seen or a["same_as"] not in by_stem:
                return "", f'lyricsSameAs target {a["same_as"]!r} unresolved'
            return resolve(by_stem[a["same_as"]], seen + (a["stem"],))
        return "", None

    for a in out:
        a["html"], a["resolve_error"] = resolve(a)
    return out


def validate(a):
    res = dict(file=a["file"], source=a["source"], is_alt=a["is_alt"],
               same_as=a["same_as"], own_lyrics=bool(a["own_html"]) and a["is_alt"],
               lyrics_source=a["lyrics_source"], lyrics_verified=a["lyrics_verified"])
    if a.get("resolve_error"):
        res["notes"] = [a["resolve_error"]]
    lines = extract_lines(a["html"])
    res["sheet_lines"] = len(lines)
    if not a["lyrics_url"]:
        res.update(status="no-vtt", cues=0, problems=[], gaps=[])
        return res

    vtt_path = REPO_ROOT / "src" / a["lyrics_url"].lstrip("/")
    if not vtt_path.exists():
        res.update(status="fail", cues=0, problems=[f"VTT missing: {a['lyrics_url']}"], gaps=[])
        return res
    res["vtt_sha1"] = hashlib.sha1(vtt_path.read_bytes()).hexdigest()
    cues = parse_vtt(vtt_path)
    res["cues"] = len(cues)

    hard, soft, gaps, mism = [], [], [], []

    if not lines:
        hard.append("no lyric sheet to validate against (cue count cannot match 0 lines)")
    elif len(cues) != len(lines):
        hard.append(f"cue count {len(cues)} != sheet lines {len(lines)}")

    # line-for-line text match — only meaningful when counts agree, but report
    # an aligned diff either way via difflib so the author sees where it breaks.
    if lines and cues:
        if len(cues) == len(lines):
            for i, (c, l) in enumerate(zip(cues, lines), 1):
                if norm(c["text"]) != norm(l):
                    mism.append((i, c["text"], l))
        else:
            from difflib import SequenceMatcher
            sm = SequenceMatcher(None, [norm(c["text"]) for c in cues],
                                 [norm(l) for l in lines], autojunk=False)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == "equal":
                    continue
                for k in range(max(i2 - i1, j2 - j1)):
                    ct = cues[i1 + k]["text"] if i1 + k < i2 else "(no cue)"
                    lt = lines[j1 + k] if j1 + k < j2 else "(no sheet line)"
                    mism.append((i1 + k + 1, ct, lt))
        if mism:
            hard.append(f"{len(mism)} cue(s) differ from the sheet text")
    res["mismatches"] = [dict(cue=i, cue_text=c, sheet_text=l) for i, c, l in mism[:12]]

    ids = [c["id"] for c in cues]
    if ids and not all(x == str(n) for n, x in enumerate(ids, 1)):
        soft.append("cue numbering is not 1..N sequential")
    short = [i for i, c in enumerate(cues, 1) if (c["end"] - c["start"]) < MIN_CUE and c["end"] > c["start"]]
    if short:
        soft.append(f"{len(short)} cue(s) < {MIN_CUE}s (e.g. #{short[0]})")
    bad = [i for i, c in enumerate(cues, 1) if c["end"] <= c["start"]]
    if bad:
        soft.append(f"{len(bad)} cue(s) with end <= start (e.g. #{bad[0]})")
    ovl = [i + 1 for i in range(len(cues) - 1) if cues[i + 1]["start"] < cues[i]["end"] - 1e-6]
    if ovl:
        soft.append(f"{len(ovl)} overlap(s) (e.g. cue #{ovl[0]} -> #{ovl[0] + 1})")
    for i in range(len(cues) - 1):
        g = cues[i + 1]["start"] - cues[i]["end"]
        if g > MAX_GAP:
            gaps.append(dict(after_cue=i + 1, start=round(cues[i]["end"], 3),
                             end=round(cues[i + 1]["start"], 3), seconds=round(g, 2)))
    if gaps:
        soft.append(f"{len(gaps)} gap(s) > {MAX_GAP:.0f}s")

    res["problems"] = hard + soft
    res["gaps"] = gaps
    res["status"] = "fail" if hard else ("warn" if soft else "ok")
    return res


def table(results):
    head = f'{"status":7} {"cues":>4} {"lines":>5}  {"arrangement":62} problems'
    rows = [head, "-" * len(head)]
    for r in results:
        rows.append(f'{r["status"]:7} {r.get("cues", 0):>4} {r["sheet_lines"]:>5}  '
                    f'{r["file"][:62]:62} {"; ".join(r["problems"])}')
    return "\n".join(rows)


def write_report(results, path):
    today = datetime.date.today().isoformat()
    n = {k: sum(1 for r in results if r["status"] == k) for k in ("ok", "warn", "fail", "no-vtt")}
    out = [f"# Lyric validation - {today}", "",
           f"Standard: WoP Musical Testimony Lyric-Sync Standard, section 4 G4. "
           f"Arrangements: {len(results)} - ok {n['ok']}, warn {n['warn']}, "
           f"fail {n['fail']}, no-vtt {n['no-vtt']}.", "",
           "`fail` (cue count or text) = the VTT is not attached; the arrangement shows static lyrics. "
           "`warn` = highlighted, but a timing check needs attention.", "",
           "| status | cues | sheet lines | arrangement | problems |",
           "|---|---:|---:|---|---|"]
    for r in results:
        out.append(f'| {r["status"]} | {r.get("cues", 0)} | {r["sheet_lines"]} | `{r["file"]}` | '
                   f'{"; ".join(r["problems"]) or ""} |')
    detail = [r for r in results if r.get("mismatches") or r.get("gaps")]
    if detail:
        out += ["", "## Detail", ""]
        for r in detail:
            out.append(f'### `{r["file"]}`')
            for m in r.get("mismatches", []):
                out.append(f'- cue {m["cue"]}: VTT "{m["cue_text"]}" / sheet "{m["sheet_text"]}"')
            for g in r.get("gaps", []):
                out.append(f'- gap {g["seconds"]}s after cue {g["after_cue"]} '
                           f'({fmt(g["start"])} - {fmt(g["end"])})')
            out.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()
    strict = args.strict or os.environ.get("LYRICS_STRICT") == "1"

    arrangements = collect_arrangements()
    results = [validate(a) for a in arrangements]

    JSON_OUT.write_text(json.dumps(
        {"arrangements": {r["file"]: {k: r[k] for k in ("status", "cues", "sheet_lines", "problems")
                                      if k in r} | ({"vtt_sha1": r["vtt_sha1"]} if "vtt_sha1" in r else {})
                          for r in results}},
        indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    bad = [r for r in results if r["status"] in ("fail", "warn")]
    if args.build:
        fails = [r for r in results if r["status"] == "fail"]
        print(f"[lyrics] {len(results)} arrangements: "
              f"{sum(r['status'] == 'ok' for r in results)} ok, "
              f"{sum(r['status'] == 'warn' for r in results)} warn, {len(fails)} fail "
              f"(failing VTTs are not attached - static lyrics)")
        for r in fails:
            print(f"[lyrics]   FAIL {r['file']}: {'; '.join(r['problems'])}")
    else:
        print(table(results))
        if not args.no_report:
            rp = REPORT_DIR / f"lyric_validation_{datetime.date.today():%Y%m%d}.md"
            write_report(results, rp)
            print(f"\nreport: {rp}")
    if strict and bad:
        print(f"[lyrics] STRICT: {len(bad)} arrangement(s) failed validation", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
