"""
WoP Sung-Content Audit - G4b of the Musical Testimony Lyric-Sync Standard.

G4 only proves the timing file fits the sheet. G4b asks the other question:
is what is SUNG what is WRITTEN? For every arrangement with a lyric sheet it
transcribes the recording (whisper, word timestamps), aligns the heard words
to the arrangement's resolved sheet (lyricsSameAs followed), and records:

    direct_pct   share of sheet lines with at least one heard word matched
    UNSHEETED    runs of 4+ consecutive heard words with no sheet match
                 (extra lines, repeated choruses, changed endings)
    UNSUNG       sheet lines with no heard match (lines the recording may skip)
    SUBSTITUTION sheet words vs heard words that differ by more than ASR noise
                 (raw diff reported, NEVER corrected; the author decides)

Runs the "small" model first; re-runs with "medium" only for arrangements
showing 3+ UNSHEETED runs or under 85% direct match (cap: --max-medium, 15).
Where a medium run exists it is the result of record; both are kept.

Proposed status (a proposal, never applied automatically):
    hold-candidate  3+ UNSHEETED runs, or direct match < 85%, or 20+ cues
                    under 1.0 s together with overlaps in the VTT
    review          any UNSHEETED run, UNSUNG line or non-noise substitution
    clean           none of the above

Nothing here edits lyric wording or the hold list.

Outputs:
    tools/reports/lyric_audit_<YYYYMMDD>.json   full results (committed)
    tools/reports/lyric_audit_<YYYYMMDD>.md     summary table, worst first
    tools/.mp3_cache/words/<stem>.<model>.json  whisper word cache (ignored)

Usage:
    python tools/wop_audit_sung.py [--only <stem-substring>] [--max-medium 15]
                                   [--report-only]
"""

import argparse
import datetime
import json
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wop_align_song as A  # noqa: E402  (fetch_mp3, normalize_token, cache)
import wop_validate_lyrics as V  # noqa: E402
from wop_lyrics_extract import extract_lines  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "tools" / "reports"
WORD_CACHE = A.CACHE_ROOT / "words"

MIN_RUN = 4
NOISE_RATIO = 0.7
FUNCTION_WORDS = {"a", "the", "and", "in", "of", "to", "or", "oh", "for", "all", "my",
                  "our", "his", "her", "he", "she", "it", "is", "i", "we", "you", "on",
                  "an", "as", "at", "that", "this", "but", "so", "with", "me"}

_models = {}


