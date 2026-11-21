// Code that runs inside the page. Everything here is applied identically to the
// reference and the candidate; none of it changes what either page does, except
// window.print, which records the call instead of opening a print dialog.

// Installed before any page script runs (context.addInitScript).
export function initScript({ seed, blockStorage }) {
  return `(() => {
  // Seeded Math.random (mulberry32). Same seed on both sides, reset on every page load.
  let a = ${Number(seed)} >>> 0;
  const P = window.__parity = { randomCalls: 0, prints: [], clipboard: [], media: [], blobs: [], errors: [], storageBlocked: ${blockStorage ? 'true' : 'false'} };
  const seeded = function random() {
    P.randomCalls++;
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  Object.defineProperty(Math, 'random', { value: seeded, writable: true, configurable: true });
  ${blockStorage ? `['localStorage', 'sessionStorage', 'indexedDB'].forEach(function (n) {
    Object.defineProperty(window, n, { get() { throw new DOMException('blocked', 'SecurityError'); }, configurable: true });
  });` : ''}
  // Print: record the call and leave the print sheet in the DOM so the harness can render it
  // in print media. The harness fires afterprint itself once the sheet is captured.
  window.print = function () {
    const sheets = Array.from(document.querySelectorAll('.tl-print-sheet'));
    P.prints.push({ sheets: sheets.length, classes: sheets.map(s => s.className) });
  };
  // Clipboard: record what the page asks to copy, then let the real call run.
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      const orig = navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = function (text) { P.clipboard.push({ via: 'clipboard.writeText', text: String(text) }); return orig(text); };
    }
  } catch (e) {}
  const execOrig = document.execCommand.bind(document);
  document.execCommand = function (cmd, ...rest) {
    if (String(cmd).toLowerCase() === 'copy') {
      const el = document.activeElement;
      const text = el && 'value' in el ? el.value : String(window.getSelection());
      P.clipboard.push({ via: 'execCommand', text });
    }
    return execOrig(cmd, ...rest);
  };
  // Blob URLs: keep the text of every Blob the page turns into a URL (the .txt exports).
  const cou = URL.createObjectURL.bind(URL);
  URL.createObjectURL = function (obj) {
    const url = cou(obj);
    if (obj instanceof Blob) {
      const rec = { type: obj.type, size: obj.size, text: null };
      P.blobs.push(rec);
      obj.text().then(t => { rec.text = t; });
    }
    return url;
  };
  // Media events (capture phase reaches non-bubbling media events).
  for (const ev of ['seeking', 'play', 'pause', 'ended']) {
    document.addEventListener(ev, e => {
      const t = e.target;
      if (!(t instanceof HTMLMediaElement)) return;
      const rec = { ev, el: t.id || t.tagName.toLowerCase() };
      if (ev === 'seeking' || ev === 'play') rec.t = Math.round(t.currentTime * 1000) / 1000;
      P.media.push(rec);
    }, true);
  }
  window.addEventListener('error', e => P.errors.push(String(e.message || e)));
  window.addEventListener('unhandledrejection', e => P.errors.push('unhandledrejection: ' + String(e.reason && (e.reason.message || e.reason))));
})();`;
}

