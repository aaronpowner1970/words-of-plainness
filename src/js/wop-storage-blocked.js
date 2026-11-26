/**
 * WORDS OF PLAINNESS — when a browser blocks storage (SITE step 81, CODE-SITE-41)
 * ================================================================================
 *
 * Rulings SITE-STORAGE-BLOCKED-MESSAGE option 1 (20 Nov 2026) and
 * SITE-BLOCKED-MSG-APPROACHES option 3 (25 Nov 2026).
 *
 * Loaded ONLY when window.wopStorage.available() is false: layouts/base.njk writes this
 * script, /js/wop-storage-blocked-words.js and /css/wop-storage-blocked.css into the page
 * from a one-line loader in <head>, and does nothing at all when storage works. The
 * stylesheet hides the lines that say the reader's words are kept before the page is
 * first drawn; this script then puts the approved sentence where they stood.
 *
 * In each place where a reader writes (the Reflect · Journal · Witness window, the
 * Reflections panel, the card chapters, Seeking Jesus, the Articles, Chapter 6's pathway
 * reflections):
 *   W1, then "Copy my answers" and "Download my answers" (W2), then the help (W5,
 *   closed). Copy puts what the reader has written or chosen in that place, as it
 *   stands, on the clipboard, in the journal download's own text form; on success the
 *   button reads W7 for two seconds; if the clipboard refuses, the text appears in a
 *   selectable box headed W3. Download uses the journal's own download tool and its
 *   four formats (js/wop-reflections-panel.js), fed from the page, not from storage.
 *   Where a place repeats on a page (cards, Articles, exercises), the one block moves to
 *   the box the reader is working in.
 * On /my-reflections/: W4 in place of the empty journal, and W5.
 * On Approaches to Belief: W1 replaces the untrue sentence on the "Take your reflections
 * with you" card, and nothing else.
 *
 * Every word comes from window.WOP_STORAGE_BLOCKED (the approved file, read at build).
 * Nothing is written to storage and nothing is sent anywhere: Copy and Download happen
 * in this browser.
 */
