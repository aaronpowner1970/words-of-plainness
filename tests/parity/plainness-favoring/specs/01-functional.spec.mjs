// Section 5.2 (1) Functional: scripted UI-only scenarios, with a state snapshot after every step.
import { scenario } from '../lib/harness.mjs';
import { cell, rule, openExamples, generate, fillLesson, buildGoldRoute, fillRecursion, TEXT } from '../lib/flows.mjs';

const lines = s => (s ? s.split('\n') : []);

// Structure and style facts that the inventory cannot see.
function probe() {
  const root = document.getElementById('tool-root');
  const cs = (e, p) => (e ? getComputedStyle(e)[p] : null);
  const h2 = root.querySelector('.tl-intro h2'), sub = root.querySelector('.tl-poem-subtitle');
  const classes = new Set();
  root.querySelectorAll('[class]').forEach(e => e.classList.forEach(c => classes.add(c)));
  const media = [];
  for (const sheet of document.styleSheets) { try { for (const r of sheet.cssRules) if (r.media) media.push(r.media.mediaText); } catch {} }
  const panel = root.querySelector('.tl-working-panel'), tab = root.querySelector('.tl-tab');
  return {
    headingTwoLines: !!(h2 && sub && sub.getBoundingClientRect().top >= h2.getBoundingClientRect().top + 10),
    nonTlClasses: [...classes].filter(c => !c.startsWith('tl-')).sort().join(' '),
    bodyChildren: Array.from(document.body.children).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '')).join(' '),
    phrasesPerLine: Array.from(root.querySelectorAll('#plainPoem p')).map(p => p.querySelectorAll('span').length).join(','),
    verses: root.querySelectorAll('#plainPoem .tl-verse').length,
    headingFont: cs(root.querySelector('.tl-intro h2'), 'fontFamily'), uiFont: cs(root.querySelector('.tl-btn'), 'fontFamily'),
    voiceColors: ['impulse', 'process', 'outcome'].map(v => cs(root.querySelector('.tl-legend-chip .tl-voice-' + v), 'color')).join(' | '),
    cellColors: ['0', '1', '2'].map(v => { const c = root.querySelector('.tl-cell[data-voice="' + v + '"]'); return c ? getComputedStyle(c, '::before').backgroundColor : null; }).join(' | '),
    tokens: ['brown-deep', 'cream', 'gold-primary', 'teal-muted', 'burgundy'].map(t => t + '=' + getComputedStyle(root).getPropertyValue('--' + t).trim()).join(' '),
    panelBackground: cs(panel, 'backgroundColor') + ' / ' + cs(panel, 'backgroundImage'),
    panelBorder: cs(panel, 'borderTopColor') + ' ' + cs(panel, 'borderTopWidth'),
    tabBorder: cs(tab, 'borderTopColor') + ' ' + cs(tab, 'borderTopWidth'),
    sceneWhiteSpace: cs(root.querySelector('.tl-scene p'), 'whiteSpace'),
    bylineFollowsTitle: root.querySelector('.tl-poem-area h2').nextElementSibling === root.querySelector('.tl-byline'),
    mediaRules: [...new Set(media)].sort().join(' ; '),
    canvasLabel: (root.querySelector('canvas') || { getAttribute: () => '' }).getAttribute('aria-label'),
    lensPressed: Array.from(root.querySelectorAll('.tl-lens')).every(b => b.hasAttribute('aria-pressed')),
    viewPressed: Array.from(root.querySelectorAll('[data-grid-display]')).every(b => b.hasAttribute('aria-pressed')),
    sixTraits: Array.from(root.querySelectorAll('.tl-six-traits h4')).map(h => h.textContent).join(' | '),
    craftHeadings: Array.from(root.querySelectorAll('.tl-craft:last-of-type h4')).map(h => h.textContent).join(' | '),
    commentaryLastChild: (root.querySelector('.tl-commentary-body > :last-child') || {}).textContent || null,
  };
}

