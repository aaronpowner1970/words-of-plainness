// Compare two runs of the suite, observation by observation (determinism proof).
//
//   npm run parity:lattice:compare -- <runA> <runB> [--side reference|candidate]
//
// <runX> is a run label under <PARITY_OUT_ROOT>\runs, or a full path. Every step snapshot (state,
// storage JSON, instrument counters), every artifact (export text, print text, copied text, media
// hashes, structure checks), page errors, dialogs, console messages and requests must be identical.
// Screenshots are compared pixel for pixel and reported, never failed.
import fs from 'node:fs';
import path from 'node:path';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';
import { comparable } from '../lib/harness.mjs';
import { flatten } from '../lib/dmap.mjs';

const args = process.argv.slice(2);
const side = args.includes('--side') ? args[args.indexOf('--side') + 1] : 'reference';
const runs = args.filter((a, i) => !a.startsWith('--') && args[i - 1] !== '--side');
if (runs.length !== 2) { console.error('usage: compare-runs.mjs <runA> <runB> [--side reference|candidate]'); process.exit(2); }
const root = path.resolve(process.env.PARITY_OUT_ROOT || 'C:\\Users\\aaron\\Documents\\wop-scratch\\Plainness_Favoring\\parity');
const dirOf = r => (fs.existsSync(r) && path.isAbsolute(r) ? r : path.join(root, 'runs', r));
const [A, B] = runs.map(dirOf);

function walk(base, dir = base, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== '_playwright') walk(base, p, out); } else out.push(path.relative(base, p));
  }
  return out;
}
const area = rel => { const parts = rel.split(path.sep); return parts[0] + '/' + parts[1]; };
function leaves(file) {
  const o = JSON.parse(fs.readFileSync(file, 'utf8'));
  const c = comparable(o);
  Object.assign(c, flatten({ console: o.console.map(m => m.type + ' ' + m.phase + ' ' + m.text), requests: o.requests.map(r => r.phase + ' ' + r.resourceType + ' ' + r.method + ' ' + r.url), checks: o.checks.map(k => k.b + ' ' + (k.na ? 'na' : k.ok) + ' ' + k.detail) }, 'meta'));
  return c;
}

const filesA = walk(A).filter(f => f.endsWith('.' + side + '.json')).sort();
const filesB = new Set(walk(B).filter(f => f.endsWith('.' + side + '.json')));
const result = { runA: A, runB: B, side, comparedAt: new Date().toISOString(), observations: 0, identical: 0, differing: [], missing: [], byArea: {}, images: { compared: 0, identical: 0, differing: [] } };
for (const rel of filesA) {
  if (!filesB.has(rel)) { result.missing.push(rel); continue; }
  filesB.delete(rel);
  result.observations++;
  const a = leaves(path.join(A, rel)), b = leaves(path.join(B, rel));
  const keys = [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();
  const diffs = keys.filter(k => a[k] !== b[k]).map(k => ({ key: k, a: a[k], b: b[k] }));
  const ar = area(rel);
  const t = (result.byArea[ar] ??= { observations: 0, leaves: 0, differing: 0 });
  t.observations++; t.leaves += keys.length; t.differing += diffs.length;
  if (diffs.length) result.differing.push({ file: rel, count: diffs.length, first: diffs.slice(0, 8) });
  else result.identical++;
}
result.missing.push(...[...filesB].map(f => '(only in B) ' + f));
// Screenshots and print-media screenshots: pixel comparison, reported only.
for (const rel of walk(A).filter(f => f.endsWith('.png') && f.split(path.sep).includes(side))) {
  const pb = path.join(B, rel);
  if (!fs.existsSync(pb)) continue;
  const x = PNG.sync.read(fs.readFileSync(path.join(A, rel))), y = PNG.sync.read(fs.readFileSync(pb));
  result.images.compared++;
  if (x.width !== y.width || x.height !== y.height) { result.images.differing.push({ file: rel, size: [[x.width, x.height], [y.width, y.height]] }); continue; }
  const n = pixelmatch(x.data, y.data, null, x.width, x.height, { threshold: 0 });
  if (n) result.images.differing.push({ file: rel, changedPixels: n }); else result.images.identical++;
}
const out = path.join(root, `determinism-${path.basename(A)}-vs-${path.basename(B)}-${side}.json`);
fs.writeFileSync(out, JSON.stringify(result, null, 2) + '\n', 'utf8');
console.log(`${side}: ${result.identical}/${result.observations} observations identical; ${result.differing.length} differing; ${result.missing.length} missing`);
for (const [k, v] of Object.entries(result.byArea)) console.log(`  ${k}: ${v.observations} observations, ${v.leaves} values, ${v.differing} differing`);
console.log(`  images: ${result.images.identical}/${result.images.compared} pixel-identical`);
for (const d of result.differing) console.log('  DIFF ' + d.file + ' (' + d.count + '): ' + d.first.map(x => x.key).join(', '));
console.log('written: ' + out);
process.exit(result.differing.length || result.missing.length ? 1 : 0);
