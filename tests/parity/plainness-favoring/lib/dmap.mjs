// The planned-differences map (Section 2), loaded as data, and the comparison that uses it.
import fs from 'node:fs';
import path from 'node:path';
import { HARNESS_DIR } from './config.mjs';

const globRe = g => new RegExp('^' + g.split('*').map(s => s.replace(/[.+?^${}()|[\]\\]/g, '\\$&')).join('.*') + '$');

let cached = null;
export function loadDmap() {
  if (cached) return cached;
  const raw = JSON.parse(fs.readFileSync(path.join(HARNESS_DIR, 'planned-differences.json'), 'utf8'));
  const text = [], keys = [], values = [], selectors = [], network = [], placeholders = [], requires = [];
  for (const item of raw.items) {
    for (const ex of item.excuses || []) {
      const r = { id: item.id, ...ex };
      if (ex.kind === 'replace' || ex.kind === 'remove' || ex.kind === 'remove-line') {
        if (ex.regex) r.re = new RegExp(ex.regex, ex.kind === 'remove-line' ? 'gm' : 'g');
        text.push(r);
      } else if (ex.kind === 'key') { r.res = ex.keys.map(globRe); keys.push(r); }
      else if (ex.kind === 'value') { r.res = ex.keys.map(globRe); values.push(r); }
      else if (ex.kind === 'selector') selectors.push(r);
      else if (ex.kind === 'network') network.push(r);
      else if (ex.kind === 'placeholder') placeholders.push(r);
      else if (ex.kind === 'require') requires.push(r);
    }
  }
  cached = { raw, text, keys, values, selectors, network, placeholders, requires };
  return cached;
}

// Apply text and value excuses to one leaf. Returns the new value and the D-items that changed it.
export function normalizeLeaf(key, value, dmap = loadDmap()) {
  const touched = new Set();
  let v = value;
  for (const r of dmap.values) {
    if (r.res.some(re => re.test(key)) && typeof v === 'string' && Object.hasOwn(r.map, v)) { v = r.map[v]; touched.add(r.id); }
  }
  if (typeof v !== 'string') return { value: v, touched };
  for (const r of dmap.text) {
    const before = v;
    if (r.kind === 'replace') v = r.re ? v.replace(r.re, r.with) : v.split(r.find).join(r.with);
    else if (r.kind === 'remove') v = r.re ? v.replace(r.re, '') : v.split(r.find).join('');
    else if (r.kind === 'remove-line') v = v.replace(r.re, '\u0000').split('\n').filter(l => l !== '\u0000').join('\n');
    if (v !== before) touched.add(r.id);
  }
  return { value: v, touched };
}

export function keyExcuse(key, dmap = loadDmap()) {
  return dmap.keys.filter(r => r.res.some(re => re.test(key))).map(r => r.id);
}

// Flatten nested JSON into "a.b.0.c" -> leaf.
export function flatten(obj, prefix = '', out = {}) {
  if (obj === null || typeof obj !== 'object') { out[prefix] = obj; return out; }
  const entries = Array.isArray(obj) ? obj.map((v, i) => [String(i), v]) : Object.entries(obj);
  if (!entries.length) { out[prefix] = Array.isArray(obj) ? '[]' : '{}'; return out; }
  for (const [k, v] of entries) flatten(v, prefix ? prefix + '.' + k : k, out);
  return out;
}

// Compare two flattened observation sets. Every key is classified equal / explained / unexplained.
export function compareLeaves(refLeaves, candLeaves, dmap = loadDmap()) {
  const keys = [...new Set([...Object.keys(refLeaves), ...Object.keys(candLeaves)])].sort();
  const explained = [], unexplained = [];
  let equal = 0;
  for (const key of keys) {
    const r = refLeaves[key], c = candLeaves[key];
    if (r === c) { equal++; continue; }
    const byKey = keyExcuse(key, dmap);
    if (byKey.length) { explained.push({ key, by: byKey, reference: r, candidate: c }); continue; }
    if (r === undefined || c === undefined) { unexplained.push({ key, reference: r ?? '(absent)', candidate: c ?? '(absent)' }); continue; }
    const nr = normalizeLeaf(key, r, dmap), nc = normalizeLeaf(key, c, dmap);
    if (nr.value === nc.value) explained.push({ key, by: [...new Set([...nr.touched, ...nc.touched])].sort(), reference: r, candidate: c });
    else unexplained.push({ key, reference: r, candidate: c, normalizedReference: nr.value, normalizedCandidate: nc.value, ...lineDiff(nr.value, nc.value) });
  }
  return { equal, explained, unexplained };
}

// For multi-line text, name the first differing line so the report is readable.
function lineDiff(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || (!a.includes('\n') && !b.includes('\n'))) return {};
  const A = a.split('\n'), B = b.split('\n');
  for (let i = 0; i < Math.max(A.length, B.length); i++) {
    if (A[i] !== B[i]) return { firstDifferentLine: i + 1, referenceLine: A[i] ?? '(none)', candidateLine: B[i] ?? '(none)' };
  }
  return {};
}

// Network: classify every http(s) request against the allow-list and D-map network excuses.
export function classifyRequests(requests, side, candidateOrigin, dmap = loadDmap()) {
  const allow = side === 'reference' ? dmap.raw.network_allow_list.reference : dmap.raw.network_allow_list.candidate.map(h => (h === '<candidate origin>' ? candidateOrigin : h));
  const findings = [];
  for (const r of requests) {
    if (!/^https?:/i.test(r.url)) continue;
    const host = new URL(r.url).host;
    const excuse = dmap.network.filter(n => n.host === host && (!n.phases || n.phases.includes(r.phase === 'load' ? 'load' : 'action')) && (!n.resourceTypes || n.resourceTypes.includes(r.resourceType)));
    if (r.phase === 'load') {
      if (allow.includes(host)) findings.push({ ...r, host, verdict: 'allowed', by: excuse.map(e => e.id) });
      else if (excuse.length) findings.push({ ...r, host, verdict: 'explained', by: excuse.map(e => e.id) });
      else findings.push({ ...r, host, verdict: 'unexplained' });
    } else {
      if (excuse.length) findings.push({ ...r, host, verdict: 'explained', by: excuse.map(e => e.id) });
      else findings.push({ ...r, host, verdict: 'unexplained' });
    }
  }
  return findings;
}
