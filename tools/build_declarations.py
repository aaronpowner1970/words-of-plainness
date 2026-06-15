# -*- coding: utf-8 -*-
"""
Transform the Declarations source .md files into Words of Plainness study .njk pages.
Both sources share the same apparatus shape; one transform handles both.

Deliverables:
  src/pages/studies/declarations/creedal-core.njk   (19 declaration cards)
  src/pages/studies/declarations/expanded-tent.njk  (18 declaration cards)
"""
import re
import os

SRC_DIR = r"C:\Users\aaron\Documents\working-folder\Articles_of_Interfaith_Discipleship_Essay_Cluster\Research"
OUT_DIR = r"C:\Users\aaron\Documents\words-of-plainness\src\pages\studies\declarations"

# ── Verbatim <style> block (pasted into both pages) ──────────────────────────
STYLE_BLOCK = r"""<style>
/* ── DECLARATIONS (reader-first) ─────────────────────── */
.decl-intro { max-width:720px; margin:0 auto 1.5rem; font-family:'Crimson Pro',Georgia,serif; font-size:1.1rem; line-height:1.75; color:var(--cream); opacity:.92; }
.decl-intro p { margin-bottom:1rem; }
.decl-method, .decl-methodology { max-width:760px; margin:1.5rem auto; }
.decl-method > summary, .decl-methodology > summary { cursor:pointer; font-family:'Crimson Pro',Georgia,serif; font-size:1.05rem; color:var(--gold-primary); font-weight:600; list-style:none; padding:.4rem 0; }
.decl-method > summary::-webkit-details-marker, .decl-methodology > summary::-webkit-details-marker { display:none; }
.decl-method > summary::before, .decl-methodology > summary::before { content:'\25B8'; display:inline-block; margin-right:.5rem; transition:transform .2s; color:var(--gold-primary); }
.decl-method[open] > summary::before, .decl-methodology[open] > summary::before { transform:rotate(90deg); }
.decl-method ol { font-family:'Crimson Pro',Georgia,serif; font-size:1.02rem; line-height:1.65; color:var(--cream); opacity:.88; padding-left:1.4rem; }
.decl-method li { margin-bottom:.6rem; }

.decl-card { max-width:760px; margin:0 auto 1.75rem; padding:1.5rem 1.75rem; background:rgba(196,148,58,0.035); border:1px solid rgba(196,148,58,0.18); border-radius:var(--radius-sm); }
.decl-num { color:var(--gold-primary); font-weight:600; margin-right:.4rem; }
.decl-title { font-family:'Crimson Pro',Georgia,serif; font-size:1.3rem; font-weight:600; color:var(--cream); margin:0 0 .9rem; }
.decl-statement { font-family:'Crimson Pro',Georgia,serif; font-size:1.12rem; font-style:italic; line-height:1.7; color:var(--cream); opacity:.95; margin:0 0 1rem; padding:.25rem 0 .25rem 1.1rem; border-left:3px solid var(--gold-primary); }
.decl-rating { font-family:'Crimson Pro',Georgia,serif; font-size:1rem; line-height:1.6; color:var(--cream); opacity:.9; margin:0 0 .75rem; }
.decl-pill { display:inline-block; font-size:.74rem; letter-spacing:.04em; text-transform:uppercase; font-weight:700; padding:.18rem .5rem; border-radius:1rem; margin-right:.5rem; vertical-align:.06em; }
.decl-pill-pass { background:rgba(196,148,58,0.18); color:var(--gold-light); border:1px solid rgba(196,148,58,0.45); }
.decl-pill-qual { background:rgba(196,148,58,0.10); color:#d8b77a; border:1px solid rgba(196,148,58,0.30); }
.decl-pill-fail { background:rgba(122,48,64,0.20); color:#d98a9a; border:1px solid rgba(122,48,64,0.5); }
.decl-pct { color:var(--gold-primary); font-weight:600; margin-right:.35rem; }
.decl-readerspace { font-family:'Crimson Pro',Georgia,serif; font-size:.98rem; line-height:1.6; color:var(--cream); opacity:.82; margin:0 0 .85rem; padding:.6rem .9rem; background:rgba(245,230,208,0.04); border-radius:var(--radius-sm); }
.decl-readerspace strong { color:var(--gold-primary); }
.decl-readerspace em { font-style:italic; }
details.decl-witness { margin-top:.25rem; }
details.decl-witness > summary { cursor:pointer; font-family:'Crimson Pro',Georgia,serif; font-size:.92rem; letter-spacing:.02em; color:var(--gold-primary); list-style:none; padding:.3rem 0; opacity:.9; }
details.decl-witness > summary::-webkit-details-marker { display:none; }
details.decl-witness > summary::before { content:'\25B8'; display:inline-block; margin-right:.45rem; transition:transform .2s; }
details.decl-witness[open] > summary::before { transform:rotate(90deg); }
.decl-witness-body { padding:.6rem 0 .2rem; }
.decl-stack { font-family:'Crimson Pro',Georgia,serif; font-size:.96rem; line-height:1.65; color:var(--cream); opacity:.86; margin:0 0 .55rem; }
.decl-stack strong { color:var(--gold-primary); font-weight:600; }
.decl-meta-rule { border:none; border-top:1px solid rgba(196,148,58,0.18); margin:.9rem 0; }
.decl-meta { font-family:'Crimson Pro',Georgia,serif; font-size:.94rem; line-height:1.6; color:var(--cream); opacity:.82; margin:0 0 .5rem; }
.decl-meta strong { color:var(--gold-primary); font-weight:600; }
.decl-flag strong { color:#d98a9a; }
.decl-card a.scripture-link { color:var(--gold-primary); text-decoration:none; border-bottom:1px dotted rgba(196,148,58,0.5); transition:color .2s, border-color .2s; }
.decl-card a.scripture-link:hover { color:var(--gold-light); border-bottom-color:var(--gold-light); }
.decl-boundary { max-width:760px; margin:1.5rem auto; }
.decl-boundary-item { margin:0 auto 1.25rem; padding:1.1rem 1.4rem; background:rgba(122,48,64,0.06); border-left:3px solid rgba(122,48,64,0.5); border-radius:0 var(--radius-sm) var(--radius-sm) 0; }
.decl-boundary-item h4 { font-family:'Crimson Pro',Georgia,serif; font-size:1.08rem; font-weight:600; color:#d98a9a; margin:0 0 .5rem; }
.decl-boundary-item p { font-family:'Crimson Pro',Georgia,serif; font-size:1rem; line-height:1.65; color:var(--cream); opacity:.88; margin:0 0 .5rem; }
.decl-boundary-refs { font-size:.9rem; opacity:.85; }
.decl-boundary-item a.scripture-link { color:var(--gold-primary); text-decoration:none; border-bottom:1px dotted rgba(196,148,58,0.5); }
@media (max-width:768px){ .decl-card{padding:1.2rem 1.15rem;} }
</style>"""

