// Build-time guard for the /about/ narration: the {% narr "id" %} targets in
// src/pages/about.njk and the IDs in src/_data/about_narration_timing.json must
// be the same set, in the same order, with sane times. Runs as part of `prebuild`.
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const page = fs.readFileSync(path.join(root, 'src/pages/about.njk'), 'utf8');
const timing = JSON.parse(fs.readFileSync(path.join(root, 'src/_data/about_narration_timing.json'), 'utf8'));

const problems = [];
const pageIds = [...page.matchAll(/\{%\s*narr\s+"([^"]+)"\s*%\}/g)].map(m => m[1]);
const timingIds = Object.keys(timing.targets);

const dupes = pageIds.filter((id, i) => pageIds.indexOf(id) !== i);
if (dupes.length) problems.push('duplicate IDs in about.njk: ' + dupes.join(', '));

const missingTiming = pageIds.filter(id => !timing.targets[id]);
const orphanTiming = timingIds.filter(id => !pageIds.includes(id));
if (missingTiming.length) problems.push('in about.njk but no timing: ' + missingTiming.join(', '));
if (orphanTiming.length) problems.push('timing but not in about.njk: ' + orphanTiming.join(', '));

if (!missingTiming.length && !orphanTiming.length && pageIds.join('|') !== timingIds.join('|')) {
    problems.push('IDs match but page order differs from timing order');
}

let prevStart = -1;
for (const id of timingIds) {
    const t = timing.targets[id];
    if (!(t.end > t.start)) problems.push(`${id}: end <= start`);
    if (t.start < prevStart) problems.push(`${id}: starts before the previous target`);
    if (t.end > timing.meta.duration) problems.push(`${id}: ends after media duration`);
    prevStart = t.start;
}

if (problems.length) {
    console.error('check-narration-ids FAILED:\n  ' + problems.join('\n  '));
    process.exit(1);
}
console.log(`check-narration-ids ok: ${pageIds.length} narrated targets match about_narration_timing.json`);
