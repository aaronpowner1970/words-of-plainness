// Playwright check for the /about/ narration (Phase 4). Run through the Playwright MCP's
// browser_run_code_unsafe with `filename`, after setting globalThis.NARR_BASE and NARR_SHOTS:
//   NARR_BASE = 'https://www.wordsofplainness.org'   NARR_SHOTS = '<folder for screenshots>'
// Verifies against src/_data/about_narration_timing.json (read from disk) at 1440 and 390 widths.
async (page) => {
    // globalThis does not persist between MCP calls: edit these two lines to retarget (e.g. http://localhost:8085).
    const BASE = 'https://www.wordsofplainness.org';
    const SHOTS = 'C:/Users/aaron/AppData/Local/Temp/claude/C--Users-aaron--claude-spares-spare-ghUcN9/f1f0090a-4b88-49be-b0c6-860d157959a8/scratchpad';
    const jp = await page.context().newPage();   // read the repo's timing JSON straight from disk (no require here)
    await jp.goto('file:///C:/Users/aaron/Documents/words-of-plainness/src/_data/about_narration_timing.json');
    const timing = JSON.parse(await jp.evaluate(() => document.body.innerText)).targets;
    await jp.close();
    const ids = Object.keys(timing);
    const expectAt = (t) => { let r = null; for (const id of ids) if (timing[id].start <= t) r = id; return r; };
    const results = {};

    for (const [label, w, h] of [['desktop1440', 1440, 900], ['mobile390', 390, 844]]) {
        const R = results[label] = { checks: {}, failures: [] };
        const ok = (name, cond, extra) => { R.checks[name] = cond ? 'PASS' : 'FAIL' + (extra ? ' ' + JSON.stringify(extra) : ''); if (!cond) R.failures.push(name); };
        const errors = [];
        page.removeAllListeners('console'); page.removeAllListeners('pageerror');
        page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
        page.on('pageerror', e => errors.push('pageerror: ' + e.message));
        await page.setViewportSize({ width: w, height: h });
        await page.evaluate(() => { try { localStorage.removeItem('wop-about-narration-v1'); } catch (_) {} }).catch(() => {});
        await page.goto(BASE + '/about/', { waitUntil: 'load' });
        await page.evaluate(() => { try { localStorage.removeItem('wop-about-narration-v1'); } catch (_) {} });
        await page.reload({ waitUntil: 'load' });

        // 1. nothing plays by default
        await page.waitForTimeout(1500);
        const idle = await page.evaluate(() => { const v = document.querySelector('.narr-player video'); return { paused: v.paused, src: v.getAttribute('src'), hidden: document.querySelector('.narr-player').hidden }; });
        ok('loads with nothing playing', idle.paused && !idle.src && idle.hidden, idle);

        // 2. button starts narration
        await page.locator('#narrEntry').click();
        await page.waitForFunction(() => { const v = document.querySelector('.narr-player video'); return !v.paused && v.currentTime > 0.5; }, null, { timeout: 30000 });
        const src = await page.evaluate(() => document.querySelector('.narr-player video').getAttribute('src'));
        ok('button starts narration', true);
        ok('rendition by width', src.endsWith(w <= 768 ? '320x180.mp4' : '480x270.mp4'), src);
        if (SHOTS) await page.screenshot({ path: `${SHOTS}/${label}-start.png` });

        // 3. five sampled times, incl. one in each aside
        const samples = [30, 141, 222.5, 404, 480];
        const sampled = [];
        for (const t of samples) {
            await page.evaluate((t) => { document.querySelector('.narr-player video').currentTime = t; }, t);
            await page.waitForFunction((t) => Math.abs(document.querySelector('.narr-player video').currentTime - t) < 3, t);
            await page.waitForTimeout(900);
            const got = await page.evaluate(() => { const a = document.querySelector('.narr.is-active'); return a && a.dataset.narr; });
            const vt = await page.evaluate(() => document.querySelector('.narr-player video').currentTime);
            sampled.push({ t, actualT: +vt.toFixed(2), got, expected: expectAt(vt) });
        }
        ok('highlight matches timing JSON at 5 times (incl. both asides)', sampled.every(s => s.got === s.expected), sampled);
        R.sampled = sampled;
        // asides highlight the figcaptions
        ok('collage aside -> #throwback-collage figcaption', sampled[1].got === 'collage-cap');
        ok('workspace aside -> #rv-workspace figcaption', sampled[3].got === 'workspace-cap');
        const capParent = await page.evaluate(() => [!!document.querySelector('#throwback-collage figcaption [data-narr="collage-cap"]'), !!document.querySelector('#rv-workspace figcaption [data-narr="workspace-cap"]')]);
        ok('caption targets sit inside the figcaptions', capParent[0] && capParent[1], capParent);

        // active target is in view, and clear of the docked player (mobile)
        const geo = await page.evaluate(() => {
            const a = document.querySelector('.narr.is-active').getBoundingClientRect();
            const p = document.querySelector('.narr-player').getBoundingClientRect();
            return { aTop: a.top, aBottom: a.bottom, pTop: p.top, pBottom: p.bottom, vh: innerHeight, layout: document.querySelector('.narr-player').dataset.layout };
        });
        ok('active target visible', geo.aBottom > 0 && geo.aTop < geo.vh, geo);
        if (geo.layout === 'dock') ok('mobile dock does not cover active target', geo.aBottom <= geo.pTop + 1 && geo.aTop >= 0, geo);
        if (SHOTS) await page.screenshot({ path: `${SHOTS}/${label}-aside.png` });

        // 4. click-to-seek; links do not seek; selecting text does not seek
        await page.evaluate(() => document.querySelector('.narr-player video').pause());
        const pt = await page.evaluate(() => { const el = document.querySelector('[data-narr="phil-p2-s2"]'); el.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = el.getClientRects()[0]; return { x: r.left + Math.min(20, r.width / 2), y: r.top + r.height / 2 }; });
        await page.mouse.click(pt.x, pt.y);
        await page.waitForTimeout(700);
        let t1 = await page.evaluate(() => document.querySelector('.narr-player video').currentTime);
        ok('click seeks to target start', Math.abs(t1 - timing['phil-p2-s2'].start) < 1.2, { t1, want: timing['phil-p2-s2'].start });
        const before = t1;
        await page.evaluate(() => { const a = document.querySelector('[data-narr="bio-p3-s5"] a'); a.addEventListener('click', e => e.preventDefault(), { once: true }); });
        await page.locator('[data-narr="bio-p3-s5"] a').click();
        await page.waitForTimeout(400);
        const t2 = await page.evaluate(() => document.querySelector('.narr-player video').currentTime);
        ok('link inside a target does not seek', t2 >= before - 0.2 && t2 < before + 3, { before, t2 });

        // 5. manual scroll -> pill; pill resumes
        await page.evaluate(() => document.querySelector('.narr-player video').play());
        await page.mouse.move(w / 2, h / 2);
        await page.mouse.wheel(0, 600);
        await page.waitForTimeout(500);
        const pillShown = await page.evaluate(() => !document.querySelector('.narr-pill').hidden);
        ok('manual scroll shows Return pill', pillShown);
        if (SHOTS) await page.screenshot({ path: `${SHOTS}/${label}-pill.png` });
        await page.waitForTimeout(3500);   // stays suspended while the narration advances
        const stillAway = await page.evaluate(() => { const a = document.querySelector('.narr.is-active').getBoundingClientRect(); return { top: a.top, vh: innerHeight, pill: !document.querySelector('.narr-pill').hidden }; });
        ok('auto-scroll stays suspended', stillAway.pill, stillAway);
        await page.locator('.narr-pill').click();
        await page.waitForTimeout(1500);
        const back = await page.evaluate(() => { const a = document.querySelector('.narr.is-active').getBoundingClientRect(); return { top: a.top, bottom: a.bottom, vh: innerHeight, pillHidden: document.querySelector('.narr-pill').hidden }; });
        ok('pill resumes and brings active target into view', back.pillHidden && back.bottom > 0 && back.top < back.vh, back);

        // 6. close and resume preserve position
        const tClose = await page.evaluate(() => document.querySelector('.narr-player video').currentTime);
        await page.keyboard.press('Escape');
        await page.waitForTimeout(300);
        const closedState = await page.evaluate(() => ({ hidden: document.querySelector('.narr-player').hidden, paused: document.querySelector('.narr-player video').paused }));
        ok('Escape closes and pauses', closedState.hidden && closedState.paused, closedState);
        await page.locator('#narrEntry').scrollIntoViewIfNeeded();
        await page.locator('#narrEntry').click();
        await page.waitForTimeout(1200);
        const tResume = await page.evaluate(() => document.querySelector('.narr-player video').currentTime);
        ok('resume keeps position', tResume >= tClose - 0.5 && tResume < tClose + 4, { tClose, tResume });
        // reload also restores the position (stored time), still nothing auto-plays
        await page.evaluate(() => document.querySelector('.narr-player video').pause());
        await page.waitForTimeout(300);
        await page.reload({ waitUntil: 'load' });
        await page.waitForTimeout(800);
        const afterReload = await page.evaluate(() => ({ paused: document.querySelector('.narr-player video').paused, label: document.querySelector('.narr-entry__label').textContent }));
        ok('reload: not playing, offers resume', afterReload.paused && /Resume/.test(afterReload.label), afterReload);

        // 7. end state
        await page.locator('#narrEntry').click();
        await page.waitForFunction(() => !document.querySelector('.narr-player video').paused, null, { timeout: 30000 });
        await page.evaluate(() => { document.querySelector('.narr-player video').currentTime = 490.2; });
        await page.waitForTimeout(5500);
        const end = await page.evaluate(() => ({ min: document.querySelector('.narr-player').dataset.min, active: document.querySelectorAll('.narr.is-active').length, paused: document.querySelector('.narr-player video').paused, label: document.querySelector('.narr-entry__label').textContent }));
        ok('end: highlight faded, player collapsed', end.min === 'true' && end.active === 0 && end.paused && /again/.test(end.label), end);
        if (SHOTS) await page.screenshot({ path: `${SHOTS}/${label}-end.png` });

        ok('no console errors', errors.length === 0, errors.slice(0, 5));
    }
    return results;
}