(function () {
    'use strict';

    var W = window.WOP_STORAGE_BLOCKED;
    if (!W || !window.wopStorage || window.wopStorage.available()) return;

    var doc = document;
    var COPIED_MS = 2000;
    var started = false;
    var uid = 0;

    // ------------------------------------------------------------ helpers
    function el(tag, attrs, children) {
        var e = doc.createElement(tag);
        if (attrs) Object.keys(attrs).forEach(function (k) {
            if (k === 'text') e.textContent = attrs[k];
            else if (k === 'className') e.className = attrs[k];
            else if (k === 'hidden') e.hidden = !!attrs[k];
            else e.setAttribute(k, attrs[k]);
        });
        (children || []).forEach(function (c) { if (c != null) e.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c); });
        return e;
    }
    function $(sel, root) { return (root || doc).querySelector(sel); }
    function $$(sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); }
    function R() { return window.wopReflections; }
    function P() { return window.WopReflectionsPanel; }
    function now() { return new Date().toISOString(); }
    function done(node) { if (node) node.classList.add('wop-sb-done'); }

    // Remove one sentence (exactly as the page has it) from an element's text, keeping
    // the rest of the element. Returns true when the sentence was found.
    function dropSentence(node, sentence) {
        if (!node) return false;
        var walker = doc.createTreeWalker(node, NodeFilter.SHOW_TEXT, null);
        var t;
        while ((t = walker.nextNode())) {
            var i = t.nodeValue.indexOf(sentence);
            if (i === -1) continue;
            var before = t.nodeValue.slice(0, i), after = t.nodeValue.slice(i + sentence.length);
            if (!before.trim()) after = after.replace(/^\s+/, '');
            t.nodeValue = before + after;
            return true;
        }
        return false;
    }

    // ------------------------------------------------------------ W5, the help
    function helpBlock() {
        var body = el('div', { className: 'wop-sb-help-body' });
        body.appendChild(el('div', { className: 'wop-sb-para', text: W.intro }));
        var ul = el('ul', { className: 'wop-sb-lines' });
        W.lines.forEach(function (line) {
            var li = el('li', {}, [el('strong', { text: line.label })]);
            var links = line.links || [];
            if (line.confirmed) {
                li.appendChild(doc.createTextNode(line.step));
            } else if (links.length === 1) {
                // The file's condition: the step is replaced by the fallback sentence, which carries the link.
                li.appendChild(doc.createTextNode(' '));
                li.appendChild(outLink(links[0].href, W.fallback));
                links = [];
            } else {
                li.appendChild(doc.createTextNode(' ' + W.fallback));
            }
            if (links.length) {
                var row = el('span', { className: 'wop-sb-links' });
                links.forEach(function (l) { row.appendChild(outLink(l.href, l.text)); });
                li.appendChild(row);
            }
            ul.appendChild(li);
        });
        body.appendChild(ul);
        body.appendChild(el('div', { className: 'wop-sb-para' }, [el('strong', { text: W.warningBold }), W.warningRest]));
        return el('details', { className: 'wop-sb-help' }, [el('summary', { text: W.summary }), body]);
    }
    // Outside links open in a new tab, as the site's other outside links do.
    function outLink(href, text) {
        return el('a', { href: href, target: '_blank', rel: 'noopener', text: text });
    }

    // ------------------------------------------------------------ the block
    // collect() returns the reader's answers in this place, as journal entries.
    function makeBlock(collect) {
        var n = ++uid;
        var copyBtn = el('button', { type: 'button', className: 'wop-sb-btn wop-sb-copy', text: W.copy });
        var dlBtn = el('button', { type: 'button', className: 'wop-sb-btn wop-sb-download', text: W.download,
            'aria-expanded': 'false', 'aria-controls': 'wopSbFormats' + n });
        var fmtRow = el('div', { className: 'wop-sb-formats', id: 'wopSbFormats' + n, hidden: true });
        var formats = (P() && P().formats) || {};
        Object.keys(formats).forEach(function (f) {
            var b = el('button', { type: 'button', className: 'wop-sb-btn wop-sb-btn--format', 'data-format': f, text: formats[f] });
            b.addEventListener('click', function () { download(f, b); });
            fmtRow.appendChild(b);
        });
        var live = el('span', { className: 'wop-sb-sr', role: 'status', 'aria-live': 'polite' });
        var fbId = 'wopSbFallback' + n;
        var fbArea = el('textarea', { id: fbId, className: 'wop-sb-fallback-text', readonly: 'readonly', rows: '6' });
        var fallback = el('div', { className: 'wop-sb-fallback', hidden: true }, [
            el('label', { 'for': fbId, className: 'wop-sb-fallback-head', text: W.w3 }), fbArea
        ]);
        var block = el('div', { className: 'wop-sb', 'data-wop-sb': String(n) }, [
            el('div', { className: 'wop-sb-msg', text: W.w1 }),
            el('div', { className: 'wop-sb-actions' }, [copyBtn, dlBtn, live]),
            fmtRow,
            fallback,
            helpBlock()
        ]);

        var copiedTimer = null;
        function text() {
            var entries = collect() || [];
            if (!entries.length || !P() || !P().textFor) return '';
            return P().textFor(entries);
        }
        function showFallback(t) {
            fbArea.value = t;
            fallback.hidden = false;
            fbArea.focus();
            fbArea.select();
        }
        copyBtn.addEventListener('click', function () {
            var t = text();
            if (!t) return;                      // nothing written yet: no message of any kind
            fallback.hidden = true;
            var ok = function () {
                copyBtn.textContent = W.copied;
                live.textContent = W.copied;
                clearTimeout(copiedTimer);
                copiedTimer = setTimeout(function () { copyBtn.textContent = W.copy; live.textContent = ''; }, COPIED_MS);
            };
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(t).then(ok, function () { showFallback(t); });
                } else {
                    showFallback(t);
                }
            } catch (e) { showFallback(t); }
        });
        dlBtn.addEventListener('click', function () {
            var open = fmtRow.hidden;
            fmtRow.hidden = !open;
            dlBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        function download(format, btn) {
            var entries = collect() || [];
            if (!entries.length || !P() || !P().downloadEntries) return;
            btn.setAttribute('aria-busy', 'true');
            P().downloadEntries(entries, format).then(function () {}, function () {}).then(function () {
                btn.removeAttribute('aria-busy');
            });
        }
        return block;
    }

    // A place that repeats on a page: one block, which moves to the box the reader is working in.
    function moving(block, anchors, place, isField) {
        var current = null;
        function moveTo(anchor, keep) {
            if (!anchor || anchor === current) return;
            var before = keep ? keep.getBoundingClientRect().top : null;
            place(block, anchor);
            current = anchor;
            if (keep) {
                var fix = function () {
                    var d = keep.getBoundingClientRect().top - before;
                    if (Math.abs(d) >= 1) window.scrollBy(0, d);
                    before = keep.getBoundingClientRect().top;
                };
                fix();
                if (window.requestAnimationFrame) window.requestAnimationFrame(fix);
            }
        }
        function onUse(e) {
            var t = e.target;
            if (!t || !t.closest || block.contains(t)) return;
            var a = anchors(t);
            if (!a) return;
            if (e.type === 'click' && !isField(t)) return;
            moveTo(a, t);
        }
        doc.addEventListener('focusin', onUse, true);
        doc.addEventListener('click', onUse, true);
        return moveTo;
    }
    function isControl(t) {
        return !!t.closest('input, textarea, select, button, [role="button"], [role="tab"], label');
    }

    // ------------------------------------------------------------ 1. Reflect · Journal · Witness window
    function rjwWindow() {
        var panel = doc.getElementById('rjwPanel');
        if (!panel) return;
        var ta = doc.getElementById('reflect-ta');
        if (ta) {
            // Keep "Your thoughts are private by default."; drop the two sentences that say the answers are kept.
            ta.setAttribute('placeholder', (ta.getAttribute('placeholder') || '')
                .replace(' Your answers stay on this device.', '').replace(' Open Your reflections to download them.', ''));
        }
        var block = makeBlock(function () {
            return (window.RJW && window.RJW.pageAnswers) ? window.RJW.pageAnswers() : [];
        });
        block.classList.add('wop-sb--rjw');
        var body = panel.querySelector('.rjw-body');
        if (body && body.parentNode === panel) panel.insertBefore(block, body.nextSibling);
        else panel.appendChild(block);
    }

    // ------------------------------------------------------------ 2. the Reflections panel
    function reflectionsPanel() {
        var panel = doc.getElementById('wopReflectionsPanel');
        if (!panel || !P()) return;
        var sub = panel.querySelector('.wop-rp-sub');
        if (sub) sub.hidden = true;
        var block = makeBlock(function () { return P().questionEntries ? P().questionEntries() : []; });
        block.classList.add('wop-sb--panel');
        var body = panel.querySelector('.wop-rp-body');
        if (body) body.insertBefore(block, body.firstChild);
    }

    // ------------------------------------------------------------ 4. card chapters
    function cardChapter() {
        var saves = $$('.card-save-btn');
        if (!saves.length) return;
        var chapterId = doc.body.dataset.chapter || 'unknown';
        var title = R() ? R().titleFromSlug(chapterId) : chapterId;
        function collect() {
            var out = [], ts = now();
            var confidence = $$('.star-btn.active').length;
            saves.forEach(function (btn) {
                var card = btn.dataset.card;
                var cardEl = doc.getElementById('card-' + card);
                var h3 = cardEl && cardEl.querySelector('.card-header-text h3');
                var cardTitle = h3 ? h3.textContent : '';
                // The same label the card's own Save keeps (js/card-chapter.js).
                var selected = doc.querySelector('input[name="commit-' + card + '"]:checked');
                if (selected) {
                    var labelText = selected.value;
                    if (selected.value === 'custom') {
                        var row = selected.closest('.custom-input-row');
                        var field = row && row.querySelector('input[type="text"]');
                        labelText = (field && field.value) ? field.value : 'Custom practice (not specified)';
                    } else if (selected.value === 'na') {
                        labelText = 'Skipped';
                    } else {
                        var opt = selected.closest('.commitment-option');
                        var textEl = opt && opt.querySelector('.option-text');
                        if (textEl) {
                            var clone = textEl.cloneNode(true);
                            var tag = clone.querySelector('.option-tag');
                            if (tag) tag.remove();
                            labelText = clone.textContent.trim();
                        }
                    }
                    if (labelText.length > 80) labelText = labelText.substring(0, 77) + '…';
                    out.push({ type: 'commitment', chapterId: chapterId, chapterTitle: title, promptLabel: cardTitle,
                        content: labelText, timestamp: ts, meta: { cardId: 'card-' + card, tier: selected.value, confidence: confidence } });
                }
                var area = cardEl && cardEl.querySelector('.reflection-area');
                if (area && area.value.trim()) {
                    out.push({ type: 'reflection', chapterId: chapterId, chapterTitle: title, promptLabel: cardTitle + ' (Reflection)',
                        content: area.value.trim(), timestamp: ts, meta: { cardId: 'card-' + card } });
                }
            });
            return out;
        }
        var block = makeBlock(collect);
        var panels = $$('.card-panel[data-panel="personalize"]');
        var summary = $('.summary-section .summary-card');
        var moveTo = moving(block, function (t) {
            var tab = t.closest('.card-tab[data-tab="personalize"]');
            if (tab) return doc.querySelector('.card-panel[data-panel="personalize"][data-card="' + tab.dataset.card + '"]');
            var p = t.closest('.card-panel[data-panel="personalize"]');
            if (p) return p;
            return (summary && summary.contains(t)) ? summary : null;
        }, function (b, anchor) {
            if (anchor === summary) {
                var sub = summary.querySelector('.summary-subtitle');
                summary.insertBefore(b, sub ? sub.nextSibling : summary.firstChild.nextSibling);
            } else {
                anchor.appendChild(b);
            }
        }, isControl);
        moveTo(panels[0] || summary, null);
    }

    // ------------------------------------------------------------ 5. Seeking Jesus
    function seekingJesus() {
        var app = doc.getElementById('sj-app');
        if (!app || !window.SJNApp || !window.SJNApp.pageAnswers) return;
        var module = app.getAttribute('data-module');
        var note = null;   // where the untrue statement stood
        if (module === 'code-it') {
            note = app.querySelector('.sj-note');
            if (note && !dropSentence(note, 'Your codings stay in this browser.')) note.hidden = true;
        } else if (module === 'orientation') {
            note = app.querySelector('#lens .sj-mute');
            if (note && !dropSentence(note, 'Your choice is stored only in this browser.')) note.hidden = true;
        } else if (module === 'self-check') {
            note = app.querySelector('#goals .sj-note');
            if (note) note.hidden = true;
        }
        done(note);
        var collectable = { 'code-it': 1, orientation: 1, conversation: 1, 'self-check': 1 };
        if (!collectable[module]) return;    // the map: nothing written there but My questions (the panel)
        var block = makeBlock(function () { return window.SJNApp.pageAnswers(); });
        var noteWrap = note && note.closest('.sj-wrap');
        var moveTo = moving(block, function (t) {
            var a = t.closest('.sj-exercise, .sj-scn, .sj-wrap');
            if (!a || !app.contains(a)) return null;
            if (a.classList.contains('sj-wrap') && !a.querySelector('input, textarea, select, .sj-lensbtn, .sj-btn')) return null;
            return a;
        }, function (b, anchor) {
            if (anchor === noteWrap && note) note.parentNode.insertBefore(b, note);
            else anchor.appendChild(b);
        }, isControl);
        var first = noteWrap || $$('.sj-scn', app).filter(function (s) { return !s.classList.contains('is-hidden'); })[0]
            || app.querySelector('.sj-exercise');
        moveTo(first, null);
    }

    // ------------------------------------------------------------ 6. Chapter 6 pathway reflections
    function pathwayReflections() {
        var saves = $$('.reflection-section .reflection-save');
        if (!saves.length) return;
        var LABELS = { assess: 'Honest Assessment', align: 'What Stirred in Me', act: 'My Commitment' };
        var block = makeBlock(function () {
            var ts = now();
            return $$('.reflection-textarea').filter(function (ta) { return ta.value.trim(); }).map(function (ta) {
                return { type: 'reflection', chapterId: '06-embrace-the-savior', chapterTitle: 'Embrace the Savior',
                    promptLabel: LABELS[ta.dataset.step] || ta.dataset.step, content: ta.value, timestamp: ts,
                    meta: { pathway: ta.dataset.path, step: ta.dataset.step } };
            });
        });
        var moveTo = moving(block, function (t) {
            var s = t.closest('.reflection-section');
            return s ? s.querySelector('.reflection-save') : null;
        }, function (b, anchor) { anchor.appendChild(b); }, isControl);
        moveTo(saves[0], null);
    }

    // ------------------------------------------------------------ 7. the Articles
    function articles() {
        if (/^\/articles\/first-edition\//.test(location.pathname)) return;   // AOID2 step 313 settles that page
        var boxes = $$('.article-rjw');
        var learners = $$('.an-learner');
        if (!boxes.length && !learners.length) return;
        var ID = 'articles-of-interfaith-discipleship', TITLE = 'Articles of Interfaith Discipleship';
        learners.forEach(function (w) {
            var n = w.querySelector('.an-learner-note');
            if (n && !dropSentence(n, 'Kept only in this browser.')) n.hidden = true;
            done(n);
        });
        function articleTitle(node) {
            var scope = node.closest('.article-section, section, article');
            while (scope) {
                var ta = scope.querySelector('.rjw-textarea');
                if (ta) return (ta.getAttribute('aria-label') || '').replace(/^Reflect on /, '');
                scope = scope.parentElement && scope.parentElement.closest('.article-section, section, article');
            }
            return '';
        }
        // In page order: each Article's reflection (as /articles/ keeps it), then its own question (T4).
        function collect() {
            var out = [], ts = now();
            $$('.rjw-textarea, .an-learner-box').forEach(function (ta) {
                if (!ta.value.trim()) return;
                if (ta.classList.contains('rjw-textarea')) {
                    var id = (ta.dataset.rjwKey || '').replace(/^rjw-/, '');
                    var box = ta.closest('.article-rjw');
                    var p = box && box.querySelector('.rjw-prompt');
                    out.push({ type: 'reflect', chapterId: ID, chapterTitle: TITLE, promptLabel: p ? p.textContent.trim() : '',
                        content: ta.value, timestamp: ts,
                        meta: { key: 'aoid:' + id, article: id, section: (ta.getAttribute('aria-label') || '').replace(/^Reflect on /, '') } });
                } else {
                    var w = ta.closest('.an-learner');
                    var label = w && w.querySelector('.an-learner-label');
                    out.push({ type: 'reflection', chapterId: ID, chapterTitle: TITLE, promptLabel: label ? label.textContent.trim() : '',
                        content: ta.value, timestamp: ts, meta: { section: w ? articleTitle(w) : '' } });
                }
            });
            return out;
        }
        var block = makeBlock(collect);
        var moveTo = moving(block, function (t) {
            return t.closest('.article-rjw, .an-learner');
        }, function (b, anchor) { anchor.parentNode.insertBefore(b, anchor.nextSibling); }, isControl);
        var all = $$('.article-rjw, .an-learner');
        moveTo(all[0], null);
    }

    // ------------------------------------------------------------ 3. /my-reflections/
    function myReflections() {
        var empty = doc.getElementById('djEmpty');
        var acc = doc.getElementById('chapterAccordion');
        if (!empty || !acc) return;
        var block = el('div', { className: 'wop-sb wop-sb--journal' }, [
            el('div', { className: 'wop-sb-msg', text: W.w4 }),
            helpBlock()
        ]);
        acc.parentNode.insertBefore(block, acc.nextSibling);
    }

    // ------------------------------------------------------------ 8. Approaches to Belief
    function approaches() {
        var dl = doc.getElementById('ab-dl');
        var card = dl && dl.parentNode;
        var p = card && $$('p', card).filter(function (x) { return x.textContent.indexOf('Everything you wrote is saved only in this browser.') !== -1; })[0];
        if (!p) return;
        var walker = doc.createTreeWalker(p, NodeFilter.SHOW_TEXT, null), t;
        while ((t = walker.nextNode())) {
            var s = 'Everything you wrote is saved only in this browser.';
            var i = t.nodeValue.indexOf(s);
            if (i !== -1) { t.nodeValue = t.nodeValue.slice(0, i) + W.w1 + t.nodeValue.slice(i + s.length); break; }
        }
        done(p);
    }

    // ------------------------------------------------------------ start
    function start() {
        if (started) return;
        started = true;
        var path = location.pathname;
        if (path === '/my-reflections/') { myReflections(); return; }
        if (path === '/studies/approaches-to-belief/') { approaches(); return; }
        [rjwWindow, reflectionsPanel, cardChapter, seekingJesus, pathwayReflections, articles].forEach(function (fn) {
            try { fn(); } catch (e) { /* never block the page */ }
        });
    }
    if (doc.readyState === 'complete') start();
    else {
        doc.addEventListener('DOMContentLoaded', start);
        window.addEventListener('load', start);
    }
})();
