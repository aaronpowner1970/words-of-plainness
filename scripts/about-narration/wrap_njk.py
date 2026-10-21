# Wrap narrated targets in about.njk with {% narr "id" %}...{% endnarr %}. Prose is untouched.
import re, sys
from pathlib import Path
SRC = Path(r'C:\Users\aaron\Documents\words-of-plainness\src\pages\about.njk')
s = SRC.read_text(encoding='utf-8')
orig = s

def sentences(txt):
    out, last = [], 0
    for m in re.finditer(r'[.!?]["”)]*\s+(?=["“A-Z])', txt):
        end = m.start() + len(m.group(0).rstrip())
        out.append(txt[last:end]); last = m.end()
    out.append(txt[last:])
    return [o.strip() for o in out if o.strip()]

def narr(i, t): return '{% narr "' + i + '" %}' + t + '{% endnarr %}'

def wrap_p(m, sec, counter):
    open_tag, inner, close = m.group(1), m.group(2), '</p>'
    if 'about-byline' in open_tag or 'about-signature' in open_tag: return m.group(0)
    counter[0] += 1; n = counter[0]
    indent = re.match(r'\n?(\s*)', inner).group(1) or '            '
    parts = []
    t = re.match(r'\s*(<strong class="text-gold">)(.*?)(</strong>)\s*', inner, re.S)
    if t:
        parts.append(t.group(1) + narr(f'{sec}-p{n}-t', t.group(2)) + t.group(3))
        inner = inner[t.end():]
    for k, snt in enumerate(sentences(inner), 1):
        parts.append(narr(f'{sec}-p{n}-s{k}', snt))
    return open_tag + '\n' + '\n'.join(indent + p for p in parts) + '\n' + indent[:-4] + close

def process(section_id, sec, start_marker=None, end_marker=None):
    global s
    a = s.index(f'id="{section_id}"'); b = s.index('</section>', a)
    seg = s[a:b]
    lo = seg.index(start_marker) if start_marker else 0
    hi = seg.index(end_marker, lo) if end_marker else len(seg)
    body = seg[lo:hi]
    counter = [0]
    body2 = re.sub(r'(<p(?:\s[^>]*)?>)(.*?)</p>', lambda m: wrap_p(m, sec, counter), body, flags=re.S)
    s = s[:a] + seg[:lo] + body2 + seg[hi:] + s[b:]

process('brother-aaron', 'bio', start_marker='<p>\n            Welcome', end_marker='<figure')
process('philosophy', 'phil')
process('ai-disclosure', 'how', end_marker='<p class="about-signature">')

def sub1(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
sub1('<h2>Ministry Philosophy</h2>', '<h2>{% narr "phil-h" %}Ministry Philosophy{% endnarr %}</h2>')
sub1('<h2 id="how-this-is-made">How This Work Is Made</h2>', '<h2 id="how-this-is-made">{% narr "how-h" %}How This Work Is Made{% endnarr %}</h2>')
sub1('<figcaption>\n                Every face here', '<figcaption>\n                {% narr "collage-cap" %}Every face here')
sub1('One Voice, One Mind</a>.”\n            </figcaption>', 'One Voice, One Mind</a>.”{% endnarr %}\n            </figcaption>')
sub1('<figcaption>\n                My workspace in our RV, from a real photograph tidied up with AI and Photoshop.\n            </figcaption>',
     '<figcaption>\n                {% narr "workspace-cap" %}My workspace in our RV, from a real photograph tidied up with AI and Photoshop.{% endnarr %}\n            </figcaption>')
sub1('<p class="about-signature">\n            — Brother Aaron Powner<br>', '<p class="about-signature">\n            {% narr "sig" %}— Brother Aaron Powner{% endnarr %}<br>')

Path(sys.argv[1]).write_text(s, encoding='utf-8')
# prose-equality check
strip = lambda t: re.sub(r'\s+', ' ', re.sub(r'\{%\s*(end)?narr[^%]*%\}', '', t)).strip()
a, b = strip(orig), strip(s)
# the only whitespace-level normalisation: tags adjacent to newlines; compare with tag-adjacent spaces removed
norm = lambda t: re.sub(r'\s*(<[^>]+>)\s*', r'\1', t)
print('prose identical:', norm(a) == norm(b), '| narr targets:', len(re.findall(r'\{% narr ', s)))
