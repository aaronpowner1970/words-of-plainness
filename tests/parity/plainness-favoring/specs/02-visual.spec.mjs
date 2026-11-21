// Section 5.2 (2) Visual at five widths, for each tab and the lesson: structure checks (fail) and
// image pairs (reported, never failed: D12 and D13 change glyphs).
import fs from 'node:fs';
import path from 'node:path';
import { scenario } from '../lib/harness.mjs';
import { writeJson } from '../lib/config.mjs';
import { loadDmap } from '../lib/dmap.mjs';
import { WIDTHS, KEY_ELEMENTS, ROW_GROUPS, structureInPage, stickyAfterScrollInPage, imagePair } from '../lib/visual.mjs';

const VIEWS = ['read', 'grid', 'cube', 'recursion', 'lesson'];

function excusedSelectors(side) {
  return loadDmap().selectors.filter(s => s.side === side || s.side === 'both').map(s => s.selector);
}
function siteHeaderSelector(side) {
  const h = loadDmap().selectors.find(s => s.role === 'siteHeader');
  return side === 'candidate' && h ? h.selector : null;
}

async function goView(d, view) {
  if (view === 'lesson') {
    await d.tab('read'); await d.settle();
    await d.click('#lessonStart'); await d.settle();
    await d.click('#lessonNext'); await d.settle(300);
  } else {
    await d.tab(view); await d.settle(view === 'cube' ? 350 : 200);
  }
  await d.page.evaluate(() => window.scrollTo(0, 0));
  await d.settle(100);
}

