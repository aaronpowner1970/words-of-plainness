/**
 * WORDS OF PLAINNESS — the Reflections panel (device-only journal)
 * =================================================================
 *
 * CODE-SITE-18, SITE step 27; spec WoP_SITE_JournalDeviceOnly_Spec_20261024.md,
 * Part 3 and 6.4. One panel on every page that asks the reader to write.
 *
 *   - A tab at the page edge, "Your reflections (n)", n = answers on this device
 *     for this page; a small dot while any of them is not yet downloaded.
 *   - The panel: the reader's answers for this page, newest first, each with its
 *     prompt; "Not yet downloaded" beside new ones; My questions; Download (DOCX,
 *     PDF, Markdown, text; this page or everything on this device); Clear.
 *   - Where Document Picture-in-Picture exists, "Pop out" moves the panel into a
 *     small always-on-top window; closing that window brings it back.
 *   - Downloads are made in the browser. The DOCX writer (/js/wop-docx.js, this
 *     site), the PDF library (pdfmake, cdnjs) and the PDF font (Noto Sans, this
 *     site, /assets/fonts/pdf/) are loaded only when the reader asks for that
 *     format. Nothing the reader wrote is sent anywhere.
 *
 * Page configuration: window.WOP_REFLECTION_PAGE = { ids: [...], title, fileSlug }
 * (components/reflections-panel.njk). Store: window.wopReflections.
 *
 * On /my-reflections/ (spec 3.6) the page sets { inline: '#selector', fileSlug: 'all' }
 * instead: the same Download and Clear actions are placed in that element, for
 * everything on this device, and no tab or floating panel is made.
 */
