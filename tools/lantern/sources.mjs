#!/usr/bin/env node
// The Lantern Post source gate. See tools/lantern/README.md.
//   node tools/lantern/sources.mjs build
//   node tools/lantern/sources.mjs manifest
//   node tools/lantern/sources.mjs check [file]      (stdin when no file)
// Published = listed in the sitemap of the production-equivalent build,
// minus Coming Soon stubs and URLs vercel.json redirects.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const SITE_DIR = path.join(ROOT, '.lantern', 'site');
export const MANIFEST_PATH = path.join(ROOT, '.lantern', 'manifest.json');
const BUILD_LOG = path.join(ROOT, '.lantern', 'build.log');
const ORIGIN = 'https://www.wordsofplainness.org';
const STUB_REMAINDER_WORDS = 60; // a page is a stub when, minus the notice, fewer words than this remain

// Production-equivalent build settings (evidence in the Phase 1 report):
// vercel.json runs `npm run build`; Vercel sets VERCEL_ENV=production; the
// Second Edition switch (src/_data/aoidSecondEdition.js) is unset in production.
const BUILD_ENV = { VERCEL_ENV: 'production' };
const UNSET_ENV = ['WOP_AOID2_SECOND_EDITION', 'LYRICS_STRICT'];

// ---- Focused-mode categories: ordered rules, first match wins, else Other pages.
export const CATEGORIES = [
  'Volume 1', 'Volume 2', 'Appendices', 'Music', 'Videos',
  'Narrations and Podcasts', 'Discipleship Apps', 'Articles of Interfaith Discipleship', 'Other pages',
];
export const CATEGORY_RULES = [
  { category: 'Videos', test: (p) => p === '/creation/' || p.startsWith('/articles/video-') },
  { category: 'Articles of Interfaith Discipleship', test: (p) => p === '/articles/' },
  { category: 'Volume 1', test: (p) => p === '/volume-1/' || p.startsWith('/chapters/') },
  { category: 'Volume 2', test: (p) => p.startsWith('/volume-2/') },
  // /writings/ lists the appendices: every /studies/ page, plus the Seeking Jesus hub
  // (its tool pages stay under Discipleship Apps).
  { category: 'Appendices', test: (p) => p.startsWith('/studies/') || p === '/seeking-jesus/' },
  { category: 'Music', test: (p) => p === '/music/' || p.startsWith('/concert/') },
  { category: 'Narrations and Podcasts', test: (p) => p === '/narrations/' },
  { category: 'Discipleship Apps', test: (p) => p === '/discipleship/' || p.startsWith('/seeking-jesus/') },
];
export function categorize(p) {
  const r = CATEGORY_RULES.find((x) => x.test(p));
  return r ? r.category : 'Other pages';
}