def heard_words(stem, model_name):
    """[(raw, token, start, end)] from whisper, cached on disk."""
    WORD_CACHE.mkdir(parents=True, exist_ok=True)
    cf = WORD_CACHE / f"{stem}.{model_name}.json"
    if cf.exists():
        return [tuple(x) for x in json.loads(cf.read_text(encoding="utf-8"))]
    import whisper
    mp3 = A.fetch_mp3(stem + ".mp3")
    if model_name not in _models:
        _models[model_name] = whisper.load_model(model_name)
    res = _models[model_name].transcribe(
        str(mp3), language="en", word_timestamps=True, fp16=False,
        condition_on_previous_text=True, verbose=False)
    words = []
    for seg in res["segments"]:
        for w in seg.get("words", []) or []:
            raw = (w.get("word") or "").strip()
            tok = A.normalize_token(raw)
            if tok:
                words.append((raw, tok, float(w["start"]), float(w["end"])))
    cf.write_text(json.dumps(words), encoding="utf-8")
    return words


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def analyse(lines, hyp, vtt_cues):
    kt, lo = [], []
    for i, line in enumerate(lines):
        for w in line.split():
            t = A.normalize_token(w)
            if t:
                kt.append(t)
                lo.append(i)
    ht = [w[1] for w in hyp]
    sm = SequenceMatcher(a=kt, b=ht, autojunk=False)
    per = [0] * len(lines)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            per[lo[a + k]] += 1
    direct = sum(1 for x in per if x)

    def line_time(i):
        """Expected time of sheet line i (0-based): VTT cue if counts agree,
        else the neighbouring heard-matched lines."""
        if vtt_cues and len(vtt_cues) == len(lines):
            return vtt_cues[i]["start"]
        return None

    # heard time at the matched boundary, for interpolation of UNSUNG lines
    line_hyp_time = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            line_hyp_time.setdefault(lo[a + k], hyp[b + k][2])

    unsheeted, subs = [], []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        hyp_n = b2 - b1
        sheet_t = kt[a1:a2]
        line_no = (lo[a1] + 1) if a1 < len(lo) else len(lines)
        if hyp_n >= MIN_RUN:
            unsheeted.append(dict(
                start=round(hyp[b1][2], 2), end=round(hyp[b2 - 1][3], 2),
                words=hyp_n, heard=" ".join(w[0] for w in hyp[b1:b2]),
                sheet_near=" ".join(sheet_t)[:140], near_line=line_no))
        elif hyp_n >= 1 and sheet_t:
            heard_t = " ".join(ht[b1:b2])
            sheet_s = " ".join(sheet_t)
            ratio = SequenceMatcher(None, sheet_s.replace(" ", ""), heard_t.replace(" ", "")).ratio()
            fn_only = (len(sheet_t) <= 2 and hyp_n <= 2 and
                       all(t in FUNCTION_WORDS for t in sheet_t + ht[b1:b2]))
            noise = ratio >= NOISE_RATIO or fn_only
            subs.append(dict(line=line_no, t=round(hyp[b1][2], 2),
                             sheet=" ".join(lines[lo[a1]].split()) if a1 < len(lo) else sheet_s,
                             sheet_words=sheet_s, heard=" ".join(w[0] for w in hyp[b1:b2]),
                             ratio=round(ratio, 2), noise=noise))
        elif hyp_n >= 1:
            pass  # 1-3 stray heard words with no sheet counterpart: ASR noise, not reported

    unsung = []
    for i, n in enumerate(per):
        if n == 0:
            t = line_time(i)
            if t is None:
                prev = max((j for j in line_hyp_time if j < i), default=None)
                nxt = min((j for j in line_hyp_time if j > i), default=None)
                t = line_hyp_time.get(prev) if prev is not None else None
                if t is None and nxt is not None:
                    t = max(0.0, line_hyp_time[nxt] - 4.0)
            unsung.append(dict(line=i + 1, text=lines[i], expected=round(t, 2) if t is not None else None))
    return dict(direct=direct, sheet_lines=len(lines), direct_pct=round(100.0 * direct / max(1, len(lines)), 1),
                heard_words=len(hyp), unsheeted=unsheeted, unsung=unsung, substitutions=subs)


def vtt_stats(a):
    if not a["lyrics_url"]:
        return dict(short=0, overlaps=0, has_vtt=False)
    p = REPO_ROOT / "src" / a["lyrics_url"].lstrip("/")
    if not p.exists():
        return dict(short=0, overlaps=0, has_vtt=False)
    c = V.parse_vtt(p)
    short = sum(1 for x in c if 0 < x["end"] - x["start"] < V.MIN_CUE)
    ovl = sum(1 for i in range(len(c) - 1) if c[i + 1]["start"] < c[i]["end"] - 1e-6)
    return dict(short=short, overlaps=ovl, has_vtt=True)


def propose(r):
    n_un = len(r["unsheeted"])
    if n_un >= 3 or r["direct_pct"] < 85 or (r["vtt"]["short"] >= 20 and r["vtt"]["overlaps"] > 0):
        return "hold-candidate"
    real_subs = [s for s in r["substitutions"] if not s["noise"]]
    if n_un or r["unsung"] or real_subs:
        return "review"
    return "clean"


def rank(r):
    return (0 if r["proposed_status"] == "hold-candidate" else 1 if r["proposed_status"] == "review" else 2,
            r["direct_pct"], -len(r["unsheeted"]))


