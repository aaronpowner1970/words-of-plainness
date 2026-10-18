import json
from pathlib import Path

import pytest

from lantern_render.spec import SpecError, default_hook, default_screens, load_spec, parse_spec, resolve_media, spoken_words

SPECS = Path(__file__).resolve().parents[1] / 'specs'


def minimal(**extra):
    d = {'image': 'a.png', 'narration': 'n.mp3', 'bed': 'b.mp3', 'lines': ['One two.', 'Three four.']}
    d.update(extra)
    return d


def test_defaults_fill_everything_but_the_lines():
    s = parse_spec(minimal())
    assert [ln.text for ln in s.lines] == ['One two.', 'Three four.']
    assert s.screens == [[0, 1]]
    assert s.zone_y == 960 and s.hook_seconds == 0.8 and s.url_text == ['wordsofplainness.org']
    assert s.credit == 'Aaron Powner · Words of Plainness Ministry'
    assert len(s.hook) == 2  # the last line, split into two rows
    assert s.url_spoken is False and s.timing == 'auto' and s.end_card_seconds == 3.0


def test_default_screens_group_in_threes():
    assert default_screens(7) == [[0, 1, 2], [3, 4, 5], [6]]


def test_default_hook_balances_the_last_line():
    assert default_hook('What does your mirror reveal?') == ['What does your', 'mirror reveal?']
    assert default_hook('Single') == ['Single']


@pytest.mark.parametrize('zone,y', [('top', 760), ('middle', 960), ('lower', 1440), (1000, 1000)])
def test_text_zone_names_and_values(zone, y):
    assert parse_spec(minimal(text_zone=zone)).zone_y == y


@pytest.mark.parametrize('bad', [
    {'lines': []}, {'lines': [{'text': ''}]}, {'lines': [{'text': 'x', 'colour': 'red'}]},
    {'screens': [[0], [0, 1]]}, {'screens': [[1], [0]]}, {'screens': [[0]]},
    {'text_zone': 'bottom'}, {'text_zone': 50}, {'timing': 'guess'}, {'hook': ['a', 'b', 'c']},
    {'end_card_seconds': 'long'}, {'image': ''},
])
def test_bad_specs_are_refused_with_a_plain_message(bad):
    with pytest.raises(SpecError):
        parse_spec(minimal(**bad))


def test_gold_italic_and_ref_flags():
    s = parse_spec(minimal(lines=['a b', {'text': 'c d', 'gold': True, 'italic': True, 'ref': 'John 13:35'}]))
    assert not s.lines[0].gold and s.lines[1].gold and s.lines[1].italic and s.lines[1].ref == 'John 13:35'
    with pytest.raises(SpecError):
        parse_spec(minimal(lines=[{'text': 'a b', 'gold': 'yes'}]))


def test_spoken_words_drop_punctuation_and_split_dashes():
    assert spoken_words('a Latter-day Saint—') == ['a', 'latter', 'day', 'saint']
    assert spoken_words('“By this shall\nall men know”') == ['by', 'this', 'shall', 'all', 'men', 'know']
    assert spoken_words('doesn’t') == ["doesn't"]


def test_spoken_override_used_when_given():
    s = parse_spec(minimal(lines=[{'text': '1 John 4:8', 'spoken': 'first john four eight'}]))
    assert s.lines[0].spoken_words() == ['first', 'john', 'four', 'eight']


def test_committed_specs_load():
    a = load_spec(SPECS / 'recognized_on_sight.json')
    b = load_spec(SPECS / 'what_the_mirror_reveals.json')
    assert (len(a.lines), a.zone_y, a.url_spoken) == (20, 760, True)
    assert sum(len(ln.spoken_words()) for ln in a.lines) == 113
    assert (len(b.lines), b.zone_y, b.end_card_seconds) == (5, 1440, 2.4)


def test_bad_json_and_missing_media(tmp_path):
    p = tmp_path / 's.json'
    p.write_text('{nope', encoding='utf-8')
    with pytest.raises(SpecError):
        load_spec(p)
    p.write_text(json.dumps(minimal()), encoding='utf-8')
    with pytest.raises(SpecError, match='not found'):
        resolve_media(load_spec(p), tmp_path)
