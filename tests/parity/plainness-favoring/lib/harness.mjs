// Scenario runner: every scenario runs on the reference and (when set) the candidate, each in a
// fresh browser context (a fresh profile), with the same seed, the same fixed clock and the same
// instrumentation. Observations are written as JSON outside git; with a candidate, the two sides
// are compared through the planned-differences map and any unexplained difference fails the test.
import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';
import { getConfig, ensureDir, writeJson } from './config.mjs';
import { initScript, snapshotInPage, inventoryInPage, storageInPage } from './page-scripts.mjs';
import { compareLeaves, flatten, classifyRequests, loadDmap } from './dmap.mjs';

export const DESKTOP = { width: 1440, height: 900 };

function safe(name) { return String(name).replace(/[^\w.-]+/g, '_'); }

export class Driver {
  constructor({ page, context, side, url, browserName, dir, cfg }) {
    Object.assign(this, { page, context, side, url, browserName, dir, cfg });
    this.steps = [];
    this.checks = [];
    this.artifacts = {};
    this.console = [];
    this.pageErrors = [];
    this.requests = [];
    this.dialogs = [];
    this.phase = 'load';
    this.labels = new Set();
    page.on('console', m => { if (['error', 'warning'].includes(m.type())) this.console.push({ type: m.type(), text: m.text().slice(0, 500), phase: this.phase }); });
    page.on('pageerror', e => this.pageErrors.push({ message: String(e.message).slice(0, 500), phase: this.phase }));
    page.on('request', r => this.requests.push({ url: r.url().replace(/^blob:[^/]*\/[\w-]+$/, 'blob:<uuid>').slice(0, 300), resourceType: r.resourceType(), method: r.method(), phase: this.phase }));
    // Any main-frame navigation (a reload from Start over, say) is a page load, not a reader action.
    page.on('framenavigated', f => { if (f === page.mainFrame()) this.phase = 'load'; });
    page.on('dialog', async d => { this.dialogs.push({ type: d.type(), message: d.message(), phase: this.phase }); await d.accept(); });
  }

  async open() {
    this.phase = 'load';
    await this.page.goto(this.url, { waitUntil: 'load' });
    await this.page.waitForSelector('#tool-root[data-ready="true"]', { state: 'attached', timeout: 30000 });
    await this.settle(400);
  }

  async reload() {
    this.phase = 'load';
    await this.page.reload({ waitUntil: 'load' });
    await this.page.waitForSelector('#tool-root[data-ready="true"]', { state: 'attached', timeout: 30000 });
    await this.settle(400);
  }