scenario('functional', 'F01-load-inventory-tabs', { b: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B13', 'B16', 'B17', 'B18', 'B19', 'B20', 'B22', 'B26', 'B27', 'B28', 'B29', 'B37', 'B43', 'B44', 'B51', 'B63', 'B64'] }, async d => {
  await d.open();
  const inv = await d.inventory(['B1', 'B2', 'B3', 'B7', 'B8', 'B13', 'B16', 'B17', 'B18', 'B19', 'B22', 'B26', 'B27', 'B28', 'B29', 'B37', 'B43', 'B44', 'B51', 'B63', 'B64']);
  const pr = await d.page.evaluate(probe);
  d.record('probe', pr);
  const s = await d.snap('load', ['B1', 'B19', 'B22', 'B29', 'B43']);
  d.check('B1', inv.tabs === '1 Read → 2 2D lattice → 3 3D lattice → 4 Recursion' && inv.tabModes === 'read,grid,cube,recursion' && s.activeTab === 'read', 'four tabs in order with numbers and arrows; Read active at load', inv.tabs);
  d.check('B2', lines(inv.cells).length === 30 && lines(inv.poemLines).length === 10 && pr.phrasesPerLine === '3,3,3,3,3,3,3,3,3,3' && pr.verses === 4, '27 stanza nodes + 3 Coda nodes; 10 lines of 3 phrases in 3 stanzas + Coda', { cells: lines(inv.cells).length, phrases: pr.phrasesPerLine });
  d.check('B3', /🍃 Impulses*⟳ Processs*◎ Outcome/.test(inv.voiceHeadings) && /teal-muted=#\w+/.test(pr.tokens) && /gold-primary=#\w+/.test(pr.tokens) && /burgundy=#\w+/.test(pr.tokens) && new Set(pr.cellColors.split(' | ')).size === 3, 'three voices with symbols and colours (teal, gold, burgundy tokens; three distinct voice colours on the cells)', pr.tokens + ' / ' + pr.cellColors);
  d.check('B4', /^Meaning in motion\s*Geometry of a Recursive Poem \|\|/.test(inv.intro) && pr.headingTwoLines, 'heading in two lines', inv.intro.split(' || ')[0]);
  d.check('B5', pr.nonTlClasses === '' && pr.bodyChildren.startsWith('div#tool-root') && /serif/i.test(pr.headingFont) && /sans/i.test(pr.uiFont), 'tl- classes only, all inside #tool-root; serif headings, sans interface', pr);
  d.check('B6', !/rgba\(0, 0, 0, 0\)/.test(pr.panelBackground.split(' / ')[0]) && /0\.35\)/.test(pr.panelBorder) && /0\.35\)/.test(pr.tabBorder), 'solid deep-brown panel; gold border at 35% on panel and tabs', { panel: pr.panelBackground, border: pr.panelBorder, tab: pr.tabBorder });
  d.check('B7', inv.scene.startsWith('Setting the scene ||') && inv.sceneEmphasis === 'What are my writings, really? | To whom do I write?' && pr.sceneWhiteSpace === 'normal', 'scene paragraph with two bold-italic questions, wrapping naturally', inv.sceneEmphasis);
  d.check('B8', inv.poemTitle === 'Plainness Favoring || by Aaron John Powner' && pr.bylineFollowsTitle, 'title then byline directly beneath');
  d.check('B13', /^ \[ranges:0\]$/.test(inv.rewindStopSlider) && inv.transport.split(' | ').every(t => t.endsWith('[0 controls]')), 'no rewind, Stop, elapsed time or seek slider', inv.rewindStopSlider + ' / ' + inv.transport);
  d.check('B16', inv.details.includes('0:closed:What did the poem answer for me?'), 'thesis disclosure closed by default');
  d.check('B17', inv.details.includes('0:closed:First time here?') && inv.firstTime.includes('Explore a pathway on your own.') && inv.firstTime.includes('Read with the author.'), '"First time here?" closed, introduces both ways in');
  d.check('B18', inv.readButtons.startsWith('Reveal the 2D structure → | Read with the author'), 'buttons beneath the poem', inv.readButtons);
  const ruleLine = lines(inv.selects).find(l => l.startsWith('pathRule:'));
  d.check('B19', ruleLine === 'pathRule: curated=Guided discovery · promising paths | open=Open pathway · any three + one Coda | geometry=All geometric · 49 straight paths | strict=Strict alignment · straight to Coda | free=Free exploration · unrestricted' && s.values.pathRule === 'curated', 'five path rules, Guided discovery default', ruleLine);
  d.check('B20', ruleLine.includes('49 straight paths') && !s.instrument.errors, 'the page ran its 49-line and curated-straightness checks without refusing (the refusal branch itself needs a modified page)');
  const hintLine = lines(inv.selects).find(l => l.startsWith('hintLevel:'));
  d.check('B22', hintLine === 'hintLevel: minimal=Minimal hints | guided=Guided discovery* | coaching=Interpretive coaching' && s.coach.includes('Step 1 of 4'), 'three hint levels; coaching panel progress', hintLine);
  d.check('B26', inv.explorerColumn === 0, 'no separate Pathway explorer column');
  d.check('B27', inv.details.includes('0:closed:Explore example pathways'), '"Explore example pathways" disclosure');
  d.check('B28', inv.stanzaHeadings.startsWith('STANZA I · The paradox of language | STANZA II · The struggle of authorship | STANZA III · The transformation of purpose') && lines(inv.voiceHeadings.replace(/ \| /g, '\n')).length === 4, 'stanza panels headed STANZA I/II/III · clarifier, with voice headings', inv.stanzaHeadings);
  d.check('B29', inv.displaySwitch === 'gallery:Gallery view | full:Full lattice | focus:Guided focus' && s.gridDisplay === 'gallery', 'views in order Gallery → Full → Guided focus', inv.displaySwitch);
  const layerLine = lines(inv.selects).find(l => l.startsWith('layerFilter:'));
  d.check('B37', layerLine === 'layerFilter: all=All stanzas | 0=Stanza I | 1=Stanza II | 2=Stanza III | c=Coda' && s.values.showWires === 'true', 'focus selector and connections checkbox', layerLine);
  d.check('B43', inv.lenses === '0:PreferenceWhat is chosen?:false | 1:BeneficenceWhat is received?:true | 2:BeholdingWhat is revealed?:false', 'three lenses, Beneficence active', inv.lenses);
  const fitLine = lines(inv.selects).find(l => l.startsWith('fitScore:'));
  d.check('B44', fitLine === 'fitScore: Undecided=Not yet decided | Strong=Strong, supported by the words | Plausible=Plausible, but not certain | Strained=Strained or unconvincing', 'Fit selector', fitLine);
  const menuLine = lines(inv.selects).find(l => l.startsWith('lessonMenu:'));
  d.check('B51', menuLine === 'lessonMenu: 0=Before we begin | 1=Line 1 | 2=Line 2 | 3=Line 3 | 4=Line 4 | 5=Line 5 | 6=Line 6 | 7=Line 7 | 8=Line 8 | 9=Line 9 | 10=Line 10 · Coda | 11=Looking back', 'lesson section menu', menuLine);
  const det = inv.details;
  d.check('B63', det.includes('0:closed:Poetry commentary A critical reading of the poem and the Lab') && ['The poem', 'The experience', 'Six traits of writing', 'A closer look at the craft'].every(t => det.includes('1:closed:' + t)) &&
    pr.sixTraits === '1. Ideas | 2. Organization | 3. Voice | 4. Word choice | 5. Sentence fluency | 6. Conventions' && pr.commentaryLastChild === 'Commentary by ChatGPT on Aaron John Powner’s poem.', 'commentary nesting, six traits, credit at bottom', det);
  d.check('B64', inv.liveRegions.split(' | ').length === 3 && pr.canvasLabel.length > 80 && /prefers-reduced-motion: reduce/.test(pr.mediaRules) && /pointer: coarse/.test(pr.mediaRules) && pr.lensPressed && pr.viewPressed, '3 live regions; canvas text label; reduced-motion and coarse-pointer rules; aria-pressed on lens and view buttons', inv.liveRegions);
  for (const mode of ['grid', 'cube', 'recursion', 'read']) {
    const t = await d.step('tab-' + mode, ['B1'], () => d.tab(mode));
    d.check('B1', t.activeTab === mode && t.activePanel === mode + 'Mode', `tab ${mode} opens its panel`, t.modeHead);
  }
  await d.step('reveal-2d', ['B18'], () => d.click('#readMode [data-go="grid"]'));
});

