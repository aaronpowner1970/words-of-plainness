/* ============================================================
   LIVING TREE PAGE WORDING  (AOID2 step 163, CODE-AOID2-112; version 2 for step 287, CODE-AOID2-113)

   Template name:  livingTreeText
   Feeds src/pages/living-tree.njk (/living-tree/) with the switch ON or OFF.

   Every reader-facing word comes from the approved wording, read at build time and
   never retyped: data-sources/living-tree/ holds a byte-identical copy of
   wop-scratch/WoP_AOID2_LivingTree_ApprovedWording_v2_20261109.md (version 2, approved by
   Aaron 9 Nov 2026 in the review of CODE-AOID2-112, CHAT-AOID2-111b). It supersedes the
   version 1 copy, which is retired; this one file governs the page. If the copy's text
   changes, its SHA-256 (line endings normalised to LF) no longer matches SHA below and the
   build stops.

     intro       Part 1, the page introduction
     practice    2.1, the practice line
     howToRead   2.2, how to read a tradition fairly
     key         2.3, the key to the rows and placement lines
     placement   2.4, the label before each branch's status line ("Placement:")
     correction  2.5, the per-branch correction line, linked to /aoid/corrections/; present only with
                 the Second Edition switch ON (the form exists only then), and checked against the
                 link text the corrections form already uses (src/_data/aoidCorrections.js)
     question    2.6, the per-branch question line
     sourceLabel 2.7, "Source:" / "Sources:"
     learnMore   2.8, the heading over each branch's inquirer resources (the resources themselves are
                 in src/_data/livingTree.json, written by tools/build_living_tree.py)
     notes       2.9 (and any later "Resource note" section), keyed by section number: a note shown in
                 small type directly under one inquirer resource, with its own sources. The generator
                 marks the resource (its "note" field, from the signed resource-labels file); the build
                 checks that the marked resource is the one the section's heading names, on the branch
                 it names, and that no resource of that name goes without its note.
     branches    Part 3, keyed by branch slug: the description and its sources

   Markup rules of the approved file: "*...*" is italic; a scripture reference such as
   "Ephesians 2:20" (a book named in src/_data/scriptures.json) is returned as its own part so the
   page can link it with the site's scripture link generator (the scriptureUrl filter).
   ============================================================ */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { on } = require('./aoidSecondEdition.js');

const FILE = 'data-sources/living-tree/WoP_AOID2_LivingTree_ApprovedWording_v2_20261109.md';
const SHA = 'd4f6e5230164fa1e28563253e1adff79db4704db97316dc6b16f0bec281907bb';

const fail = (m) => { throw new Error('living tree wording: ' + m); };
const text = fs.readFileSync(path.join(process.cwd(), FILE), 'utf8').replace(/\r\n/g, '\n');
const sha = crypto.createHash('sha256').update(text, 'utf8').digest('hex');
if (sha !== SHA) fail('the approved-wording copy has changed (SHA-256 ' + sha + ', expected ' + SHA + ')');
const lines = text.split('\n');

// The lines from the line matching `startRe` up to (not including) the next line matching `endRe`.
const section = (startRe, endRe, what) => {
  const i = lines.findIndex((l) => startRe.test(l));
  if (i < 0) fail(what + ': not found');
  let j = i + 1;
  while (j < lines.length && !endRe.test(lines[j])) j++;
  return lines.slice(i + 1, j);
};
// The one "> " paragraph in a block of lines.
const quote = (block, what) => {
  const q = block.filter((l) => l.startsWith('> '));
  if (q.length !== 1) fail(what + ': expected exactly one "> " paragraph, found ' + q.length);
  return q[0].slice(2);
};
// The one capture of `re` in a block of lines.
const one = (block, re, what) => {
  const hits = block.map((l) => re.exec(l)).filter(Boolean);
  if (hits.length !== 1) fail(what + ': expected exactly once, found ' + hits.length);
  return hits[0][1];
};