EMDASH = "—"
ENDASH = "–"

LINK_RE = re.compile(r'\[\[(.+?)\]\{\.underline\}\]\(([^)]+)\)')


def collapse_ws(s):
    return re.sub(r'\s+', ' ', s).strip()


def typography(s):
    """Apply WoP typography to a chunk of plain prose (no pandoc links).
    Em/en dashes -> literal U+2014 / U+2013; apostrophes/quotes/ampersand -> entities."""
    s = s.replace('&', '&amp;')
    # normalise any pre-existing curly punctuation to entities
    s = s.replace('’', '&rsquo;').replace('‘', '&lsquo;')
    s = s.replace('“', '&ldquo;').replace('”', '&rdquo;')
    # dashes (em before en)
    s = s.replace('---', EMDASH).replace('--', ENDASH)
    # escaped apostrophe -> placeholder
    s = s.replace("\\'", '\x01')
    # straight double quotes -> alternating curly entities
    out = []
    open_q = True
    for ch in s:
        if ch == '"':
            out.append('&ldquo;' if open_q else '&rdquo;')
            open_q = not open_q
        else:
            out.append(ch)
    s = ''.join(out)
    # remaining straight single quotes -> right single
    s = s.replace("'", '&rsquo;')
    s = s.replace('\x01', '&rsquo;')
    return s


