// Section 5.2 (5) Storage: the same keys and the same JSON after the same scenario; with storage
// blocked, the page works, shows the unavailable message and logs no errors.
import { scenario } from '../lib/harness.mjs';
import { buildGoldRoute, fillRecursion, fillLesson, cell, rule, TEXT } from '../lib/flows.mjs';

const VISIT = 'words-of-plainness:lattice:visit:v1', JOURNAL = 'words-of-plainness:lattice:author-journal:v1';

scenario('storage', 'S01-keys-and-json', { b: ['B59', 'B60'], timeout: 180000 }, async d => {
  await d.open();
  await buildGoldRoute(d);
  await d.click('#gridOpenReflection'); await d.settle();
  await fillRecursion(d); await d.settle();
  await d.select('#hintLevel', 'coaching');
  await d.tab('cube'); await d.settle(250);
  await d.select('#layerFilter', '2'); await d.click('#explode'); await d.click('#showWires'); await d.click('#topCamera');
  await d.settle();
  const s1 = await d.snap('route-notes-settings', ['B59']);
  await d.tab('read'); await d.settle();
  await fillLesson(d);
  const s2 = await d.snap('lesson-written', ['B59']);
  const v = s2.storage[VISIT] || {}, j = s2.storage[JOURNAL] || {};
  d.check('B59', Object.keys(s2.storage).join(',') === [JOURNAL, VISIT].join(','), 'exactly the two keys', Object.keys(s2.storage));
  d.check('B59', ['mode', 'lastLattice', 'route', 'undo', 'redo', 'grid', 'hint', 'yaw', 'pitch', 'zoom', 'explode', 'layerFilter', 'showWires', 'notes', 'lessonOpen', 'contextOpen'].every(k => k in v) && v.notes[0] === TEXT.before && v.route.path.join() === 'n011,n111,n211,c1', 'visit key holds route, reflections, active view and lattice settings', Object.keys(v));
  d.check('B59', Array.isArray(j.entries) && j.entries.length === 11 && j.closing.length === 5 && typeof j.comparison === 'string' && Number.isInteger(j.step), 'journal key holds the lesson (11 entries, 5 closing, comparison, step)', { entries: j.entries && j.entries.length, step: j.step });
  d.check('B60', s1.status.visit === 'Progress saved in this browser', 'progress saved message', s1.status.visit);
});

scenario('storage', 'S02-blocked', { b: ['B59', 'B60'], blockStorage: true, timeout: 180000 }, async d => {
  await d.open();
  const s0 = await d.snap('blocked-load', ['B60']);
  d.check('B60', s0.status.visit === 'This browser could not save your place. Export your notes before leaving.' && s0.storage.__error === 'SecurityError', 'separate message when storage is unavailable', s0.status.visit);
  await d.tab('grid');
  for (const id of ['n011', 'n111', 'n211', 'c1']) await cell(d, id);
  const s1 = await d.snap('blocked-route', ['B59']);
  d.check('B59', s1.route.nodes.split(' / ').length === 4, 'the lattice works with storage blocked', s1.route.nodes);
  await d.click('#gridOpenReflection'); await d.settle();
  await fillRecursion(d); await d.settle();
  await rule(d, 'free');
  await d.tab('read');
  await fillLesson(d);
  const s2 = await d.snap('blocked-lesson', ['B59']);
  d.check('B59', s2.lesson && s2.lesson.storage === 'This browser can keep your journal only during this visit. Export a copy before leaving.', 'lesson works and says it keeps the journal only for this visit', s2.lesson && s2.lesson.storage);
  d.check('B59', d.console.filter(c => c.type === 'error').length === 0 && d.pageErrors.length === 0, 'no console errors or page errors with storage blocked', { console: d.console, pageErrors: d.pageErrors });
});
