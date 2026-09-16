/* ============================================================
   aoid-video.js — /articles/video-NN/  Articles of Interfaith
   Discipleship readings.

   Generalised from creation.js. One script drives all twelve
   readings; everything page-specific arrives in the config object
   window.WOP_AOID_VIDEO (see layouts/aoid-video.njk). /creation/
   and creation.js are untouched.

   WHAT IT DOES
     - Plays the reading through the YouTube IFrame Player API on the
       privacy-preserving youtube-nocookie host.
     - Follows the film: highlights the sentence being spoken and
       auto-scrolls the article column, with a resume-follow handoff.
     - Streams the citation dock beside it — the apparatus entry for
       the [data-span] currently being spoken, rendered the way
       articles-panel.js renders it on /articles/.
     - Absence renders as absence: a line with no [data-span] gets a
       quiet neutral state, never the previous line's citation.
     - Tap any line to hold and study it; the film pauses.
     - On ENDED, an overlay covers YouTube's suggestion grid and puts
       the article's own reflection question up as the discussion opener.

   THE ARTICLE DOM IS NOT REWRITTEN. Sentences are highlighted with the
   CSS Custom Highlight API over Range objects, so the prose in
   src/_includes/aoid/aNN.njk renders identically here and on
   /articles/. Only where that API is missing does the script fall back
   to wrapping sentences — and only on this page.
   ============================================================ */
