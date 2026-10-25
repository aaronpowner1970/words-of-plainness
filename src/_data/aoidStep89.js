/* ============================================================
   AOID2 STEP 89 TEXT  (Phase C6, CODE-AOID2-48)

   Template name:  aoidStep89
   Exists only when the Second Edition switch is ON (src/_data/aoidSecondEdition.js);
   with it OFF this module is { on: false } and nothing here reaches a page.

   Builds three things, all from approved wording read at build time, never retyped.
   data-sources/aoid/second-edition/ holds byte-identical copies of
     wop-scratch/WoP_AOID2_Step89_ChangeLog_Draft_v1_20261019.md
     wop-scratch/WoP_AOID2_Step89_MethodAccount_Draft_v1_20261019.md
     wop-scratch/WoP_AOID2_Step89_Stage1Disclosures_Draft_v1_20261019.md

   changeLog   "What Changed in the Second Edition" with AMENDMENTS v2 A1-A5 and AMENDMENTS v3 B1-B5 applied (CODE-AOID2-49).
   method      "How These Articles Were Measured" with AMENDMENTS A1-A5 and A7 applied in the
               positions given (A6, the Living Tree link, has no page to link to; see METHOD_LINKS).
               The figures in A1 and A4 are read from the Father of Spirits disclosure source
               (aoidDisclosures) and checked against the approved words; if they differ the
               build stops.
   stage1      each Article's "What the measurement found" (Articles 2, 4, 6, 11).

   Bracketed instructions in the approved files ([VERIFY ...], [PENDING ...]) are not page
   text. They are removed from what renders; each is reported by the build run.

   REVIEW-ONLY WRAP. A Stage 1 paragraph whose [VERIFY] check found a mismatch is listed in
   REVIEW_ONLY below. It is then left out of the build unless WOP_AOID2_BUILD_REVIEW=1, and
   in that build it is shown inside a visibly marked box. To remove the wrap for a paragraph,
   delete its line from REVIEW_ONLY (the paragraph then renders like every other one).
   ============================================================ */

const fs = require('fs');
const path = require('path');
const MarkdownIt = require('markdown-it');
const { on } = require('./aoidSecondEdition.js');

const DIR = 'data-sources/aoid/second-edition/';
const CHANGELOG = DIR + 'WoP_AOID2_Step89_ChangeLog_Draft_v1_20261019.md';
const METHOD = DIR + 'WoP_AOID2_Step89_MethodAccount_Draft_v1_20261019.md';
const STAGE1 = DIR + 'WoP_AOID2_Step89_Stage1Disclosures_Draft_v1_20261019.md';
const ARTICLES_TEMPLATE = 'src/pages/articles.njk';

// Paragraphs shown only in a build-review build (WOP_AOID2_BUILD_REVIEW=1). Key: Article code + bold lead-in.
const REVIEW_ONLY = {};  // empty since CODE-AOID2-51: both held paragraphs checked out and are shown

// B4 (AMENDMENTS v3): the films line states what the build run found. The films for Articles 2 and 6 (made 7 Oct 2026,
// A02v2 vapwjdfYqEA and A06v2 4Bp1-gPunxc) read the Second Edition text of their Articles: the builder's aligner matches
// the reading to the Article text at 100.00% (Article 2, 119 words) and 99.44% (Article 6, 356 words, the one difference
// being "co heirs" against "coheirs"), and the Article 2 and Article 6 text of the Second Edition is the text it aligned to.
const FILMS_LINE = "The First Edition's films, PDFs and slides are labelled First Edition. The films for Articles 2 and 6, made on 7 October 2026, read the Second Edition text of those Articles and are labelled Second Edition.";

// Links the approved amendments ask for, where a target exists on the site.
const METHOD_LINKS = {
  livingTree: '/living-tree/', // A6, A6a (approved 25 Oct 2026): the first form of the page, src/pages/living-tree.njk.
};