  async settle(ms = 120) {
    await this.page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
    await this.page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))).catch(() => {});
    if (ms) await this.page.waitForTimeout(ms);
  }

  // Run one reader action, then take a state snapshot.
  async step(label, b, fn, opts = {}) {
    if (fn) {
      this.phase = 'action:' + label;
      await fn();
      await this.settle(opts.settle ?? 120);
    }
    return this.snap(label, b);
  }

  async snap(label, b = []) {
    if (this.labels.has(label)) throw new Error(`Duplicate step label "${label}"`);
    this.labels.add(label);
    const snap = await this.page.evaluate(snapshotInPage);
    snap.storage = await this.page.evaluate(storageInPage);
    const p = await this.page.evaluate(() => {
      const P = window.__parity;
      return { randomCalls: P.randomCalls, prints: P.prints.length, clipboard: P.clipboard.length, media: P.media.map(m => m.ev + ':' + m.el + (m.t !== undefined ? '@' + m.t : '')).join(' '), errors: P.errors.join(' | ') };
    });
    snap.instrument = p;
    this.steps.push({ label, b, snap });
    return snap;
  }

  async inventory(b = []) {
    const inv = await this.page.evaluate(inventoryInPage);
    this.steps.push({ label: 'inventory', b, snap: inv });
    this.labels.add('inventory');
    return inv;
  }

  // Reference expectation from Section 1. Soft: recorded for the report, never fatal.
  check(b, ok, detail, value) {
    this.checks.push({ b, ok: !!ok, detail, value: value === undefined ? undefined : value });
    return !!ok;
  }

  // A Section 1 expectation this browser cannot exercise (with the reason, for the report).
  na(b, detail, reason) {
    this.checks.push({ b, ok: null, na: true, detail, reason });
  }

  async click(selector, opts = {}) { await this.page.locator(selector).first().click(opts); }
  async select(selector, value) { await this.page.locator(selector).first().selectOption(value); }
  async fill(selector, text) { await this.page.locator(selector).first().fill(text); }
  async tab(mode) { await this.click(`[data-mode="${mode}"]`); }

  record(label, value) { this.artifacts[label] = value; return value; }

  file(name) { return path.join(ensureDir(path.join(this.dir, this.side)), safe(name)); }

  // A .txt export: the real download (file name and bytes), with the page's Blob text as a cross-check.
  async download(label, trigger) {
    this.phase = 'action:' + label;
    const blobsBefore = await this.page.evaluate(() => window.__parity.blobs.length);
    let download = null, error = null;
    try {
      [download] = await Promise.all([this.page.waitForEvent('download', { timeout: 10000 }), trigger()]);
    } catch (e) { error = String(e.message).split('\n')[0]; }
    await this.page.waitForFunction(n => window.__parity.blobs.length > n && window.__parity.blobs[window.__parity.blobs.length - 1].text !== null, blobsBefore, { timeout: 5000 }).catch(() => {});
    const blobText = await this.page.evaluate(n => (window.__parity.blobs[n] || {}).text ?? null, blobsBefore);
    let text = null, filename = null;
    if (download) {
      filename = download.suggestedFilename();
      const target = this.file(label + '__' + filename);
      await download.saveAs(target);
      text = fs.readFileSync(target, 'utf8');
    }
    const rec = { filename, text, blobText, downloadEvent: !!download, error, blobMatchesDownload: download ? text === blobText : null };
    this.artifacts[label] = rec;
    return rec;
  }

  // A print edition: window.print is recorded (see initScript), so the sheet stays in the DOM. It is
  // rendered in print media: PDF in Chromium, full-page print-media screenshot in WebKit.
  async print(label, trigger) {
    this.phase = 'action:' + label;
    const before = await this.page.evaluate(() => window.__parity.prints.length);
    await trigger();
    await this.page.waitForFunction(n => window.__parity.prints.length > n, before, { timeout: 5000 }).catch(() => {});
    const call = await this.page.evaluate(n => window.__parity.prints[n] || null, before);
    const outline = await this.page.evaluate(() => {
      const s = document.querySelector('.tl-print-sheet');
      if (!s) return null;
      return Array.from(s.querySelectorAll('*')).filter(e => e.children.length === 0 || e.tagName === 'P').map(e => e.tagName.toLowerCase() + ': ' + e.textContent).join('\n');
    });
    await this.page.emulateMedia({ media: 'print' });
    await this.settle(150);
    const printText = await this.page.evaluate(() => document.body.innerText.replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').trim());
    let file = null;
    if (this.browserName === 'chromium') {
      file = this.file(label + '.pdf');
      await this.page.pdf({ path: file, format: 'Letter', printBackground: true });
    } else {
      file = this.file(label + '.print.png');
      await this.page.screenshot({ path: file, fullPage: true });
    }
    await this.page.emulateMedia({ media: 'screen' });
    await this.page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await this.settle(80);
    const rec = { printCalled: !!call, sheetClass: call ? call.classes.join(',') : null, outline, printText, file: path.basename(file) };
    this.artifacts[label] = rec;
    return rec;
  }

  async lastClipboard() {
    return this.page.evaluate(() => { const c = window.__parity.clipboard; return c.length ? c[c.length - 1] : null; });
  }

  async screenshot(name, opts = {}) {
    const file = this.file(name + '.png');
    if (opts.locator) await this.page.locator(opts.locator).first().screenshot({ path: file, animations: 'disabled' });
    else await this.page.screenshot({ path: file, fullPage: opts.fullPage ?? true, animations: 'disabled' });
    return file;
  }

  observation(meta) {
    return {
      area: meta.area, scenario: meta.name, side: this.side, browser: this.browserName, url: this.side === 'reference' ? '(reference)' : this.url,
      bItems: meta.b, steps: this.steps, checks: this.checks, artifacts: this.artifacts,
      console: this.console, pageErrors: this.pageErrors, requests: this.requests, dialogs: this.dialogs,
    };
  }
}

// What two observations are compared on: every step snapshot and every artifact's text.
export function comparable(obs) {
  const out = {};
  for (const s of obs.steps) out[s.label] = s.snap;
  for (const [k, v] of Object.entries(obs.artifacts)) {
    if (v && typeof v === 'object') {
      const { file, error, ...rest } = v;
      out['artifact:' + k] = rest;
    } else out['artifact:' + k] = v;
  }
  out.pageErrors = obs.pageErrors.map(e => e.message).join(' | ');
  out.dialogs = obs.dialogs.map(d => d.type + ': ' + d.message).join(' | ');
  return flatten(out);
}

