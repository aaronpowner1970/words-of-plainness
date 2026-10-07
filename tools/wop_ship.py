"""
Shared "ship an arrangement" steps for wop_lyrics_apply_validated.py and
wop_lyrics_ship.py.

    arrangement(stem)              the collected arrangement dict (V.collect_arrangements)
    save_own_sheet(arr, html)      write html as that arrangement's OWN sheet; if the arrangement
                                   is a primary that others inherit via lyricsSameAs, those
                                   dependants first receive an explicit copy of the OLD sheet,
                                   so no other arrangement's sheet changes
    align_attach(arr, lines)       align (base -> small -> medium, first with >= 90% lines matched
                                   directly), write the VTT, validate (G4), attach on pass, else
                                   restore the old VTT and keep the candidate in
                                   tools/lyrics_candidates/

Nothing here writes wording of its own.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wop_align_song as A  # noqa: E402
import wop_audit_sung as AU  # noqa: E402
import wop_sheet_edit as SE  # noqa: E402
import wop_validate_lyrics as V  # noqa: E402
from wop_lyrics_extract import extract_lines  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CAND = REPO / "tools" / "lyrics_candidates"
LYRICS_DIR = REPO / "src" / "assets" / "lyrics"
TXT_DIR = REPO / "tools" / "lyrics_txt"
MODELS = ("base", "small", "medium")


def all_arrangements():
    return V.collect_arrangements()


def arrangement(stem):
    for a in all_arrangements():
        if a["stem"] == stem:
            return a
    raise KeyError(stem)


def save_own_sheet(arr, html):
    """Give `arr` its own sheet = html. Dependants of a primary keep the old sheet."""
    arrs = all_arrangements()
    is_ministry = "chapter_path" not in arr
    if not is_ministry and not arr["is_alt"]:
        old = arr["html"]
        for d in arrs:
            if d["is_alt"] and d["same_as"] == arr["stem"] and not d["own_html"] and d.get("chapter_path") == arr["chapter_path"]:
                SE.set_chapter_sheet(d["chapter_path"], d["file"], old, arr["file"])
    if is_ministry:
        SE.set_ministry_sheet(arr["file"], html)
    else:
        SE.set_chapter_sheet(arr["chapter_path"], arr["file"], html, arr["file"] if not arr["is_alt"] else arr["primary_stem"] + ".mp3")
    TXT_DIR.mkdir(exist_ok=True)
    (TXT_DIR / f"{arr['stem']}.txt").write_bytes(("\n".join(extract_lines(html)) + "\n").encode("utf-8"))


def _words(stem, model):
    return AU.heard_words(stem, model)


def pick_alignment(stem, lines):
    """-> (model, spans, direct_pct) using the first model with >= 90% direct, else the best."""
    best = None
    for m in MODELS:
        f = AU.WORD_CACHE / f"{stem}.{m}.json"
        if not f.exists() and m == "medium":
            continue            # never start a slow medium run just for alignment
        hyp = _words(stem, m)
        r = AU.analyse(lines, hyp, None)
        spans = A.align_lines_to_words(lines, [(w[1], w[2], w[3]) for w in hyp])
        cand = (m, spans, r["direct_pct"])
        if best is None or cand[2] > best[2]:
            best = cand
        if r["direct_pct"] >= 90:
            return cand
    return best


def align_attach(arr, lines, label=""):
    """Align + validate + attach/candidate. Returns a result dict."""
    stem = arr["stem"]
    model, spans, direct = pick_alignment(stem, lines)
    vtt = LYRICS_DIR / f"{stem}.vtt"
    backup = vtt.read_bytes() if vtt.exists() else None
    A.write_vtt(spans, lines, vtt)
    a2 = arrangement(stem)
    a2["lyrics_url"] = f"/assets/lyrics/{stem}.vtt"
    a2["html"] = a2["html"]
    res = V.validate(a2)
    res_out = dict(stem=stem, model=model, direct_pct=direct, status=res["status"], problems=res["problems"],
                   cues=res.get("cues"), sheet_lines=res["sheet_lines"])
    if direct < 90 or res["status"] == "fail":
        CAND.mkdir(exist_ok=True)
        shutil.copyfile(vtt, CAND / f"{stem}.{model}.vtt")
        if backup is None:
            vtt.unlink()
        else:
            vtt.write_bytes(backup)
        res_out["attached"] = False
        return res_out
    url = f"/assets/lyrics/{stem}.vtt"
    if "chapter_path" in arr:
        SE.ensure_lyrics_url(arr["chapter_path"], arr["file"], arr["primary_stem"] + ".mp3", url)
    else:
        SE.ensure_ministry_lyrics_url(arr["file"], url)
    res_out["attached"] = True
    return res_out