for (const vp of WIDTHS) {
  scenario('visual', `V-${vp.width}`, { b: ['B5', 'B6', 'B9', 'B25', 'B55', 'B62'], viewport: vp, timeout: 240000,
    after: async ({ obs, dir, cfg }) => {
      if (!obs.candidate) return;
      const pairs = {};
      for (const view of VIEWS) {
        const r = path.join(dir, 'reference', view + '.png'), c = path.join(dir, 'candidate', view + '.png');
        if (fs.existsSync(r) && fs.existsSync(c)) pairs[view] = imagePair(r, c, path.join(dir, view + '.diff.png'));
      }
      writeJson(path.join(dir, 'image-pairs.json'), { note: 'Reported, not failed (D12, D13).', width: vp.width, pairs });
    } }, async (d, { side }) => {
    await d.open();
    const rects = {};
    for (const view of VIEWS) {
      await goView(d, view);
      await d.screenshot(view, { fullPage: true });
      const st = await d.page.evaluate(structureInPage, { keys: KEY_ELEMENTS[view], groups: ROW_GROUPS, excused: excusedSelectors(side), siteHeader: siteHeaderSelector(side) });
      let sticky = null;
      if (vp.width >= 768) {
        await d.page.evaluate(() => window.scrollTo(0, 700));
        await d.settle(120);
        sticky = await d.page.evaluate(stickyAfterScrollInPage, { siteHeader: siteHeaderSelector(side) });
        await d.page.evaluate(() => window.scrollTo(0, 0));
        await d.settle(60);
      }
      rects[view] = { rects: st.rects, rows: st.rows, scrollWidth: st.scrollWidth, clientWidth: st.clientWidth, sticky };
      const stacked = await d.page.evaluate(() => ({ read: !!document.querySelector('#plainPoem.tl-stacked'), lesson: !!document.querySelector('#lessonBody.tl-stacked'), panel: !!document.querySelector('#contextText.tl-stacked'), panelShown: !document.querySelector('#poemContext').hidden }));
      // Only booleans and names are compared between the two sides; positions differ with fonts.
      const rec = d.record('structure-' + view, {
        missing: st.missing.join(' '), hidden: st.hidden.join(' '), orderOk: st.orderOk, orderBreak: st.orderBreak || '',
        overlaps: st.overlaps.join(' | '), hScroll: st.hScroll, innerScroll: st.innerScroll.join(' '),
        rowsOneRow: Object.entries(st.rows).map(([k, v]) => k + '=' + v.oneRow).join(' '),
        panelPosition: st.panelPosition, guideBelowPanel: st.guideBelowPanel, guideBesidePanel: st.guideBesidePanel,
        tabsPosition: st.tabsPosition, stickyClear: sticky ? sticky.clear : null, stacked,
      });
      d.check('B5', !st.missing.length && st.orderOk, `${vp.width}px ${view}: key elements present and in order`, { missing: rec.missing, hidden: rec.hidden, orderBreak: rec.orderBreak });
      d.check('B5', !st.overlaps.length, `${vp.width}px ${view}: no overlaps among controls`, rec.overlaps);
      d.check('B5', !st.hScroll, `${vp.width}px ${view}: no horizontal scroll`, { scrollWidth: st.scrollWidth, clientWidth: st.clientWidth });
      d.check('B25', !st.innerScroll.length, `${vp.width}px ${view}: no separate scrollbars in the workspace or guide`, rec.innerScroll);
      if (vp.width >= 768) d.check('B25', sticky && sticky.clear, `${vp.width}px ${view}: sticky tabs stay clear of any fixed header after scrolling`, sticky);
      if (vp.width >= 768) d.check('B25', st.guideBesidePanel === true && st.panelPosition === 'sticky', `${vp.width}px ${view}: guide beside the working panel, which stays in place (sticky)`, { beside: st.guideBesidePanel, position: st.panelPosition });
      if (vp.width < 768) d.check('B25', st.guideBelowPanel === true, `${vp.width}px ${view}: guide stacked below the working panel`, { below: st.guideBelowPanel });
      if (view === 'read') d.check('B9', vp.width >= 1200 ? stacked.read === false : vp.width <= 480 ? stacked.read === true : true, `${vp.width}px: verse stacking (full lines when wide, stacked phrases when narrow; 768-1199 px depends on the panel width and font, recorded only)`, stacked);
      if (view === 'lesson') d.check('B55', vp.width >= 768 ? stacked.panelShown === true : stacked.panelShown === false, `${vp.width}px: whole-poem panel opens automatically on Line 1 on desktop only`, stacked);
      if (vp.width < 768) {
        const rows = st.rows;
        const need = { read: ['tabs'], grid: ['tabs', 'views', 'editGrid'], cube: ['tabs', 'camera', 'cameraSettings', 'editCube'], recursion: ['tabs', 'lenses', 'editRecursion'], lesson: [] }[view];
        for (const g of need) d.check('B62', rows[g] && rows[g].oneRow, `${vp.width}px ${view}: ${g} on one row`, rows[g] || 'not visible');
        if (view === 'cube' && rows.camera && rows.cameraSettings && rows.editCube) {
          d.check('B62', rows.cameraSettings.top >= rows.camera.bottom - 1 && rows.editCube.top >= rows.cameraSettings.bottom - 1, `${vp.width}px cube: Focus row below the camera row, Undo/Redo/Clear on their own row below it`, { camera: rows.camera, settings: rows.cameraSettings, edit: rows.editCube });
        }
      }
    }
    writeJson(d.file('layout-rects.json'), rects);
  });
}

// Reduced motion and coarse pointer (B64).
scenario('visual', 'V-motion-pointer', { b: ['B64'], reducedMotion: 'reduce', hasTouch: true, viewport: { width: 768, height: 1024 } }, async d => {
  await d.open();
  await d.click('#lessonStart'); await d.settle();
  await d.click('#lessonNext'); await d.settle(300);
  const r = d.record('motion-pointer', await d.page.evaluate(() => ({
    reduce: matchMedia('(prefers-reduced-motion: reduce)').matches,
    coarse: matchMedia('(pointer: coarse)').matches,
    btnTransition: getComputedStyle(document.querySelector('#tool-root .tl-btn')).transitionDuration,
    scrollBehavior: getComputedStyle(document.querySelector('#tool-root .tl-btn')).scrollBehavior,
    panelLineMinHeight: (b => (b ? getComputedStyle(b).minHeight : null))(document.querySelector('#contextText button')),
  })));
  d.check('B64', r.reduce && /^0s(, 0s)*$/.test(r.btnTransition), 'reduced-motion rule removes transitions', r);
  d.check('B64', !r.coarse || r.panelLineMinHeight === '44px', 'coarse-pointer rule: 44 px panel lines (only checkable where the browser reports a coarse pointer)', r);
});
