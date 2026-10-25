/* ============================================================
   AOID2 RECORD-TAB NOTES  (CODE-AOID2-56; ruling AOID2-RECORD-NOTES-PLACE option 1)

   Template name:  aoidRecordNotes
   Exists only when the Second Edition switch is ON (src/_data/aoidSecondEdition.js);
   with it OFF this module is { on: false } and nothing here reaches a page.

   One shared component: a short "Notes" list directly under a teaching's per-family table on a Record tab,
   shown only where an approved note exists, each note led by the family's name and a period, in bold. The notes are data:
     data-sources/aoid/second-edition/record_notes.json   { notes: [{id, article, teaching, [table], family, text}]  (table: the teaching whose table the note sits under, where it differs), held: [...] }
   Each text is checked at build time, word for word, against the approved wording file (R1-R5); a difference
   stops the build. "held" lists approved notes that have no per-family table to sit under; they are not rendered.

   A note whose "table" is "summary" sits under the Article's Record-tab summary table (src/_data/aoidCounts.js).
   Use:  notesHtml('A11', 'A11-F7')  ->  the list, or '' when no note is held for that teaching;
         notesHtml('A06', 'summary')  ->  the notes under that Article's summary table.
   ============================================================ */

const fs = require('fs');
const path = require('path');
const { on } = require('./aoidSecondEdition.js');

const DATA = 'data-sources/aoid/second-edition/record_notes.json';
const WORDING = 'data-sources/aoid/second-edition/WoP_AOID2_Step89_53Review_ApprovedWording_20261025.md';

if (!on) module.exports = { on: false };
else {
  const fail = (m) => { throw new Error('record notes: ' + m); };
  const read = (f) => fs.readFileSync(path.join(process.cwd(), f), 'utf8').replace(/\r\n/g, '\n');
  const MarkdownIt = require('markdown-it');
  const inline = (s) => MarkdownIt({ html: false, linkify: false, typographer: false }).renderInline(s);
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const data = JSON.parse(read(DATA));

  // The approved text of one R note: the first non-empty line under its "## Rn. " heading.
  const wording = read(WORDING).split('\n');
  const approved = (id) => {
    const at = wording.findIndex((l) => l.startsWith('## ' + id + '. '));
    if (at < 0) fail(id + ' not found in the approved wording');
    return wording.slice(at + 1).filter((l) => l.trim() !== '')[0];
  };
  data.notes.forEach((n) => {
    if (n.text !== approved(n.id)) fail(n.id + ': the text differs from the approved wording');
  });

  const used = new Set();
  const notesHtml = (article, teaching) => {
    const mine = data.notes.filter((n) => n.article === article && (n.table || n.teaching) === teaching);
    if (!mine.length) return '';
    mine.forEach((n) => used.add(n.id + '|' + n.teaching));
    return '<div class="an-notes" data-notes-for="' + esc(teaching) + '"><h5 class="an-notes-title">Notes</h5><ul>'
      + mine.map((n) => '<li data-note="' + esc(n.id) + '"><strong class="an-notes-family">' + esc(n.family) + '.</strong> ' + inline(n.text) + '</li>').join('')
      + '</ul></div>';
  };

  module.exports = { on: true, source: DATA, notes: data.notes, held: data.held, notesHtml, used };
}
