"""The whole render: spec + background image + narration + bed -> out.mp4, cover_9x16.png, check.json/.md."""
import json
import os
import shutil
import struct
from pathlib import Path

from . import audio, media, subs, timing, visuals
from .spec import load_spec, resolve_media

FPS = 30
CROSSFADE = 0.6
ZOOM = 0.03
SCRIM_MARGIN = 110
BLOCK_GAP_REF = 55
TARGET_LUFS_TOL = 1.0


def snap(t):
    """Round a time up to a whole frame."""
    return round(t * FPS) / FPS


def faststart_ok(path):
    """True when the moov box comes before the mdat box."""
    seen = []
    with open(path, 'rb') as f:
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            size, kind = struct.unpack('>I4s', head)
            seen.append(kind)
            if size == 1:
                size = struct.unpack('>Q', f.read(8))[0]
                f.seek(size - 16, 1)
            elif size == 0:
                break
            else:
                f.seek(size - 8, 1)
    return b'moov' in seen and b'mdat' in seen and seen.index(b'moov') < seen.index(b'mdat')


def describe_output(path):
    info = media.ffprobe_json(path)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    num, den = v['r_frame_rate'].split('/')
    loud = media.loudnorm_stats(path)
    return {
        'bytes': os.path.getsize(path), 'width': v['width'], 'height': v['height'],
        'duration_s': round(float(info['format']['duration']), 3), 'fps': round(int(num) / int(den), 3),
        'video_codec': v['codec_name'], 'profile': v.get('profile'), 'level': v.get('level'),
        'pix_fmt': v['pix_fmt'], 'audio_codec': a['codec_name'], 'audio_profile': a.get('profile'),
        'audio_sample_rate': int(a['sample_rate']), 'audio_bit_rate': int(a.get('bit_rate', 0)),
        'faststart': faststart_ok(path),
        'loudness_lufs': round(loud['input_i'], 2), 'true_peak_dbtp': round(loud['input_tp'], 2),
    }


def standard_checks(o, target_total):
    return {
        'size_1080x1920': (o['width'], o['height']) == (1080, 1920),
        'fps_30': abs(o['fps'] - 30) < 0.01,
        'h264_high_4_1': o['video_codec'] == 'h264' and o['profile'] == 'High' and o['level'] == 41,
        'yuv420p': o['pix_fmt'] == 'yuv420p',
        'aac_lc_48k_192k': o['audio_codec'] == 'aac' and o['audio_sample_rate'] == 48000
                           and 150_000 <= o['audio_bit_rate'] <= 200_000,
        'faststart': o['faststart'],
        'length_as_planned': abs(o['duration_s'] - target_total) < 0.1,
        'loudness_near_-16': abs(o['loudness_lufs'] - audio.TARGET_I) <= TARGET_LUFS_TOL,
        'true_peak_below_-1': o['true_peak_dbtp'] <= -1.0,
    }


