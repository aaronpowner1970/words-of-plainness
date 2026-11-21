// Section 5.2 (6) Exports and prints: both .txt exports (compared line by line, D2/D5/D6/D9 applied
// through the planned-differences map) and all three print editions in print media.
import { scenario } from '../lib/harness.mjs';
import { buildGoldRoute, fillRecursion, fillLesson, TEXT } from '../lib/flows.mjs';

async function poemLines(d) {
  return d.page.evaluate(() => Array.from(document.querySelectorAll('#plainPoem .tl-verse')).map(v => Array.from(v.querySelectorAll('p')).map(p => Array.from(p.querySelectorAll('span')).map(s => s.textContent))));
}
function expectedCopy(verses, stacked) {
  const poem = verses.map(st => st.map(l => l.join(stacked ? '\n' : ' ')).join(stacked ? '\n\n' : '\n'));
  return 'Plainness Favoring\nby Aaron John Powner\n\n' + poem.join(stacked ? '\n\n\n' : '\n\n');
}

async function copy(d, label, sel, stackedSel) {
  await d.click(sel);
  await d.settle(60);
  const after = await d.page.locator(sel).textContent();
  const clip = await d.lastClipboard();
  const stacked = await d.page.evaluate(s => document.querySelector(s).classList.contains('tl-stacked'), stackedSel);
  await d.page.waitForTimeout(1900);
  const restored = await d.page.locator(sel).textContent();
  return d.record(label, { text: clip && clip.text, via: clip && clip.via, label: after, restored, stacked });
}

for (const vp of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
  scenario('exports', `E01-copy-${vp.width}`, { b: ['B14', 'B56'], viewport: vp }, async d => {
    await d.open();
    const verses = await poemLines(d);
    const r = await copy(d, 'copy-read', '#copyPoem', '#plainPoem');
    d.check('B14', r.text === expectedCopy(verses, r.stacked) && ['Copied ✓', 'Copy attempted'].includes(r.label) && r.restored === 'Copy plain poem', `${vp.width}px Read: title, byline, blank line, poem in the shown layout (${r.stacked ? 'stacked' : 'full lines'}); label then restored`, { label: r.label, via: r.via, stacked: r.stacked });
    d.check('B9', vp.width === 375 ? r.stacked : !r.stacked, `${vp.width}px: copy follows the layout shown`, r.stacked);
    await d.click('#lessonStart'); await d.settle();
    await d.click('#lessonNext'); await d.settle(300);
    if (await d.page.locator('#poemContext').isHidden()) await d.click('#contextTrigger');
    await d.settle(200);
    const p = await copy(d, 'copy-panel', '#contextCopy', '#contextText');
    d.check('B56', p.text === expectedCopy(verses, p.stacked) && p.restored === 'Copy plain poem', `${vp.width}px panel: Copy plain poem uses the panel's layout (${p.stacked ? 'stacked' : 'full lines'})`, { stacked: p.stacked, label: p.label });
  });
}

scenario('exports', 'E02-pathway-export-print', { b: ['B50', 'B49'] }, async d => {
  await d.open();
  await buildGoldRoute(d);
  await d.click('#gridOpenReflection'); await d.settle();
  await fillRecursion(d); await d.settle();
  const x = await d.download('pathway-export', () => d.click('#recursionExport'));
  const t = x.text || x.blobText || '';
  d.check('B50', x.filename === 'plainness-favoring-pathway-notes.txt', 'export file name', x.filename);
  d.check('B50', x.downloadEvent && x.blobMatchesDownload, 'the downloaded file is the text the page built', { downloadEvent: x.downloadEvent, error: x.error });
  const want = ['Plainness Favoring\nby Aaron John Powner', 'PATHWAY: Your guided route', '1. weathering and whethering, [Stanza I · Line 2 · Process]', 'INTERPRETIVE LENS IN USE: Beholding', 'PROMPT: Follow the changing relationship', 'CONNECTIONS AMONG THE STANZA NODES:\n' + TEXT.before, 'JUDGMENT THROUGH THE CODA:\n' + TEXT.after, 'FIT: Plausible', 'This is a reader-generated interpretation, not necessarily an author-intended decoding.'];
  d.check('B50', want.every(w => t.includes(w)) && /\n2\. torment enduring, \[Stanza II · Line 2 · Process\]\n/.test(t) && /\n4\. His plainness favoring: \[Coda · Process\]\n/.test(t), 'title and byline, ordered phrases with labels, Coda, lens and prompt, both reflections, fit, closing line', want.filter(w => !t.includes(w)));
  const p = await d.print('pathway-print', () => d.click('#recursionPrint'));
  d.check('B50', p.printCalled && p.sheetClass.includes('tl-print-journal') && want.slice(3).every(w => p.printText.replace(/\n+/g, '\n').includes(w.replace(/\n+/g, '\n'))), 'print edition carries the same sections', { sheet: p.sheetClass });
  await d.click('#exploreAnotherRoute');
  const x2 = await d.download('dialog-export', () => d.click('#exportOldRoute'));
  d.check('B49', x2.text === x.text, 'export from the fresh-pathway dialog is the same file', x2.filename);
  const p2 = await d.print('dialog-print', () => d.click('#printOldRoute'));
  d.check('B49', p2.printText === p.printText, 'print from the dialog is the same edition');
});

