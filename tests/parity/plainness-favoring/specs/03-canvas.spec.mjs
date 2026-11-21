// Section 5.2 (3) Canvas: images at Reset, Front and Top, with and without Spread layers and
// connections (compared with a tolerance); clicking each node's projected position must select
// the same node on both sides.
import fs from 'node:fs';
import path from 'node:path';
import { scenario, expect } from '../lib/harness.mjs';
import { writeJson } from '../lib/config.mjs';
import { imagePair } from '../lib/visual.mjs';
import { rule } from '../lib/flows.mjs';

const TOLERANCE = Number(process.env.PARITY_CANVAS_TOLERANCE || 0.03);
const VISIT = 'words-of-plainness:lattice:visit:v1';
const NODES = [];
for (let s = 0; s < 3; s++) for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) NODES.push({ id: `n${s}${r}${c}`, s, r, c, type: 'stanza' });
for (let c = 0; c < 3; c++) NODES.push({ id: `c${c}`, s: 3, r: 1, c, type: 'coda' });

// The same projection v1.88 uses (coords + projector), fed with the camera the page saved.
function project(n, cam, w, h) {
  const p = { x: (n.c - 1) * 1.3, y: (1 - n.r) * 1.23, z: n.type === 'coda' ? 3.06 : (n.s - 1) * (cam.explode ? 2.05 : 1.35) };
  const c = Math.cos(cam.yaw), s = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
  const x1 = p.x * c + p.z * s, z1 = -p.x * s + p.z * c, y2 = p.y * cp - z1 * sp, z2 = p.y * sp + z1 * cp;
  const k = 8.8 / (8.8 - z2), scale = Math.min(w / 7.8, h / 6.45) * cam.zoom;
  return { x: w * 0.5 + x1 * scale * k, y: h * 0.49 - y2 * scale * k, z: z2, k };
}

// v1.88's hitNode: every node whose hit circle (max(1.22 × size, 16) px) covers the point; the
// nearest to the viewer wins, ties broken by distance.
function expectedHit(pt, cam, w, h, slack = 0) {
  const opts = NODES.map(n => { const p = project(n, cam, w, h); const sz = Math.max(7, Math.min(24, 13 * p.k * cam.zoom)); return { n, p, rad: Math.max(sz * 1.22, 16) + slack }; })
    .filter(o => Math.hypot(pt.x - o.p.x, pt.y - o.p.y) <= o.rad);
  opts.sort((a, b) => (a.p.z === b.p.z ? Math.hypot(pt.x - a.p.x, pt.y - a.p.y) - Math.hypot(pt.x - b.p.x, pt.y - b.p.y) : b.p.z - a.p.z));
  return opts[0] ? opts[0].n : null;
}

async function camera(d) {
  const v = await d.page.evaluate(k => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } }, VISIT);
  return { yaw: v.yaw, pitch: v.pitch, zoom: v.zoom, explode: v.explode };
}

const VIEWS = [['reset', '#resetCamera'], ['front', '#frontCamera'], ['top', '#topCamera']];

scenario('canvas', 'C01-images', { b: ['B35', 'B36', 'B37'], timeout: 180000,
  after: async ({ obs, dir }) => {
    if (!obs.candidate) return;
    const pairs = {};
    for (const f of fs.readdirSync(path.join(dir, 'reference')).filter(f => f.endsWith('.png'))) {
      const c = path.join(dir, 'candidate', f);
      if (fs.existsSync(c)) pairs[f] = imagePair(path.join(dir, 'reference', f), c, path.join(dir, f.replace('.png', '.diff.png')));
    }
    writeJson(path.join(dir, 'image-pairs.json'), { tolerance: TOLERANCE, pairs });
    const over = Object.entries(pairs).filter(([, p]) => p.changedRatio > TOLERANCE || p.reference.join() !== p.candidate.join());
    expect(over.map(([f, p]) => `${f}: ${p.changedRatio}`), `canvas images beyond tolerance ${TOLERANCE}`).toEqual([]);
  } }, async d => {
  await d.open();
  await d.tab('cube'); await d.settle(300);
  for (const [view, sel] of VIEWS) {
    for (const spread of [false, true]) {
      for (const wires of [true, false]) {
        await d.click(sel);
        const cam = await camera(d);
        if (cam.explode !== spread) await d.click('#explode');
        const on = await d.page.locator('#showWires').isChecked();
        if (on !== wires) await d.click('#showWires');
        await d.page.mouse.move(2, 2);
        await d.settle(150);
        const name = `${view}-${spread ? 'spread' : 'gathered'}-${wires ? 'wires' : 'nowires'}`;
        await d.screenshot(name, { locator: '#cube' });
        const s = await d.snap(name, ['B35', 'B36', 'B37']);
        d.record('camera-' + name, await camera(d));
        d.check('B36', s.cube.startsWith(spread ? '⇤ Gather layers' : '⇔ Spread layers') && s.values.showWires === String(wires), `${name}: controls reflect the view`, s.cube);
      }
    }
  }
});

