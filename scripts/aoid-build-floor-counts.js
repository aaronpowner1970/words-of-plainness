#!/usr/bin/env node
/* ============================================================
   AOID2 floor counts  (CODE-AOID2-48, pathway step 89)

   Builds data-sources/aoid/floor_counts.json, the ONE source of every per-floor count the
   Second Edition shows (the count sentence in a span's panel and the Record tab's
   summary table). Nothing in the build retypes a count: it reads that file.

   How a floor gets a count
     1. The scoring record is data-sources/aoid/floor_ledger.yaml: each scored floor's
        `result` line ("taught 15, contradicted 0, no position 1 of 16; review queue 1"),
        its span list and its `scored_on` date. A floor with no `scored_on` is NOT SCORED
        and gets no count at all (absence is not zero).
     2. The count is then cross-checked against every other record found for that floor:
          report     the Stage 1 scoring reports' summary tables (wop-scratch), latest report wins
          notes      the CODE-AOID2-11 / -10 review notes' "Standing after rulings" lines
          conductor  the closing text of the conductor's review steps (state.json, READ ONLY)
          disclosure the sixteen-family table in the A2-F1 and 29a/29b disclosure sources
        A floor is MATCH only if at least one such record exists and EVERY one agrees with
        the ledger on taught / contradicted / no position (and on the queue where it states
        one). Any disagreement makes the floor MISMATCH and it is given NO count. A floor
        with no second record is NO_SECOND_RECORD and also gets no count.
     3. Borderline readings and the queued families are tallied from the per-family tables
        of the scoring reports, and accepted only for the table whose own tally equals the
        ledger (taught / contradicted / no position / queue). If no table does, they are
        left null (shown as absent, never as zero).

   Run:    node scripts/aoid-build-floor-counts.js            (writes the JSON)
           node scripts/aoid-build-floor-counts.js --check    (fails if the JSON is stale)
   Paths:  WOP_SCRATCH (default C:/Users/aaron/Documents/wop-scratch)
           WOP_CONDUCTOR_STATE (default C:/Users/aaron/Documents/wop-conductor/state/state.json)
   ============================================================ */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const ROOT = path.join(__dirname, '..');
const SCRATCH = process.env.WOP_SCRATCH || 'C:/Users/aaron/Documents/wop-scratch';
const STATE = process.env.WOP_CONDUCTOR_STATE || 'C:/Users/aaron/Documents/wop-conductor/state/state.json';
const OUT = path.join(ROOT, 'data-sources/aoid/floor_counts.json');

const LEDGER = 'data-sources/aoid/floor_ledger.yaml';
const REPORTS = [ // latest first: the first report that states a floor decides the "report" record
  'WoP_AOID2_Stage1_A11_Scoring_Report_20261004.md',
  'WoP_AOID2_Stage1_A06_Scoring_Report_20261004.md',
  'WoP_AOID2_Stage1_A04_Scoring_Report_20261003.md',
];
const NOTES = [
  'WoP_AOID2_CODE-AOID2-11_Review_Notes_20261005.md',
];
const FAMILIES = [
  'Catholic', 'Eastern Orthodox', 'Lutheran', 'Anglican', 'Reformed', 'Methodist', 'Baptist', 'Pentecostal',
  'Stone-Campbell', 'Anabaptist', 'Adventist', 'Latter-day Saints', "Jehovah's Witnesses", 'Oriental Orthodox',
  'Church of the East', 'Holiness',
];

const read = (p) => fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n').split('\n');
const num = (s) => Number(s);
const floorId = (s) => {
  const m = /^(A\d+-F\d+|G\d+|L\d+|R\d+|29[ab])\b/.exec(s.trim().replace(/\*/g, ''));
  return m ? m[1] : null;
};

