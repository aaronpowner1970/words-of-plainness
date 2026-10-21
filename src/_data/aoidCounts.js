/* ============================================================
   AOID2 COUNTS ON THE PAGE  (CODE-AOID2-48, pathway step 89; ruling AOID2-COUNT-PLACEMENT option 3)

   Template name:  aoidCounts
   Exists only when the Second Edition switch is ON (src/_data/aoidSecondEdition.js);
   with it OFF this module is { on: false } and nothing here reaches a page.

   The ONE source of every count shown is data-sources/aoid/floor_counts.json, written by
   scripts/aoid-build-floor-counts.js from the floor ledger and cross-checked against a second
   record (see that script). Nothing here retypes a number. Two things read it:
     - spans    {A04: {s1: [{id, title, t, c, n}]}}: embedded in the page; src/aoid-second-edition/articles-tabs.js
                shows, in a span's panel, "Taught in X, contradicted in Y, no position in Z, of sixteen."
                with the links "See the record" and "How this was measured"
     - tables   {A04: html}: the summary table that opens each Article's Record tab

   Only floors whose status is MATCH carry a count. A floor that is UNSCORED (waiting for Stage 2),
   MISMATCH (the records disagree) or NO_SECOND_RECORD gets no sentence and no links; in a summary table a
   MISMATCH floor keeps its row, with dashes where the numbers would be. Absence is never shown as zero.

   Safety net: at build time every MATCH floor is re-read against the ledger in the repository and, where a
   disclosure holds a sixteen-family table for it, against that table. A disagreement stops the build.
   ============================================================ */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { on } = require('./aoidSecondEdition.js');

const COUNTS = 'data-sources/aoid/floor_counts.json';
const LEDGER = 'data-sources/aoid/floor_ledger.yaml';

if (!on) module.exports = { on: false };
else {
  const fail = (m) => { throw new Error('floor counts: ' + m); };
  const data = JSON.parse(fs.readFileSync(path.join(process.cwd(), COUNTS), 'utf8'));
  const ledger = yaml.load(fs.readFileSync(path.join(process.cwd(), LEDGER), 'utf8')).scored;
  const disclosures = require('./aoidDisclosures.js');
  const disclosed = {};
  [disclosures.fatherOfSpirits, disclosures.sexualHoliness].forEach((d) => d.teachings.forEach((t) => { disclosed[t.id] = t.counts; }));

  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const spanNo = (s) => Number(s.split('.s')[1]);
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const dateText = (iso) => { const [y, m, d] = iso.split('-').map(Number); return d + ' ' + MONTHS[m - 1] + ' ' + y; };

  // Re-read each shown count against the ledger (and the disclosure table, where one exists).
  data.floors.filter((f) => f.status === 'MATCH').forEach((f) => {
    const e = ledger.find((x) => String(x.item) === f.id);
    const m = e && /taught (\d+), (?:contradicted|divided) (\d+), no position (\d+)/.exec(e.result || '');
    if (!m) fail(f.id + ': no scored ledger entry');
    if (Number(m[1]) !== f.counts.taught || Number(m[2]) !== f.counts.contradicted || Number(m[3]) !== f.counts.noPosition) {
      fail(f.id + ': floor_counts.json disagrees with the ledger; rerun scripts/aoid-build-floor-counts.js');
    }
    const d = disclosed[f.id];
    if (d && (d.teach !== f.counts.taught || d.divided !== f.counts.contradicted || d.none !== f.counts.noPosition)) {
      fail(f.id + ': floor_counts.json disagrees with its disclosure table');
    }
  });

  const code = (span) => span.split('.')[0];
  const spans = {};
  const rowsBy = {};
  data.floors.forEach((f) => {
    if (f.status === 'UNSCORED') return;
    const art = code(f.spans[0]);
    const first = Math.min(...f.spans.filter((s) => code(s) === art).map(spanNo));
    (rowsBy[art] = rowsBy[art] || []).push({ f, first });
    if (f.status !== 'MATCH') return;
    f.spans.forEach((s) => {
      const [a, sp] = s.split('.');
      ((spans[a] = spans[a] || {})[sp] = spans[a][sp] || []).push({ id: f.id, t: f.counts.taught, c: f.counts.contradicted, n: f.counts.noPosition });
    });
  });

  const DASH = '—';
  const tables = {};
  Object.keys(rowsBy).forEach((art) => {
    const id = art.toLowerCase();
    const rows = rowsBy[art].sort((a, b) => a.first - b.first).map(({ f }) => {
      const ok = f.status === 'MATCH';
      const q = !ok || f.queue === null ? DASH : (f.queue + (f.queuedFamilies && f.queuedFamilies.length ? ' (' + f.queuedFamilies.map(esc).join(', ') + ')' : ''));
      return '<tr id="' + id + '-record-' + esc(f.id) + '"><th scope="row">' + esc(f.title) + '</th>'
        + '<td>' + (ok ? f.counts.taught : DASH) + '</td><td>' + (ok ? f.counts.contradicted : DASH) + '</td><td>' + (ok ? f.counts.noPosition : DASH) + '</td>'
        + '<td>' + (ok && f.measured ? esc(dateText(f.measured) + (f.revised ? ', revised ' + dateText(f.revised) : '')) : DASH) + '</td>'
        + '<td>' + (ok && f.borderline !== null ? f.borderline : DASH) + '</td>'
        + '<td>' + q + '</td></tr>';
    }).join('');
    tables[art] = '<div class="disc-table-wrap an-summary"><table><caption>Taught, contradicted and no position are each counted of sixteen.</caption><thead><tr><th scope="col">Teaching</th><th scope="col">Taught</th><th scope="col">Contradicted</th><th scope="col">No position</th>'
      + '<th scope="col">Date measured</th><th scope="col">Borderline readings</th><th scope="col">Families still being confirmed</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
  });

  module.exports = { on: true, source: COUNTS, spans, tables, status: data.floors.map((f) => ({ id: f.id, status: f.status })) };
}
