"""Text helpers shared by the adapters: HTML segmentation, encoding/footnote repair, normalization.

Normalization for phrase assertion reuses sjn_pipeline.textnorm (NFKC, quote/dash folding, casefold,
whitespace collapse; PDF soft-hyphen/ligature/line-break repairs)."""
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sjn_pipeline.scope import html_segments as _segments  # noqa: E402
from sjn_pipeline.textnorm import normalize, pdf_repair, phrase_word_count, contains  # noqa: E402

__all__ = ["segments", "fix_mojibake", "strip_footnote_digits", "clean", "sha", "normalize",
           "pdf_repair", "phrase_word_count", "contains", "join", "words", "has_greek", "has_polytonic", "punct_key",
           "nfc", "strip_foreign_parentheticals", "scrub_urls", "dehyphenate", "hyphenation_residue",
           "join_soft_hyphens", "strip_page_furniture", "page_furniture_lines", "repair_intraword_splits",
           "intraword_split_candidates"]

_SKIP_TAGS = {"sup", "script", "style", "noscript", "figcaption", "button", "form", "input", "select", "option"}


def fix_mojibake(text):
    """Repair UTF-8 bytes decoded as cp1252 ('â€™', 'Â ')."""
    if not text or not re.search(r"[ÂÃâ][\x80-\xbf€™œ‚„†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ\xa0-\xbf]", text):
        return text
    try:
        fixed = text.encode("cp1252", errors="ignore").decode("utf-8", errors="ignore")
        # only accept if it reduced the mojibake markers
        if fixed and len(re.findall(r"[ÂÃâ]", fixed)) < len(re.findall(r"[ÂÃâ]", text)):
            return fixed
    except Exception:
        pass
    return text


def strip_footnote_digits(text):
    """'them,1 who' -> 'them, who'; 'spirit,3 invisible,4' -> 'spirit, invisible,'. Only digits glued to
    a preceding letter or punctuation mark (never a space), one or two digits, followed by space/end."""
    return re.sub(r"(?<=[A-Za-z,;:.!?\)\]’'\"”])\d{1,2}(?=(\s|$|[,;:.]))", "", text)


def clean(text):
    t = text.replace(" ", " ").replace("\r", " ").replace("\n", " ")
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t


def join(parts):
    return clean(" ".join(p for p in parts if p and p.strip()))


def segments(html, skip=_SKIP_TAGS):
    """(tag, text) pairs of direct text in document order, mojibake repaired, junk tags dropped."""
    html = fix_mojibake(html)
    out = []
    for tag, text in _segments(html):
        if tag in skip:
            continue
        out.append((tag, text))
    return out


def sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def words(text):
    return [w for w in re.split(r"\s+", (text or "").strip()) if w]


_URL_TOKEN = re.compile(r"(?:<\s*)?(?:https?://|www\.)\S+(?:\s*>)?", re.I)


def scrub_urls(text):
    """Replace any URL token in a chunk's text with a neutral marker. Three corpus chunks carry links
    (a footnote URL in the Apology, a stray web-bot tag in Philaret Q.611, a bibliography URL in the
    ACNA catechism); an agent never sees a URL (guards.assert_no_urls), so the agent-visible text is
    scrubbed here. The stored chunk text and its hash are untouched; a phrase can never legitimately
    span a link, so the verbatim check is unaffected."""
    return _URL_TOKEN.sub("[link removed]", text or "")


# ---------------------------------------------------------------- punctuation-stripped comparison key
def punct_key(text):
    """NFKC, casefolded, every punctuation and symbol character (any quote or dash style) removed, whitespace
    collapsed. Nothing else: a different word, a different word order or a spelling variant is a different text.

    Two rules compare on this key and must compare alike: R6-4's one-text-one-slot guard (allocation.same_text_key)
    and R6-5/R6-10's phrase-level creed and definition resolution (registry.Registry.resolve_registered_phrase)."""
    import unicodedata
    t = unicodedata.normalize("NFKC", text or "").casefold()
    t = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- scripts / languages
_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_POLYTONIC = re.compile(r"[ἀ-῿]")


def has_greek(text):
    return bool(_GREEK.search(text or ""))


