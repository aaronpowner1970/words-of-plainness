"""Tests for src/_data/apparatusShown.js, the apparatus the Articles page embeds (CODE-AOID2-41).

The Article 12 Second Edition changes (new spans s11 and s12, revised text of s5 and s6, revised panel comments
s1-s10, added anchors on s4-s6) are carried in apparatusData.json by marker fields: `text_first_edition`,
`panel_comment_first_edition` and an anchor's `second_edition: true`. With the switch OFF the embedded apparatus
must hold the First Edition values; with it ON it must hold the Second Edition values; and no marker field may
reach either output.

Run: python -m pytest scripts/aoid_tests
"""
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = json.loads((REPO / "src" / "_data" / "apparatusData.json").read_text(encoding="utf-8"))
MARKERS = ("text_first_edition", "panel_comment_first_edition", "comment_first_edition", "second_edition", "first_edition_only")
NEW_SPANS = ("s11", "s12")


def shown(on):
    env = {k: v for k, v in os.environ.items() if k != "WOP_AOID2_SECOND_EDITION"}
    if on:
        env["WOP_AOID2_SECOND_EDITION"] = "1"
    p = subprocess.run(
        ["node", "-e", "process.stdout.write(JSON.stringify(require('./src/_data/apparatusShown.js')))"],
        cwd=REPO, env=env, capture_output=True, encoding="utf-8", check=True,
    )
    return json.loads(p.stdout)


def keys_anywhere(o, found=None):
    found = set() if found is None else found
    if isinstance(o, dict):
        for k, v in o.items():
            found.add(k)
            keys_anywhere(v, found)
    elif isinstance(o, list):
        for v in o:
            keys_anywhere(v, found)
    return found


def test_switch_off_embeds_first_edition_article_12():
    a12 = shown(False)["A12"]
    assert list(a12) == [f"s{i}" for i in range(1, 11)]
    for sid, s in a12.items():
        src = DATA["A12"][sid]
        assert s["panel_comment"] == src["panel_comment_first_edition"], sid
        assert s["text"] == src.get("text_first_edition", src["text"]), sid
        for col in ("biblical", "restoration"):
            assert [a["ref"] for a in s[col]] == [a["ref"] for a in src[col] if not a.get("second_edition")], (sid, col)


def test_switch_on_embeds_second_edition_article_12():
    a12 = shown(True)["A12"]
    assert list(a12) == [f"s{i}" for i in range(1, 13)]
    for sid, s in a12.items():
        src = DATA["A12"][sid]
        assert s["panel_comment"] == src["panel_comment"], sid
        assert s["text"] == src["text"], sid
        for col in ("biblical", "restoration"):
            assert [a["ref"] for a in s[col]] == [a["ref"] for a in src[col]], (sid, col)
    assert "naked honesty" not in a12["s5"]["text"] and a12["s6"]["text"].endswith("remembered")


def test_no_marker_field_reaches_either_output():
    for on in (False, True):
        assert not (keys_anywhere(shown(on)) & set(MARKERS)), f"marker field embedded with switch {'ON' if on else 'OFF'}"


def test_every_article_12_span_with_a_revised_comment_keeps_its_first_edition_comment():
    for sid in (f"s{i}" for i in range(1, 11)):
        assert DATA["A12"][sid]["panel_comment_first_edition"], sid
    for sid in NEW_SPANS:
        assert "panel_comment_first_edition" not in DATA["A12"][sid]


def test_article_12_second_edition_comments_use_closed_em_dashes():
    for sid, s in shown(True)["A12"].items():
        assert " - " not in s["panel_comment"] and " — " not in s["panel_comment"], sid


# Article 9 s6-s9 (CODE-AOID2-44): revised panel comments, six revised anchor comments and one added anchor,
# all behind the switch. The anchor-comment marker `comment_first_edition` and the added-anchor marker
# `second_edition` are the CODE-AOID2-32/33 ones; the panel-comment marker is the CODE-AOID2-41 one.
A09_REVISED = ("s6", "s7", "s8", "s9")


