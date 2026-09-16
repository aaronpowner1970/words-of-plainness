#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aoid_build_timing.py — word-level timing for the AoID video-reading pages.

THE AUTHORITY RULE
    The article text in src/_includes/aoid/aNN.njk is the authority for
    wording. The SRT files supply timing ONLY. SRT text is never emitted and
    never displayed: the readings match the articles nearly word for word but
    the cues break mid-sentence and carry typos (A1 "orderand").

WHAT IT DOES
    1. Tokenises the spoken prose of each article body — the <p> children of
       .article-body that are not .article-footnote; the .article-rjw block
       and the footnotes are not read aloud and are excluded.
    2. Tokenises the SRT and gives every SRT word a time by interpolating
       within its cue in proportion to character position.
    3. Aligns the two token streams with difflib.SequenceMatcher and carries
       the SRT times onto the article's own words. Article words the reading
       skipped or garbled are interpolated between their matched neighbours.
    4. Emits src/_data/aoid_video_timing.json and a per-article alignment
       report at tools/reports/aoid_alignment_report.md.

HARD STOP
    Exits non-zero, writing no JSON, if any article falls below MIN_MATCH
    word match or if any data-span cannot be timed.

    python tools/aoid_build_timing.py
"""

import difflib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BODY_DIR = ROOT / "src" / "_includes" / "aoid"
SRT_DIR = Path(r"C:\Users\aaron\Documents\wop-scratch\AoID videos SRT files")
OUT_JSON = ROOT / "src" / "_data" / "aoid_video_timing.json"
OUT_REPORT = ROOT / "tools" / "reports" / "aoid_alignment_report.md"

MIN_MATCH = 0.97

# A03 has no reading video — its page is the full film at /creation/.
YOUTUBE = {
    "A01": "v3ZJY3CT0Rc", "A02": "Q05joaJNmro", "A04": "ZSo_cd5cgw8",
    "A05": "_HWBD4A2Hyk", "A06": "MKLA4kTXnJI", "A07": "30_eLVjsDD4",
    "A08": "jsv2f8j8Suw", "A09": "s6Xz4Hg2aSQ", "A10": "InIH8qFgFOA",
    "A11": "PNZ8vCzZJGg", "A12": "MbyLnbVlaIw", "A13": "Wv9hBC9MjaY",
}

# SRT file names are NOT zero-padded.
def srt_path(code):
    return SRT_DIR / f"A{int(code[1:])}_Avatar_Reading.srt"

# ── Tokeniser ───────────────────────────────────────────────────────────────
# ONE definition of a word, shared verbatim with js/aoid-video.js. Letters,
# digits and apostrophes; every other character is a separator. Punctuation,
# em-dashes, daggers and entity differences therefore cannot desynchronise the
# browser's token stream from this one.
WORD_RE = re.compile(r"[0-9A-Za-z\u00C0-\u024F'\u2019]+")


def norm(tok):
    return tok.lower().replace("\u2019", "'")


def tokenize(text):
    """-> [(token, start_char, end_char)]"""
    return [(m.group(0), m.start(), m.end()) for m in WORD_RE.finditer(text)]


# ── Article body reader ─────────────────────────────────────────────────────
class BodyReader(HTMLParser):
    """
    Pulls the spoken prose out of an aNN.njk body, tracking which [data-span]
    each word falls inside.

    Mirrors the browser's error recovery for the two malformed-nesting patterns
    in the source (A04's <strong>We <span>receive</strong> …</span> and the
    </p></span> tails in A12/A13): </p> closes any spans still open, and a
    stray </span> with nothing open is ignored. The result matches what the
    HTML parser actually builds, which is what the page will highlight.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = 0
        self.body_depth = 0
        self.div_depth = 0
        self.in_p = False
        self.skip_p = False
        self.span_stack = []
        self.chunks = []          # (text, span_id)
        self.paragraphs = []      # [[(text, span_id), …]]
        self._cur = []

    # -- helpers
    def _cls(self, attrs):
        return dict(attrs).get("class", "") or ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div":
            self.div_depth += 1
            if not self.in_body and "article-body" in self._cls(attrs):
                self.in_body = True
                self.body_depth = self.div_depth
            return
        if not self.in_body:
            return
        if tag == "p" and self.div_depth == self.body_depth:
            # Direct child of .article-body. Footnotes are not read aloud.
            self.in_p = True
            self.skip_p = "article-footnote" in self._cls(attrs)
            self._cur = []
            return
        if tag == "span":
            self.span_stack.append(a.get("data-span"))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag == "div":
            if self.in_body and self.div_depth == self.body_depth:
                self.in_body = False
            self.div_depth -= 1
            return
        if not self.in_body:
            return
        if tag == "p" and self.in_p:
            if not self.skip_p and self._cur:
                self.paragraphs.append(self._cur)
            self.in_p = False
            self._cur = []
            self.span_stack = []          # browser closes open spans at </p>
            return
        if tag == "span" and self.span_stack:
            self.span_stack.pop()

    def handle_data(self, data):
        if not (self.in_body and self.in_p and not self.skip_p):
            return
        sid = None
        for s in reversed(self.span_stack):
            if s:
                sid = s
                break
        self._cur.append((data, sid))