// ---- record 1: the ledger --------------------------------------------------------------------
function readLedger() {
  const d = yaml.load(fs.readFileSync(path.join(ROOT, LEDGER), 'utf8'));
  return d.scored.map((e) => {
    const spans = [].concat(e.span || []);
    const out = { id: String(e.item), title: e.title, spans, scored_on: e.scored_on ? new Date(e.scored_on).toISOString().slice(0, 10) : null, revised_on: e.revised_on ? new Date(e.revised_on).toISOString().slice(0, 10) : null, result: e.result, superseded: e.superseded_records || [], withheld: e.withheld || null };
    const m = /taught (\d+), (?:contradicted|divided) (\d+), no position (\d+)(?:, being confirmed (\d+))? of 16/.exec(e.result || '');
    if (m && out.scored_on) {
      out.t = num(m[1]); out.c = num(m[2]); out.n = num(m[3]);
      const q = /review queue (\d+)/.exec(e.result);
      out.q = q ? num(q[1]) : (m[4] ? num(m[4]) : 0);
    }
    return out;
  });
}

// ---- second records ---------------------------------------------------------------------------
const queueOf = (cell) => {
  const s = cell.trim();
  if (/^(none|0)$/i.test(s)) return { q: 0, names: [] };
  const m = /^q?(\d+)\s*(?:\((.*)\))?$/i.exec(s);
  if (!m) return null;
  const names = m[2] ? FAMILIES.filter((f) => m[2].toLowerCase().includes(f.toLowerCase().replace('latter-day saints', 'latter-day'))) : [];
  return { q: num(m[1]), names };
};

function fromReports(obs) {
  REPORTS.forEach((file) => {
    const lines = read(path.join(SCRATCH, file));
    lines.forEach((l, i) => {
      const loc = file + ':' + (i + 1);
      let m;
      // | A4-F1 | 14 | 0 | 2 (names) | q1 | yes |   and   | A2-F2 (amended) | 15 | 0 | 1 (Stone-Campbell) | 0 | **Yes** |
      const last = () => l.split('|').slice(1, -1).map((x) => x.trim()).pop();
      if ((m = /^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)[^|]*\|\s*([^|]+?)\s*\|/.exec(l))) {
        const id = floorId(m[1]); const q = queueOf(m[5]);
        if (id && q) (obs[id] = obs[id] || []).push({ record: 'report', locator: loc, t: num(m[2]), c: num(m[3]), n: num(m[4]), q: q.q, qNames: q.names, rank: REPORTS.indexOf(file), file, status: last() });
      } else if ((m = /^\|\s*([^|]+?)\s*\|\s*(\d+)\/(\d+)\/(\d+)\s*\|\s*([^|]+?)\s*\|/.exec(l))) { // | A6-F1 | 15/0/1 | none |
        const id = floorId(m[1]); const q = queueOf(m[5]);
        if (id && q) (obs[id] = obs[id] || []).push({ record: 'report', locator: loc, t: num(m[2]), c: num(m[3]), n: num(m[4]), q: q.q, qNames: q.names, rank: REPORTS.indexOf(file), file, status: last() });
      }
      // **Article 4 (rescored): A4-F4 15/0/1; A4-F6 15/0/1.
      if (/Article 4 \(rescored\)/.test(l)) {
        const re = /(A4-F\d) (\d+)\/(\d+)\/(\d+)/g;
        while ((m = re.exec(l))) (obs[m[1]] = obs[m[1]] || []).push({ record: 'report', locator: loc, t: num(m[2]), c: num(m[3]), n: num(m[4]), q: null, qNames: [], rank: REPORTS.indexOf(file), file, status: 'rescored' });
      }
    });
  });
  // keep only the latest report's observation per floor
  Object.keys(obs).forEach((id) => {
    const rep = obs[id].filter((o) => o.record === 'report');
    if (!rep.length) return;
    const best = Math.min(...rep.map((o) => o.rank));
    const latest = rep.filter((o) => o.rank === best);
    obs[id] = obs[id].filter((o) => o.record !== 'report').concat(latest.slice(0, 1).map(({ rank, ...o }) => o));
  });
}

function fromNotes(obs) {
  NOTES.forEach((file) => {
    read(path.join(SCRATCH, file)).forEach((l, i) => {
      const m0 = /^- \*\*Article (\d+):\*\*(.*)$/.exec(l);
      if (!m0) return;
      const art = m0[1];
      m0[2].split(';').forEach((part) => {
        const m = /(F\d+|G\d+)\s+(\d+)\/(\d+)\/(\d+)(?:\s*\(([^)]*)\))?/.exec(part);
        if (!m) return;
        const id = m[1].startsWith('G') ? m[1] : 'A' + art + '-' + m[1];
        const queued = m[5] && /queued/i.test(m[5]) ? 1 : 0;
        (obs[id] = obs[id] || []).push({ record: 'notes', locator: file + ':' + (i + 1), t: num(m[2]), c: num(m[3]), n: num(m[4]), q: queued, qNames: queued ? FAMILIES.filter((f) => m[5].includes(f)) : [] });
      });
    });
  });
}

