"""Still images: the framed background, end card and cover. Pure Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HERE = Path(__file__).resolve().parent.parent
FONT_DIR = HERE / 'fonts'
LOGO_PATH = HERE.parent.parent.parent / 'src' / 'assets' / 'images' / 'lantern_logo_line_art.png'
GOLD = (239, 194, 79)
CREAM = (245, 234, 216)
CREDIT_TAN = (200, 178, 140)
HEADER_H = 352


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size)


F_MED = 'eb-garamond-latin-500-normal.ttf'
F_SEMI = 'eb-garamond-latin-600-normal.ttf'
F_ITAL = 'eb-garamond-latin-500-italic.ttf'


def source_width_warning(path):
    with Image.open(path) as im:
        w, h = im.size
    if w < W:
        scale = max(W / w, H / h)
        return (f'The source image is {w}x{h}, narrower than {W} px, so it is enlarged about {scale:.2f}x '
                f'and will look soft.')
    return None


def scene(image_path, zone_y, scrim_half):
    """Cover-crop to 1080x1920, scrim behind the text zone, gradient for the credit line."""
    im = Image.open(image_path).convert('RGB')
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    top, bot = max(0, zone_y - scrim_half), min(H, zone_y + scrim_half)
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rectangle([0, top, W, bot], fill=140)
    m = m.filter(ImageFilter.GaussianBlur(115))
    im = Image.composite(Image.new('RGB', (W, H), (10, 8, 6)), im, m)
    b = Image.new('L', (W, H), 0)
    bd = ImageDraw.Draw(b)
    for yy in range(H - 280, H):
        bd.line([(0, yy), (W, yy)], fill=int(205 * (yy - (H - 280)) / 280))
    return Image.composite(Image.new('RGB', (W, H), (8, 6, 4)), im, b)


def _logo(height):
    lg = Image.open(LOGO_PATH).convert('RGBA')
    return lg.resize((int(lg.width * height / lg.height), height), Image.LANCZOS)


def header(img):
    band = Image.new('RGBA', (W, HEADER_H), (12, 9, 6, int(255 * 0.5)))
    mask = Image.new('L', (W, HEADER_H), 255)
    md = ImageDraw.Draw(mask)
    for y in range(300, HEADER_H):
        md.line([(0, y), (W, y)], fill=int(255 * (HEADER_H - y) / 52))
    img = img.convert('RGBA')
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    layer.paste(band, (0, 0), mask)
    img = Image.alpha_composite(img, layer)
    d = ImageDraw.Draw(img)
    d.line([(0, 350), (W, 350)], fill=GOLD + (180,), width=2)
    lg = _logo(250)
    img.alpha_composite(lg, (150 - lg.width // 2, 50))
    d = ImageDraw.Draw(img)
    x = 290
    d.text((x, 92), 'WORDS OF PLAINNESS', font=font(F_SEMI, 56), fill=GOLD)
    d.line([(x, 168), (x + 700, 168)], fill=GOLD, width=2)
    d.text((x, 196), 'wordsofplainness.org', font=font(F_MED, 38), fill=CREAM)
    return img.convert('RGB')


def framed(bg, credit):
    fr = header(bg)
    d = ImageDraw.Draw(fr)
    cf = font(F_ITAL, 30)
    d.text(((W - d.textlength(credit, font=cf)) / 2, H - 120), credit, font=cf, fill=CREDIT_TAN)
    return fr


def end_card(bg, url_text):
    ec = Image.blend(bg, Image.new('RGB', (W, H), (0, 0, 0)), 0.78)
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W / 2 - 300, 520, W / 2 + 300, 1220], fill=200)
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    ec = Image.composite(Image.new('RGB', (W, H), (232, 160, 76)), ec, glow.point(lambda v: int(v * 0.40))).convert('RGBA')
    lg = _logo(480)
    ec.alpha_composite(lg, ((W - lg.width) // 2, 580))
    d = ImageDraw.Draw(ec)
    f = font(F_SEMI, 64)
    t = url_text[0]
    d.text(((W - d.textlength(t, font=f)) / 2, 1110), t, font=f, fill=CREAM)
    return ec.convert('RGB')


def cover(bg, hook, zone_y, hook_size):
    cv = header(bg.copy()).convert('RGBA')
    strip = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(strip).rectangle([0, zone_y - 200, W, zone_y + 200], fill=(10, 8, 6, 90))
    cv = Image.alpha_composite(cv, strip.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(cv)
    f = font(F_MED, hook_size)
    pitch = int(hook_size * 1.3)
    y0 = zone_y - (len(hook) * pitch) // 2
    for i, line in enumerate(hook):
        col = GOLD if (i == 1 or len(hook) == 1) else CREAM
        d.text(((W - d.textlength(line, font=f)) / 2, y0 + i * pitch), line, font=f, fill=col)
    return cv.convert('RGB')