SENT_SPLIT = re.compile(
    r'(?<=[.!?])["\u201D\u2019\u2020\u2021]*\s+(?=[\u201C"\u2018\u2019A-Z0-9])'
)


def read_article(code):
    """
    -> (plain_text, [ {tok, n, a, b, span} … ], [ (tok_start, tok_end) sentences ])
    """
    r = BodyReader()
    r.feed((BODY_DIR / f"{code.lower()}.njk").read_text(encoding="utf-8"))

    plain_parts, words, para_bounds = [], [], []
    cursor = 0
    for para in r.paragraphs:
        p_start_tok = len(words)
        p_start_char = cursor
        for text, sid in para:
            for tok, a, b in tokenize(text):
                words.append({"tok": tok, "n": norm(tok),
                              "a": cursor + a, "b": cursor + b, "span": sid})
            cursor += len(text)
            plain_parts.append(text)
        plain_parts.append("\n\n")
        para_bounds.append((p_start_tok, len(words), p_start_char, cursor))
        cursor += 2

    plain = "".join(plain_parts)

    # Sentence units, segmented per paragraph so a sentence never spans one.
    sentences = []
    for t0, t1, c0, c1 in para_bounds:
        if t1 <= t0:
            continue
        seg = plain[c0:c1]
        cuts = [c0] + [c0 + m.end() for m in SENT_SPLIT.finditer(seg)] + [c1]
        for i in range(len(cuts) - 1):
            lo, hi = cuts[i], cuts[i + 1]
            s0 = next((k for k in range(t0, t1) if words[k]["a"] >= lo), None)
            if s0 is None:
                continue
            s1 = max((k for k in range(t0, t1) if words[k]["b"] <= hi), default=None)
            if s1 is None or s1 < s0:
                continue
            if sentences and sentences[-1][1] > s0:
                continue
            sentences.append((s0, s1 + 1))
    return plain, words, sentences


# ── SRT reader ──────────────────────────────────────────────────────────────
TS = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{1,3})")


