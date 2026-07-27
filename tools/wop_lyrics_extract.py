"""
WoP Lyrics Extractor — formatted HTML lyrics → clean per-line plaintext.

Feeds the forced-aligner (aeneas / whisperX). One sung line per row of the
emitted .txt file so aeneas can produce line-level cue timings that map
1:1 back to VTT cues.

Sources (both mine the same shape — a Nunjucks-friendly HTML fragment):
    src/_data/ministryMusic.json   → item.lyrics per collection entry
    src/chapters/*.{md,njk}        → frontmatter `lyrics:` field alongside
                                     audio.testimony.file

Filter rules:
    <p class="section">…</p>   → NOT sung, dropped from aligner input
    <p class="verse">…</p>     → each <br>-separated line is one sung line
    <p class="chorus">…</p>    → each <br>-separated line is one sung line
    Whitespace collapsed; leading/trailing space stripped; blank lines dropped.
    HTML entities decoded; smart quotes preserved (aeneas + espeak handle
    them; whisperX doesn't care).

Output:
    tools/lyrics_txt/<mp3-basename>.txt   (one sung line per row)
    tools/lyrics_txt/manifest.json        (mp3 file → line count, source
                                           chapter/anthem label, whether
                                           any lyrics were found)

Usage:
    python tools/wop_lyrics_extract.py                 # write everything
    python tools/wop_lyrics_extract.py --dry-run       # preview
    python tools/wop_lyrics_extract.py --only <file>   # single mp3
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, NavigableString


REPO_ROOT = Path(__file__).resolve().parent.parent
MINISTRY_PATH = REPO_ROOT / "src" / "_data" / "ministryMusic.json"
CHAPTERS_DIR = REPO_ROOT / "src" / "chapters"
OUT_DIR = REPO_ROOT / "tools" / "lyrics_txt"
MANIFEST_PATH = OUT_DIR / "manifest.json"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def extract_lines(html):
    """Return a list of sung lines from a formatted-HTML lyrics fragment."""
    if not html or not html.strip():
        return []
    soup = BeautifulSoup(html, "html.parser")
    lines = []
    # Only .verse and .chorus paragraphs carry sung content. .section is a
    # non-sung label; anything without an explicit class we skip too, since
    # the two source formats we see always classify the sung blocks.
    for p in soup.find_all("p"):
        classes = p.get("class") or []
        if "section" in classes:
            continue
        if not ("verse" in classes or "chorus" in classes):
            continue
        buf = []
        _walk(p, buf, lines)
        _flush(buf, lines)
    return lines


def _walk(node, buf, lines):
    """Recursively walk a paragraph, flushing buf at every <br> at any depth."""
    for child in node.children:
        if isinstance(child, NavigableString):
            buf.append(str(child))
        elif getattr(child, "name", None) == "br":
            _flush(buf, lines)
        else:
            _walk(child, buf, lines)


def _flush(buf, lines):
    text = "".join(buf)
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        lines.append(text)
    buf.clear()


def load_frontmatter(path):
    """Return (frontmatter dict or None) from a WoP chapter .md or .njk file."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        print(f"  ! YAML error in {path.name}: {e}", file=sys.stderr)
        return None


def iter_ministry_entries():
    """Yield (mp3-file, label, formatted-html) from ministryMusic.json."""
    data = json.loads(MINISTRY_PATH.read_text(encoding="utf-8"))
    anthem_fallback = data.get("anthemLyrics", "")
    for item in data.get("collection", []):
        html = item.get("lyrics") or (anthem_fallback if item.get("hasLyrics") else "")
        yield (item["file"], f'Ministry — {item.get("title","?")}', html)
        # Alternates share the primary lyrics.
        for alt in item.get("alternates", []) or []:
            yield (alt["file"], f'Ministry — {item.get("title","?")} ({alt.get("label","alt")})', html)


def iter_chapter_entries():
    """Yield (mp3-file, label, formatted-html) from each chapter frontmatter."""
    for path in sorted(CHAPTERS_DIR.glob("*.md")) + sorted(CHAPTERS_DIR.glob("*.njk")):
        if path.name.startswith("_"):     # _template.md, _card-template.njk
            continue
        fm = load_frontmatter(path)
        if not fm:
            continue
        t = (fm.get("audio") or {}).get("testimony") or {}
        if not t.get("file"):
            continue
        html = fm.get("lyrics") or ""
        label = f'Ch {fm.get("chapter","?")} — {t.get("title", path.stem)}'
        yield (t["file"], label, html)
        for alt in t.get("alternates", []) or []:
            yield (alt["file"], f'{label} ({alt.get("label","alt")})', html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be written; touch nothing.")
    ap.add_argument("--only", metavar="FILE",
                    help="Extract just one mp3 filename (e.g. Panteles.mp3)")
    args = ap.parse_args()

    entries = list(iter_ministry_entries()) + list(iter_chapter_entries())
    if args.only:
        entries = [e for e in entries if e[0] == args.only]
        if not entries:
            sys.exit(f"No source entry found for --only {args.only!r}")

    if not args.dry_run:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {}
    seen_files = set()

    for mp3, label, html in entries:
        if mp3 in seen_files:
            # Alternates would overwrite with the same lyrics; skip duplicates.
            continue
        seen_files.add(mp3)
        lines = extract_lines(html)
        base = Path(mp3).stem
        out_path = OUT_DIR / f"{base}.txt"
        manifest[mp3] = {
            "source": label,
            "lines": len(lines),
            "txt": f"lyrics_txt/{base}.txt" if lines else None,
        }
        status = f'{len(lines):3d} lines' if lines else '  NO LYRICS'
        print(f'  {status}  {mp3}  ({label})')
        if lines and not args.dry_run:
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = len(manifest)
    with_lyrics = sum(1 for v in manifest.values() if v["lines"])
    print("-" * 72)
    print(f'  Entries : {total}    with-lyrics : {with_lyrics}')
    print(f'  Out dir : {OUT_DIR}')
    if not args.dry_run:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