async function newSide(browser, browserName, cfg, meta, side, url, dir) {
  const opts = { viewport: meta.viewport || DESKTOP, acceptDownloads: true, reducedMotion: meta.reducedMotion || 'no-preference', hasTouch: !!meta.hasTouch, locale: 'en-US', timezoneId: 'America/New_York' };
  if (meta.deviceScaleFactor) opts.deviceScaleFactor = meta.deviceScaleFactor;
  const context = await browser.newContext(opts);
  if (browserName === 'chromium') await context.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  await context.addInitScript({ content: initScript({ seed: cfg.seed, blockStorage: !!meta.blockStorage }) });
  if (cfg.fonts === 'stub') {
    await context.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({ status: 200, contentType: r.request().url().includes('googleapis') ? 'text/css' : 'font/woff2', body: '' }));
  }
  const page = await context.newPage();
  // Same fixed clock on both sides. v1.88 never reads the clock; this keeps any rebuild honest too.
  await page.clock.setFixedTime(new Date(cfg.fixedTime));
  return new Driver({ page, context, side, url, browserName, dir, cfg });
}

// Register one scenario as a Playwright test.
export function scenario(area, name, meta, body) {
  meta = { area, name, b: [], ...meta };
  test(name, async ({ browser, browserName }, testInfo) => {
    if (meta.timeout) testInfo.setTimeout(meta.timeout);
    const cfg = getConfig();
    const dir = ensureDir(path.join(cfg.runDir, browserName, area, safe(name)));
    const sides = [['reference', cfg.referenceUrl]];
    if (cfg.candidate) sides.push(['candidate', cfg.candidate.url]);
    const obs = {};
    for (const [side, url] of sides) {
      const d = await newSide(browser, browserName, cfg, meta, side, url, dir);
      try {
        await body(d, { side, cfg, browserName });
        await d.snap('end', meta.b);
      } catch (e) {
        d.artifacts.__failure = String(e && e.stack || e).slice(0, 2000);
        writeJson(path.join(cfg.runDir, browserName, area, safe(name) + '.' + side + '.json'), d.observation(meta));
        await d.context.close();
        throw e;
      }
      obs[side] = d.observation(meta);
      writeJson(path.join(cfg.runDir, browserName, area, safe(name) + '.' + side + '.json'), obs[side]);
      await d.context.close();
    }
    if (meta.after) await meta.after({ obs, dir, cfg, browserName });
    if (!cfg.candidate) return;
    const result = compareLeaves(comparable(obs.reference), comparable(obs.candidate));
    const origin = cfg.candidate.kind === 'url' ? new URL(cfg.candidate.url).host : '';
    const network = { reference: classifyRequests(obs.reference.requests, 'reference', origin), candidate: classifyRequests(obs.candidate.requests, 'candidate', origin) };
    const candidateConsoleErrors = obs.candidate.console.filter(c => c.type === 'error');
    const diff = {
      area, scenario: name, browser: browserName, selfParity: cfg.selfParity, bItems: meta.b,
      equal: result.equal, explained: result.explained, unexplained: result.unexplained,
      networkUnexplained: network.candidate.filter(n => n.verdict === 'unexplained'),
      candidateConsoleErrors,
    };
    writeJson(path.join(cfg.runDir, browserName, area, safe(name) + '.diff.json'), diff);
    const problems = diff.unexplained.length + diff.networkUnexplained.length + candidateConsoleErrors.length;
    const sample = diff.unexplained.slice(0, 6).map(u => `  ${u.key}\n    reference: ${JSON.stringify(u.normalizedReference ?? u.reference).slice(0, 220)}\n    candidate: ${JSON.stringify(u.normalizedCandidate ?? u.candidate).slice(0, 220)}` +
      (u.firstDifferentLine ? `\n    first different line ${u.firstDifferentLine}: ${JSON.stringify(u.referenceLine)} vs ${JSON.stringify(u.candidateLine)}` : '')).join('\n');
    expect(problems, `${problems} unexplained difference(s) in ${area}/${name} [${browserName}]\n${sample}\n` +
      diff.networkUnexplained.slice(0, 4).map(n => `  request ${n.phase} ${n.url}`).join('\n') +
      candidateConsoleErrors.slice(0, 4).map(c => `  console error: ${c.text}`).join('\n')).toBe(0);
  });
}

export { test, expect, loadDmap };
