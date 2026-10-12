/* ============================================================
   AOID2 DISCLOSURE RENDERER  (CODE-AOID2-26)

   Template name:  aoidDisclosures
   One reader, one rendering, for both places a disclosure appears:
     - the standalone pages  /aoid/disclosures/father-of-spirits/ and
       /aoid/disclosures/sexual-holiness/   (src/pages/aoid/disclosures/)
     - the Disclosure and Record tabs on Article 2 and Article 11
       (src/_includes/components/article-tabs.njk, via aoidArticleTabs.js)
   Both read the same two source files in data-sources/aoid/disclosures/.
   No disclosure text is copied anywhere; it is read and rendered at build time.

   Source layout this file relies on (it throws if any of it is missing):
     "## Part 2. The companion study"      -> "### <Title>: <Subtitle>", an
                                              "*Address: /path*" line, then the body
     "## Part 3. The record behind the counts" -> the record, opening with the
                                              builder's instruction paragraph
                                              ("Families are named here, ...") which is dropped,
                                              then the sixteen-family table
     "## Gaps to fill ..."                 -> never rendered
   Part 1 (the footnote) is not rendered here; the footnote lives in the Article.

   Fragment links. Part 2 links to a section of Part 3 with a plain fragment
   ("#what-the-sixteen-cover"). The renderer gives the target its id, and
   `prefix` keeps that id unique where several records share one page:
     standalone page:  prefix ''             -> #what-the-sixteen-cover
     Article 2 tab:    prefix 'a02-record-'  -> #a02-record-what-the-sixteen-cover
   (the tab script opens the Record tab when a link points into it).

   Count strips. The strip at the head of each Record is built by reading the
   sixteen-family table in Part 3 and counting its cells, then checking the
   counts against the table's own "Total teaching it" row and its
   "C4 requires N of 16" cell. If the table is not in the expected form, or the
   counts disagree with the total row, the build stops rather than guess.
   ============================================================ */

const fs = require('fs');
const path = require('path');
const MarkdownIt = require('markdown-it');

const DIR = 'data-sources/aoid/disclosures';
const SOURCES = {
  fatherOfSpirits: { code: 'A02', file: 'WoP_AOID2_FatherOfSpirits_Disclosure_Final_20261004.md' },
  sexualHoliness: { code: 'A11', file: 'WoP_AOID2_SexualHoliness_Disclosure_Final_20261002.md' },
};

// The one copy of the correction line (was typed in each standalone page).
const CORRECTION_HTML = 'If you belong to one of these traditions and believe we have misread its teaching, please <a href="/connect/#contact">tell us</a>, and name the adopted text we should read.';

const COVER_ID = 'what-the-sixteen-cover';
const COVER_RE = /<(p|li)><strong>What the sixteen cover\.<\/strong>/g;

function renderer(prefix) {
  const md = MarkdownIt({ html: false, linkify: false, typographer: false });
  const defaultTable = md.renderer.rules.table_open || ((t, i, o, e, s) => s.renderToken(t, i, o));
  md.renderer.rules.table_open = (t, i, o, e, s) => '<div class="disc-table-wrap">' + defaultTable(t, i, o, e, s);
  md.renderer.rules.table_close = (t, i, o, e, s) => s.renderToken(t, i, o) + '</div>';
  const defaultLink = md.renderer.rules.link_open || ((t, i, o, e, s) => s.renderToken(t, i, o));
  md.renderer.rules.link_open = (tokens, idx, opts, env, self) => {
    const href = tokens[idx].attrGet('href');
    if (prefix && href && href.charAt(0) === '#') tokens[idx].attrSet('href', '#' + prefix + href.slice(1));
    return defaultLink(tokens, idx, opts, env, self);
  };
  return md;
}

const CATEGORY = [
  [/^Teaches it/, 'teach'],
  [/^Divided/, 'divided'],
  [/^Being confirmed/, 'confirm'],
  [/^No common position/, 'none'],
];
const TOTAL_WORDS = { divided: 'divided', 'no common position': 'none', 'being confirmed': 'confirm' };

