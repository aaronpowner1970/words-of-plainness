"""
WoP lyric triage - sorts every arrangement into tiers from the G4b audit.

For each lyric-bearing arrangement (author-validated stems excluded) it
re-runs the sung-content audit against the CURRENT sheet using cached whisper
words (medium where cached, else small) and classifies every UNSHEETED run
(4+ consecutive heard words with no sheet match):

    REPEAT  the heard words match (fuzzy, ASR-tolerant) a contiguous span of
            1-10 lines of the SAME arrangement's resolved sheet. Rule: join
            heard tokens, compare with each candidate window's tokens using
            SequenceMatcher on token lists; REPEAT when ratio >= 0.72 and the
            window has between 0.6x and 1.6x the heard word count. The best
            window wins (ties: longer window).
    NEW     anything else.

Tiers (substitutions alone are treated as ASR noise):
    A  no unsheeted runs and no UNSUNG lines
    B  only REPEAT runs, no UNSUNG lines     (author ruling R1: add the repeats)
    C  any NEW run or any UNSUNG line        (author ruling R2/R3: list for Aaron)

Outputs tools/reports/lyric_triage_<date>.{json,md}. With --apply, tier B
arrangements get the repeated sheet lines inserted (exact copies of lines that
already exist in that arrangement's sheet), written to the arrangement's OWN
sheet (see wop_sheet_edit.py); that part is run by wop_lyrics_ship.py.
"""
import argparse
import datetime
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wop_align_song as A  # noqa: E402
import wop_audit_sung as AU  # noqa: E402
import wop_validate_lyrics as V  # noqa: E402
from wop_lyrics_extract import extract_lines  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO / "tools" / "reports"
VALIDATED_STEMS = {"09_02_Established_in_Him_Contemporary_Christian",
                   "07_02_Promises_Kept_Contemporary_Christian"}
MAX_WINDOW = 10
REPEAT_RATIO = 0.72
# Canonical whisper hallucinations over silence/outros. A run whose whole text is one of these
# is tagged ARTIFACT, reported, and ignored for tiering (nothing else is ever ignored).
ARTIFACT_RE = re.compile(
    r"^(thank you( so much)? for watching[.!]*|thanks for watching[.!]*|please subscribe[.!]*|"
    r"transcribed by .*|subtitles? by .*|amara\.org.*)$", re.I)


def best_cached_words(stem):
    """medium if cached, else small (never triggers a transcription here)."""
    for m in ("medium", "small"):
        f = AU.WORD_CACHE / f"{stem}.{m}.json"
        if f.exists():
            return m, [tuple(x) for x in json.loads(f.read_text(encoding="utf-8"))]
    return None, None


def sheet_tokens(lines):
    out = []
    for i, line in enumerate(lines):
        toks = [A.normalize_token(w) for w in line.split()]
        out.append([t for t in toks if t])
    return out


def _near(t, vocab):
    """ASR tolerance: map a heard word to the closest sheet word (seeking -> seek, I'll -> ill ...)."""
    if t in vocab:
        return t
    best, br = t, 0.0
    for w in vocab:
        r = SequenceMatcher(None, t, w).ratio()
        pre = len(t) >= 5 and len(w) >= 4 and (t.startswith(w) or w.startswith(t))
        if (r >= 0.8 or pre) and r > br:
            best, br = w, r
    return best


def _best_window(h, per_line_tokens):
    """best (ratio, first_line, n_lines) contiguous sheet window for the heard tokens h, or None"""
    best = None
    n = len(per_line_tokens)
    for i in range(n):
        acc = []
        for L in range(1, MAX_WINDOW + 1):
            if i + L > n:
                break
            acc = acc + per_line_tokens[i + L - 1]
            if not (0.6 * len(h) <= len(acc) <= 1.6 * len(h)):
                continue
            sm = SequenceMatcher(None, h, acc, autojunk=False)
            r = sm.ratio()
            cover = sum(b.size for b in sm.get_matching_blocks()) / len(h)
            if r >= REPEAT_RATIO and cover >= (0.75 if len(h) <= 8 else 0.85) and (best is None or (r, L) > (best[0], best[2])):
                best = (r, i, L)
    return best


def classify_run(run_tokens, per_line_tokens):
    """-> dict(kind, lines(0-based, in sung order), ratio)

    REPEAT when the whole heard run matches ONE contiguous span of sheet lines, or when it splits at
    one point into two such spans (a chorus followed by a tag from elsewhere in the sheet).
    Anything else is NEW. Runs over 60 words are only tested as a single span."""
    vocab = {t for line in per_line_tokens for t in line}
    h = [_near(t, vocab) for t in run_tokens]
    w = _best_window(h, per_line_tokens)
    if w:
        return dict(kind="REPEAT", lines=list(range(w[1], w[1] + w[2])), ratio=round(w[0], 2))
    if len(h) <= 60:
        best = None
        for s in range(3, len(h) - 2):
            left = _best_window(h[:s], per_line_tokens)
            if not left:
                continue
            right = _best_window(h[s:], per_line_tokens)
            if not right:
                continue
            score = min(left[0], right[0])
            if best is None or score > best[0]:
                best = (score, left, right)
        if best:
            _, l, r = best
            return dict(kind="REPEAT", lines=list(range(l[1], l[1] + l[2])) + list(range(r[1], r[1] + r[2])),
                        ratio=round(best[0], 2))
    return dict(kind="NEW", lines=[], ratio=0.0)