(function () {
    'use strict';

    var CFG = window.WOP_REFLECTION_PAGE;
    var R = window.wopReflections;
    if (!CFG || !R) return;
    if (!CFG.inline && (!CFG.ids || !CFG.ids.length)) return;

    // Reader-facing wording. The quoted lines are the approved wording, word for
    // word: spec 6.4 (heading, subheading, invitation, marker, confirmation),
    // spec 3.1 / 3.3 / 3.5 (tab, My questions, scope names, Clear), and the
    // approved Part 6.1 sentence reused as the after-download suggestion.
    var T = {
        tab: 'Your reflections',
        heading: 'Your reflections',
        sub: 'Kept only on this device. Download to keep them.',
        questions: 'My questions',
        invite: 'What question is this raising for you? Write it down; it is yours to keep.',
        // Teaching Practices v1.1, gate G5, word for word (src/_data/g5.js). The panel is its own
        // panel, so My questions carries the first-prompt line; the page passes "read on" or
        // "continue" (components/reflections-panel.njk).
        g5: CFG.g5 || 'You are invited to pause and write a personal reflection here, or simply to read on.',
        marker: 'Not yet downloaded',
        clear: 'Clear my answers from this browser',
        confirm: function (n) { return n === 1 ? 'Remove 1 answer from this browser? This cannot be undone.' : 'Remove all ' + n + ' answers from this browser? This cannot be undone.'; },
        suggest: 'If you share this computer with others, use “Clear my answers from this browser” when you are finished.',
        scopePage: 'This page',
        scopeAll: 'Everything on this device',
        fileTitle: 'My Reflections — Words of Plainness',
        // Interface labels
        download: 'Download',
        popout: 'Pop out',
        close: 'Close',
        saveQuestion: 'Save question',
        remove: 'Remove',
        cancel: 'Cancel',
        journal: 'My Discipleship Journal',
        written: 'Written',
        writtenBefore: 'Written before',
        downloadedOn: 'Downloaded',
        prompt: 'Prompt',
        formats: { docx: 'Word (.docx)', pdf: 'PDF', md: 'Markdown (.md)', txt: 'Text (.txt)' },
        types: {
            reflect: 'Reflect', journal: 'Journal', witness: 'Witness', question: 'My question',
            reflection: 'Reflection', commitment: 'Commitment', 'pathway-choice': 'Pathway choice'
        }
    };

    var PDFMAKE = {
        lib: { src: 'https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.20/pdfmake.min.js',
               integrity: 'sha512-3UPyJyVWGE3fxbMXeKW+XANfpCDOZPZUYKnkjr3oMnNR12pM21HQW6qkDzFfx/F5RjT6GC9Y4sdhlqiN95Q6Bw==' },
        fonts: { src: 'https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.20/vfs_fonts.min.js',
                 integrity: 'sha512-Y7muj1VaXLhN0OxEZ99vVxM4/o9aaYF7Plz22TiuABHFvrqWp9W9hYankFs1q2E2Kqj2ppcIyGXgnMAIK0JjJQ==' }
    };
    // The PDF font (CODE-SITE-20, ruling SITE-JOURNAL-PDF-GREEK): pdfmake's bundled Roboto has
    // no polytonic Greek, so a word such as "Ἰησοῦς" lost letters in the PDF. Noto Sans (SIL OFL
    // 1.1; Latin, Greek with all of Greek Extended, Cyrillic) is served by this site and fetched
    // only when a reader asks for a PDF. If it cannot be fetched, the PDF is still made, in Roboto.
    var PDF_FONT = {
        family: 'NotoSans',
        files: {
            normal: '/assets/fonts/pdf/NotoSans-Regular.ttf',
            bold: '/assets/fonts/pdf/NotoSans-Bold.ttf',
            italics: '/assets/fonts/pdf/NotoSans-Italic.ttf',
            bolditalics: '/assets/fonts/pdf/NotoSans-BoldItalic.ttf'
        }
    };
    var DOCX_SRC = '/js/wop-docx.js';
    var SAVE_DELAY_MS = 600;
    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

    // ------------------------------------------------------------ helpers
    function el(doc, tag, attrs, children) {
        var e = doc.createElement(tag);
        if (attrs) Object.keys(attrs).forEach(function (k) {
            if (k === 'text') e.textContent = attrs[k];
            else if (k === 'className') e.className = attrs[k];
            else if (k === 'hidden') e.hidden = !!attrs[k];
            else e.setAttribute(k, attrs[k]);
        });
        (children || []).forEach(function (c) { if (c) e.appendChild(c); });
        return e;
    }

    function pad(n) { return (n < 10 ? '0' : '') + n; }
    function isoDay(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
    function longDate(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        if (isNaN(d.getTime())) return '';
        return d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear();
    }

    var INLINE = null;   // the /my-reflections/ actions container, when CFG.inline is set
    function pageEntries() { return INLINE ? R.loadAll() : R.loadMany(CFG.ids); }
    function scopeIsAll() { return INLINE ? true : !!(scopeAll && scopeAll.checked); }

    function entryTitle(e) { return R.titleFor(e.chapterId, e.chapterTitle); }

    function typeLabel(e) { return T.types[e.type] || T.types.reflection; }

    function sectionLabel(e) {
        var m = e.meta || {};
        if (e.type === 'question') return '';
        if (m.section) return m.section;
        if (e.type === 'commitment' || (e.type === 'reflection' && m.cardId)) {
            return (e.promptLabel || '').replace(/ \(Reflection\)$/, '');
        }
        return '';
    }

    function promptOf(e) {
        var m = e.meta || {};
        if (e.type === 'question') return '';
        if (e.type === 'commitment' || (e.type === 'reflection' && m.cardId)) return '';
        return e.promptLabel || '';
    }

    function writtenLine(e) {
        var d = longDate(e.timestamp);
        if (!d) return '';
        return ((e.meta && e.meta.carriedOver) ? T.writtenBefore : T.written) + ' ' + d;
    }

    // ------------------------------------------------------------ build the panel
    var doc = document;
    var homeParent, tabBtn, panel, listEl, countEl, dotEl, qArea, qBtn, scopePage, scopeAll,
        fmtBtns = {}, clearBtn, confirmBox, confirmText, suggestEl, popBtn, statusEl;
    var pipWindow = null;
    var lastFocus = null;
    var currentQuestion = null;   // id of the question being written, until "Save question"
    var suggested = false;

    function build() {
        homeParent = doc.body;

        tabBtn = el(doc, 'button', { type: 'button', className: 'wop-rp-tab', 'aria-expanded': 'false', 'aria-controls': 'wopReflectionsPanel' });
        var tabText = el(doc, 'span', { className: 'wop-rp-tab-text' });
        tabText.appendChild(doc.createTextNode(T.tab + ' ('));
        countEl = el(doc, 'span', { className: 'wop-rp-count', text: '0' });
        tabText.appendChild(countEl);
        tabText.appendChild(doc.createTextNode(')'));
        dotEl = el(doc, 'span', { className: 'wop-rp-dot', hidden: true });
        var dotSr = el(doc, 'span', { className: 'wop-rp-sr', text: T.marker });
        dotEl.appendChild(dotSr);
        tabBtn.appendChild(tabText);
        tabBtn.appendChild(dotEl);

        panel = el(doc, 'section', { id: 'wopReflectionsPanel', className: 'wop-rp', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'wopRpHeading', hidden: true, tabindex: '-1' });

        // Head
        popBtn = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--ghost wop-rp-popout', text: T.popout, hidden: !('documentPictureInPicture' in window) });
        var closeBtn = el(doc, 'button', { type: 'button', className: 'wop-rp-close', 'aria-label': T.close, title: T.close, text: '✕' });
        var head = el(doc, 'div', { className: 'wop-rp-head' }, [
            el(doc, 'div', { className: 'wop-rp-headtext' }, [
                el(doc, 'h2', { id: 'wopRpHeading', className: 'wop-rp-heading', text: T.heading }),
                el(doc, 'p', { className: 'wop-rp-sub' }, [el(doc, 'em', { text: T.sub })])
            ]),
            el(doc, 'div', { className: 'wop-rp-headbtns' }, [popBtn, closeBtn])
        ]);

        // Entries
        listEl = el(doc, 'ol', { className: 'wop-rp-list', 'aria-label': T.heading });

        // My questions
        qArea = el(doc, 'textarea', { id: 'wopRpQuestion', className: 'wop-rp-qarea', rows: '3', 'aria-describedby': 'wopRpInvite wopRpG5' });
        qBtn = el(doc, 'button', { type: 'button', className: 'wop-rp-btn', text: T.saveQuestion });
        var qSec = el(doc, 'div', { className: 'wop-rp-questions' }, [
            el(doc, 'h3', { className: 'wop-rp-h3' }, [el(doc, 'label', { 'for': 'wopRpQuestion', text: T.questions })]),
            el(doc, 'p', { id: 'wopRpInvite', className: 'wop-rp-invite' }, [el(doc, 'em', { text: T.invite })]),
            el(doc, 'p', { id: 'wopRpG5', className: 'wop-rp-g5' }, [el(doc, 'em', { text: T.g5 })]),
            qArea,
            el(doc, 'div', { className: 'wop-rp-row' }, [qBtn])
        ]);

        // Download
        scopePage = el(doc, 'input', { type: 'radio', name: 'wopRpScope', value: 'page', id: 'wopRpScopePage' });
        scopeAll = el(doc, 'input', { type: 'radio', name: 'wopRpScope', value: 'all', id: 'wopRpScopeAll' });
        scopePage.checked = true;
        var fmtRow = el(doc, 'div', { className: 'wop-rp-row wop-rp-formats' });
        ['docx', 'pdf', 'md', 'txt'].forEach(function (f) {
            fmtBtns[f] = el(doc, 'button', { type: 'button', className: 'wop-rp-btn', 'data-format': f, text: T.formats[f] });
            fmtRow.appendChild(fmtBtns[f]);
        });
        statusEl = el(doc, 'p', { className: 'wop-rp-status', role: 'status', 'aria-live': 'polite' });
        var dl = el(doc, 'fieldset', { className: 'wop-rp-download' }, [
            el(doc, 'legend', { text: T.download }),
            el(doc, 'div', { className: 'wop-rp-row wop-rp-scope' }, [
                el(doc, 'label', {}, [scopePage, doc.createTextNode(' ' + T.scopePage)]),
                el(doc, 'label', {}, [scopeAll, doc.createTextNode(' ' + T.scopeAll)])
            ]),
            fmtRow,
            statusEl
        ]);

        // Clear
        clearBtn = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--ghost wop-rp-clear', text: T.clear });
        confirmText = el(doc, 'p', { className: 'wop-rp-confirm-text', id: 'wopRpConfirmText' });
        var yes = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--danger', text: T.remove, 'aria-describedby': 'wopRpConfirmText' });
        var no = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--ghost', text: T.cancel });
        confirmBox = el(doc, 'div', { className: 'wop-rp-confirm', role: 'alertdialog', 'aria-labelledby': 'wopRpConfirmText', hidden: true }, [
            confirmText, el(doc, 'div', { className: 'wop-rp-row' }, [yes, no])
        ]);
        suggestEl = el(doc, 'p', { className: 'wop-rp-suggest', text: T.suggest, hidden: true });

        var foot = el(doc, 'div', { className: 'wop-rp-foot' }, [
            dl,
            suggestEl,
            el(doc, 'div', { className: 'wop-rp-row' }, [clearBtn]),
            confirmBox,
            el(doc, 'p', { className: 'wop-rp-journal-link' }, [el(doc, 'a', { href: '/my-reflections/', text: T.journal })])
        ]);

        panel.appendChild(head);
        panel.appendChild(el(doc, 'div', { className: 'wop-rp-body' }, [listEl, qSec, foot]));

        doc.body.appendChild(tabBtn);
        doc.body.appendChild(panel);

        // Wiring
        tabBtn.addEventListener('click', function () {
            if (pipWindow) { pipWindow.close(); return; }
            if (panel.hidden) open(); else close();
        });
        closeBtn.addEventListener('click', function () { if (pipWindow) pipWindow.close(); else close(); });
        popBtn.addEventListener('click', popOut);
        qArea.addEventListener('input', onQuestionInput);
        qBtn.addEventListener('click', finishQuestion);
        Object.keys(fmtBtns).forEach(function (f) {
            fmtBtns[f].addEventListener('click', function () { download(f); });
        });
        [scopePage, scopeAll].forEach(function (r) { r.addEventListener('change', render); });
        clearBtn.addEventListener('click', askClear);
        yes.addEventListener('click', doClear);
        no.addEventListener('click', function () { confirmBox.hidden = true; clearBtn.focus(); });
        doc.addEventListener('keydown', onKey);

        window.addEventListener('wop:reflections-changed', render);
        window.addEventListener('storage', function (e) {
            if (!e.key || e.key.indexOf('wop-reflection-') === 0) render();
        });
        window.addEventListener('resize', placeClear);
    }

    function buildInline(container) {
        INLINE = container;
        var fmtRow = el(doc, 'div', { className: 'wop-rp-row wop-rp-formats' });
        ['docx', 'pdf', 'md', 'txt'].forEach(function (f) {
            fmtBtns[f] = el(doc, 'button', { type: 'button', className: 'wop-rp-btn', 'data-format': f, text: T.formats[f] });
            fmtRow.appendChild(fmtBtns[f]);
            fmtBtns[f].addEventListener('click', function () { download(f); });
        });
        statusEl = el(doc, 'p', { className: 'wop-rp-status', role: 'status', 'aria-live': 'polite' });
        clearBtn = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--ghost wop-rp-clear', text: T.clear });
        confirmText = el(doc, 'p', { className: 'wop-rp-confirm-text', id: 'wopRpConfirmText' });
        var yes = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--danger', text: T.remove, 'aria-describedby': 'wopRpConfirmText' });
        var no = el(doc, 'button', { type: 'button', className: 'wop-rp-btn wop-rp-btn--ghost', text: T.cancel });
        confirmBox = el(doc, 'div', { className: 'wop-rp-confirm', role: 'alertdialog', 'aria-labelledby': 'wopRpConfirmText', hidden: true }, [
            confirmText, el(doc, 'div', { className: 'wop-rp-row' }, [yes, no])
        ]);
        suggestEl = el(doc, 'p', { className: 'wop-rp-suggest', text: T.suggest, hidden: true });
        var box = el(doc, 'div', { className: 'wop-rp wop-rp--inline' }, [
            el(doc, 'fieldset', { className: 'wop-rp-download' }, [
                el(doc, 'legend', { text: T.download }),
                el(doc, 'p', { className: 'wop-rp-scope-fixed', text: T.scopeAll }),
                fmtRow,
                statusEl
            ]),
            suggestEl,
            el(doc, 'div', { className: 'wop-rp-row' }, [clearBtn]),
            confirmBox
        ]);
        box.hidden = false;
        container.appendChild(box);
        clearBtn.addEventListener('click', askClear);
        yes.addEventListener('click', doClear);
        no.addEventListener('click', function () { confirmBox.hidden = true; clearBtn.focus(); });
        doc.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !confirmBox.hidden) { confirmBox.hidden = true; clearBtn.focus(); }
        });
        window.addEventListener('wop:reflections-changed', render);
    }

    function onKey(e) {
        if (e.key !== 'Escape' || panel.hidden || pipWindow) return;
        if (!confirmBox.hidden) { confirmBox.hidden = true; clearBtn.focus(); return; }
        close();
    }

    // ------------------------------------------------------------ open / close / placement
    function open() {
        lastFocus = doc.activeElement;
        render();
        panel.hidden = false;
        tabBtn.setAttribute('aria-expanded', 'true');
        tabBtn.classList.add('is-open');
        placeClear();
        panel.focus();
    }

    function close() {
        commitQuestionNow();
        panel.hidden = true;
        confirmBox.hidden = true;
        tabBtn.setAttribute('aria-expanded', 'false');
        tabBtn.classList.remove('is-open');
        if (lastFocus && lastFocus.focus && doc.contains(lastFocus)) lastFocus.focus();
        else tabBtn.focus();
    }

    // Keep the panel clear of controls fixed to the bottom of the window
    // (the narration player, the floating toolbars, the mini player).
    var KEEP_CLEAR = ['#audioPlayer', '.audio-player', '.audio-player-bar', '#floatingActionBar', '.floating-action-bar',
        '#bottomToolbar', '.bottom-toolbar', '.wop-player', '#wopPlayer', '.chat-bar', '.narration-player-bar', '.sticky-player'];
    function placeClear() {
        if (pipWindow || panel.hidden) return;
        var vh = window.innerHeight, clear = 0;
        KEEP_CLEAR.forEach(function (sel) {
            Array.prototype.forEach.call(doc.querySelectorAll(sel), function (node) {
                if (node === panel || panel.contains(node)) return;
                var cs = window.getComputedStyle(node);
                if (cs.position !== 'fixed' && cs.position !== 'sticky') return;
                if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return;
                var r = node.getBoundingClientRect();
                if (r.width === 0 || r.height === 0) return;
                if (r.bottom < vh - 160 || r.top >= vh) return;   // not along the bottom edge
                clear = Math.max(clear, vh - r.top);
            });
        });
        panel.style.setProperty('--wop-rp-bottom', Math.ceil(clear) + 'px');
    }

    // ------------------------------------------------------------ render
    function render() {
        if (INLINE) {
            var any = R.loadAll().length > 0;
            Object.keys(fmtBtns).forEach(function (f) { fmtBtns[f].disabled = !any; });
            clearBtn.disabled = R.countForClear() === 0;
            return;
        }
        var entries = pageEntries();
        var pending = entries.some(R.isPending);
        countEl.textContent = String(entries.length);
        dotEl.hidden = !pending;
        tabBtn.classList.toggle('has-pending', pending);

        listEl.innerHTML = '';
        entries.forEach(function (e) {
            var li = el(doc, 'li', { className: 'wop-rp-entry wop-rp-entry--' + (e.type || 'reflection') });
            var labelParts = [typeLabel(e)];
            var sec = sectionLabel(e);
            if (sec) labelParts.push(sec);
            li.appendChild(el(doc, 'p', { className: 'wop-rp-entry-label', text: labelParts.join(' · ') }));
            var p = promptOf(e);
            if (p) li.appendChild(el(doc, 'p', { className: 'wop-rp-entry-prompt', text: p }));
            li.appendChild(el(doc, 'p', { className: 'wop-rp-entry-text', text: e.content || '' }));
            var meta = el(doc, 'p', { className: 'wop-rp-entry-meta' });
            meta.appendChild(doc.createTextNode(writtenLine(e)));
            if (R.isPending(e)) {
                meta.appendChild(doc.createTextNode(' '));
                meta.appendChild(el(doc, 'span', { className: 'wop-rp-marker', text: T.marker }));
            }
            li.appendChild(meta);
            listEl.appendChild(li);
        });
        listEl.hidden = entries.length === 0;

        var scoped = scopeIsAll() ? R.loadAll() : entries;
        Object.keys(fmtBtns).forEach(function (f) { fmtBtns[f].disabled = scoped.length === 0; });
        clearBtn.disabled = R.countForClear() === 0;
    }

    // ------------------------------------------------------------ My questions
    var qTimer = null;
    function questionProbe(id) { return { type: 'question', meta: { key: 'question:' + id } }; }

    function writeQuestion() {
        var text = qArea.value;
        if (!currentQuestion) {
            if (!text.trim()) return;
            currentQuestion = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
        }
        try {
            R.put({
                chapterId: CFG.ids[0],
                chapterTitle: CFG.title || R.titleFor(CFG.ids[0]),
                type: 'question',
                promptLabel: '',
                content: text,
                meta: { key: 'question:' + currentQuestion, pageUrl: location.pathname }
            });
        } catch (e) { /* storage unavailable */ }
        if (!text.trim()) currentQuestion = null;
    }

    function onQuestionInput() {
        clearTimeout(qTimer);
        qTimer = setTimeout(writeQuestion, SAVE_DELAY_MS);
    }

    function commitQuestionNow() {
        if (qTimer) { clearTimeout(qTimer); qTimer = null; writeQuestion(); }
    }

    function finishQuestion() {
        commitQuestionNow();
        if (!qArea.value.trim()) { qArea.focus(); return; }
        currentQuestion = null;
        qArea.value = '';
        render();
        qArea.focus();
    }

    // ------------------------------------------------------------ Clear
    function askClear() {
        if (!INLINE) commitQuestionNow();
        var n = R.countForClear();
        if (!n) return;
        confirmText.textContent = T.confirm(n);
        confirmBox.hidden = false;
        confirmBox.querySelector('.wop-rp-btn--danger').focus();
    }

    function doClear() {
        R.clearAll();
        currentQuestion = null;
        if (qArea) qArea.value = '';
        confirmBox.hidden = true;
        suggestEl.hidden = true;
        render();
        clearBtn.focus();
        // The page's own fields show what is stored; reload them from the now-empty store.
        try { window.dispatchEvent(new CustomEvent('wop:reflections-cleared')); } catch (e) { /* ignore */ }
    }

    // ------------------------------------------------------------ export model
    function exportModel(scopeAllOn) {
        var entries = scopeAllOn ? R.loadAll() : pageEntries();
        var groups = {};
        entries.forEach(function (e) {
            var gid = R.groupIdFor(e.chapterId);
            var g = groups[gid] || (groups[gid] = { id: gid, title: R.titleFor(gid, e.chapterTitle), answers: [], questions: [] });
            var item = {
                type: e.type,
                label: typeLabel(e),
                section: sectionLabel(e),
                prompt: promptOf(e),
                content: e.content || '',
                written: writtenLine(e)
            };
            if (e.type === 'question') g.questions.push({ item: item, ts: e.timestamp || '' });
            else g.answers.push({ item: item, ts: e.timestamp || '' });
        });
        var ordered = Object.keys(groups).sort(function (a, b) {
            var d = R.orderFor(a) - R.orderFor(b);
            return d !== 0 ? d : groups[a].title.localeCompare(groups[b].title);
        }).map(function (k) {
            var g = groups[k];
            var byTime = function (x, y) { return x.ts.localeCompare(y.ts); };
            return {
                title: g.title,
                answers: g.answers.sort(byTime).map(function (x) { return x.item; }),
                questions: g.questions.sort(byTime).map(function (x) { return x.item; })
            };
        });
        var now = new Date();
        return {
            title: T.fileTitle,
            dateLine: T.downloadedOn + ' ' + longDate(now.toISOString()),
            questionsHeading: T.questions,
            promptLabel: T.prompt,
            groups: ordered,
            entries: entries,
            day: isoDay(now)
        };
    }

    function itemHeading(it) {
        return it.section ? it.label + ' · ' + it.section : it.label;
    }

    function toMarkdown(m) {
        var out = ['# ' + m.title, '', m.dateLine, ''];
        m.groups.forEach(function (g) {
            out.push('## ' + g.title, '');
            g.answers.forEach(function (it) {
                out.push('### ' + itemHeading(it), '');
                if (it.prompt) out.push('*' + m.promptLabel + ':* ' + it.prompt.replace(/\n+/g, ' '), '');
                out.push(it.content, '');
                if (it.written) out.push('*' + it.written + '*', '');
            });
            if (g.questions.length) {
                out.push('### ' + m.questionsHeading, '');
                g.questions.forEach(function (it) {
                    out.push(it.content, '');
                    if (it.written) out.push('*' + it.written + '*', '');
                });
            }
        });
        return out.join('\n');
    }

    function rule(s, ch) { return new Array(Math.max(4, s.length) + 1).join(ch); }

    function toText(m) {
        var out = [m.title, rule(m.title, '='), '', m.dateLine, ''];
        m.groups.forEach(function (g) {
            out.push('', g.title, rule(g.title, '-'), '');
            g.answers.forEach(function (it) {
                out.push('[' + itemHeading(it) + ']');
                if (it.prompt) out.push(m.promptLabel + ': ' + it.prompt.replace(/\n+/g, ' '));
                out.push('', it.content, '');
                if (it.written) out.push(it.written, '');
            });
            if (g.questions.length) {
                out.push('[' + m.questionsHeading + ']', '');
                g.questions.forEach(function (it) {
                    out.push(it.content, '');
                    if (it.written) out.push(it.written, '');
                });
            }
        });
        return out.join('\r\n');
    }

    function toPdfDefinition(m) {
        var content = [
            { text: m.title, style: 'title' },
            { text: m.dateLine, style: 'date' }
        ];
        m.groups.forEach(function (g) {
            content.push({ text: g.title, style: 'h1' });
            g.answers.forEach(function (it) {
                content.push({ text: itemHeading(it), style: 'h2' });
                if (it.prompt) content.push({ text: [{ text: m.promptLabel + ': ', italics: true }, { text: it.prompt }], style: 'prompt' });
                content.push({ text: it.content, style: 'words' });
                if (it.written) content.push({ text: it.written, style: 'written' });
            });
            if (g.questions.length) {
                content.push({ text: m.questionsHeading, style: 'h2' });
                g.questions.forEach(function (it) {
                    content.push({ text: it.content, style: 'words' });
                    if (it.written) content.push({ text: it.written, style: 'written' });
                });
            }
        });
        return {
            info: { title: m.title },
            pageMargins: [56, 56, 56, 56],
            content: content,
            defaultStyle: { fontSize: 11, lineHeight: 1.25 },
            styles: {
                title: { fontSize: 18, bold: true, margin: [0, 0, 0, 4] },
                date: { fontSize: 10, color: '#555555', margin: [0, 0, 0, 14] },
                h1: { fontSize: 14, bold: true, margin: [0, 14, 0, 6] },
                h2: { fontSize: 11.5, bold: true, margin: [0, 10, 0, 3] },
                prompt: { fontSize: 10, color: '#444444', margin: [0, 0, 0, 4] },
                words: { margin: [0, 2, 0, 3] },
                written: { fontSize: 9, italics: true, color: '#666666', margin: [0, 0, 0, 4] }
            }
        };
    }

    // ------------------------------------------------------------ loaders (on request only)
    var loading = {};
    function loadScript(src, integrity) {
        if (loading[src]) return loading[src];
        loading[src] = new Promise(function (resolve, reject) {
            var s = document.createElement('script');
            s.src = src;
            if (integrity) { s.integrity = integrity; s.crossOrigin = 'anonymous'; s.referrerPolicy = 'no-referrer'; }
            s.onload = function () { resolve(); };
            s.onerror = function () { delete loading[src]; reject(new Error('Could not load ' + src)); };
            document.head.appendChild(s);
        });
        return loading[src];
    }

    function toBase64(buffer) {
        var bytes = new Uint8Array(buffer), parts = [], CHUNK = 0x8000;
        for (var i = 0; i < bytes.length; i += CHUNK) {
            parts.push(String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK)));
        }
        return btoa(parts.join(''));
    }

    // Fetch the four Noto Sans files (same origin) into pdfmake's virtual file system, once.
    // Resolves true when the font is ready, false when it could not be fetched.
    var pdfFontReady = null;
    function loadPdfFont() {
        if (pdfFontReady) return pdfFontReady;
        var styles = Object.keys(PDF_FONT.files);
        pdfFontReady = Promise.all(styles.map(function (style) {
            var url = PDF_FONT.files[style];
            return fetch(url, { credentials: 'same-origin' }).then(function (r) {
                if (!r.ok) throw new Error('Could not load ' + url);
                return r.arrayBuffer();
            });
        })).then(function (buffers) {
            var pm = window.pdfMake;
            var vfs = {}, family = {};
            styles.forEach(function (style, i) {
                var file = PDF_FONT.files[style].split('/').pop();
                vfs[file] = toBase64(buffers[i]);
                family[style] = file;
            });
            pm.vfs = Object.assign({}, pm.vfs || {}, vfs);
            var fonts = {};
            fonts[PDF_FONT.family] = family;
            pm.fonts = Object.assign({}, pm.fonts || {}, fonts);
            return true;
        }).catch(function () {
            pdfFontReady = null;   // try again next time
            return false;
        });
        return pdfFontReady;
    }

    function saveBlob(blob, name) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = name;
        a.rel = 'noopener';
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 4000);
    }

    function fileName(ext, all) {
        var part = all ? 'all' : (CFG.fileSlug || 'page');
        return 'My-Reflections_' + part + '_' + isoDay(new Date()) + '.' + ext;
    }

    function download(format) {
        if (!INLINE) commitQuestionNow();
        var all = scopeIsAll();
        var m = exportModel(all);
        if (!m.entries.length) return;
        var name = fileName(format, all);
        var done = function () {
            R.markDownloaded(m.entries);
            statusEl.textContent = '';
            if (!suggested) { suggested = true; suggestEl.hidden = false; }
        };
        var fail = function () { statusEl.textContent = ''; };
        Object.keys(fmtBtns).forEach(function (f) { fmtBtns[f].disabled = true; });

        var p;
        if (format === 'md') {
            saveBlob(new Blob([toMarkdown(m)], { type: 'text/markdown;charset=utf-8' }), name);
            p = Promise.resolve();
        } else if (format === 'txt') {
            saveBlob(new Blob(['﻿' + toText(m)], { type: 'text/plain;charset=utf-8' }), name);
            p = Promise.resolve();
        } else if (format === 'docx') {
            statusEl.textContent = '…';
            p = loadScript(DOCX_SRC).then(function () {
                saveBlob(window.WopDocx.build(m), name);
            });
        } else if (format === 'pdf') {
            statusEl.textContent = '…';
            p = loadScript(PDFMAKE.lib.src, PDFMAKE.lib.integrity)
                .then(loadPdfFont)
                .then(function (noto) {
                    // Without the site's font, fall back to the library's Roboto.
                    return noto ? true : loadScript(PDFMAKE.fonts.src, PDFMAKE.fonts.integrity).then(function () { return false; });
                })
                .then(function (noto) {
                    var def = toPdfDefinition(m);
                    if (noto) def.defaultStyle.font = PDF_FONT.family;
                    return new Promise(function (resolve) {
                        window.pdfMake.createPdf(def).getBlob(function (blob) {
                            saveBlob(blob, name);
                            resolve();
                        });
                    });
                });
        }
        p.then(done, fail).then(render);
    }

    // ------------------------------------------------------------ pop-out (Document Picture-in-Picture)
    function popOut() {
        if (!('documentPictureInPicture' in window) || pipWindow) return;
        window.documentPictureInPicture.requestWindow({ width: 420, height: 640 }).then(function (pip) {
            pipWindow = pip;
            var link = pip.document.createElement('link');
            link.rel = 'stylesheet';
            link.href = new URL(CFG.css || '/css/wop-reflections-panel.css', location.href).href;
            pip.document.head.appendChild(link);
            pip.document.title = T.heading;
            pip.document.body.className = 'wop-rp-pipbody';
            pip.document.body.appendChild(panel);
            panel.classList.add('is-pip');
            panel.hidden = false;
            popBtn.hidden = true;
            tabBtn.setAttribute('aria-expanded', 'true');
            pip.document.addEventListener('keydown', function (e) { if (e.key === 'Escape') pip.close(); });
            pip.addEventListener('pagehide', function () {
                commitQuestionNow();
                panel.classList.remove('is-pip');
                homeParent.appendChild(panel);
                pipWindow = null;
                popBtn.hidden = false;
                panel.hidden = false;
                tabBtn.setAttribute('aria-expanded', 'true');
                render();
                placeClear();
            });
        }).catch(function () { /* the reader can keep using the in-page panel */ });
    }

    // ------------------------------------------------------------ writing fonts
    // The site's web fonts come from Google Fonts in character-range pieces, and a
    // browser fetches a piece only when a character from it is first drawn. Typing
    // Greek, Cyrillic or Vietnamese into a reflection would then make the browser
    // ask fonts.gstatic.com for that piece: no words leave the device, but a reader
    // action would cause an off-site request (ruling SITE-JOURNAL-CHECK1-NETWORK).
    // So, once the page has loaded, the remaining pieces of the fonts that the
    // writing fields use are loaded now, as part of the page load.
    function weightMatches(faceWeight, weight) {
        var parts = String(faceWeight).split(/\s+/).map(Number);
        var w = Number(weight);
        if (parts.length === 2) return w >= parts[0] && w <= parts[1];
        return parts[0] === w;
    }

    function warmWritingFonts() {
        if (!doc.fonts || typeof doc.fonts.forEach !== 'function') return;
        var want = [];
        var sel = 'textarea, input[type="text"], input[type="email"], input:not([type]), .wop-rp-entry-text, .wop-rp-qarea';
        Array.prototype.forEach.call(doc.querySelectorAll(sel), function (n) {
            var cs = window.getComputedStyle(n);
            var fam = (cs.fontFamily.split(',')[0] || '').trim().replace(/^["']|["']$/g, '').toLowerCase();
            want.push({ family: fam, weight: cs.fontWeight, style: cs.fontStyle });
        });
        doc.fonts.forEach(function (face) {
            if (face.status !== 'unloaded') return;
            var fam = String(face.family).replace(/^["']|["']$/g, '').toLowerCase();
            var used = want.some(function (w) {
                return w.family === fam && w.style === face.style && weightMatches(face.weight, w.weight);
            });
            if (used) face.load().catch(function () { /* the system font is used instead */ });
        });
    }

    function scheduleWarm() {
        var go = function () { setTimeout(warmWritingFonts, 0); };
        if (doc.readyState === 'complete') go();
        else window.addEventListener('load', go, { once: true });
    }

    // ------------------------------------------------------------ start
    function start() {
        if (CFG.inline) {
            var container = doc.querySelector(CFG.inline);
            if (!container) return;
            buildInline(container);
        } else {
            build();
        }
        render();
        scheduleWarm();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();

    // For the page's own scripts and for tests.
    window.WopReflectionsPanel = {
        open: function () { if (panel && panel.hidden) open(); },
        render: function () { render(); },
        close: function () { if (panel && !panel.hidden && !pipWindow) close(); },
        exportModel: exportModel,
        toMarkdown: toMarkdown,
        toText: toText,
        toPdfDefinition: toPdfDefinition
    };
})();
