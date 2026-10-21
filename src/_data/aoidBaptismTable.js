/* ============================================================
   AOID2 ARTICLE 11 BAPTISM TABLE  (CODE-AOID2-51)

   Template name:  aoidBaptismTable
   Exists only when the Second Edition switch is ON (src/_data/aoidSecondEdition.js);
   with it OFF this module is { on: false } and nothing here reaches a page.

   Builds the sixteen-family table on Article 11's Record tab, after the summary table and before the
   per-family floor tables. Every cell comes from one data file, never retyped:
     data-sources/aoid/second-edition/a11_baptism_families.json
   (generated from the CODE-AOID2-50 task 2 table). Before the table is built it is checked against the
   approved "Born of water and of the Spirit." paragraph (section 7 of the approved Article 11 file): the
   rows marked Yes, Joined and Sign must name exactly the families that paragraph names. A disagreement
   stops the build.
   ============================================================ */

const fs = require('fs');
const path = require('path');
const { on } = require('./aoidSecondEdition.js');

const DATA = 'data-sources/aoid/second-edition/a11_baptism_families.json';
const APPROVED = 'data-sources/aoid/second-edition/WoP_AOID2_Step89_Article11_Baptism_Approved_20261020.md';

if (!on) module.exports = { on: false };
else {
  const fail = (m) => { throw new Error('baptism table: ' + m); };
  const read = (f) => fs.readFileSync(path.join(process.cwd(), f), 'utf8').replace(/\r\n/g, '\n');
  const data = JSON.parse(read(DATA));
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const base = (v) => v.replace(' (borderline)', '');

  // The paragraph says "Pentecostal", "Latter-day Saint", "Jehovah's Witness"; the table uses the Articles' list names.
  const short = (f) => (/^Pentecostal/.test(f) ? 'Pentecostal' : /Latter-day Saints$/.test(f) ? 'Latter-day Saint' : f === "Jehovah's Witnesses" ? "Jehovah's Witness" : f);
  const names = (s) => s.split(/, | and /).map((x) => x.trim().replace(/^the /, '')).filter(Boolean);

  const para = read(APPROVED).split('\n').filter((l) => l.startsWith('**Born of water and of the Spirit.** Christ was baptized') && l.includes('Every tradition but three'));
  if (para.length !== 1) fail('the approved "Born of water and of the Spirit." paragraph (section 7) was not found exactly once');
  const p = para[0];
  const grab = (re, what) => { const m = re.exec(p); if (!m) fail('approved paragraph: ' + what + ' not found'); return names(m[1]); };
  const notFoundA = grab(/it was not found in the (.+?) texts read\./, 'the families without the water-baptism claim');
  const listB = grab(/Of them, the (.+?) join it to the new birth/, 'list (b)');
  const others = grab(/Others, the (.+?), confess the new birth as the Spirit's work and baptism as its sign/, 'the sign families');

  const rows = data.rows;
  if (rows.length !== 16) fail('expected sixteen rows, found ' + rows.length);
  const sorted = (a) => a.slice().sort().join('|');
  const set = (f) => sorted(rows.filter(f).map((r) => short(r.family)));
  rows.forEach((r) => {
    if (!['Yes', 'Not found'].includes(base(r.ordained))) fail(r.family + ': column 3 must be Yes or Not found');
    if (!['Joined', 'Sign', 'Not found'].includes(base(r.joined))) fail(r.family + ': column 4 must be Joined, Sign or Not found');
  });
  if (rows.filter((r) => r.ordained === 'Yes').length !== 13) fail('column 3 must have thirteen Yes');
  if (set((r) => r.ordained === 'Not found') !== sorted(notFoundA)) fail('the families without the water-baptism claim disagree with the approved paragraph');
  if (set((r) => base(r.joined) === 'Joined') !== sorted(listB)) fail('the Joined rows disagree with list (b) of the approved paragraph');
  if (set((r) => base(r.joined) === 'Sign') !== sorted(others)) fail('the Sign rows disagree with the "Others" of the approved paragraph');

  const html = '<section class="an-baptism-table" id="a11-baptism-families"><h4>' + esc(data.heading) + '</h4><p>' + esc(data.line) + '</p>'
    + '<div class="disc-table-wrap an-summary"><table><thead><tr>' + data.columns.map((c) => '<th scope="col">' + esc(c) + '</th>').join('') + '</tr></thead><tbody>'
    + rows.map((r) => '<tr><th scope="row">' + esc(r.family) + '</th><td>' + esc(r.document) + '</td><td>' + esc(r.ordained) + '</td><td>' + esc(r.joined) + '</td></tr>').join('')
    + '</tbody></table></div></section>';

  module.exports = { on: true, source: DATA, rows, html, byArticle: { A11: html } };
}
