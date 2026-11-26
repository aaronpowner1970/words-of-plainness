/* ============================================================
   BLOCKED-STORAGE MESSAGE (SITE step 81, CODE-SITE-41)
   Rulings SITE-STORAGE-BLOCKED-MESSAGE option 1 (20 Nov 2026) and
   SITE-BLOCKED-MSG-APPROACHES option 3 (25 Nov 2026).

   Template name:  storageBlocked
   Shown only when a reader's browser blocks storage (window.wopStorage.available()
   is false). With storage working nothing here reaches the reader: the pages carry
   only a one-line loader in <head> (layouts/base.njk) that does nothing unless
   storage is blocked.

   Every reader-visible word comes from the approved-wording file, read at build
   time and never retyped: data-sources/site/ holds a copy of
   wop-scratch/WoP_SITE_BlockedStorage_Wording_Approved_20261120.md (W1-W7 and the
   condition on W5's browser lines). The build stops if a section is missing.

   W5's browser lines: a step is shown only where the browser maker's own current
   help page states it in substance (checked 26 Nov 2026, CODE-SITE-41; see the
   report). Where it could not be confirmed the file's condition applies: the step is
   replaced by "See your browser’s help page" with the official link.
   ============================================================ */

const fs = require('fs');
const path = require('path');

const WORDING = 'data-sources/site/WoP_SITE_BlockedStorage_Wording_Approved_20261120.md';

// The places (layouts, and pages by address) that load the blocked-storage script.
const LAYOUTS = ['layouts/chapter.njk', 'layouts/interactive-chapter.njk', 'layouts/card-chapter.njk',
    'layouts/articles.njk', 'layouts/sjn.njk'];
const URLS = ['/my-reflections/', '/studies/approaches-to-belief/'];

// W5 browser lines, in the file's order. `confirmed` records the check of 26 Nov 2026
// (CODE-SITE-41): Chrome's step is stated on support.google.com/chrome/answer/114662, but
// Microsoft's own Edge help states no address-bar route for site data, so the shared
// "Chrome or Edge" line takes the fallback; Firefox's lock route is stated
// (kb/block-websites-storing-cookies-site-data-firefox) but its shield route is not said
// to let a site keep data, so that line takes the fallback; Safari's toggle is stated on
// support.apple.com/en-us/105082 and the Mac "Enable cookies" page.
const LINES = [
    { label: 'Chrome or Edge:', confirmed: false, links: [
        { w6: 'Chrome help', href: 'https://support.google.com/chrome/answer/95647' },
        { w6: 'Edge help', href: 'https://support.microsoft.com/en-us/edge/manage-cookies-in-microsoft-edge-view-allow-block-delete-and-use' }] },
    { label: 'Safari (iPhone, iPad or Mac):', confirmed: true, links: [
        { w6: 'Safari help', href: 'https://support.apple.com/en-us/105082' }] },
    { label: 'Firefox:', confirmed: false, links: [
        { w6: 'Firefox help', href: 'https://support.mozilla.org/en-US/kb/storage' }] },
    { label: 'Opened from Facebook, Instagram or another app?', confirmed: true, links: [] }
];

function fail(msg) { throw new Error('blocked-storage wording (' + WORDING + '): ' + msg); }

const src = fs.readFileSync(path.join(process.cwd(), WORDING), 'utf8').replace(/\r\n/g, '\n');
const lines = src.split('\n');

function section(re) {
    const i = lines.findIndex((l) => re.test(l));
    if (i < 0) fail('section not found: ' + re);
    let j = i + 1;
    while (j < lines.length && !/^#{1,2} /.test(lines[j])) j++;
    return lines.slice(i + 1, j).filter((l) => l.trim() !== '');
}
function one(arr, what) {
    if (arr.length !== 1) fail('expected exactly one ' + what + ', found ' + arr.length);
    return arr[0];
}
function prefixed(arr, prefix, what) {
    return one(arr.filter((l) => l.startsWith(prefix)), what).slice(prefix.length);
}

const w1 = one(section(/^## W1\. /), 'W1 sentence');
const w2 = section(/^## W2\. /);
if (w2.length !== 2) fail('W2: expected two button labels');
const w3 = one(section(/^## W3\. /), 'W3 heading');
const w4 = one(section(/^## W4\. /), 'W4 sentence');

const w5 = section(/^## W5\. /);
const summary = prefixed(w5, 'Summary (the toggle): ', 'W5 summary');
const bodyAt = w5.indexOf('Body:');
if (bodyAt < 0) fail('W5 body not found');
const w5body = w5.slice(bodyAt + 1);
const intro = w5body[0];
const bullets = w5body.filter((l) => l.startsWith('- '));
const warning = one(w5body.filter((l) => l.startsWith('**Before ')), 'W5 reload warning');
if (bullets.length !== LINES.length) fail('W5: expected ' + LINES.length + ' browser lines, found ' + bullets.length);

const condition = section(/^## Condition on W5/).join(' ');
const fb = /show only "([^"]+)"/.exec(condition);
if (!fb) fail('the fallback sentence in the condition on W5 was not found');

const w6 = section(/^## W6\. /);
const w7 = one(section(/^## W7\. /).slice(0, 1), 'W7 confirmation');

// "**Bold:** rest" → { bold, rest }
function splitBold(s, what) {
    const m = /^\*\*(.+?)\*\*(.*)$/.exec(s);
    if (!m) fail(what + ': no bold lead');
    return { bold: m[1], rest: m[2] };
}

const browserLines = bullets.map((b, i) => {
    const cfg = LINES[i];
    const parts = splitBold(b.slice(2), 'W5 line ' + (i + 1));
    if (parts.bold !== cfg.label) fail('W5 line ' + (i + 1) + ' reads "' + parts.bold + '", expected "' + cfg.label + '"');
    cfg.links.forEach((l) => { if (w6.indexOf(l.w6) < 0) fail('W6 label not in the file: ' + l.w6); });
    return {
        label: parts.bold,
        step: parts.rest,                    // begins with a space, as in the file
        confirmed: cfg.confirmed,
        links: cfg.links.map((l) => ({ text: l.w6, href: l.href }))
    };
});
const warn = splitBold(warning, 'W5 reload warning');

module.exports = {
    source: WORDING,
    layouts: LAYOUTS,
    urls: URLS,
    words: {
        w1: w1,
        copy: w2[0],
        download: w2[1],
        w3: w3,
        w4: w4,
        summary: summary,
        intro: intro,
        lines: browserLines,
        fallback: fb[1],
        warningBold: warn.bold,
        warningRest: warn.rest,
        copied: w7
    }
};