def convert(text):
    """Collapse whitespace, convert pandoc scripture links to <a> (URL verbatim,
    visible text typographed), then typograph the surrounding prose."""
    text = collapse_ws(text)
    links = []

    def repl(m):
        visible = typography(collapse_ws(m.group(1)))
        url = m.group(2).strip()
        links.append(
            '<a class="scripture-link" href="%s" target="_blank" rel="noopener">%s</a>'
            % (url, visible)
        )
        return '\x00%d\x00' % (len(links) - 1)

    text = LINK_RE.sub(repl, text)
    text = typography(text)
    text = re.sub(r'\x00(\d+)\x00', lambda m: links[int(m.group(1))], text)
    return text


def deblock(s):
    return '\n'.join(re.sub(r'^>\s?', '', ln) for ln in s.split('\n'))


def strip_italic(s):
    s = s.strip()
    if s.startswith('**') and s.endswith('**'):
        return s
    if s.startswith('*') and s.endswith('*'):
        s = s[1:-1]
    return s


def split_paras(text):
    return [p for p in re.split(r'\n[ \t]*\n', text) if p.strip()]


# ── Declaration card ─────────────────────────────────────────────────────────

PILL = {
    'PASS': ('Widely shared', 'decl-pill-pass'),
    'QUALIFIED': ('Shared, with care', 'decl-pill-qual'),
    'FAIL': ('Beyond the shared floor', 'decl-pill-fail'),
}

RATING_RE = re.compile(
    r'^\*\*\s*(.+?):\s*(PASS|QUALIFIED|FAIL)\s*\*\*\s*(?:~([\d.]+%)\s*)?(?:---\s*)?(.*)$',
    re.DOTALL)
META_RE = re.compile(r'^\*\*(.+?)\*\*\s*(.*)$', re.DOTALL)
TITLE_RE = re.compile(r'^\*\*(\d{2})\s+(.+?)\*\*$', re.DOTALL)


def build_card(block):
    chunks = split_paras(block)
    # title
    m = TITLE_RE.match(collapse_ws(chunks[0]))
    num, title = m.group(1), typography(collapse_ws(m.group(2)))

    # locate WITNESS STACK marker
    idx_ws = next(i for i, c in enumerate(chunks)
                  if collapse_ws(c) == '**WITNESS STACK**')
    statement = typography(strip_italic(collapse_ws(deblock(chunks[1]))))
    witness_block = chunks[idx_ws + 1]
    rest = chunks[idx_ws + 2:]
    rating_chunk = collapse_ws(rest[0])
    meta_chunks = rest[1:]

    # ── witness tiers ──
    tiers = [collapse_ws(g) for g in split_paras(deblock(witness_block))]
    reader_note = None          # visible decl-readerspace text (or None)
    stack_html = []
    for t in tiers:
        mm = META_RE.match(t)
        label = typography(mm.group(1))      # "Tier 1 · red letter ---" -> "... —"
        rawval = mm.group(2).strip()
        if mm.group(1).strip().startswith('Reader space'):
            if rawval == 'open':
                value_html = 'open'
            else:
                inner = convert(strip_italic(rawval))
                value_html = '<em>%s</em>' % inner
                reader_note = inner
        else:
            value_html = convert(rawval)
        stack_html.append(
            '    <p class="decl-stack"><strong>%s</strong> %s</p>' % (label, value_html))

    # ── rating ──
    rm = RATING_RE.match(rating_chunk)
    verdict = rm.group(2)
    pct = rm.group(3)
    rationale = convert(rm.group(4))
    pill_label, pill_cls = PILL[verdict]
    pct_span = '<span class="decl-pct">~%s</span> ' % pct if pct else ''
    rating_html = ('  <p class="decl-rating"><span class="decl-pill %s">%s</span> '
                   '%s&mdash; %s</p>' % (pill_cls, pill_label, pct_span, rationale))

    # ── meta lines ──
    meta_html = []
    for c in meta_chunks:
        mm = META_RE.match(collapse_ws(c))
        if not mm:
            continue
        label = mm.group(1).strip()
        value = convert(mm.group(2))
        cls = 'decl-meta decl-flag' if label.startswith('Verification flag') else 'decl-meta'
        meta_html.append('    <p class="%s"><strong>%s</strong> %s</p>'
                         % (cls, label, value))

    # ── assemble card ──
    parts = []
    parts.append('<article class="decl-card" id="decl-%s">' % num)
    parts.append('  <h3 class="decl-title"><span class="decl-num">%s</span> %s</h3>'
                 % (num, title))
    parts.append('  <blockquote class="decl-statement">%s</blockquote>' % statement)
    parts.append(rating_html)
    if reader_note is not None:
        parts.append('  <p class="decl-readerspace"><strong>Left open for your '
                     'tradition:</strong> <em>%s</em></p>' % reader_note)
    parts.append('  <details class="decl-witness"><summary>Show the witness</summary>'
                 '<div class="decl-witness-body">')
    parts.extend(stack_html)
    parts.append('    <hr class="decl-meta-rule">')
    parts.extend(meta_html)
    parts.append('  </div></details>')
    parts.append('</article>')
    return '\n'.join(parts)


