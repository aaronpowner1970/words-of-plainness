/* ============================================================
   AOID2 READER CORRECTIONS FORM  (CODE-AOID2-47, pathway step 88)

   Template name:  aoidCorrections
   Feeds src/pages/aoid-corrections.njk (the form at /aoid/corrections/) and the
   "Has your church's text been misread or missed? Tell us." links on the Article
   Disclosure and Record tabs and on both disclosure pages.
   Exists only when the Second Edition switch is ON (src/_data/aoidSecondEdition.js);
   with it OFF this module is { on: false } and nothing here reaches a page.

   Every reader-facing word comes from the approved wording, read at build time and
   never retyped: data-sources/aoid/second-edition/ holds a byte-identical copy of
   wop-scratch/WoP_AOID2_Step88_CorrectionsForm_Spec_Draft_v1_20261019.md (Part 1).
   The sixteen family names are read from the disclosure source (the list "named as
   they appear on The Living Tree of Christ-Believing Traditions", codex C4(d)), so
   they are the names the site already shows.

   Pre-fill query parameters (field 3):
     article  the displayed Article number, 1 to 13
     floor    one or more floor-item ids of that Article, comma-separated
              (for example A2-F1 or 29a,29b); an id the Article does not hold is ignored
   ============================================================ */

const fs = require('fs');
const path = require('path');
const { on } = require('./aoidSecondEdition.js');

const WORDING = 'data-sources/aoid/second-edition/WoP_AOID2_Step88_CorrectionsForm_Spec_Draft_v1_20261019.md';
const TRADITIONS_SOURCE = 'data-sources/aoid/disclosures/WoP_AOID2_FatherOfSpirits_Disclosure_Final_20261004.md';
const PAGE = '/aoid/corrections/';

if (!on) module.exports = { on: false };
else {
  const fail = (m) => { throw new Error('corrections form: ' + m); };
  const read = (f) => fs.readFileSync(path.join(process.cwd(), f), 'utf8').replace(/\r\n/g, '\n').split('\n');

  // ---- Part 1 of the approved wording -------------------------------------------------
  const all = read(WORDING);
  const p1 = all.findIndex((l) => /^## Part 1/.test(l));
  const p2 = all.findIndex((l) => /^## Part 2/.test(l));
  if (p1 < 0 || p2 < p1) fail('Part 1 not found in the approved wording');
  const part = all.slice(p1 + 1, p2);

  // The text after "<label>:" on the same line.
  const inline = (re, what) => {
    const m = part.map((l) => l.match(re)).filter(Boolean);
    if (m.length !== 1) fail('expected exactly one ' + what + ', found ' + m.length);
    return m[0][1];
  };
  // The paragraph under a line that is exactly "<label>:".
  const under = (label) => {
    const i = part.findIndex((l) => l === label + ':');
    if (i < 0) fail('"' + label + ':" not found');
    const out = [];
    for (let j = i + 1; j < part.length && part[j].trim() !== ''; j++) out.push(part[j]);
    if (out.length !== 1) fail('"' + label + ':" should be followed by exactly one paragraph');
    return out[0];
  };

  const title = inline(/^Page title: (.+)$/, 'page title');
  const intro = under('Intro');
  const next = { heading: 'What happens next', text: under('What happens next') };
  const weigh = { heading: 'What we can weigh', text: under('What we can weigh') };
  const privacy = inline(/^Privacy line \(above the button\): (.+)$/, 'privacy line');
  const button = inline(/^Button: (.+)$/, 'button');
  const success = inline(/^Success message: (.+)$/, 'success message');
  const failure = inline(/^Failure message: (.+)$/, 'failure message');
  const linkText = inline(/^Link text used on [^:]+: "(.+)"$/, 'link text');

  // Fields: "N. Label (required|optional ...) / Helper text"
  const fi = part.findIndex((l) => /^Fields /.test(l));
  if (fi < 0) fail('Fields block not found');
  const fields = [];
  for (let j = fi + 1; j < part.length && part[j].trim() !== ''; j++) {
    const m = part[j].match(/^(\d)\. (.+)$/);
    if (!m) fail('unrecognised field line: ' + part[j].slice(0, 60));
    const cut = m[2].indexOf(' / ');
    const left = cut < 0 ? m[2] : m[2].slice(0, cut);
    const helper = cut < 0 ? '' : m[2].slice(cut + 3);
    const lm = left.match(/^(.*?) \((required|optional)\b.*\)$/);
    if (!lm) fail('field ' + m[1] + ': no (required) or (optional) mark');
    fields.push({ n: Number(m[1]), label: lm[1], required: lm[2] === 'required', helper });
  }
  if (fields.length !== 8 || fields.some((f, k) => f.n !== k + 1)) fail('expected the eight fields in order, found ' + fields.length);

  // ---- The sixteen families, as the site already names them ----------------------------
  const src = read(TRADITIONS_SOURCE);
  const at = src.findIndex((l) => /^Each tradition measured is counted as a family/.test(l));
  if (at < 0) fail('family list not found in the disclosure source');
  const traditions = [];
  for (let j = at + 1; j < src.length; j++) {
    const m = src[j].match(/^(\d+)\. (.+)$/);
    if (m) traditions.push(m[2]);
    else if (traditions.length) break;
  }
  if (traditions.length !== 16) fail('expected the sixteen families, found ' + traditions.length);
  const OTHER = 'Another tradition';
  const reOther = inline(/^1\. .*plus "([^"]+)"/, 'the "plus" option in field 1');
  if (reOther !== OTHER) fail('field 1 option differs from "' + OTHER + '"');

  // ---- Links ----------------------------------------------------------------------------
  const tabs = require('./aoidArticleTabs.js');
  const floorsByArticle = {};
  Object.values(tabs.articles).forEach((a) => {
    floorsByArticle[a.n] = {};
    if (a.source) a.source.teachings.forEach((t) => { floorsByArticle[a.n][t.id] = t.label; });
  });

  /** The floor-item ids shown on Article n's Record tab, in table order. */
  const floorIds = (n) => Object.keys(floorsByArticle[n] || {});

  /** Link to the form for Article n, carrying the floor items in view (ids) where there are any. */
  const href = (n, ids) => PAGE + '?article=' + n + (ids && ids.length ? '&floor=' + ids.map(encodeURIComponent).join(',') : '');
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const linkHtml = (n, ids) => '<a href="' + esc(href(n, ids)) + '">' + esc(linkText) + '</a>';

  module.exports = {
    on: true,
    page: PAGE,
    title,
    intro,
    sections: [next, weigh],
    fields,
    traditions,
    otherTradition: OTHER,
    privacy,
    button,
    success,
    failure,
    linkText,
    floorsByArticle,
    floorIds,
    href,
    linkHtml,
  };
}