// State snapshot, taken after every scripted step. Returns plain JSON.
export function snapshotInPage() {
  const root = document.getElementById('tool-root') || document.body;
  const q = s => root.querySelector(s);
  const norm = s => (s == null ? null : String(s).replace(/ /g, ' ').replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim());
  const tc = s => { const e = typeof s === 'string' ? q(s) : s; return e ? norm(e.textContent).replace(/\s+/g, ' ') : null; };
  const it = s => { const e = typeof s === 'string' ? q(s) : s; return e ? norm(e.innerText) : null; };
  const shown = e => !!e && !e.closest('[hidden]') && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden';
  const keyOf = e => e.id || (e.dataset.mode && 'mode:' + e.dataset.mode) || (e.dataset.lens && 'lens:' + e.dataset.lens) ||
    (e.dataset.gridDisplay && 'display:' + e.dataset.gridDisplay) || (e.dataset.node && 'node:' + e.dataset.node) || tc(e);
  const s = {};
  s.title = document.title;
  s.activeTab = Array.from(root.querySelectorAll('[data-mode].tl-active')).map(b => b.dataset.mode).join(',');
  s.activePanel = Array.from(root.querySelectorAll('.tl-mode.tl-active')).map(m => m.id).join(',');
  s.modeHead = ['modeTitle', 'modeSub', 'modePill'].map(id => tc('#' + id)).join(' | ');
  s.guideText = it('#coachPanel');
  s.coach = ['coachPhase', 'coachHeadline', 'coachProgress', 'coachNarrative', 'coachThink'].map(id => tc('#' + id)).join(' | ');
  s.route = { name: tc('#pathName'), count: tc('#pathCount'),
    nodes: Array.from(root.querySelectorAll('#pathList .tl-path-node')).map(r => tc(r.querySelector('strong')) + ' [' + tc(r.querySelector('small')) + ']').join(' / '),
    empty: tc('#pathList > p') };
  s.pressed = Array.from(root.querySelectorAll('[aria-pressed]')).filter(e => !e.closest('#lessonBody')).map(e => keyOf(e) + '=' + e.getAttribute('aria-pressed')).join('; ');
  const ids = ['gridReflection', 'cubeReflection', 'openReflection', 'gridNotice', 'recursionPreview', 'recursionReady', 'authorLesson', 'poemContext', 'reversePath', 'focusStatus', 'lessonPrev', 'lessonNext', 'restartVisit', 'readAloud'];
  s.hidden = ids.map(id => { const e = q('#' + id); return id + '=' + (e ? (e.hidden ? 'hidden' : shown(e) ? 'shown' : 'not-rendered') : 'absent'); }).join('; ');
  s.disabled = ['undoPath', 'redoPath', 'undoGrid', 'redoGrid', 'clearGrid', 'undoViewer', 'redoViewer', 'clearViewer', 'undoRecursion', 'redoRecursion', 'clearRecursion', 'reversePath']
    .map(id => { const e = q('#' + id); return id + '=' + (e ? (e.disabled ? 'off' : 'on') : 'absent'); }).join('; ');
  s.cells = Array.from(root.querySelectorAll('.tl-cell')).map(x => x.dataset.node + ':' + (x.classList.contains('tl-selected') ? 'S' : '') +
    (x.classList.contains('tl-valid-next') ? 'V' : '') + (x.classList.contains('tl-unavailable') ? 'U' : '') + (x.classList.contains('tl-spotlight') ? 'P' : '')).join(' ');
  s.gridDisplay = (q('#gridVisual') || {}).dataset ? q('#gridVisual').dataset.display : null;
  s.gridExplain = tc('#gridViewExplain');
  s.gridNotice = q('#gridNotice') && !q('#gridNotice').hidden ? tc('#gridNoticeTitle') + ' — ' + tc('#gridNoticeBody') : '';
  const val = id => { const e = q('#' + id); return e ? (e.type === 'checkbox' ? String(e.checked) : e.value) : null; };
  s.values = { pathRule: val('pathRule'), hintLevel: val('hintLevel'), beforeNote: val('beforeNote'), afterNote: val('afterNote'), fitScore: val('fitScore'), layerFilter: val('layerFilter'), showWires: val('showWires') };
  s.cube = ['explode', 'wireLabel', 'wireStatus', 'focusStatus', 'canvasStatus'].map(id => tc('#' + id)).join(' | ');
  s.status = { selection: tc('#selectionStatus'), visit: tc('#visitStatus'), freshExport: tc('#freshExportStatus'), audioError: tc('#audioError'), contextAudioError: tc('#contextAudioError') };
  s.dialogs = ['freshRouteDialog', 'cubeFilm'].map(id => { const d = q('#' + id); return id + '=' + (d ? (d.open ? 'open' : 'closed') : 'absent'); }).join('; ');
  const film = q('#cubeFilm video');
  s.filmPaused = film ? String(film.paused) : null;
  s.recursion = { stanza: it('#stanzaReflection'), coda: it('#codaReflection'), lensPrompt: tc('#lensPrompt'), connectionPrompt: tc('#connectionPrompt'),
    returnTo: tc('#returnToLattice'), exploreAnother: tc('#exploreAnotherRoute'), stepsRemaining: tc('#recursionStepsRemaining') };
  s.audio = { label: tc('#audioLabel'), contextLabel: tc('#contextAudioLabel'),
    spokenRead: Array.from(root.querySelectorAll('#plainPoem p')).map((p, i) => p.classList.contains('tl-spoken-line') ? i : -1).filter(i => i >= 0).join(','),
    spokenPanel: Array.from(root.querySelectorAll('#contextText button')).map((p, i) => p.classList.contains('tl-spoken-line') ? i : -1).filter(i => i >= 0).join(',') };
  s.stacked = { read: !!q('#plainPoem.tl-stacked'), lesson: !!q('#lessonBody.tl-stacked'), panel: !!q('#contextText.tl-stacked') };
  const lesson = q('#authorLesson');
  if (lesson && !lesson.hidden) {
    const disclosure = q('#lessonBody [aria-controls="lessonPerspective"]');
    s.lesson = { menu: val('lessonMenu'), body: it('#lessonBody'), storage: tc('#lessonStorage'),
      prev: (q('#lessonPrev').hidden ? 'hidden' : tc('#lessonPrev')), next: (q('#lessonNext').hidden ? 'hidden' : tc('#lessonNext')),
      disclosureDisabled: disclosure ? String(disclosure.disabled) : null, disclosureExpanded: disclosure ? disclosure.getAttribute('aria-expanded') : null,
      perspectiveHidden: q('#lessonPerspective') ? String(q('#lessonPerspective').hidden) : null,
      fields: Array.from(root.querySelectorAll('#lessonBody textarea')).map(t => t.value).join(' ¦ '),
      revisitPressed: (q('#lessonBody [aria-pressed]') || { getAttribute: () => null }).getAttribute('aria-pressed') };
  } else s.lesson = null;
  const ctx = q('#poemContext');
  s.panel = ctx ? { hidden: String(ctx.hidden), place: tc('#contextPlace'), lineAction: val('contextLineAction'),
    current: Array.from(root.querySelectorAll('#contextText button')).findIndex(b => b.getAttribute('aria-current') === 'true'),
    markers: Array.from(root.querySelectorAll('#contextText button')).map(b => (b.dataset.marker || '·') + '|' + (b.title || '')).join(' ; ') } : null;
  s.tooltip = q('#tooltip') && q('#tooltip').style.display === 'block' ? tc('#tooltip') : '';
  s.focus = document.activeElement ? (document.activeElement.id || document.activeElement.tagName.toLowerCase()) : null;
  return s;
}

