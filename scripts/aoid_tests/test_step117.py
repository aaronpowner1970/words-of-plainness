"""Tests for AOID2 step 117 (CODE-AOID2-74): the A14 banner (Of Love for God and Neighbor, Article 1 in the Second
Edition) is in src/_data/banners.json in the same form as the other Article banners, with the alt text Aaron
confirmed, and it renders in the switch-ON build and nowhere in the switch-OFF build.

Run: python -m pytest scripts/aoid_tests/test_step117.py
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CDN = "https://media.wordsofplainness.org/web/banners/a14-of-love-for-god-and-neighbor"
ALT = "Article 1 — Of Love for God and Neighbor"
WIDTHS = [480, 768, 1536, 2048]
ITEMS = json.loads((REPO / "src" / "_data" / "banners.json").read_text(encoding="utf-8"))["items"]


def build(out, on):
    env = {k: v for k, v in os.environ.items() if k not in ("WOP_AOID2_SECOND_EDITION", "WOP_AOID2_BUILD_REVIEW")}
    if on:
        env["WOP_AOID2_SECOND_EDITION"] = "1"
    r = subprocess.run(["npx", "@11ty/eleventy", f"--output={Path(out).as_posix()}"], cwd=REPO, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", shell=(os.name == "nt"))
    assert r.returncode == 0, r.stderr[-2000:] + r.stdout[-1000:]


@pytest.fixture(scope="module")
def articles_on(tmp_path_factory):
    out = tmp_path_factory.mktemp("on")
    build(out, True)
    return (out / "articles" / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def articles_off(tmp_path_factory):
    out = tmp_path_factory.mktemp("off")
    build(out, False)
    return (out / "articles" / "index.html").read_text(encoding="utf-8")


def test_entry_matches_pattern():
    b = ITEMS["a14"]
    assert b["slug"] == "a14-of-love-for-god-and-neighbor"
    assert b["title"] == "Of Love for God and Neighbor"
    assert b["article"] == 1 and b["role"] is None
    assert b["alt"] == ALT
    assert (b["nativeWidth"], b["nativeHeight"]) == (2172, 724)
    assert b["widths"] == WIDTHS
    assert b["urls"] == {str(w): f"{CDN}-{w}.webp" for w in WIDTHS}


def test_other_entries_untouched():
    # AOID2 step 132 (CODE-AOID2-78): a01 reads "Prologue" in the Second Edition; the First Edition alt is held beside it
    assert ITEMS["a01"]["alt"] == "Prologue — Of Plainness"
    assert ITEMS["a01"]["alt_first_edition"] == "Article 1 — Of Plainness"
    assert sorted(ITEMS) == [f"a{n:02d}" for n in range(15)]


def test_banner_renders_in_on_build(articles_on):
    assert f'alt="{ALT}"' in articles_on
    for w in WIDTHS:
        assert f"{CDN}-{w}.webp {w}w" in articles_on
    assert f'src="{CDN}-768.webp"' in articles_on


def test_banner_absent_in_off_build(articles_off):
    assert "a14-of-love-for-god-and-neighbor" not in articles_off
    assert "Of Love for God and Neighbor" not in articles_off
