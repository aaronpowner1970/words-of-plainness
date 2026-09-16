#!/usr/bin/env python3
"""
aoid_extract_bodies.py — one-shot refactor helper (kept for the record).

Lifts each Articles-of-Interfaith-Discipleship body out of
src/pages/articles.njk into src/_includes/aoid/aNN.njk, then rewrites
articles.njk to {% include %} the extracted file.

The extracted block is exactly:

    <h2 class="article-title">…</h2>
    <div class="article-body">
        …paragraphs, .article-rjw, .article-footnote…
    </div>

The banner() call stays in articles.njk (the video pages use the banner
image in their entry dialog instead, so it is not part of the shared body).

Byte-fidelity rule: the include file holds the block verbatim, including the
leading indentation of the <h2> line, and the {% include %} tag sits at
column 0. Rendered output is therefore byte-identical to the original.

Run once from the repo root:  python tools/aoid_extract_bodies.py
Idempotent: refuses to run a second time (nothing left to extract).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pages" / "articles.njk"
OUT_DIR = ROOT / "src" / "_includes" / "aoid"

SECTION_RE = re.compile(
    r'<section class="article-section" id="(?P<slug>[^"]+)" data-audio="AP_(?P<code>A\d{2})_[^"]*">'
)


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    if "aoid/a01.njk" in text:
        print("articles.njk already includes aoid/*.njk — nothing to do.")
        return 0

    lines = text.split("\n")
    out_lines = []
    i = 0
    extracted = 0

    while i < len(lines):
        line = lines[i]
        m = SECTION_RE.search(line)
        if not m:
            out_lines.append(line)
            i += 1
            continue

        code = m.group("code")
        out_lines.append(line)
        i += 1

        # Carry the banner() call (and any blank lines) through untouched.
        while i < len(lines) and '<h2 class="article-title">' not in lines[i]:
            out_lines.append(lines[i])
            i += 1
        if i >= len(lines):
            print(f"!! {code}: no article-title found", file=sys.stderr)
            return 1

        start = i
        # Body runs to the line immediately before </section>.
        end = i
        while end < len(lines) and "</section>" not in lines[end]:
            end += 1
        if end >= len(lines):
            print(f"!! {code}: no </section> found", file=sys.stderr)
            return 1

        block = "\n".join(lines[start:end])
        (OUT_DIR / f"{code.lower()}.njk").write_text(block, encoding="utf-8", newline="\n")
        out_lines.append(f'{{% include "aoid/{code.lower()}.njk" %}}')
        extracted += 1
        i = end

    SRC.write_text("\n".join(out_lines), encoding="utf-8", newline="\n")
    print(f"extracted {extracted} article bodies -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