function cells(line) {
  return line.split('|').slice(1, -1).map((c) => c.trim());
}

// Read the sixteen-family table from Part 3 and return one tally per measured teaching.
function readTeachings(rec, who) {
  const fail = (m) => { throw new Error('disclosure ' + who + ': count strip: ' + m); };
  const head = rec.findIndex((l) => /^\| # \| Family \|/.test(l));
  if (head < 0) fail('sixteen-family table header not found');
  const cols = cells(rec[head]);
  const decide = cols.findIndex((c) => /^Deciding adopted texts/.test(c));
  if (decide < 3) fail('no teaching columns before "Deciding adopted texts"');
  const floors = cols.slice(2, decide); // e.g. "A2-F1: Father of our spirits", "29a: within marriage"
  const rows = [];
  let total = null;
  for (let i = head + 2; i < rec.length && /^\|/.test(rec[i]); i++) {
    const c = cells(rec[i]);
    if (c.length !== cols.length) fail('row ' + (i - head - 1) + ' has ' + c.length + ' cells, expected ' + cols.length);
    if (/^\d+$/.test(c[0])) rows.push(c);
    else if (/Total teaching it/.test(c[1])) total = c;
    else fail('unrecognised table row: ' + rec[i].slice(0, 60));
  }
  if (rows.length !== 16) fail('expected 16 family rows, found ' + rows.length);
  if (!total) fail('"Total teaching it" row not found');
  const need = (total[decide].match(/requires (\d+) of 16/) || [])[1];
  if (!need) fail('"C4 requires N of 16" not found in the total row');

  return floors.map((f, k) => {
    const n = { teach: 0, divided: 0, confirm: 0, none: 0 };
    rows.forEach((r) => {
      const hit = CATEGORY.find(([re]) => re.test(r[2 + k]));
      if (!hit) fail('unrecognised cell "' + r[2 + k] + '" in row ' + r[0]);
      n[hit[1]]++;
    });
    const t = total[2 + k];
    const teach = (t.match(/(\d+) of 16/) || [])[1];
    if (Number(teach) !== n.teach) fail(floors[k] + ': total row says ' + teach + ' teach it, the cells count ' + n.teach);
    const said = { divided: 0, confirm: 0, none: 0 };
    let m;
    const re = /(\d+) (divided|no common position|being confirmed)/g;
    while ((m = re.exec(t))) said[TOTAL_WORDS[m[2]]] = Number(m[1]);
    ['divided', 'confirm', 'none'].forEach((key) => {
      if (said[key] !== n[key]) fail(floors[k] + ': total row says ' + said[key] + ' ' + key + ', the cells count ' + n[key]);
    });
    const [id, ...rest] = f.split(': ');
    return { id: id.trim(), label: rest.join(': ').trim(), counts: n, need: Number(need) };
  });
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function stripHtml(t) {
  const n = t.counts;
  const parts = [];
  if (n.divided) parts.push(n.divided + ' divided');
  else parts.push('0 divided');
  parts.push(n.none + ' no common position');
  if (n.confirm) parts.push(n.confirm + ' being confirmed');
  parts.push(t.need + ' needed');
  const said = n.teach + ' of 16 teach it; ' + parts.join('; ');
  const cell = (cls, k) => Array(k).fill('<i class="an-cell an-cell-' + cls + '"></i>').join('');
  const key = [
    ['teach', 'Teaches it'], ['divided', 'Divided'], ['confirm', 'Being confirmed'], ['none', 'No common position'],
  ].filter(([k]) => n[k] > 0).map(([k, w]) => '<span><i class="an-key-' + k + '"></i>' + w + '</span>').join('')
    + '<span><i class="an-key-th"></i>' + t.need + ' needed</span>';
  return '<div class="an-tally" role="group" aria-label="' + esc(t.label + ': ' + said) + '">'
    + '<p class="an-tally-label">' + esc(t.id + ' · ' + t.label) + '</p>'
    + '<div class="an-tally-head"><span class="an-tally-big">' + n.teach + ' <small>of 16 teach it</small></span>'
    + '<span class="an-tally-need">' + esc(parts.join(' · ')) + '</span></div>'
    + '<div class="an-strip" aria-hidden="true">'
    + cell('teach', n.teach) + cell('divided', n.divided) + cell('confirm', n.confirm) + cell('none', n.none)
    + '<span class="an-thresh" style="--need:' + t.need + '"></span></div>'
    + '<div class="an-key">' + key + '</div></div>';
}

function build(name, spec) {
  const src = fs.readFileSync(path.join(process.cwd(), DIR, spec.file), 'utf8').replace(/\r\n/g, '\n');
  const lines = src.split('\n');
  const at = (re, from) => {
    for (let i = from || 0; i < lines.length; i++) if (re.test(lines[i])) return i;
    throw new Error('disclosure ' + name + ': anchor not found: ' + re);
  };
  const p2 = at(/^## Part 2\. /);
  const h = at(/^### /, p2);
  const p3 = at(/^## Part 3\. /, h);
  const gaps = at(/^## Gaps to fill/, p3);
  const heading = lines[h].slice(4);
  const cut = heading.indexOf(': ');
  if (cut < 0) throw new Error('disclosure ' + name + ': heading is not "Title: Subtitle"');
  const addrLine = lines.slice(h + 1, p3).find((l) => /^\*Address: /.test(l));
  if (!addrLine) throw new Error('disclosure ' + name + ': Address line not found');
  const address = addrLine.replace(/^\*Address: (.+)\*$/, '$1').replace(/\/?$/, '/');

  // Part 2 body: after the heading (carried by the page title) and the Address line, up to the rule before Part 3.
  let body = lines.slice(h + 1, p3).filter((l) => !/^\*Address: /.test(l));
  while (body.length && /^(---)?\s*$/.test(body[body.length - 1])) body.pop();
  // Part 3 record: drop the builder's instruction paragraph, stop before the rule preceding "Gaps to fill".
  const rec = lines.slice(p3 + 1, gaps);
  const instr = rec.findIndex((l) => /^Families are named here, in the apparatus/.test(l));
  if (instr < 0) throw new Error('disclosure ' + name + ': Part 3 instruction paragraph not found');
  rec.splice(instr, 1);
  while (rec.length && /^(---)?\s*$/.test(rec[rec.length - 1])) rec.pop();

  const teachings = readTeachings(rec, name);

  const view = (prefix) => {
    const md = renderer(prefix);
    const bodyHtml = md.render(body.join('\n'));
    let recHtml = md.render(rec.join('\n'));
    if ((recHtml.match(COVER_RE) || []).length !== 1) throw new Error('disclosure ' + name + ': "What the sixteen cover." paragraph not found exactly once');
    recHtml = recHtml.replace(COVER_RE, '<$1 id="' + prefix + COVER_ID + '"><strong>What the sixteen cover.</strong>');
    // every fragment link in Part 2 must land on an id in Part 3
    const links = bodyHtml.match(/href="#[^"]+"/g) || [];
    if (!links.length) throw new Error('disclosure ' + name + ': the "What the sixteen cover" link is missing from Part 2');
    links.forEach((l) => {
      const id = l.slice(7, -1);
      if (recHtml.indexOf('id="' + id + '"') < 0) throw new Error('disclosure ' + name + ': link target #' + id + ' not found in Part 3');
    });
    return { body: bodyHtml, record: recHtml };
  };

  const prefix = spec.code.toLowerCase() + '-record-';
  return {
    code: spec.code,
    address,
    title: heading.slice(0, cut),
    subtitle: heading.slice(cut + 2),
    teachings,
    standalone: view(''),
    tab: Object.assign(view(prefix), { strips: teachings.map(stripHtml).join('') }),
  };
}

const out = { correctionHtml: CORRECTION_HTML };
Object.keys(SOURCES).forEach((k) => { out[k] = build(k, SOURCES[k]); });
module.exports = out;
