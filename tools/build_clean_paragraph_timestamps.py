"""
Build a Format-C paragraph timestamp JSON for a CLEAN-PARAGRAPH chapter.

"Clean-paragraph" chapters keep their markdown body free of {% sentence %} /
{% para %} shortcodes. Instead, the Eleventy `paragraphSync` transform (see
.eleventy.js) stamps a sequential data-paragraph="N" hook onto every narrated
<p>/<li> inside <article class="chapter-content"> at BUILD time.

This script reads those data-paragraph hooks straight from the BUILT HTML — so
the p{N} keys it emits are guaranteed to match what audio-sync.js looks for in
the DOM. It NEVER touches audio: it only reads alignment data you already have.

INDEXING CONVENTION (kept in lock-step with the transform and NARRATION.md):
  * <p> and <li> inside the chapter prose article, document order, 0-based.
  * Headings (<h2>/<h3>), the <style> block, and non-prose UI are NOT indexed.

OUTPUT (Format C, consumed by AudioSync legacy init path):
  "p{N}": float   -- start time (seconds) of paragraph N in the narration file
  (No s{N} keys: clean chapters have no sentence spans; click-to-seek binds to
   the data-paragraph elements directly.)

USAGE
  # 1) Build the site first so the HTML carries data-paragraph hooks:
  npm run build

  # 2a) Emit an all-zero PLACEHOLDER (safe to ship; sync stays disabled until
  #     real values land — audio-sync.js has an all-zero guard):
  python tools/build_clean_paragraph_timestamps.py 01-introduction

  # 2b) Populate REAL times from an ElevenLabs character-alignment JSON for the
  #     single narration file:
  python tools/build_clean_paragraph_timestamps.py 01-introduction \
      --alignment path/to/alignment.json

The alignment JSON is the standard ElevenLabs shape:
  { "characters": [...],
    "character_start_times_seconds": [...],
    "character_end_times_seconds": [...] }
For a chunked narration, align each chunk separately and add the cumulative
chunk offsets exactly as tools/build_paragraph_timestamps.py does for Ch 9.
"""

import argparse
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── HTML extraction ─────────────────────────────────────────────────────────

def extract_paragraphs(built_html_path):
    """Return [(idx, plain_text), ...] for every data-paragraph element, in
    document order, scoped to the chapter prose article."""
    with open(built_html_path, "r", encoding="utf-8") as f:
        html = f.read()

    art = re.search(
        r'<article class="chapter-content"[^>]*>([\s\S]*?)</article>', html
    )
    if not art:
        raise SystemExit(f"No <article class=\"chapter-content\"> in {built_html_path}")
    inner = art.group(1)

    # <p ... data-paragraph="N">...</p>  /  <li ... data-paragraph="N">...</li>
    # <p>/<li> are not nested in their own kind in our content, so non-greedy
    # capture to the matching close tag is safe.
    pat = re.compile(
        r'<(p|li)\b[^>]*\bdata-paragraph="(\d+)"[^>]*>(.*?)</\1>',
        re.DOTALL,
    )
    out = []
    for tag, idx, body in pat.findall(inner):
        text = re.sub(r"<[^>]+>", " ", body)        # strip inner tags
        text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text) # strip entities
        text = re.sub(r"\s+", " ", text).strip()
        out.append((int(idx), text))

    out.sort(key=lambda t: t[0])
    return out


# ── Alignment helpers (mirror tools/build_paragraph_timestamps.py) ───────────

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def words_of(text):
    return normalize(text).split()


def alignment_to_word_times(alignment):
    chars  = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends   = alignment.get("character_end_times_seconds", [])

    words = []
    current_word = ""
    word_start = None
    word_end = None

    for i, ch in enumerate(chars):
        s = starts[i] if i < len(starts) else 0.0
        e = ends[i]   if i < len(ends)   else 0.0
        if ch in (" ", "\n", "\t"):
            if current_word.strip():
                words.append({"word": current_word.strip(),
                              "start": word_start, "end": word_end})
            current_word = ""
            word_start = None
        else:
            if word_start is None:
                word_start = s
            current_word += ch
            word_end = e

    if current_word.strip():
        words.append({"word": current_word.strip(),
                      "start": word_start, "end": word_end})
    return words


def find_block_start(block_text, word_times, search_from=0):
    """Find the start time of block_text's first words within word_times,
    advancing a pointer so successive paragraphs scan forward only."""
    block_words = words_of(block_text)
    if not block_words:
        t = word_times[search_from]["start"] if search_from < len(word_times) else 0.0
        return t, search_from

    first = block_words[0]
    check_len = min(3, len(block_words))
    limit = min(search_from + 120, len(word_times))

    for i in range(search_from, limit):
        if normalize(word_times[i]["word"]) == first:
            matches = sum(
                1 for k in range(check_len)
                if i + k < len(word_times) and k < len(block_words)
                and normalize(word_times[i + k]["word"]) == block_words[k]
            )
            if matches >= min(2, check_len):
                next_ptr = i + max(len(block_words) - 1, 1)
                return word_times[i]["start"], next_ptr

    t = word_times[search_from]["start"] if search_from < len(word_times) else 0.0
    return t, search_from + 1


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", help="chapter slug, e.g. 01-introduction")
    ap.add_argument("--alignment", help="ElevenLabs character-alignment JSON for "
                                        "the narration file. Omit for an all-zero "
                                        "placeholder.")
    ap.add_argument("--site", default=os.path.join(REPO, "_site"),
                    help="built site dir (default: ./_site)")
    args = ap.parse_args()

    built = os.path.join(args.site, "chapters", args.slug, "index.html")
    if not os.path.exists(built):
        raise SystemExit(f"Built HTML not found: {built}\nRun `npm run build` first.")

    paras = extract_paragraphs(built)
    if not paras:
        raise SystemExit("No data-paragraph elements found — is this a clean-"
                         "paragraph chapter that the paragraphSync transform ran on?")

    out = {}
    if args.alignment:
        with open(args.alignment, "r", encoding="utf-8") as f:
            alignment = json.load(f)
        word_times = alignment_to_word_times(alignment)
        ptr = 0
        for idx, text in paras:
            t, ptr = find_block_start(text, word_times, ptr)
            out[f"p{idx}"] = round(t, 3)
        # First paragraph anchored to 0.0 (ignore any pre-roll silence).
        if "p0" in out:
            out["p0"] = 0.0
        print(f"Populated {len(out)} paragraph timestamps from alignment.")
    else:
        for idx, _ in paras:
            out[f"p{idx}"] = 0.0
        print(f"Wrote {len(out)} placeholder (0.0) paragraph timestamps.")
        print("All-zero guard in audio-sync.js keeps sync disabled until real "
              "values land.")

    dest = os.path.join(REPO, "src", "_data", "timestamps", f"chapter-{args.slug}.json")
    # Stable p0..pN ordering
    ordered = {k: out[k] for k in sorted(out, key=lambda s: int(s[1:]))}
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2)
        f.write("\n")
    print(f"Saved -> {dest}")
    print(f"Paragraph count: {len(ordered)} (p0..p{len(ordered) - 1})")


if __name__ == "__main__":
    main()