scenario('functional', 'F02-rules-generate-examples', { b: ['B19', 'B21', 'B22', 'B23', 'B24', 'B27'] }, async d => {
  await d.open();
  let calls = (await d.snap('start')).instrument.randomCalls;
  const perRule = { curated: 1, open: 4, geometry: 2, strict: 1, free: 2 };
  for (const r of ['curated', 'open', 'geometry', 'strict', 'free']) {
    const s0 = await d.step('rule-' + r, ['B19', 'B24'], () => rule(d, r));
    if (r !== 'curated') d.check('B24', /^Path rules changed to /.test(s0.status.selection), `announcement on rule change (${r})`, s0.status.selection);
    for (let k = 1; k <= 3; k++) {
      const s = await d.step(`generate-${r}-${k}`, ['B23', 'B22', 'B24'], () => generate(d));
      const n = s.route.nodes.split(' / ').length;
      d.check('B23', s.instrument.randomCalls - calls === perRule[r] && n === 4 && /Coda ·/.test(s.route.nodes.split(' / ')[3]), `Generate under ${r}: four nodes ending in a Coda, ${perRule[r]} Math.random call(s)`, { route: s.route.nodes, calls: s.instrument.randomCalls - calls, rule: s.values.pathRule });
      calls = s.instrument.randomCalls;
    }
  }
  await d.step('rule-back-curated', ['B19'], () => rule(d, 'curated'));
  await openExamples(d);
  const labels = await d.page.locator('#examples button').allTextContents();
  d.check('B27', labels.length === 6, 'six example pathways', labels.join(' | '));
  for (let i = 0; i < labels.length; i++) {
    const s = await d.step('example-' + i, ['B21', 'B24'], () => d.page.locator('#examples button').nth(i).click());
    d.check('B21', s.route.nodes.split(' / ').length === 4 && s.route.name.length > 5, `example "${labels[i]}" loads a named four-node route`, s.route.name);
  }
  // Hint levels on a completed curated route (route cues reach the "think" line at coaching level).
  await d.page.locator('#examples button').nth(0).click();
  for (const h of ['minimal', 'guided', 'coaching']) {
    const s = await d.step('hint-' + h, ['B21', 'B22'], () => d.select('#hintLevel', h));
    if (h === 'coaching') d.check('B21', s.coach.endsWith('Does the experience of struggle make the later act of bridging more significant?'), 'route cue question shown at coaching level', s.coach);
    if (h === 'minimal') d.check('B22', s.coach.includes('4 of 4 complete') && s.coach.includes('Completed. Review the path through the Coda.'), 'minimal hint on a complete path', s.coach);
  }
  // Coaching level while building step by step, including "n chosen" in free mode.
  await d.tab('grid');
  await d.step('coach-step1-clear', ['B22'], () => d.click('#clearGrid'));
  const c1 = await d.step('coach-pick1', ['B22'], () => cell(d, 'n011'));
  d.check('B22', c1.coach.includes('Step 2 of 4') && c1.coach.startsWith('STEP 2 · CONNECTION'), 'Step n of 4 while building', c1.coach);
  await d.step('coach-pick2', ['B22'], () => cell(d, 'n111'));
  await d.step('rule-free-coaching', ['B22'], () => rule(d, 'free'));
  await cell(d, 'n000');
  const f = await d.step('free-pick2', ['B22'], () => cell(d, 'n222'));
  d.check('B22', f.coach.includes('2 chosen'), '"n chosen" in free mode', f.coach);
});