def has_polytonic(text):
    """True when the text carries Greek Extended (polytonic) code points — the accent forms that
    NFKC would fold to their monotonic look-alikes."""
    return bool(_POLYTONIC.search(text or ""))


def nfc(text):
    """Normalise to NFC exactly once, at fetch. Applied by the adapters that store Greek text
    (BSR-EO-12, the Crete parallel witness). The phrase check normalises both sides identically
    later, so a phrase cut from stored text always matches it; what must never happen is a
    second, different normalisation between fetch and check."""
    import unicodedata
    return unicodedata.normalize("NFC", text or "")


_PAREN = re.compile(r"\s*\(([^()]*)\)")


def strip_foreign_parentheticals(text, latin_markers=("in duabus naturis", "inconfuse", "immutabiliter")):
    """Remove parenthetical groups that carry Greek script (or the known Latin gloss of the
    Chalcedon clause) from an English sentence, so no chunk offered to an agent mixes languages.
    Returns (english_text, removed_groups). The removed groups are kept beside the chunk as a
    parallel witness; they never enter the citable text."""
    removed = []

    def repl(m):
        inner = m.group(1)
        if has_greek(inner) or any(k in inner.casefold() for k in latin_markers):
            removed.append(inner.strip())
            return ""
        return m.group(0)

    out = _PAREN.sub(repl, text or "")
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return clean(out), removed


# ---------------------------------------------------------------- hyphenation artifacts (2026-09-12)
# Line-break hyphenation carried into the fetched text breaks verbatim matching: the Thirty-Nine
# Articles page carries "ever- lasting" in its own HTML, the PCUSA and ROEA PDFs carry "na-\nture" and
# "heav-\nenly", and a locator that quotes "everlasting" is then refused as "not present verbatim"
# (cal-3, Q-341). A word split across a line break is joined here, at extraction, for every row.
#
# Decision per split `A- b` (hyphen, optional line break, lowercase continuation), using the whole
# document's own vocabulary as evidence:
#   1. `b` is a coordinating word ("and", "or", "et", …): a SUSPENDED hyphen ("wine- and beer-cellars",
#      "patres- et matresfamilias") — left alone.
#   2. the closed form "Ab" occurs elsewhere in the document — join without the hyphen ("everlasting").
#   3. the hyphenated compound "A-b" occurs elsewhere unbroken — the break fell on a real hyphen
#      ("life-\ncreating" → "life-creating"); the hyphen is kept and the break removed.
#   4. otherwise — join without the hyphen (line-break hyphenation is the overwhelmingly common case).
# Only a break at a line end (`-\n`) or the single-space residue of one (`- `) qualifies; a hyphen
# followed by a capital ("Thirty- Nine") or by punctuation is never touched.
_SUSPENDED_NEXT = {"and", "or", "nor", "et", "aut", "vel", "to", "the", "a", "an", "of", "as", "but", "und", "oder"}
_SPLIT = re.compile(r"(?<![\w-])([A-Za-z]{2,})[-‐‑]( ?[ \t]*\r?\n[ \t]*| )([a-z][A-Za-z]*)")


