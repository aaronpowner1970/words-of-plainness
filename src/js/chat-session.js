/* ============================================================
   chat-session.js — /chat/video-NN/ only.

   The chat pages are the reading pages (or /creation/) shown to a room:
   in VR, or on a projector at an in-person group. Visitor mics are off
   while a film plays and open afterwards for questions, and people
   arrive all evening — so the SCREEN has to answer "why can't I talk?"
   without anyone having to ask it.

   This script owns the wings, the mic state, the part gate, focus view
   and the host keys. It owns nothing else. It never reaches inside
   aoid-video.js or creation.js: those two dispatch 'wop:player',
   'wop:state' and (on the creation layout) 'wop:dock', and those three
   events are the whole interface. So the public pages carry none of
   this, and the follow / dock / worship-gate behaviour the chat pages
   inherit is the same code, not a second copy.

   Everything page-specific arrives in window.WOP_CHAT (see the chat
   branch of layouts/aoid-video.njk and layouts/creation.njk). The part
   break in particular is DATA — src/_data/chat_videos.json — never a
   number in this file.

   HOST CONTROLS, deliberately invisible
     M   open the mics early, or close them again; pressing M a third
         time hands control back to the film
     F   focus view on/off (the "Focus video" button does the same)
   Nothing on screen advertises either one. A screen-share should show
   the room what it needs and nothing about how it is driven.
   ============================================================ */