scenario('functional', 'F03-grid-picking-notices-undo', { b: ['B24', 'B28', 'B29', 'B30', 'B31', 'B32', 'B33', 'B34'] }, async d => {
  await d.open();
  await d.step('grid', ['B28'], () => d.tab('grid'));
  for (const v of ['full', 'focus', 'gallery']) {
    const s = await d.step('display-' + v, ['B29'], () => d.click(`[data-grid-display="${v}"]`));
    d.check('B29', s.gridDisplay === v && s.pressed.includes(`display:${v}=true`) && s.gridExplain.length > 20, `view ${v} with its explanation`, s.gridExplain);
  }
  const notices = [];
  const n1 = await d.step('notice-coda-first', ['B31'], () => cell(d, 'c0')); notices.push(n1.gridNotice);
  const n2 = await d.step('notice-not-curated-start', ['B31'], () => cell(d, 'n010')); notices.push(n2.gridNotice);
  await rule(d, 'strict');
  const n3 = await d.step('notice-strict-start', ['B31'], () => cell(d, 'n000')); notices.push(n3.gridNotice);
  await rule(d, 'curated');
  const p1 = await d.step('pick-n011', ['B30', 'B31'], () => cell(d, 'n011'));
  d.check('B30', p1.gridDisplay === 'focus', 'first selection in Gallery switches to Guided focus', p1.gridDisplay);
  d.check('B31', p1.cells.includes('n111:V') && p1.cells.includes('n211:V') && p1.cells.includes('n000:U'), 'eligible next phrases outlined; others inspectable but unavailable', p1.cells);
  const n4 = await d.step('notice-breaks-route', ['B31'], () => cell(d, 'n000')); notices.push(n4.gridNotice);
  await d.step('pick-n111', ['B31'], () => cell(d, 'n111'));
  await d.step('pick-n211', ['B31'], () => cell(d, 'n211'));
  const done = await d.step('pick-c1', ['B31', 'B33'], () => cell(d, 'c1'));
  d.check('B33', done.hidden.includes('gridReflection=shown'), 'completion notice "Your pathway is ready to interpret" with Open interpretation exercise', done.hidden);
  const n5 = await d.step('notice-complete', ['B31'], () => cell(d, 'n000')); notices.push(n5.gridNotice);
  await d.step('dismiss-notice', ['B31'], () => d.click('#dismissGridNotice'));
  await rule(d, 'open');
  for (const id of ['n000', 'n001', 'n002']) await cell(d, id);
  const n6 = await d.step('notice-open-three', ['B31'], () => cell(d, 'n010')); notices.push(n6.gridNotice);
  const reasons = new Set(notices.map(n => n.split(' — ')[1]));
  d.check('B31', reasons.size === 6 && notices.every(n => n.includes('is available to inspect')), 'notice reasons: five rule-specific reasons plus the Coda-first reason (six distinct texts in v1.88)', [...reasons]);
  // Undo, Redo, Clear beneath the 2D lattice; keyboard Ctrl+Z / Ctrl+Y.
  const u1 = await d.step('undo-grid-1', ['B32', 'B24'], () => d.click('#undoGrid'));
  d.check('B24', u1.status.selection === 'Undid the last pathway change.', 'Undo announces', u1.status.selection);
  await d.step('undo-grid-2', ['B32'], () => d.click('#undoGrid'));
  const r1 = await d.step('redo-grid', ['B32', 'B24'], () => d.click('#redoGrid'));
  d.check('B24', r1.status.selection === 'Restored the pathway change.', 'Redo announces', r1.status.selection);
  const c = await d.step('clear-grid', ['B32', 'B24'], () => d.click('#clearGrid'));
  d.check('B32', c.route.nodes === '' && c.disabled.includes('clearGrid=off'), 'Clear selections empties the route', c.disabled);
  await d.step('key-undo', ['B24'], async () => { await d.page.locator('#undoGrid').focus(); await d.page.keyboard.press('Control+z'); });
  await d.step('key-redo', ['B24'], () => d.page.keyboard.press('Control+y'));
  // Free exploration toggles phrases on and off.
  await rule(d, 'free');
  await d.step('free-add', ['B31'], () => cell(d, 'n120'));
  await d.step('free-remove', ['B31'], () => cell(d, 'n120'));
  await cell(d, 'n120');
  const sd = await d.step('start-new-path', ['B34', 'B49'], () => d.click('#gridStartCustom'));
  d.check('B34', sd.dialogs.includes('freshRouteDialog=open'), '"Start a new path" opens the fresh-pathway dialog', sd.dialogs);
  await d.step('keep-reflecting', ['B49'], () => d.click('#keepRoute'));
});

