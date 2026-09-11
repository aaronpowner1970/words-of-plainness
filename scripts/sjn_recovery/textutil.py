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
           "pdf_repair", "phrase_word_count", "contains", "join", "words"]

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
