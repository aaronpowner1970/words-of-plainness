// Section 5.2 (4) Audio: line timings within 0.05 s, highlight in Read and in the panel, pause holds
// it, the end clears it, each line clip highlights its line; media byte-identical (SHA-256).
//
// WebKit on Windows (Playwright build) cannot decode MP3 or MP4: media stay at readyState 0 and a
// Blob copy of the reading fails with MEDIA_ERR_SRC_NOT_SUPPORTED. The page's own play/seek calls
// still run, so seek time, highlight-on-play and pause-holds are checked in WebKit; anything that
// needs real playback (the recording or a clip reaching its end) is checked in Chromium only and
// recorded as not runnable in WebKit.
import fs from 'node:fs';
import path from 'node:path';
import { scenario, expect } from '../lib/harness.mjs';
import { getConfig } from '../lib/config.mjs';
import { hashBuffer } from '../lib/media.mjs';

const STARTS = [5.18, 11.32, 17.98, 24.64, 31.38, 37.67, 46.06, 55.05, 62.38, 71.28];
const NOPLAY = 'WebKit on Windows cannot decode the MP3 (readyState 0; MEDIA_ERR_SRC_NOT_SUPPORTED), so playback never reaches its end here; checked in Chromium.';

async function mediaCount(d) { return d.page.evaluate(() => window.__parity.media.length); }
async function mediaSince(d, n) { return d.page.evaluate(k => window.__parity.media.slice(k), n); }
async function waitHighlight(d, sel, i, timeout = 4000) {
  return d.page.waitForFunction(([s, k]) => { const l = document.querySelectorAll(s); return l[k] && l[k].classList.contains('tl-spoken-line'); }, [sel, i], { timeout }).then(() => true, () => false);
}
async function playable(d) { return d.page.evaluate(() => { const a = document.getElementById('readingAudio'); return a.readyState > 0 || !Number.isNaN(a.duration); }); }

async function seekOf(d, before, el) {
  const ev = await mediaSince(d, before);
  const seek = ev.filter(e => e.el === el && e.ev === 'seeking').pop() || ev.filter(e => e.el === el && e.ev === 'play').pop();
  return seek ? seek.t : null;
}

scenario('audio', 'A01-read-lines', { b: ['B10', 'B11', 'B12', 'B13'], timeout: 180000 }, async (d, { browserName }) => {
  await d.open();
  const r0 = await d.step('read-aloud', ['B10'], async () => { await d.click('#readAloud'); await d.page.waitForTimeout(600); });
  d.check('B10', r0.audio.label === 'Pause reading', '"Read poem aloud" plays the full recording', r0.audio.label);
  const p0 = await d.step('read-aloud-pause', ['B10', 'B13'], () => d.click('#readAloud'));
  if (await playable(d)) d.check('B13', p0.audio.label === 'Resume reading', 'pause and resume only', p0.audio.label);
  else d.na('B13', 'pause then "Resume reading"', NOPLAY + ' The label returns to "Read poem aloud" because currentTime never left 0.');
  for (let i = 0; i < 10; i++) {
    const before = await mediaCount(d);
    await d.page.locator('#plainPoem p').nth(i).click();
    const lit = await waitHighlight(d, '#plainPoem p', i);
    const t = await seekOf(d, before, 'readingAudio');
    d.record(`seek-line-${i + 1}`, t);
    const s = await d.snap(`line-${i + 1}-playing`, ['B11', 'B12']);
    d.check('B11', t !== null && Math.abs(t - STARTS[i]) <= 0.05, `line ${i + 1}: playback starts within 0.05 s of ${STARTS[i]}`, t);
    d.check('B12', lit && s.audio.spokenRead === String(i) && s.audio.spokenPanel === String(i), `line ${i + 1}: highlighted in Read and in the panel`, s.audio);
    await d.click('#readAloud');
    await d.page.waitForTimeout(400);
    const p = await d.snap(`line-${i + 1}-paused`, ['B12', 'B13']);
    d.check('B12', p.audio.spokenRead === String(i) && p.audio.label === 'Resume reading', `line ${i + 1}: pause holds the highlight`, p.audio);
  }
  // The end clears it: play line 10 to the end of the recording.
  if (browserName === 'chromium' && await playable(d)) {
    await d.page.locator('#plainPoem p').nth(9).click();
    const ended = await d.page.waitForFunction(() => window.__parity.media.some(e => e.el === 'readingAudio' && e.ev === 'ended'), null, { timeout: 30000 }).then(() => true, () => false);
    await d.settle(150);
    const e = await d.snap('recording-ended', ['B12']);
    d.check('B12', ended && e.audio.spokenRead === '' && e.audio.spokenPanel === '' && e.audio.label === 'Read poem aloud again', 'the highlight clears when the recording ends', e.audio);
  } else d.na('B12', 'the highlight clears when the recording ends', NOPLAY);
});