scenario('functional', 'F04-recursion-dialog-reverse', { b: ['B24', 'B33', 'B39', 'B41', 'B42', 'B43', 'B44', 'B45', 'B46', 'B47', 'B48', 'B49', 'B50'] }, async d => {
  await d.open();
  await d.step('recursion-preview', ['B41'], () => d.tab('recursion'));
  await buildGoldRoute(d);
  const r0 = await d.step('open-interpretation', ['B33', 'B41', 'B43'], () => d.click('#gridOpenReflection'));
  d.check('B41', r0.activeTab === 'recursion' && r0.recursion.stanza.split('\n').filter(Boolean).length >= 3 && /Coda · Process · Beneficence/.test(r0.recursion.coda), 'selected phrases as ordered cards; Coda beside the lens invitation', r0.recursion);
  d.check('B43', r0.pressed.includes('lens:1=true') && r0.recursion.lensPrompt.startsWith('Beneficence · His plainness favoring: — Look for an experience'), 'Beneficence lens with its Coda phrase and prompt', r0.recursion.lensPrompt);
  const b1 = await d.step('before-note', ['B42'], () => d.fill('#beforeNote', TEXT.before));
  d.check('B42', b1.recursion.connectionPrompt.startsWith('Observe the three stanza nodes selected and comment on what you think connects them.'), 'first reflection asks what connects the three nodes', b1.recursion.connectionPrompt);
  for (const l of ['0', '2', '1']) {
    const s = await d.step('lens-' + l, ['B43'], () => d.click(`[data-lens="${l}"]`));
    d.check('B43', s.pressed.includes(`lens:${l}=true`), `lens ${l} pressed`, s.recursion.lensPrompt.slice(0, 60));
  }
  await d.step('after-note', ['B44'], () => d.fill('#afterNote', TEXT.after));
  const f = await d.step('fit-strong', ['B44'], () => d.select('#fitScore', 'Strong'));
  d.check('B44', f.values.fitScore === 'Strong', 'Fit selector set');
  await d.step('undo-recursion', ['B46'], () => d.click('#undoRecursion'));
  await d.step('redo-recursion', ['B46'], () => d.click('#redoRecursion'));
  const cl = await d.step('clear-recursion', ['B46'], () => d.click('#clearRecursion'));
  d.check('B46', cl.route.nodes === '' && cl.values.beforeNote === TEXT.before, 'Clear selections beneath the pathway keeps the reflections', cl.values);
  await d.step('undo-after-clear', ['B46'], () => d.click('#undoRecursion'));
  const ret = await d.step('return-to-2d', ['B47'], () => d.click('#returnToLattice'));
  d.check('B47', ret.activeTab === 'grid' && ret.route.nodes.split(' / ').length === 4, '"Return to 2D lattice" reopens it with the current route', ret.modeHead);
  await d.tab('cube'); await d.settle();
  const r3 = await d.step('recursion-after-3d', ['B47', 'B48'], () => d.tab('recursion'));
  d.check('B47', r3.recursion.returnTo === 'Return to 3D lattice', 'names the last lattice used (3D)', r3.recursion.returnTo);
  d.check('B48', r3.recursion.exploreAnother === 'Explore another route in 3D', '"Explore another route in 3D"', r3.recursion.exploreAnother);
  const dl = await d.step('explore-another-dialog', ['B48', 'B49'], () => d.click('#exploreAnotherRoute'));
  d.check('B49', dl.dialogs.includes('freshRouteDialog=open'), 'fresh-pathway dialog opens when there is something to lose');
  await d.step('dialog-keep', ['B49'], () => d.click('#keepRoute'));
  await d.click('#exploreAnotherRoute');
  await d.download('dialog-export', () => d.click('#exportOldRoute'));
  const ex = await d.snap('dialog-after-export', ['B49', 'B50']);
  d.check('B49', ex.status.freshExport === 'Download requested. When you’re ready, choose Start fresh.', 'export from the dialog', ex.status.freshExport);
  await d.print('dialog-print', () => d.click('#printOldRoute'));
  await d.snap('dialog-after-print', ['B49', 'B50']);
  const fr = await d.step('dialog-start-fresh', ['B49'], () => d.click('#beginFreshRoute'));
  d.check('B49', fr.activeTab === 'cube' && fr.route.nodes === '' && fr.values.beforeNote === '' && fr.values.fitScore === 'Undecided' && fr.dialogs.includes('freshRouteDialog=closed'), 'Start fresh clears route and reflections and returns to the remembered view (3D)', fr.modeHead);
  // Clear notes.
  await d.tab('recursion');
  await fillRecursion(d);
  const cn = await d.step('clear-notes', ['B45'], () => d.click('#clearNotes'));
  d.check('B45', cn.values.beforeNote === '' && cn.values.afterNote === '' && cn.values.fitScore === 'Undecided', 'Clear notes empties both reflections and Fit');
  // Reverse: only in free exploration.
  const rv0 = await d.snap('reverse-hidden-curated', ['B24']);
  d.check('B24', rv0.hidden.includes('reversePath=hidden'), 'Reverse hidden outside Free exploration');
  await rule(d, 'free');
  await d.tab('grid');
  for (const id of ['n000', 'n111', 'n222']) await cell(d, id);
  const rv = await d.step('reverse-free', ['B24'], () => d.click('#reversePath'));
  d.check('B24', rv.route.nodes.startsWith('apprenticed to the Master') && rv.status.selection === 'Pathway reversed. Undo restores its previous order.', 'Reverse in free mode', rv.route.nodes);
  await d.step('clear-path-keeps-camera', ['B24'], () => d.click('#clearGrid'));
});

