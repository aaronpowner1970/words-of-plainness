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
            if (litEl) litEl.classList.remove('ct-lit');
            if (c) {
                c.classList.add('ct-lit');
                if (follow) {
                    programmatic = true;
                    c.scrollIntoView({ block: 'center', behavior: 'smooth' });
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
        if (litEl) { programmatic = true; litEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
            window.setTimeout(function () { programmatic = false; }, 650); }
    });

    /* ---- citation panel (reuses articles-panel.css .ap-) ---- */
    var backdrop = document.createElement('div');
    backdrop.className = 'ap-backdrop';
    var panel = document.createElement('aside');
    panel.className = 'ap-panel ap-panel--creation';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-hidden', 'true');
    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

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

    var openSpan = null;
    function openPanel(spanEl) {
        var id = spanEl.dataset.s;
        var d = CITES[id] || { st: 'pending', ty: '', tx: spanEl.textContent.trim(), pc: '', b: [], r: [] };

        if (player && playerReady) { try { player.pauseVideo(); } catch (_) {} }
        if (openSpan) openSpan.classList.remove('ct-open');
        spanEl.classList.add('ct-open'); openSpan = spanEl;

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

        panel.innerHTML =
            '<div class="ap-header"><div class="ap-header-left">' +
                (d.ty ? '<span class="ap-type-badge" data-type="' + esc(d.ty) + '">' + esc(d.ty) + '</span>' : '') +
                '<button class="ap-seek" type="button" aria-label="Play the film from this passage">' +
                    '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>' +
                    '<span>Play from here</span>' +
                '</button>' +
            '</div>' +
            '<button class="ap-close" type="button" aria-label="Close">' +
                '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            '</button></div>' +
            '<div class="ap-body">' +
                '<div class="ap-span-text">\u201C' + esc(d.tx || spanEl.textContent.trim()) + '\u201D</div>' +
                body +
            '</div>';

        panel.querySelector('.ap-close').addEventListener('click', closePanel);
        (function () {
            var seekBtn = panel.querySelector('.ap-seek');
            if (!seekBtn) return;
            var startT = parseFloat(spanEl.dataset.start);
            seekBtn.addEventListener('click', function () {
                if (player && playerReady && !isNaN(startT)) {
                    try { player.seekTo(startT, true); player.playVideo(); } catch (_) {}
                }
                follow = true; if (resume) resume.classList.remove('ct-show');  // re-arm auto-follow
                closePanel();
            });
        })();
        panel.classList.add('ap-open');
        backdrop.classList.add('ap-open');
        panel.setAttribute('aria-hidden', 'false');
    }

    function closePanel() {
        panel.classList.remove('ap-open');
        backdrop.classList.remove('ap-open');
        panel.setAttribute('aria-hidden', 'true');
        if (openSpan) { openSpan.classList.remove('ct-open'); openSpan = null; }
    }

    spans.forEach(function (sp) {
        if (!sp.hasAttribute('data-has-cite')) return;   // inert bridge / pending stub
        sp.addEventListener('click', function () { openPanel(sp); });
        sp.setAttribute('tabindex', '0');
        sp.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPanel(sp); }
        });
    });
    backdrop.addEventListener('click', closePanel);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePanel(); });

    /* ---- entry / about worship notice ---- */
    var entry = document.getElementById('creationEntry');
    var enterBtn = document.getElementById('creationEnterBtn');
    var aboutBtn = document.getElementById('creationAboutBtn');
    if (enterBtn && entry) enterBtn.addEventListener('click', function () {
        entry.classList.add('creation-hide');
        if (player && playerReady) { try { player.playVideo(); } catch (_) {} }
    });
    if (aboutBtn && entry) aboutBtn.addEventListener('click', function () {
        entry.classList.remove('creation-hide');
        if (player && playerReady) { try { player.pauseVideo(); } catch (_) {} }
    });
})();