scenario('exports', 'E03-journal-export-print', { b: ['B58', 'B5'], timeout: 180000 }, async d => {
  await d.open();
  await fillLesson(d);
  const x = await d.download('journal-export', () => d.click('#lessonExport'));
  const t = x.text || x.blobText || '';
  d.check('B58', x.filename === 'plainness-favoring-reading-journal.txt' && x.downloadEvent && x.blobMatchesDownload, 'journal export file', x.filename);
  const iScene = t.indexOf('Setting the scene\n'), iBegin = t.indexOf('Before we begin\n');
  d.check('B58', t.startsWith('Plainness Favoring\nby Aaron John Powner\n\nMY READING JOURNAL · Read with the author\n\n') && iScene > 0 && iScene < iBegin, 'title, byline, then Setting the scene before the opening reflection');
  d.check('B58', t.includes('Line 1\nMarked to revisit\nWriting plainly is breathing:\ninspiration,\nexpiration\n\nWhat do I take in when I write') && t.includes(TEXT.line1), 'each part with its phrases one per line, question, response, revisit mark');
  d.check('B58', t.includes('Line 2\n') && /Line 2\n[^]*?\n\(Skipped\)\n/.test(t) && /Line 3\nMarked to revisit\n[^]*?\n\(No response recorded\)\n/.test(t), 'skipped and blank parts marked as v1.88 does (D11 changes this in the rebuild)');
  d.check('B58', TEXT.closing.every(c => t.includes(c)) && t.includes('What did the poem answer for me?\nI am learning to write plainly') && t.trimEnd().endsWith(TEXT.comparison) && t.includes("My reading alongside the author's"), 'five closing answers, the thesis, and the comparison when filled');
  const p = await d.print('journal-print', () => d.click('#lessonPrint'));
  d.check('B58', p.printCalled && p.printText.includes('MY READING JOURNAL · Read with the author') && p.printText.includes(TEXT.comparison), 'print edition of the journal', p.sheetClass);
});

scenario('exports', 'E04-poem-print', { b: ['B15', 'B56'] }, async d => {
  await d.open();
  const p = await d.print('poem-print-read', () => d.click('#printPoem'));
  const o = (p.outline || '').split('\n');
  d.check('B15', p.printCalled && o[0] === 'h1: Plainness Favoring' && o[1] === 'p: by Aaron John Powner' && o[2] === 'p: Writing plainly is breathing: inspiration, expiration' && o.length === 12, 'print edition: byline directly under the title, then the ten lines', o.slice(0, 3));
  d.check('B15', p.printText.replace(/\n+/g, '\n').startsWith('Plainness Favoring\nby Aaron John Powner\nWriting plainly is breathing: inspiration, expiration\n'), 'print-media text order: title, byline, first verse', p.printText.slice(0, 80));
  await d.click('#lessonStart'); await d.settle();
  await d.click('#lessonNext'); await d.settle(300);
  const q = await d.print('poem-print-panel', () => d.click('#contextPrint'));
  d.check('B56', q.printText === p.printText, 'Print plain poem from the panel gives the same edition');
});
