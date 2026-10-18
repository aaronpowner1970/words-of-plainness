"""Kinetic text: ASS subtitle generation, plus measuring text with the same libass the encode uses."""
import shutil
from pathlib import Path

from PIL import Image, ImageFont

from . import media
from .visuals import FONT_DIR, F_MED, W, H

GOLD = '&H4FC2EF&'    # BGR of #EFC24F
CREAM = '&HD8EAF5&'   # BGR of #F5EAD8
FIT_WIDTH = 960       # widest line must fit inside this many pixels
FS_CAP = 92           # the approved standard size
FS_FLOOR = 40
HOOK_CAP = 92
URL_CAP = 96
FADE_IN_MS = 350


def ts(t):
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f'{h}:{m:02d}:{s:05.2f}'


def esc(text):
    return text.replace('\n', '\\N')


def header_block(fs):
    return '\n'.join([
        '[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {W}', f'PlayResY: {H}', 'WrapStyle: 2', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, '
        'Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, '
        'MarginR, MarginV, Encoding',
        f'Style: K,EB Garamond Medium,{fs},&H00D8EAF5,&H00D8EAF5,&H00060809,&H96000000,0,0,0,0,100,100,0,0,1,2,4,5,60,60,0,1',
        'Style: R,EB Garamond Medium,54,&H00A8C4DC,&H00A8C4DC,&H00060809,&H96000000,0,1,0,0,100,100,1,0,1,0,2,5,60,60,0,1',
        '', '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'])


# ---------------- measuring (libass, same as the final encode) ----------------

def _render_ass(workdir, ass_text, out_png):
    wd = Path(workdir)
    (wd / 'm.ass').write_text(ass_text, encoding='utf-8')
    fonts = wd / 'fonts'
    if not fonts.exists():
        shutil.copytree(FONT_DIR, fonts, ignore=shutil.ignore_patterns('*.txt'))
    media.ffmpeg('-f', 'lavfi', '-i', f'color=c=0x808080:s={W}x{H}:d=1:r=1', '-vf',
                 'ass=m.ass:fontsdir=fonts', '-frames:v', '1', out_png, cwd=str(wd))
    return Image.open(wd / out_png).convert('L')


def _ink_bbox(im, y0, y1):
    """Bounding box of pixels that differ from the grey background inside rows y0..y1."""
    band = im.crop((0, y0, W, y1)).point(lambda v: 255 if abs(v - 128) > 24 else 0)
    return band.getbbox()


def measure_lines(workdir, items):
    """items: [(text with \\N, font size)]. Returns [(width, height)] of the drawn ink, bands of 400 px."""
    out = []
    for i in range(0, len(items), 4):
        chunk = items[i:i + 4]
        events = [f'Dialogue: 0,0:00:00.00,0:00:01.00,K,,0,0,0,,{{\\pos(540,{200 + 400 * j})\\fs{fs}\\alpha&H00&}}{esc(t)}'
                  for j, (t, fs) in enumerate(chunk)]
        im = _render_ass(workdir, header_block(60) + '\n' + '\n'.join(events) + '\n', 'm.png')
        for j in range(len(chunk)):
            bb = _ink_bbox(im, 400 * j, 400 * j + 400)
            out.append((bb[2] - bb[0], bb[3] - bb[1]) if bb else (0, 0))
    return out


def measure_block(workdir, text, fs):
    im = _render_ass(workdir, header_block(60) + '\n' + f'Dialogue: 0,0:00:00.00,0:00:01.00,K,,0,0,0,,'
                     f'{{\\pos(540,960)\\fs{fs}\\alpha&H00&}}{esc(text)}\n', 'b.png')
    bb = _ink_bbox(im, 0, H)
    return (bb[2] - bb[0], bb[3] - bb[1]) if bb else (0, 0)


def _pil_width(text, size):
    f = ImageFont.truetype(str(FONT_DIR / F_MED), size)
    return f.getlength(text)


def fit_font(workdir, texts, cap, limit=FIT_WIDTH):
    """Largest integer size, at most `cap`, at which every explicit line of `texts` is no wider than
    `limit` px as libass draws it. Returns (size, widest_px_at_that_size)."""
    lines = sorted({ln for t in texts for ln in t.split('\n')}, key=lambda s: -_pil_width(s, 100))[:3]

    def widest(fs):
        return max(w for w, _ in measure_lines(workdir, [(ln, fs) for ln in lines]))

    lo, hi = FS_FLOOR, cap
    if widest(hi) <= limit:
        return hi, widest(hi)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if widest(mid) <= limit:
            lo = mid
        else:
            hi = mid
    return lo, widest(lo)


# ---------------- the subtitle file ----------------

def build_ass(spec, fs, hook_fs, url_fs, onsets, url0, text_end, ref_ys):
    """onsets: absolute start time of each line. ref_ys: {screen index: y of the scripture reference}."""
    y = spec.zone_y
    lines, screens = spec.lines, spec.screens

    def seg(k, visible, fade):
        ln = lines[k]
        tag = '{\\c' + (GOLD if ln.gold else CREAM) + ('\\i1' if ln.italic else '\\i0')
        if not visible:
            tag += '\\alpha&HFF&'
        elif fade:
            tag += '\\alpha&HFF&\\t(0,%d,\\alpha&H00&)' % FADE_IN_MS
        else:
            tag += '\\alpha&H00&'
        return tag + '}' + esc(ln.text)

    out = [header_block(fs)]
    for si, sc in enumerate(screens):
        screen_end = onsets[screens[si + 1][0]] if si + 1 < len(screens) else url0
        for j, k in enumerate(sc):
            st = onsets[k]
            en = onsets[sc[j + 1]] if j + 1 < len(sc) else screen_end
            body = '\\N\\N'.join(seg(m, m <= k, m == k) for m in sc)
            fo = '{\\fad(0,300)}' if j == len(sc) - 1 else ''
            out.append(f'Dialogue: 0,{ts(st)},{ts(en)},K,,0,0,0,,{fo}{{\\pos(540,{y})}}{body}')
        refs = [k for k in sc if lines[k].ref]
        if refs:
            k = refs[0]
            st = onsets[k] + 0.4
            out.append(f'Dialogue: 0,{ts(st)},{ts(screen_end)},R,,0,0,0,,{{\\fad(350,300)\\pos(540,{ref_ys[si]})}}'
                       f'{lines[k].ref}')
    hook = '\\N'.join((('{\\c%s}' % GOLD) if (i == 1 or len(spec.hook) == 1) else '') + esc(t)
                      for i, t in enumerate(spec.hook))
    out.append(f'Dialogue: 1,{ts(0)},{ts(spec.hook_seconds)},K,,0,0,0,,{{\\fad(0,250)\\pos(540,{y})\\fs{hook_fs}}}{hook}')
    url = '\\N'.join((('{\\c%s}' % GOLD) if i == 1 else '') + esc(t) for i, t in enumerate(spec.url_text))
    out.append(f'Dialogue: 0,{ts(url0)},{ts(text_end)},K,,0,0,0,,{{\\fad(350,300)\\pos(540,{y})\\fs{url_fs}}}{url}')
    return '\n'.join(out) + '\n'
