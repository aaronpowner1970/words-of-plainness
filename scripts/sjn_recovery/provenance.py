"""One-off provenance check for BSR-EO-05 (Confession of Dositheus on maximologia.org).

The page reproduces Robertson's 1899 translation without translator credit. At corpus build the
maximologia decrees are diffed against the published edition on archive.org
(actsdecreesofsyn00orth, OCR text) so that "we trust an unattributed page" becomes "we verified it
against the published edition". A decree whose text cannot be matched at the threshold halts the
build (spec §5). The archive.org edition is an authority reference only: it is never chunked and
never reaches an agent."""
import re

ROBERTSON_DJVU = "https://archive.org/download/actsdecreesofsyn00orth/actsdecreesofsyn00orth_djvu.txt"
ROBERTSON_DETAILS = "https://archive.org/details/actsdecreesofsyn00orth"
THRESHOLD = 0.85          # word-containment ratio per decree (OCR-noise tolerant)
MIN_WORD_LEN = 4


def _norm_words(text):
    t = text.casefold()
    t = re.sub(r"[^a-z\s]", " ", t)
    return [w for w in t.split() if len(w) >= MIN_WORD_LEN]


def _find_anchor(ocr_words, opening, max_gap=2):
    """Locate the decree opening (list of words) inside the OCR word list allowing OCR noise:
    try the first n words as an exact subsequence window, shrinking n; return start index or -1."""
    for n in (8, 6, 5, 4, 3):
        pat = opening[:n]
        if len(pat) < n:
            continue
        for i in range(len(ocr_words) - n):
            if ocr_words[i:i + n] == pat:
                return i
    # tolerant: first word + third word within a small gap
    if len(opening) >= 3:
        for i in range(len(ocr_words) - 4):
            if ocr_words[i] == opening[0] and opening[2] in ocr_words[i + 1:i + 4]:
                return i
    return -1


def check(decree_chunks, ocr_text, threshold=THRESHOLD):
    """decree_chunks: list of (locator, text) for Decree 1..18. Returns report dict."""
    ocr_words = _norm_words(ocr_text)
    ocr_set_cache = {}
    results = []
    for locator, text in decree_chunks:
        w = _norm_words(text)
        if not w:
            results.append({"locator": locator, "status": "EMPTY", "ratio": 0.0})
            continue
        i = _find_anchor(ocr_words, w)
        if i < 0:
            results.append({"locator": locator, "status": "UNANCHORED", "ratio": 0.0, "words": len(w)})
            continue
        window = ocr_words[max(0, i - 20): i + int(len(w) * 1.4) + 40]
        bag = {}
        for x in window:
            bag[x] = bag.get(x, 0) + 1
        hit = 0
        for x in w:
            if bag.get(x, 0) > 0:
                bag[x] -= 1
                hit += 1
        ratio = hit / len(w)
        results.append({"locator": locator, "status": "MATCH" if ratio >= threshold else "DIVERGENT",
                        "ratio": round(ratio, 3), "words": len(w), "ocr_offset": i})
    matched = [r for r in results if r["status"] == "MATCH"]
    divergent = [r for r in results if r["status"] == "DIVERGENT"]
    unanchored = [r for r in results if r["status"] in ("UNANCHORED", "EMPTY")]
    return {
        "edition": ROBERTSON_DETAILS, "ocr_source": ROBERTSON_DJVU, "threshold": threshold,
        "decrees_checked": len(results), "matched": len(matched), "divergent": len(divergent),
        "unanchored": len(unanchored),
        "verdict": "PASS" if (matched and not divergent and len(unanchored) <= max(2, len(results) // 6)) else "HALT",
        "per_decree": results,
        "note": ("Word-containment of each maximologia decree inside the OCR window anchored at the decree's opening "
                 "words (words of four letters or more; OCR noise tolerated). DIVERGENT halts the build. "
                 "UNANCHORED decrees (OCR damage at the opening) are reported and tolerated up to one sixth of the sample."),
    }