def write_reports(results, skipped_medium, date):
    jpath = REPORT_DIR / f"lyric_audit_{date}.json"
    jpath.write_text(json.dumps({"date": date, "skipped_medium": skipped_medium,
                                 "arrangements": results}, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    counts = {k: sum(1 for r in results if r["proposed_status"] == k)
              for k in ("hold-candidate", "review", "clean")}
    md = [f"# Sung-content audit (G4b) - {date}", "",
          f"Arrangements audited: {len(results)} - hold-candidate {counts['hold-candidate']}, "
          f"review {counts['review']}, clean {counts['clean']}. Models: small for all; medium re-run "
          f"for {sum(1 for r in results if r.get('medium_run'))} (result of record where present).", "",
          "Proposals only: nothing is added to the hold list and no wording is changed. "
          "Cut-offs: hold-candidate = 3+ unsheeted runs, or direct match under 85%, or 20+ cues under 1.0 s with overlaps.", ""]
    if skipped_medium:
        md += ["Medium re-runs skipped (cap reached): " + ", ".join(skipped_medium), ""]
    md += ["| proposed status | direct % | unsheeted runs | unsung lines | substitutions | short cues / overlaps | model | arrangement |",
           "|---|---:|---:|---:|---:|---|---|---|"]
    for r in results:
        real = sum(1 for s in r["substitutions"] if not s["noise"])
        md.append(f"| {r['proposed_status']} | {r['direct_pct']} | {len(r['unsheeted'])} | {len(r['unsung'])} | "
                  f"{real} | {r['vtt']['short']} / {r['vtt']['overlaps']} | {r['model']} | `{r['stem']}` |")
    (REPORT_DIR / f"lyric_audit_{date}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return jpath


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="audit only stems containing this text")
    ap.add_argument("--max-medium", type=int, default=15)
    ap.add_argument("--report-only", action="store_true",
                    help="use cached whisper words only; fail if one is missing")
    args = ap.parse_args()
    date = datetime.date.today().strftime("%Y%m%d")

    arrs = [a for a in V.collect_arrangements()]
    work = []
    for a in arrs:
        lines = extract_lines(a["html"])
        if not lines:
            print(f"skip (no lyrics): {a['file']}")
            continue
        if args.only and args.only not in a["stem"]:
            continue
        work.append((a, lines))

    results = {}
    total = len(work)
    for n, (a, lines) in enumerate(work, 1):
        t0 = time.time()
        hyp = heard_words(a["stem"], "small")
        vp = REPO_ROOT / "src" / a["lyrics_url"].lstrip("/") if a["lyrics_url"] else None
        cues = V.parse_vtt(vp) if vp and vp.exists() else None
        r = analyse(lines, hyp, cues)
        r.update(stem=a["stem"], file=a["file"], title=a["title"], label=a["label"], source=a["source"],
                 is_alt=a["is_alt"], model="small", medium_run=False, vtt=vtt_stats(a), sheet=lines)
        r["small"] = {k: r[k] for k in ("direct_pct", "unsheeted", "unsung", "substitutions")}
        results[a["stem"]] = (r, cues)
        print(f"audit {n}/{total} {a['stem'][:48]}  direct {r['direct_pct']}%  "
              f"unsheeted {len(r['unsheeted'])}  unsung {len(r['unsung'])}  ({time.time() - t0:.0f}s)", flush=True)

    # medium re-runs, worst first, capped
    cand = [s for s, (r, _) in results.items() if len(r["unsheeted"]) >= 3 or r["direct_pct"] < 85]
    cand.sort(key=lambda s: (results[s][0]["direct_pct"], -len(results[s][0]["unsheeted"])))
    skipped = cand[args.max_medium:]
    for k, stem in enumerate(cand[:args.max_medium], 1):
        r, cues = results[stem]
        t0 = time.time()
        hyp = heard_words(stem, "medium")
        m = analyse(r["sheet"], hyp, cues)
        print(f"medium {k}/{min(len(cand), args.max_medium)} {stem[:48]}  direct {m['direct_pct']}%  "
              f"unsheeted {len(m['unsheeted'])}  ({time.time() - t0:.0f}s)", flush=True)
        r.update({k2: m[k2] for k2 in ("direct", "direct_pct", "heard_words", "unsheeted", "unsung", "substitutions")})
        r["model"] = "medium"
        r["medium_run"] = True
    out = []
    for s, (r, _) in results.items():
        r["proposed_status"] = propose(r)
        out.append(r)
    out.sort(key=rank)
    p = write_reports(out, skipped, date)
    print(f"wrote {p}")
    print({k: sum(1 for r in out if r['proposed_status'] == k) for k in ("hold-candidate", "review", "clean")})
    if skipped:
        print("medium skipped:", skipped)


if __name__ == "__main__":
    main()
