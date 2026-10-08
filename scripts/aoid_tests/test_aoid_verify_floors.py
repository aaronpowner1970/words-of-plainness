"""Tests for scripts/aoid-verify-floors.js (the AoID floor-transfer check, codex A4(a), A4(d)).

Every test runs the script on temporary copies of the ledger and the apparatus data, kept outside
the repo (pytest tmp_path). Tests that need a real ratified floor point --root at the repo so the
ledger's floor_document paths resolve to the real documents under data-sources/aoid/floors/; the
real ledger and the real apparatusData.json are never written.

Run: python -m pytest scripts/aoid_tests
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "aoid-verify-floors.js"
FLOORS = "data-sources/aoid/floors/"
STAGE1 = FLOORS + "WoP_AOID2_ScopeNotes_Stage1_A02_A04_A06_A11_Ratified_20261002.md"
G_DOC = FLOORS + "WoP_AOID2_ScopeNotes_A04_A05_Draft_20260922.md"

FLOOR = "The Article confesses only what Psalm 1 confesses: the one who delights in the law is blessed. This is the floor."
SECTION = "## Z1. Test floor\n\n**Panel comment (the floor), ratified:**\n\n> " + FLOOR + "\n\nWhy this floor.\n"


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def sha(s):
    return hashlib.sha256(norm(s).encode("utf-8")).hexdigest()


def run(tmp_path, entries, apparatus, docs=None, root=None, extra=()):
    """Write a ledger and apparatus under tmp_path, run the check, return (code, stdout, stderr)."""
    root = Path(root) if root else tmp_path
    for name, text in (docs or {}).items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text("scored:\n" + entries + "\npending_floors: []\n", encoding="utf-8")
    app = tmp_path / "apparatus.json"
    app.write_text(json.dumps(apparatus), encoding="utf-8")
    p = subprocess.run(
        ["node", str(SCRIPT), "--root", str(root), "--ledger", str(ledger), "--apparatus", str(app), *extra],
        capture_output=True, text=True, encoding="utf-8",
    )
    return p.returncode, p.stdout, p.stderr


def entry(item="Z1", span="A01.s1", heading="Z1. Test floor", doc="floor.md", sha256="", anchor=None):
    s = f'  - item: {item}\n    floor_document: {doc}\n    floor_heading: "{heading}"\n'
    if anchor is not None:
        s += f"    floor_anchor: {json.dumps(anchor)}\n"
    s += f"    span: {span}\n    floor_sha256: \"{sha256}\"\n"
    return s


def states(out):
    """{(item, span): state} read from the report."""
    found, item = {}, None
    for line in out.splitlines():
        m = re.match(r"^  (\S+): (TRANSFERRED|FAILED|PENDING)$", line)
        if m:
            item, state = m.groups()
            found[(item, None)] = state
            continue
        m = re.match(r"^  (\S+): \d+ spans$", line)
        if m:
            item = m.group(1)
            continue
        m = re.match(r"^      (A\d\d\.s\d+|none): (TRANSFERRED|FAILED|PENDING)\b", line)
        if m and item:
            found[(item, m.group(1))] = m.group(2)
    return found


def single(out, item):
    return states(out)[(item, None)]


APP_OK = {"A01": {"s1": {"panel_comment": FLOOR}}}


# ---------------------------------------------------------------- the six 30 Sep failure routes + control

def test_control_matching_comment_transfers(tmp_path):
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), APP_OK, {"floor.md": SECTION})
    assert single(out, "Z1") == "TRANSFERRED" and code == 0


def test_control_messy_wrapping_still_transfers(tmp_path):
    wrapped = "## Z1. Test floor\n\n**Panel comment (the floor), ratified:**\n\n> The Article confesses only what\n>   Psalm 1 confesses:   the one who delights\n> in the law is blessed.\n> This is the floor.\n"
    messy = "The Article  confesses only what Psalm 1\tconfesses: the one who delights in the law\n is blessed.   This is the floor.  "
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), {"A01": {"s1": {"panel_comment": messy}}}, {"floor.md": wrapped})
    assert single(out, "Z1") == "TRANSFERRED" and code == 0


def test_route1_span_named_but_absent(tmp_path):
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), {"A01": {"s2": {"panel_comment": FLOOR}}}, {"floor.md": SECTION})
    assert single(out, "Z1") == "FAILED" and "does not exist" in out and code == 1


def test_route2_panel_comment_one_word_changed(tmp_path):
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), {"A01": {"s1": {"panel_comment": FLOOR.replace("blessed", "happy")}}}, {"floor.md": SECTION})
    assert single(out, "Z1") == "FAILED" and "opening paragraph differs from floor" in out and code == 1


def test_route3_recorded_hash_altered(tmp_path):
    bad = sha(FLOOR)[:-1] + ("0" if sha(FLOOR)[-1] != "0" else "1")
    code, out, _ = run(tmp_path, entry(sha256=bad), APP_OK, {"floor.md": SECTION})
    assert single(out, "Z1") == "FAILED" and "changed without a ruling" in out and code == 1


def test_route4_empty_panel_comment(tmp_path):
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), {"A01": {"s1": {"panel_comment": "  "}}}, {"floor.md": SECTION})
    assert single(out, "Z1") == "FAILED" and "no panel_comment" in out and code == 1


def test_route5_floor_heading_misspelled(tmp_path):
    code, out, err = run(tmp_path, entry(heading="Z1. Test flor", sha256=sha(FLOOR)), APP_OK, {"floor.md": SECTION})
    assert single(out, "Z1") == "FAILED" and "heading not found" in out and "LEDGER / FLOOR PROBLEMS" in err and code == 1


def test_route6_unrecorded_hash(tmp_path):
    code, out, _ = run(tmp_path, entry(sha256=""), APP_OK, {"floor.md": SECTION})
    assert single(out, "Z1") == "FAILED" and "not recorded" in out and code == 1


# ---------------------------------------------------------------- headings and anchors

def test_heading_levels_2_3_4_and_section_end(tmp_path):
    for hashes in ("##", "###", "####"):
        doc = f"# Doc\n\n{hashes} Z1. Test floor\n\n**Panel comment (the floor):**\n\n> {FLOOR}\n\n{hashes} Next\n\n> other\n"
        code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), APP_OK, {"floor.md": doc})
        assert single(out, "Z1") == "TRANSFERRED", hashes
    # a deeper heading does not end the section; a same-level heading does
    deeper = f"### Z1. Test floor\n\n**Panel comment (the floor):**\n\n> {FLOOR}\n\n#### Sub\n\ntext\n"
    assert single(run(tmp_path, entry(sha256=sha(FLOOR)), APP_OK, {"floor.md": deeper})[1], "Z1") == "TRANSFERRED"
    # a label line that sits after a same-level heading is outside the section
    outside = f"### Z1. Test floor\n\nno label here\n\n### Other\n\n**Panel comment (the floor):**\n\n> {FLOOR}\n"
    assert single(run(tmp_path, entry(sha256=sha(FLOOR)), APP_OK, {"floor.md": outside})[1], "Z1") == "FAILED"


ANCHOR_DOC = (
    "### Z1. Test floor\n\nOld text.\n\n> OLD FLOOR WORDING\n\n**Amended by Aaron 2 Oct:**\n\n> " + FLOOR + "\n> and more.\n\nTail.\n"
)


def test_anchor_selects_first_blockquote_after_it(tmp_path):
    want = FLOOR + " and more."
    app = {"A01": {"s1": {"panel_comment": want}}}
    code, out, _ = run(tmp_path, entry(anchor="**Amended by", sha256=sha(want)), app, {"floor.md": ANCHOR_DOC})
    assert single(out, "Z1") == "TRANSFERRED" and code == 0


def test_anchor_missing_fails(tmp_path):
    code, out, err = run(tmp_path, entry(anchor="**No such line", sha256=sha(FLOOR)), APP_OK, {"floor.md": ANCHOR_DOC})
    assert single(out, "Z1") == "FAILED" and "floor_anchor not found" in out and code == 1


def test_anchor_on_two_lines_fails(tmp_path):
    doc = ANCHOR_DOC + "\n**Amended by someone else:**\n\n> x\n"
    code, out, err = run(tmp_path, entry(anchor="**Amended by", sha256=sha(FLOOR)), APP_OK, {"floor.md": doc})
    assert single(out, "Z1") == "FAILED" and "2 lines" in out and code == 1


def test_no_anchor_keeps_label_rule(tmp_path):
    # without floor_anchor an unlabelled blockquote is not a floor
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), APP_OK, {"floor.md": ANCHOR_DOC})
    assert single(out, "Z1") == "FAILED" and "Panel comment (the floor)" in out and code == 1


# ---------------------------------------------------------------- span lists

def test_span_list_reports_each_span(tmp_path):
    app = {"A01": {"s1": {"panel_comment": FLOOR}, "s2": {"panel_comment": FLOOR}, "s3": {"panel_comment": "No floor here."}}}
    e = entry(span="[A01.s1, A01.s2, A01.s3]", sha256=sha(FLOOR))
    code, out, _ = run(tmp_path, e, app, {"floor.md": SECTION})
    st = states(out)
    assert st[("Z1", "A01.s1")] == "TRANSFERRED"
    assert st[("Z1", "A01.s2")] == "TRANSFERRED"
    assert st[("Z1", "A01.s3")] == "FAILED"
    assert "2 transferred, 0 pending, 1 failed" in out and code == 1


def test_span_list_all_good_exits_zero(tmp_path):
    app = {"A01": {"s1": {"panel_comment": FLOOR}, "s2": {"panel_comment": FLOOR}}}
    code, out, _ = run(tmp_path, entry(span="[A01.s1, A01.s2]", sha256=sha(FLOOR)), app, {"floor.md": SECTION})
    assert code == 0 and "2 transferred" in out


def test_span_list_floor_problem_fails_every_span(tmp_path):
    app = {"A01": {"s1": {"panel_comment": FLOOR}, "s2": {"panel_comment": FLOOR}}}
    code, out, _ = run(tmp_path, entry(span="[A01.s1, A01.s2]", heading="Nope", sha256=sha(FLOOR)), app, {"floor.md": SECTION})
    st = states(out)
    assert st[("Z1", "A01.s1")] == st[("Z1", "A01.s2")] == "FAILED" and code == 1


def test_malformed_span_lists(tmp_path):
    for span in ("[A01.s1, A01.s1]", "[]", "[A01.s1, bogus]"):
        code, out, err = run(tmp_path, entry(span=span, sha256=sha(FLOOR)), APP_OK, {"floor.md": SECTION})
        assert "malformed ledger entry" in err and code == 1, span


# ---------------------------------------------------------------- --record-hashes

def test_record_hashes_fills_empty_only(tmp_path):
    e = entry(item="Z1", sha256="") + "\n" + entry(item="Z2", sha256="0" * 64)
    run(tmp_path, e, APP_OK, {"floor.md": SECTION}, extra=("--record-hashes",))
    text = (tmp_path / "ledger.yaml").read_text(encoding="utf-8")
    assert f'floor_sha256: "{sha(FLOOR)}"' in text
    assert 'floor_sha256: "' + "0" * 64 + '"' in text  # recorded hash never overwritten


# ---------------------------------------------------------------- the real Stage 1 floors

def real(tmp_path, item, heading, anchor, comment, doc=STAGE1, span="A01.s1"):
    e = entry(item=item, span=span, heading=heading, doc=doc, anchor=anchor)
    code, out, _ = run(tmp_path, e, {"A01": {"s1": {"panel_comment": comment}}}, root=REPO, extra=("--record-hashes",))
    return single(out, item)


def doc_lines(doc):
    return (REPO / doc).read_text(encoding="utf-8").splitlines()


def quote_starting(doc, prefix, nth=0):
    hits = [l for l in doc_lines(doc) if l.startswith("> " + prefix)]
    return hits[nth][2:]


def heading_of(doc, start):
    hits = [l for l in doc_lines(doc) if l.startswith("#") and l.lstrip("# ").startswith(start)]
    assert len(hits) == 1, (start, hits)
    return hits[0].lstrip("# ")


def test_a4_f3_selects_form_a_never_form_b(tmp_path):
    form_a = quote_starting(STAGE1, "The Article confesses only what Hebrews 1:1-2, John 16:13")
    form_b = quote_starting(STAGE1, "The Article confesses only what Acts 2:17-18, Amos 3:7")
    h = heading_of(STAGE1, "A4-F3.")
    assert real(tmp_path, "A4-F3", h, "**Form A", form_a) == "TRANSFERRED"
    assert real(tmp_path, "A4-F3", h, "**Form A", form_b) == "FAILED"


def test_g8_selects_2_oct_amended_never_22_sep(tmp_path):
    old = quote_starting(G_DOC, "The Article confesses only what Acts 2:38", 0)
    new = quote_starting(G_DOC, "The Article confesses only what Acts 2:38", 1)
    assert old != new and "how baptism is related to the remission of sins" in new and "how baptism is related to the remission of sins" not in old
    h = heading_of(G_DOC, "G8.")
    assert real(tmp_path, "G8", h, "**Amended by Aaron 2 Oct 2026", new, doc=G_DOC) == "TRANSFERRED"
    assert real(tmp_path, "G8", h, "**Amended by Aaron 2 Oct 2026", old, doc=G_DOC) == "FAILED"


def test_a2_f2_selects_amended_never_superseded(tmp_path):
    new = quote_starting(STAGE1, "The Article confesses only what Psalm 145:9, Romans 8:28", 0)
    old = quote_starting(STAGE1, "The Article confesses only what Psalm 145:9, James 1:17", 0)
    h = heading_of(STAGE1, "A2-F2.")
    assert real(tmp_path, "A2-F2", h, "A2-F2. ", new) == "TRANSFERRED"
    assert real(tmp_path, "A2-F2", h, "A2-F2. ", old) == "FAILED"


def test_a4_f4_and_f6_select_amended_wording(tmp_path):
    f4 = quote_starting(STAGE1, "The Article confesses only what 2 Corinthians 4:7, 1 Corinthians 1:27-29 and Romans 3:23")
    f6 = quote_starting(STAGE1, "The Article confesses only what Isaiah 40:8, Matthew 24:35 and Romans 15:4")
    assert real(tmp_path, "A4-F4", heading_of(STAGE1, "A4-F4."), "A4-F4. ", f4) == "TRANSFERRED"
    assert real(tmp_path, "A4-F6", heading_of(STAGE1, "A4-F6."), "A4-F6. ", f6) == "TRANSFERRED"


def test_a2_f5_selects_amended_wording(tmp_path):
    f5 = quote_starting(STAGE1, "The Article confesses only what Isaiah 55:8-9, Romans 11:33, Deuteronomy 29:29 and 1 Corinthians 13:9, 12")
    assert real(tmp_path, "A2-F5", heading_of(STAGE1, "A2-F5."), "A2-F5. ", f5) == "TRANSFERRED"


# ---------------------------------------------------------------- the real ledger

def test_real_ledger_29a_29b_pending_with_unchanged_hashes():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, encoding="utf-8", cwd=REPO)
    st = states(p.stdout)
    assert st[("29a", None)] == "PENDING" and st[("29b", None)] == "PENDING"
    ledger = (REPO / "data-sources/aoid/floor_ledger.yaml").read_text(encoding="utf-8")
    assert "e7565fa2d367a2ad7a3bf9df823581860e024846d6a80b9a926dd459c31b5c3e" in ledger
    assert "bc7ffe63e994aca78e3ba533192efd43787dcee3df5eb3072c568289de04a35c" in ledger


# ---------------------------------------------------------------- opening-paragraph rule (AOID2-FLOOR-OPENING-PARAGRAPH)

BREAK_MSG = "floor is followed by further text in the same paragraph; a paragraph break is needed after the floor"


def opening(tmp_path, comment):
    app = {"A01": {"s1": {"panel_comment": comment}}}
    code, out, _ = run(tmp_path, entry(sha256=sha(FLOOR)), app, {"floor.md": SECTION})
    return single(out, "Z1"), out, code


def test_opening_floor_then_break_then_notes_passes(tmp_path):
    state, _, code = opening(tmp_path, FLOOR + "\n\nApproved note one.\n\nApproved note two.")
    assert state == "TRANSFERRED" and code == 0


def test_opening_floor_with_whitespace_around_break_passes(tmp_path):
    state, _, _ = opening(tmp_path, FLOOR + "  \n \r\n\t\nNotes.")
    assert state == "TRANSFERRED"


def test_opening_floor_followed_by_text_in_same_paragraph_fails(tmp_path):
    for tail in (" Further notes.", "\nNext line, no blank line."):
        state, out, code = opening(tmp_path, FLOOR + tail)
        assert state == "FAILED" and BREAK_MSG in out and code == 1


def test_opening_floor_alone_passes(tmp_path):
    state, _, code = opening(tmp_path, FLOOR)
    assert state == "TRANSFERRED" and code == 0


def test_opening_notes_before_floor_fail(tmp_path):
    state, out, code = opening(tmp_path, "A note first.\n\n" + FLOOR)
    assert state == "FAILED" and "opening paragraph differs from floor" in out and code == 1


def test_opening_truncated_floor_fails(tmp_path):
    state, out, code = opening(tmp_path, FLOOR[:-20] + "\n\nNotes.")
    assert state == "FAILED" and "opening paragraph differs from floor" in out and BREAK_MSG not in out and code == 1


def test_real_ledger_a4s6_a6s18_a11s19_transferred():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, encoding="utf-8", cwd=REPO)
    st = states(p.stdout)
    assert st[("A4-F3", None)] == "TRANSFERRED"
    assert st[("A6-F9", "A06.s18")] == "TRANSFERRED"
    assert st[("A11-F4", "A11.s19")] == "TRANSFERRED"
