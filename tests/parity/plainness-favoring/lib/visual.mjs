// Visual structure checks (run in the page) and image-pair comparison (run in Node).
import fs from 'node:fs';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

export const WIDTHS = [
  { width: 1440, height: 900 },
  { width: 1024, height: 768 },
  { width: 768, height: 1024 },
  { width: 480, height: 854 },
  { width: 375, height: 812 },
];

// Key elements per view, in the order they should appear.
export const KEY_ELEMENTS = {
  read: ['.tl-tabs', '.tl-working-panel', '#modeTitle', '#readAloud', '#sceneTitle', '.tl-poem-area h2', '.tl-byline', '#plainPoem', '.tl-read-thesis', '.tl-read-actions', '#coachPanel', '.tl-commentary'],
  grid: ['.tl-tabs', '.tl-working-panel', '#modeTitle', '.tl-display-switch', '#grids', '#undoGrid', '#gridStartCustom', '#coachPanel', '#pathRule'],
  cube: ['.tl-tabs', '.tl-working-panel', '#modeTitle', '#cubeFilmOpen', '#cube', '.tl-camera-row', '.tl-camera-settings', '#undoViewer', '#coachPanel'],
  recursion: ['.tl-tabs', '.tl-working-panel', '#modeTitle', '#stanzaReflection', '#beforeNote', '#lenses', '#afterNote', '#fitScore', '#exploreAnotherRoute', '#coachPanel'],
  lesson: ['.tl-tabs', '.tl-working-panel', '#lessonTitle', '#lessonMenu', '#lessonBody', '#lessonNext', '#lessonExport'],
};

// Groups that must not overlap, and (below 768 px) the B62 single rows.
export const ROW_GROUPS = {
  tabs: '.tl-tabs > *',
  views: '.tl-display-switch > *',
  lenses: '#lenses > .tl-lens',
  camera: '.tl-camera-row > button',
  cameraSettings: '.tl-camera-settings > *',
  editGrid: '#gridMode .tl-path-edit-row > button',
  editCube: '#cubeMode .tl-path-edit-row > button',
  editRecursion: '#recursionMode .tl-path-edit-row > button',
  readActions: '#readMode .tl-read-actions > button',
};

export function structureInPage({ keys, groups, excused, siteHeader }) {
  const vis = e => !!e && !e.closest('[hidden]') && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none';
  const R = e => { const r = e.getBoundingClientRect(); return { x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  const isExcused = e => excused.some(sel => { try { return e.closest(sel); } catch { return false; } });
  const out = { missing: [], hidden: [], orderOk: true, overlaps: [], rows: {}, rects: {} };
  const found = [];
  for (const sel of keys) {
    const e = document.querySelector(sel);
    if (!e) { out.missing.push(sel); continue; }
    if (!vis(e)) { out.hidden.push(sel); continue; }
    found.push([sel, e]);
    out.rects[sel] = R(e);
  }
  for (let i = 1; i < found.length; i++) {
    if (!(found[i - 1][1].compareDocumentPosition(found[i][1]) & Node.DOCUMENT_POSITION_FOLLOWING)) { out.orderOk = false; out.orderBreak = found[i - 1][0] + ' !< ' + found[i][0]; }
  }
  for (const [name, sel] of Object.entries(groups)) {
    const items = Array.from(document.querySelectorAll(sel)).filter(vis).filter(e => !isExcused(e));
    if (!items.length) continue;
    const rects = items.map(e => e.getBoundingClientRect());
    for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left), iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ix > 1 && iy > 1) out.overlaps.push(name + ': ' + (items[i].id || items[i].textContent.trim().slice(0, 20)) + ' × ' + (items[j].id || items[j].textContent.trim().slice(0, 20)));
    }
    const tops = rects.map(r => r.top), bottoms = rects.map(r => r.bottom);
    out.rows[name] = { count: items.length, oneRow: Math.max(...tops) < Math.min(...bottoms), top: Math.round(Math.min(...tops) + scrollY), bottom: Math.round(Math.max(...bottoms) + scrollY) };
  }
  const de = document.documentElement;
  out.hScroll = de.scrollWidth > de.clientWidth + 1;
  out.scrollWidth = de.scrollWidth;
  out.clientWidth = de.clientWidth;
  // Inner scrollbars in the workspace or the guide (B25).
  out.innerScroll = ['.tl-workbench', '.tl-right', '#coachPanel', '#pathList', '.tl-working-panel'].filter(sel => {
    const e = document.querySelector(sel);
    if (!e || !vis(e)) return false;
    const oy = getComputedStyle(e).overflowY;
    return (oy === 'auto' || oy === 'scroll') && e.scrollHeight > e.clientHeight + 1;
  });
  const panel = document.querySelector('.tl-working-panel'), guide = document.querySelector('.tl-right');
  out.panelPosition = panel ? getComputedStyle(panel).position : null;
  out.guideBelowPanel = panel && guide ? guide.getBoundingClientRect().top >= panel.getBoundingClientRect().bottom - 1 : null;
  out.guideBesidePanel = panel && guide ? guide.getBoundingClientRect().left >= panel.getBoundingClientRect().right - 1 : null;
  // Nothing under the site header: scroll, then the sticky tabs must sit at or below its bottom edge.
  const tabs = document.querySelector('.tl-tabs');
  const header = siteHeader ? document.querySelector(siteHeader) : null;
  out.tabsPosition = tabs ? getComputedStyle(tabs).position : null;
  out.siteHeaderFound = !!header;
  return out;
}

export function stickyAfterScrollInPage({ siteHeader }) {
  const tabs = document.querySelector('.tl-tabs');
  const header = siteHeader ? document.querySelector(siteHeader) : null;
  const headerBottom = header && ['fixed', 'sticky'].includes(getComputedStyle(header).position) ? header.getBoundingClientRect().bottom : 0;
  const t = tabs ? tabs.getBoundingClientRect().top : null;
  return { tabsTop: t === null ? null : Math.round(t), headerBottom: Math.round(headerBottom), clear: t === null ? null : t >= headerBottom - 1 };
}

// Pixel comparison of an image pair. Reported, never failed (D12, D13 change glyphs).
export function imagePair(refFile, candFile, diffFile) {
  const a = PNG.sync.read(fs.readFileSync(refFile)), b = PNG.sync.read(fs.readFileSync(candFile));
  const w = Math.min(a.width, b.width), h = Math.min(a.height, b.height);
  const crop = (img) => { if (img.width === w && img.height === h) return img.data; const out = Buffer.alloc(w * h * 4); for (let y = 0; y < h; y++) img.data.copy(out, y * w * 4, y * img.width * 4, y * img.width * 4 + w * 4); return out; };
  const diff = new PNG({ width: w, height: h });
  const changed = pixelmatch(crop(a), crop(b), diff.data, w, h, { threshold: 0.1 });
  fs.writeFileSync(diffFile, PNG.sync.write(diff));
  return { reference: [a.width, a.height], candidate: [b.width, b.height], comparedArea: [w, h], changedPixels: changed, changedRatio: +(changed / (w * h)).toFixed(5) };
}