def test_article_9_s6_to_s9_switch_off_keeps_first_edition_comments_and_anchors():
    a09 = shown(False)["A09"]
    for sid in A09_REVISED:
        src = DATA["A09"][sid]
        assert a09[sid]["panel_comment"] == src["panel_comment_first_edition"], sid
        assert not a09[sid]["panel_comment"].startswith("The Article confesses only"), sid
        for col in ("biblical", "restoration"):
            assert [a["ref"] for a in a09[sid][col]] == [a["ref"] for a in src[col] if not a.get("second_edition")], (sid, col)
            for a in a09[sid][col]:
                srca = next(x for x in src[col] if x["ref"] == a["ref"])
                assert a["comment"] == srca.get("comment_first_edition", srca["comment"]), (sid, a["ref"])
    assert "2 John 1:9" not in [a["ref"] for a in a09["s7"]["biblical"]]


def test_article_9_s6_to_s9_switch_on_opens_each_comment_with_its_floor_and_adds_2_john_1_9():
    a09 = shown(True)["A09"]
    for sid in A09_REVISED:
        first, second = a09[sid]["panel_comment"].split(chr(10) * 2)
        assert first.startswith("The Article confesses only what") and second, sid
    assert [a["ref"] for a in a09["s7"]["biblical"]].count("2 John 1:9") == 1
    assert next(a for a in a09["s7"]["biblical"] if a["ref"] == "2 John 1:9")["comment"] == (
        "Named in the s7 floor as its qualifier: precedence is not dismissal. John binds abiding in the doctrine of Christ "
        "to having God; the span ranks doctrine beneath the relationship without setting the two against each other."
    )
    assert next(a for a in a09["s28"]["restoration"] if a["ref"] == "Moroni 10:8–18")["comment"] == (
        "Read with Moroni 10:4–5, cited above with the Spirit as Teacher."
    )
    assert sum("comment_first_edition" in a for sid in A09_REVISED for col in ("biblical", "restoration") for a in DATA["A09"][sid][col]) >= 6

# Article 9 commentary corrections (CODE-AOID2-46): revised panel comments on s1-s22 (s8's was built in CODE-AOID2-44),
# revised anchor notes, one added anchor (2 Nephi 9:25-26 at s17), one removed anchor (D&C 35:17-18 at s4, marked
# `first_edition_only`), the s26 floor sentence, all behind the switch.
A09_CORRECTED = tuple(f"s{i}" for i in range(1, 23))


def test_article_9_corrections_switch_off_keeps_head_comments_and_anchors():
    a09 = shown(False)["A09"]
    for sid in A09_CORRECTED:
        src = DATA["A09"][sid]
        assert src["panel_comment_first_edition"], sid
        assert a09[sid]["panel_comment"] == src["panel_comment_first_edition"], sid
        for col in ("biblical", "restoration"):
            for a in a09[sid][col]:
                srca = next(x for x in src[col] if x["ref"] == a["ref"])
                assert a["comment"] == srca.get("comment_first_edition", srca["comment"]), (sid, a["ref"])
    assert "D&C 35:17–18" in [a["ref"] for a in a09["s4"]["restoration"]]
    assert "2 Nephi 9:25–26" not in [a["ref"] for a in a09["s17"]["restoration"]]
    assert "s26" not in a09 and "s29" not in a09


def test_article_9_corrections_switch_on_shows_approved_changes():
    a09 = shown(True)["A09"]
    for sid in A09_CORRECTED:
        assert a09[sid]["panel_comment"] == DATA["A09"][sid]["panel_comment"], sid
        assert a09[sid]["panel_comment"] != DATA["A09"][sid].get("panel_comment_first_edition"), sid
    assert "D&C 35:17–18" not in [a["ref"] for a in a09["s4"]["restoration"]]
    assert len(a09["s4"]["restoration"]) == len(DATA["A09"]["s4"]["restoration"]) - 1
    assert [a["ref"] for a in a09["s17"]["restoration"]].count("2 Nephi 9:25–26") == 1
    assert a09["s26"]["panel_comment"].split(chr(10) * 2)[0].endswith(
        "It connects to the one boundary the Prologue names. It does not settle how that witness is received or recognised."
    )
    assert "AOID2-BOUNDARY" not in a09["s26"]["panel_comment"]
    assert a09["s29"]["panel_comment"].count(chr(10) * 2) == 2 - 1