scenario('functional', 'F05-cube-controls-film', { b: ['B35', 'B36', 'B37', 'B38', 'B39', 'B40'] }, async d => {
  await d.open();
  const c0 = await d.step('cube', ['B35'], () => d.tab('cube'));
  d.check('B35', (c0.storage['words-of-plainness:lattice:visit:v1'] || {}).yaw === 0.63 && (c0.storage['words-of-plainness:lattice:visit:v1'] || {}).pitch === -0.36 && (c0.storage['words-of-plainness:lattice:visit:v1'] || {}).zoom === 1, 'starting view yaw 0.63, pitch −0.36, zoom 1 (read back from the visit record)');
  for (const [id, label] of [['frontCamera', 'front'], ['topCamera', 'top'], ['explode', 'spread'], ['explode', 'gather'], ['resetCamera', 'reset']]) {
    const s = await d.step('camera-' + label, ['B36'], () => d.click('#' + id));
    const v = s.storage['words-of-plainness:lattice:visit:v1'] || {};
    d.record('camera-' + label, { yaw: v.yaw, pitch: v.pitch, zoom: v.zoom, explode: v.explode });
  }
  for (const f of ['0', '1', '2', 'c', 'all']) await d.step('focus-' + f, ['B37'], () => d.select('#layerFilter', f));
  const w0 = await d.step('wires-off', ['B37'], () => d.click('#showWires'));
  d.check('B37', w0.cube.includes('Show connections | Structural connections hidden'), 'connections checkbox with status text', w0.cube);
  await d.step('wires-on', ['B37'], () => d.click('#showWires'));
  // Drag to rotate, wheel to zoom.
  const box = await d.page.locator('#cube').boundingBox();
  await d.step('drag-rotate', ['B35'], async () => {
    await d.page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.2);
    await d.page.mouse.down();
    await d.page.mouse.move(box.x + box.width * 0.2 + 100, box.y + box.height * 0.2 + 40, { steps: 5 });
    await d.page.mouse.up();
  });
  const z = await d.step('wheel-zoom', ['B35'], async () => { await d.page.mouse.move(box.x + 30, box.y + 30); await d.page.mouse.wheel(0, -120); });
  const v = z.storage['words-of-plainness:lattice:visit:v1'] || {};
  d.check('B35', Math.abs(v.yaw - (0.63 + 100 * 0.007)) < 1e-9 && Math.abs(v.pitch - (-0.36 - 40 * 0.007)) < 1e-9 && Math.abs(v.zoom - 1.09) < 1e-9, 'drag rotates (0.007 rad/px) and wheel zooms (×1.09)', v);
  await d.step('reset-after-drag', ['B36'], () => d.click('#resetCamera'));
  // Undo, Redo, Clear in 3D, on an example route.
  await openExamples(d);
  await d.page.locator('#examples button').nth(1).click();
  const cr = await d.snap('example-complete-3d', ['B39']);
  d.check('B39', cr.hidden.includes('cubeReflection=shown'), 'completion notice over the cube');
  await d.step('clear-viewer', ['B38'], () => d.click('#clearViewer'));
  await d.step('undo-viewer', ['B38'], () => d.click('#undoViewer'));
  await d.step('redo-viewer', ['B38'], () => d.click('#redoViewer'));
  await d.step('undo-viewer-2', ['B38'], () => d.click('#undoViewer'));
  const rr = await d.step('cube-open-reflection', ['B39'], () => d.click('#cubeOpenReflection'));
  d.check('B39', rr.activeTab === 'recursion', 'direct entry to Recursion from the cube');
  await d.tab('cube');
  const fo = await d.step('film-open', ['B40'], () => d.click('#cubeFilmOpen'));
  d.check('B40', fo.dialogs.includes('cubeFilm=open'), 'film window opens');
  await d.step('film-description', ['B40'], () => d.click('#cubeFilm details > summary'));
  const fc = await d.step('film-close', ['B40'], () => d.click('#cubeFilmClose'));
  d.check('B40', fc.dialogs.includes('cubeFilm=closed') && fc.filmPaused === 'true' && fc.activeTab === 'cube', 'closing pauses the film and returns to the cube in place', fc.dialogs);
});