scenario('canvas', 'C02-hit-testing', { b: ['B35'], timeout: 240000 }, async d => {
  await d.open();
  await rule(d, 'free');
  await d.tab('cube'); await d.settle(300);
  const box = await d.page.locator('#cube').boundingBox();
  for (const [view, sel] of VIEWS) {
    await d.click(sel); await d.settle(80);
    const cam = await camera(d);
    const hits = [];
    for (const n of NODES) {
      const p = project(n, cam, box.width, box.height);
      // A node drawn under the legend, the corner label or the hover tooltip, or off the canvas,
      // cannot be clicked there: record what covers it instead of clicking blind.
      await d.page.mouse.move(2, 2);
      const cover = await d.page.evaluate(([x, y]) => {
        const e = document.elementFromPoint(x, y);
        if (e && e.id === 'cube') return null;
        return e ? (e.id ? '#' + e.id : '.' + [...e.classList].join('.') || e.tagName.toLowerCase()) : 'off-page';
      }, [box.x + p.x, box.y + p.y]);
      if (cover || p.x < 0 || p.y < 0 || p.x > box.width || p.y > box.height) { hits.push(n.id + ' → (covered by ' + (cover || 'off-canvas') + ')'); continue; }
      await d.page.mouse.click(box.x + p.x, box.y + p.y);
      await d.settle(0);
      const got = await d.page.evaluate(() => { const r = document.querySelectorAll('#pathList .tl-path-node'); return r.length ? r[r.length - 1].querySelector('small').textContent + ' · ' + r[r.length - 1].querySelector('strong').textContent : ''; });
      hits.push(n.id + ' → ' + got);
      if (got) { await d.page.mouse.click(box.x + p.x, box.y + p.y); await d.settle(0); }
    }
    d.record('hits-' + view, hits.join('\n'));
    const labelOf = n => n.type === 'coda' ? `Coda · ${['Impulse', 'Process', 'Outcome'][n.c]}` : `Stanza ${['I', 'II', 'III'][n.s]} · Line ${n.r + 1} · ${['Impulse', 'Process', 'Outcome'][n.c]}`;
    const own = NODES.filter((n, i) => hits[i].split(' → ')[1].startsWith(labelOf(n) + ' · ')).length;
    // A click that lands within 1.5 px of a hit-circle edge may round either way (browsers round pointer
    // coordinates differently), so both neighbours are accepted there.
    const covered = hits.filter(h => h.includes('(covered by')).length;
    const mismatch = NODES.filter((n, i) => {
      if (hits[i].includes('(covered by')) return false;
      const pt = project(n, cam, box.width, box.height);
      const ok = [-1.5, 0, 1.5].map(sl => expectedHit(pt, cam, box.width, box.height, sl)).filter(Boolean).map(e => labelOf(e) + ' · ');
      return !ok.some(l => hits[i].split(' → ')[1].startsWith(l));
    }).map(n => n.id);
    d.check('B35', mismatch.length === 0, `${view}: every clickable point selects the node v1.88's hit rule predicts (${own} of 30 select their own node; ${covered} lie under an overlay or off the canvas; the rest are covered by a nearer node)`, { own, covered, mismatch });
    await d.snap('after-' + view, ['B35']);
  }
  // Hover tooltip at Reset.
  await d.click('#resetCamera'); await d.settle(80);
  const cam = await camera(d);
  const p = project(NODES[0], cam, box.width, box.height);
  const t = await d.step('hover-n000', ['B35'], () => d.page.mouse.move(box.x + p.x, box.y + p.y));
  d.check('B35', t.tooltip === 'Stanza I · Line 1 · Impulse · Writing plainly is breathing:', 'hover tooltip names the node', t.tooltip);
  // Coda focus: clicking a diamond before the path is complete chooses its lens.
  await rule(d, 'curated');
  await d.select('#layerFilter', 'c'); await d.settle(80);
  const camC = await camera(d);
  const pc = project(NODES[27], camC, box.width, box.height);
  const l = await d.step('coda-focus-lens', ['B37', 'B43'], () => d.page.mouse.click(box.x + pc.x, box.y + pc.y));
  d.check('B37', l.pressed.includes('lens:0=true') && l.cube.includes('Coda focus · Preference'), 'Coda focus: clicking a diamond explores its lens', l.cube);
});