// ---- Scripture references: books the site's generator knows -------------------------------
const BOOKS = require('./scriptures.json').books;
const REF = /((?:[1-4] )?[A-Z][A-Za-z&]*(?: (?:of )?[A-Z][A-Za-z&]*)*) (\d+):(\d+(?:[-–]\d+)?)/g;

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** A paragraph of the approved file as parts: { html } (escaped text, *...* as <em>) or { ref } (a scripture reference). */
function parts(src, what) {
  if ((src.match(/\*/g) || []).length % 2) fail(what + ': unpaired "*"');
  const out = [];
  let last = 0;
  const html = (s) => { if (s) out.push({ html: esc(s).replace(/\*([^*]+)\*/g, '<em>$1</em>') }); };
  for (const m of src.matchAll(REF)) {
    // the book name may have picked up capitalised words before it ("See John 3:16"): keep the longest known tail
    const words = m[1].split(' ');
    let book = null;
    for (let k = 0; k < words.length && !book; k++) {
      const cand = words.slice(k).join(' ');
      if (BOOKS[cand.toLowerCase()]) book = cand;
    }
    if (!book) continue;
    const ref = book + ' ' + m[2] + ':' + m[3];
    const at = m.index + m[0].length - ref.length;
    if (src.slice(last, at).split('*').length % 2 === 0) fail(what + ': a scripture reference inside italics');
    html(src.slice(last, at));
    out.push({ ref });
    last = at + ref.length;
  }
  html(src.slice(last));
  return out;
}
/** The plain text of a paragraph's parts, as a reader sees it (for the build check of the page). */
const plain = (ps) => ps.map((p) => (p.ref ? p.ref : p.html.replace(/<\/?em>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'))).join('');

// ---- Part 1 ---------------------------------------------------------------------------------
const introSrc = quote(section(/^## Part 1: /, /^## /, 'Part 1'), 'Part 1 introduction');

// ---- Part 2 ---------------------------------------------------------------------------------
const p2 = (n) => section(new RegExp('^### 2\\.' + n + ' '), /^##/, 'Part 2.' + n);
const practiceSrc = quote(p2(1), '2.1 practice line');
const howToReadSrc = quote(p2(2), '2.2 how-to-read line');
const keySrc = quote(p2(3), '2.3 key');
const placement = one(p2(4), /with the label "([^"]+)" before it/, '2.4 placement label');
const correctionSrc = quote(p2(5), '2.5 correction line');
const correctionHref = one(p2(5), /^Links to (\/\S+\/)\.$/, '2.5 link target');
const questionSrc = quote(p2(6), '2.6 question line');
const srcLabels = /^Shown as "([^"]+)" or "([^"]+)" followed by/.exec(p2(7).find((l) => l.startsWith('Shown as ')) || '');
if (!srcLabels) fail('2.7: the "Source:" / "Sources:" labels were not found');
const learnMore = one(p2(8), /^Each branch shows "([^"]+)" followed by/, '2.8 heading');

// 2.5 is built only with the switch ON, where /aoid/corrections/ exists; its words and target must be the form's own.
let correction = null;
if (on) {
  const corr = require('./aoidCorrections.js');
  if (!corr.on) fail('2.5: the corrections form is off while the Second Edition switch is on');
  if (corr.linkText !== correctionSrc) fail('2.5: the approved line differs from the corrections form link text');
  if (corr.page !== correctionHref) fail('2.5: the approved target ' + correctionHref + ' differs from the form at ' + corr.page);
  correction = { text: correctionSrc, href: corr.page };
}

// ---- Resource notes (2.9): a "> " paragraph, then "Source:" / "Sources:" right after it, then the sources ----
const SRC_LINE = /^- (.+) \| (https?:\/\/\S+)$/;
const notes = {};
lines.forEach((l, i) => {
  const h = /^### (2\.\d+) Resource note: (.+?) \(.* on the (.+?) branch[;)]/.exec(l);
  if (!h) return;
  const id = h[1];
  let j = i + 1;
  while (j < lines.length && !/^##/.test(lines[j])) j++;
  const block = lines.slice(i + 1, j);
  const src = quote(block, id + ' resource note');
  const sources = block.map((x) => SRC_LINE.exec(x)).filter(Boolean).map((m) => ({ label: m[1], url: m[2] }));
  const label = block.find((x) => x === srcLabels[1] || x === srcLabels[2]);
  if (!label) fail(id + ': no "' + srcLabels[1] + '" / "' + srcLabels[2] + '" line');
  if (!sources.length) fail(id + ': no sources listed');
  if ((label === srcLabels[1]) !== (sources.length === 1)) fail(id + ': "' + label + '" with ' + sources.length + ' source(s)');
  if (block[block.findIndex((x) => x.startsWith('> ')) + 1] !== label) fail(id + ': the source line does not follow the note');
  const ps = parts(src, id);
  notes[id] = { id, resource: h[2], branch: h[3], parts: ps, text: plain(ps), sourceLabel: label, sources };
});

// ---- Part 3 ---------------------------------------------------------------------------------
const part3 = section(/^## Part 3: /, /^## /, 'Part 3');
const branches = {};
const order = [];
for (let i = 0; i < part3.length; i++) {
  const h = /^### ([a-z0-9-]+) \| (.+)$/.exec(part3[i]);
  if (!h) continue;
  const slug = h[1];
  if (branches[slug]) fail(slug + ': listed twice');
  let j = i + 1;
  while (j < part3.length && !/^### /.test(part3[j])) j++;
  const block = part3.slice(i + 1, j);
  const desc = quote(block, slug + ' description');
  const sources = [];
  let label = null;
  block.forEach((l) => {
    const s = /^- (.+) \| (https?:\/\/\S+)$/.exec(l);
    if (s) sources.push({ label: s[1], url: s[2] });
    else if (l === srcLabels[1] || l === srcLabels[2]) label = l;
  });
  const none = block.some((l) => /^Source: none shown \(/.test(l));
  if (none && (sources.length || label)) fail(slug + ': "none shown" and sources together');
  if (!none) {
    if (!label) fail(slug + ': no "' + srcLabels[1] + '" / "' + srcLabels[2] + '" line');
    if (!sources.length) fail(slug + ': no sources listed');
    if ((label === srcLabels[1]) !== (sources.length === 1)) fail(slug + ': "' + label + '" with ' + sources.length + ' source(s)');
    // the description must stand right after the heading and the source line right after the description (2.7)
    const di = block.findIndex((l) => l.startsWith('> '));
    if (block[di + 1] !== label) fail(slug + ': the source line does not follow the description');
  }
  const descParts = parts(desc, slug);
  branches[slug] = { slug, label: h[2], description: descParts, descriptionText: plain(descParts), sourceLabel: none ? null : label, sources };
  order.push(slug);
}
if (order.length !== 25) fail('expected twenty-five branch descriptions, found ' + order.length);

// The descriptions are keyed by the same slugs, in the same order, as the generator's branches.
const tree = require('./livingTree.json');
const treeSlugs = tree.branches.map((b) => b.slug);
if (treeSlugs.join(' ') !== order.join(' ')) fail('Part 3 slugs or order differ from src/_data/livingTree.json');

// Each resource note stands under the resource its heading names, on the branch it names, and under no other.
const noted = {};
tree.branches.forEach((b) => (b.resources || []).forEach((r) => {
  const named = Object.values(notes).find((n) => n.branch === b.label && r.label.startsWith(n.resource + ', '));
  if (r.note) {
    const n = notes[r.note];
    if (!n) fail(b.slug + ': resource "' + r.label + '" carries note ' + r.note + ', which the approved file does not have');
    if (n !== named) fail(r.note + ': it names ' + n.resource + ' on the ' + n.branch + ' branch, not "' + r.label + '" on ' + b.label);
    if (noted[r.note]) fail(r.note + ': attached to more than one resource');
    noted[r.note] = r.label;
  } else if (named) fail(b.slug + ': resource "' + r.label + '" is shown without its approved note ' + named.id);
}));

const para = (src, what) => { const ps = parts(src, what); return { parts: ps, text: plain(ps) }; };

module.exports = {
  source: FILE,
  intro: para(introSrc, 'Part 1'),
  practice: para(practiceSrc, '2.1'),
  howToRead: para(howToReadSrc, '2.2'),
  key: para(keySrc, '2.3'),
  placement,
  question: questionSrc,
  correction,
  sourceLabels: { one: srcLabels[1], many: srcLabels[2] },
  learnMore,
  notes,
  branches,
  order,
};
