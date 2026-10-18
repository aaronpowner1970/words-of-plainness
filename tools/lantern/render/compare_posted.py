#!/usr/bin/env python3
"""Compare a render with the video that was actually posted. Manual tool: it needs the posted video,
which is Aaron's media and never lives in the repo. Needs numpy and Pillow.

    python tools/lantern/render/compare_posted.py SPEC.json --render OUT_DIR --posted POSTED.mp4 --report DIR --name A

Writes DIR/<name>_compare.json, DIR/<name>_compare.md and DIR/<name>_strip.png (posted on the top row,
render on the bottom row). Line onsets are judged from the pixels of both videos with the same detector:
the first frame at which a line's rows hold 10% of the text-coloured pixels they hold once fully faded in."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lantern_render import media  # noqa: E402
from lantern_render.spec import load_spec  # noqa: E402

FPS = 30
SCALE = 2           # decode the text zone at half size
ONSET_FRACTION = 0.10
COLOURS = np.array([(245, 234, 216), (239, 194, 79)], dtype=np.int32)
COLOUR_TOL = 38
ZONE_HALF = 440
HEADER_BOTTOM = 380  # keep the header band and its gold rule out of the text search
MIN_BAND_ROWS = 8     # half-resolution rows; thinner runs are noise, not a line of text


def zone_frames(video, y_mid, seconds):
    """Yield (t, boolean text-colour mask) for the rows around the text zone, every frame."""
    y0 = max(HEADER_BOTTOM, y_mid - ZONE_HALF)
    h = (min(1920, y_mid + ZONE_HALF - 40) - y0) // 2 * 2
    cmd = [media._bin('ffmpeg'), '-v', 'error', '-i', str(video), '-t', str(seconds),
           '-vf', f'fps={FPS},crop=1080:{h}:0:{y0},scale={1080 // SCALE}:{h // SCALE},format=rgb24',
           '-f', 'rawvideo', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    w, hh = 1080 // SCALE, h // SCALE
    size = w * hh * 3
    i = 0
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        a = np.frombuffer(buf, dtype=np.uint8).reshape(hh, w, 3).astype(np.int32)
        d = np.abs(a[:, :, None, :] - COLOURS[None, None, :, :]).max(axis=3).min(axis=2)
        yield i / FPS, d < COLOUR_TOL
        i += 1
    p.wait()
    yield None, (y0, h)


def row_series(video, y_mid, seconds):
    rows, y0h = [], None
    for t, m in zone_frames(video, y_mid, seconds):
        if t is None:
            y0h = m
        else:
            rows.append(m.sum(axis=1))
    return np.array(rows), y0h


def bands_from(profile, min_gap=6, min_peak=4):
    """Contiguous runs of rows (half-res) whose peak text-pixel count over time is above a floor."""
    peak = profile.max(axis=0)
    on = peak > min_peak
    bands, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        if not v and start is not None:
            bands.append([start, i])
            start = None
    if start is not None:
        bands.append([start, len(on)])
    bands = [b for b in bands if b[1] - b[0] >= MIN_BAND_ROWS]
    merged = []
    for b in bands:
        if merged and b[0] - merged[-1][1] < min_gap:
            merged[-1][1] = b[1]
        else:
            merged.append(b)
    return merged


def line_onsets(profile, spec, plan_onsets, hook_s):
    """Return a list (one per spoken line) of detected onset seconds, or None when a screen cannot be read."""
    n = len(spec.lines)
    out = [None] * n
    ends = [plan_onsets[sc[0]] for sc in spec.screens[1:]] + [plan_onsets[-1] + 3.0]
    for si, sc in enumerate(spec.screens):
        t0 = max(plan_onsets[sc[0]] - 0.02, hook_s + 0.05)
        t1 = ends[si] - 0.4
        f0, f1 = int(t0 * FPS), int(t1 * FPS)
        window = profile[f0:f1]
        if len(window) < 3:
            continue
        bands = bands_from(window)
        expected = sum(spec.lines[k].text.count('\n') + 1 for k in sc)
        if len(bands) != expected:
            continue
        bi = 0
        for k in sc:
            nb = spec.lines[k].text.count('\n') + 1
            b0, b1 = bands[bi]
            bi += nb
            series = window[:, b0:b1].sum(axis=1)
            plateau = series.max()
            if plateau <= 0:
                continue
            hit = np.argmax(series > ONSET_FRACTION * plateau)
            out[k] = round((f0 + int(hit)) / FPS, 3)
    return out


def gold_mask(img):
    a = np.asarray(img.convert('RGB')).astype(np.int32)
    return np.abs(a - np.array((239, 194, 79))).max(axis=2) < 45


def frame_at(video, t, scale_w=270):
    p = subprocess.run([media._bin('ffmpeg'), '-v', 'error', '-ss', f'{t:.3f}', '-i', str(video), '-frames:v', '1',
                        '-f', 'image2pipe', '-vcodec', 'png', '-'], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    im = Image.open(__import__('io').BytesIO(p.stdout)).convert('RGB')
    return im


def header_check(posted, mine):
    """Header band and logo present in both: compare the gold-ink masks of the header and of the logo corner."""
    a, b = frame_at(posted, 1.0), frame_at(mine, 1.0)
    out = {}
    for name, box in (('header', (0, 0, 1080, 352)), ('logo', (20, 40, 280, 310))):
        ma, mb = gold_mask(a.crop(box)), gold_mask(b.crop(box))
        inter, union = (ma & mb).sum(), (ma | mb).sum()
        out[name] = {'gold_pixels_posted': int(ma.sum()), 'gold_pixels_render': int(mb.sum()),
                     'overlap_iou': round(float(inter / union), 3) if union else 0.0}
    out['pass'] = (out['logo']['gold_pixels_render'] > 500 and out['header']['gold_pixels_render'] > 1500
                   and out['logo']['overlap_iou'] > 0.6 and out['header']['overlap_iou'] > 0.5)
    return out


def strip(posted, mine, times, path, w=300):
    h = int(w * 16 / 9)
    sheet = Image.new('RGB', (w * len(times), h * 2 + 30), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(times):
        for row, vid in enumerate((posted, mine)):
            im = frame_at(vid, t).resize((w, h), Image.LANCZOS)
            sheet.paste(im, (i * w, row * h + 30))
        d.text((i * w + 6, 8), f't = {t:.1f} s   (top: posted, bottom: render)', fill=(230, 230, 230))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--render', required=True)
    ap.add_argument('--posted', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--name', required=True)
    a = ap.parse_args()
    spec = load_spec(a.spec)
    chk = json.loads((Path(a.render) / 'check.json').read_text(encoding='utf-8'))
    mine = Path(a.render) / 'out.mp4'
    posted = Path(a.posted)
    rep = Path(a.report)
    rep.mkdir(parents=True, exist_ok=True)

    pi, mi = media.ffprobe_json(posted), media.ffprobe_json(mine)
    pv = next(s for s in pi['streams'] if s['codec_type'] == 'video')
    dp, dm = float(pi['format']['duration']), float(mi['format']['duration'])
    lp = media.loudnorm_stats(posted)['input_i']
    lm = media.loudnorm_stats(mine)['input_i']
    plan = [r['video_onset_s'] for r in chk['timing']['lines']]
    hook_s = chk['plan']['hook_s']
    seconds = min(dp, dm)

    prof_p, _ = row_series(posted, spec.zone_y, seconds)
    prof_m, _ = row_series(mine, spec.zone_y, seconds)
    on_p = line_onsets(prof_p, spec, plan, hook_s)
    on_m = line_onsets(prof_m, spec, plan, hook_s)
    rows = []
    for i, ln in enumerate(spec.lines):
        d = None if on_p[i] is None or on_m[i] is None else round(on_m[i] - on_p[i], 3)
        rows.append({'n': i + 1, 'text': ln.text.replace('\n', ' / '), 'planned_s': plan[i], 'posted_s': on_p[i],
                     'render_s': on_m[i], 'render_minus_posted_s': d, 'within_0.25s': None if d is None else abs(d) <= 0.25})
    judged = [r for r in rows if r['within_0.25s'] is not None]
    hdr = header_check(posted, mine)
    result = {
        'resolution': {'posted': [pv['width'], pv['height']], 'render': [chk['output']['width'], chk['output']['height']],
                       'pass': [pv['width'], pv['height']] == [chk['output']['width'], chk['output']['height']]},
        'length_s': {'posted': round(dp, 3), 'render': round(dm, 3), 'difference': round(dm - dp, 3), 'pass': abs(dm - dp) <= 0.5},
        'loudness_lufs': {'posted': round(lp, 2), 'render': round(lm, 2), 'difference': round(lm - lp, 2), 'pass': abs(lm - lp) <= 0.5},
        'header_and_logo': hdr,
        'onsets': {'lines': rows, 'judged': len(judged), 'of': len(rows),
                   'max_abs_difference_s': max((abs(r['render_minus_posted_s']) for r in judged), default=None),
                   'pass': bool(judged) and all(r['within_0.25s'] for r in judged)},
    }
    (rep / f'{a.name}_compare.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    L = [f'# {a.name}: render vs posted video', '',
         f"- Resolution: posted {result['resolution']['posted']}, render {result['resolution']['render']}: {'PASS' if result['resolution']['pass'] else 'FAIL'}",
         f"- Length: posted {dp:.2f} s, render {dm:.2f} s ({dm - dp:+.2f}): {'PASS' if result['length_s']['pass'] else 'FAIL'} (limit 0.5 s)",
         f"- Loudness: posted {lp:.2f} LUFS, render {lm:.2f} LUFS ({lm - lp:+.2f}): {'PASS' if result['loudness_lufs']['pass'] else 'FAIL'} (limit 0.5 LU)",
         f"- Header and logo: {'PASS' if hdr['pass'] else 'FAIL'} (logo overlap {hdr['logo']['overlap_iou']}, header overlap {hdr['header']['overlap_iou']})",
         f"- Line onsets: {len(judged)} of {len(rows)} lines judged; largest difference {result['onsets']['max_abs_difference_s']} s: "
         f"{'PASS' if result['onsets']['pass'] else 'FAIL'} (limit 0.25 s)", '',
         '| # | Line | Planned (s) | Posted frames (s) | Render frames (s) | Difference |', '|---|---|---|---|---|---|']
    L += [f"| {r['n']} | {r['text']} | {r['planned_s']} | {r['posted_s']} | {r['render_s']} | {r['render_minus_posted_s']} |" for r in rows]
    (rep / f'{a.name}_compare.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    p = chk['plan']
    first = chk['timing']['lines'][0]['video_onset_s']
    mid = chk['timing']['lines'][len(rows) // 2]['video_onset_s']
    times = [0.4, first + 0.9, mid + 0.9, (plan[-1] + p['url_screen_at_s']) / 2 + 0.3, p['url_screen_at_s'] + 1.0, dm - 0.6]
    strip(posted, mine, [min(t, seconds - 0.1) for t in times], rep / f'{a.name}_strip.png')
    print('\n'.join(L))
    ok = all(result[k]['pass'] for k in ('resolution', 'length_s', 'loudness_lufs', 'header_and_logo', 'onsets'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