def line_spans(lines, hyp):
    """per sheet line: (first matched heard start, last matched heard end) or None"""
    kt, lo = [], []
    for i, line in enumerate(lines):
        for w in line.split():
            t = A.normalize_token(w)
            if t:
                kt.append(t)
                lo.append(i)
    ht = [w[1] for w in hyp]
    sm = SequenceMatcher(a=kt, b=ht, autojunk=False)
    st = [None] * len(lines)
    en = [None] * len(lines)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            li = lo[a + k]
            s, e = hyp[b + k][2], hyp[b + k][3]
            st[li] = s if st[li] is None else min(st[li], s)
            en[li] = e if en[li] is None else max(en[li], e)
    return [(st[i], en[i]) if st[i] is not None else None for i in range(len(lines))]


def insert_position(spans, run_start):
    """0-based index of the sheet line after which a run starting at run_start is sung."""
    after = -1
    for i, sp in enumerate(spans):
        if sp is not None and sp[1] <= run_start + 0.6:
            after = i
    return after


def triage_one(a, lines, words=None):
    model, hyp = best_cached_words(a["stem"]) if words is None else words
    if hyp is None:
        return None
    r = AU.analyse(lines, hyp, None)
    ptoks = sheet_tokens(lines)
    spans = line_spans(lines, hyp)
    runs = []
    for u in r["unsheeted"]:
        toks = [A.normalize_token(w) for w in u["heard"].split()]
        toks = [t for t in toks if t]
        if ARTIFACT_RE.match(u["heard"].strip()):
            c = dict(kind="ARTIFACT", lines=[], ratio=0.0)
        else:
            c = classify_run(toks, ptoks)
        c.update(start=u["start"], end=u["end"], heard=u["heard"], near_line=u["near_line"],
                 after=insert_position(spans, u["start"]))
        runs.append(c)
    n_new = sum(1 for x in runs if x["kind"] == "NEW")
    n_rep = sum(1 for x in runs if x["kind"] == "REPEAT")
    n_art = sum(1 for x in runs if x["kind"] == "ARTIFACT")
    n_unsung = len(r["unsung"])
    if n_new or n_unsung:
        tier = "C"
        reason = f"{n_new} NEW run(s), {n_unsung} unsung line(s)"
    elif n_rep:
        tier = "B"
        reason = f"{n_rep} repeat run(s) to add"
    else:
        tier = "A"
        reason = "sung words match the sheet"
    return dict(stem=a["stem"], file=a["file"], title=a["title"], label=a["label"], model=model,
                direct_pct=r["direct_pct"], tier=tier, reason=reason, new=n_new, repeat=n_rep, artifact=n_art,
                unsung=r["unsung"], runs=runs, sheet=lines, is_alt=a["is_alt"],
                has_vtt=bool(a["lyrics_url"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    date = datetime.date.today().strftime("%Y%m%d")
    rows = []
    for a in V.collect_arrangements():
        lines = extract_lines(a["html"])
        if not lines or a["stem"] in VALIDATED_STEMS:
            continue
        if args.only and args.only not in a["stem"]:
            continue
        row = triage_one(a, lines)
        if row is None:
            print(f"no cached words for {a['stem']}")
            continue
        rows.append(row)
        print(f"triage {len(rows)} {a['stem'][:48]} tier {row['tier']}  ({row['reason']})", flush=True)
    order = {"C": 0, "B": 1, "A": 2}
    rows.sort(key=lambda r: (order[r["tier"]], r["direct_pct"]))
    suffix = f"_only-{args.only}" if args.only else ""
    (REPORT_DIR / f"lyric_triage_{date}{suffix}.json").write_text(
        json.dumps({"date": date, "rule": {"repeat_ratio": REPEAT_RATIO, "max_window_lines": MAX_WINDOW},
                    "rows": rows}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    cnt = {t: sum(1 for r in rows if r["tier"] == t) for t in "ABC"}
    md = [f"# Lyric triage - {date}", "",
          f"{len(rows)} arrangements: tier A {cnt['A']}, tier B {cnt['B']}, tier C {cnt['C']}.", "",
          "A = sung words match the sheet. B = only repeats of existing sheet lines (added automatically, ruling R1). "
          "C = new words or possibly skipped lines (listed for Aaron, rulings R2/R3).", "",
          "REPEAT rule: a 4+ word heard run with no sheet match is a REPEAT when its words match "
          f"(SequenceMatcher token ratio >= {REPEAT_RATIO}) a contiguous span of 1-{MAX_WINDOW} lines of the same "
          "arrangement's sheet; a longer run is consumed left to right by successive spans; otherwise NEW.", "",
          "| tier | direct % | new | repeat | unsung | model | arrangement | reason |", "|---|---:|---:|---:|---:|---|---|---|"]
    for r in rows:
        md.append(f"| {r['tier']} | {r['direct_pct']} | {r['new']} | {r['repeat']} | {len(r['unsung'])} | "
                  f"{r['model']} | `{r['stem']}` | {r['reason']} |")
    (REPORT_DIR / f"lyric_triage_{date}{suffix}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(cnt)


if __name__ == "__main__":
    main()
