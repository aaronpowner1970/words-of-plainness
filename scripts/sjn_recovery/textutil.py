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
           "pdf_repair", "phrase_word_count", "contains", "join", "words", "has_greek", "has_polytonic",
           "nfc", "strip_foreign_parentheticals", "scrub_urls"]

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