# ── Boundary items ───────────────────────────────────────────────────────────

def build_boundary(region):
    paras = split_paras(region)
    preamble = None
    bq = None
    for p in paras:
        ps = p.strip()
        if ps.startswith('**What We Could Not'):
            continue
        if ps.startswith('>'):
            bq = (bq + '\n\n' + p) if bq else p
        elif ps.startswith('*') and not ps.startswith('**'):
            preamble = convert(strip_italic(collapse_ws(ps)))

    iparts = [collapse_ws(x) for x in split_paras(deblock(bq))]
    items = []
    i = 0
    while i < len(iparts):
        m = TITLE_RE.match(iparts[i])
        if m:
            num = m.group(1)
            btitle = typography(m.group(2))
            expl = convert(iparts[i + 1])
            refs = convert(iparts[i + 2])
            items.append(
                '  <div class="decl-boundary-item"><h4>%s %s %s</h4><p>%s</p>'
                '<p class="decl-boundary-refs">%s</p></div>'
                % (num, EMDASH, btitle, expl, refs))
            i += 3
        else:
            i += 1
    return preamble, '\n'.join(items)


# ── Intro / method / methodology ─────────────────────────────────────────────

def build_intro(region):
    paras = split_paras(region)
    out = []
    for p in paras:
        ps = collapse_ws(p)
        if ps.startswith('**How to read this**'):
            continue
        out.append('    <p>%s</p>' % convert(ps))
    return '\n'.join(out)


PHASE_RE = re.compile(r'^\d+\.\s*\*\*(.+?)\*\*\s*(.*)$', re.DOTALL)


def build_phases(region):
    out = []
    for p in split_paras(region):
        ps = collapse_ws(p)
        m = PHASE_RE.match(ps)
        if not m:
            continue
        lead = m.group(1).strip()
        rest = convert(m.group(2))
        out.append('      <li><strong>%s</strong> %s</li>' % (lead, rest))
    return '\n'.join(out)


def build_methodology(region):
    out = []
    for p in split_paras(region):
        ps = collapse_ws(p)
        if ps.startswith('**Methodology'):
            continue
        m = META_RE.match(ps)
        if not m:
            continue
        label = m.group(1).strip()
        value = convert(m.group(2))
        out.append('    <p class="decl-meta"><strong>%s</strong> %s</p>'
                   % (label, value))
    return '\n'.join(out)


# ── Page assembly ────────────────────────────────────────────────────────────

def slice_between(text, start_marker, end_marker):
    a = text.index(start_marker)
    b = text.index(end_marker, a + len(start_marker))
    return text[a:b]