function fromConductor(obs) {
  if (!fs.existsSync(STATE)) return;
  const st = JSON.parse(fs.readFileSync(STATE, 'utf8'));
  const found = {};
  st.steps.forEach((s) => {
    const t = s.instruction || '';
    let m;
    const re = /(A\d+-F\d+)(?: \(Form A\))?(?: re-centred and ratified| amended)?,? taught (\d+)\/(\d+)\/(\d+)(?:, queue (\d+))?/g;
    while ((m = re.exec(t))) found[m[1]] = { step: s.n, t: num(m[2]), c: num(m[3]), n: num(m[4]), q: m[5] ? num(m[5]) : 0 };
    if ((m = /(A2-F1) declared witness \(taught (\d+), contradicted (\d+), no position (\d+), being confirmed (\d+)\)/.exec(t))) found[m[1]] = { step: s.n, t: num(m[2]), c: num(m[3]), n: num(m[4]), q: num(m[5]) };
  });
  Object.keys(found).forEach((id) => {
    const f = found[id];
    (obs[id] = obs[id] || []).push({ record: 'conductor', locator: path.basename(STATE) + ' step n=' + f.step, t: f.t, c: f.c, n: f.n, q: f.q, qNames: [] });
  });
}

function fromDisclosures(obs) {
  const d = require(path.join(ROOT, 'src/_data/aoidDisclosures.js'));
  const add = (src, file) => src.teachings.forEach((t) => {
    (obs[t.id] = obs[t.id] || []).push({ record: 'disclosure', locator: 'data-sources/aoid/disclosures/' + file + ' (sixteen-family table, ' + t.id + ' column)', t: t.counts.teach, c: t.counts.divided, n: t.counts.none, q: t.counts.confirm, qNames: [] });
  });
  add(d.fatherOfSpirits, 'WoP_AOID2_FatherOfSpirits_Disclosure_Final_20261004.md');
  add(d.sexualHoliness, 'WoP_AOID2_SexualHoliness_Disclosure_Final_20261002.md');
}

// ---- per-family tables (borderline readings, queued families) ----------------------------------
function familyTables() {
  const out = {};
  REPORTS.forEach((file, rank) => {
    const lines = read(path.join(SCRATCH, file));
    let cur = null;
    for (let i = 0; i < lines.length; i++) {
      const h = /^#{2,4}\s+(.*)$/.exec(lines[i]);
      if (h) cur = floorId(h[1]) && /^(A\d+-F\d+|G8)\b/.test(h[1]) ? floorId(h[1]) : null;
      if (cur && /^\|\s*Family\s*\|\s*(Result|Outcome)\s*\|/.test(lines[i])) {
        const rows = [];
        for (let j = i + 2; j < lines.length && /^\|/.test(lines[j]); j++) {
          const c = lines[j].split('|').slice(1, -1).map((x) => x.trim());
          rows.push({ family: c[0], result: c[1] });
        }
        (out[cur] = out[cur] || []).push({ rank, locator: file + ':' + (i + 1), rows });
      }
    }
  });
  return out;
}
function tally(rows) {
  const r = { t: 0, c: 0, n: 0, q: 0, borderline: [], queued: [] };
  rows.forEach((x) => {
    if (/^TEACHES/i.test(x.result)) { r.t++; if (/borderline/i.test(x.result)) r.borderline.push(x.family); }
    else if (/^NO POSITION/i.test(x.result)) r.n++;
    else if (/^(DIFFERS|CONTRADICT)/i.test(x.result)) r.c++;
    else if (/^REVIEW QUEUE/i.test(x.result)) { r.q++; r.queued.push(x.family); }
  });
  return r;
}

