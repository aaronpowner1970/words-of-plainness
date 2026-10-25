/* ============================================================
   AOID2 TEACHING ADDITIONS T1-T6  (CODE-AOID2-52)

   Template name:  aoidTeaching
   Exists only when the Second Edition switch is ON (src/_data/aoidSecondEdition.js);
   with it OFF this module is { on: false } and nothing here reaches a page.

   Every sentence comes from the approved file, read at build time and never retyped:
   data-sources/aoid/second-edition/ holds a byte-identical copy of
     wop-scratch/WoP_AOID2_TeachingPractices_Scores.md
   section "Teaching additions T1-T6" (approved by Aaron, 21 Oct 2026, 12:59 ET).
   One entry serves all thirteen Articles; src/_includes/components/article-tabs.njk places it.

     practice   T1  one small-type line under each tab heading (declaration, disclosure, record)
     before     T2  the boxed prompt at the top of the Disclosure tab ("Before you read on:" in bold)
     correction T3  the line at the foot of the Declaration tab, linked to /aoid/corrections/
     question   T4  label and note for the learner's own question (the box is built in aoidArticleTabs.js)
     asRead     T5  the line above each Article's text

   T6 (the summary table's "Borderline readings" and "Families still being confirmed" cells) is in
   aoidCounts.js and scripts/aoid-build-floor-counts.js.
   ============================================================ */

const fs = require('fs');
const path = require('path');
const { on } = require('./aoidSecondEdition.js');

const FILE = 'data-sources/aoid/second-edition/WoP_AOID2_TeachingPractices_Scores.md';
const CORRECTIONS_URL = '/aoid/corrections/';

if (!on) module.exports = { on: false };
else {
  const fail = (m) => { throw new Error('teaching additions: ' + m); };
  const lines = fs.readFileSync(path.join(process.cwd(), FILE), 'utf8').replace(/\r\n/g, '\n').split('\n');
  const start = lines.findIndex((l) => /^## Teaching additions T1-T6/.test(l));
  if (start < 0) fail('section "Teaching additions T1-T6" not found');
  const sect = lines.slice(start + 1);

  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  // The one line matching `re` (with one capture group), exactly once.
  const one = (re, what) => {
    const hits = sect.map((l) => re.exec(l)).filter(Boolean);
    if (hits.length !== 1) fail(what + ': expected exactly one line, found ' + hits.length);
    return hits[0][1];
  };

  const practice = {
    declaration: one(/^- Declaration: "(.+)"$/, 'T1 Declaration line'),
    disclosure: one(/^- Disclosure: "(.+)"$/, 'T1 Disclosure line'),
    record: one(/^- Record: "(.+)"$/, 'T1 Record line'),
  };
  const beforeLead = 'Before you read on:';
  const beforeFull = one(/^"(Before you read on: .+?)" \("Before you read on:" in bold\.\)$/, 'T2 prompt');
  const correction = one(/^"(If you believe we have misstated .+)"$/, 'T3 line');
  const asRead = one(/^"(As you read, .+)"$/, 'T5 line');
  const label = one(/^Label \(bold\): "(.+)"$/, 'T4 label');
  const note = one(/^Note \(italic, under the box\): "(.+)"$/, 'T4 note');
  if (!beforeFull.startsWith(beforeLead + ' ')) fail('T2 prompt does not open with "' + beforeLead + '"');

  const practiceLine = (t) => '<p class="an-practice">' + esc(t) + '</p>';
  const beforeBox = (full) => {
    if (!full.startsWith(beforeLead + ' ')) fail('a "Before you read on:" prompt must open with "' + beforeLead + '"');
    return '<div class="an-before" role="note"><p><strong>' + esc(beforeLead) + '</strong>' + esc(full.slice(beforeLead.length)) + '</p></div>';
  };
  const correctionLine = (t) => '<p class="an-correction-line"><a href="' + CORRECTIONS_URL + '">' + esc(t) + '</a></p>';

  module.exports = {
    on: true,
    source: FILE,
    correctionsUrl: CORRECTIONS_URL,
    text: { practice, before: beforeFull, correction, asRead, label, note },
    practiceHtml: Object.fromEntries(Object.keys(practice).map((k) => [k, practiceLine(practice[k])])),
    beforeHtml: beforeBox(beforeFull),
    correctionHtml: correctionLine(correction),
    // The same three components for other pages (CODE-AOID2-56: /living-tree/ L1, L2, L3), so they cannot drift from T1-T3.
    practiceLine, beforeBox, correctionLine,
    asReadHtml: '<p class="an-as-read">' + esc(asRead) + '</p>',
    // T4: the box for one Article. `id` is the Article's tab id ("a11"). Stored by the tabs script, in this browser only.
    questionHtml: (id) => '<div class="an-learner" data-an-learner="' + id + '">'
      + '<label class="an-learner-label" for="' + id + '-learner-question"><strong>' + esc(label) + '</strong></label>'
      + '<textarea class="an-learner-box" id="' + id + '-learner-question" rows="3" autocomplete="off"></textarea>'
      + '<p class="an-learner-note"><em>' + esc(note) + '</em></p></div>',
  };
}