scenario('audio', 'A02-panel-lines', { b: ['B11', 'B12', 'B56'], timeout: 180000 }, async d => {
  await d.open();
  await d.click('#lessonStart'); await d.settle();
  await d.click('#lessonNext'); await d.settle(300);
  await d.select('#contextLineAction', 'listen');
  for (let i = 0; i < 10; i++) {
    const before = await mediaCount(d);
    await d.page.locator('#contextText button').nth(i).click();
    const lit = await waitHighlight(d, '#contextText button', i);
    const t = await seekOf(d, before, 'readingAudio');
    d.record(`panel-seek-line-${i + 1}`, t);
    const s = await d.snap(`panel-line-${i + 1}`, ['B11', 'B12', 'B56']);
    d.check('B11', t !== null && Math.abs(t - STARTS[i]) <= 0.05, `panel line ${i + 1}: Play from line starts within 0.05 s`, t);
    d.check('B12', lit && s.audio.spokenPanel === String(i) && s.audio.spokenRead === String(i), `panel line ${i + 1}: highlighted in the panel and in Read`, s.audio);
    d.check('B56', s.lesson && s.lesson.menu === '1', `panel line ${i + 1}: listening keeps the current discussion (Line 1) open`, s.lesson && s.lesson.menu);
    await d.click('#contextReadAloud');
    await d.page.waitForTimeout(300);
    const p = await d.snap(`panel-line-${i + 1}-paused`, ['B12']);
    d.check('B12', p.audio.spokenPanel === String(i), `panel line ${i + 1}: pause holds the highlight`, p.audio);
  }
});

scenario('audio', 'A03-line-clips', { b: ['B54', 'B12'], timeout: 240000 }, async (d, { browserName }) => {
  await d.open();
  await d.click('#lessonStart'); await d.settle();
  const real = browserName === 'chromium';
  for (let i = 1; i <= 10; i++) {
    await d.select('#lessonMenu', String(i)); await d.settle();
    await d.page.locator('#lessonBody button', { hasText: 'Listen to this line' }).click();
    const lit = await waitHighlight(d, '#plainPoem p', i - 1);
    const s = await d.snap(`clip-${i}-playing`, ['B54']);
    d.check('B54', lit && s.audio.spokenRead === String(i - 1) && s.audio.spokenPanel === String(i - 1) && s.lesson.body.includes('Stop line reading'), `line ${i}: its own clip plays and highlights the line`, s.audio);
    if (real) {
      const ended = await d.page.waitForFunction(() => window.__parity.media.filter(e => e.el === 'studyAudio' && e.ev === 'ended').length > 0 && document.querySelector('#lessonBody button') && !document.querySelector('#plainPoem p.tl-spoken-line'), null, { timeout: 20000 }).then(() => true, () => false);
      await d.page.evaluate(() => { window.__parity.media = window.__parity.media.filter(e => !(e.el === 'studyAudio' && e.ev === 'ended')); });
      const e = await d.snap(`clip-${i}-ended`, ['B54', 'B12']);
      d.check('B12', ended && e.audio.spokenRead === '' && e.lesson.body.includes('Listen to this line'), `line ${i}: highlight clears when the clip ends`, e.audio);
    } else {
      await d.page.locator('#lessonBody button', { hasText: 'Stop line reading' }).click();
      await d.settle();
      await d.snap(`clip-${i}-stopped`, ['B54']);
      if (i === 1) d.na('B12', 'line clip: highlight clears when the clip ends', NOPLAY);
    }
  }
});

// Media: every file the page plays, hashed, against the hashes extracted from v1.88.
scenario('audio', 'A04-media-hashes', { b: ['B10', 'B40', 'B54'], timeout: 180000 }, async (d, { side }) => {
  const cfg = getConfig();
  const manifest = JSON.parse(fs.readFileSync(path.join(cfg.mediaDir, 'media-hashes.json'), 'utf8'));
  const want = Object.fromEntries(manifest.items.map(i => [i.role, i.sha256]));
  await d.open();
  const bytesOf = async src => {
    if (!src) return null;
    if (src.startsWith('data:')) return Buffer.from(src.slice(src.indexOf(',') + 1), 'base64');
    if (src.startsWith('file:')) return fs.readFileSync(new URL(src));
    const r = await d.context.request.get(src);
    return Buffer.from(await r.body());
  };
  const short = src => (src ? (src.startsWith('data:') ? src.slice(0, src.indexOf(',')) + ',…(' + src.length + ' chars)' : src) : null);
  const media = {};
  const add = async (role, src) => { const b = await bytesOf(src); media[role] = { src: short(src), bytes: b ? b.length : null, sha256: b ? hashBuffer(b) : null }; };
  await add('reading', await d.page.$eval('#readingAudio', a => a.currentSrc || a.src));
  await add('film', await d.page.$eval('#cubeFilm video', v => v.currentSrc || v.src || (v.querySelector('source') || {}).src));
  const logo = await d.page.$('img.tl-logo');
  if (logo) await add('logo', await logo.evaluate(i => i.src));
  await d.click('#lessonStart'); await d.settle();
  for (let i = 1; i <= 10; i++) {
    await d.select('#lessonMenu', String(i)); await d.settle(60);
    await add('clip' + String(i).padStart(2, '0'), await d.page.$eval('#studyAudio', a => a.currentSrc || a.src));
  }
  d.record('media', media);
  for (const [role, m] of Object.entries(media)) {
    d.check(role === 'film' ? 'B40' : role === 'reading' ? 'B10' : role === 'logo' ? 'B5' : 'B54', m.sha256 === want[role], `${role}: SHA-256 matches the media extracted from v1.88`, m.sha256);
  }
  if (side === 'candidate' && !cfg.selfParity) {
    for (const role of Object.keys(want).filter(r => r !== 'logo')) expect(media[role] && media[role].sha256, `${role} must be byte-identical to v1.88 (D3)`).toBe(want[role]);
  }
});
