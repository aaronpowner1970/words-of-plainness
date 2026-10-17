import test, { before } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { normalizeUrl, sitemapPaths, checkText, categorize, isComingSoonStub, SITE_DIR, MANIFEST_PATH } from '../sources.mjs';

const TOOL = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'sources.mjs');
let mf;

before(() => {
  // Use the existing build when present; otherwise build, as a cloud session would.
  if (!fs.existsSync(path.join(SITE_DIR, 'sitemap.xml'))) {
    assert.equal(spawnSync(process.execPath, [TOOL, 'build'], { stdio: 'inherit' }).status, 0, 'build');
  }
  assert.equal(spawnSync(process.execPath, [TOOL, 'manifest'], { stdio: 'ignore' }).status, 0, 'manifest');
  mf = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
});

test('manifest plus recorded exclusions are exactly the sitemap URL set', () => {
  const sitemap = new Set(sitemapPaths().map((p) => 'https://www.wordsofplainness.org' + p));
  const pages = new Set(mf.pages.map((p) => p.url));
  const excl = new Set(mf.excluded.map((e) => e.url));
  assert.equal(pages.size, mf.pages.length, 'no duplicate manifest URLs');
  for (const u of pages) assert.ok(!excl.has(u), 'a URL is both published and excluded: ' + u);
  assert.deepEqual([...new Set([...pages, ...excl])].sort(), [...sitemap].sort());
  assert.equal(mf.sitemapCount, sitemap.size);
});

test('every manifest URL is in the sitemap and no stub or redirect is published', () => {
  const sitemap = new Set(sitemapPaths());
  for (const p of mf.pages) assert.ok(sitemap.has(p.path), p.path);
  for (const p of mf.pages) assert.ok(!p.path.startsWith('/volume-2/chapters/'), 'Volume 2 stub published: ' + p.path);
  assert.ok(!mf.pages.some((p) => p.path === '/chapters/09-christs-personal-character/'));
  // Since 17 Oct 2026 the sitemap itself omits these (eleventyExcludeFromCollections); the filters are a backstop.
  assert.deepEqual(mf.excluded, [], 'unexpected stub or redirect in the sitemap: ' + JSON.stringify(mf.excluded));
  assert.ok(mf.pages.some((p) => p.path === '/concert/'), 'a real page that merely mentions Coming Soon stays published');
});

test('a Coming Soon stub is absent from the sitemap and a draft linking it is refused', () => {
  assert.ok(!sitemapPaths().includes('/chapters/searching-the-scriptures/'), 'published-only rule would be broken at the source');
  const draft = 'Read more: https://www.wordsofplainness.org/chapters/searching-the-scriptures/ today.';
  const bad = checkText(draft, mf);
  assert.equal(bad.length, 1);
  assert.equal(bad[0].normalized, '/chapters/searching-the-scriptures/');
  // and through the command line, as a session would run it
  const r = spawnSync(process.execPath, [TOOL, 'check'], { input: draft, encoding: 'utf8' });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /searching-the-scriptures/);
});

test('stub and redirect URLs are refused', () => {
  const bad = checkText('/volume-2/chapters/v2-01-review-of-restoration/ and /chapters/09-christs-personal-character/', mf);
  assert.equal(bad.length, 2);
  // the backstop still names the reason when a URL is in the sitemap but excluded
  const withReasons = { pages: mf.pages, excluded: [{ url: 'https://www.wordsofplainness.org/x-stub/', reason: 'Coming Soon stub' }] };
  assert.equal(checkText('/x-stub/', withReasons)[0].reason, 'Coming Soon stub');
});

test('a draft linking a real published chapter passes', () => {
  const draft = 'See https://www.wordsofplainness.org/chapters/01-introduction/#top and [Music](/music/?x=1) and wordsofplainness.org is fine.';
  assert.deepEqual(checkText(draft, mf), []);
  const r = spawnSync(process.execPath, [TOOL, 'check'], { input: draft, encoding: 'utf8' });
  assert.equal(r.status, 0);
});

test('links to other hosts are ignored by check', () => {
  assert.deepEqual(checkText('https://commandments.brotheraaron.org/ and https://media.wordsofplainness.org/web/x.mp3', mf), []);
});

test('normalizeUrl cases', () => {
  const same = '/chapters/01-introduction/';
  for (const v of [
    'https://www.wordsofplainness.org/chapters/01-introduction/',
    'https://www.wordsofplainness.org/chapters/01-introduction',
    'https://wordsofplainness.org/chapters/01-introduction/',
    'HTTP://WWW.WordsOfPlainness.org/chapters/01-introduction/?utm=1#x',
    '/chapters/01-introduction',
    '/chapters/01-introduction/#sec',
    '/chapters/01-introduction?a=b',
    '//www.wordsofplainness.org/chapters/01-introduction/',
    '/chapters//01-introduction/',
    '/chapters/01-introduction/index.html',
  ]) assert.equal(normalizeUrl(v), same, v);
  assert.equal(normalizeUrl('https://www.wordsofplainness.org'), '/');
  assert.equal(normalizeUrl('https://www.wordsofplainness.org/#top'), '/');
  assert.equal(normalizeUrl('/sitemap.xml'), '/sitemap.xml');
  assert.equal(normalizeUrl('https://example.com/chapters/01-introduction/'), null);
  assert.equal(normalizeUrl('https://media.wordsofplainness.org/x/'), null);
  assert.equal(normalizeUrl('mailto:a@b.c'), null);
  assert.equal(normalizeUrl(''), null);
});

test('stub detection and category rules', () => {
  const notice = '<div class="coming-soon-notice"><h2>Coming Soon</h2><p>x</p></div>';
  assert.equal(isComingSoonStub(notice), true);
  assert.equal(isComingSoonStub('<p>' + 'word '.repeat(100) + '</p>' + notice), false);
  assert.equal(isComingSoonStub('<div class="concert-card concert-card--coming-soon">Coming Soon</div>'), false);
  assert.equal(categorize('/chapters/01-introduction/'), 'Volume 1');
  assert.equal(categorize('/volume-2/'), 'Volume 2');
  assert.equal(categorize('/seeking-jesus/map/'), 'Discipleship Apps');
  assert.equal(categorize('/articles/'), 'Articles of Interfaith Discipleship');
  assert.equal(categorize('/studies/broken-vessels/'), 'Appendices');
  assert.equal(categorize('/seeking-jesus/'), 'Appendices');
});

test('every appendix entry listed on /writings/ is categorized Appendices', () => {
  const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
  const src = fs.readFileSync(path.join(root, 'src', 'pages', 'writings.njk'), 'utf8');
  const entries = [...src.matchAll(/<a\s+href="([^"]+)"\s+class="appendix-entry"/g)].map((m) => m[1]);
  assert.ok(entries.length > 0, 'found appendix entries on /writings/');
  const published = new Map(mf.pages.map((p) => [p.path, p.category]));
  for (const e of entries) {
    assert.ok(published.has(e), 'appendix entry is a published page: ' + e);
    assert.equal(published.get(e), 'Appendices', e);
  }
});