# --- AOID2 step 107 (CODE-AOID2-66): Article 9 rally point (span s30, author's note, floor A9-F14) ---
S30_TEXT = 'Whatever first turned you toward Christ, we rejoice that you seek Him. We may differ on how the map is rightly read, and on which way leads most surely to Him, but let none of us fail to come unto Jesus of Nazareth. Should any instrument we carry, even this one, turn us from Christ or teach us contempt for a fellow traveler, we have surely lost our bearing, and must take our sighting of Him anew.'
S30_NOTE = 'This Article proposes a rallying point for disciples of every Christian tradition. Its picture is not new: Christ the North Star, His Spirit the compass, the scriptures the map. Each part is drawn from scripture that Christians of every tradition receive, and the arrangement adds nothing to the gospel of Jesus Christ. I offer it not as a creed, nor as a correction to any church, but as a place where we may gather and look together toward the One who prayed that all who believe in Him might be one (John 17:20-23). Its only test is the one it sets for itself: does it bring us, together, to Him?'
S30_FLOOR = 'The Article confesses only what Philippians 1:15-18, Mark 9:38-40 and John 17:20-23 confess: wherever Christ is preached, His disciples rejoice; Christ forbade His disciples to stop one who worked in His name though he followed not with them; and Christ prayed that all who believe on Him might be one. This is the floor: the disciple rejoices in every turning toward Christ, differences over the way to Him are no warrant for forbidding one another, and whatever turns disciples from Christ or toward contempt for one another has lost its bearing. It does not settle which way leads most surely to Him, how the scriptures are rightly read or by what authority, what a church may require of its own members, or whether and how the traditions should be united; each tradition fills those in its own house.'
S30_ANCHORS = {
    "biblical": ["Philippians 1:15–18", "Mark 9:38–40", "John 17:20–23", "1 Corinthians 1:10–13", "Matthew 11:28", "Matthew 7:7"],
    "restoration": ["2 Nephi 26:33", "3 Nephi 11:29", "Moroni 10:32"],
}


def render_a09(on):
    script = (
        "const n=require('nunjucks');const e=new n.Environment(new n.FileSystemLoader('src/_includes'),{autoescape:false});"
        "process.stdout.write(e.render('aoid/a09.njk',{aoidSecondEdition:{on:%s}}))" % ("true" if on else "false")
    )
    return subprocess.run(["node", "-e", script], cwd=REPO, capture_output=True, encoding="utf-8", check=True).stdout


def test_article_9_rally_point_span_and_anchors_appear_only_with_the_switch_on():
    on, off = shown(True)["A09"], shown(False)["A09"]
    assert "s30" not in off
    s = on["s30"]
    assert (s["text"], s["type"], s["named_concept"]) == (S30_TEXT, "concept", False)
    assert s["panel_comment"] == S30_FLOOR and chr(10) not in s["panel_comment"]
    for col, refs in S30_ANCHORS.items():
        assert [a["ref"] for a in s[col]] == refs
        assert all(a["comment"] == "" for a in s[col])
    assert list(on)[-1] == "s30" and list(on)[-2] == "s29"
    assert not keys_anywhere(s) & set(MARKERS)


def test_article_9_rally_point_span_and_note_render_only_with_the_switch_on():
    on, off = render_a09(True), render_a09(False)
    assert 'data-span="s30"' not in off and "article-author-note" not in off
    assert S30_NOTE not in off and S30_TEXT not in off
    assert on.count('data-span="s30"') == 1 and on.count(S30_TEXT) == 1 and on.count(S30_NOTE) == 1
    assert "(John 17:20-23)" in S30_NOTE
    # note first in the body, span after s22 and immediately before the reflection prompt
    assert on.index('<div class="article-body">') < on.index("article-author-note") < on.index('data-span="s1"')
    assert on.index('data-span="s22"') < on.index('data-span="s30"') < on.index('<div class="article-rjw">')
    assert on.count("article-author-note") == 1


def test_article_9_rally_point_floor_a9_f14_is_in_the_ledger_and_the_floor_document():
    ledger = (REPO / "data-sources" / "aoid" / "floor_ledger.yaml").read_text(encoding="utf-8")
    block = ledger.split("- item: A9-F14", 1)[1].split(chr(10) + "  - item:", 1)[0].split(chr(10) + "# ", 1)[0]
    assert "span: A09.s30" in block and "floor_ratified: 2026-10-31" in block
    assert "scored_on: null" in block and "scoring_records: []" in block
    doc = (REPO / "data-sources" / "aoid" / "floors" / "WoP_AOID2_A09_s30_RallyPoint_Floor_Ratified_20261031.md").read_text(encoding="utf-8")
    assert "> " + S30_FLOOR in doc.split(chr(10))