(function () {
    'use strict';

    var CFG = window.WOP_AOID_VIDEO;
    if (!CFG || !CFG.timing || !CFG.timing.sentences) { return; }

    var T = CFG.timing;
    var SENTS = T.sentences || [];
    var WTIME = T.words || [];
    var SPAN_TIME = T.spans || {};
    var APP = CFG.apparatus || {};
    var BOOKS = CFG.books || {};

    function byId(k) { return document.getElementById(CFG.el[k]); }

    var article = byId('article');
    var reading = byId('reading');
    if (!article || !SENTS.length) { return; }

    /* ── Tokeniser ────────────────────────────────────────────────
       ONE definition of a word, shared verbatim with
       tools/aoid_build_timing.py. Letters, digits and apostrophes;
       everything else separates. Punctuation, em-dashes, daggers and
       entity differences therefore cannot desynchronise this token
       stream from the one the timing was built against. */
    var WORD_RE = /[0-9A-Za-zÀ-ɏ'’]+/g;

    /* The spoken prose is the <p> children of .article-body that are not
       footnotes. The .article-rjw block and the footnote lines are not
       read aloud, and the build script excludes them identically. */
    function buildTokens() {
        var out = [];
        var paras = article.querySelectorAll('.article-body > p:not(.article-footnote)');
        for (var p = 0; p < paras.length; p++) {
            var tw = document.createTreeWalker(paras[p], NodeFilter.SHOW_TEXT, null);
            var n;
            while ((n = tw.nextNode())) {
                var txt = n.nodeValue, m;
                WORD_RE.lastIndex = 0;
                while ((m = WORD_RE.exec(txt))) {
                    out.push({ node: n, a: m.index, b: m.index + m[0].length, s: undefined });
                }
            }
        }
        return out;
    }

    var TOK = buildTokens();
    if (TOK.length !== T.tokens) {
        // The page and the timing data disagree about the article's words.
        // Say so loudly rather than following the film against stale timing.
        console.error('[aoid-video] token mismatch for ' + CFG.code +
            ': page has ' + TOK.length + ', timing was built for ' + T.tokens +
            '. Re-run tools/aoid_build_timing.py.');
        return;
    }

    // Resolve every word's owning [data-span] up front — before any fallback
    // wrapping moves text nodes, and so the malformed-nesting patterns the
    // browser repairs (A04, A12, A13) are read from the repaired DOM.
    for (var i = 0; i < TOK.length; i++) {
        var el = TOK[i].node.parentElement;
        var sp = el && el.closest ? el.closest('[data-span]') : null;
        TOK[i].s = sp ? sp.getAttribute('data-span') : null;
    }

    // Per sentence: the ordered, de-duplicated list of spans it covers.
    var SENT_SPANS = SENTS.map(function (s) {
        var list = [], last = null;
        for (var k = s.w0; k < s.w1; k++) {
            var id = TOK[k].s;
            if (id && id !== last) { list.push({ id: id, at: k }); }
            last = id;
        }
        return list;
    });

    /* ── Sentence highlighting ───────────────────────────────────── */
    var HL_OK = (typeof window.Highlight === 'function' && window.CSS && window.CSS.highlights);
    var hlLit = null, hlHeld = null, WRAPS = null;

    if (HL_OK) {
        hlLit = new window.Highlight();
        hlHeld = new window.Highlight();
        window.CSS.highlights.set('aoid-lit', hlLit);
        window.CSS.highlights.set('aoid-held', hlHeld);
        document.documentElement.classList.add('aoid-hl');
    } else {
        // Fallback only, and only on this page: wrap each sentence's text-node
        // runs so the same treatment can be applied with a class. Walked back
        // to front so each splitText leaves every earlier token untouched.
        WRAPS = [];
        for (var si = SENTS.length - 1; si >= 0; si--) {
            var s = SENTS[si], pieces = [], cur = null;
            for (var k = s.w0; k < s.w1; k++) {
                var t = TOK[k];
                if (cur && cur.node === t.node) { cur.b = t.b; }
                else { cur = { node: t.node, a: t.a, b: t.b }; pieces.push(cur); }
            }
            for (var j = pieces.length - 1; j >= 0; j--) {
                var pc = pieces[j];
                pc.node.splitText(pc.b);
                var mid = pc.node.splitText(pc.a);
                var w = document.createElement('span');
                w.className = 'aoid-sent';
                w.setAttribute('data-sent', si);
                mid.parentNode.replaceChild(w, mid);
                w.appendChild(mid);
            }
        }
        for (var q = 0; q < SENTS.length; q++) {
            WRAPS[q] = [].slice.call(article.querySelectorAll('[data-sent="' + q + '"]'));
        }
    }

    function sentRange(i) {
        var s = SENTS[i];
        var r = document.createRange();
        r.setStart(TOK[s.w0].node, TOK[s.w0].a);
        r.setEnd(TOK[s.w1 - 1].node, TOK[s.w1 - 1].b);
        return r;
    }

    function paintSentence(hl, cls, i) {
        if (HL_OK) {
            hl.clear();
            if (i != null) { hl.add(sentRange(i)); }
            return;
        }
        for (var q = 0; q < WRAPS.length; q++) {
            for (var w = 0; w < WRAPS[q].length; w++) { WRAPS[q][w].classList.remove(cls); }
        }
        if (i != null) {
            for (var v = 0; v < WRAPS[i].length; v++) { WRAPS[i][v].classList.add(cls); }
        }
    }

    function sentRect(i) {
        if (HL_OK) { return sentRange(i).getBoundingClientRect(); }
        var els = WRAPS[i];
        if (!els.length) { return null; }
        var a = els[0].getBoundingClientRect(), b = els[els.length - 1].getBoundingClientRect();
        return { top: a.top, bottom: b.bottom, height: b.bottom - a.top };
    }

    function sentText(i) {
        var s = SENTS[i], out = '';
        if (HL_OK) { return sentRange(i).toString().replace(/\s+/g, ' ').trim(); }
        for (var k = s.w0; k < s.w1; k++) { out += TOK[k].node.nodeValue.slice(TOK[k].a, TOK[k].b) + ' '; }
        return out.trim();
    }

    /* ── YouTube IFrame Player API ───────────────────────────────── */
    var player = null, playerReady = false, pollTimer = null;
    var follow = true, programmatic = false;
    var litSent = null, litSpan = null;
    var endedEl = byId('ended');
    var stageWrap = document.querySelector(CFG.el.stage);

    // Deep links. #sNN holds that span and cues the film to its word;
    // ?t=SECONDS cues the film. Neither autoplays.
    var deepSpan = null, deepTime = null;
    (function () {
        var h = (window.location.hash || '').replace(/^#/, '');
        if (h && Object.prototype.hasOwnProperty.call(SPAN_TIME, h)) {
            deepSpan = h;
            deepTime = SPAN_TIME[h];
            return;
        }
        var m = /[?&]t=([0-9.]+)/.exec(window.location.search);
        if (m) { deepTime = Math.max(0, parseFloat(m[1]) || 0); }
    })();

    /* ── Player hook (additive) ───────────────────────────────────
       The chat pages at /chat/video-NN/ need the player and its state, and
       they are a separate script (js/chat-session.js) that must not reach
       inside this closure. Two window events are the whole interface. On a
       page with no listener this costs one dispatch; nothing else here
       changes, and the wrapping try/catch means a listener that throws can
       never break a player callback. */
    function emit(name, detail) {
        try { window.dispatchEvent(new CustomEvent(name, { detail: detail })); }
        catch (_) {}
    }

    window.onYouTubeIframeAPIReady = function () {
        player = new YT.Player(CFG.el.video, {
            width: '100%', height: '100%', videoId: CFG.youtube,
            host: 'https://www.youtube-nocookie.com',
            playerVars: {
                rel: 0, modestbranding: 1, playsinline: 1,
                cc_load_policy: 0, iv_load_policy: 3,
                origin: window.location.origin
            },
            events: {
                onReady: function () {
                    playerReady = true;
                    if (deepTime != null) {
                        try { player.cueVideoById({ videoId: CFG.youtube, startSeconds: deepTime }); } catch (_) {}
                    }
                    startPoll();
                    emit('wop:player', { player: player });
                },
                onStateChange: onState
            }
        });
    };

    function onState(e) {
        if (e.data === YT.PlayerState.ENDED) { showEnded(); }
        else if (e.data === YT.PlayerState.PLAYING) { hideEnded(); }
        emit('wop:state', { state: e.data });
    }

    function currentTime() {
        try { return (player && player.getCurrentTime) ? player.getCurrentTime() : 0; }
        catch (_) { return 0; }
    }

    function startPoll() { if (!pollTimer) { pollTimer = window.setInterval(tick, 120); tick(); } }

    /* Centre the spoken line in the reading band BELOW the sticky player, not
       in the whole viewport: on desktop the pinned film covers the top of the
       screen, so viewport-centring would ride the film's bottom edge. Measured
       live, so it adapts to desktop/mobile, resize, fullscreen, and the
       not-yet-pinned state (film off-screen -> offset 0 -> plain centring). */
    function centerSentence(i) {
        var r = sentRect(i);
        if (!r) { return; }
        var vh = window.innerHeight || document.documentElement.clientHeight;
        var top = 0;
        if (stageWrap) {
            var pr = stageWrap.getBoundingClientRect();
            top = Math.min(Math.max(pr.bottom, 0), vh);
        }
        if (vh - top < 160) { top = Math.max(0, vh - 320); }
        var target = top + (vh - top) / 2;
        window.scrollBy({ top: (r.top + r.height / 2) - target, behavior: 'smooth' });
    }

    function sentenceAt(t) {
        var lo = 0, hi = SENTS.length - 1, found = -1;
        if (t < SENTS[0].start) { return -1; }
        while (lo <= hi) {
            var mid = (lo + hi) >> 1;
            if (SENTS[mid].start <= t) { found = mid; lo = mid + 1; } else { hi = mid - 1; }
        }
        // Past the end of a sentence with a gap before the next one, the line
        // just spoken stays lit rather than the column going dark.
        return found;
    }

    /* The span being spoken. Resolution is per word, so the dock turns over at
       span boundaries — but a connective word INSIDE a cited sentence holds
       that sentence's span rather than flashing the neutral state. A sentence
       with no spans at all returns null, and absence renders as absence. */
    function spanAt(sentIdx, t) {
        var list = SENT_SPANS[sentIdx];
        if (!list || !list.length) { return null; }
        var s = SENTS[sentIdx], w = s.w0;
        for (var k = s.w0; k < s.w1; k++) { if (WTIME[k] <= t) { w = k; } else { break; } }
        if (TOK[w].s) { return TOK[w].s; }
        var held = list[0].id;
        for (var j = 0; j < list.length; j++) { if (list[j].at <= w) { held = list[j].id; } }
        return held;
    }

    function tick() {
        var t = currentTime();
        var i = sentenceAt(t);
        if (i < 0) { return; }
        var sp = spanAt(i, t);

        if (i !== litSent) {
            litSent = i;
            if (!held) { paintSentence(hlLit, 'aoid-lit', i); }
            if (follow && !held) {
                programmatic = true;
                centerSentence(i);
                window.clearTimeout(tick._p);
                tick._p = window.setTimeout(function () { programmatic = false; }, 650);
            }
        }
        // Repaint on a span boundary — and, while no span is being spoken, on
        // every sentence boundary too, so the neutral state quotes the line
        // actually being read rather than the first uncited one in a run.
        var stale = !shown || shown.span !== sp || (sp === null && shown.sent !== i);
        litSpan = sp;
        if (stale && !held) { streamTo(i, sp); }
    }

    /* ── Ended overlay (blocks YouTube's suggestion grid) ─────────── */
    // The discussion opener is the article's own reflection prompt, read from
    // the shared include rather than restated here.
    (function () {
        var q = byId('endedQuestion');
        var prompt = article.querySelector('.article-rjw .rjw-prompt');
        if (q && prompt) { q.textContent = prompt.textContent.trim(); }
        else if (q) { q.remove(); }
    })();

    function showEnded() {
        if (endedEl) { endedEl.classList.add('creation-ended--show'); endedEl.setAttribute('aria-hidden', 'false'); }
    }
    function hideEnded() {
        if (endedEl) { endedEl.classList.remove('creation-ended--show'); endedEl.setAttribute('aria-hidden', 'true'); }
    }
    var replay = byId('replay');
    if (replay) {
        replay.addEventListener('click', function () {
            hideEnded();
            unhold(true);
            if (player && playerReady) { try { player.seekTo(0, true); player.playVideo(); } catch (_) {} }
        });
    }

    /* ── Resume-follow handoff on manual scroll ──────────────────── */
    var resume = byId('resume');
    window.addEventListener('scroll', function () {
        if (programmatic) { return; }
        if (follow) { follow = false; if (resume) { resume.classList.add('ct-show'); } }
    }, { passive: true });
    if (resume) {
        resume.addEventListener('click', function () {
            follow = true;
            resume.classList.remove('ct-show');
            if (litSent != null) {
                programmatic = true;
                centerSentence(litSent);
                window.setTimeout(function () { programmatic = false; }, 650);
            }
        });
    }

    /* ── Citation dock ───────────────────────────────────────────
       ONE panel, three states — the same model as /creation/:
         stream  — docked column (>=1200px), follows the film, never pauses
         held    — a line held for study; the film is paused
         overlay — narrow screens: holding a line raises it as a drawer
       Non-modal by design; focus is never trapped and the film keeps playing. */
    var WIDE = window.matchMedia('(min-width: 1200px)');
    var dock = byId('dock');
    var backdrop = document.createElement('div');
    backdrop.className = 'ap-backdrop';
    var panel = document.createElement('aside');
    panel.className = 'ap-panel ap-panel--aoid ct-docked';
    panel.setAttribute('role', 'complementary');
    panel.setAttribute('aria-label', 'Witnesses behind the line now being read');
    panel.setAttribute('aria-hidden', 'true');
    document.body.appendChild(backdrop);
    (dock || document.body).appendChild(panel);

    function prefOff() {
        try { return window.localStorage.getItem(CFG.prefKey) === 'off'; } catch (_) { return false; }
    }
    function setPrefOff(off) {
        try {
            if (off) { window.localStorage.setItem(CFG.prefKey, 'off'); }
            else { window.localStorage.removeItem(CFG.prefKey); }
        } catch (_) {}
    }

    function esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* Scripture links and definition markup are the shared apparatus rules
       (js/apparatus-common.js), so this dock and the /articles/ panel cannot
       drift apart. If the helper failed to load, a reference renders as plain
       text rather than a broken link. */
    var AP_COMMON = window.WOP_APPARATUS || null;

    function scriptureUrl(ref) {
        return AP_COMMON ? AP_COMMON.scriptureUrl(ref, BOOKS) : null;
    }

    function definitionHtml(text) {
        return AP_COMMON ? AP_COMMON.definitionHtml(text) : esc(text);
    }

    function typeBadgeLabel(type) {
        return { direct: 'Direct', concept: 'Concept', paraphrase: 'Paraphrase', xref: 'Cross-ref' }[type] || type || '';
    }

    /* ── A3 · Correction channel ──────────────────────────────────
       An apparatus entry makes a claim about how a tradition reads a text, and
       the people best placed to catch a misreading are the ones inside that
       tradition. So every entry carries the way to say so, prefilled with what
       the ministry would otherwise have to ask for: which article, which span,
       and which page it was read on.

       ONE config value governs the route (site.json correctionUrl). While it is
       empty the link does not render at all — a channel that cannot receive a
       message is worse than none, because it looks like an invitation.
       Only the span's OWN identifiers travel in the URL; nothing about the
       reader does. The neutral state carries no link: there is no claim there
       to correct. */
    function correctionHtml(spanId, spanText) {
        var base = (CFG.correctionUrl || '').trim();
        if (!base) { return ''; }

        var code = CFG.code || '';
        var pageUrl = '';
        try { pageUrl = window.location.origin + window.location.pathname; } catch (_) {}

        var quoted = (spanText || '').replace(/\s+/g, ' ').trim();
        if (quoted.length > 240) { quoted = quoted.slice(0, 237) + '…'; }

        var subject = code + ' ' + spanId + ' — possible misrepresentation';
        var message = 'Article ' + code + ', span ' + spanId + '\n' +
            pageUrl + '\n\n' +
            (quoted ? 'The line: “' + quoted + '”\n\n' : '') +
            'What it misrepresents, and the tradition it concerns:\n';

        // The fragment has to stay last for the browser to act on it, so the
        // query is spliced in ahead of whatever hash the config value carries.
        var hash = '', q = base;
        var h = base.indexOf('#');
        if (h >= 0) { hash = base.slice(h); q = base.slice(0, h); }
        var sep = q.indexOf('?') >= 0 ? '&' : '?';
        var href = q + sep +
            'submission_type=suggestion' +
            '&subject=' + encodeURIComponent(subject) +
            '&message=' + encodeURIComponent(message) + hash;

        return '<p class="aoid-correction">' +
            '<a class="aoid-correction-link" href="' + esc(href) + '">' +
            'Does this misrepresent your tradition? Tell us</a></p>';
    }

    function anchorList(list, isRestoration, emptyText) {
        if (!list || !list.length) {
            return '<p class="ap-anchor-pane-empty">' + esc(emptyText) + '</p>';
        }
        return '<ul class="ap-anchor-list">' + list.map(function (a) {
            var url = scriptureUrl(a.ref);
            var ref = url
                ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(a.ref) + '</a>'
                : esc(a.ref);
            return '<li class="ap-anchor-item' + (isRestoration ? ' ap-restoration-ref' : '') + '">' +
                '<div class="ap-anchor-ref">' + ref + '</div>' +
                (a.text ? '<p class="ap-anchor-text">' + esc(a.text) + '</p>' : '') +
                (a.comment ? '<p class="ap-anchor-comment">' + esc(a.comment) + '</p>' : '') +
                '</li>';
        }).join('') + '</ul>';
    }

    function crossrefList(list) {
        return '<ul class="ap-crossref-list">' + list.map(function (x) {
            var ext = x.href && x.href.charAt(0) !== '#';
            return '<li><a class="ap-crossref-link" href="' + esc(x.href || '#') + '"' +
                (ext ? ' target="_blank" rel="noopener"' : '') + '>' +
                (x.label ? '<span class="ap-crossref-label">' + esc(x.label) + '</span>' : '') +
                '<span class="ap-crossref-title">' + esc(x.title || '') + '</span></a></li>';
        }).join('') + '</ul>';
    }

    function headerHtml(badges) {
        return '<div class="ap-header"><div class="ap-header-left">' + badges +
            '<button class="ap-seek" type="button" aria-label="Play the reading from this line">' +
                '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>' +
                '<span>Play from here</span>' +
            '</button>' +
            '<button class="ct-resume-film" type="button" hidden>' +
                '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>' +
                '<span>Resume film</span>' +
            '</button>' +
            '</div>' +
            '<button class="ap-close ct-hide-cites" type="button" aria-label="Hide citations">' +
                '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
                '<span>Hide citations</span>' +
            '</button></div>';
    }

    /* The ONE place the dock's markup is built. Stream and hold both call it;
       there is no second renderer. Structure and classes match the way
       articles-panel.js renders a span on /articles/ (the per-article label is
       the one omission — the whole page is that article). */
    function renderSpan(spanId, sentIdx) {
        var d = APP[spanId];
        if (!d) { return renderEmpty(sentIdx, 'Commentary for this line is not yet available.'); }

        var badges = (d.type ? '<span class="ap-type-badge" data-type="' + esc(d.type) + '">' + esc(typeBadgeLabel(d.type)) + '</span>' : '') +
            (d.named_concept ? '<span class="ap-named-badge">◈ Named</span>' : '');

        var biblical = d.biblical || [], restoration = d.restoration || [], crossref = d.crossref || [];
        var hasAnchors = biblical.length || restoration.length;
        var hasDef = !!(d.named_concept && d.definition && d.definition.trim());
        var hasComment = !!(d.panel_comment && d.panel_comment.trim());
        var bibFirst = biblical.length > 0;

        var body = '<div class="ap-span-text">“' + esc(d.text || sentText(sentIdx)) + '”</div>';
        if (hasDef) {
            body += '<div class="ap-definition-block"><h4 class="ap-section-title">Definition</h4>' +
                '<p class="ap-definition">' + definitionHtml(d.definition) + '</p></div>';
        }
        if (hasAnchors) {
            body += '<div class="ap-anchor-tabs-block">' +
                '<div class="ap-anchor-tab-bar" role="tablist">' +
                    '<button class="ap-anchor-tab' + (bibFirst ? ' ap-anchor-tab--active' : '') + '" type="button" role="tab" data-pane="bib" aria-selected="' + (bibFirst ? 'true' : 'false') + '">Biblical Witness</button>' +
                    '<button class="ap-anchor-tab' + (bibFirst ? '' : ' ap-anchor-tab--active') + '" type="button" role="tab" data-pane="res" aria-selected="' + (bibFirst ? 'false' : 'true') + '">Restoration Witness</button>' +
                '</div>' +
                '<div class="ap-anchor-pane' + (bibFirst ? '' : ' ap-hidden') + '" data-pane="bib" role="tabpanel">' +
                    anchorList(biblical, false, 'No biblical anchors for this span.') + '</div>' +
                '<div class="ap-anchor-pane' + (bibFirst ? ' ap-hidden' : '') + '" data-pane="res" role="tabpanel">' +
                    anchorList(restoration, true, 'No Restoration anchors for this span.') + '</div>' +
                '</div>';
        }
        if (hasComment) {
            body += '<div class="ap-comment-block"><h4 class="ap-section-title">Commentary</h4>' +
                '<p class="ap-comment">' + esc(d.panel_comment) + '</p></div>';
        }
        if (crossref.length) {
            body += '<div class="ap-crossref-block"><h4 class="ap-section-title">See Also</h4>' +
                crossrefList(crossref) + '</div>';
        }
        if (!hasDef && !hasAnchors && !hasComment && !crossref.length) {
            body += '<p class="ap-empty-note">Commentary for this span is not yet available.</p>';
        }
        body += correctionHtml(spanId, d.text || sentText(sentIdx));
        return headerHtml(badges) + '<div class="ap-body">' + body + '</div>';
    }

    /* Absence renders as absence. A line that carries no [data-span] gets this
       quiet state — never the previous line's citation held over as if it
       belonged here. */
    function renderEmpty(sentIdx, note) {
        return headerHtml('<span class="aoid-dock-badge">No citation</span>') +
            '<div class="ap-body">' +
            '<div class="ap-span-text">“' + esc(sentText(sentIdx)) + '”</div>' +
            '<p class="aoid-dock-empty">' + esc(note || 'This line carries no separate citation.') + '</p>' +
            '</div>';
    }

    /* ── Panel state ─────────────────────────────────────────────── */
    var streamOn = false;
    var held = null;             // { sent, span } — held for study; film paused
    var shown = null;            // what the dock is currently painted with

    function setDockHidden(hidden) {
        if (reading) { reading.classList.toggle('dock-hidden', hidden); }
    }
    function showBox() {
        panel.classList.add('ap-open');
        panel.setAttribute('aria-hidden', 'false');
        setDockHidden(false);
    }
    function hideBox() {
        panel.classList.remove('ap-open');
        panel.setAttribute('aria-hidden', 'true');
        backdrop.classList.remove('ap-open');
        setDockHidden(true);
    }

    function paint(sentIdx, spanId) {
        shown = { sent: sentIdx, span: spanId };
        panel.innerHTML = spanId ? renderSpan(spanId, sentIdx) : renderEmpty(sentIdx);

        var tabs = panel.querySelectorAll('.ap-anchor-tab');
        [].forEach.call(tabs, function (btn) {
            btn.addEventListener('click', function () {
                [].forEach.call(tabs, function (b) {
                    var on = b === btn;
                    b.classList.toggle('ap-anchor-tab--active', on);
                    b.setAttribute('aria-selected', on ? 'true' : 'false');
                });
                [].forEach.call(panel.querySelectorAll('.ap-anchor-pane'), function (p) {
                    p.classList.toggle('ap-hidden', p.dataset.pane !== btn.dataset.pane);
                });
            });
        });

        var hideBtn = panel.querySelector('.ct-hide-cites');
        if (hideBtn) { hideBtn.addEventListener('click', hideCitations); }

        var seekBtn = panel.querySelector('.ap-seek');
        if (seekBtn) {
            seekBtn.addEventListener('click', function () {
                var at = (spanId != null && SPAN_TIME[spanId] != null)
                    ? SPAN_TIME[spanId] : SENTS[sentIdx].start;
                if (player && playerReady) {
                    try { player.seekTo(at, true); player.playVideo(); } catch (_) {}
                }
                unhold(true);
            });
        }

        var resumeFilm = panel.querySelector('.ct-resume-film');
        if (resumeFilm) {
            resumeFilm.hidden = !held;
            resumeFilm.addEventListener('click', function () {
                if (player && playerReady) { try { player.playVideo(); } catch (_) {} }
                unhold(true);
            });
        }

        var b = panel.querySelector('.ap-body');
        if (b) { b.classList.remove('ct-fade'); void b.offsetWidth; b.classList.add('ct-fade'); }
    }

    function streamTo(sentIdx, spanId) {
        if (!streamOn || held || !WIDE.matches) { return; }
        paint(sentIdx, spanId);
        showBox();
    }

    function openStream() {
        if (prefOff()) { if (citeToggle) { citeToggle.classList.add('ct-show'); } return; }
        streamOn = true;
        if (citeToggle) { citeToggle.classList.remove('ct-show'); }
        if (!WIDE.matches) { return; }
        var i = (litSent != null) ? litSent : 0;
        paint(i, litSpan || (SENT_SPANS[i][0] && SENT_SPANS[i][0].id) || null);
        showBox();
    }

    function hideCitations() {
        if (held) { unhold(false); }
        streamOn = false;
        hideBox();
        setPrefOff(true);
        if (citeToggle) { citeToggle.classList.add('ct-show'); }
    }

    function showCitations() {
        setPrefOff(false);
        if (citeToggle) { citeToggle.classList.remove('ct-show'); }
        if (WIDE.matches) { openStream(); return; }
        var i = (litSent != null) ? litSent : 0;
        holdLine(i, litSpan || (SENT_SPANS[i][0] && SENT_SPANS[i][0].id) || null, false);
    }

    /* Hold a line for study. The film pauses and the stream is suspended until
       the reader resumes it. */
    function holdLine(sentIdx, spanId, pause) {
        if (pause !== false && player && playerReady) { try { player.pauseVideo(); } catch (_) {} }
        held = { sent: sentIdx, span: spanId };
        paintSentence(hlLit, 'aoid-lit', null);
        paintSentence(hlHeld, 'aoid-held', sentIdx);
        panel.classList.add('ct-pinned');
        paint(sentIdx, spanId);
        showBox();
        if (!WIDE.matches) { backdrop.classList.add('ap-open'); }
    }

    function unhold(rearm) {
        if (!held) { return; }
        held = null;
        paintSentence(hlHeld, 'aoid-held', null);
        if (litSent != null) { paintSentence(hlLit, 'aoid-lit', litSent); }
        panel.classList.remove('ct-pinned');
        backdrop.classList.remove('ap-open');
        if (rearm) { follow = true; if (resume) { resume.classList.remove('ct-show'); } }
        if (!WIDE.matches || !streamOn) { hideBox(); return; }
        if (litSent != null) { paint(litSent, litSpan); } else { hideBox(); }
    }

    /* ── Tap any line to hold & study ─────────────────────────────
       A click anywhere in the prose resolves to the sentence under the
       pointer, so plain narrative lines are holdable too — not only the
       underlined claims. */
    function tokenAtCaret(x, y) {
        var node = null, offset = 0;
        if (document.caretRangeFromPoint) {
            var r = document.caretRangeFromPoint(x, y);
            if (r) { node = r.startContainer; offset = r.startOffset; }
        } else if (document.caretPositionFromPoint) {
            var p = document.caretPositionFromPoint(x, y);
            if (p) { node = p.offsetNode; offset = p.offset; }
        }
        if (!node || node.nodeType !== 3) { return -1; }
        for (var k = 0; k < TOK.length; k++) {
            if (TOK[k].node === node && offset <= TOK[k].b) { return k; }
        }
        return -1;
    }

    function sentenceOfToken(k) {
        for (var i = 0; i < SENTS.length; i++) {
            if (k >= SENTS[i].w0 && k < SENTS[i].w1) { return i; }
        }
        return -1;
    }

    article.addEventListener('click', function (e) {
        if (e.target.closest('a') || e.target.closest('textarea') || e.target.closest('button')) { return; }

        var sentIdx = -1, spanId = null;

        if (!HL_OK) {
            var w = e.target.closest('[data-sent]');
            if (w) { sentIdx = parseInt(w.getAttribute('data-sent'), 10); }
        }
        if (sentIdx < 0) {
            var k = tokenAtCaret(e.clientX, e.clientY);
            if (k >= 0) { sentIdx = sentenceOfToken(k); spanId = TOK[k].s; }
        }
        if (sentIdx < 0) {
            // Last resort: the underlined claim itself.
            var sp = e.target.closest('[data-span]');
            if (!sp) { return; }
            spanId = sp.getAttribute('data-span');
            for (var q = 0; q < TOK.length; q++) {
                if (TOK[q].s === spanId) { sentIdx = sentenceOfToken(q); break; }
            }
        }
        if (sentIdx < 0) { return; }
        if (!spanId) {
            var list = SENT_SPANS[sentIdx];
            spanId = list && list.length ? list[0].id : null;
        }
        holdLine(sentIdx, spanId, true);
    });

    // Keyboard parity: the underlined claims stay reachable by Tab/Enter.
    [].forEach.call(article.querySelectorAll('[data-span]'), function (sp) {
        if (!sp.hasAttribute('tabindex')) {
            sp.setAttribute('tabindex', '0');
            sp.setAttribute('role', 'button');
            sp.setAttribute('aria-label', 'Hold and study: ' + sp.textContent.trim().slice(0, 60));
        }
        sp.addEventListener('keydown', function (e) {
            if (e.key !== 'Enter' && e.key !== ' ') { return; }
            e.preventDefault();
            var id = sp.getAttribute('data-span'), idx = -1;
            for (var q = 0; q < TOK.length; q++) { if (TOK[q].s === id) { idx = sentenceOfToken(q); break; } }
            if (idx >= 0) { holdLine(idx, id, true); }
        });
    });

    function dismiss() {
        if (held) { unhold(true); return; }
        if (!WIDE.matches) { hideBox(); }
    }
    backdrop.addEventListener('click', dismiss);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { dismiss(); } });

    var citeToggle = byId('citeToggle');
    if (citeToggle) { citeToggle.addEventListener('click', showCitations); }

    /* ── Streaming hint (dismissible, remembered) ─────────────────── */
    var hint = byId('hint'), hintX = byId('hintX');
    function hintDismissed() {
        try { return window.localStorage.getItem(CFG.hintKey) === 'off'; } catch (_) { return false; }
    }
    function showHint() { if (hint && !hintDismissed()) { hint.classList.add('ct-show'); } }
    if (hintX && hint) {
        hintX.addEventListener('click', function () {
            hint.classList.remove('ct-show');
            try { window.localStorage.setItem(CFG.hintKey, 'off'); } catch (_) {}
        });
    }

    /* ── The reflection textarea belongs to the journal on /articles/ ──
       It is not wired up here, and a box that silently loses what a reader
       types is worse than no box: point at the journal instead. */
    (function () {
        var ta = article.querySelector('.article-rjw .rjw-textarea');
        if (!ta) { return; }
        var a = document.createElement('a');
        a.className = 'aoid-rjw-link';
        a.href = CFG.articleUrl;
        a.textContent = 'Write your reflection in your Discipleship Journal →';
        ta.parentNode.replaceChild(a, ta);
    })();

    /* ── Entry / about worship notice ─────────────────────────────
       Worship gate first, always: nothing plays before Enter. A deep link
       cues its moment and holds its line instead of autoplaying. */
    var entry = byId('entry'), enterBtn = byId('enter'), aboutBtn = byId('about');

    function enterPage() {
        if (entry) { entry.classList.add('creation-hide'); }
        openStream();
        showHint();
        if (deepTime != null) {
            var i = 0;
            if (deepSpan) {
                for (var q = 0; q < TOK.length; q++) {
                    if (TOK[q].s === deepSpan) { i = sentenceOfToken(q); break; }
                }
            } else {
                i = Math.max(0, sentenceAt(deepTime));
            }
            litSent = i;
            litSpan = deepSpan;
            holdLine(i, deepSpan || ((SENT_SPANS[i][0] || {}).id || null), false);
            follow = false;
            if (resume) { resume.classList.add('ct-show'); }
            window.setTimeout(function () { centerSentence(i); }, 60);
            return;
        }
        if (player && playerReady) { try { player.playVideo(); } catch (_) {} }
    }

    if (enterBtn) { enterBtn.addEventListener('click', enterPage); }
    if (aboutBtn && entry) {
        aboutBtn.addEventListener('click', function () {
            entry.classList.remove('creation-hide');
            if (player && playerReady) { try { player.pauseVideo(); } catch (_) {} }
        });
    }
})();