def secs(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def read_srt(path):
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    words = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        m = None
        for i, line in enumerate(lines):
            m = TS.search(line)
            if m:
                body = " ".join(lines[i + 1:])
                break
        if not m or not body.strip():
            continue
        st = secs(*m.groups()[:4])
        en = secs(*m.groups()[4:])
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()
        span = max(en - st, 0.001)
        L = max(len(body), 1)
        for tok, a, b in tokenize(body):
            # Interpolate inside the cue in proportion to character position.
            words.append({"tok": tok, "n": norm(tok),
                          "s": st + span * (a / L), "e": st + span * (b / L)})
    return words


# ── Alignment ───────────────────────────────────────────────────────────────
def align(code):
    plain, awords, sentences = read_article(code)
    swords = read_srt(srt_path(code))
    sm = difflib.SequenceMatcher(
        None, [w["n"] for w in awords], [w["n"] for w in swords], autojunk=False)

    times = [None] * len(awords)
    matched = 0
    issues = []

    def ctx(i, lo, hi):
        lo = max(0, lo - 4)
        hi = min(len(awords), hi + 4)
        return " ".join(awords[k]["tok"] for k in range(lo, hi))

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (swords[j1 + k]["s"], swords[j1 + k]["e"])
            matched += i2 - i1
        else:
            art = [awords[k]["tok"] for k in range(i1, i2)]
            red = [swords[k]["tok"] for k in range(j1, j2)]
            issues.append({
                "kind": tag, "at": i1,
                "article": " ".join(art) or "(nothing)",
                "reading": " ".join(red) or "(nothing)",
                "context": ctx(i1, i1, i2 if i2 > i1 else i1 + 1),
            })

    # Article words the reading skipped or garbled: interpolate between the
    # nearest timed neighbours so no word is left without a clock.
    for i in range(len(times)):
        if times[i] is not None:
            continue
        lo = next((k for k in range(i - 1, -1, -1) if times[k]), None)
        hi = next((k for k in range(i + 1, len(times)) if times[k]), None)
        if lo is None and hi is None:
            times[i] = (0.0, 0.0)
        elif lo is None:
            times[i] = (times[hi][0], times[hi][0])
        elif hi is None:
            times[i] = (times[lo][1], times[lo][1])
        else:
            a, b = times[lo][1], times[hi][0]
            gap = next((k for k in range(i, len(times)) if times[k]), len(times)) - lo
            step = (b - a) / max(gap, 1)
            off = i - lo
            times[i] = (a + step * (off - 1), a + step * off)

    pct = matched / len(awords) if awords else 0.0

    sents = [{"i": n, "start": round(times[s0][0], 2), "end": round(times[s1 - 1][1], 2),
              "w0": s0, "w1": s1}
             for n, (s0, s1) in enumerate(sentences)]

    spans, missing = {}, []
    seen = []
    for k, w in enumerate(awords):
        if w["span"] and w["span"] not in spans:
            spans[w["span"]] = round(times[k][0], 2)
            seen.append(w["span"])
    # Every [data-span] in the spoken prose must have received a time.
    for w in awords:
        if w["span"] and w["span"] not in spans:
            missing.append(w["span"])

    data = {
        "youtube": YOUTUBE[code],
        "tokens": len(awords),
        "match": round(pct, 4),
        "sentences": sents,
        "words": [round(t[0], 2) for t in times],
        "spans": spans,
    }
    return data, pct, issues, missing, len(swords)


def main():
    codes = sorted(YOUTUBE)
    out, report, failures = {}, [], []

    report.append("# AoID reading alignment report\n")
    report.append(
        "Article text is the authority for wording; the SRT supplies timing only. "
        "Every row below is a place where the reading and the article text differ — "
        "the article wording is what the page displays in every case.\n")
    report.append(f"Threshold: {MIN_MATCH:.0%} word match per article.\n")

    for code in codes:
        p = srt_path(code)
        if not p.exists():
            failures.append(f"{code}: SRT missing at {p}")
            continue
        data, pct, issues, missing, nsrt = align(code)
        out[code] = data
        flag = "PASS" if pct >= MIN_MATCH else "**FAIL**"
        if pct < MIN_MATCH:
            failures.append(f"{code}: match {pct:.2%} below {MIN_MATCH:.0%}")
        if missing:
            failures.append(f"{code}: untimed data-spans {sorted(set(missing))}")

        report.append(f"\n## {code} — {pct:.2%} {flag}\n")
        report.append(
            f"- article words: {data['tokens']} · reading words: {nsrt} · "
            f"sentences: {len(data['sentences'])} · timed spans: {len(data['spans'])}")
        report.append(f"- first word at {data['words'][0]:.2f}s · "
                      f"last sentence ends {data['sentences'][-1]['end']:.2f}s")
        if missing:
            report.append(f"- **untimed spans: {sorted(set(missing))}**")
        if not issues:
            report.append("\nNo differences — the reading matches the article word for word.")
        else:
            report.append(f"\n{len(issues)} difference(s):\n")
            report.append("| # | kind | article text | reading said | context (article) |")
            report.append("|---|------|--------------|--------------|-------------------|")
            for n, it in enumerate(issues, 1):
                report.append(
                    f"| {n} | {it['kind']} | `{it['article']}` | `{it['reading']}` "
                    f"| …{it['context']}… |")

    OUT_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(f"report -> {OUT_REPORT.relative_to(ROOT)}")

    if failures:
        print("\nHARD STOP — no timing JSON written:", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        return 1

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"timing -> {OUT_JSON.relative_to(ROOT)}  ({len(out)} articles)")
    for code in codes:
        print(f"  {code}  {out[code]['match']:.2%}  "
              f"{out[code]['tokens']} words  {len(out[code]['spans'])} spans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
