// Section 5.2 (7) Console and network: no console errors; no request from any reader action;
// page-load hosts within the allow-list. Every scenario in the suite also records its requests
// by phase, and the run summary totals them; this scenario walks every kind of reader action.
import { scenario } from '../lib/harness.mjs';
import { buildGoldRoute, fillRecursion, fillLesson, generate, rule, cell } from '../lib/flows.mjs';
import { classifyRequests } from '../lib/dmap.mjs';
import { getConfig } from '../lib/config.mjs';

scenario('network', 'N01-every-reader-action', { b: ['NET'], timeout: 240000 }, async (d, { side }) => {
  await d.open();
  const act = async (label, fn) => { d.phase = 'action:' + label; await fn(); await d.settle(150); };
  await act('tabs', async () => { for (const m of ['grid', 'cube', 'recursion', 'read']) await d.tab(m); });
  await act('read-aloud', async () => { await d.click('#readAloud'); await d.page.waitForTimeout(500); await d.click('#readAloud'); });
  await act('play-from-line', async () => { await d.page.locator('#plainPoem p').nth(3).click(); await d.page.waitForTimeout(400); await d.click('#readAloud'); });
  await act('copy', () => d.click('#copyPoem'));
  await act('generate', async () => { for (const r of ['curated', 'open', 'geometry', 'strict', 'free']) { await rule(d, r); await generate(d); } await rule(d, 'curated'); });
  await act('pick-nodes', () => buildGoldRoute(d));
  await act('canvas', async () => { await d.tab('cube'); await d.settle(200); const b = await d.page.locator('#cube').boundingBox(); await d.page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); for (const id of ['#frontCamera', '#topCamera', '#explode', '#resetCamera']) await d.click(id); });
  await act('film', async () => { await d.click('#cubeFilmOpen'); await d.page.waitForTimeout(300); await d.click('#cubeFilmClose'); });
  await act('writing', async () => { await d.tab('recursion'); await fillRecursion(d); });
  await act('export-pathway', () => d.download('net-pathway-export', () => d.click('#recursionExport')));
  await act('print-pathway', () => d.print('net-pathway-print', () => d.click('#recursionPrint')));
  await act('print-poem', async () => { await d.tab('read'); await d.print('net-poem-print', () => d.click('#printPoem')); });
  await act('lesson-writing-saving', async () => { await fillLesson(d); });
  await act('line-clip', async () => { await d.select('#lessonMenu', '3'); await d.page.locator('#lessonBody button', { hasText: 'Listen to this line' }).click(); await d.page.waitForTimeout(500); });
  await act('export-journal', () => d.download('net-journal-export', () => d.click('#lessonExport')));
  await act('print-journal', () => d.print('net-journal-print', () => d.click('#lessonPrint')));
  await act('fresh-dialog', async () => { await d.click('#lessonExit'); await d.tab('recursion'); await d.click('#exploreAnotherRoute'); await d.click('#keepRoute'); });
  const cfg = getConfig();
  const origin = cfg.candidate && cfg.candidate.kind === 'url' ? new URL(cfg.candidate.url).host : '';
  const classified = classifyRequests(d.requests, side, origin);
  const actionHttp = d.requests.filter(r => r.phase !== 'load' && /^https?:/i.test(r.url));
  const loadHosts = [...new Set(d.requests.filter(r => r.phase === 'load' && /^https?:/i.test(r.url)).map(r => new URL(r.url).host))].sort();
  d.record('network', {
    loadHosts: loadHosts.join(' '),
    actionRequests: actionHttp.map(r => r.phase + ' ' + r.resourceType + ' ' + r.url).join('\n'),
    nonHttpRequests: [...new Set(d.requests.filter(r => !/^https?:/i.test(r.url)).map(r => r.url.split(':')[0] + ':' + r.resourceType))].sort().join(' '),
    unexplained: classified.filter(c => c.verdict === 'unexplained').map(c => c.phase + ' ' + c.url).join('\n'),
  });
  d.check('NET', actionHttp.length === 0, 'zero http(s) requests from any reader action', actionHttp.map(r => r.phase + ' ' + r.url));
  d.check('NET', classified.filter(c => c.verdict === 'unexplained').length === 0, 'page-load hosts within the allow-list', loadHosts);
  d.check('NET', d.console.filter(c => c.type === 'error').length === 0 && d.pageErrors.length === 0, 'no console errors or page errors', { console: d.console.filter(c => c.type === 'error'), pageErrors: d.pageErrors });
});
