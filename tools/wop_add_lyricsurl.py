"""
WoP lyricsUrl injector — add `lyricsUrl: /assets/lyrics/<stem>.vtt` to every
source entry (chapter frontmatter + ministryMusic.json) that (a) has a
testimony mp3 file and (b) has a matching .vtt on disk under
src/assets/lyrics/. Idempotent — skips entries that already carry a lyricsUrl.

Preserves each source file's existing formatting:
  - Chapter .md / .njk : line-based regex insert (doesn't rewrite YAML)
  - ministryMusic.json : json load + json dump (2-space indent, matches
    original — verified against the shipped file).

Usage:
    python tools/wop_add_lyricsurl.py               # apply
    python tools/wop_add_lyricsurl.py --dry-run     # preview only
"""

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = REPO_ROOT / "src" / "chapters"
MINISTRY_PATH = REPO_ROOT / "src" / "_data" / "ministryMusic.json"
VTT_DIR = REPO_ROOT / "src" / "assets" / "lyrics"


# Match a YAML `file: "some.mp3"` line (either a normal mapping key or an
# `- file:` list-item form under `alternates:`). Capture:
#   - leading indent
#   - optional `-\s+` list prefix (its width shifts the effective key column)
#   - the mp3 filename
FILE_LINE = re.compile(
    r'^(?P<indent>[ \t]*)(?P<listpfx>-\s+)?file:\s*["\']?(?P<name>[^\s"\']+\.mp3)["\']?\s*$',
    re.MULTILINE,
)


def vtt_exists(mp3_name):
    return (VTT_DIR / (Path(mp3_name).stem + ".vtt")).exists()


def rewrite_yaml_frontmatter(text, dry_run):
    """
    Walk each 'file: X.mp3' line in text. If a matching .vtt exists and the
    testimony block doesn't already carry a lyricsUrl, insert a peer line at
    the same indent right after the file: line.

    "Testimony block" here = the ~10 lines following the file: line at the
    same or deeper indent, up to the next line dedented ≤ file-line indent.
    """
    lines = text.split("\n")
    additions = []      # list of (line index after which to insert, new_line)
    for m in FILE_LINE.finditer(text):
        line_start_idx = text.count("\n", 0, m.start())
        indent = m.group("indent")
        listpfx = m.group("listpfx") or ""
        # Effective column for peer keys: `- file:` puts `file:` `len(listpfx)`
        # columns further right than `indent`; a plain-key `file:` has listpfx="".
        peer_col = len(indent) + len(listpfx)
        name = m.group("name")
        stem = Path(name).stem
        if not vtt_exists(name):
            continue

        # Scan forward through this mapping's siblings. A row belongs to the
        # same mapping when its first non-whitespace column is >= peer_col
        # (and it is not the start of a new list item at this level).
        block_end = line_start_idx + 1
        while block_end < len(lines):
            row = lines[block_end]
            if not row.strip():
                block_end += 1
                continue
            leading = len(row) - len(row.lstrip(" \t"))
            if leading < peer_col:
                break
            # New list item at peer_col means we've exited into a sibling
            # entry — for `- file:` this signals the next alternate.
            if leading == peer_col - len(listpfx) and row.lstrip().startswith("- "):
                # (this row would open a NEW list item at THIS list's level)
                break
            block_end += 1

        block_lines = lines[line_start_idx: block_end]
        already = any(re.match(r"^[ \t]*lyricsUrl:", ln) for ln in block_lines)
        if already:
            continue
        peer_indent = " " * peer_col
        insertion = f"{peer_indent}lyricsUrl: /assets/lyrics/{stem}.vtt"
        additions.append((line_start_idx, insertion))

    if not additions:
        return text, 0

    # Apply insertions from the bottom up so indices stay valid.
    for idx, new_line in sorted(additions, key=lambda x: -x[0]):
        lines.insert(idx + 1, new_line)

    return "\n".join(lines), len(additions)


def process_chapter_file(path, dry_run):
    text = path.read_text(encoding="utf-8")
    new_text, n = rewrite_yaml_frontmatter(text, dry_run)
    if n and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return n


def process_ministry_json(dry_run):
    data = json.loads(MINISTRY_PATH.read_text(encoding="utf-8"))
    added = 0

    def maybe_add(entry):
        nonlocal added
        name = entry.get("file")
        if not name or not vtt_exists(name):
            return
        if entry.get("lyricsUrl"):
            return
        entry["lyricsUrl"] = f"/assets/lyrics/{Path(name).stem}.vtt"
        added += 1

    for item in data.get("collection", []):
        maybe_add(item)
        for alt in item.get("alternates", []) or []:
            maybe_add(alt)

    if added and not dry_run:
        MINISTRY_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total = 0
    files_touched = 0
    for path in sorted(CHAPTERS_DIR.glob("*.md")) + sorted(CHAPTERS_DIR.glob("*.njk")):
        if path.name.startswith("_"):
            continue
        n = process_chapter_file(path, args.dry_run)
        if n:
            files_touched += 1
            total += n
            print(f"  +{n:2d}  {path.relative_to(REPO_ROOT)}")

    n = process_ministry_json(args.dry_run)
    if n:
        files_touched += 1
        total += n
        print(f"  +{n:2d}  {MINISTRY_PATH.relative_to(REPO_ROOT)}")

    print("-" * 60)
    verb = "would add" if args.dry_run else "added"
    print(f"  {verb} {total} lyricsUrl line(s) across {files_touched} file(s)")


if __name__ == "__main__":
    main()