def _vocab(text):
    """Word forms of the document: closed words and hyphenated compounds, casefolded."""
    return set(w.casefold() for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", text or ""))


def dehyphenate(text, vocab_text=None, stats=None):
    """Join words split across a line break (see the note above). `vocab_text` supplies the evidence
    vocabulary (defaults to `text` itself); `stats`, if given, is a dict that receives counts per rule."""
    if not text:
        return text
    vocab = _vocab(vocab_text if vocab_text is not None else text)
    counts = stats if stats is not None else {}

    def repl(m):
        a, b = m.group(1), m.group(3)
        if b.casefold() in _SUSPENDED_NEXT:
            counts["suspended_kept"] = counts.get("suspended_kept", 0) + 1
            return m.group(0)
        closed, compound = (a + b).casefold(), f"{a}-{b}".casefold()
        if closed in vocab:
            counts["joined_closed"] = counts.get("joined_closed", 0) + 1
            return a + b
        if compound in vocab:
            counts["joined_compound"] = counts.get("joined_compound", 0) + 1
            return f"{a}-{b}"
        counts["joined_default"] = counts.get("joined_default", 0) + 1
        return a + b
    return _SPLIT.sub(repl, text)


def hyphenation_residue(text):
    """Remaining `word- word` splits (lowercase continuation) after extraction — reported, never silent."""
    return [m.group(0) for m in _SPLIT.finditer(text or "") if m.group(3).casefold() not in _SUSPENDED_NEXT]


# ---------------------------------------------------------------- page furniture and intra-word splits (2026-09-13)
# The Anglican packet showed two PDF defects that the line-break de-hyphenation above does not touch
# (Q-101, BSR-AN-05 Q.322: "cove nantal", and a running header "the ten commandments" spliced into the
# middle of a sentence). Both fail SILENTLY: a phrase that spans the splice is refused as "not present
# verbatim" with no rejection record, so the only place they show is a chunk read.
#
# 1a  Page furniture. A running header or footer is a short line that recurs at the same position
#     (the top or the bottom of the page) across many pages. It is removed BEFORE the pages are joined,
#     so it can never land mid-sentence. A line is furniture only when, digits folded, it occurs on at
#     least FURNITURE_MIN_PAGES pages in the same zone AND at least FURNITURE_MIN_SHARE of all its
#     full-line occurrences in the document are in that zone. The share test is what keeps prose out:
#     "Q." opens 13 pages of the Episcopal catechism but is a full line 124 times, "Amen." closes 18
#     pages of the BCP but occurs 85 times, so neither qualifies. A line is never removed merely
#     because it is short. Removed lines are reported (per document, with counts) — never silent.
# 1b  Intra-word splits. The ACNA PDF hyphenates at SOFT hyphens (U+00AD): "cove­\nnantal". The
#     old path stripped the soft hyphen after the line split and joined the two lines with a space.
#     join_soft_hyphens() joins a soft-hyphen line break at extraction, before any split. As a safety
#     net for splits with another cause, repair_intraword_splits() joins "a b" only where the closed
#     form "ab" occurs elsewhere in the document and NEITHER fragment occurs anywhere except inside
#     this very split — conservative by construction — and returns every join it made for the log.
FURNITURE_MIN_PAGES = 3
FURNITURE_MIN_SHARE = 0.75
FURNITURE_MAX_WORDS = 10
FURNITURE_ZONE = 3
FF = chr(12)                            # form feed: the page separator pdf_text() emits
NL = chr(10)                      # lines from the top / bottom of a page that count as the zone
_PROSE_OPENERS = {"or", "and", "but", "nor", "for", "so", "yet"}   # a line opening this way is prose, not furniture
_SOFT_HYPHEN_BREAK = re.compile("­[ \t]*\r?\n[ \t]*")


def join_soft_hyphens(text, stats=None):
    """Join a word split at a soft hyphen across a line break ("cove­\\nnantal" -> "covenantal"); a
    soft hyphen elsewhere (a discretionary break that was not taken) is simply removed."""
    if not text:
        return text
    counts = stats if stats is not None else {}
    n_break = len(_SOFT_HYPHEN_BREAK.findall(text))
    out = _SOFT_HYPHEN_BREAK.sub("", text)
    n_rest = out.count("­")
    out = out.replace("­", "")
    counts["soft_hyphen_breaks_joined"] = counts.get("soft_hyphen_breaks_joined", 0) + n_break
    counts["soft_hyphens_removed_midline"] = counts.get("soft_hyphens_removed_midline", 0) + n_rest
    return out


def _furniture_key(line):
    """The comparison form of a line: NBSP folded, casefolded, digit runs folded to '#'."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line.replace(" ", " ").strip().casefold()))


def _qualifies(key):
    if not key or key == "#":
        return True                     # a bare page number is always furniture
    words = key.split()
    if len(words) > FURNITURE_MAX_WORDS:
        return False
    if re.search(r"[.?!;:,]$", key):
        return False                    # a sentence or a clause, not a heading
    if words[0] in _PROSE_OPENERS:
        return False
    return True


def page_furniture_lines(pages):
    """Detect running headers / footers across `pages` (list of page texts). Returns
    ({"top": {key: n_pages}, "bottom": {key: n_pages}}, {key: total_full_line_count})."""
    total = {}
    zone = {"top": {}, "bottom": {}}
    for p in pages:
        lines = [l for l in (x.strip() for x in p.split("\n")) if l]
        keys = [_furniture_key(l) for l in lines]
        for k in keys:
            total[k] = total.get(k, 0) + 1
        for k in keys[:FURNITURE_ZONE]:
            zone["top"][k] = zone["top"].get(k, 0) + 1
        for k in keys[-FURNITURE_ZONE:]:
            zone["bottom"][k] = zone["bottom"].get(k, 0) + 1
    found = {"top": {}, "bottom": {}}
    for z in ("top", "bottom"):
        for k, n in zone[z].items():
            if n >= FURNITURE_MIN_PAGES and n / max(1, total[k]) >= FURNITURE_MIN_SHARE and _qualifies(k):
                found[z][k] = n
    return found, total


def strip_page_furniture(text, report=None, max_rounds=4):
    """Remove detected running headers / footers from the top / bottom zone of every page of a
    form-feed-separated PDF text. Only zone occurrences are removed: a heading that also stands in the
    body (the section title on its first page) stays there. Detection is repeated on the peeled pages
    (up to `max_rounds`) because furniture stacks: the PC(USA) Book of Confessions opens every
    Westminster page with six lines (section title, reference range, a four-line column header), and a
    single three-line zone would leave the last three spliced into the body. `report`, if given,
    receives {"top": {line: pages_removed}, "bottom": {...}, "lines_removed": n, "rounds": r}."""
    if not text:
        return text
    pages = text.split(FF)
    removed = {"top": {}, "bottom": {}, "lines_removed": 0, "rounds": 0}
    for _round in range(max_rounds):
        found, _ = page_furniture_lines(pages)
        if not found["top"] and not found["bottom"]:
            break
        out_pages, n_round = [], 0
        for p in pages:
            raw_lines = p.split(NL)
            idx = [i for i, l in enumerate(raw_lines) if l.strip()]     # the zone is counted on content lines, as in detection
            drop = set()
            for i in idx[:FURNITURE_ZONE]:
                k = _furniture_key(raw_lines[i])
                if k in found["top"]:
                    drop.add(i); removed["top"][k] = removed["top"].get(k, 0) + 1
            for i in idx[-FURNITURE_ZONE:]:
                k = _furniture_key(raw_lines[i])
                if k in found["bottom"] and i not in drop:
                    drop.add(i); removed["bottom"][k] = removed["bottom"].get(k, 0) + 1
            n_round += len(drop)
            out_pages.append(NL.join(l for i, l in enumerate(raw_lines) if i not in drop))
        removed["lines_removed"] += n_round
        removed["rounds"] += 1
        pages = out_pages
        if not n_round:
            break
    if report is not None:
        report.update(removed)
    return FF.join(pages)


_WORD = re.compile(r"[A-Za-z]+")
# Every adjacent pair is examined: `b` is captured in a lookahead so "the cove nant" yields both
# ("the", "cove") and ("cove", "nant") — a consuming pattern would swallow "the cove" and never see the split.
_SPLIT_PAIR = re.compile(r"(?<![A-Za-z-])([A-Za-z]{2,})(?= ([a-z]{2,})(?![A-Za-z-]))")
STEM_SUFFIX_MAX = 4                     # "cove nantal" extends the attested "cove nant" -> covenant by "al"


def intraword_split_candidates(text, vocab_text=None, corpus_vocab=None):
    """Conservative detection of "a b" pairs that are one word split by a space (the ACNA text layer
    prints "cove nant" six times and "cove nantal" once; neither is a line break). Evidence, all of it
    counted, none of it guessed:
      ATTESTED   the closed form "ab" is a word of the document (or of the wider ratified corpus,
                 `corpus_vocab`, a set of casefolded tokens) AND neither fragment is a word of the
                 document: every occurrence of `a` as a token is the left half of some adjacent pair,
                 and every occurrence of `b` is the right half of one.
      STEM       "ab" is not attested, but `a` is an established split fragment — it has at least two
                 ATTESTED joins with right halves b0 — and `b` extends one of those b0 by a short
                 suffix (≤ STEM_SUFFIX_MAX letters): "cove nantal" after "cove nant" -> "covenant".
    Returns [{"a", "b", "pairs", "evidence": "ATTESTED"|"STEM", "closed_form_count", "stem"}], casefolded."""
    src = vocab_text if vocab_text is not None else text
    counts = {}
    for t in _WORD.findall(src or ""):
        t = t.casefold()
        counts[t] = counts.get(t, 0) + 1
    pairs = {}
    for m in _SPLIT_PAIR.finditer(src or ""):
        k = (m.group(1).casefold(), m.group(2).casefold())
        pairs[k] = pairs.get(k, 0) + 1
    corpus_vocab = corpus_vocab or set()

    def attested_join(a, b):
        return counts.get(a + b, 0) >= 1 or (a + b) in corpus_vocab

    # Fragment evidence is counted over ATTESTED pairs only: "cove" is a fragment because every one of its
    # occurrences is the left half of "cove nant" (attested as "covenant"); "cove is quiet" would not do.
    att = {k: n for k, n in pairs.items() if attested_join(*k)}
    left_att, right_att = {}, {}
    for (a, b), n in att.items():
        left_att[a] = left_att.get(a, 0) + n
        right_att[b] = right_att.get(b, 0) + n
    # STEM candidates: `a` has attested joins with right halves b0, and `b` extends one of them by a short suffix
    stem = {}
    for (a, b), n in pairs.items():
        if (a, b) in att or a not in left_att or left_att[a] < 2:
            continue
        for b0 in sorted({b0 for (a0, b0) in att if a0 == a}, key=len, reverse=True):
            if b != b0 and b.startswith(b0) and 0 < len(b) - len(b0) <= STEM_SUFFIX_MAX:
                stem[(a, b)] = (n, a + b0)
                break
    left_stem, right_stem = {}, {}
    for (a, b), (n, _s) in stem.items():
        left_stem[a] = left_stem.get(a, 0) + n
        right_stem[b] = right_stem.get(b, 0) + n

    def fragment(a, b):
        return (counts.get(a, 0) == left_att.get(a, 0) + left_stem.get(a, 0)
                and counts.get(b, 0) == right_att.get(b, 0) + right_stem.get(b, 0))

    out = []
    for (a, b), n in att.items():
        if fragment(a, b):
            out.append({"a": a, "b": b, "pairs": n, "evidence": "ATTESTED", "closed_form_count": counts.get(a + b, 0),
                        "closed_form_in_corpus": (a + b) in corpus_vocab, "stem": None})
    attested_a = {o["a"] for o in out}
    for (a, b), (n, stem_word) in stem.items():
        if a in attested_a and fragment(a, b):
            out.append({"a": a, "b": b, "pairs": n, "evidence": "STEM", "closed_form_count": 0,
                        "closed_form_in_corpus": False, "stem": stem_word})
    return out


def repair_intraword_splits(text, vocab_text=None, joins=None, corpus_vocab=None):
    """Join the splits intraword_split_candidates() finds, preserving the first fragment's case.
    `joins`, if given, receives one record per join made: {"from": "cove nantal", "to": "covenantal",
    "evidence": "ATTESTED"|"STEM", ...}. Nothing is joined without that evidence."""
    if not text:
        return text
    cands = intraword_split_candidates(text, vocab_text, corpus_vocab)
    if not cands:
        return text
    by_pair = {(c["a"], c["b"]): c for c in cands}
    out, cursor = [], 0
    for m in _SPLIT_PAIR.finditer(text):
        if m.start() < cursor:
            continue                    # inside a pair already joined
        a, b = m.group(1), m.group(2)
        key = (a.casefold(), b.casefold())
        if key not in by_pair:
            continue
        end = m.end() + 1 + len(b)      # the space and the right fragment (in the lookahead, not consumed)
        out.append(text[cursor:m.start()]); out.append(a + b)
        cursor = end
        if joins is not None:
            c = by_pair[key]
            joins.append({"from": a + " " + b, "to": a + b, "evidence": c["evidence"], "pairs": c["pairs"],
                          "closed_form_count": c["closed_form_count"], "closed_form_in_corpus": c["closed_form_in_corpus"], "stem": c["stem"]})
    out.append(text[cursor:])
    return "".join(out)