def render(spec_path, out_dir, media_dir=None, keep_work=False, log=print):
    spec_path = Path(spec_path)
    spec = load_spec(spec_path)
    paths = resolve_media(spec, media_dir or spec_path.parent)
    out_dir = Path(out_dir)
    work = out_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    warnings = []

    # ---- timing
    nar_dur = media.duration(paths['narration'])
    log('timing...')
    t = timing.measure_timing(str(paths['narration']), [ln.spoken_words() for ln in spec.lines],
                              spec.url_spoken, spec.timing, str(work), nar_dur)
    offset = max(0.0, round(spec.hook_seconds - t['onsets'][0], 3))
    onsets = [o + offset for o in t['onsets']]
    speech_end = t['speech_end'] + offset
    if spec.url_spoken and t['url_onset'] is not None:
        url0 = t['url_onset'] + offset
        text_end = max(url0 + spec.url_seconds, offset + nar_dur)
    else:
        if spec.url_spoken:
            warnings.append('url_spoken is set but no speech was found after the last line; the URL screen is timed from the last line instead.')
        url0 = speech_end + spec.url_gap
        text_end = max(url0 + spec.url_seconds, offset + nar_dur)
    url0, text_end = snap(url0), snap(text_end)
    first_clip = text_end + CROSSFADE
    total = snap(text_end + spec.end_card_seconds)

    # ---- audio
    log('audio...')
    gains = audio.mix_and_normalize(str(paths['narration']), str(paths['bed']), offset, total,
                                    spec.bed_under_voice_lu, str(work))
    if media.duration(paths['bed']) < total - 0.05:
        warnings.append('The music bed (%.1f s) is shorter than the video (%.1f s); it ends early.'
                        % (media.duration(paths['bed']), total))

    # ---- fonts: largest size at which the widest line fits 960 px, as libass draws it
    log('fitting text...')
    body_texts = [ln.text for ln in spec.lines]
    fs, widest = subs.fit_font(str(work), body_texts, subs.FS_CAP)
    hook_fs, hook_w = subs.fit_font(str(work), spec.hook, subs.HOOK_CAP)
    url_fs, url_w = subs.fit_font(str(work), spec.url_text, subs.URL_CAP)
    blocks = []
    for sc in spec.screens:
        text = '\n\n'.join(spec.lines[k].text for k in sc)
        blocks.append(subs.measure_block(str(work), text, fs))
    block_h = max(h for _, h in blocks)
    top, bottom = spec.zone_y - block_h / 2, spec.zone_y + block_h / 2
    ref_ys = {}
    for si, (_, h) in enumerate(blocks):
        ref_ys[si] = int(min(spec.zone_y + h / 2 + BLOCK_GAP_REF, visuals.H - 260))
        if any(spec.lines[k].ref for k in spec.screens[si]):
            bottom = max(bottom, ref_ys[si] + 30)
    if top < visuals.HEADER_H + 20:
        warnings.append('The text block starts at y %d, inside the header band (to y %d).' % (top, visuals.HEADER_H))
    if bottom > visuals.H - 150:
        warnings.append('The text block ends at y %d, close to the credit line.' % bottom)

    # ---- stills
    log('stills...')
    w = visuals.source_width_warning(paths['image'])
    if w:
        warnings.append(w)
    scrim_half = int(block_h / 2 + SCRIM_MARGIN)
    bg = visuals.scene(paths['image'], spec.zone_y, scrim_half)
    visuals.framed(bg, spec.credit).save(work / 'frame.png')
    visuals.end_card(bg, spec.url_text).save(work / 'endcard.png')
    cover = visuals.cover(bg, spec.hook, spec.zone_y, hook_fs)
    cover.save(out_dir / 'cover_9x16.png')

    # ---- subtitles + encode
    (work / 'post.ass').write_text(subs.build_ass(spec, fs, hook_fs, url_fs, onsets, url0, text_end, ref_ys),
                                   encoding='utf-8')
    if not (work / 'fonts').exists():
        shutil.copytree(visuals.FONT_DIR, work / 'fonts', ignore=shutil.ignore_patterns('*.txt'))
    frames = round(first_clip * FPS)
    vf = (f"[0:v]zoompan=z='1+{ZOOM}*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS},"
          f"ass=post.ass:fontsdir=fonts,setsar=1[a];[1:v]fps={FPS},setsar=1[b];"
          f"[a][b]xfade=transition=fade:duration={CROSSFADE}:offset={text_end:.3f},format=yuv420p[v]")
    preset = os.environ.get('LANTERN_X264_PRESET', 'medium')
    log('encoding...')
    media.ffmpeg('-loop', '1', '-framerate', FPS, '-t', f'{first_clip:.3f}', '-i', 'frame.png',
                 '-loop', '1', '-framerate', FPS, '-t', f'{spec.end_card_seconds:.3f}', '-i', 'endcard.png',
                 '-i', 'mixn.wav', '-filter_complex', vf, '-map', '[v]', '-map', '2:a',
                 '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.1', '-preset', preset, '-crf', '18',
                 '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                 '-movflags', '+faststart', '-t', f'{total:.3f}', '../out.mp4', cwd=str(work))

    # ---- the check report
    out_mp4 = out_dir / 'out.mp4'
    o = describe_output(out_mp4)
    checks = standard_checks(o, total)
    check = {
        'spec': str(spec_path.name), 'title': spec.title, 'ok': all(checks.values()), 'checks': checks,
        'output': o,
        'plan': {'narration_offset_s': offset, 'hook_s': spec.hook_seconds, 'url_screen_at_s': round(url0, 3),
                 'text_end_s': round(text_end, 3), 'end_card_s': spec.end_card_seconds, 'crossfade_s': CROSSFADE,
                 'xfade_offset_s': round(text_end, 3), 'total_s': round(total, 3), 'zoom_frames': frames,
                 'text_zone_y': spec.zone_y, 'scrim_half_height': scrim_half},
        'timing': {'method': t['method'], 'detail': t['detail'], 'notes': t['notes'],
                   'speech_end_s': round(t['speech_end'], 3),
                   'lines': [{'n': i + 1, 'text': ln.text.replace('\n', ' / '),
                              'narration_onset_s': round(t['onsets'][i], 3), 'video_onset_s': round(onsets[i], 3)}
                             for i, ln in enumerate(spec.lines)]},
        'fonts': {'family': 'EB Garamond (Medium, SemiBold, Medium Italic), @fontsource/eb-garamond 5.3.0, SIL OFL 1.1',
                  'body_size': fs, 'body_widest_px': widest, 'hook_size': hook_fs, 'hook_widest_px': hook_w,
                  'url_size': url_fs, 'url_widest_px': url_w, 'fit_limit_px': subs.FIT_WIDTH,
                  'standard_size': subs.FS_CAP},
        'audio': {**gains, 'target_lufs': audio.TARGET_I, 'target_tp': audio.TARGET_TP, 'target_lra': audio.TARGET_LRA},
        'warnings': warnings,
    }
    (out_dir / 'check.json').write_text(json.dumps(check, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out_dir / 'check.md').write_text(check_markdown(check), encoding='utf-8')
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return check


def check_markdown(c):
    o, p, t, f, a = c['output'], c['plan'], c['timing'], c['fonts'], c['audio']
    L = [f"# Render check: {c['title'] or c['spec']}", '',
         f"Overall: {'PASS' if c['ok'] else 'FAIL'}", '', '## Output', '',
         f"- Size {o['width']}x{o['height']}, {o['duration_s']} s, {o['fps']} fps, {o['bytes'] / 1e6:.1f} MB",
         f"- Video {o['video_codec']} {o['profile']} level {o['level'] / 10:.1f}, {o['pix_fmt']}; "
         f"audio {o['audio_codec']} {o['audio_profile']}, {o['audio_sample_rate']} Hz, {o['audio_bit_rate'] // 1000} kbps; "
         f"faststart {'yes' if o['faststart'] else 'NO'}",
         f"- Loudness {o['loudness_lufs']} LUFS (target {a['target_lufs']}), true peak {o['true_peak_dbtp']} dBTP (limit {a['target_tp']})",
         '', '## Standard checks', '']
    L += [f"- {'PASS' if v else 'FAIL'}: {k}" for k, v in c['checks'].items()]
    L += ['', '## Timing', '', f"- Method: {t['method']}"]
    if t['detail']:
        d = t['detail']
        L.append(f"- Pause setting {d['setting'][0]} dB / {d['setting'][1]} s; {d['settings_agreeing']} of {d['settings_tried']} "
                 f"settings gave one segment per line; onsets differ by at most {d['onset_spread']} s between them")
    L += [f"- {n}" for n in t['notes']]
    lead = (f"Narration starts {p['narration_offset_s']} s into the video (the hook plays first)"
            if p['narration_offset_s'] else 'Narration starts at 0 s (it already begins after the hook ends)')
    L += [f"- {lead}",
          f"- URL screen at {p['url_screen_at_s']} s, text ends {p['text_end_s']} s, end card crossfade at "
          f"{p['xfade_offset_s']} s, total {p['total_s']} s, zoom over {p['zoom_frames']} frames", '',
          '| # | Line | Narration onset (s) | Video onset (s) |', '|---|---|---|---|']
    L += [f"| {r['n']} | {r['text']} | {r['narration_onset_s']} | {r['video_onset_s']} |" for r in t['lines']]
    L += ['', '## Text and audio', '',
          f"- Body font {f['body_size']} (standard {f['standard_size']}); widest line {f['body_widest_px']} px of {f['fit_limit_px']}",
          f"- Hook font {f['hook_size']}, URL font {f['url_size']}",
          f"- Voice {a['voice_lufs']} LUFS, gain {a['voice_gain_db']:+} dB; bed {a['bed_lufs']} LUFS, gain {a['bed_gain_db']:+} dB; "
          f"bed sits {a['bed_under_voice_lu']} LU under the voice before the final normalise",
          '', '## Warnings', '']
    L += [f'- {w}' for w in c['warnings']] or ['- none']
    return '\n'.join(L) + '\n'
