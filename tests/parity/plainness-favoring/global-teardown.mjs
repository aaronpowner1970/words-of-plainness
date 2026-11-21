// After all scenarios: gather every observation, B-item check and diff of this run into summary.json
// and summary.md in the run folder.
import fs from 'node:fs';
import path from 'node:path';
import { getConfig, fingerprint, writeJson } from './lib/config.mjs';

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== '_playwright') walk(p, out); } else out.push(p);
  }
  return out;
}

export default async function globalTeardown() {
  const cfg = getConfig();
  const files = walk(cfg.runDir);
  const bItems = {}; // B -> browser -> { checks: n, failed: [], scenarios: Set, parity: 'equal'|'explained'|'unexplained' }
  const scenarios = [];
  const diffs = [];
  for (const f of files) {
    if (f.endsWith('.diff.json')) { diffs.push(JSON.parse(fs.readFileSync(f, 'utf8'))); continue; }
    if (!f.endsWith('.reference.json')) continue;
    const o = JSON.parse(fs.readFileSync(f, 'utf8'));
    scenarios.push({ area: o.area, scenario: o.scenario, browser: o.browser, steps: o.steps.length, checks: o.checks.length, failedChecks: o.checks.filter(c => c.ok === false).length, naChecks: o.checks.filter(c => c.na).length, failure: o.artifacts.__failure || null, consoleErrors: o.console.filter(c => c.type === 'error').length, pageErrors: o.pageErrors.length,
      actionHttpRequests: o.requests.filter(r => r.phase !== 'load' && /^https?:/i.test(r.url)).map(r => r.phase + ' ' + r.url),
      loadHosts: [...new Set(o.requests.filter(r => r.phase === 'load' && /^https?:/i.test(r.url)).map(r => new URL(r.url).host))].sort() });
    const touch = (b, browser) => ((bItems[b] ??= {})[browser] ??= { checks: 0, failed: [], scenarios: new Set(), snapshots: 0, parity: null });
    for (const b of o.bItems || []) touch(b, o.browser).scenarios.add(`${o.area}/${o.scenario}`);
    for (const s of o.steps) for (const b of s.b || []) touch(b, o.browser).snapshots++;
    for (const c of o.checks) {
      const t = touch(c.b, o.browser);
      t.scenarios.add(`${o.area}/${o.scenario}`);
      if (c.na) { (t.na ??= []).push({ scenario: `${o.area}/${o.scenario}`, detail: c.detail, reason: c.reason }); continue; }
      t.checks++;
      if (!c.ok) t.failed.push({ scenario: `${o.area}/${o.scenario}`, detail: c.detail, value: c.value });
    }
  }
  for (const df of diffs) {
    for (const b of df.bItems || []) {
      const t = ((bItems[b] ??= {})[df.browser] ??= { checks: 0, failed: [], scenarios: new Set(), snapshots: 0, parity: null });
      const v = df.unexplained.length || df.networkUnexplained.length || df.candidateConsoleErrors.length ? 'unexplained' : df.explained.length ? 'explained' : 'equal';
      const rank = { equal: 0, explained: 1, unexplained: 2 };
      if (t.parity === null || rank[v] > rank[t.parity]) t.parity = v;
    }
  }
  const num = k => (/^B\d+$/.test(k) ? Number(k.slice(1)) : 1000);
  const order = Object.keys(bItems).sort((a, b) => num(a) - num(b) || (a < b ? -1 : 1));
  const bOut = Object.fromEntries(order.map(b => [b, Object.fromEntries(Object.entries(bItems[b]).map(([br, t]) => [br, { ...t, scenarios: [...t.scenarios].sort() }]))]));
  const summary = {
    run: cfg.run, finishedAt: new Date().toISOString(), reference: fingerprint(cfg.referencePath),
    candidate: cfg.candidate ? cfg.candidate.label : null, selfParity: cfg.selfParity,
    scenarios: scenarios.sort((a, b) => (a.browser + a.area + a.scenario < b.browser + b.area + b.scenario ? -1 : 1)),
    bItems: bOut,
    diffs: diffs.map(d => ({ area: d.area, scenario: d.scenario, browser: d.browser, equal: d.equal, explained: d.explained.length, explainedBy: [...new Set(d.explained.flatMap(e => e.by))].sort(), unexplained: d.unexplained.length, networkUnexplained: d.networkUnexplained.length, candidateConsoleErrors: d.candidateConsoleErrors.length, firstUnexplained: d.unexplained.slice(0, 5).map(u => u.key) })),
  };
  writeJson(path.join(cfg.runDir, 'summary.json'), summary);
  const md = [];
  md.push(`# Parity run ${cfg.run}`, '', `Reference: ${summary.reference.path} (${summary.reference.bytes} bytes, ${summary.reference.modified}, SHA-256 ${summary.reference.sha256})`, `Candidate: ${summary.candidate || '(none)'}${cfg.selfParity ? ' (self-parity: byte-identical to the reference)' : ''}`, '');
  md.push('| B-item | browser | checks | failed | not runnable here | parity | scenarios |', '|---|---|---|---|---|---|---|');
  for (const b of order) for (const [br, t] of Object.entries(bOut[b])) md.push(`| ${b} | ${br} | ${t.checks} | ${t.failed.length} | ${(t.na || []).length} | ${t.parity ?? '—'} | ${t.scenarios.join(', ')} |`);
  if (summary.diffs.length) {
    md.push('', '| area/scenario | browser | equal | explained (by) | unexplained | network | console |', '|---|---|---|---|---|---|---|');
    for (const d of summary.diffs) md.push(`| ${d.area}/${d.scenario} | ${d.browser} | ${d.equal} | ${d.explained} (${d.explainedBy.join(' ')}) | ${d.unexplained} | ${d.networkUnexplained} | ${d.candidateConsoleErrors} |`);
  }
  fs.writeFileSync(path.join(cfg.runDir, 'summary.md'), md.join('\n') + '\n', 'utf8');
}
