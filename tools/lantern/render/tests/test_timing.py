import pytest

from lantern_render.timing import MAX_ONSET_SPREAD, choose_pause_timing, first_speech_after, speech_segments


def test_speech_segments_are_the_gaps_between_silences():
    sil = [(0, 0.86), (7.93, 8.83), (10.2, 11.0)]
    assert speech_segments(sil, 12.0) == [(0.86, 7.93), (8.83, 10.2), (11.0, 12.0)]


def test_speech_segments_without_edge_silence_and_tiny_slivers():
    assert speech_segments([(2.0, 3.0)], 5.0) == [(0.0, 2.0), (3.0, 5.0)]
    assert speech_segments([(0, 4.99)], 5.0) == []  # a 10 ms sliver is not speech


def segs(*starts, dur=1.0):
    return [(s, s + dur) for s in starts]


def test_chooser_takes_the_setting_closest_to_the_default():
    cands = {(-35, 0.35): segs(0, 3, 7), (-33, 0.30): segs(0.02, 3.01, 7.0), (-40, 0.40): segs(0, 3, 7, 9),
             (-30, 0.35): segs(0, 3)}
    got = choose_pause_timing(cands, 3)
    assert got['setting'] == (-35, 0.35)
    assert got['settings_agreeing'] == 2 and got['settings_tried'] == 4
    assert got['onset_spread'] == pytest.approx(0.02)


def test_chooser_moves_off_the_default_when_only_other_settings_work():
    cands = {(-35, 0.35): segs(0, 3), (-38, 0.30): segs(0, 3, 7)}
    assert choose_pause_timing(cands, 3)['setting'] == (-38, 0.30)


def test_chooser_refuses_when_no_setting_gives_the_count():
    assert choose_pause_timing({(-35, 0.35): segs(0, 3), (-36, 0.35): segs(0, 3, 7, 9)}, 3) is None


def test_chooser_refuses_when_matching_settings_disagree_on_onsets():
    shift = MAX_ONSET_SPREAD + 0.1
    cands = {(-35, 0.35): segs(0, 3, 7), (-34, 0.35): segs(0, 3 + shift, 7)}
    assert choose_pause_timing(cands, 3) is None


def test_first_speech_after_finds_the_url_blip():
    sil = [(0, 0.9), (46.7, 47.3), (47.4, 47.8)]
    assert first_speech_after(sil, 52.0, 46.8) == pytest.approx(47.3)
    assert first_speech_after(sil, 52.0, 60.0) is None
