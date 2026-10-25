/* ============================================================
   AOID2 ARTICLE TABS  (CODE-AOID2-26)

   Template name:  aoidArticleTabs
   Feeds src/_includes/components/article-tabs.njk, which builds the
   Declaration / Disclosure / Record tabs on each counted Article.
   Used ONLY when the Second Edition switch is ON
   (src/_data/aoidSecondEdition.js); with it OFF nothing here reaches a page.
   The Prologue (A01) never gets tabs.

   ADDING AN ARTICLE (the new Article 1, "A14", is the next one):
     1. add its code to TABBED below;
     2. add its <section> in src/pages/articles.njk with the one-line
        tabs include used by the other Articles (copy A13's);
     3. nothing else. It gets three tabs, and the two generated lines,
        until it has a disclosure or a record of its own.

   WHAT EACH TAB HOLDS
     Declaration  the Article exactly as the include renders it, plus the
                  Listen / Slides / Video buttons (moved in by the tabs script).
     Disclosure   - an Article with a disclosure source (registered in
                    aoidDisclosures.js by its code): Part 2 of that source.
                  - an Article with a "How we hold this" note
                    (src/_data/howWeHold.js, matched on targetArticle): the note,
                    moved into the tab by the tabs script.
                  - otherwise a generated line (GENERATED.noDisclosure).
                  Every Disclosure tab ends with the shared method account, when it exists.
     Record       - an Article with a disclosure source: Part 3 of it, opening with
                    the count strip read from its table.
                  - otherwise one generated line (GENERATED.noRecord).
                  The Record line disappears by itself the moment an Article has a
                  record source: the test is "does aoidDisclosures hold a source for
                  this code". No counts are shown from any other place.

   THE METHOD ACCOUNT (Phase C6; does not exist yet)
     Read from:   data-sources/aoid/method-account/method-account.md
     Format:      Markdown (the same renderer as the disclosures). The whole file is
                  shown, so it carries its own heading.
     Switching on: while that file is missing or empty, no method section is shown and
                  the generated Disclosure line is its first sentence only. As soon as
                  the file has text, every Disclosure tab ends with it and the generated
                  line gains its second sentence (GENERATED.method). No other change is
                  needed: add the file and rebuild.
   ============================================================ */

const fs = require('fs');
const path = require('path');
const MarkdownIt = require('markdown-it');
const disclosures = require('./aoidDisclosures.js');
const howWeHold = require('./howWeHold.js');
const step89 = require('./aoidStep89.js');   // { on: false } with the switch OFF
const counts = require('./aoidCounts.js');   // { on: false } with the switch OFF
const baptism = require('./aoidBaptismTable.js');   // { on: false } with the switch OFF
const teaching = require('./aoidTeaching.js');   // T1-T6 teaching additions; { on: false } with the switch OFF

const TABBED = ['A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10', 'A11', 'A12', 'A13', 'A14'];

// Displayed Article number where it differs from the key: the new Article 1 is keyed A14.
const DISPLAYED_N = { A14: 1 };

const METHOD_FILE = 'data-sources/aoid/method-account/method-account.md';

// Approved wording (AOID2-TABS-MIDDLE-TAB, AOID2-TABS-RECORD-EMPTY). Do not reword.
const GENERATED = {
  noDisclosure: 'This Article has no disclosure of its own.',
  method: 'What follows is the method by which every teaching in these Articles was measured.',
  noRecord: 'The measured record for this Article will appear here once its teachings have been scored against the sixteen traditions.',
};

function readMethod() {
  const file = path.join(process.cwd(), METHOD_FILE);
  if (!fs.existsSync(file)) return '';
  const src = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  if (!src.trim()) return '';
  return MarkdownIt({ html: false, linkify: false, typographer: false }).render(src);
}
// Phase C6 (CODE-AOID2-48): the method account is built from the approved wording (aoidStep89.js); the file above
// stays the fallback so that, with the switch OFF, this module still reads exactly what it read before.
const methodHtml = step89.on ? step89.methodHtml : readMethod();

// Disclosure sources by Article code.
const sources = {};
Object.keys(disclosures).forEach((k) => {
  if (disclosures[k] && disclosures[k].code) sources[disclosures[k].code] = disclosures[k];
});

// "How we hold this" notes by Article code.
const notes = {};
Object.keys(howWeHold).forEach((key) => { notes[howWeHold[key].targetArticle] = key; });

const articles = {};
// A6a (approved 25 Oct 2026): in Article 11's record note "What the sixteen cover." the Tree's name links to its page.
// Done on a copy, so the disclosure source and the standalone pages are untouched.
const TREE_NAME = '<strong>What the sixteen cover.</strong> <em>The Living Tree of Christ-Believing Traditions</em>';
function withTreeLink(source) {
  const url = step89.on && step89.methodLinks.livingTree;
  if (!url || !source || source.code !== 'A11') return source;
  const rec = source.tab.record;
  if (rec.split(TREE_NAME).length !== 2) throw new Error('article tabs: the Article 11 "What the sixteen cover." note, with the Tree name, expected exactly once');
  const linked = TREE_NAME.replace('<em>The Living Tree of Christ-Believing Traditions</em>', '<em><a href="' + url + '">The Living Tree of Christ-Believing Traditions</a></em>');
  return Object.assign({}, source, { tab: Object.assign({}, source.tab, { record: rec.replace(TREE_NAME, linked) }) });
}

TABBED.forEach((code) => {
  const source = withTreeLink(sources[code] || null);
  const noteKey = notes[code] || null;
  const id = code.toLowerCase();
  articles[id] = {
    code,
    id,
    n: DISPLAYED_N[code] || Number(code.slice(1)),
    source,                       // disclosure source: Part 2 -> Disclosure tab, Part 3 -> Record tab
    noteKey,                      // howWeHold key: its note is moved into the Disclosure tab
    stage1: step89.on ? (step89.stage1[code] || '') : '',    // "What the measurement found" (Stage 1 disclosures)
    summary: counts.on ? (counts.tables[code] || '') : '',   // the Record tab's summary table
    baptism: baptism.on ? (baptism.byArticle[code] || '') : '',   // Article 11: the sixteen-family baptism table, after the summary table
    disclosureLine: !source && !noteKey && !(step89.on && step89.stage1[code])
      ? GENERATED.noDisclosure + (methodHtml ? ' ' + GENERATED.method : '')
      : '',
    recordLine: source || (counts.on && counts.tables[code]) ? '' : GENERATED.noRecord,
  };
});

// Split an Article include into its title and its body, without touching either.
function split(html) {
  const m = /^\s*(<h2 class="article-title">[^]*?<\/h2>)\s*(<div class="article-body">[^]*<\/div>)\s*$/.exec(html);
  if (!m) throw new Error('article tabs: an Article include is not "<h2 class=article-title> + <div class=article-body>"');
  return { title: m[1], body: m[2] };
}

// T4 (CODE-AOID2-52): the learner's own-question box goes straight after the Article's reflection block
// (.article-rjw), inside the Article body. The Article includes are not touched: the box is added here, once,
// for every Article. Each include must hold exactly one reflection block.
function withQuestion(body, id) {
  const re = /<div class="article-rjw">[^]*?<\/div>/g;
  const n = (body.match(re) || []).length;
  if (n !== 1) throw new Error('article tabs: ' + id + ' expected exactly one reflection block, found ' + n);
  return body.replace(re, (m) => m + '\n        ' + teaching.questionHtml(id));
}

module.exports = { articles, methodHtml, generated: GENERATED, split, teaching, withQuestion };