def build_page(md, frontmatter):
    md = md.replace('\r\n', '\n')
    md = md.replace('\\~', '~')           # unescape pandoc tilde globally

    intro_region = slice_between(md, '**How to read this**', '**The method, in seven phases**')
    phases_region = slice_between(md, '**The method, in seven phases**', 'THE DECLARATIONS')
    decl_region = slice_between(md, 'THE DECLARATIONS', 'THE BOUNDARY')
    boundary_region = slice_between(md, 'THE BOUNDARY', '**Methodology & limits**')
    methodology_region = md[md.index('**Methodology & limits**'):]

    intro_html = build_intro(intro_region)
    phases_html = build_phases(phases_region)

    # declaration cards
    starts = [m.start() for m in re.finditer(r'^\*\*(\d{2})\s', decl_region, re.MULTILINE)]
    starts.append(len(decl_region))
    cards = []
    for j in range(len(starts) - 1):
        block = decl_region[starts[j]:starts[j + 1]]
        cards.append(build_card(block))
    cards_html = '\n'.join(cards)

    preamble, boundary_items = build_boundary(boundary_region)
    methodology_html = build_methodology(methodology_region)

    body = []
    body.append(frontmatter)
    body.append('')
    body.append(STYLE_BLOCK)
    body.append('')
    body.append('<div data-pagefind-body>')
    body.append('')
    body.append('  <p class="study-intro">A Words of Plainness Companion Study</p>')
    body.append('')
    body.append('  <div class="decl-intro">')
    body.append(intro_html)
    body.append('  </div>')
    body.append('')
    body.append('  <details class="decl-method"><summary>How we built this %s the method in seven phases</summary>' % EMDASH)
    body.append('    <ol>')
    body.append(phases_html)
    body.append('    </ol>')
    body.append('  </details>')
    body.append('')
    body.append('  <div class="study-divider">&#10022;&ensp;&ensp;&#10022;&ensp;&ensp;&#10022;</div>')
    body.append('')
    body.append('  <h2 class="study-section-heading">The Declarations</h2>')
    body.append('')
    body.append(cards_html)
    body.append('')
    body.append('  <div class="study-divider">&#10022;&ensp;&ensp;&#10022;&ensp;&ensp;&#10022;</div>')
    body.append('')
    body.append('  <h2 class="study-section-heading">The Boundary %s What We Could Not Yet Share</h2>' % EMDASH)
    body.append('  <p class="decl-intro"><em>%s</em></p>' % preamble)
    body.append('')
    body.append('  <div class="decl-boundary">')
    body.append(boundary_items)
    body.append('  </div>')
    body.append('')
    body.append('  <details class="decl-methodology"><summary>Methodology &amp; limits</summary>')
    body.append(methodology_html)
    body.append('  </details>')
    body.append('')
    body.append('  <p class="study-footer-note">&ldquo;For my soul delighteth in plainness; '
                'for after this manner doth the Lord God<br>work among the children of men.&rdquo; '
                '&mdash; 2 Nephi 31:3</p>')
    body.append('')
    body.append('</div>')
    body.append('{% include "partials/search-fab.njk" %}')
    body.append('')
    return '\n'.join(body)


CREEDAL_FM = '''---
layout: layouts/study.njk
title: "What We Confess Together"
pageTitle: "What We Confess Together"
pageSubtitle: "Nineteen teachings of Christ, shared across the historic Christian families"
permalink: /studies/declarations/creedal-core/
eleventyExcludeFromCollections: true
---'''

EXPANDED_FM = '''---
layout: layouts/study.njk
title: "What We Hold in Common"
pageTitle: "What We Hold in Common"
pageSubtitle: "Belief declarations from the four gospels, shared across all who confess Christ."
permalink: /studies/declarations/expanded-tent/
eleventyExcludeFromCollections: true
---'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    jobs = [
        ('Declarations_Creedal_Core.md', CREEDAL_FM, 'creedal-core.njk'),
        ('Declarations_Expanded_Tent.md', EXPANDED_FM, 'expanded-tent.njk'),
    ]
    for src, fm, out in jobs:
        with open(os.path.join(SRC_DIR, src), encoding='utf-8') as f:
            md = f.read()
        page = build_page(md, fm)
        outpath = os.path.join(OUT_DIR, out)
        with open(outpath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(page)
        ncards = page.count('class="decl-card"')
        print('wrote %s  (%d cards)' % (outpath, ncards))


if __name__ == '__main__':
    main()