// ---- assemble ----------------------------------------------------------------------------------
function build() {
  const ledger = readLedger();
  const obs = {};
  fromReports(obs); fromNotes(obs); fromConductor(obs); fromDisclosures(obs);
  const tables = familyTables();

  const floors = ledger.map((e) => {
    const f = { id: e.id, title: e.title, spans: e.spans, measured: e.scored_on, ...(e.revised_on ? { revised: e.revised_on } : {}), counts: null, status: null, queue: null, queuedFamilies: null, borderline: null, borderlineFamilies: null, ledger: e.result, observations: [] };
    if (e.t === undefined) { f.status = 'UNSCORED'; return f; }
    f.observations.push({ record: 'ledger', locator: LEDGER + ' item ' + e.id, taught: e.t, contradicted: e.c, noPosition: e.n, queue: e.q });
    if (e.withheld) { f.status = 'WITHHELD'; f.withheld = e.withheld; return f; }
    // A record named in the ledger's `superseded_records` is kept for provenance but not compared: a later dated
    // ruling replaced the score it states (AOID2-A2F1-COUNT-RECONCILE).
    const all = (obs[e.id] || []);
    const others = all.filter((o) => !e.superseded.includes(o.record));
    const disagree = [];
    all.forEach((o) => {
      const sup = e.superseded.includes(o.record);
      f.observations.push({ record: o.record, locator: o.locator, taught: o.t, contradicted: o.c, noPosition: o.n, queue: o.q, queuedFamilies: o.qNames && o.qNames.length ? o.qNames : undefined, superseded: sup ? true : undefined });
      if (sup) return;
      const same = o.t === e.t && o.c === e.c && o.n === e.n && (o.q === null || o.q === undefined || o.q === e.q);
      if (!same) disagree.push(o.record);
    });
    if (!others.length) { f.status = 'NO_SECOND_RECORD'; return f; }
    if (disagree.length) { f.status = 'MISMATCH'; f.disagreeing = disagree; return f; }
    f.status = 'MATCH';
    f.counts = { taught: e.t, contradicted: e.c, noPosition: e.n };
    f.queue = e.q;
    const named = others.find((o) => o.qNames && o.qNames.length === e.q && e.q > 0);
    if (e.q === 0) f.queuedFamilies = [];
    else if (named) f.queuedFamilies = named.qNames;
    const cands = (tables[e.id] || []).map((t) => ({ t, y: tally(t.rows) }))
      .filter(({ y }) => y.t === e.t && y.c === e.c && y.n === e.n && y.q === e.q)
      .filter(({ t }) => {
        // A family table counts only if no later record re-scored the floor: it comes from the report that
        // supplied the report-record, or that report's row calls the floor unchanged (and not "strengthened").
        const rep = others.find((o) => o.record === 'report');
        if (!rep) return false;
        if (path.basename(rep.file || '') === t.locator.split(':')[0]) return true;
        return /^unchanged/i.test(rep.status || '') && !/strengthen|moved|rescored|queue closed/i.test(rep.status || '');
      }).sort((a, b) => a.t.rank - b.t.rank);
    if (cands.length) {
      f.borderline = cands[0].y.borderline.length;
      f.borderlineFamilies = cands[0].y.borderline;
      f.tableLocator = cands[0].t.locator;
      if (e.q > 0 && !f.queuedFamilies) f.queuedFamilies = cands[0].y.queued;
    }
    return f;
  });

  return {
    note: 'Generated by scripts/aoid-build-floor-counts.js. Do not edit by hand. Counts appear on the page only for floors whose status is MATCH.',
    source: LEDGER,
    families: 16,
    floors,
  };
}

const text = JSON.stringify(build(), null, 2) + '\n';
if (process.argv.includes('--check')) {
  const cur = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : '';
  if (cur !== text) { console.error('floor_counts.json is stale: rerun scripts/aoid-build-floor-counts.js'); process.exit(1); }
  console.log('floor_counts.json is current');
} else {
  fs.writeFileSync(OUT, text);
  const d = JSON.parse(text);
  const tally2 = {};
  d.floors.forEach((f) => { tally2[f.status] = (tally2[f.status] || 0) + 1; });
  console.log('wrote', path.relative(ROOT, OUT), JSON.stringify(tally2));
}
