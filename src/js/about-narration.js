/**
 * about-narration.js — the opt-in narrated-video player on /about/.
 *
 * Nothing plays until the visitor asks: the "Hear it from me" button, or a click
 * on any narrated sentence. Sync, auto-scroll and click-to-seek come from
 * js/sync-core.js; times come from the /about/narration.vtt track, which is
 * generated from src/_data/about_narration_timing.json.
 */
(function () {
    'use strict';

    var entry = document.getElementById('narrEntry');
    if (!entry || !window.WopSync) return;
    var probe = document.createElement('video');
    if (!probe.canPlayType || !probe.canPlayType('video/mp4')) return;

    var cfg = {
        desktop: entry.dataset.videoDesktop,
        mobile: entry.dataset.videoMobile,
        audio: entry.dataset.audio,
        poster: entry.dataset.poster,
        vtt: entry.dataset.vtt,
        duration: parseFloat(entry.dataset.duration) || 0
    };
    var KEY = 'wop-about-narration-v1';
    var mqDock = window.matchMedia('(max-width: 768px)');

    /* ---------- persistence (localStorage may be missing or throw) ---------- */
    function loadState() {
        try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (_) { return {}; }
    }
    function saveState() {
        try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (_) { /* page still works */ }
    }
    var st = loadState();
    if (typeof st !== 'object' || st === null) st = {};
    var lastSave = 0;

    /* ---------- DOM ---------- */
    var ICON = {
        play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>',
        pause: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>',
        prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 5h2v14H6zM20 5v14L9 12z"/></svg>',
        next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 5h2v14h-2zM4 5v14l11-7z"/></svg>',
        min: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 17h14v2H5z"/></svg>',
        expand: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h7v2H6v5H4zM20 20h-7v-2h5v-5h2z"/></svg>',
        close: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.4 5 5 6.4 10.6 12 5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6L19 6.4 17.6 5 12 10.6z"/></svg>',
        audio: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 0 0-9 9v6a3 3 0 0 0 3 3h2v-8H5v-1a7 7 0 0 1 14 0v1h-3v8h2a3 3 0 0 0 3-3v-6a9 9 0 0 0-9-9z"/></svg>',
        pip: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18v14H3zm2 2v10h14V7zm7 5h6v4h-6z"/></svg>',
        swap: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3 3 7h3v7h2V7h3zm10 18 4-4h-3V10h-2v7h-3z"/></svg>'
    };

    var player = document.createElement('div');
    player.className = 'narr-player';
    player.hidden = true;
    player.setAttribute('role', 'region');
    player.setAttribute('aria-label', 'Narration player');
    player.innerHTML =
        '<div class="narr-player__bar">' +
            '<span class="narr-player__title">Hear it from me</span>' +
            '<button type="button" class="narr-btn narr-btn--swap" data-act="dock" aria-label="Move player to the top of the screen">' + ICON.swap + '</button>' +
            '<button type="button" class="narr-btn narr-btn--audio" data-act="audio" aria-pressed="false" aria-label="Audio only">' + ICON.audio + '</button>' +
            '<button type="button" class="narr-btn narr-btn--pip" data-act="pip" aria-label="Picture in picture" hidden>' + ICON.pip + '</button>' +
            '<button type="button" class="narr-btn" data-act="min" aria-label="Minimize player">' + ICON.min + '</button>' +
            '<button type="button" class="narr-btn" data-act="close" aria-label="Close player">' + ICON.close + '</button>' +
        '</div>' +
        '<div class="narr-player__stage">' +
            '<video class="narr-player__video" playsinline preload="none" poster="' + cfg.poster + '">' +
                '<track kind="metadata" src="' + cfg.vtt + '" srclang="en" label="Narration targets">' +
            '</video>' +
            '<button type="button" class="narr-mini narr-mini--expand" data-act="expand" aria-label="Expand player">' + ICON.expand + '</button>' +
            '<button type="button" class="narr-mini narr-mini--play" data-act="play" aria-label="Play">' + ICON.play + '</button>' +
        '</div>' +
        '<div class="narr-player__controls">' +
            '<button type="button" class="narr-btn" data-act="prev" aria-label="Previous sentence">' + ICON.prev + '</button>' +
            '<button type="button" class="narr-btn narr-btn--play" data-act="play" aria-label="Play">' + ICON.play + '</button>' +
            '<button type="button" class="narr-btn" data-act="next" aria-label="Next sentence">' + ICON.next + '</button>' +
            '<input type="range" class="narr-player__range" min="0" max="' + cfg.duration + '" step="1" value="0" aria-label="Seek narration">' +
            '<span class="narr-player__time" aria-hidden="true">0:00</span>' +
        '</div>' +
        '<span class="narr-player__resize" aria-hidden="true"></span>';
    document.body.appendChild(player);

    var pill = document.createElement('button');
    pill.type = 'button';
    pill.className = 'narr-pill';
    pill.hidden = true;
    pill.textContent = 'Return to narration';
    document.body.appendChild(pill);

    var video = player.querySelector('video');
    var trackEl = player.querySelector('track');
    var range = player.querySelector('.narr-player__range');
    var timeEl = player.querySelector('.narr-player__time');
    var titleEl = player.querySelector('.narr-player__title');
    var pipBtn = player.querySelector('.narr-btn--pip');
    var audioBtn = player.querySelector('.narr-btn--audio');
    var dockBtn = player.querySelector('.narr-btn--swap');
    var labelEl = entry.querySelector('.narr-entry__label');
    var subEl = entry.querySelector('.narr-entry__sub');
    var subDefault = subEl ? subEl.textContent : '';

    var closed = true;

    /* ---------- helpers ---------- */
    function fmt(s) {
        s = Math.max(0, Math.round(s || 0));
        return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }
    function clamp(v, lo, hi) { return Math.min(Math.max(v, lo), hi); }
    function chosenSrc() { return st.audioOnly ? cfg.audio : (mqDock.matches ? cfg.mobile : cfg.desktop); }

    function ensureSrc() {
        if (video.getAttribute('src')) return;
        video.src = chosenSrc();
        if (st.t > 0 && !st.finished) { try { video.currentTime = st.t; } catch (_) { /* set on loadedmetadata */ } }
    }
    video.addEventListener('loadedmetadata', function () {
        if (video._want != null) { video.currentTime = video._want; video._want = null; }
        else if (st.t > 0 && !st.finished && video.currentTime === 0 && !video._started) video.currentTime = st.t;
    });

    function play() {
        ensureSrc();
        if (st.finished || sync.isFinished()) {
            st.finished = false;
            sync.reset();
            try { video.currentTime = 0; } catch (_) { /* ignore */ }
        }
        var p = video.play();
        if (p && p.catch) p.catch(function () { /* blocked or interrupted: the visitor can press play */ });
    }
    function pause() { video.pause(); }
    function toggle() { if (video.paused) play(); else pause(); }

    /* ---------- entry button text ---------- */
    function entryText() {
        if (!labelEl) return;
        if (st.finished) { labelEl.textContent = 'Hear it again'; if (subEl) subEl.textContent = subDefault; }
        else if (!closed && !player.hidden) { labelEl.textContent = 'Hear it from me'; if (subEl) subEl.textContent = 'Narration is open'; }
        else if (st.t > 5) { labelEl.textContent = 'Resume narration'; if (subEl) subEl.textContent = 'Pick up at ' + fmt(st.t); }
        else { labelEl.textContent = 'Hear it from me'; if (subEl) subEl.textContent = subDefault; }
    }

    /* ---------- open / close / minimize ---------- */
    function open() {
        closed = false;
        player.hidden = false;
        if (st.finished) st.min = false;
        applyMin();
        layout();
        entryText();
        sync.resumeFollow({ scroll: false });
    }
    function close() {
        pause();
        closed = true;
        player.hidden = true;
        pill.hidden = true;
        st.t = video.currentTime || st.t;
        saveState();
        entryText();
        setInsetVars();
    }
    function applyMin() {
        var on = !!st.min;
        player.dataset.min = on ? 'true' : 'false';
        var b = player.querySelector('[data-act="min"]');
        b.setAttribute('aria-label', on ? 'Expand player' : 'Minimize player');
        layout();
    }
    function setMin(on) { st.min = !!on; applyMin(); saveState(); }

    /* ---------- layout: float (desktop) or dock (mobile) ---------- */
    function layout() {
        var dock = mqDock.matches;
        player.dataset.layout = dock ? 'dock' : 'float';
        if (dock) {
            player.dataset.dock = st.dock === 'top' ? 'top' : 'bottom';
            player.style.left = player.style.top = player.style.width = '';
            dockBtn.setAttribute('aria-label', st.dock === 'top' ? 'Move player to the bottom of the screen' : 'Move player to the top of the screen');
        } else {
            delete player.dataset.dock;
            var w = clamp(st.w || 224, 160, Math.min(420, window.innerWidth - 16));
            player.style.width = w + 'px';
            if (typeof st.x !== 'number' || typeof st.y !== 'number') {
                st.x = Math.max(12, Math.round((window.innerWidth - 800) / 2 - w - 24));
                st.y = 120;
            }
            player.style.left = st.x + 'px';
            player.style.top = st.y + 'px';
            clampToViewport();
        }
        setInsetVars();
    }
    function clampToViewport() {
        if (mqDock.matches || player.hidden) return;
        var r = player.getBoundingClientRect();
        if (r.width > window.innerWidth) { player.style.width = Math.max(160, window.innerWidth - 16) + 'px'; r = player.getBoundingClientRect(); }
        var x = clamp(r.left, 0, Math.max(0, window.innerWidth - r.width));
        var y = clamp(r.top, 0, Math.max(0, window.innerHeight - r.height));
        player.style.left = x + 'px';
        player.style.top = y + 'px';
        st.x = Math.round(x); st.y = Math.round(y);
    }
    function headerBottom() {
        var h = document.querySelector('.header');
        return h ? Math.min(Math.max(h.getBoundingClientRect().bottom, 0), 140) : 0;
    }
    function setInsetVars() {
        var root = document.documentElement.style;
        root.setProperty('--narr-header-h', headerBottom() + 'px');
        var dockedBottom = !closed && !player.hidden && mqDock.matches && player.dataset.dock !== 'top';
        root.setProperty('--narr-dock-b', dockedBottom ? player.offsetHeight + 'px' : '0px');
    }
    // Only a docked (mobile) player reserves space; a free-dragged desktop player is ignored.
    function insets() {
        var top = headerBottom() + 8, bottom = 16;
        if (!closed && !player.hidden && mqDock.matches) {
            var h = player.offsetHeight;
            if (player.dataset.dock === 'top') top += h; else bottom += h;
        }
        return { top: top, bottom: bottom };
    }

    /* ---------- drag + resize (desktop) ---------- */
    var drag = null;
    player.addEventListener('pointerdown', function (e) {
        if (mqDock.matches || e.button !== 0) return;
        var onBar = e.target.closest('.narr-player__bar') && !e.target.closest('button');
        var onMiniStage = player.dataset.min === 'true' && e.target.closest('.narr-player__stage') && !e.target.closest('.narr-mini--play');
        var onResize = e.target.closest('.narr-player__resize');
        if (!onBar && !onMiniStage && !onResize) return;
        var r = player.getBoundingClientRect();
        drag = { kind: onResize ? 'resize' : 'move', sx: e.clientX, sy: e.clientY, x: r.left, y: r.top, w: r.width, moved: false, id: e.pointerId };
        player.setPointerCapture(e.pointerId);
        if (!onResize) player.classList.add('is-dragging');
        e.preventDefault();
    });
    player.addEventListener('pointermove', function (e) {
        if (!drag || e.pointerId !== drag.id) return;
        var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
        if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
        if (drag.kind === 'move') {
            player.style.left = drag.x + dx + 'px';
            player.style.top = drag.y + dy + 'px';
        } else {
            var w = clamp(drag.w + Math.max(dx, dy), 160, Math.min(480, window.innerWidth - drag.x));
            player.style.width = w + 'px';
            st.w = Math.round(w);
        }
    });
    function endDrag(e) {
        if (!drag || (e && e.pointerId !== drag.id)) return;
        var d = drag; drag = null;
        player.classList.remove('is-dragging');
        clampToViewport();
        saveState();
        if (d.kind === 'move' && !d.moved && player.dataset.min === 'true') setMin(false);   // a tap on the mini circle expands it
    }
    player.addEventListener('pointerup', endDrag);
    player.addEventListener('pointercancel', endDrag);
    window.addEventListener('resize', function () { layout(); });
    window.addEventListener('orientationchange', function () { setTimeout(layout, 200); });
    if (mqDock.addEventListener) mqDock.addEventListener('change', layout);

    /* ---------- controls ---------- */
    player.addEventListener('click', function (e) {
        var b = e.target.closest('[data-act]');
        if (!b) return;
        switch (b.dataset.act) {
            case 'play': toggle(); break;
            case 'prev': sync.prev(); break;
            case 'next': sync.next(); break;
            case 'min': setMin(!st.min); break;
            case 'expand': setMin(false); break;
            case 'close': close(); break;
            case 'dock': st.dock = st.dock === 'top' ? 'bottom' : 'top'; layout(); saveState(); break;
            case 'audio': setAudioOnly(!st.audioOnly); break;
            case 'pip':
                if (document.pictureInPictureElement) document.exitPictureInPicture();
                else if (video.requestPictureInPicture) video.requestPictureInPicture().catch(function () {});
                break;
        }
    });
    range.addEventListener('input', function () {
        ensureSrc();
        video.currentTime = parseFloat(range.value);
        sync.resumeFollow({ scroll: true });
    });
    if (document.pictureInPictureEnabled && video.requestPictureInPicture) pipBtn.hidden = false;

    function setAudioOnly(on) {
        var t = video.currentTime || st.t || 0, wasPlaying = !video.paused;
        st.audioOnly = !!on;
        player.dataset.audio = on ? 'true' : 'false';
        audioBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
        pipBtn.disabled = !!on;
        if (document.pictureInPictureElement && on) document.exitPictureInPicture().catch(function () {});
        if (video.getAttribute('src')) {
            video._want = t;
            video.src = chosenSrc();
            video.load();
            if (wasPlaying) play();
        }
        saveState();
    }

    /* ---------- media events -> UI ---------- */
    function syncUi() {
        var playing = !video.paused && !video.ended;
        player.dataset.playing = playing ? 'true' : 'false';
        player.querySelectorAll('[data-act="play"]').forEach(function (b) {
            b.innerHTML = playing ? ICON.pause : ICON.play;
            b.setAttribute('aria-label', playing ? 'Pause' : 'Play');
        });
    }
    video.addEventListener('play', function () { video._started = true; syncUi(); });
    video.addEventListener('pause', function () { syncUi(); st.t = video.currentTime; saveState(); });
    video.addEventListener('ended', syncUi);
    video.addEventListener('timeupdate', function () {
        var t = video.currentTime;
        range.value = t;
        timeEl.textContent = fmt(t) + ' / ' + fmt(cfg.duration || video.duration);
        if (Date.now() - lastSave > 2000 && !st.finished) { lastSave = Date.now(); st.t = t; saveState(); }
    });
    video.addEventListener('error', function () { titleEl.textContent = 'Narration unavailable'; });
    window.addEventListener('pagehide', function () { if (!st.finished) st.t = video.currentTime || st.t; saveState(); });

    /* ---------- the shared sync component ---------- */
    var sync = WopSync.create({
        mode: 'video',
        media: video,
        trackEl: trackEl,
        selector: '[data-narr]',
        idAttr: 'data-narr',
        insets: insets,
        keysActive: function () { return !closed && !player.hidden; },
        onToggle: toggle,
        onEscape: close,
        onTargetClick: function (id) {
            if (closed || player.hidden) { st.min = false; open(); }
            ensureSrc();
            st.finished = false;
            sync.seekTo(id, { scroll: false });
            play();
        },
        onSuspend: function () { if (!closed && !player.hidden) { setInsetVars(); pill.hidden = false; } },
        onResume: function () { pill.hidden = true; },
        onEnd: function () {
            st.finished = true; st.t = 0;
            pause();
            pill.hidden = true;
            st.min = true; applyMin();
            saveState();
            entryText();
        }
    });
    sync.start();

    pill.addEventListener('click', function () { sync.resumeFollow({ scroll: true }); pill.hidden = true; });

    /* ---------- targets: focusable, hover cue ---------- */
    document.querySelectorAll('[data-narr]').forEach(function (el) { el.setAttribute('tabindex', '0'); });
    document.documentElement.classList.add('narr-ready');

    /* ---------- entry button ---------- */
    entry.closest('.narr-entry').hidden = false;
    entry.addEventListener('click', function () {
        if (closed || player.hidden) open();
        if (st.min && !st.finished) setMin(false);
        play();
    });

    if (st.audioOnly) { player.dataset.audio = 'true'; audioBtn.setAttribute('aria-pressed', 'true'); pipBtn.disabled = true; }
    entryText();
})();