if (!on) module.exports = { on: false };
else {
  const fail = (m) => { throw new Error('step 89 text: ' + m); };
  const read = (f) => fs.readFileSync(path.join(process.cwd(), f), 'utf8').replace(/\r\n/g, '\n');
  const md = () => MarkdownIt({ html: false, linkify: false, typographer: false });
  const once = (s, part, what) => {
    const n = s.split(part).length - 1;
    if (n !== 1) fail('"' + (what || part) + '" expected exactly once, found ' + n);
  };
  const replaceOnce = (s, from, to) => { once(s, from); return s.replace(from, () => to); };

  // The lines of `src` from the first line matching `startRe` up to (not including) the first later line matching `endRe`.
  const slice = (src, startRe, endRe, what) => {
    const lines = src.split('\n');
    const i = lines.findIndex((l) => startRe.test(l));
    if (i < 0) fail(what + ': start not found');
    let j = i + 1;
    while (j < lines.length && !endRe.test(lines[j])) j++;
    if (j >= lines.length) fail(what + ': end not found');
    return lines.slice(i, j);
  };
  // The ">" quoted paragraphs that follow the line matching `tagRe`.
  const quoted = (src, tagRe, what) => {
    const lines = src.split('\n');
    const i = lines.findIndex((l) => tagRe.test(l));
    if (i < 0) fail(what + ': amendment not found');
    const paras = [];
    let cur = [];
    let started = false;
    for (let j = i + 1; j < lines.length; j++) {
      const l = lines[j];
      if (/^>/.test(l)) {
        started = true;
        const t = l.replace(/^> ?/, '');
        if (t === '') { if (cur.length) { paras.push(cur.join(' ')); cur = []; } } else cur.push(t);
      } else if (started && l.trim() === '') { if (cur.length) { paras.push(cur.join(' ')); cur = []; } break; }
      else if (started) break;
    }
    if (cur.length) paras.push(cur.join(' '));
    if (!paras.length) fail(what + ': no quoted text');
    return paras;
  };
  const blocks = (lines) => lines.join('\n').replace(/\n{3,}/g, '\n\n').trim().split('\n\n');

  // ---------------------------------------------------------------- change log
  const changeLog = (() => {
    const src = read(CHANGELOG);
    const body = slice(src, /^## What Changed in the Second Edition$/, /^---$/, 'change log');
    const title = body[0].replace(/^## /, '');
    let text = body.slice(1).join('\n').trim();

    // The marker on the count line is removed: this run builds the count (step 89).
    text = replaceOnce(text, '[PENDING, step 89] ', '');
    // The step 124 line is not rendered; it stays in the page template as a comment.
    const step124 = text.split('\n').filter((l) => l.includes('[PENDING, step 124]'));
    if (step124.length !== 1) fail('the [PENDING, step 124] line expected exactly once');
    text = text.split('\n').filter((l) => !l.includes('[PENDING, step 124]')).join('\n');
    // The two [VERIFY] markers are instructions; they do not render.
    once(text, ' [VERIFY which, against the First Edition text]');
    text = text.replace(' [VERIFY which, against the First Edition text]', '');
    once(text, '- [VERIFY] The First Edition');
    text = text.replace('- [VERIFY] The First Edition', '- The First Edition');

    // AMENDMENTS v3 B1-B5 (approved 20 Oct 2026). The wording is read from the amendment lines, never retyped.
    const amendLine = (tag) => {
      const hit = src.split('\n').filter((l) => l.startsWith('**' + tag + '.'));
      if (hit.length !== 1) fail('amendment ' + tag + ' expected exactly once, found ' + hit.length);
      return hit[0];
    };
    const unq = (s) => s.split('\\"').join('"');
    const swapLine = (text0, startsWith, withText, what) => {
      const ls = text0.split('\n');
      const k = ls.map((l, i) => (l.startsWith(startsWith) ? i : -1)).filter((i) => i >= 0);
      if (k.length !== 1) fail(what + ': line expected exactly once, found ' + k.length);
      ls[k[0]] = withText;
      return ls.join('\n');
    };
    const b1 = amendLine('B1');
    const b1a = /The line becomes: "(.*?)" The held step-124 line becomes \(.*?\): "(.*)"$/.exec(b1);
    if (!b1a) fail('B1: wording not found');
    text = swapLine(text, '- **Article 9, Of Finding Our Way.**', '- ' + unq(b1a[1]), 'B1');
    const step124B = unq(b1a[2]);
    const b2 = amendLine('B2');
    const b2a = /The line becomes: "(.*)" \(The witness mark is the dagger/.exec(b2);
    if (!b2a) fail('B2: wording not found');
    text = swapLine(text, '- **Article 11, Of Covenants and Commitments.**', '- ' + unq(b2a[1]), 'B2');
    const b3 = amendLine('B3');
    const b3a = /^\*\*B3\. Article 12\.\*\* "(.*?)" becomes "(.*?)"/.exec(b3);
    if (!b3a) fail('B3: wording not found');
    text = replaceOnce(text, b3a[1], b3a[2]);
    // B4: the films line states what was found (FILMS_LINE, above). The check below keeps the finding honest.
    const films = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'src/_data/aoid_videos.json'), 'utf8'));
    const filmIds = { A02: 'vapwjdfYqEA', A06: '4Bp1-gPunxc' };
    Object.keys(filmIds).forEach((k) => {
      const entry = films.find((e) => e.code === k);
      if (!entry || entry.youtube !== filmIds[k]) fail('B4: the film for ' + k + ' is no longer ' + filmIds[k] + '; re-check which edition it reads');
    });
    text = swapLine(text, '- The First Edition', '- ' + FILMS_LINE, 'B4');
    const b5 = amendLine('B5');
    const b5a = /^\*\*B5\..*?:\*\* "(.*)" \(Ruling /.exec(b5);
    if (!b5a) fail('B5: wording not found');
    // B5 is the last line under "How the Articles are now shown", after the films line.
    text = replaceOnce(text, '- ' + FILMS_LINE, '- ' + FILMS_LINE + '\n- ' + unq(b5a[1]));

    // AMENDMENTS v2 A1-A5 (the approved file gives the wording and the positions).
    text = replaceOnce(text, 'were added to nine others', 'were added to seven others');                       // A1
    const a5 = quoted(src, /^\*\*A5 \(criterion 9\)/, 'A5')[0];                                                  // A5
    const inShort = text.split('\n').findIndex((l) => l.startsWith('**In short.**'));
    if (inShort < 0) fail('"In short" paragraph not found');
    const tl = text.split('\n');
    tl.splice(inShort + 1, 0, '', a5);
    text = tl.join('\n');
    text = replaceOnce(text, 'measured against sixteen traditions', '[measured against sixteen traditions](METHOD_URL)'); // A2 (url set below)
    text = replaceOnce(text, '**A way to correct us.**', '**[A way to correct us](/aoid/corrections/).**');          // A4

    // AMENDMENTS v4 C1 and C2 (approved 25 Oct 2026). The wording is read from the amendment, never retyped.
    // C1: the bullet that follows the line "**C1. New bullet under ...**" goes immediately after the "A way to correct us" bullet.
    const c1Head = src.split('\n').map((l, i) => (l.startsWith('**C1. New bullet under "How the Articles are now shown"') ? i : -1)).filter((i) => i >= 0);
    if (c1Head.length !== 1) fail('C1: amendment line expected exactly once, found ' + c1Head.length);
    const c1Bullet = src.split('\n').slice(c1Head[0] + 1).filter((l) => l.trim() !== '')[0];
    if (!c1Bullet || !c1Bullet.startsWith('- **Helps for the reader.**')) fail('C1: the bullet "Helps for the reader." was not found after the C1 line');
    const afterCorrect = text.split('\n').findIndex((l) => l.startsWith('- **[A way to correct us]'));
    if (afterCorrect < 0) fail('C1: the "A way to correct us" bullet was not found');
    const cl = text.split('\n');
    cl.splice(afterCorrect + 1, 0, c1Bullet);
    text = cl.join('\n');
    // C2: markup only. Each disclosure title in the "Two disclosures in full" bullet links to its page; both must exist.
    const c2 = src.split('\n').filter((l) => l.startsWith('**C2 (APPROVED'));
    if (c2.length !== 1) fail('C2: amendment line expected exactly once, found ' + c2.length);
    const c2a = /\*Of the Father of Spirits\* links to (\/aoid\/disclosures\/[a-z-]+\/) and \*Sexual Holiness\* links to (\/aoid\/disclosures\/[a-z-]+\/)/.exec(c2[0]);
    if (!c2a) fail('C2: the two links were not found in the amendment');
    [c2a[1], c2a[2]].forEach((u) => {
      const pages = ['father-of-spirits', 'sexual-holiness'].map((n) => read('src/pages/aoid/disclosures/' + n + '.njk'));
      if (!pages.some((p) => p.includes('permalink: "' + u + '"'))) fail('C2: no page has the permalink ' + u);
    });
    text = replaceOnce(text, '*Of the Father of Spirits*', '*[Of the Father of Spirits](' + c2a[1] + ')*');
    text = replaceOnce(text, '*Sexual Holiness*', '*[Sexual Holiness](' + c2a[2] + ')*');

    // A3: each Article name links to its Article. Section ids are read from the Articles page.
    const tpl = read(ARTICLES_TEMPLATE);
    const ids = [];
    const re = /<section class="article-section" id="([^"]+)"/g;
    let m;
    while ((m = re.exec(tpl))) if (m[1] !== 'of-plainness' && !ids.includes(m[1])) ids.push(m[1]);
    if (ids.length !== 13) fail('expected 13 counted Article sections, found ' + ids.length);
    let linked = 0;
    text = text.split('\n').map((l) => {
      const b = /^- \*\*(Article (\d+), [^*]+?)(\.?)\*\*/.exec(l);
      if (!b) return l;
      linked++;
      return l.replace(b[0], '- **[' + b[1] + '](/articles/#' + ids[Number(b[2]) - 1] + ')' + b[3] + '**');
    }).join('\n');
    if (linked !== 13) fail('expected 13 Article lines in "What each Article gained", linked ' + linked);

    return { title, text, step124: step124B, articleIds: ids };
  })();

  // ---------------------------------------------------------------- method account
  const NUM = ['none', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen'];
  const method = (() => {
    const src = read(METHOD);
    const base = blocks(slice(src, /^## How These Articles Were Measured$/, /^---$/, 'method account'));

    // A1 and A4 read the Father of Spirits figures from its disclosure source; the approved words must agree.
    const fos = require('./aoidDisclosures.js').fatherOfSpirits;
    const f1 = fos.teachings.find((t) => t.id === 'A2-F1');
    if (!f1) fail('A2-F1 not found in the Father of Spirits disclosure source');
    const k = f1.counts;
    const a1 = quoted(src, /^\*\*A1\. Before "In short"/, 'A1')[0];
    const am = /Of sixteen Christian traditions, (\w+) teach it in their own adopted texts, (\w+) teaches otherwise, (\w+) have adopted no text on it either way, and (\w+) are still being confirmed\./.exec(a1);
    if (!am) fail('A1: the sentence with the four figures was not found in the approved wording');
    const want = [NUM[k.teach], NUM[k.divided], NUM[k.none], NUM[k.confirm]];
    if (want.join('|') !== am.slice(1).join('|')) {
      fail('A1 DISAGREES with the Father of Spirits disclosure source: the approved wording says ' + am.slice(1).join('/') + ', the source gives ' + want.join('/') + ' (' + k.teach + ' teach, ' + k.divided + ' divided, ' + k.none + ' no position, ' + k.confirm + ' being confirmed). Stop and report.');
    }
    const a4 = quoted(src, /^\*\*A4\. End of "When a teaching falls short"/, 'A4')[0];
    const cap = NUM[k.teach][0].toUpperCase() + NUM[k.teach].slice(1);
    if (!a4.includes(cap + ' is short of thirteen')) fail('A4 DISAGREES with the Father of Spirits disclosure source: "' + cap + ' is short of thirteen" not in the approved wording');
    if (k.teach >= 13 || k.divided !== 0) fail('A4: the source count no longer fits "short of thirteen" and "no tradition contradicts it"');

    const a2 = quoted(src, /^\*\*A2\. After "In short"/, 'A2')[0];
    const a3 = quoted(src, /^\*\*A3\. End of "What we read"/, 'A3')[0];
    const a5 = quoted(src, /^\*\*A5\. New section after/, 'A5');
    const a7 = quoted(src, /^\*\*A7\. APPROVED/, 'A7')[0];
    if (a5.length !== 2 || !/^### /.test(a5[0])) fail('A5: expected a heading and one paragraph');

    const at = (re, what) => {
      const hit = base.map((b, i) => (re.test(b) ? i : -1)).filter((i) => i >= 0);
      if (hit.length !== 1) fail('method account: ' + what + ' expected once, found ' + hit.length);
      return hit[0];
    };
    const out = base.slice();
    // Work from the end so earlier indexes stay valid.
    const iIfWrong = at(/^### If we have it wrong$/, '"If we have it wrong"');
    out.splice(iIfWrong, 0, a5[0], a5[1]);                                                  // A5: new section after "How quotations were checked"
    const iReadings = at(/^### Readings still being weighed$/, '"Readings still being weighed"');
    out.splice(iReadings, 0, a4);                                                           // A4: end of "When a teaching falls short"
    const iOnly = at(/^Only the first number counts toward thirteen\.$/, '"Only the first number..."');
    out[iOnly] = out[iOnly] + ' ' + a7;                                                     // A7: after that sentence
    const iSixteen = at(/^### The sixteen traditions$/, '"The sixteen traditions"');
    out.splice(iSixteen, 0, a3);                                                            // A3: end of "What we read"
    const iShort = at(/^\*\*In short\.\*\*/, '"In short"');
    out.splice(iShort + 1, 0, a2);                                                          // A2: after "In short"
    out.splice(1, 0, a1);                                                                   // A1: before "In short" (after the heading)
    let text = out.join('\n\n');
    // A6 / A6a: the words "The Living Tree of Christ-Believing Traditions" link to the page.
    if (METHOD_LINKS.livingTree) text = replaceOnce(text, '*The Living Tree of Christ-Believing Traditions*', '*[The Living Tree of Christ-Believing Traditions](' + METHOD_LINKS.livingTree + ')*');
    return { text, figures: { taught: k.teach, divided: k.divided, none: k.none, confirm: k.confirm } };
  })();

  // The method account has one copy per Article's Disclosure tab. The change log's A2 link goes to Article 2's.
  const METHOD_URL = '/articles/#a02-method';
  const changeLogHtml = md().render(changeLog.text.replace('METHOD_URL', METHOD_URL));
  const methodHtml = md().render(method.text);

  // ---------------------------------------------------------------- Living Tree page (A6a, "A6a RELEASED")
  // Title, subtitle, the one sentence linking the method account, and the alt text are read from the approved A6a section.
  const livingTree = (() => {
    const src = read(METHOD);
    const lines = src.split('\n');
    const i = lines.findIndex((l) => l.startsWith('## A6a, the Living Tree page'));
    if (i < 0) fail('A6a section not found');
    const sec = lines.slice(i);
    const one = (re, what) => {
      const hit = sec.filter((l) => re.test(l));
      if (hit.length !== 1) fail('A6a: ' + what + ' expected once, found ' + hit.length);
      return hit[0];
    };
    const title = one(/^> # /, 'title').replace(/^> # /, '');
    const subtitle = /^> \*(.+)\*$/.exec(one(/^> \*[^*]+\*$/, 'subtitle'))[1];
    const sentence = one(/^> The Tree shows twenty-five branches\./, 'method sentence').replace(/^> /, '');
    const alt = /^\*\*Alt text:\*\* "(.+)"$/.exec(one(/^\*\*Alt text:\*\* "/, 'alt text'))[1];
    if (!/\[How These Articles Were Measured\]\(method account anchor\)/.test(sentence)) fail('A6a: the method-account link in the sentence was not found');
    // L1-L3 (approved 25 Oct 2026, "A6a TEACHING LINES L1-L3"): each is the quoted line after its tag line, built by the same
    // components as the Articles' T1 (practice line), T2 (boxed prompt) and T3 (correction line), in aoidTeaching.js.
    const after = (tag) => {
      const k = sec.findIndex((l) => l.startsWith(tag));
      if (k < 0) fail('A6a: ' + tag + ' not found');
      const q = sec.slice(k + 1).find((l) => l.trim() !== '');
      if (!q || !q.startsWith('> ')) fail('A6a: no quoted line after ' + tag);
      return q.slice(2);
    };
    const teaching = require('./aoidTeaching.js');
    const l1 = after('L1 (');
    const l2 = after('L2 (');
    const l3 = after('L3 (');
    const l2m = /^\*\*Before you read on:\*\* (.+)$/.exec(l2);
    if (!l2m) fail('A6a: L2 does not open with "**Before you read on:**"');
    const teachLines = { l1Html: teaching.practiceLine(l1), l2Html: teaching.beforeBox('Before you read on: ' + l2m[1]), l3Html: teaching.correctionLine(l3), l1, l2: 'Before you read on: ' + l2m[1], l3 };
    // The cover note (Article 11 record note) with the table; L2 goes directly above the table.
    const cover = require('./aoidDisclosures.js').sexualHoliness.coverHtml;
    const t = cover.indexOf('<div class="disc-table-wrap">');
    if (t < 0 || cover.split('<div class="disc-table-wrap">').length !== 2) fail('A6a: the cover note must hold exactly one table');
    return { title, subtitle, sentenceHtml: md().renderInline(sentence.replace('(method account anchor)', '(' + METHOD_URL + ')')), alt, lines: teachLines, coverAbove: cover.slice(0, t), coverFrom: cover.slice(t) };
  })();

  // ---------------------------------------------------------------- Stage 1 disclosures
  const stage1 = (() => {
    const src = read(STAGE1);
    const lines = src.split('\n');
    const CODES = { 2: 'A02', 4: 'A04', 6: 'A06', 11: 'A11' };
    const out = {};
    const verifyMarks = [];
    Object.keys(CODES).forEach((n) => {
      const i = lines.findIndex((l) => new RegExp('^## Article ' + n + ', ').test(l));
      if (i < 0) fail('Article ' + n + ' section not found');
      let j = i + 1;
      while (j < lines.length && !/^## /.test(lines[j])) j++;
      const sec = lines.slice(i, j);
      const h = sec.findIndex((l) => l === '### What the measurement found');
      if (h < 0) fail('Article ' + n + ': "What the measurement found" not found');
      let e = h + 1;
      while (e < sec.length && !/^### /.test(sec[e])) e++;
      const bl = blocks(sec.slice(h, e));
      const code = CODES[n];
      const html = [];
      bl.forEach((b, idx) => {
        let text = b;
        if (/\[VERIFY[^\]]*\]/.test(text)) {
          verifyMarks.push({ code, mark: text.match(/\[VERIFY[^\]]*\]/)[0] });
          text = text.replace(/\s*\[VERIFY[^\]]*\]/, '');
        }
        const lead = (/^\*\*([^*]+)\*\*/.exec(text) || [])[1];
        const key = code + ' ' + lead;
        const rendered = md().render(text);
        if (lead && REVIEW_ONLY[key]) {
          if (process.env.WOP_AOID2_BUILD_REVIEW === '1') html.push('<div class="an-review-only" role="note"><p class="an-review-only-tag">Build review only: ' + REVIEW_ONLY[key].replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</p>' + rendered + '</div>');
        } else html.push(rendered);
      });
      out[code] = html.join('');
    });
    return { html: out, verifyMarks };
  })();

  module.exports = {
    on: true,
    changeLog: { title: changeLog.title, html: changeLogHtml, step124: changeLog.step124, articleIds: changeLog.articleIds },
    methodHtml,
    methodFigures: method.figures,
    methodUrl: METHOD_URL,
    methodLinks: METHOD_LINKS,
    livingTree,
    stage1: stage1.html,
    stage1VerifyMarks: stage1.verifyMarks,
  };
}
