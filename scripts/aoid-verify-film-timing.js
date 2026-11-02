#!/usr/bin/env node
/**
 * Film-timing guard for the Articles of Interfaith Discipleship (AoID) film pages.
 *
 * src/js/aoid-video.js plays a film with sentence-by-sentence follow only while the page's
 * word count equals the count the timing was built for (src/_data/aoid_video_timing.json,
 * built by tools/aoid_build_timing.py). On a mismatch the player logs a console warning and
 * plays WITHOUT follow, and the visitor sees nothing wrong. This check makes that failure
 * loud at build time instead of in a live session.
 *
 * It reads a finished build (default _site), finds every film page
 * (/chat/video-NN/ and /articles/video-NN/), counts the page's words exactly as
 * aoid-video.js does, and compares the count with the timing's.
 *
 *   Switch OFF (production)  any mismatch exits 1, naming the page, both counts and the two remedies.
 *   Switch ON  (WOP_AOID2_SECOND_EDITION=1)  mismatches are printed and the run exits 0: several
 *                            films are known to disagree until they are re-recorded at Gate 2.
 *
 * The word rule is NOT restated here: WORD_RE is read out of aoid-video.js itself. The element
 * selection (".article-body > p:not(.article-footnote)" inside the page's article element) is
 * implemented below, and the script fails if aoid-video.js no longer contains that selector, so
 * the check cannot drift from the player unnoticed.
 *
 * Usage:
 *   node scripts/aoid-verify-film-timing.js [build-folder]      (default: _site)
 *   npm run aoid:films
 *
 * Writes nothing. Uses htmlparser2 (devDependency).
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { parseDocument } = require('htmlparser2');

const ROOT = path.resolve(__dirname, '..');
const PLAYER = path.join(ROOT, 'src', 'js', 'aoid-video.js');
const TIMING = path.join(ROOT, 'src', '_data', 'aoid_video_timing.json');
const SELECTOR = ".article-body > p:not(.article-footnote)";

const OFF = process.env.WOP_AOID2_SECOND_EDITION !== '1';   // same rule as src/_data/aoidSecondEdition.js
const buildDir = path.resolve(process.argv[2] || path.join(ROOT, '_site'));

function die(msg) { console.error('aoid-verify-film-timing: FAILED\n' + msg); process.exit(1); }

// ── The word rule, taken from the player ──────────────────────────────────────
const playerSrc = fs.readFileSync(PLAYER, 'utf8');
const reMatch = playerSrc.match(/var WORD_RE = \/(.+)\/([a-z]*);/);
if (!reMatch) die('Could not find "var WORD_RE = /.../g;" in src/js/aoid-video.js. The player\'s word rule has changed shape; update this check.');
if (playerSrc.indexOf("querySelectorAll('" + SELECTOR + "')") === -1) {
  die('src/js/aoid-video.js no longer selects its words with querySelectorAll(\'' + SELECTOR + '\').\n' +
      'The player\'s element selection has changed; update scripts/aoid-verify-film-timing.js to match.');
}
const WORD_RE = new RegExp(reMatch[1], reMatch[2]);

function countWords(text) {
  WORD_RE.lastIndex = 0;
  let n = 0;
  while (WORD_RE.exec(text)) n++;
  return n;
}

// ── DOM helpers ───────────────────────────────────────────────────────────────
function hasClass(el, cls) { return (' ' + (el.attribs.class || '') + ' ').indexOf(' ' + cls + ' ') !== -1; }
function isTag(n) { return n.type === 'tag' || n.type === 'script' || n.type === 'style'; }

function findById(node, id) {
  for (const c of node.children || []) {
    if (!isTag(c)) continue;
    if (c.attribs.id === id) return c;
    const f = findById(c, id);
    if (f) return f;
  }
  return null;
}

function textOf(node) {            // every text node under node, in document order (TreeWalker SHOW_TEXT)
  let s = [];
  (function walk(n) {
    for (const c of n.children || []) {
      if (c.type === 'text') s.push(c.data);
      else if (c.children) walk(c);
    }
  })(node);
  return s;
}

function pageWords(article) {      // article.querySelectorAll('.article-body > p:not(.article-footnote)')
  let n = 0;
  (function walk(el) {
    for (const c of el.children || []) {
      if (!isTag(c)) continue;
      if (c.name === 'p' && !hasClass(c, 'article-footnote') && hasClass(el, 'article-body')) {
        for (const t of textOf(c)) n += countWords(t);
      }
      walk(c);
    }
  })(article);
  return n;
}

// ── Film pages ────────────────────────────────────────────────────────────────
const timing = JSON.parse(fs.readFileSync(TIMING, 'utf8'));
const pages = [];
for (const kind of ['chat', 'articles']) {
  const dir = path.join(buildDir, kind);
  if (!fs.existsSync(dir)) continue;
  for (const name of fs.readdirSync(dir).filter((d) => /^video-\d+$/.test(d)).sort()) {
    const file = path.join(dir, name, 'index.html');
    if (fs.existsSync(file)) pages.push({ url: '/' + kind + '/' + name + '/', file });
  }
}
if (!pages.length) die('No film pages (/chat/video-NN/ or /articles/video-NN/) found under ' + buildDir + '. Is this a build folder?');

const rows = [];
for (const p of pages) {
  const html = fs.readFileSync(p.file, 'utf8');
  const at = html.indexOf('window.WOP_AOID_VIDEO = {');
  if (at === -1) { rows.push({ url: p.url, status: 'skip', note: 'no film config (no reading timing, e.g. video-03)' }); continue; }
  const cfg = html.slice(at);
  const code = (cfg.match(/\bcode:\s*"([A-Z]\d+)"/) || [])[1];
  const articleId = (cfg.match(/\bel:\s*\{[^}]*?\barticle:\s*"([^"]+)"/) || [])[1];
  if (!code || !articleId) die(p.url + ': could not read the film config (code / article element id) from the page.');
  const article = findById(parseDocument(html), articleId);
  if (!article) die(p.url + ': article element #' + articleId + ' not found in the page.');
  const t = timing[code];
  const page = pageWords(article);
  if (!t || typeof t.tokens !== 'number') {
    rows.push({ url: p.url, code, page, status: 'notiming' });
    continue;
  }
  rows.push({ url: p.url, code, page, timing: t.tokens, status: page === t.tokens ? 'ok' : 'mismatch' });
}

// ── Report ────────────────────────────────────────────────────────────────────
const bad = rows.filter((r) => r.status === 'mismatch' || r.status === 'notiming');
for (const r of rows) {
  if (r.status === 'ok') console.log('  ok        ' + r.url + '  ' + r.code + '  page ' + r.page + ' = timing ' + r.timing);
  else if (r.status === 'skip') console.log('  skipped   ' + r.url + '  ' + r.note);
}
const REMEDIES =
  '    Remedy 1: pin the page\'s as-filmed text (src/_includes/aoid-asfilmed/, selected in src/_includes/layouts/aoid-video.njk),\n' +
  '              so the page keeps the words the film was recorded with.\n' +
  '    Remedy 2: for a new film, rebuild the timing with tools/aoid_build_timing.py.';
for (const r of bad) {
  if (r.status === 'mismatch') {
    console.error('  MISMATCH  ' + r.url + '  ' + r.code + ': page has ' + r.page + ' words, timing was built for ' + r.timing + '.\n' +
      '    aoid-video.js would play this film WITHOUT follow (no highlight, auto-scroll, citation stream, tap-to-hold or deep links).\n' + REMEDIES);
  } else {
    console.error('  NO TIMING ' + r.url + '  ' + r.code + ': the page has an article (' + r.page + ' words) but src/_data/aoid_video_timing.json has no entry for ' + r.code + '.\n' + REMEDIES);
  }
}
console.log('aoid-verify-film-timing: ' + pages.length + ' film pages checked in ' + buildDir + '; ' +
  rows.filter((r) => r.status === 'ok').length + ' match, ' + bad.length + ' mismatch, ' +
  rows.filter((r) => r.status === 'skip').length + ' skipped. Switch ' + (OFF ? 'OFF' : 'ON') + '.');

if (bad.length && OFF) {
  console.error('aoid-verify-film-timing: FAILED (switch OFF: every film page must match its timing).');
  process.exit(1);
}
if (bad.length) console.log('aoid-verify-film-timing: switch ON, mismatches reported only (known until Gate 2 re-records the films).');
else console.log('aoid-verify-film-timing: PASS');
