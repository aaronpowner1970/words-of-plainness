"""The per-post spec: load, validate, fill defaults. No audio or image access here."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ZONES = {'top': 760, 'middle': 960, 'lower': 1440}
ZONE_MIN, ZONE_MAX = 400, 1700
GROUP_SIZE = 3  # default screen grouping when "screens" is absent


class SpecError(ValueError):
    pass


@dataclass
class Line:
    text: str            # display text; "\n" is an explicit line break
    gold: bool = False
    italic: bool = False
    ref: str = ''        # scripture reference shown beneath the screen
    spoken: str = ''     # optional spoken-text override for forced alignment

    def spoken_words(self):
        return spoken_words(self.spoken or self.text)


@dataclass
class Spec:
    lines: list
    screens: list
    hook: list
    url_text: list
    url_spoken: bool
    zone_y: int
    credit: str
    image: str
    narration: str
    bed: str
    title: str = ''
    hook_seconds: float = 0.8
    url_seconds: float = 3.0
    url_gap: float = 1.4
    end_card_seconds: float = 3.0
    bed_under_voice_lu: float = 12.5
    timing: str = 'auto'
    raw: dict = field(default_factory=dict)


def spoken_words(text):
    """Display text -> the words the narrator says (lowercase, no punctuation).
    Dashes and hyphens split words ("Latter-day" -> "latter day")."""
    t = text.replace('’', "'").replace('‘', "'")
    t = re.sub(r'[—–\-/\n\\]', ' ', t)
    t = re.sub(r"[^A-Za-z0-9' ]", ' ', t)
    return [w for w in t.lower().split() if w.strip("'")]


def _bool(v, name):
    if not isinstance(v, bool):
        raise SpecError(f'"{name}" must be true or false')
    return v


def _num(d, key, default, lo, hi):
    v = d.get(key, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
        raise SpecError(f'"{key}" must be a number from {lo} to {hi}')
    return float(v)


def _str_list(v, name, max_len):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list) or not v or len(v) > max_len or not all(isinstance(x, str) and x.strip() for x in v):
        raise SpecError(f'"{name}" must be 1 to {max_len} non-empty strings')
    return v


def default_screens(n):
    return [list(range(i, min(i + GROUP_SIZE, n))) for i in range(0, n, GROUP_SIZE)]


def default_hook(last_text):
    """Split the final line into two balanced rows; the second row is gold."""
    words = last_text.replace('\n', ' ').split()
    if len(words) < 2:
        return [last_text]
    best = min(range(1, len(words)), key=lambda i: abs(len(' '.join(words[:i])) - len(' '.join(words[i:]))))
    return [' '.join(words[:best]), ' '.join(words[best:])]


def parse_spec(data):
    if not isinstance(data, dict):
        raise SpecError('the spec must be a JSON object')
    raw_lines = data.get('lines')
    if not isinstance(raw_lines, list) or not raw_lines:
        raise SpecError('"lines" is required: the spoken lines, in order')
    lines = []
    for i, item in enumerate(raw_lines):
        if isinstance(item, str):
            item = {'text': item}
        if not isinstance(item, dict) or not isinstance(item.get('text'), str) or not item['text'].strip():
            raise SpecError(f'line {i + 1} needs a "text"')
        unknown = set(item) - {'text', 'gold', 'italic', 'ref', 'spoken'}
        if unknown:
            raise SpecError(f'line {i + 1} has unknown keys: {sorted(unknown)}')
        ln = Line(text=item['text'].strip(), gold=_bool(item.get('gold', False), 'gold'),
                  italic=_bool(item.get('italic', False), 'italic'),
                  ref=str(item.get('ref', '')).strip(), spoken=str(item.get('spoken', '')).strip())
        if not ln.spoken_words():
            raise SpecError(f'line {i + 1} has no spoken words')
        lines.append(ln)
    n = len(lines)

    screens = data.get('screens')
    if screens is None:
        screens = default_screens(n)
    else:
        flat = [i for s in screens if isinstance(s, list) for i in s]
        if (not isinstance(screens, list) or not all(isinstance(s, list) and s for s in screens)
                or flat != list(range(n))):
            raise SpecError('"screens" must split line numbers 0 to %d, in order, each line exactly once' % (n - 1))

    hook = _str_list(data['hook'], 'hook', 2) if 'hook' in data else default_hook(lines[-1].text)
    url_text = _str_list(data['url_text'], 'url_text', 2) if 'url_text' in data else ['wordsofplainness.org']

    zone = data.get('text_zone', 'middle')
    if isinstance(zone, str) and zone in ZONES:
        zone_y = ZONES[zone]
    elif isinstance(zone, int) and not isinstance(zone, bool) and ZONE_MIN <= zone <= ZONE_MAX:
        zone_y = zone
    else:
        raise SpecError('"text_zone" must be top, middle, lower, or a y value from %d to %d' % (ZONE_MIN, ZONE_MAX))

    timing = data.get('timing', 'auto')
    if timing not in ('auto', 'pause', 'align'):
        raise SpecError('"timing" must be auto, pause or align')
    for key in ('image', 'narration', 'bed'):
        if not isinstance(data.get(key), str) or not data[key]:
            raise SpecError(f'"{key}" is required: the file name of the {key} input')

    return Spec(
        lines=lines, screens=screens, hook=hook, url_text=url_text,
        url_spoken=_bool(data.get('url_spoken', False), 'url_spoken'), zone_y=zone_y,
        credit=str(data.get('credit', 'Aaron Powner · Words of Plainness Ministry')),
        image=data['image'], narration=data['narration'], bed=data['bed'], title=str(data.get('title', '')),
        hook_seconds=_num(data, 'hook_seconds', 0.8, 0.3, 3),
        url_seconds=_num(data, 'url_seconds', 3.0, 1, 10),
        url_gap=_num(data, 'url_gap', 1.4, 0, 5),
        end_card_seconds=_num(data, 'end_card_seconds', 3.0, 1.5, 6),
        bed_under_voice_lu=_num(data, 'bed_under_voice_lu', 12.5, 8, 18),
        timing=timing, raw=data)


def load_spec(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise SpecError(f'{path} is not valid JSON: {e}')
    return parse_spec(data)


def resolve_media(spec, media_dir):
    """Absolute paths of the three inputs; each must exist."""
    out = {}
    for key in ('image', 'narration', 'bed'):
        p = Path(getattr(spec, key))
        p = p if p.is_absolute() else Path(media_dir) / p
        if not p.is_file():
            raise SpecError(f'{key} file not found: {p}')
        out[key] = p
    return out
