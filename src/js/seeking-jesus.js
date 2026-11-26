/**
 * SEEKING JESUS OF NAZARETH — /seeking-jesus/ study app (Gate 3 MVP: M0, M1, M2, M5, M6)
 * ---------------------------------------------------------------------------
 * Data: window.SJN (build-time derivation of src/_data/sjn/*.json; never hand-copied).
 * State: every key is namespaced sjn: — lens, map, codeit, convo, selfcheck-pre,
 *        selfcheck-post, goals. All of it stays in this browser. Journal entries are kept
 *        only through window.wopReflections (js/wop-reflections.js) and are never sent off
 *        the device (CODE-SITE-18; the old sjn:journal-queue is carried over there).
 * Numbers: the sjn-stat component is rendered at build (macros/sjn.njk); this script never
 *        computes a percentage.
 */
(function () {
  'use strict';
  var SJN = window.SJN || {};
  var app = document.getElementById('sj-app');
  if (!app) return;
  var MODULE = app.getAttribute('data-module');
  var CHAPTER_ID = 'seeking-jesus';
  var CHAPTER_TITLE = 'Seeking Jesus of Nazareth';
  var LENSES = {
    latter_day_saint: 'Latter-day Saint background',
    other_christian: 'Another Christian tradition',
    exploring: 'Exploring'
  };

  // ------------------------------------------------------------ storage
  // Storage blocked (SITE step 81, CODE-SITE-41): what the reader chooses or writes is held in this
  // page's memory only, never written anywhere and never sent, so the starting point, codings,
  // self-check and goals stay on the page for as long as it is open. Unused while storage works.
  var pageMemory = {};
  function blocked() { return !!(window.wopStorage && !window.wopStorage.available()); }
  function get(key, fallback) {
    try { var v = localStorage.getItem('sjn:' + key); return v == null ? fallback : JSON.parse(v); }
    catch (e) {
      if (blocked() && Object.prototype.hasOwnProperty.call(pageMemory, key)) return JSON.parse(pageMemory[key]);
      return fallback;
    }
  }
  // Returns whether the value was kept, so nothing says "saved" when storage is blocked (CODE-SITE-26).
  function set(key, val) {
    try { localStorage.setItem('sjn:' + key, JSON.stringify(val)); return true; } catch (e) {
      /* private mode */
      if (blocked()) pageMemory[key] = JSON.stringify(val);
      return false;
    }
  }
  // The reader's answers on this page, as journal entries, for the blocked-storage Copy and
  // Download (js/wop-storage-blocked.js). Each module adds what its own journal Save would keep.
  var collectors = [];
  function entry(promptLabel, content, cardId) {
    return { chapterId: CHAPTER_ID, chapterTitle: CHAPTER_TITLE, type: 'commitment', promptLabel: promptLabel, content: content,
      timestamp: new Date().toISOString(), meta: { cardId: cardId, tier: 'seeking-jesus', confidence: 0, module: MODULE } };
  }
  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return [].slice.call((root || document).querySelectorAll(sel)); }
  var byId = {};
  (SJN.predicates || []).forEach(function (p) { byId[p.id] = p; });

  var toastEl;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement('div'); toastEl.className = 'sj-toast'; document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.classList.add('is-on');
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.classList.remove('is-on'); }, 2200);
  }

  // ------------------------------------------------------------ lens
  function lens() { return get('lens', null); }
  function setLens(v) {
    var kept = false;
    if (v === null) { try { localStorage.removeItem('sjn:lens'); } catch (e) { delete pageMemory.lens; } } else { kept = set('lens', v); }
    paintLens();
    document.dispatchEvent(new CustomEvent('sjn:lens', { detail: { lens: v } }));
    return kept;
  }
  function paintLens() {
    var v = lens();
    var badge = $('#sj-lensbadge-v');
    if (badge) badge.textContent = v && LENSES[v] ? LENSES[v] : 'Not chosen';
    $$('.sj-lensbtn').forEach(function (b) { b.classList.toggle('is-on', b.getAttribute('data-lens') === v); });
  }
  var badgeBtn = $('#sj-lensbadge');
  if (badgeBtn) badgeBtn.addEventListener('click', function () {
    if (MODULE === 'orientation') { var t = $('#lens'); if (t) t.scrollIntoView({ behavior: 'smooth' }); }
    else { window.location.href = '/seeking-jesus/#lens'; }
  });
  $$('.sj-lensbtn').forEach(function (b) {
    b.addEventListener('click', function () { if (setLens(b.getAttribute('data-lens'))) toast('Starting point saved'); });
  });
  paintLens();
  if (MODULE === 'orientation') collectors.push(function () {
    var v = lens();
    return v && LENSES[v] ? [entry('Starting point', LENSES[v], 'sjn-lens')] : [];
  });

  // ------------------------------------------------------------ journal bridge
  var journal = {
    save: function (opts) {
      var entry = { chapterId: CHAPTER_ID, chapterTitle: CHAPTER_TITLE, type: 'commitment',
        promptLabel: opts.promptLabel, content: opts.content,
        meta: { cardId: opts.cardId, tier: 'seeking-jesus', confidence: opts.confidence || 0, module: MODULE } };
      // Returns null when the entry could not be kept (storage blocked), so no "Saved" toast shows (CODE-SITE-26).
      if (!window.wopReflections) return null;
      try { window.wopReflections.save(entry); } catch (e) { return null; }
      return entry;
    }
  };

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { toast('Copied'); });
    }
    var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); toast('Copied'); } catch (e) { toast('Copy failed'); }
    document.body.removeChild(ta);
  }

  // ------------------------------------------------------------ scripture links (client side)
  function scriptureUrl(ref) {
    var books = SJN.scripture_books || {};
    var m = String(ref || '').match(/^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/);
    if (!m) return null;
    var path = books[m[1].toLowerCase().trim()];
    if (!path) return null;
    var url = 'https://www.churchofjesuschrist.org/study/scriptures/' + path + '/' + m[2];
    return m[4] ? url + '?lang=eng&id=p' + m[3] + '-p' + m[4] + '#p' + m[3] : url + '?lang=eng&id=p' + m[3] + '#p' + m[3];
  }

  // ============================================================ M1 — map
  function initMap() {
    var state = get('map', { corpus: 'all', code: 'all', mode: 'all', family: 'all', q: '' });
    var cards = $$('.sj-pcard');
    var corpusSel = $('#sj-f-corpus'), modeSel = $('#sj-f-mode'), famSel = $('#sj-f-family'), qIn = $('#sj-f-q');
    var codeBtns = $$('.sj-codebtn');
    function paint() {
      if (corpusSel) corpusSel.value = state.corpus;
      if (modeSel) modeSel.value = state.mode;
      if (famSel) famSel.value = state.family;
      if (qIn) qIn.value = state.q;
      codeBtns.forEach(function (b) { b.classList.toggle('is-on', b.getAttribute('data-code') === state.code); });
      var q = state.q.trim().toLowerCase(), shown = 0;
      cards.forEach(function (c) {
        var ok = (state.corpus === 'all' || c.getAttribute('data-corpus') === state.corpus)
          && (state.code === 'all' || c.getAttribute('data-code') === state.code)
          && (state.mode === 'all' || c.getAttribute('data-mode') === state.mode)
          && (state.family === 'all' || c.getAttribute('data-family') === state.family)
          && (!q || c.textContent.toLowerCase().indexOf(q) !== -1);
        c.classList.toggle('is-hidden', !ok);
        if (ok) shown++;
      });
      var cnt = $('#sj-count');
      if (cnt) cnt.textContent = 'Showing ' + shown + ' of ' + cards.length + ' descriptions';
      set('map', state);
    }
    if (corpusSel) corpusSel.addEventListener('change', function () { state.corpus = corpusSel.value; paint(); });
    if (modeSel) modeSel.addEventListener('change', function () { state.mode = modeSel.value; paint(); });
    if (famSel) famSel.addEventListener('change', function () { state.family = famSel.value; paint(); });
    if (qIn) qIn.addEventListener('input', function () { state.q = qIn.value; paint(); });
    codeBtns.forEach(function (b) { b.addEventListener('click', function () { state.code = b.getAttribute('data-code'); paint(); }); });
    var reset = $('#sj-f-reset');
    if (reset) reset.addEventListener('click', function () { state = { corpus: 'all', code: 'all', mode: 'all', family: 'all', q: '' }; paint(); });
    // deep link: /seeking-jesus/map/#RNR-H22 — clear filters so the card is visible
    if (location.hash && byId[location.hash.slice(1)]) {
      state = { corpus: 'all', code: 'all', mode: 'all', family: 'all', q: '' }; paint();
      var target = document.getElementById(location.hash.slice(1));
      if (target) { var d = target.querySelector('details'); if (d) d.open = true; target.scrollIntoView(); }
    } else { paint(); }
    $$('.sj-copy-sentence').forEach(function (b) {
      b.addEventListener('click', function () {
        var p = byId[b.getAttribute('data-id')];
        if (p) copyText(p.predicate + ' — ' + p.sentence + ' ' + p.summary);
      });
    });
  }

  // ============================================================ M2 — code it yourself
  function initCodeIt() {
    var state = get('codeit', {});
    var exercises = $$('.sj-exercise');
    // G5 (Teaching Practices v1.1; CODE-SITE-20): no count of what is left uncoded, and the
    // project's code and reasoning never wait on a choice ("Show the project's code and reasoning").
    exercises.forEach(function (ex) {
      var id = ex.getAttribute('data-id'), code = ex.getAttribute('data-code');
      var rec = state[id] || {};
      var verdict = $('.sj-verdict', ex), note = $('textarea', ex), saveBtn = $('.sj-save-note', ex), jBtn = $('.sj-to-journal', ex);
      var showBtn = $('.sj-show-code', ex);
      function reveal(pick) {
        ex.classList.add('is-revealed');
        $$('.sj-choice', ex).forEach(function (c) { c.classList.toggle('is-picked', c.getAttribute('data-code') === pick); });
        if (verdict && !pick) { verdict.className = 'sj-verdict'; verdict.textContent = ''; }
        else if (verdict) {
          var same = pick === code;
          verdict.className = 'sj-verdict ' + (same ? 'is-match' : 'is-diff');
          verdict.textContent = same
            ? 'You coded this ' + pick + ', and so did the project.'
            : 'You coded this ' + pick + '; the project coded it ' + code + '. Read the rationale, then decide whether you still differ.';
        }
      }
      $$('.sj-choice', ex).forEach(function (c) {
        c.addEventListener('click', function () {
          rec.pick = c.getAttribute('data-code'); rec.at = new Date().toISOString();
          state[id] = rec; set('codeit', state); reveal(rec.pick);
        });
      });
      if (showBtn) showBtn.addEventListener('click', function () {
        rec.shown = true; state[id] = rec; set('codeit', state); reveal(rec.pick || null);
      });
      if (note) { note.value = rec.note || ''; note.addEventListener('input', function () { rec.note = note.value; state[id] = rec; set('codeit', state); }); }
      if (saveBtn) saveBtn.addEventListener('click', function () { rec.note = note ? note.value : ''; state[id] = rec; if (set('codeit', state)) toast('Saved in this browser'); });
      function journalContent() {
        var p = byId[id];
        return (rec.pick ? 'I coded ' + (p ? p.predicate : id) + ' as ' + rec.pick + '; the project coded it ' + code + '.'
          : (p ? p.predicate : id) + ': the project coded it ' + code + '.')
          + (rec.note ? ' My reasoning: ' + rec.note : '');
      }
      if (jBtn) jBtn.addEventListener('click', function () {
        var p = byId[id];
        if (journal.save({ promptLabel: 'Code It Yourself — ' + (p ? p.predicate : id), content: journalContent(), cardId: 'sjn-codeit-' + id })) toast('Saved to My Discipleship Journal');
      });
      collectors.push(function () {
        if (note) rec.note = note.value;
        if (!rec.pick && !(rec.note && rec.note.trim())) return [];
        var p = byId[id];
        return [entry('Code It Yourself — ' + (p ? p.predicate : id), journalContent(), 'sjn-codeit-' + id)];
      });
      if (rec.pick) reveal(rec.pick);
      else if (rec.shown) reveal(null);
    });
    var clr = $('#sj-codeit-clear');
    if (clr) clr.addEventListener('click', function () {
      if (!confirm('Clear your codings in this browser?')) return;
      state = {}; set('codeit', state);
      exercises.forEach(function (ex) { ex.classList.remove('is-revealed'); $$('.sj-choice', ex).forEach(function (c) { c.classList.remove('is-picked'); }); var t = $('textarea', ex); if (t) t.value = ''; });
    });
  }

  // ============================================================ M5 — conversation builder
  function initConversation() {
    var state = get('convo', { lens: null, script: [] });
    var cur = state.lens || lens() || 'latter_day_saint';
    var lensBtns = $$('.sj-convo-lens');
    function paintLensBtns() {
      lensBtns.forEach(function (b) { b.classList.toggle('is-on', b.getAttribute('data-lens') === cur); });
      $$('.sj-scn').forEach(function (s) { s.classList.toggle('is-hidden', s.getAttribute('data-lens') !== cur); });
      var lbl = $('#sj-convo-lenslabel');
      if (lbl) lbl.textContent = cur === 'latter_day_saint' ? 'You come from a Latter-day Saint background; the questions come from other Christians.'
        : 'You come from another Christian tradition; the questions come from Latter-day Saints.';
      state.lens = cur; set('convo', state);
    }
    lensBtns.forEach(function (b) { b.addEventListener('click', function () { cur = b.getAttribute('data-lens'); paintLensBtns(); }); });
    document.addEventListener('sjn:lens', function (e) { if (e.detail.lens && e.detail.lens !== 'exploring') { cur = e.detail.lens; paintLensBtns(); } });
    paintLensBtns();

    $$('.sj-scn').forEach(function (card) {
      var id = card.getAttribute('data-id');
      var textOf = function () {
        var t = [];
        t.push(card.getAttribute('data-title'));
        t.push('Said to me: ' + $('.sj-scn-line', card).textContent.trim());
        t.push('What is really being asked: ' + $('.sj-scn-asking', card).textContent.trim());
        t.push('Resolves to: ' + $$('.sj-clauses li', card).map(function (li) { return li.textContent.trim(); }).join(' '));
        t.push('A response I could give: ' + $('.sj-scn-response', card).textContent.trim());
        t.push('Avoid: ' + $('.sj-scn-avoid', card).textContent.trim());
        return t.join('\n\n');
      };
      var cp = $('.sj-scn-copy', card); if (cp) cp.addEventListener('click', function () { copyText(textOf()); });
      var chosen = false;   // the reader asked to keep this card (used only when storage is blocked)
      var jb = $('.sj-scn-journal', card); if (jb) jb.addEventListener('click', function () {
        chosen = true;
        if (journal.save({ promptLabel: 'Conversation Builder — ' + card.getAttribute('data-title'), content: textOf(), cardId: 'sjn-scn-' + id })) toast('Saved to My Discipleship Journal');
      });
      collectors.push(function () {
        return chosen ? [entry('Conversation Builder — ' + card.getAttribute('data-title'), textOf(), 'sjn-scn-' + id)] : [];
      });
    });

    // Build your own: pick predicates, assemble the four-clause script
    var picker = $('#sj-build-pick'), list = $('#sj-build-list'), out = $('#sj-build-script');
    function render() {
      if (!list || !out) return;
      list.innerHTML = state.script.map(function (id) {
        var p = byId[id]; if (!p) return '';
        return '<li class="c-' + p.code + '"><b>' + esc(p.predicate) + '</b> — ' + esc(p.sentence) + ' <span class="sj-mute">' + esc(p.summary) + '</span>'
          + ' <button type="button" class="sj-goal-x" data-rm="' + esc(id) + '" aria-label="Remove">×</button></li>';
      }).join('');
      var groups = { A: [], Q: [], D: [], ADDITION: [] };
      state.script.forEach(function (id) { var p = byId[id]; if (p) groups[p.code].push(p); });
      var lines = [];
      Object.keys(groups).forEach(function (k) {
        if (!groups[k].length) return;
        lines.push(SJN.four_clause[k] + ' ' + groups[k].map(function (p) {
          // Additions carry their full proposition as the predicate; inherited rows pair name + summary.
          return p.corpus === 'restoration' ? p.summary.replace(/\.$/, '') : p.predicate + ' (' + p.summary.replace(/\.$/, '') + ')';
        }).join('; ') + '.');
      });
      out.textContent = lines.length ? lines.join('\n') : 'Pick descriptions above to assemble the sentence.';
      // G5 (CODE-SITE-20): with nothing picked the Save button simply rests; no warning.
      var bjBtn = $('#sj-build-journal'); if (bjBtn) bjBtn.disabled = !state.script.length;
      set('convo', state);
      $$('[data-rm]', list).forEach(function (b) { b.addEventListener('click', function () {
        state.script = state.script.filter(function (x) { return x !== b.getAttribute('data-rm'); }); render();
      }); });
    }
    if (picker) picker.addEventListener('change', function () {
      var id = picker.value; if (!id || !byId[id]) return;
      if (state.script.indexOf(id) === -1) state.script.push(id);
      picker.value = ''; render();
    });
    var bc = $('#sj-build-copy'); if (bc) bc.addEventListener('click', function () { if (out) copyText(out.textContent); });
    var bj = $('#sj-build-journal'); if (bj) bj.addEventListener('click', function () {
      if (!state.script.length) return;
      if (journal.save({ promptLabel: 'Conversation Builder — my four-clause sentence', content: out.textContent, cardId: 'sjn-build-' + Date.now() })) toast('Saved to My Discipleship Journal');
    });
    var bx = $('#sj-build-clear'); if (bx) bx.addEventListener('click', function () { state.script = []; render(); });
    collectors.push(function () {
      return (state.script.length && out) ? [entry('Conversation Builder — my four-clause sentence', out.textContent, 'sjn-build')] : [];
    });
    render();
    if (location.hash && byId[location.hash.slice(1)]) {
      if (state.script.indexOf(location.hash.slice(1)) === -1) { state.script.push(location.hash.slice(1)); render(); }
      var b = $('#sj-build'); if (b) b.scrollIntoView();
    }
  }

  // ============================================================ M6 — self-check and goals
  function initSelfCheck() {
    ['pre', 'post'].forEach(function (phase) {
      var state = get('selfcheck-' + phase, {});
      $$('.sj-scale[data-phase="' + phase + '"]').forEach(function (row) {
        var q = row.getAttribute('data-q');
        $$('input', row).forEach(function (inp) {
          if (state[q] === Number(inp.value)) inp.checked = true;
          inp.addEventListener('change', function () { state[q] = Number(inp.value); state._at = new Date().toISOString(); set('selfcheck-' + phase, state); paintCompare(); });
        });
      });
    });
    function paintCompare() {
      var pre = get('selfcheck-pre', {}), post = get('selfcheck-post', {});
      $$('.sj-compare tr[data-q]').forEach(function (tr) {
        var q = tr.getAttribute('data-q');
        $('.c-pre', tr).textContent = pre[q] ? pre[q] + ' / 5' : '—';
        $('.c-post', tr).textContent = post[q] ? post[q] + ' / 5' : '—';
        var d = (pre[q] && post[q]) ? post[q] - pre[q] : null;
        $('.c-delta', tr).textContent = d === null ? '' : (d > 0 ? '▲ ' + d : d < 0 ? '▼ ' + Math.abs(d) : 'same');
      });
    }
    paintCompare();
    function selfCheckLines() {
      var pre = get('selfcheck-pre', {}), post = get('selfcheck-post', {});
      return $$('.sj-compare tr[data-q]').map(function (tr) {
        var q = tr.getAttribute('data-q');
        return $('.c-label', tr).textContent.trim() + ': before ' + (pre[q] || '—') + ', after ' + (post[q] || '—');
      });
    }
    var sc = $('#sj-selfcheck-journal'); if (sc) sc.addEventListener('click', function () {
      if (journal.save({ promptLabel: 'Seeking Jesus of Nazareth — self-check', content: selfCheckLines().join('\n'), cardId: 'sjn-selfcheck' })) toast('Saved to My Discipleship Journal');
    });
    collectors.push(function () {
      var pre = get('selfcheck-pre', {}), post = get('selfcheck-post', {});
      var any = Object.keys(pre).concat(Object.keys(post)).some(function (k) { return k !== '_at'; });
      return any ? [entry('Seeking Jesus of Nazareth — self-check', selfCheckLines().join('\n'), 'sjn-selfcheck')] : [];
    });

    var goals = get('goals', []);
    var list = $('#sj-goals'), form = $('#sj-goalform');
    function renderGoals() {
      if (!list) return;
      // G5 (CODE-SITE-20): no goals is not unfinished; the list is simply empty and the Save button rests.
      var gjBtn = $('#sj-goals-journal'); if (gjBtn) gjBtn.disabled = !goals.length;
      if (!goals.length) { list.innerHTML = ''; return; }
      list.innerHTML = goals.map(function (g, i) {
        return '<li class="sj-goal' + (g.done ? ' is-done' : '') + '">'
          + '<input type="checkbox" aria-label="Done" data-i="' + i + '"' + (g.done ? ' checked' : '') + '>'
          + '<div><div class="sj-goal-text">' + esc(g.text) + '</div><small>' + esc(g.when || '') + (g.done && g.doneAt ? ' · done ' + esc(g.doneAt.slice(0, 10)) : '') + '</small></div>'
          + '<button type="button" class="sj-goal-x" data-x="' + i + '" aria-label="Remove goal">×</button></li>';
      }).join('');
      $$('input[type=checkbox]', list).forEach(function (cb) { cb.addEventListener('change', function () {
        var g = goals[Number(cb.getAttribute('data-i'))]; g.done = cb.checked; g.doneAt = cb.checked ? new Date().toISOString() : null; set('goals', goals); renderGoals();
      }); });
      $$('[data-x]', list).forEach(function (b) { b.addEventListener('click', function () { goals.splice(Number(b.getAttribute('data-x')), 1); set('goals', goals); renderGoals(); }); });
    }
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = $('#sj-goal-text').value.trim(), when = $('#sj-goal-when').value.trim();
      if (!text) return;
      goals.push({ text: text, when: when, done: false, at: new Date().toISOString() }); set('goals', goals);
      $('#sj-goal-text').value = ''; $('#sj-goal-when').value = ''; renderGoals();
    });
    function goalLine(g) { return (g.done ? '[done] ' : '[ ] ') + g.text + (g.when ? ' (' + g.when + ')' : ''); }
    var gj = $('#sj-goals-journal'); if (gj) gj.addEventListener('click', function () {
      if (!goals.length) return;
      var content = goals.map(goalLine).join('\n');
      if (journal.save({ promptLabel: 'Seeking Jesus of Nazareth — my goals', content: content, cardId: 'sjn-goals' })) toast('Saved to My Discipleship Journal');
    });
    collectors.push(function () {
      // Goals added, and a goal still being written in the form.
      var lines = goals.map(goalLine);
      var t = $('#sj-goal-text'), w = $('#sj-goal-when');
      var text = t ? t.value.trim() : '', when = w ? w.value.trim() : '';
      if (text) lines.push(goalLine({ text: text, when: when, done: false }));
      return lines.length ? [entry('Seeking Jesus of Nazareth — my goals', lines.join('\n'), 'sjn-goals')] : [];
    });
    var ex = $('#sj-export'); if (ex) ex.addEventListener('click', function () {
      var pre = get('selfcheck-pre', {}), post = get('selfcheck-post', {});
      var lines = ['Seeking Jesus of Nazareth — my record', 'Starting point: ' + (LENSES[lens()] || 'not chosen'), ''];
      lines.push('Self-check (1–5, before / after):');
      $$('.sj-compare tr[data-q]').forEach(function (tr) { var q = tr.getAttribute('data-q'); lines.push('  ' + $('.c-label', tr).textContent.trim() + ': ' + (pre[q] || '—') + ' / ' + (post[q] || '—')); });
      lines.push('', 'Goals:'); goals.forEach(function (g) { lines.push('  ' + (g.done ? '[done] ' : '[ ] ') + g.text + (g.when ? ' (' + g.when + ')' : '')); });
      var codeit = get('codeit', {});
      var ids = Object.keys(codeit).filter(function (k) { return codeit[k].pick || codeit[k].note; });
      if (ids.length) { lines.push('', 'Code It Yourself:'); ids.forEach(function (id) { var p = byId[id]; lines.push('  ' + (p ? p.predicate : id) + ': ' + (codeit[id].pick ? 'mine ' + codeit[id].pick + ', ' : '') + 'project ' + (p ? p.code : '?') + (codeit[id].note ? ' — ' + codeit[id].note : '')); }); }
      copyText(lines.join('\n'));
    });
    var wipe = $('#sj-wipe'); if (wipe) wipe.addEventListener('click', function () {
      if (!confirm('Erase everything this study has stored in this browser (starting point, codings, goals, self-check)?')) return;
      window.wopStorage.keys('sjn:').forEach(function (k) { window.wopStorage.remove(k); });
      location.reload();
    });
    renderGoals();
  }

  // ============================================================ boot
  if (MODULE === 'map') initMap();
  else if (MODULE === 'code-it') initCodeIt();
  else if (MODULE === 'conversation') initConversation();
  else if (MODULE === 'self-check') initSelfCheck();
  window.SJNApp = { lens: lens, setLens: setLens, journal: journal, scriptureUrl: scriptureUrl,
    pageAnswers: function () { return collectors.reduce(function (all, c) { return all.concat(c()); }, []); } };
})();
