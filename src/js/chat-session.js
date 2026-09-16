/* ============================================================
   chat-session.js — /chat/video-NN/ only.

   The chat pages are the reading pages (or /creation/) shown to a room:
   in VR, or on a projector at an in-person group. Visitor mics are off
   while a film plays and open afterwards for questions, and people
   arrive all evening — so the SCREEN has to answer "why can't I talk?"
   without anyone having to ask it.

   This script owns the wings, the mic state, focus view and the host
   keys. It owns nothing else. It never reaches inside aoid-video.js or
   creation.js: those two dispatch 'wop:player' and 'wop:state', and
   those two events are the whole interface. So the public pages carry
   none of this, and the follow / dock / worship-gate behaviour the
   chat pages inherit is the same code, not a second copy.

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

    /* ── Wiring ──────────────────────────────────────────────────
       Every live value is written through [data-chat] rather than an id,
       because the badge, the time-left line and the message each exist
       TWICE — in the right wing and in the narrow-screen band — and only
       one of the two is on screen at a given width. One selector, both
       copies, no branch on layout. */
    function all(hook) { return [].slice.call(document.querySelectorAll('[data-chat="' + hook + '"]')); }
    function setText(hook, text) { all(hook).forEach(function (el) { el.textContent = text; }); }

    /* Four messages, not two, because the host's override makes two more states
       real. The brief's two describe the film running (muted) and the film
       finished (open) — say either one in the wrong state and the screen tells
       the room something untrue: "The video has ended" over a film that is
       still playing is the exact failure this display exists to prevent. */
    var MSG_MUTED = 'All visitor mics are turned off while this short video plays. Mics will be turned on at the end for Q/A + discussion.';
    var MSG_OPEN = 'The video has ended. Mics are on for Q/A + discussion.';
    var MSG_OPEN_EARLY = 'Mics are on early, while the film is still playing. Questions and discussion are welcome.';
    var MSG_MUTED_AFTER = 'Visitor mics are off for the moment. They will be back on shortly.';

    var MSG_MUTED_SHORT = 'Mics open at the end for Q/A.';
    var MSG_OPEN_SHORT = 'Mics are on for Q/A + discussion.';
    var MSG_OPEN_EARLY_SHORT = 'Mics on — the film is still playing.';
    var MSG_MUTED_AFTER_SHORT = 'Mics are off for the moment.';

    function messageLong(open) {
        if (open) { return ended ? MSG_OPEN : MSG_OPEN_EARLY; }
        return ended ? MSG_MUTED_AFTER : MSG_MUTED;
    }
    function messageShort(open) {
        if (open) { return ended ? MSG_OPEN_SHORT : MSG_OPEN_EARLY_SHORT; }
        return ended ? MSG_MUTED_AFTER_SHORT : MSG_MUTED_SHORT;
    }

    /* ── Session state ───────────────────────────────────────────
       `override` is the host's thumb on the scale: null means follow the
       film, true/false force open/muted. Keeping it separate from `ended`
       is what lets a third press of M return to following the film
       rather than latching on the last thing the host chose. */
    var player = null;
    var override = null;
    var ended = false;
    var started = false;
    var pollTimer = null;

    function micIsOpen() { return override === null ? ended : override; }

    function duration() {
        try { return (player && player.getDuration) ? (player.getDuration() || 0) : 0; }
        catch (_) { return 0; }
    }
    function current() {
        try { return (player && player.getCurrentTime) ? (player.getCurrentTime() || 0) : 0; }
        catch (_) { return 0; }
    }

    function mmss(s) {
        s = Math.max(0, Math.round(s));
        return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }

    /* The time-left line is the one piece of text a latecomer reads to decide
       whether to wait quietly or unmute. It therefore says something true in
       every state, including before the film has started and after it ends. */
    function timeLeftText() {
        if (ended) { return 'Film has ended'; }
        if (!started) { return 'Starting shortly'; }

        var dur = duration();
        var left = dur > 0 ? Math.max(0, dur - current()) : 0;

        // Mics opened early: the room can hear itself, so the line has to say
        // the film is still running, and exactly how much of it is left.
        if (override === true) {
            return dur > 0 ? ('Mics opened early · ' + mmss(left) + ' left') : 'Mics opened early';
        }
        if (dur <= 0) { return 'Starting shortly'; }
        if (left < 60) { return 'Under a minute left · ' + Math.ceil(left) + 's'; }
        return 'About ' + Math.max(1, Math.round(left / 60)) + ' min left';
    }

    function render() {
        var open = micIsOpen();

        all('mic').forEach(function (el) { el.setAttribute('data-state', open ? 'open' : 'muted'); });
        setText('mic-text', open ? 'Mics open' : 'Visitor mics off');
        setText('message', messageLong(open));
        setText('message-short', messageShort(open));
        setText('timeleft', timeLeftText());

        var dur = duration();
        var pct = dur > 0 ? Math.min(100, Math.max(0, (current() / dur) * 100)) : 0;
        if (ended) { pct = 100; }
        all('meter').forEach(function (el) { el.style.width = pct.toFixed(2) + '%'; });
    }

    /* 250 ms while playing, per the brief: fast enough that the last-minute
       countdown ticks visibly, slow enough to be free. Stopped whenever the
       film is not running, so a paused room is not polling forever. */
    function startPoll() {
        if (!pollTimer) { pollTimer = window.setInterval(render, 250); }
        render();
    }
    function stopPoll() {
        if (pollTimer) { window.clearInterval(pollTimer); pollTimer = null; }
        render();
    }

    /* ── The film ────────────────────────────────────────────────── */
    window.addEventListener('wop:player', function (e) {
        player = (e.detail && e.detail.player) || null;
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
            startPoll();
        } else if (s === YTS.ENDED) {
            ended = true;
            stopPoll();
        } else {
            // PAUSED / BUFFERING / CUED: keep the numbers current but stop
            // the clock, since nothing is advancing.
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
            started = true;
            render();
        });
    }

    /* ── Focus view ──────────────────────────────────────────────
       Not browser fullscreen and not YouTube's: a class on <html> and CSS
       does the rest. That matters more than it sounds — the player element
       is never moved in the DOM, because re-parenting an iframe reloads it
       and would restart the film in front of the room.

       The transcript stays in the layout (visibility, not display), so the
       host page's own follow code keeps measuring real rectangles while it
       is invisible. That is why the transcript is already on the current
       sentence when the host comes back, instead of jumping there. */
    var FOCUS_KEY = 'wop-chat-focus:' + window.location.pathname;

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
            override = (override === null) ? !ended : null;
            render();
        } else if (k === 'f') {
            e.preventDefault();
            setFocus(!focusOn());
        }
    });

    render();
}());
