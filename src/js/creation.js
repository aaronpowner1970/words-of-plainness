/* ============================================================
   creation.js — /creation/  His Work and Glory  (YouTube path)
   - Plays the film via the YouTube IFrame Player API on the
     privacy-preserving youtube-nocookie host (adaptive bitrate).
   - Follows the film: highlights the active cue and auto-scrolls
     the transcript (with a resume-follow handoff).
   - Click a passage -> pause the film + open the citation panel
     (reuses the /articles/ .ap- apparatus; two-column Biblical /
     Restoration body via .ap-panel--creation).
   - On ENDED, an overlay covers YouTube's end-screen suggestions.
   - Entry/About worship notice; Enter starts playback.
   Data: window.WOP_CREATION_CITES {spanId:{st,ty,tx,pc,b[],r[]}}
         window.WOP_CREATION_VIDEO_ID "…"
   ============================================================ */
(function () {
    'use strict';

    var SCRIPTURE_BASE = 'https://www.churchofjesuschrist.org/study/scriptures/';
    var CITES = window.WOP_CREATION_CITES || {};
    var VIDEO_ID = window.WOP_CREATION_VIDEO_ID || '';

    var transcript = document.getElementById('creationTranscript');
    if (!transcript) return;

    var cues = [].slice.call(transcript.querySelectorAll('.ct-cue'));
    var spans = [].slice.call(transcript.querySelectorAll('.ct-span'));
    var cueData = cues.map(function (el) {
        return { el: el, s: parseFloat(el.dataset.cs), e: parseFloat(el.dataset.ce) };
    });

    // A span is interactive only when it carries real, viewable citation content
    // (drafted or locked). Pending scaffold stubs and removed narrative bridges
    // (e.g. s18, s35, s56, s57) get no marker — they render as inert prose.
    spans.forEach(function (sp) {
        var d = CITES[sp.dataset.s];
        if (d && d.st && d.st !== 'pending') {
            sp.setAttribute('data-has-cite', '');
            sp.setAttribute('data-status', d.st);
        }
    });

    var player = null, playerReady = false;
    var follow = true, litEl = null, lastIdx = 0, programmatic = false, pollTimer = null;
    var endedEl = document.getElementById('creationEnded');

    /* ---- YouTube IFrame Player API ---- */
    window.onYouTubeIframeAPIReady = function () {
        player = new YT.Player('creationVideo', {
            width: '100%', height: '100%', videoId: VIDEO_ID,
            host: 'https://www.youtube-nocookie.com',
            playerVars: {
                rel: 0, modestbranding: 1, playsinline: 1,
                cc_load_policy: 0, iv_load_policy: 3,
                origin: window.location.origin
            },
            events: {
                onReady: function () { playerReady = true; startPoll(); },
                onStateChange: onState
            }
        });
    };

    function onState(e) {
        if (e.data === YT.PlayerState.ENDED) { showEnded(); }
        else if (e.data === YT.PlayerState.PLAYING) { hideEnded(); }
    }

    function currentTime() {
        try { return (player && player.getCurrentTime) ? player.getCurrentTime() : 0; }
        catch (_) { return 0; }
    }

    /* ---- follow + highlight (poll the API clock) ---- */
    var stageWrap = document.querySelector('.creation-stage-wrap');

    // Center the active line in the reading band *below* the sticky player, not
    // in the whole viewport. On desktop the tall pinned player pushes viewport-
    // center onto its own bottom edge, so the lit line rode the player border.
    // Measured live each call: adapts to desktop/mobile, resize, fullscreen, and
    // the not-yet-pinned state (player off-screen -> offset 0 -> old behavior).
    // The reading field is the band between the film's bottom and the viewport
    // bottom; the active line is centred in THAT band, not in the viewport.
    // Measured live each call from the film's own rect, so it holds identically
    // whether the dock is open or closed (the film spans the container in both
    // states and its bottom edge does not move), and adapts to resize,
    // fullscreen, mobile, and the not-yet-pinned state (film off-screen ->
    // offset 0 -> plain viewport centring).
    function centerCue(el) {
        var vh = window.innerHeight || document.documentElement.clientHeight;
        var top = 0;
        if (stageWrap) {
            var pr = stageWrap.getBoundingClientRect();
            top = Math.min(Math.max(pr.bottom, 0), vh);   // how much of the top the player covers
        }
        if (vh - top < 160) top = Math.max(0, vh - 320);  // guard a too-thin band on short windows
        var r = el.getBoundingClientRect();
        var target = top + (vh - top) / 2;
        window.scrollBy({ top: (r.top + r.height / 2) - target, behavior: 'smooth' });
    }

    function startPoll() { if (!pollTimer) { pollTimer = window.setInterval(tick, 200); tick(); } }

    function activeCue(t) {
        if (lastIdx >= cueData.length || t < cueData[lastIdx].s) lastIdx = 0;
        for (var i = lastIdx; i < cueData.length; i++) {
            if (t >= cueData[i].s && t < cueData[i].e) { lastIdx = i; return cueData[i].el; }
            if (cueData[i].s > t) break;
        }
        return null;
    }

    function tick() {
        var c = activeCue(currentTime());
        if (c !== litEl) {
            // ct-active-span tints the whole sentence containing the lit cue.
            // Removed before it is added, so consecutive cues sharing a parent
            // span end up with the class still applied.
            if (litEl) {
                litEl.classList.remove('ct-lit');
                var prevSpan = litEl.closest && litEl.closest('.ct-span');
                if (prevSpan) prevSpan.classList.remove('ct-active-span');
            }
            if (c) {
                c.classList.add('ct-lit');
                var curSpan = c.closest && c.closest('.ct-span');
                if (curSpan) curSpan.classList.add('ct-active-span');
                // Stream: advance the panel only on a passage that actually has
                // citations. Connective spans hold the last cited one rather
                // than flashing an empty panel.
                if (curSpan && curSpan !== activeSpan) {
                    activeSpan = curSpan;
                    if (curSpan.hasAttribute('data-has-cite')) {
                        lastCited = curSpan;
                        streamTo(curSpan);
                    }
                }
                if (follow) {
                    programmatic = true;
                    centerCue(c);
                    window.clearTimeout(tick._p);
                    tick._p = window.setTimeout(function () { programmatic = false; }, 650);
                }
            }
            litEl = c;
        }
    }

    /* ---- ended overlay (blocks YouTube suggestion grid) ---- */
    function showEnded() { if (endedEl) { endedEl.classList.add('creation-ended--show'); endedEl.setAttribute('aria-hidden', 'false'); } }
    function hideEnded() { if (endedEl) { endedEl.classList.remove('creation-ended--show'); endedEl.setAttribute('aria-hidden', 'true'); } }
    var replay = document.getElementById('creationReplay');
    if (replay) replay.addEventListener('click', function () {
        hideEnded();
        if (player && playerReady) { try { player.seekTo(0, true); player.playVideo(); } catch (_) {} }
    });

    /* ---- resume-follow handoff on manual scroll ---- */
    var resume = document.getElementById('ctResume');
    window.addEventListener('scroll', function () {
        if (programmatic) return;
        if (follow) { follow = false; if (resume) resume.classList.add('ct-show'); }
    }, { passive: true });
    if (resume) resume.addEventListener('click', function () {
        follow = true; resume.classList.remove('ct-show');
        if (litEl) { programmatic = true; centerCue(litEl);
            window.setTimeout(function () { programmatic = false; }, 650); }
    });

    /* ---- citation panel (reuses articles-panel.css .ap-) ----
       ONE panel serves three states:
         stream  — docked column (>=1200px), follows the film, never pauses
         pinned  — a passage held for study; the film is paused
         overlay — narrow screens: tapping a passage raises it as a drawer
       Non-modal by design. Focus was never trapped here, so aria-modal is no
       longer claimed; role is complementary and the film keeps playing. */
    var PREF_KEY = 'wop_creation_citations';
    var HINT_KEY = 'wop_creation_hint';
    var WIDE = window.matchMedia('(min-width: 1200px)');

    function prefOff() {
        try { return window.localStorage.getItem(PREF_KEY) === 'off'; } catch (_) { return false; }
    }
    function setPrefOff(off) {
        try {
            if (off) { window.localStorage.setItem(PREF_KEY, 'off'); }
            else { window.localStorage.removeItem(PREF_KEY); }
        } catch (_) {}
    }

    var dock = document.getElementById('creationDock');
    var citeToggle = document.getElementById('ctCiteToggle');
    var backdrop = document.createElement('div');
    backdrop.className = 'ap-backdrop';
    var panel = document.createElement('aside');
    panel.className = 'ap-panel ap-panel--creation ct-docked';
    panel.setAttribute('role', 'complementary');
    panel.setAttribute('aria-label', 'Scriptures behind the passage now playing');
    panel.setAttribute('aria-hidden', 'true');
    document.body.appendChild(backdrop);
    (dock || document.body).appendChild(panel);

    function esc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

    function anchorItems(list, restoration) {
        if (!list || !list.length) {
            return '<p class="ap-col-empty">' +
                (restoration ? 'No Restoration witness cited for this span yet.' : '\u2014') + '</p>';
        }
        return '<ul class="ap-anchor-list">' + list.map(function (a) {
            return '<li class="ap-anchor-item">' +
                '<div class="ap-anchor-ref"><a href="' + SCRIPTURE_BASE + a.url + '" target="_blank" rel="noopener">' + esc(a.ref) + '</a></div>' +
                '<p class="ap-anchor-text">' + esc(a.text) + '</p>' +
                (a.comment ? '<p class="ap-anchor-comment">' + esc(a.comment) + '</p>' : '') +
                '</li>';
        }).join('') + '</ul>';
    }

    /* The ONE place citation markup is built. Both the stream and the
       pinned/overlay view call this \u2014 there is no second renderer. */
    function renderCitations(spanEl) {
        var id = spanEl.dataset.s;
        var d = CITES[id] || { st: 'pending', ty: '', tx: spanEl.textContent.trim(), pc: '', b: [], r: [] };

        var body;
        if (d.st === 'pending') {
            body = '<div class="ap-pending">Citations for this passage are pending. This span is part of the ' +
                'comprehensive apparatus scaffold; its exhaustive biblical and Restoration anchors and interfaith ' +
                'commentary are sourced from the A3 Creation Scriptural Compilation and the Ch&#8202;42 / Ch&#8202;39 ' +
                'manuscript commentary.</div>';
        } else {
            body =
                (d.pc ? '<div class="ap-comment-block"><p class="ap-comment">' + esc(d.pc) + '</p></div>' : '') +
                '<div class="ap-cols">' +
                    '<div class="ap-col"><p class="ap-section-title ap-section-title--biblical">Biblical</p>' + anchorItems(d.b, false) + '</div>' +
                    '<div class="ap-col ap-restoration-ref"><p class="ap-section-title ap-section-title--restoration">Restoration witness</p>' + anchorItems(d.r, true) + '</div>' +
                '</div>';
        }

        return '<div class="ap-header"><div class="ap-header-left">' +
                (d.ty ? '<span class="ap-type-badge" data-type="' + esc(d.ty) + '">' + esc(d.ty) + '</span>' : '') +
                '<button class="ap-seek" type="button" aria-label="Play the film from this passage">' +
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
            '</button></div>' +
            '<div class="ap-body">' +
                '<div class="ap-span-text">\u201C' + esc(d.tx || spanEl.textContent.trim()) + '\u201D</div>' +
                body +
            '</div>';
    }

    /* ---- panel state ---- */
    var streamOn = false;      // stream enabled (and panel showing)
    var pinned = null;         // span held for study; film paused
    var activeSpan = null;     // span under the lit cue
    var lastCited = null;      // last span that HAD citations \u2014 held over bridges

    function firstCited() {
        for (var i = 0; i < spans.length; i++) {
            if (spans[i].hasAttribute('data-has-cite')) return spans[i];
        }
        return null;
    }

    // .dock-hidden collapses the two-column grid to one and drops the dock
    // track, so the transcript reflows to the full container width whenever the
    // panel is not showing. Ships on by default in the markup (panel starts
    // closed); every visibility change flows through showBox/hideBox, so the
    // layout and the panel can never disagree.
    var reading = document.getElementById('creationReading');
    function setDockHidden(hidden) {
        if (reading) reading.classList.toggle('dock-hidden', hidden);
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

    function paint(spanEl) {
        panel.innerHTML = renderCitations(spanEl);

        var hideBtn = panel.querySelector('.ct-hide-cites');
        if (hideBtn) hideBtn.addEventListener('click', hideCitations);

        var seekBtn = panel.querySelector('.ap-seek');
        if (seekBtn) seekBtn.addEventListener('click', function () {
            var startT = parseFloat(spanEl.dataset.start);
            if (player && playerReady && !isNaN(startT)) {
                try { player.seekTo(startT, true); player.playVideo(); } catch (_) {}
            }
            unpin(true);
        });

        var resumeFilm = panel.querySelector('.ct-resume-film');
        if (resumeFilm) {
            resumeFilm.hidden = !pinned;
            resumeFilm.addEventListener('click', function () {
                if (player && playerReady) { try { player.playVideo(); } catch (_) {} }
                unpin(true);
            });
        }

        // Calm fade on each new passage; the reduced-motion block neutralises it.
        var b = panel.querySelector('.ap-body');
        if (b) { b.classList.remove('ct-fade'); void b.offsetWidth; b.classList.add('ct-fade'); }
    }

    /* Stream: follow the film. Never pauses, never steals focus. */
    function streamTo(spanEl) {
        if (!streamOn || pinned || !WIDE.matches) return;
        paint(spanEl);
        showBox();
    }

    function openStream() {
        if (prefOff()) { if (citeToggle) citeToggle.classList.add('ct-show'); return; }
        streamOn = true;
        if (citeToggle) citeToggle.classList.remove('ct-show');
        if (!WIDE.matches) return;                       // no forced stream when narrow
        var seed = lastCited || activeSpan || firstCited();
        if (seed) { paint(seed); showBox(); }
    }

    function hideCitations() {
        if (pinned) unpin(false);
        streamOn = false;
        hideBox();
        setPrefOff(true);
        if (citeToggle) citeToggle.classList.add('ct-show');
    }

    function showCitations() {
        setPrefOff(false);
        if (citeToggle) citeToggle.classList.remove('ct-show');
        if (WIDE.matches) { openStream(); return; }
        var sp = lastCited || activeSpan || firstCited();   // narrow: current passage on demand
        if (sp) pinSpan(sp);
    }

    /* Pin: hold a passage for study. Pauses the film and suspends the stream. */
    function pinSpan(spanEl) {
        if (player && playerReady) { try { player.pauseVideo(); } catch (_) {} }
        if (pinned) pinned.classList.remove('ct-open');
        pinned = spanEl;
        spanEl.classList.add('ct-open');
        panel.classList.add('ct-pinned');
        paint(spanEl);
        showBox();
        if (!WIDE.matches) backdrop.classList.add('ap-open');
    }

    function unpin(rearm) {
        if (pinned) { pinned.classList.remove('ct-open'); pinned = null; }
        panel.classList.remove('ct-pinned');
        backdrop.classList.remove('ap-open');
        if (rearm) { follow = true; if (resume) resume.classList.remove('ct-show'); }

        if (!WIDE.matches || !streamOn) { hideBox(); return; }
        var sp = lastCited || activeSpan;                // back to the stream
        if (sp) paint(sp); else hideBox();
    }

    spans.forEach(function (sp) {
        if (!sp.hasAttribute('data-has-cite')) return;   // inert bridge / pending stub
        sp.addEventListener('click', function () { pinSpan(sp); });
        sp.setAttribute('tabindex', '0');
        sp.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pinSpan(sp); }
        });
    });

    // Backdrop / Escape release the pin (or close the narrow overlay). Neither
    // sets the remembered preference \u2014 only the labelled Hide control does.
    function dismiss() {
        if (pinned) { unpin(true); return; }
        if (!WIDE.matches) hideBox();
    }
    backdrop.addEventListener('click', dismiss);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') dismiss(); });
    if (citeToggle) citeToggle.addEventListener('click', showCitations);

    /* ---- streaming hint (dismissible, remembered) ---- */
    var hint = document.getElementById('ctHint');
    var hintX = document.getElementById('ctHintX');
    function hintDismissed() {
        try { return window.localStorage.getItem(HINT_KEY) === 'off'; } catch (_) { return false; }
    }
    function showHint() { if (hint && !hintDismissed()) hint.classList.add('ct-show'); }
    if (hintX && hint) hintX.addEventListener('click', function () {
        hint.classList.remove('ct-show');
        try { window.localStorage.setItem(HINT_KEY, 'off'); } catch (_) {}
    });

    /* ---- entry / about worship notice ----
       Worship gate first, always: the stream opens on Enter, never before. */
    var entry = document.getElementById('creationEntry');
    var enterBtn = document.getElementById('creationEnterBtn');
    var aboutBtn = document.getElementById('creationAboutBtn');
    if (enterBtn && entry) enterBtn.addEventListener('click', function () {
        entry.classList.add('creation-hide');
        if (player && playerReady) { try { player.playVideo(); } catch (_) {} }
        openStream();          // no-ops (and offers the toggle) when the pref is 'off'
        showHint();
    });
    if (aboutBtn && entry) aboutBtn.addEventListener('click', function () {
        entry.classList.remove('creation-hide');
        if (player && playerReady) { try { player.pauseVideo(); } catch (_) {} }
    });
})();
