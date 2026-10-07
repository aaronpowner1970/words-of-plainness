"""
Sheet-editing helpers shared by wop_lyrics_apply_validated.py and
wop_triage_lyrics.py (--apply).

A lyric sheet lives as HTML (section/verse/chorus/bridge paragraphs) in one of:
  - a chapter's frontmatter `lyrics: |` block (the PRIMARY arrangement's sheet),
  - an alternate's own `lyrics: |` block inside audio.testimony.alternates[],
  - src/_data/ministryMusic.json (item.lyrics / alt.lyrics / anthemLyrics).

Functions here edit the HTML while keeping its paragraph structure, and write
it back to the right place. They never invent wording: lines are either kept,
replaced by author-supplied text (VALIDATED files), or copied from lines that
already exist in the same arrangement's sheet (author ruling R1, repeats).
"""
import html as htmlmod
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wop_lyrics_extract import extract_lines  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
P_RE = re.compile(r'(<p class="([^"]*)">)(.*?)(</p>)', re.S)
BR_RE = re.compile(r'<br\s*/?>\s*', re.I)


def _plain(fragment):
    t = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", htmlmod.unescape(t)).strip()


def parse(html):
    """-> (pre, [paragraph dict], post). paragraph: cls, open, close, frags(list of raw)"""
    paras, pos, pieces = [], 0, []
    for m in P_RE.finditer(html):
        pieces.append(html[pos:m.start()])
        cls = m.group(2)
        frags = BR_RE.split(m.group(3).strip()) if "section" not in cls.split() else None
        paras.append(dict(cls=cls, open=m.group(1), close=m.group(4), raw=m.group(3), frags=frags))
        pos = m.end()
    pieces.append(html[pos:])
    return pieces, paras


def render(pieces, paras):
    out = [pieces[0]]
    for i, p in enumerate(paras):
        if p["frags"] is None:
            out.append(p["open"] + p["raw"] + p["close"])
        else:
            out.append(p["open"] + "<br>\n".join(f for f in p["frags"]) + p["close"])
        out.append(pieces[i + 1])
    return "".join(out)


def sung_index(paras):
    """flat list of (para_idx, frag_idx, text) in sung order (section paragraphs skipped)."""
    out = []
    for pi, p in enumerate(paras):
        if p["frags"] is None:
            continue
        for fi, f in enumerate(p["frags"]):
            t = _plain(f)
            if t:
                out.append((pi, fi, t))
    return out


def checked_parse(html):
    pieces, paras = parse(html)
    flat = [t for _, _, t in sung_index(paras)]
    ref = extract_lines(html)
    if flat != ref:
        raise ValueError("sheet HTML is not safely editable (paragraph parse != extractor)")
    return pieces, paras


def _esc(t):
    return htmlmod.escape(t, quote=False)


def apply_lines(old_html, new_lines):
    """Make the sheet's sung lines equal new_lines, keeping structure.
    Returns new html (unchanged string if already equal)."""
    pieces, paras = checked_parse(old_html)
    idx = sung_index(paras)
    old = [t for _, _, t in idx]
    if old == list(new_lines):
        return old_html
    sm = SequenceMatcher(None, [_norm(t) for t in old], [_norm(t) for t in new_lines], autojunk=False)
    # build edits against (para, frag) positions; apply from the end
    ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
    for tag, i1, i2, j1, j2 in reversed(ops):
        new_chunk = [_esc(t) for t in new_lines[j1:j2]]
        if tag in ("replace", "delete"):
            # replace in place where possible
            common = min(i2 - i1, j2 - j1) if tag == "replace" else 0
            for k in range(common):
                pi, fi, _ = idx[i1 + k]
                paras[pi]["frags"][fi] = new_chunk[k]
            extra_new = new_chunk[common:]
            dele = list(range(i1 + common, i2))
            for k in reversed(dele):
                pi, fi, _ = idx[k]
                del paras[pi]["frags"][fi]
            if extra_new:
                anchor = idx[i1 + common - 1] if common else (idx[i2 - 1] if i2 > i1 else None)
                _insert_after(paras, idx, i1 + common - 1 if common else i1 - 1, extra_new)
        elif tag == "insert":
            _insert_after(paras, idx, i1 - 1, new_chunk)
    out = render(pieces, paras)
    if extract_lines(out) != list(new_lines):
        raise ValueError("apply_lines: result does not equal requested lines")
    return out


def _norm(t):
    return re.sub(r"\s+", " ", t).strip()


def _insert_after(paras, idx, k, escaped_lines):
    """Insert fragments after sung line k (0-based; -1 = before first)."""
    if k < 0:
        pi, fi, _ = idx[0]
        paras[pi]["frags"][fi:fi] = escaped_lines
        return
    pi, fi, _ = idx[k]
    paras[pi]["frags"][fi + 1:fi + 1] = escaped_lines


def insert_repeats(old_html, repeats):
    """repeats: list of (after_line_idx, [source line idx...]) with 0-based indices
    into the CURRENT sung lines. Source lines are copied verbatim (as plain text
    of existing lines). Applied from the bottom up. Each repeat becomes its own
    paragraph (class of the source lines' paragraph) so the sheet stays readable.
    """
    pieces, paras = checked_parse(old_html)
    idx = sung_index(paras)
    texts = [t for _, _, t in idx]
    for after, src in sorted(repeats, key=lambda r: -r[0]):
        chunk = [_esc(texts[s]) for s in src]
        spi = idx[src[0]][0]
        cls = paras[spi]["cls"].split()[0] if paras[spi]["cls"] else "chorus"
        pi, fi, _ = idx[after]
        p = paras[pi]
        if fi == len(p["frags"]) - 1 or all(not _plain(f) for f in p["frags"][fi + 1:]):
            newp = dict(cls=cls, open=f'<p class="{cls}">', close="</p>", raw="", frags=chunk)
            paras.insert(pi + 1, newp)
            pieces.insert(pi + 1, "\n\n" + (" " * 0))
        else:
            p["frags"][fi + 1:fi + 1] = chunk
        idx = sung_index(paras)  # indices shift, but we go bottom-up so earlier ones are stable
    out = render(pieces, paras)
    return out


