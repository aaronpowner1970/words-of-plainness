"""Text normalization for phrase-containment assertions.

Rule source: Citation Selection Rules 8/10/11 and Citation Phrase Targets
"Normalization" column: HTML→visible text; Unicode NFKC; casefold; normalize
whitespace; normalize curly quotes/apostrophes/dashes. PDF branch additionally
strips U+00AD, expands ﬁ/ﬂ ligatures (NFKC does this), and joins hyphenated
line breaks BEFORE the common normalization.
"""
import re
import unicodedata

_QUOTES = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "′": "'", "″": '"', "«": '"', "»": '"',
}
_DASHES = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-",
    "—": "-", "―": "-", "−": "-", "⁃": "-",
}
_TRANS = str.maketrans({**_QUOTES, **_DASHES, " ": " ", " ": " ", " ": " "})


def normalize(text: str) -> str:
    """Common normalization applied to both fetched text and quoted phrases."""
    if text is None:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.translate(_TRANS)
    t = t.casefold()
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pdf_repair(text: str) -> str:
    """PDF-specific repairs applied before normalize()."""
    if text is None:
        return ""
    t = text.replace("­", "")                # soft hyphens
    t = t.replace("ﬁ", "fi").replace("ﬂ", "fl")  # ligatures (NFKC also does this)
    t = t.replace("ﬀ", "ff").replace("ﬃ", "ffi").replace("ﬄ", "ffl")
    # join hyphenated line breaks: "eter-\nnal" -> "eternal" (only lowercase continuation)
    t = re.sub(r"(\w)-\s*\n\s*(?=[a-z])", r"\1", t)
    return t


def phrase_word_count(phrase: str) -> int:
    return len([w for w in re.split(r"\s+", (phrase or "").strip()) if w])


def contains(scoped_text: str, phrase: str) -> bool:
    return normalize(phrase) in normalize(scoped_text)


def style_flags(text: str):
    """Church style lint: flag 'LDS' and 'Mormon' outside permitted uses.
    Returns list of offending tokens (empty list when clean)."""
    if not text:
        return []
    flags = []
    if re.search(r"\bLDS\b", text):
        flags.append("LDS")
    # Permitted: 'Book of Mormon', 'Mormon 9:19' (scripture), the subtitle 'Mormon Christianity'
    for m in re.finditer(r"\bMormon\b", text):
        pre = text[max(0, m.start() - 8):m.start()]
        post = text[m.end():m.end() + 14]
        if pre.endswith("Book of ") or re.match(r"\s+\d", post) or post.startswith(" Christianity"):
            continue
        flags.append("Mormon")
        break
    return flags