// ---- URL normalization. Returns a canonical site path, or null if not a site URL.
export function normalizeUrl(raw) {
  let s = String(raw).trim();
  if (!s) return null;
  if (/^\/\//.test(s)) s = 'https:' + s;
  let p;
  if (/^https?:\/\//i.test(s)) {
    let u;
    try { u = new URL(s); } catch { return null; }
    const h = u.hostname.toLowerCase();
    if (h !== 'wordsofplainness.org' && h !== 'www.wordsofplainness.org') return null;
    p = u.pathname;
  } else if (s.startsWith('/')) {
    p = s.split('#')[0].split('?')[0];
  } else return null;
  try { p = decodeURI(p); } catch { /* keep as is */ }
  p = p.replace(/\/{2,}/g, '/');
  if (!p.startsWith('/')) p = '/' + p;
  if (p.endsWith('/index.html')) p = p.slice(0, -'index.html'.length);
  if (!p.endsWith('/') && !/\.[A-Za-z0-9]+$/.test(p.split('/').pop())) p += '/';
  return p;
}

// ---- HTML helpers (no dependencies)
const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—', ndash: '–', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“', hellip: '…', dagger: '†', Dagger: '‡', para: '¶', rarr: '→', middot: '·', sect: '§' };
export function decode(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === '#') {
      const n = e[1].toLowerCase() === 'x' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      try { return String.fromCodePoint(n); } catch { return m; }
    }
    return Object.prototype.hasOwnProperty.call(ENT, e) ? ENT[e] : m;
  });
}
export function htmlToText(html) {
  let h = html.replace(/<!--[\s\S]*?-->/g, '');
  h = h.replace(/<(script|style|noscript|nav|footer|svg|template|button)\b[\s\S]*?<\/\1>/gi, ' ');
  h = h.replace(/<\/(p|div|h[1-6]|li|tr|section|article|header|blockquote|ul|ol|table)>|<br\s*\/?>/gi, '\n');
  h = h.replace(/<[^>]+>/g, ' ');
  h = decode(h).replace(/ /g, ' ');
  return h.split('\n').map((l) => l.replace(/[ \t]+/g, ' ').trim()).filter(Boolean).join('\n');
}
export function contentRegion(html, narrow = true) {
  const mStart = html.search(/<main\b/i);
  const mEnd = html.lastIndexOf('</main>');
  let region = mStart >= 0 && mEnd > mStart ? html.slice(mStart, mEnd) : html;
  if (!narrow) return region;
  const aStart = region.search(/<article\b/i);
  const aEnd = region.lastIndexOf('</article>');
  if (aStart >= 0 && aEnd > aStart) region = region.slice(aStart, aEnd);
  return region;
}
export function pageTitle(html) {
  const m = html.match(/<title>([\s\S]*?)<\/title>/i);
  const t = m ? decode(m[1]).replace(/\s+/g, ' ').trim() : '';
  return t.replace(/\s*[|–—-]\s*Words of Plainness\s*$/i, '') || t;
}
const NOTICE_RE = /<div\b[^>]*class="[^"]*\bcoming-soon-notice\b[^"]*"[^>]*>[\s\S]*?<\/div>/i;
export function isComingSoonStub(region) {
  if (!NOTICE_RE.test(region)) return false;
  const rest = htmlToText(region.replace(NOTICE_RE, ' '));
  return rest.split(/\s+/).filter(Boolean).length < STUB_REMAINDER_WORDS;
}
export function hasMetaRefresh(html) {
  return /<meta[^>]+http-equiv=["']?refresh/i.test(html);
}

// ---- Media found inside the content region of a page
const attr = (tag, name) => { const m = tag.match(new RegExp('\\s' + name + '="([^"]*)"', 'i')); return m ? decode(m[1]) : ''; };
function mediaKind(file) {
  const f = file.split('/').pop();
  if (/^POD_|^PO_/.test(f)) return 'podcast';
  if (/^NR_|^SW_/.test(f)) return 'narration';
  return 'music';
}
const stem = (f) => decodeURIComponent(f.split('/').pop()).replace(/\.[a-z0-9]+$/i, '').replace(/_/g, ' ');
export function extractMedia(region, pageUrl) {
  const out = []; const seen = new Set();
  const add = (kind, title, src, titleFrom) => {
    const key = kind + '|' + src; if (seen.has(key)) return; seen.add(key);
    out.push({ kind, title: title || stem(src), titleFrom: title ? titleFrom : 'filename', src, page: pageUrl });
  };
  // music arrangements: <tr class="playlist-row" data-play-file="...">
  for (const m of region.matchAll(/<tr\b[^>]*data-play-file="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/gi)) {
    const t = (m[2].match(/class="song-title">([\s\S]*?)<\/span>/i) || [])[1];
    const l = (m[2].match(/class="song-label">([\s\S]*?)<\/span>/i) || [])[1];
    const title = t ? decode((t + ' ' + (l || '').replace(/&mdash;|—/g, '').trim()).replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim() : '';
    add('music', title, m[1], 'playlist row');
  }
  // narrations and podcasts: elements with data-src (+ data-title)
  for (const m of region.matchAll(/<[a-z]+\b[^>]*\sdata-src="([^"]+\.(?:mp3|m4a))"[^>]*>/gi)) {
    add(mediaKind(m[1]), attr(m[0], 'data-title'), m[1], 'data-title');
  }
  // plain <source src=...> audio/video inside the content
  for (const m of region.matchAll(/<source\b[^>]*\ssrc="([^"]+\.(?:mp3|m4a|mp4))"[^>]*>/gi)) {
    add(/\.mp4$/i.test(m[1]) ? 'video' : mediaKind(m[1]), '', m[1], '');
  }
  // videos: YouTube buttons and embeds
  for (const m of region.matchAll(/<[a-z]+\b[^>]*\sdata-youtube-id="([^"]+)"[^>]*>/gi)) {
    add('video', attr(m[0], 'data-video-title'), 'https://www.youtube.com/watch?v=' + m[1], 'data-video-title');
  }
  for (const m of region.matchAll(/<iframe\b[^>]*\ssrc="https?:\/\/www\.youtube(?:-nocookie)?\.com\/embed\/([\w-]+)[^"]*"[^>]*>/gi)) {
    add('video', attr(m[0], 'title'), 'https://www.youtube.com/watch?v=' + m[1], 'iframe title');
  }
  return out;
}

// ---- vercel.json redirects (source paths, normalized)
export function redirectSources(root = ROOT) {
  const f = path.join(root, 'vercel.json');
  if (!fs.existsSync(f)) return new Map();
  const j = JSON.parse(fs.readFileSync(f, 'utf8'));
  const m = new Map();
  for (const r of j.redirects || []) {
    if (typeof r.source === 'string' && !/[:*()]/.test(r.source)) m.set(normalizeUrl(r.source), r.destination);
  }
  return m;
}

// ---- build
function build() {
  fs.rmSync(SITE_DIR, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(BUILD_LOG), { recursive: true });
  const env = { ...process.env, ...BUILD_ENV };
  for (const k of UNSET_ENV) delete env[k];
  // Same read-only data check production runs as part of `prebuild`.
  const v = spawnSync(process.execPath, ['scripts/sjn-verify-data.js'], { cwd: ROOT, env, encoding: 'utf8' });
  if (v.status !== 0) { process.stderr.write((v.stdout || '') + (v.stderr || '')); console.error('sjn-verify-data failed; production would fail too.'); process.exit(1); }
  const out = path.relative(ROOT, SITE_DIR).replace(/\\/g, '/');
  const r = spawnSync('npx', ['--no-install', '@11ty/eleventy', '--output=' + out], { cwd: ROOT, env, encoding: 'utf8', shell: true, maxBuffer: 1 << 28 });
  fs.writeFileSync(BUILD_LOG, (r.stdout || '') + (r.stderr || ''));
  if (r.status !== 0) { console.error('eleventy build failed; see ' + BUILD_LOG); process.exit(1); }
  console.log('built to ' + out + ' (VERCEL_ENV=production, Second Edition switch unset)');
}

// ---- manifest
function inputMap() {
  const m = new Map();
  if (!fs.existsSync(BUILD_LOG)) return m;
  for (const line of fs.readFileSync(BUILD_LOG, 'utf8').split(/\r?\n/)) {
    const x = line.match(/Writing (\S+) from (\S+)/);
    if (x) m.set(path.posix.normalize(x[1].replace(/\\/g, '/')), x[2].replace(/^\.\//, ''));
  }
  return m;
}
export function sitemapPaths(siteDir = SITE_DIR) {
  const xml = fs.readFileSync(path.join(siteDir, 'sitemap.xml'), 'utf8');
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => normalizeUrl(decode(m[1]))).filter(Boolean);
}
export function buildManifest(siteDir = SITE_DIR) {
  const rel = path.relative(ROOT, siteDir).replace(/\\/g, '/');
  const inputs = inputMap();
  const redirects = redirectSources();
  const pages = []; const excluded = []; const media = [];
  for (const p of sitemapPaths(siteDir)) {
    const file = path.join(siteDir, p.endsWith('/') ? p + 'index.html' : p);
    if (!fs.existsSync(file)) { excluded.push({ url: ORIGIN + p, reason: 'sitemap entry has no built file' }); continue; }
    const html = fs.readFileSync(file, 'utf8');
    if (redirects.has(p)) { excluded.push({ url: ORIGIN + p, reason: 'redirected in vercel.json to ' + redirects.get(p) }); continue; }
    if (hasMetaRefresh(html)) { excluded.push({ url: ORIGIN + p, reason: 'meta-refresh redirect page' }); continue; }
    const region = contentRegion(html);
    if (isComingSoonStub(region)) { excluded.push({ url: ORIGIN + p, reason: 'Coming Soon stub' }); continue; }
    const text = htmlToText(region);
    const url = ORIGIN + p;
    pages.push({
      url, path: p, title: pageTitle(html), category: categorize(p), text,
      wordCount: text.split(/\s+/).filter(Boolean).length,
      sourceInput: inputs.get(rel + (p.endsWith('/') ? p + 'index.html' : p)) || null,
    });
    media.push(...extractMedia(contentRegion(html, false), url));
  }
  return { generated: new Date().toISOString(), siteDir: rel, sitemapCount: pages.length + excluded.length, pages, excluded, media };
}
function manifest() {
  if (!fs.existsSync(path.join(SITE_DIR, 'sitemap.xml'))) { console.error('No built site. Run: node tools/lantern/sources.mjs build'); process.exit(1); }
  const m = buildManifest();
  fs.mkdirSync(path.dirname(MANIFEST_PATH), { recursive: true });
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(m, null, 1));
  const counts = {}; for (const c of CATEGORIES) counts[c] = 0; for (const p of m.pages) counts[p.category]++;
  console.log(`manifest: ${m.pages.length} published of ${m.sitemapCount} sitemap URLs; ${m.excluded.length} excluded; ${m.media.length} media`);
  for (const [c, n] of Object.entries(counts)) console.log(`  ${c}: ${n}`);
  console.log('  written ' + path.relative(ROOT, MANIFEST_PATH));
}

// ---- check
export function extractLinks(text) {
  const found = new Set();
  for (const m of text.matchAll(/https?:\/\/(?:www\.)?wordsofplainness\.org(?![\w.-])[^\s<>"'`\])]*/gi)) found.add(m[0]);
  for (const m of text.matchAll(/(?:^|[\s(["'=<])(\/(?!\/)[A-Za-z0-9][^\s<>"'`\])]*)/g)) found.add(m[1]);
  return [...found].map((s) => s.replace(/[.,;:!?]+$/, ''));
}
export function checkText(text, mf) {
  const ok = new Set(mf.pages.map((p) => p.path));
  const why = new Map(mf.excluded.map((e) => [normalizeUrl(e.url), e.reason]));
  const bad = [];
  for (const raw of extractLinks(text)) {
    const n = normalizeUrl(raw);
    if (n && !ok.has(n)) bad.push({ link: raw, normalized: n, reason: why.get(n) || 'not in the manifest of published pages' });
  }
  return bad;
}
function check(file) {
  if (!fs.existsSync(MANIFEST_PATH)) { console.error('No manifest. Run build, then manifest.'); process.exit(2); }
  const mf = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  const text = file ? fs.readFileSync(file, 'utf8') : fs.readFileSync(0, 'utf8');
  const bad = checkText(text, mf);
  if (bad.length) {
    console.error('REFUSED: ' + bad.length + ' link(s) not published:');
    for (const b of bad) console.error(`  ${b.link}  ->  ${b.normalized}  (${b.reason})`);
    process.exit(1);
  }
  console.log('OK: every site link is in the manifest.');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [cmd, arg] = process.argv.slice(2);
  if (cmd === 'build') build();
  else if (cmd === 'manifest') manifest();
  else if (cmd === 'check') check(arg);
  else { console.error('usage: sources.mjs build | manifest | check [file]'); process.exit(2); }
}