# ---------------------------------------------------------------- write-back

def _fm_bounds(text):
    lines = text.split("\n")
    assert lines[0].startswith("---")
    end = next(i for i in range(1, len(lines)) if lines[i].rstrip("\r") == "---")
    return lines, end


def _block_lines(html, indent):
    pad = " " * indent
    return [pad + ln if ln.strip() else "" for ln in html.strip("\n").split("\n")]


def set_chapter_sheet(path, file, html, primary_file):
    """Write html as the `lyrics: |` of the arrangement `file` in chapter `path`.
    Primary -> top-level `lyrics: |`. Alternate -> own `lyrics: |` inside its entry
    (lyricsSameAs removed)."""
    p = Path(path)
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    lines, end = _fm_bounds(text)
    if file == primary_file:
        i = next(k for k in range(end) if lines[k].startswith("lyrics: |"))
        j = i + 1
        while j < end and (lines[j].startswith(" ") or not lines[j].strip()):
            j += 1
        while j > i + 1 and not lines[j - 1].strip():
            j -= 1
        lines[i + 1:j] = _block_lines(html, 2)
    else:
        i = next(k for k in range(end) if re.match(r'^\s*-\s+file:\s*"?' + re.escape(file) + r'"?\s*$', lines[k]))
        dash_indent = len(lines[i]) - len(lines[i].lstrip())
        key_indent = dash_indent + 2
        j = i + 1
        while j < end and (not lines[j].strip() or (len(lines[j]) - len(lines[j].lstrip())) >= key_indent):
            j += 1
        while j > i + 1 and not lines[j - 1].strip():
            j -= 1
        entry = lines[i + 1:j]
        # drop lyricsSameAs and any existing own lyrics block
        kept, k = [], 0
        while k < len(entry):
            ln = entry[k]
            if re.match(r"^\s*lyricsSameAs:", ln):
                k += 1
                continue
            if re.match(r"^\s*lyrics:\s*\|", ln):
                k += 1
                while k < len(entry) and (not entry[k].strip() or (len(entry[k]) - len(entry[k].lstrip())) > key_indent):
                    k += 1
                continue
            kept.append(ln)
            k += 1
        # insert after lyricsUrl (or at top)
        pos = next((q + 1 for q, ln in enumerate(kept) if re.match(r"^\s*lyricsUrl:", ln)), 0)
        kept[pos:pos] = [" " * key_indent + "lyrics: |"] + _block_lines(html, key_indent + 2)
        lines[i + 1:j] = kept
    out = "\n".join(lines)
    if crlf:
        out = out.replace("\n", "\r\n")
    p.write_bytes(out.encode("utf-8"))


def set_ministry_sheet(file, html):
    path = REPO / "src" / "_data" / "ministryMusic.json"
    raw = path.read_bytes().decode("utf-8")
    data = json.loads(raw)
    done = False
    for item in data["collection"]:
        if item["file"] == file:
            item["lyrics"] = html
            done = True
        for alt in item.get("alternates", []) or []:
            if alt["file"] == file:
                alt["lyrics"] = html
                alt.pop("lyricsSameAs", None)
                done = True
    assert done
    crlf = "\r\n" in raw
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if crlf:
        out = out.replace("\n", "\r\n")
    path.write_bytes(out.encode("utf-8"))


def ensure_lyrics_url(path, file, primary_file, url):
    """Make sure the arrangement's frontmatter entry carries lyricsUrl: <url>."""
    p = Path(path)
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    lines = raw.replace("\r\n", "\n").split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].rstrip("\r") == "---")
    i = next(k for k in range(end) if re.match(r'^\s*(-\s+)?file:\s*"?' + re.escape(file) + r'"?\s*$', lines[k]))
    indent = len(lines[i]) - len(lines[i].lstrip())
    key_indent = indent + 2 if lines[i].lstrip().startswith("-") else indent
    j = i + 1
    while j < end:
        ln = lines[j]
        if ln.strip():
            ind = len(ln) - len(ln.lstrip())
            if ind < key_indent or re.match(r"^\s*alternates:", ln) or ln.lstrip().startswith("- "):
                break
        j += 1
    for k in range(i + 1, j):
        if re.match(r"^\s*lyricsUrl:", lines[k]):
            lines[k] = " " * key_indent + "lyricsUrl: " + url
            break
    else:
        lines.insert(i + 1, " " * key_indent + "lyricsUrl: " + url)
    out = "\n".join(lines)
    p.write_bytes((out.replace("\n", "\r\n") if crlf else out).encode("utf-8"))


def ensure_ministry_lyrics_url(file, url):
    path = REPO / "src" / "_data" / "ministryMusic.json"
    raw = path.read_bytes().decode("utf-8")
    data = json.loads(raw)
    for item in data["collection"]:
        for e in [item] + (item.get("alternates") or []):
            if e["file"] == file:
                e["lyricsUrl"] = url
    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_bytes((out.replace("\n", "\r\n") if "\r\n" in raw else out).encode("utf-8"))