(function () {
    'use strict';

    var root = document.documentElement;
    if (!document.querySelector('.chat-stage-row')) { return; }

    var CFG = window.WOP_CHAT || {};
    var TITLE = CFG.title || '';

    /* ── The part gate ───────────────────────────────────────────
       "His Work and Glory" is really two films: the Creation account in
       the words of scripture, then a prayer of gratitude built entirely
       out of biblical quotation. The host usually shows the first only,
       so the evening stops at the break and the prayer stays one click
       away. The boundary is a real ten-second silence in the reading,
       and it lives in chat_videos.json — this file only reads it. */
    var PARTS = CFG.parts || null;
    var PART1_END = (PARTS && PARTS[0] && typeof PARTS[0].end === 'number') ? PARTS[0].end : null;
    var HAS_PARTS = PART1_END !== null;
    var PART2_SUFFIX = (PARTS && PARTS[1] && PARTS[1].titleSuffix) || '';

    /* ── Wiring ──────────────────────────────────────────────────
       Every live value is written through [data-chat] rather than an id,
       because the badge, the time-left line and the message each exist
       TWICE — in the right wing and in the narrow-screen band — and only
       one of the two is on screen at a given width. One selector, both
       copies, no branch on layout. */
    function all(hook) { return [].slice.call(document.querySelectorAll('[data-chat="' + hook + '"]')); }
    function setText(hook, text) { all(hook).forEach(function (el) { el.textContent = text; }); }

    /* Four messages, not two. The brief's two describe the film running
       (muted) and the film finished (open); the host's override makes two
       more states real. Say either of the first two in the wrong state and
       the screen tells the room something untrue — "The video has ended"
       over a film that is still playing is the exact failure this display
       exists to prevent. The noun is per page: a ninety-second reading is a
       "short video", the Creation film is not. */
    var NOUN = CFG.micNoun || 'short video';
    var MSG_MUTED = 'All visitor mics are turned off while this ' + NOUN + ' plays. Mics will be turned on at the end for Q/A + discussion.';
    var MSG_OPEN = 'The video has ended. Mics are on for Q/A + discussion.';
    // At the Part 1 break the film has NOT ended — four minutes of prayer are
    // one click away — so the break gets its own open message.
    var MSG_OPEN_PART = 'Part 1 has ended. Mics are on for Q/A + discussion.';
    var MSG_OPEN_EARLY = 'Mics are on early, while the film is still playing. Questions and discussion are welcome.';
    var MSG_MUTED_AFTER = 'Visitor mics are off for the moment. They will be back on shortly.';

    var MSG_MUTED_SHORT = 'Mics open at the end for Q/A.';
    var MSG_OPEN_SHORT = 'Mics are on for Q/A + discussion.';
    var MSG_OPEN_PART_SHORT = 'Part 1 done. Mics are on for Q/A.';
    var MSG_OPEN_EARLY_SHORT = 'Mics on — the film is still playing.';
    var MSG_MUTED_AFTER_SHORT = 'Mics are off for the moment.';

    /* ── Session state ───────────────────────────────────────────
       `override` is the host's thumb on the scale: null means follow the
       film, true/false force open/muted. Keeping it separate from the
       film's own state is what lets a third press of M return to
       following the film rather than latching on the last choice. */
    var player = null;
    var override = null;
    var ended = false;          // the real end of the video
    var partEnded = false;      // stopped at the Part 1 break
    var started = false;
    var pollTimer = null;
    var gateTimer = null;

    /* Part-gate state. `armed` is what makes seeking past the break by hand
       harmless: once the gate has fired it stays disarmed until the viewer is
       back before the break, so the film never stops the room twice.
       `countingFull` is what "Continue to the prayer" turns on — from there
       the clock runs to the real end, not to the break. */
    var mode = 'part1';
    var armed = true;
    var countingFull = false;

    var MODE_KEY = 'wop-chat-mode:' + window.location.pathname;
    var FOCUS_KEY = 'wop-chat-focus:' + window.location.pathname;

    if (HAS_PARTS) {
        try {
            var saved = window.sessionStorage.getItem(MODE_KEY);
            if (saved === 'full' || saved === 'part1') { mode = saved; }
        } catch (_) {}
    } else {
        mode = 'full';
    }

    function atEnd() { return ended || partEnded; }
    function micIsOpen() { return override === null ? atEnd() : override; }

    function duration() {
        try { return (player && player.getDuration) ? (player.getDuration() || 0) : 0; }
        catch (_) { return 0; }
    }
    function current() {
        try { return (player && player.getCurrentTime) ? (player.getCurrentTime() || 0) : 0; }
        catch (_) { return 0; }
    }

    /* The clock the room is being shown. In Part 1 mode it runs to the break,
       so "About 3 min left" means three minutes until the discussion — not
       until a prayer the host was never going to play. */
    function effectiveEnd() {
        if (HAS_PARTS && mode === 'part1' && !countingFull) { return PART1_END; }
        return duration();
    }

    function mmss(s) {
        s = Math.max(0, Math.round(s));
        return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }

    /* The time-left line is what a latecomer reads to decide whether to wait
       quietly or unmute, so it has to say something true in every state —
       including before the film starts, at the part break, and after the end. */
    function timeLeftText() {
        if (ended) { return 'Film has ended'; }
        if (partEnded) { return 'Part 1 has ended'; }
        if (!started) { return 'Starting shortly'; }

        var end = effectiveEnd();
        var left = end > 0 ? Math.max(0, end - current()) : 0;

        // Mics opened early: the room can hear itself, so the line has to say
        // the film is still running, and exactly how much of it is left.
        if (override === true) {
            return end > 0 ? ('Mics opened early · ' + mmss(left) + ' left') : 'Mics opened early';
        }
        if (end <= 0) { return 'Starting shortly'; }
        if (left < 60) { return 'Under a minute left · ' + Math.ceil(left) + 's'; }
        return 'About ' + Math.max(1, Math.round(left / 60)) + ' min left';
    }

    function messageLong(open) {
        if (open) {
            if (ended) { return MSG_OPEN; }
            return partEnded ? MSG_OPEN_PART : MSG_OPEN_EARLY;
        }
        return atEnd() ? MSG_MUTED_AFTER : MSG_MUTED;
    }
    function messageShort(open) {
        if (open) {
            if (ended) { return MSG_OPEN_SHORT; }
            return partEnded ? MSG_OPEN_PART_SHORT : MSG_OPEN_EARLY_SHORT;
        }
        return atEnd() ? MSG_MUTED_AFTER_SHORT : MSG_MUTED_SHORT;
    }

    function titleText() {
        return (countingFull && PART2_SUFFIX) ? (TITLE + ' · ' + PART2_SUFFIX) : TITLE;
    }

    function render() {
        var open = micIsOpen();

        all('mic').forEach(function (el) { el.setAttribute('data-state', open ? 'open' : 'muted'); });
        setText('mic-text', open ? 'Mics open' : 'Visitor mics off');
        setText('message', messageLong(open));
        setText('message-short', messageShort(open));
        setText('timeleft', timeLeftText());
        setText('title', titleText());

        if (HAS_PARTS) {
            setText('mode', mode === 'part1' ? '⇄ Part 1 only' : '⇄ Full film');
            all('mode').forEach(function (el) {
                el.setAttribute('aria-label', mode === 'part1' ? 'Switch to the full film' : 'Switch to Part 1 only');
            });
        }

        var end = effectiveEnd();
        var pct = end > 0 ? Math.min(100, Math.max(0, (current() / end) * 100)) : 0;
        if (atEnd()) { pct = 100; }
        all('meter').forEach(function (el) { el.style.width = pct.toFixed(2) + '%'; });
    }

    /* 250 ms while playing, per the brief: fast enough that the last-minute
       countdown ticks visibly, slow enough to be free. Stopped whenever the
       film is not running, so a paused room is not polling forever. */
    function startPoll() {
        if (!pollTimer) { pollTimer = window.setInterval(render, 250); }
        startGate();
        render();
    }
    function stopPoll() {
        if (pollTimer) { window.clearInterval(pollTimer); pollTimer = null; }
        stopGate();
        render();
    }

    /* The gate runs on its own, faster interval. At 250 ms the pause could
       land a quarter-second past the break, and the room would hear the first
       words of the prayer before the screen stopped. */
    function startGate() {
        if (!HAS_PARTS || gateTimer) { return; }
        gateTimer = window.setInterval(checkGate, 50);
    }
    function stopGate() {
        if (gateTimer) { window.clearInterval(gateTimer); gateTimer = null; }
    }

    function checkGate() {
        if (!HAS_PARTS || mode !== 'part1') { return; }
        var t = current();

        // Back before the break — by a hand seek, or by "Watch Part 1 again".
        // Re-arm, and put the clock back on Part 1.
        if (t < PART1_END - 0.05) {
            armed = true;
            if (countingFull) { countingFull = false; }
            if (partEnded) { partEnded = false; hidePartEnd(); }
            return;
        }
        if (countingFull || !armed || partEnded) { return; }
        if (t >= PART1_END) { firePartEnd(); }
    }

    function firePartEnd() {
        armed = false;
        partEnded = true;
        // Pause first, then land exactly on the break: pauseVideo on its own
        // leaves the clock wherever the poll happened to catch it.
        try { player.pauseVideo(); } catch (_) {}
        try { player.seekTo(PART1_END, true); } catch (_) {}
        stopGate();
        showPartEnd();
        render();
    }

    /* ── The part-end overlay ────────────────────────────────────── */
    var partEndEl = document.getElementById('chatPartEnd');
    function showPartEnd() {
        if (!partEndEl) { return; }
        partEndEl.classList.add('creation-ended--show');
        partEndEl.setAttribute('aria-hidden', 'false');
    }
    function hidePartEnd() {
        if (!partEndEl) { return; }
        partEndEl.classList.remove('creation-ended--show');
        partEndEl.setAttribute('aria-hidden', 'true');
    }

    all('part-again').forEach(function (b) {
        b.addEventListener('click', function () {
            hidePartEnd();
            partEnded = false;
            armed = true;
            countingFull = false;
            override = null;            // a fresh showing is a fresh stretch of quiet
            try { player.seekTo(0, true); player.playVideo(); } catch (_) {}
            render();
        });
    });

    all('part-continue').forEach(function (b) {
        b.addEventListener('click', function () {
            hidePartEnd();
            partEnded = false;
            armed = false;              // already past the break; do not stop again
            countingFull = true;        // the clock runs to the real end now
            override = null;            // and the room goes quiet again for the prayer
            try { player.seekTo(PART1_END, true); player.playVideo(); } catch (_) {}
            render();
        });
    });

    /* ── Mode ────────────────────────────────────────────────────── */
    all('mode').forEach(function (b) {
        b.addEventListener('click', function () {
            setMode(mode === 'part1' ? 'full' : 'part1');
        });
    });

    function setMode(m) {
        mode = m;
        try { window.sessionStorage.setItem(MODE_KEY, m); } catch (_) {}
        if (m === 'full') {
            armed = false;
            if (partEnded) { partEnded = false; hidePartEnd(); }
        } else {
            // Switching back mid-prayer must not rewind the room: the gate only
            // re-arms if the film is actually still inside Part 1.
            armed = current() < PART1_END;
            countingFull = !armed;
        }
        if (pollTimer) { startGate(); }
        render();
    }

    /* ── YouTube captions ────────────────────────────────────────
       These films carry their words burned into the picture. YouTube's own
       caption layer prints them a second time, a few frames out of step, over
       the top — which on a projector reads as a fault. Off here. The reading
       pages (js/aoid-video.js) now do this themselves; it stays here because
       /chat/video-03/ runs on js/creation.js, which keeps its uploaded track on
       the public /creation/ page. Unloading twice is harmless. */
    function killCaptions() {
        if (!player) { return; }
        try { player.unloadModule('captions'); } catch (_) {}
        try { player.unloadModule('cc'); } catch (_) {}
    }

    /* ── The film ────────────────────────────────────────────────── */
    window.addEventListener('wop:player', function (e) {
        player = (e.detail && e.detail.player) || null;
        killCaptions();
        render();
    });

    window.addEventListener('wop:state', function (e) {
        var s = e.detail ? e.detail.state : null;
        var YTS = window.YT && window.YT.PlayerState;
        if (!YTS) { return; }

        if (s === YTS.PLAYING) {
            started = true;
            // Replay after the end: the film is running again, so the mics
            // follow it back to muted unless the host is holding them open.
            ended = false;
            killCaptions();     // the module reloads itself on some transitions
            startPoll();
        } else if (s === YTS.ENDED) {
            ended = true;
            partEnded = false;
            hidePartEnd();
            stopPoll();
        } else {
            if (s === YTS.PAUSED) { stopPoll(); } else { render(); }
        }
    });

    /* "Watch again" resets the session to muted: a new showing of the film is
       a new stretch of quiet, whatever the host did during the last one. */
    var replay = document.getElementById('aoidReplay') || document.getElementById('creationReplay');
    if (replay) {
        replay.addEventListener('click', function () {
            override = null;
            ended = false;
            partEnded = false;
            countingFull = false;
            armed = HAS_PARTS;
            started = true;
            hidePartEnd();
            render();
        });
    }

    /* ── A3 · Correction channel on the film page ────────────────
       The reading pages build this into their own dock renderer. The creation
       layout cannot: its dock is creation.js, which stays as it is. So
       creation.js says WHAT it just painted, through 'wop:dock', and the link
       is appended from out here. Citations only — a pending scaffold span
       makes no claim about anyone's tradition, so there is nothing there to
       correct, exactly as the reading pages leave their neutral state alone. */
    function esc(s) {
        return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function correctionHtml(spanId, spanText) {
        var base = (CFG.correctionUrl || '').trim();
        if (!base) { return ''; }

        var pageUrl = '';
        try { pageUrl = window.location.origin + window.location.pathname; } catch (_) {}

        var quoted = (spanText || '').replace(/\s+/g, ' ').trim()
            .replace(/^[“"]/, '').replace(/[”"]$/, '').trim();
        if (quoted.length > 240) { quoted = quoted.slice(0, 237) + '…'; }

        var subject = TITLE + ' ' + spanId + ' — possible misrepresentation';
        var message = TITLE + ', span ' + spanId + '\n' +
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

    window.addEventListener('wop:dock', function (e) {
        var d = e.detail || {};
        if (d.kind !== 'citation' || !d.el || !d.el.querySelector) { return; }
        var body = d.el.querySelector('.ap-body');
        if (!body || body.querySelector('.aoid-correction-link')) { return; }
        var quoted = body.querySelector('.ap-span-text');
        var html = correctionHtml(d.spanId, quoted ? quoted.textContent : '');
        if (html) { body.insertAdjacentHTML('beforeend', html); }
    });

    /* ── Focus view ──────────────────────────────────────────────
       Not browser fullscreen and not YouTube's: a class on <html> and CSS
       does the rest. That matters more than it sounds — the player element
       is never moved in the DOM, because re-parenting an iframe reloads it
       and would restart the film in front of the room.

       The transcript stays in the layout (visibility, not display), so the
       host page's own follow code keeps measuring real rectangles while it
       is invisible. That is why the transcript is already on the current
       sentence when the host comes back, instead of jumping there. */
    function focusOn() { return root.classList.contains('chat-focus'); }

    function setFocus(on) {
        root.classList.toggle('chat-focus', !!on);
        try { window.sessionStorage.setItem(FOCUS_KEY, on ? '1' : '0'); } catch (_) {}
    }

    all('focus').forEach(function (b) {
        b.addEventListener('click', function () { setFocus(true); });
    });
    all('focus-exit').forEach(function (b) {
        b.addEventListener('click', function () { setFocus(false); });
    });

    try {
        if (window.sessionStorage.getItem(FOCUS_KEY) === '1') { root.classList.add('chat-focus'); }
    } catch (_) {}

    /* ── Host keys ───────────────────────────────────────────────── */
    function typing(el) {
        if (!el) { return false; }
        var t = (el.tagName || '').toLowerCase();
        return t === 'input' || t === 'textarea' || t === 'select' || el.isContentEditable;
    }

    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey || e.metaKey || e.altKey) { return; }
        if (typing(e.target)) { return; }
        var k = (e.key || '').toLowerCase();

        if (k === 'm') {
            e.preventDefault();
            // Follow → overridden to the opposite of what the film wants →
            // follow again. Two presses always get back to automatic.
            override = (override === null) ? !atEnd() : null;
            render();
        } else if (k === 'f') {
            e.preventDefault();
            setFocus(!focusOn());
        }
    });

    render();
}());