scenario('functional', 'F06-lesson', { b: ['B16', 'B51', 'B52', 'B53', 'B55', 'B56', 'B57'], timeout: 180000 }, async d => {
  await d.open();
  const snaps = {};
  await fillLesson(d, async (label, b) => { snaps[label] = await d.snap(label, b); });
  const L = snaps;
  d.check('B52', L['lesson-open'].lesson.body.includes('Setting the scene') && L['lesson-open'].lesson.body.includes('What do you already believe plain speech can accomplish between people who see things differently?') && L['lesson-open'].lesson.body.includes('A sentence, a question, or an example from your own experience is enough.'), 'Before we begin: scene, opening question, encouragement');
  d.check('B53', L['lesson-open'].lesson.disclosureDisabled === 'true' && L['opening-saved'].lesson.disclosureDisabled === 'false' && L['opening-saved'].lesson.body.includes('Reflection saved.'), 'After discussion opens only after Save or Skip', [L['lesson-open'].lesson.disclosureDisabled, L['opening-saved'].lesson.disclosureDisabled]);
  d.check('B53', L.line1.lesson.body.includes('What question does this line of the poem pose?') && L.line1.lesson.body.includes('Save reflection') && L.line1.lesson.body.includes('Skip for now') && L.line1.lesson.body.includes('⚑ Revisit'), 'line part: gold heading, author question, field, Save/Skip, Revisit');
  d.check('B53', L['line2-skip-or-blank'].lesson.disclosureDisabled === 'false' && L['line3-blank-revisit'].lesson.disclosureDisabled === 'true', 'Skip unlocks the disclosure; a blank line keeps it locked');
  d.check('B55', L.line1.panel.hidden === 'false' && L.line1.panel.current === 0 && L.line1.panel.place === 'Line 1 of 10', 'whole-poem panel opens on reaching Line 1 on desktop, current line marked', L.line1.panel);
  d.check('B55', L['line3-blank-revisit'].panel.markers.startsWith('✓⚑|Saved, marked to revisit ; –|Skipped ; ⚑|No saved reflection, marked to revisit'), 'progress marks for saved, skipped and to-revisit lines', L['line3-blank-revisit'].panel.markers);
  d.check('B57', L['looking-back'].lesson.body.includes('Your opening reflection') && L['looking-back'].lesson.body.includes(TEXT.opening) && ['First impression', 'Sensory and emotional impact', 'Personal resonance', 'Points of friction', 'Shift in perspective'].every(t => L['looking-back'].lesson.body.includes(t)), 'five closing prompts after the opening reflection');
  d.check('B57', L['closing-thesis-open'].lesson.body.includes('Your shift in perspective') && L['closing-thesis-open'].lesson.body.includes(TEXT.closing[4]) && L['closing-thesis-open'].lesson.body.includes('Where does your reading meet mine, and where does it take you somewhere else?'), 'thesis disclosure, Shift-in-perspective echo, optional comparison');
  // The whole-poem panel: Line action both ways, closing, reopening, Escape.
  await d.select('#lessonMenu', '4'); await d.settle();
  await d.step('panel-open-line4', ['B55'], async () => { if (await d.page.locator('#poemContext').isHidden()) await d.click('#contextTrigger'); });
  await d.select('#contextLineAction', 'listen');
  const pl = await d.step('panel-listen-line6', ['B56'], async () => { await d.page.locator('#contextText button').nth(5).click(); await d.page.waitForFunction(() => document.querySelectorAll('#contextText button')[5].classList.contains('tl-spoken-line'), null, { timeout: 5000 }).catch(() => {}); await d.click('#contextReadAloud'); });
  d.check('B56', pl.lesson.menu === '4' && pl.audio.spokenPanel === '5', 'Play from line keeps the current discussion open (Line 4) and highlights line 6', { menu: pl.lesson.menu, spoken: pl.audio.spokenPanel });
  await d.select('#contextLineAction', 'study');
  const ps = await d.step('panel-study-line7', ['B56'], () => d.page.locator('#contextText button').nth(6).click());
  d.check('B56', ps.lesson.menu === '7', 'Open discussion jumps the lesson to that line', ps.lesson.menu);
  const pc = await d.step('panel-close', ['B55'], () => d.click('#closeContext'));
  d.check('B55', pc.panel.hidden === 'true', 'panel closable');
  await d.step('panel-reopen', ['B55'], () => d.click('#contextTrigger'));
  const pe = await d.step('panel-escape', ['B55'], () => d.page.keyboard.press('Escape'));
  d.check('B55', pe.panel.hidden === 'true', 'Escape closes the panel');
  await d.step('lesson-prev', ['B51'], () => d.click('#lessonPrev'));
  const ex = await d.step('lesson-exit', ['B51'], () => d.click('#lessonExit'));
  d.check('B51', ex.lesson === null && ex.hidden.includes('authorLesson=hidden'), 'exit returns to the poem');
});

