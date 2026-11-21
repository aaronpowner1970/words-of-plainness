// Reader actions shared by several scenarios. They drive the UI only.

export async function cell(d, id) { await d.click(`#grids [data-node="${id}"]`); }

export async function rule(d, value) { await d.select('#pathRule', value); }

export async function openExamples(d) {
  const open = await d.page.evaluate(() => document.querySelector('.tl-path-examples').open);
  if (!open) await d.click('.tl-path-examples > summary');
}

export async function generate(d) { await openExamples(d); await d.click('#randomPath'); }

export async function clickText(d, scope, text) {
  await d.page.locator(scope).getByRole('button', { name: text, exact: true }).first().click();
}

export async function hasButton(d, scope, text) {
  return (await d.page.locator(scope).getByRole('button', { name: text, exact: true }).count()) > 0;
}

// D11 (G5 ruling): v1.88 offers "Skip for now"; the rebuild does not, and the reader simply moves on.
export async function skipOrLeaveBlank(d) {
  if (await hasButton(d, '#lessonBody', 'Skip for now')) await clickText(d, '#lessonBody', 'Skip for now');
}

export async function lessonField(d, text, nth = 0) { await d.page.locator('#lessonBody textarea').nth(nth).fill(text); }

export async function saveReflection(d) { await clickText(d, '#lessonBody', 'Save reflection'); }

export async function revisit(d) { await d.page.locator('#lessonBody button', { hasText: 'Revisit' }).first().click(); }

export async function disclosureEnabled(d) {
  return d.page.evaluate(() => { const b = document.querySelector('#lessonBody [aria-controls="lessonPerspective"]'); return !!b && !b.disabled; });
}

export async function openDisclosure(d) { await d.click('#lessonBody [aria-controls="lessonPerspective"]'); }

export const TEXT = {
  opening: 'Plain speech can let two people stand on the same ground long enough to listen.',
  line1: 'I hear breath as both receiving and giving back.',
  line4: 'Revision returns each morning; the task stays open.',
  line10: 'The reversal makes the favor run both ways.',
  closing: [
    'It felt like breathing before I knew why.',
    'The colon after breathing made me pause aloud.',
    'Unfinished pages on my own desk.',
    'Would you ask whether whethering is a real word?',
    'I would keep my opening reflection, and qualify it: plain speech also asks for listening.',
  ],
  comparison: 'We meet at listening; mine goes toward the classroom.',
  before: 'Each phrase turns from asking toward holding on.',
  after: 'Looking back, I now notice the bridge is a gift as much as a labor.',
};

// A complete lesson pass used by the functional, storage and export scenarios.
// Lines: 1 saved + revisit, 2 skipped (or left blank: D11), 3 blank + revisit, 4 saved, 10 saved.
export async function fillLesson(d, snap = async () => {}) {
  await d.click('#lessonStart'); await d.settle();
  await snap('lesson-open', ['B51', 'B52', 'B53']);
  await lessonField(d, TEXT.opening); await d.settle();
  await snap('opening-typed', ['B53']);
  await saveReflection(d); await d.settle();
  await snap('opening-saved', ['B53']);
  await openDisclosure(d); await d.settle();
  await snap('opening-disclosure', ['B53', 'B16']);
  await d.click('#lessonNext'); await d.settle(250);
  await snap('line1', ['B51', 'B53', 'B55']);
  await lessonField(d, TEXT.line1); await saveReflection(d); await d.settle();
  await snap('line1-saved', ['B53', 'B55']);
  await revisit(d); await d.settle();
  await snap('line1-revisit', ['B53', 'B55']);
  await d.click('#lessonNext'); await d.settle();
  await skipOrLeaveBlank(d); await d.settle();
  await snap('line2-skip-or-blank', ['B53', 'B55']);
  await d.click('#lessonNext'); await d.settle();
  await revisit(d); await d.settle();
  await snap('line3-blank-revisit', ['B53', 'B55']);
  await d.click('#lessonNext'); await d.settle();
  await lessonField(d, TEXT.line4); await saveReflection(d); await d.settle();
  await snap('line4-saved', ['B53']);
  await d.select('#lessonMenu', '10'); await d.settle();
  await snap('line10', ['B51', 'B53']);
  await lessonField(d, TEXT.line10); await saveReflection(d); await d.settle();
  await openDisclosure(d); await d.settle();
  await snap('line10-saved-disclosure', ['B53']);
  await d.click('#lessonNext'); await d.settle();
  await snap('looking-back', ['B51', 'B57']);
  for (let i = 0; i < 5; i++) await lessonField(d, TEXT.closing[i], i);
  await d.settle();
  await snap('closing-filled', ['B57']);
  await d.click('#lessonBody details > summary'); await d.settle();
  await snap('closing-thesis-open', ['B57']);
  await lessonField(d, TEXT.comparison, 5); await d.settle();
  await snap('comparison-filled', ['B57']);
}

// Gold route (Questioning → blessing) built by hand in the 2D lattice.
export async function buildGoldRoute(d) {
  await d.tab('grid'); await d.settle();
  for (const id of ['n011', 'n111', 'n211', 'c1']) { await cell(d, id); await d.settle(60); }
}

export async function fillRecursion(d) {
  await d.fill('#beforeNote', TEXT.before);
  await d.click('[data-lens="2"]');
  await d.fill('#afterNote', TEXT.after);
  await d.select('#fitScore', 'Plausible');
}
