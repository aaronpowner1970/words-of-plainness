/**
 * SEEKING JESUS OF NAZARETH — /seeking-jesus/ study app (Gate 3 MVP: M0, M1, M2, M5, M6)
 * ---------------------------------------------------------------------------
 * Data: window.SJN (build-time derivation of src/_data/sjn/*.json; never hand-copied).
 * State: every key is namespaced sjn: — lens, map, codeit, convo, selfcheck-pre,
 *        selfcheck-post, goals, journal-queue. localStorage-first; when a WoP account is
 *        signed in, journal entries also sync through API.saveCardCommitment and the
 *        queue flushes on wop:auth-login (same pattern as card-chapter commitments).
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
  function get(key, fallback) {
    try { var v = localStorage.getItem('sjn:' + key); return v == null ? fallback : JSON.parse(v); }
    catch (e) { return fallback; }
  }
  function set(key, val) {
    try { localStorage.setItem('sjn:' + key, JSON.stringify(val)); } catch (e) { /* private mode */ }
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
    if (v === null) { try { localStorage.removeItem('sjn:lens'); } catch (e) {} } else { set('lens', v); }
    paintLens();
    document.dispatchEvent(new CustomEvent('sjn:lens', { detail: { lens: v } }));
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
    b.addEventListener('click', function () { setLens(b.getAttribute('data-lens')); toast('Starting point saved'); });
  });
  paintLens();

  // ------------------------------------------------------------ journal bridge
  var journal = {
    save: function (opts) {
      var entry = { chapterId: CHAPTER_ID, chapterTitle: CHAPTER_TITLE, type: 'commitment',
        promptLabel: opts.promptLabel, content: opts.content,
        meta: { cardId: opts.cardId, tier: 'seeking-jesus', confidence: opts.confidence || 0, module: MODULE } };
      if (window.wopReflections) window.wopReflections.save(entry);
      var payload = { chapter_slug: CHAPTER_ID, card_id: opts.cardId, card_title: opts.promptLabel, tier: 'seeking-jesus',
        commitment_text: opts.content, reflection_text: opts.reflection || '', confidence: opts.confidence || 0 };
      if (window.API && API.isAuthenticated && API.isAuthenticated()) {
        API.saveCardCommitment(payload).catch(function (err) {
          console.warn('[SJN] journal sync failed; queued for next login:', err && err.message);
          journal.enqueue(payload);
        });
      } else {
        journal.enqueue(payload);
      }
      return entry;
    },
    enqueue: function (payload) {
      var q = get('journal-queue', []).filter(function (p) { return p.card_id !== payload.card_id; });
      q.push(payload); set('journal-queue', q.slice(-50));
    },
    flush: function () {
      if (!(window.API && API.isAuthenticated && API.isAuthenticated())) return;
      var q = get('journal-queue', []);
      if (!q.length) return;
      var next = function () {
        var p = q.shift();
        if (!p) { set('journal-queue', []); return; }
        API.saveCardCommitment(p).then(next).catch(function () { q.unshift(p); set('journal-queue', q); });
      };
      next();
    }
  };
  document.addEventListener('wop:auth-login', journal.flush);
  setTimeout(journal.flush, 1500);

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
    function paintProgress() {
      var done = exercises.filter(function (e) { return state[e.getAttribute('data-id')] && state[e.getAttribute('data-id')].pick; }).length;
      var el = $('#sj-codeit-progress');
      if (el) el.textContent = done + ' of ' + exercises.length + ' coded';
    }
    exercises.forEach(function (ex) {
      var id = ex.getAttribute('data-id'), code = ex.getAttribute('data-code');
      var rec = state[id] || {};
      var verdict = $('.sj-verdict', ex), note = $('textarea', ex), saveBtn = $('.sj-save-note', ex), jBtn = $('.sj-to-journal', ex);
      function reveal(pick) {
        ex.classList.add('is-revealed');
        $$('.sj-choice', ex).forEach(function (c) { c.classList.toggle('is-picked', c.getAttribute('data-code') === pick); });
        if (verdict) {
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
          state[id] = rec; set('codeit', state); reveal(rec.pick); paintProgress();
        });
      });
      if (note) { note.value = rec.note || ''; note.addEventListener('input', function () { rec.note = note.value; state[id] = rec; set('codeit', state); }); }
      if (saveBtn) saveBtn.addEventListener('click', function () { rec.note = note ? note.value : ''; state[id] = rec; set('codeit', state); toast('Saved in this browser'); });
      if (jBtn) jBtn.addEventListener('click', function () {
        var p = byId[id];
        var content = 'I coded ' + (p ? p.predicate : id) + ' as ' + (rec.pick || '—') + '; the project coded it ' + code + '.'
          + (rec.note ? ' My reasoning: ' + rec.note : '');
        journal.save({ promptLabel: 'Code It Yourself — ' + (p ? p.predicate : id), content: content, cardId: 'sjn-codeit-' + id });
        toast('Saved to My Discipleship Journal');
      });
      if (rec.pick) reveal(rec.pick);
    });
    paintProgress();
    var clr = $('#sj-codeit-clear');
    if (clr) clr.addEventListener('click', function () {
      if (!confirm('Clear your codings in this browser?')) return;
      state = {}; set('codeit', state);
      exercises.forEach(function (ex) { ex.classList.remove('is-revealed'); $$('.sj-choice', ex).forEach(function (c) { c.classList.remove('is-picked'); }); var t = $('textarea', ex); if (t) t.value = ''; });
      paintProgress();
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
      var jb = $('.sj-scn-journal', card); if (jb) jb.addEventListener('click', function () {
        journal.save({ promptLabel: 'Conversation Builder — ' + card.getAttribute('data-title'), content: textOf(), cardId: 'sjn-scn-' + id });
        toast('Saved to My Discipleship Journal');
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
      if (!state.script.length) { toast('Nothing to save yet'); return; }
      journal.save({ promptLabel: 'Conversation Builder — my four-clause sentence', content: out.textContent, cardId: 'sjn-build-' + Date.now() });
      toast('Saved to My Discipleship Journal');
    });
    var bx = $('#sj-build-clear'); if (bx) bx.addEventListener('click', function () { state.script = []; render(); });
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
    var sc = $('#sj-selfcheck-journal'); if (sc) sc.addEventListener('click', function () {
      var pre = get('selfcheck-pre', {}), post = get('selfcheck-post', {});
      var lines = $$('.sj-compare tr[data-q]').map(function (tr) {
        var q = tr.getAttribute('data-q');
        return $('.c-label', tr).textContent.trim() + ': before ' + (pre[q] || '—') + ', after ' + (post[q] || '—');
      });
      journal.save({ promptLabel: 'Seeking Jesus of Nazareth — self-check', content: lines.join('\n'), cardId: 'sjn-selfcheck' });
      toast('Saved to My Discipleship Journal');
    });

    var goals = get('goals', []);
    var list = $('#sj-goals'), form = $('#sj-goalform');
    function renderGoals() {
      if (!list) return;
      if (!goals.length) { list.innerHTML = '<li class="sj-mute">No goals yet.</li>'; return; }
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
    var gj = $('#sj-goals-journal'); if (gj) gj.addEventListener('click', function () {
      if (!goals.length) { toast('No goals yet'); return; }
      var content = goals.map(function (g) { return (g.done ? '[done] ' : '[ ] ') + g.text + (g.when ? ' (' + g.when + ')' : ''); }).join('\n');
      journal.save({ promptLabel: 'Seeking Jesus of Nazareth — my goals', content: content, cardId: 'sjn-goals' });
      toast('Saved to My Discipleship Journal');
    });
    var ex = $('#sj-export'); if (ex) ex.addEventListener('click', function () {
      var pre = get('selfcheck-pre', {}), post = get('selfcheck-post', {});
      var lines = ['Seeking Jesus of Nazareth — my record', 'Starting point: ' + (LENSES[lens()] || 'not chosen'), ''];
      lines.push('Self-check (1–5, before / after):');
      $$('.sj-compare tr[data-q]').forEach(function (tr) { var q = tr.getAttribute('data-q'); lines.push('  ' + $('.c-label', tr).textContent.trim() + ': ' + (pre[q] || '—') + ' / ' + (post[q] || '—')); });
      lines.push('', 'Goals:'); goals.forEach(function (g) { lines.push('  ' + (g.done ? '[done] ' : '[ ] ') + g.text + (g.when ? ' (' + g.when + ')' : '')); });
      var codeit = get('codeit', {});
      var ids = Object.keys(codeit).filter(function (k) { return codeit[k].pick; });
      if (ids.length) { lines.push('', 'Code It Yourself:'); ids.forEach(function (id) { var p = byId[id]; lines.push('  ' + (p ? p.predicate : id) + ': mine ' + codeit[id].pick + ', project ' + (p ? p.code : '?') + (codeit[id].note ? ' — ' + codeit[id].note : '')); }); }
      copyText(lines.join('\n'));
    });
    var wipe = $('#sj-wipe'); if (wipe) wipe.addEventListener('click', function () {
      if (!confirm('Erase everything this study has stored in this browser (starting point, codings, goals, self-check)?')) return;
      var keys = []; for (var i = 0; i < localStorage.length; i++) { var k = localStorage.key(i); if (k && k.indexOf('sjn:') === 0) keys.push(k); }
      keys.forEach(function (k) { localStorage.removeItem(k); });
      location.reload();
    });
    renderGoals();
  }

  // ============================================================ boot
  if (MODULE === 'map') initMap();
  else if (MODULE === 'code-it') initCodeIt();
  else if (MODULE === 'conversation') initConversation();
  else if (MODULE === 'self-check') initSelfCheck();
  window.SJNApp = { lens: lens, setLens: setLens, journal: journal, scriptureUrl: scriptureUrl };
})();
