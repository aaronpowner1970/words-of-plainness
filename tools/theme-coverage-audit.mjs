#!/usr/bin/env node
/**
 * Theme Coverage Audit — Words of Plainness
 * ------------------------------------------------------------------
 * Crawls the site's written content and stress-tests the proposed
 * 22-theme vocabulary for gaps. It does NOT decide importance — it
 * surfaces frequency evidence so you (and Claude) can judge whether
 * any vitally important concept lacks a theme.
 *
 *   Run from anywhere:   node tools/theme-coverage-audit.mjs
 *   Report written to:   tools/theme-coverage-report.md
 *
 * Read-only. Lives in tools/ (outside src/), so it never builds or deploys.
 *
 * The cue lists below are deliberately CONSERVATIVE — when a real word
 * isn't clearly thematic it falls into the "uncovered" report rather
 * than being hidden under a theme. The uncovered lists + watchlist are
 * the real signal; edit the cues freely.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const SRC  = path.join(ROOT, 'src');

// ---- 1. Where to look ------------------------------------------------
const CONTENT_ROOTS = [
  { dir: path.join(SRC, 'chapters'),          exts: ['.md', '.njk'] },
  { dir: path.join(SRC, 'pages', 'studies'),  exts: ['.md', '.njk', '.html'] },
  { dir: path.join(SRC, 'posts'),             exts: ['.md'] },
];
const EXPLICIT_FILES = [ path.join(SRC, 'pages', 'articles.njk') ];
const MUSIC_JSON     = path.join(SRC, '_data', 'ministryMusic.json');

// ---- 2. Proposed theme vocabulary (slug -> cue stems, lowercase) -----
// A token is "covered" if it CONTAINS any cue. Overlap is fine.
const THEMES = {
  'plainness':                ['plain', 'humil', 'humble', 'mystery', 'secret', 'merognos', 'speculat', 'partial'],
  'nature-of-god':            ['god', 'father', 'almighty', 'divine', 'heavenly', 'creator'],
  'creation-purpose':         ['creat', 'agency', 'agenc', 'mortal', 'purpose', 'choice', 'choose', 'fallen', 'earth'],
  'revelation-scripture':     ['scriptur', 'prophet', 'reveal', 'revelation', 'canon', 'testament', 'vessel'],
  'jesus-christ':             ['jesus', 'christ', 'messiah', 'savior', 'redeemer', 'nazareth'],
  'atonement':                ['atone', 'cross', 'crucif', 'gethsemane', 'sacrifice', 'risen', 'calvary', 'suffering'],
  'salvation':                ['salvation', 'saved', 'redeem', 'deliver', 'cleans', 'justif'],
  'grace':                    ['grace', 'graci', 'unmerited', 'sanctif', 'transform', 'renew'],
  'faith':                    ['faith', 'believ', 'trust'],
  'repentance':               ['repent', 'contrition', 'confess', 'forgive'],
  'prayer':                   ['pray', 'prayer', 'fasting', 'kneel', 'petition', 'intercess'],
  'spirit-guidance':          ['spirit', 'ghost', 'discern', 'conscience', 'whisper', 'prompt', 'compass'],
  'kingdom-now':              ['kingdom', 'abundant', 'reign', 'eternal life'],
  'fellowship-unity':         ['fellowship', 'unity', 'unite', 'denomination', 'division', 'contention', 'brother', 'sister'],
  'discipleship-practice':    ['disciple', 'covenant', 'commit', 'ordinance', 'baptism', 'sacrament', 'obedien'],
  'character-virtue':         ['virtue', 'character', 'honor', 'honour', 'gratitude', 'integrity', 'meek', 'beatitude', 'christlike'],
  'love-service':             ['love', 'charity', 'serve', 'service', 'neighbor', 'neighbour', 'minister', 'compassion'],
  'family':                   ['marri', 'spouse', 'children', 'parent', 'family', 'household'],
  'stewardship':              ['steward', 'tithe', 'offering', 'talent', 'provident', 'health', 'treasure'],
  'trials-endurance':         ['trial', 'endur', 'persever', 'patience', 'affliction', 'tribulation'],
  'immortality-eternal-life': ['immortal', 'resurrect', 'eternal', 'afterlife', 'heaven', 'glory', 'inherit'],
  'assurance':                ['assurance', 'confiden', 'comfort', 'certain', 'hope'],
};

// ---- 3. Concepts to watch specifically (suspected gaps) --------------
// The report prints each one's frequency + whether a theme covers it.
const WATCHLIST = [
  'witness', 'testimony', 'worship', 'worth', 'gather', 'sabbath',
  'agency', 'justice', 'mercy', 'relationship', 'knowing', 'image',
  'light', 'truth', 'peace', 'name', 'gift', 'rest', 'death',
  'temple', 'priesthood', 'restoration', 'gospel', 'heart', 'soul', 'covenant',
];

// ---- 4. Stopwords ----------------------------------------------------
const STOP = new Set(`a about above after again against all am an and any are aren't as at be because been before being below between both but by can cannot could couldn't did didn't do does doesn't doing don't down during each few for from further had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its itself let's me more most mustn't my myself no nor not of off on once only or other ought our ours ourselves out over own same shan't she she'd she'll she's should shouldn't so some such than that that's the their theirs them themselves then there there's these they they'd they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're we've were weren't what what's when when's where where's which while who who's whom why why's with won't would wouldn't you you'd you'll you're you've your yours yourself yourselves
also may might must shall upon thee thou thy thine unto will many thing things make made come came go went see saw say said within without whether neither either among yet still even though although because since whose into onto able really very much well good great new
chapter chapters page pages read reading words plainness article articles section class span div data href https stroke width fill viewbox path http rel noopener target blank button aria label svg true false null lang eng`.split(/\s+/));

// ---- 5. Crawl --------------------------------------------------------
function walk(dir, exts, out) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    if (e.name.startsWith('_')) continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walk(full, exts, out);
    else if (exts.includes(path.extname(e.name))) out.push(full);
  }
}

const files = [];
for (const r of CONTENT_ROOTS) walk(r.dir, r.exts, files);
for (const f of EXPLICIT_FILES) if (fs.existsSync(f)) files.push(f);

function clean(raw) {
  return raw
    .replace(/^\uFEFF?---[\r\n][\s\S]*?[\r\n]---[ \t]*\r?\n?/, ' ') // leading frontmatter
    .replace(/\{[%#][\s\S]*?[%#]\}/g, ' ')   // {% %} and {# #}
    .replace(/\{\{[\s\S]*?\}\}/g, ' ')       // {{ }}
    .replace(/<!--[\s\S]*?-->/g, ' ')        // html comments
    .replace(/<[^>]+>/g, ' ')                // html tags
    .replace(/&[a-z#0-9]+;/gi, ' ')          // entities
    .toLowerCase();
}

let corpus = '';
for (const f of files) { try { corpus += ' ' + clean(fs.readFileSync(f, 'utf8')); } catch {} }

// music titles / descriptions / lyrics
try {
  const m = JSON.parse(fs.readFileSync(MUSIC_JSON, 'utf8'));
  const grab = (arr) => (arr || []).forEach(x => {
    corpus += ' ' + [x.title, x.description, x.label].filter(Boolean).join(' ').toLowerCase();
    if (x.lyrics) corpus += ' ' + clean(x.lyrics);
  });
  grab(m.collection); grab(m.ambient);
  if (m.anthemLyrics) corpus += ' ' + clean(m.anthemLyrics);
} catch {}

// ---- 6. Tokenize + count --------------------------------------------
const tokens = corpus.split(/[^a-z']+/).filter(w => w.length >= 4 && !STOP.has(w));
const uni = new Map();
for (const w of tokens) uni.set(w, (uni.get(w) || 0) + 1);
const big = new Map();
for (let i = 0; i < tokens.length - 1; i++) {
  const b = tokens[i] + ' ' + tokens[i + 1];
  big.set(b, (big.get(b) || 0) + 1);
}

// ---- 7. Coverage -----------------------------------------------------
const cueEntries = Object.entries(THEMES);
const themesFor = (term) => cueEntries.filter(([, cues]) => cues.some(c => term.includes(c))).map(([s]) => s);

const themeHits = Object.fromEntries(Object.keys(THEMES).map(s => [s, 0]));
let coveredInst = 0, totalInst = 0;
const uncovered = [];
for (const [w, n] of uni) {
  totalInst += n;
  const th = themesFor(w);
  if (th.length) { coveredInst += n; th.forEach(s => themeHits[s] += n); }
  else uncovered.push([w, n]);
}
uncovered.sort((a, b) => b[1] - a[1]);
const uncoveredBig = [...big.entries()].filter(([b]) => themesFor(b).length === 0).sort((a, b) => b[1] - a[1]);

// ---- 8. Report -------------------------------------------------------
const col = (arr, n) => arr.slice(0, n).map(([w, c]) => `  ${String(c).padStart(5)}  ${w}`).join('\n');
const pct = totalInst ? ((coveredInst / totalInst) * 100).toFixed(1) : '0.0';

const themeTable = Object.entries(themeHits).sort((a, b) => a[1] - b[1])
  .map(([s, n]) => `  ${String(n).padStart(6)}  ${s}`).join('\n');

const watch = WATCHLIST.map(w => {
  const c = uni.get(w) || 0;
  const th = themesFor(w);
  return `  ${String(c).padStart(5)}  ${w.padEnd(13)} ${th.length ? '-> ' + th.join(', ') : 'X  NOT COVERED'}`;
}).join('\n');

const report = `# Theme Coverage Audit — Words of Plainness

Files scanned: ${files.length}   Filtered tokens: ${totalInst}   Coverage: ${pct}%

## Theme attestation (lowest first)
A near-zero count means the theme is barely present in DEPLOYED text — which may
mean it is miscalibrated, OR simply that its chapters are not written yet
(many Movement 3 / Volume 2 chapters are still placeholders). Judge accordingly.

${themeTable}

## Watchlist — concepts that might deserve their own theme
${watch}

## Top 50 UNCOVERED single words (candidate gaps)
${col(uncovered, 50)}

## Top 30 UNCOVERED two-word phrases (candidate gaps)
${col(uncoveredBig, 30)}

---
Method: word frequency only. It surfaces candidates; it does not judge importance.
Scan the uncovered lists + watchlist for any concept that recurs but has no theme,
then prune or extend the vocabulary before locking it.
`;

fs.writeFileSync(path.join(HERE, 'theme-coverage-report.md'), report, 'utf8');
console.log(report);
console.log(`Report written to tools/theme-coverage-report.md`);