// Static inventory: the page's fixed text and structure, taken once at load.
export function inventoryInPage() {
  const root = document.getElementById('tool-root') || document.body;
  const norm = s => (s == null ? null : String(s).replace(/ /g, ' ').replace(/\s+/g, ' ').trim());
  const tc = s => { const e = typeof s === 'string' ? root.querySelector(s) : s; return e ? norm(e.textContent) : null; };
  const all = (s, f = tc) => Array.from(root.querySelectorAll(s)).map(f);
  const inv = {};
  inv.title = document.title;
  inv.mainCount = document.querySelectorAll('main').length;
  inv.labHeader = tc('header.tl-site');
  inv.intro = tc('.tl-intro h2') + ' || ' + tc('.tl-intro p');
  inv.version = tc('.tl-version');
  inv.tabs = all('.tl-tabs > *').join(' ');
  inv.tabModes = all('[data-mode]', e => e.dataset.mode).join(',');
  inv.visitControls = all('.tl-visit-controls button').join(' | ');
  inv.scene = tc('#sceneTitle') + ' || ' + tc('.tl-scene p');
  inv.sceneEmphasis = all('.tl-scene p strong > em').join(' | ');
  inv.poemTitle = tc('.tl-poem-area h2') + ' || ' + tc('.tl-byline');
  inv.poemLines = all('#plainPoem p').join('\n');
  inv.poemLineRoles = all('#plainPoem p', e => (e.getAttribute('role') || '') + ':' + (e.getAttribute('aria-label') || '')).join('\n');
  inv.readButtons = all('#readMode .tl-read-actions button').join(' | ');
  inv.readHeader = all('.tl-read-header-audio button').join(' | ');
  inv.transport = all('.tl-transport', e => norm(e.textContent) + ' [' + e.querySelectorAll('input[type=range],button').length + ' controls]').join(' | ');
  inv.details = all('details', e => {
    let depth = 0; for (let p = e.parentElement; p; p = p.parentElement) if (p.tagName === 'DETAILS') depth++;
    return depth + ':' + (e.open ? 'open' : 'closed') + ':' + tc(e.querySelector(':scope > summary'));
  }).join('\n');
  inv.firstTime = tc(Array.from(root.querySelectorAll('details')).find(d => /First time here/.test(d.textContent)));
  inv.thesis = tc('.tl-read-thesis');
  inv.selects = all('select', e => (e.id || '?') + ': ' + Array.from(e.options).map(o => o.value + '=' + norm(o.text) + (o.defaultSelected ? '*' : '')).join(' | ')).join('\n');
  inv.lenses = all('.tl-lens', e => e.dataset.lens + ':' + tc(e) + ':' + e.classList.contains('tl-active')).join(' | ');
  inv.displaySwitch = all('[data-grid-display]', e => e.dataset.gridDisplay + ':' + tc(e)).join(' | ');
  inv.cameraButtons = all('.tl-camera-row button').join(' | ');
  inv.editRows = all('.tl-path-edit-row', e => all2(e)).join(' || ');
  function all2(e) { return Array.from(e.querySelectorAll('button')).map(b => b.id + ':' + tc(b)).join(' | '); }
  inv.stanzaHeadings = all('.tl-stanza-heading').join(' | ');
  inv.voiceHeadings = all('.tl-voice-headings').join(' | ');
  inv.cells = all('.tl-cell', e => e.dataset.node + '=' + tc(e)).join('\n');
  inv.examples = all('#examples button').join(' | ');
  inv.guideButtons = all('#coachPanel button', e => (e.id || '') + ':' + tc(e)).join(' | ');
  inv.recursionStatic = tc('.tl-recursion > .tl-kicker') + ' || ' + all('.tl-step').join(' | ') + ' || ' + tc('.tl-center-highlight');
  inv.recursionButtons = all('#recursionMode button', e => (e.id || '') + ':' + tc(e)).join(' | ');
  inv.fields = all('textarea', e => (e.id || '?') + ':' + (e.placeholder || '') + ':' + tc(e.closest('label') && e.closest('label').querySelector('span'))).join('\n');
  inv.cubeStatic = tc('#cubeFilmOpen') + ' || ' + tc('#cubeFilm details') + ' || ' + tc('.tl-view-legend') + ' || ' + tc('.tl-viewer-corner') + ' || canvas:' + ((root.querySelector('canvas') || {}).getAttribute ? root.querySelector('canvas').getAttribute('aria-label') : '');
  inv.freshDialog = tc('#freshRouteDialog');
  inv.panelStatic = tc('#poemContext .tl-context-tools') + ' || ' + tc('#poemContext .tl-context-credit');
  inv.lessonControls = all('#authorLesson > .tl-side-actions button', e => e.id + ':' + tc(e)).join(' | ');
  inv.commentary = tc('.tl-commentary');
  inv.commentarySummary = tc('.tl-commentary > summary');
  inv.structural = tc(Array.from(root.querySelectorAll('.tl-right > section.tl-card')).find(s => /Structural integrity/.test(s.textContent)));
  inv.footer = tc('.tl-footer');
  inv.links = all('a[href]', e => tc(e) + ' → ' + e.getAttribute('href')).join('\n');
  inv.liveRegions = all('[aria-live]', e => (e.id || e.className) + '=' + e.getAttribute('aria-live')).join(' | ');
  inv.roleStatus = root.querySelectorAll('[role=status]').length;
  inv.ids = Array.from(root.querySelectorAll('[id]')).map(e => e.id).filter(id => id).join(' ');
  inv.rewindStopSlider = all('button, input[type=range]', e => tc(e)).filter(t => /rewind|^stop$|elapsed|seek/i.test(t || '')).join(' | ') +
    ' [ranges:' + root.querySelectorAll('input[type=range]').length + ']';
  inv.explorerColumn = root.querySelectorAll('#pathExplorer, .tl-path-explorer').length;
  return inv;
}

// Reads every localStorage key back as JSON (or the error name when storage is blocked).
export function storageInPage() {
  try {
    const ls = window.localStorage;
    const out = {};
    for (let i = 0; i < ls.length; i++) {
      const k = ls.key(i);
      const raw = ls.getItem(k);
      try { out[k] = JSON.parse(raw); } catch { out[k] = { __unparsed: raw }; }
    }
    return Object.fromEntries(Object.entries(out).sort(([a], [b]) => (a < b ? -1 : 1)));
  } catch (e) {
    return { __error: e.name };
  }
}
