"""Renders a few seconds from generated tone and a solid-colour image. Suitable for CI: no real media."""
import json
import math
import shutil
import struct
import wave

import pytest
from PIL import Image

from lantern_render.pipeline import render
from lantern_render.timing import TimingError

pytestmark = pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='ffmpeg not installed')

RATE = 48000


def write_tone(path, bursts, total, freq=440, amp=0.3):
    """Mono tone bursts [(start, length)] in silence."""
    frames = bytearray()
    for i in range(int(total * RATE)):
        t = i / RATE
        on = any(s <= t < s + n for s, n in bursts)
        frames += struct.pack('<h', int(32767 * amp * math.sin(2 * math.pi * freq * t)) if on else 0)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


@pytest.fixture(scope='module')
def media_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp('media')
    write_tone(d / 'narration.wav', [(0.3, 0.8), (1.8, 0.8), (3.3, 0.8)], 4.6)
    write_tone(d / 'bed.wav', [(0, 15)], 15, freq=220, amp=0.2)
    Image.new('RGB', (540, 960), (40, 70, 110)).save(d / 'image.png')
    return d


def spec(**extra):
    d = {'title': 'Smoke', 'image': 'image.png', 'narration': 'narration.wav', 'bed': 'bed.wav',
         'lines': ['One tone.', {'text': 'Two tones.', 'gold': True}, 'Three tones.'],
         'screens': [[0, 1, 2]], 'hook': ['Smoke', 'test'], 'url_seconds': 1.5, 'end_card_seconds': 2.0,
         'text_zone': 'middle'}
    d.update(extra)
    return d


def test_renders_a_passing_video_with_the_report(tmp_path, media_dir, monkeypatch):
    monkeypatch.setenv('LANTERN_X264_PRESET', 'veryfast')
    (tmp_path / 'spec.json').write_text(json.dumps(spec()), encoding='utf-8')
    out = tmp_path / 'out'
    c = render(tmp_path / 'spec.json', out, media_dir)
    assert c['ok'], c['checks']
    o = c['output']
    assert (o['width'], o['height'], o['fps']) == (1080, 1920, 30.0)
    assert (o['video_codec'], o['profile'], o['level'], o['pix_fmt']) == ('h264', 'High', 41, 'yuv420p')
    assert (o['audio_codec'], o['audio_sample_rate']) == ('aac', 48000) and o['faststart']
    assert abs(o['loudness_lufs'] + 16) <= 1.0 and o['true_peak_dbtp'] <= -1.0
    t = c['timing']
    assert t['method'] == 'pause detection'
    # tone starts at 0.3, 1.8, 3.3; the narration is delayed so the first line lands when the 0.8 s hook ends
    assert c['plan']['narration_offset_s'] == pytest.approx(0.5, abs=0.02)
    got = [r['narration_onset_s'] for r in t['lines']]
    assert got == pytest.approx([0.3, 1.8, 3.3], abs=0.06)
    assert t['lines'][0]['video_onset_s'] == pytest.approx(0.8, abs=0.06)
    assert c['fonts']['body_widest_px'] <= 960 and c['fonts']['body_size'] <= 92
    assert any('narrower than 1080' in w for w in c['warnings'])
    assert abs(o['duration_s'] - c['plan']['total_s']) < 0.1
    for name in ('out.mp4', 'cover_9x16.png', 'check.json', 'check.md'):
        assert (out / name).is_file()
    assert Image.open(out / 'cover_9x16.png').size == (1080, 1920)
    assert 'PASS' in (out / 'check.md').read_text(encoding='utf-8')
    assert not (out / 'work' / 'mixn.wav').exists()  # intermediates are cleaned up


def test_a_line_count_that_pauses_cannot_show_is_refused_not_guessed(tmp_path, media_dir):
    s = spec(lines=['One.', 'Two.', 'Three.', 'Four.'], screens=[[0, 1, 2, 3]], timing='pause')
    (tmp_path / 'spec.json').write_text(json.dumps(s), encoding='utf-8')
    with pytest.raises(TimingError, match='not 4'):
        render(tmp_path / 'spec.json', tmp_path / 'out', media_dir)
