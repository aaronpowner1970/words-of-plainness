// The planned-differences map itself: well-formed and complete (always); and, against a real
// candidate, every placeholder filled in and matching something, and every required difference
// present. Skipped in self-parity, where there is no rebuild to find.
import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';
import { getConfig, writeJson } from '../lib/config.mjs';
import { loadDmap } from '../lib/dmap.mjs';
import { DESKTOP } from '../lib/harness.mjs';

const KINDS = new Set(['replace', 'remove', 'remove-line', 'key', 'value', 'selector', 'network', 'placeholder', 'require', 'visual']);

test('D00-map-well-formed', async ({ browserName }) => {
  const cfg = getConfig();
  const dm = loadDmap();
  const ids = dm.raw.items.map(i => i.id);
  const want = Array.from({ length: 18 }, (_, i) => 'D' + (i + 1));
  const bad = dm.raw.items.flatMap(i => (i.excuses || []).filter(e => !KINDS.has(e.kind)).map(e => i.id + ':' + e.kind));
  const placeholders = dm.placeholders.map(p => ({ id: p.id, name: p.name, filled: !!(p.selector || p.text), note: p.note }));
  writeJson(path.join(cfg.runDir, browserName, 'dmap', 'map.json'), { ids, placeholders, counts: Object.fromEntries(['text', 'keys', 'values', 'selectors', 'network', 'placeholders', 'requires'].map(k => [k, dm[k].length])) });
  expect([...ids].sort()).toEqual([...want].sort());
  expect(bad).toEqual([]);
  for (const r of dm.text) if (r.kind === 'replace' || r.kind === 'remove') expect(r.find || r.re, `${r.id} needs find or regex`).toBeTruthy();
});

test('D01-placeholders-and-requirements', async ({ browser, browserName }) => {
  const cfg = getConfig();
  test.skip(!cfg.candidate, 'No candidate: nothing to check the planned differences against.');
  test.skip(cfg.selfParity, 'Self-parity: the candidate is v1.88 itself, which carries none of the planned differences.');
  const dm = loadDmap();
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await page.goto(cfg.candidate.url, { waitUntil: 'load' });
  await page.waitForSelector('#tool-root', { state: 'attached', timeout: 30000 });
  const failures = [];
  for (const p of dm.placeholders) {
    if (!p.selector && !p.text) { failures.push(`${p.id} placeholder ${p.name} is not filled in: ${p.note}`); continue; }
    if (p.selector) {
      const n = await page.locator(p.selector).count();
      if (!n) failures.push(`${p.id} placeholder ${p.name} matches nothing: ${p.selector}`);
    }
  }
  // Text-level requirements are checked against the page text with every lesson part opened.
  const pageText = await page.evaluate(() => document.documentElement.textContent);
  let lessonText = '';
  if (await page.locator('#lessonStart').count()) {
    await page.click('#lessonStart');
    for (let i = 0; i <= 11; i++) {
      await page.selectOption('#lessonMenu', String(i));
      lessonText += await page.evaluate(() => document.querySelector('#lessonBody').textContent) + '\n';
    }
  }
  const all = pageText + '\n' + lessonText + '\n' + (await page.title());
  for (const r of dm.requires) {
    if (r.absent) for (const t of r.absent) if (all.includes(t)) failures.push(`${r.id} requires "${t}" to be gone`);
    if (r.present) for (const t of r.present) if (!all.includes(t)) failures.push(`${r.id} requires "${t}"`);
    if (r.check === 'title' && (await page.title()) !== r.equals) failures.push(`${r.id} title must be "${r.equals}", is "${await page.title()}"`);
    if (r.check === 'mainCount') { const n = await page.locator('main').count(); if (n !== r.equals) failures.push(`${r.id} needs ${r.equals} <main>, found ${n}`); }
    if (r.selectorPresent && !(await page.locator(r.selectorPresent).count())) failures.push(`${r.id} needs ${r.selectorPresent}${r.where ? ' (' + r.where + ')' : ''}`);
  }
  writeJson(path.join(cfg.runDir, browserName, 'dmap', 'candidate-checks.json'), { failures });
  await context.close();
  expect(failures, 'planned differences not yet carried by the candidate').toEqual([]);
});
