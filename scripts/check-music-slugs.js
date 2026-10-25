#!/usr/bin/env node
// Collision check for the shareable song links on the built site (_site/).
//   #listen=<slug>  -> data-listen-slug / data-listen-file anchors
//   #watch=<slug>   -> data-watch-slug (space-separated) / data-youtube-id buttons
// Fails (exit 1) when one slug maps to two different files (or two videos), either
// within a page or anywhere across the site, or when a page repeats an element id
// from the listen anchors. Run after a build: node scripts/check-music-slugs.js
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', '_site');
const listen = new Map();   // slug -> Map(file -> Set(pages))
const watch = new Map();    // slug -> Map(videoId -> Set(pages))
const problems = [];

function note(map, slug, val, page) {
    if (!map.has(slug)) map.set(slug, new Map());
    const m = map.get(slug);
    if (!m.has(val)) m.set(val, new Set());
    m.get(val).add(page);
}

function walk(dir) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) walk(p);
        else if (e.name.endsWith('.html')) scan(p);
    }
}

function scan(file) {
    const page = '/' + path.relative(root, file).split(path.sep).join('/').replace(/index\.html$/, '');
    const html = fs.readFileSync(file, 'utf8');
    const ids = new Map();
    for (const m of html.matchAll(/<span class="listen-anchor" id="([^"]+)" data-listen-slug="([^"]+)" data-listen-file="([^"]+)"/g)) {
        ids.set(m[1], (ids.get(m[1]) || 0) + 1);
        note(listen, m[2], m[3], page);
    }
    for (const [id, n] of ids) if (n > 1) problems.push(`duplicate listen anchor id "${id}" x${n} on ${page}`);
    for (const m of html.matchAll(/<button[^>]*data-action="watch"[^>]*>/g)) {
        const id = /data-youtube-id="([^"]+)"/.exec(m[0]);
        const slugs = /data-watch-slug="([^"]+)"/.exec(m[0]);
        if (!id || !slugs) continue;
        slugs[1].split(' ').forEach(s => note(watch, s, id[1], page));
    }
}

walk(root);
let nL = 0, nW = 0;
for (const [kind, map] of [['listen', listen], ['watch', watch]]) {
    for (const [slug, vals] of map) {
        if (kind === 'listen') nL++; else nW++;
        if (vals.size > 1) {
            problems.push(`#${kind}=${slug} maps to ${vals.size} targets: ` +
                [...vals].map(([v, pages]) => `${v} (${[...pages].join(', ')})`).join(' | '));
        }
    }
}
console.log(`listen slugs: ${nL}, watch slugs: ${nW}`);
if (problems.length) {
    console.error(problems.join('\n'));
    process.exit(1);
}
console.log('no slug collisions');