scenario('functional', 'F07-returning-start-over', { b: ['B59', 'B60', 'B61'] }, async d => {
  await d.open();
  const s0 = await d.snap('first-load', ['B60']);
  d.check('B60', s0.status.visit === 'Progress saved in this browser', '"Progress saved in this browser" beside Start over', s0.status.visit);
  await d.tab('grid');
  await cell(d, 'n011'); await cell(d, 'n111');
  await d.snap('two-steps', ['B59']);
  const r1 = await d.step('reload-two-steps', ['B59', 'B61'], () => d.reload());
  d.check('B61', r1.status.visit === 'Welcome back. 2 of 4 pathway steps restored.' && r1.activeTab === 'grid' && r1.route.nodes.split(' / ').length === 2, 'welcome-back names "n of 4 pathway steps"; view restored', r1.status.visit);
  await rule(d, 'free');
  for (const id of ['n000', 'n001', 'n002']) await cell(d, id);
  const r2 = await d.step('reload-free', ['B61'], () => d.reload());
  d.check('B61', r2.status.visit === 'Welcome back. 3 pathway steps restored.', '"n pathway steps" in free mode', r2.status.visit);
  await d.tab('read');
  await d.click('#lessonStart'); await d.settle();
  await d.page.locator('#lessonBody textarea').first().fill(TEXT.opening); await d.settle();
  const r3 = await d.step('reload-lesson-open', ['B59'], () => d.reload());
  d.check('B59', r3.lesson && r3.lesson.fields === TEXT.opening && Object.keys(r3.storage).join(',') === 'words-of-plainness:lattice:author-journal:v1,words-of-plainness:lattice:visit:v1', 'two keys; lesson restored open with its text', Object.keys(r3.storage));
  const so = await d.step('start-over', ['B60'], async () => {
    await Promise.all([d.page.waitForEvent('load'), d.click('#restartVisit')]);
    await d.page.waitForSelector('#tool-root[data-ready="true"]', { state: 'attached' });
  }, { settle: 400 });
  const visit = so.storage['words-of-plainness:lattice:visit:v1'] || {};
  const journal = so.storage['words-of-plainness:lattice:author-journal:v1'] || {};
  d.check('B60', d.dialogs.some(x => x.type === 'confirm') && visit.route && visit.route.path.length === 0 && visit.mode === 'read' && journal.entries && journal.entries[0].text === TEXT.opening, 'Start over clears the visit, keeps the lesson journal', { dialogs: d.dialogs.map(x => x.message), journalKept: journal.entries && journal.entries[0].text });
});
