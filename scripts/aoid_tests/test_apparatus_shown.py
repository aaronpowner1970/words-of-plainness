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
MARKERS = ("text_first_edition", "panel_comment_first_edition", "comment_first_edition", "second_edition")
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
