/**
 * WORDS OF PLAINNESS - Anthem Player
 * ====================================
 * 
 * Homepage anthem player for "The Marks of Your Worth"
 * Handles play/pause with HTML5 Audio, waveform animation,
 * progress tracking, and lyrics dropdown toggle.
 * 
 * Follows the DOMContentLoaded pattern established in main.js.
 */

document.addEventListener('DOMContentLoaded', () => {
    const playArea = document.getElementById('anthemPlayArea');
    const playBtn = document.getElementById('anthemPlayBtn');
    const audio = document.getElementById('anthemAudio');
    const lyricsToggle = document.getElementById('anthemLyricsToggle');
    const lyricsBody = document.getElementById('anthemLyricsBody');
    const lyricsToggleText = document.getElementById('anthemLyricsToggleText');
    const currentTimeEl = document.getElementById('anthemTimeCurrent');
    const progressFill = document.getElementById('anthemProgressFill');

    if (!playArea || !playBtn || !audio) return;

    let animationFrames = [];

    const lyricsScroll = lyricsBody ? lyricsBody.querySelector('.anthem-lyrics-scroll') : null;
    const lineEls = lyricsBody ? Array.from(lyricsBody.querySelectorAll('.anthem-line')) : [];
    const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isDev = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
    const USER_SCROLL_PAUSE_MS = 4000;

    let cues = [];            // cues[i] pairs with lineEls[i]; null if unmatched
    let activeIdx = -1;
    let autoScrollResumeAt = 0;
    let programmaticScrollUntil = 0;

    // ── Format time as m:ss ──────────────────
    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    // ── Waveform animation ───────────────────
    function startWaveformAnimation() {
        const bars = playArea.querySelectorAll('.anthem-waveform-bars span');
        bars.forEach(bar => {
            const pulse = () => {
                if (audio.paused) return;
                bar.style.height = (18 + Math.random() * 82) + '%';
                bar.style.opacity = (0.35 + Math.random() * 0.65).toString();
                const timeout = setTimeout(pulse, 180 + Math.random() * 350);
                animationFrames.push(timeout);
            };
            pulse();
        });
    }

    function stopWaveformAnimation() {
        // Clear all pending timeouts
        animationFrames.forEach(id => clearTimeout(id));
        animationFrames = [];

        // Reset bars to CSS defaults
        const bars = playArea.querySelectorAll('.anthem-waveform-bars span');
        bars.forEach(bar => {
            bar.style.height = '';
            bar.style.opacity = '';
        });
    }

    // Listen-only flag: set when the visitor hides the panel by hand, cleared
    // when they open it by hand, honored by togglePlay(). In memory only (never
    // localStorage/sessionStorage/cookies), so a reload restores auto-open.
    let listenOnly = false;

    // ── Lyrics panel open / close ────────────
    function setLyricsOpen(open) {
        if (!lyricsToggle || !lyricsBody) return;
        lyricsToggle.classList.toggle('is-open', open);
        lyricsBody.classList.toggle('is-open', open);
        if (lyricsToggleText) lyricsToggleText.textContent = open ? 'Hide Lyrics' : 'View Lyrics';
    }

    // ── Lyrics sync (VTT cues -> .anthem-line) ─
    function normalize(t) {
        return String(t)
            .toLowerCase()
            .replace(/[‘’‛]/g, "'")
            .replace(/[“”]/g, '"')
            .replace(/[–—―-]/g, ' ')
            .replace(/…/g, '...')
            .replace(/[^a-z0-9\s]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function mapCues(track) {
        const list = track && track.cues ? Array.from(track.cues) : [];
        const mismatches = [];
        if (list.length !== lineEls.length) {
            mismatches.push('count: ' + list.length + ' cues vs ' + lineEls.length + ' lines');
        }
        cues = lineEls.map((el, i) => {
            const cue = list[i];
            if (!cue) { mismatches.push('line ' + (i + 1) + ' has no cue: "' + el.textContent.trim() + '"'); return null; }
            if (normalize(cue.text) !== normalize(el.textContent)) {
                mismatches.push('line ' + (i + 1) + ': "' + el.textContent.trim() + '" vs cue "' + cue.text + '"');
                return null;
            }
            return cue;
        });
        if (mismatches.length && isDev) console.warn('Anthem lyric/VTT mismatches:', mismatches);
    }

    function setupTrack() {
        if (!lyricsBody || !lineEls.length) return;
        const url = lyricsBody.dataset.vttUrl;
        if (!url) return;
        try {
            const el = document.createElement('track');
            el.kind = 'metadata';
            el.src = url;
            el.default = true;
            audio.appendChild(el);
            const track = el.track;
            if (!track) return;
            track.mode = 'hidden';
            el.addEventListener('load', () => {
                mapCues(track);
                track.addEventListener('cuechange', syncToTime);
                syncToTime();
            });
            el.addEventListener('error', () => { if (isDev) console.warn('Anthem VTT failed to load:', url); });
        } catch (err) {
            if (isDev) console.warn('Anthem lyric sync unavailable:', err);
        }
    }

    function indexForTime(t) {
        for (let i = 0; i < cues.length; i++) {
            const c = cues[i];
            if (c && t >= c.startTime && t < c.endTime) return i;
        }
        return -1;
    }

    function setActive(idx) {
        if (idx === activeIdx) return;
        if (activeIdx >= 0 && lineEls[activeIdx]) lineEls[activeIdx].classList.remove('is-active');
        activeIdx = idx;
        if (idx < 0) return;
        if (lyricsScroll) lyricsScroll.classList.add('is-syncing');
        lineEls[idx].classList.add('is-active');
        scrollToLine(lineEls[idx]);
    }

    function syncToTime() {
        if (!cues.length) return;
        setActive(indexForTime(audio.currentTime));
    }

    // Scroll only the lyrics container, never the page.
    function scrollToLine(el) {
        if (!lyricsScroll || !lyricsBody.classList.contains('is-open')) return;
        if (Date.now() < autoScrollResumeAt) return;
        const lineTop = el.getBoundingClientRect().top - lyricsScroll.getBoundingClientRect().top + lyricsScroll.scrollTop;
        const target = Math.max(0, lineTop - lyricsScroll.clientHeight / 3);
        programmaticScrollUntil = Date.now() + (reducedMotion ? 100 : 900);
        lyricsScroll.scrollTo({ top: target, behavior: reducedMotion ? 'auto' : 'smooth' });
    }

    let resumeTimer = null;
    function noteUserScroll() {
        autoScrollResumeAt = Date.now() + USER_SCROLL_PAUSE_MS;
        clearTimeout(resumeTimer);
        resumeTimer = setTimeout(() => {
            if (!audio.paused && activeIdx >= 0) scrollToLine(lineEls[activeIdx]);
        }, USER_SCROLL_PAUSE_MS + 50);
    }

    if (lyricsScroll) {
        ['wheel', 'touchstart', 'touchmove', 'pointerdown'].forEach(evt =>
            lyricsScroll.addEventListener(evt, noteUserScroll, { passive: true }));
        // Scrollbar drag / keyboard scrolling: ignore scroll events we caused ourselves.
        lyricsScroll.addEventListener('scroll', () => {
            if (Date.now() > programmaticScrollUntil) noteUserScroll();
        }, { passive: true });
    }

    audio.addEventListener('seeked', () => {
        autoScrollResumeAt = 0; // a seek is an intentional jump; follow it
        syncToTime();
        if (activeIdx >= 0) scrollToLine(lineEls[activeIdx]);
    });

    setupTrack();

    // ── Play / Pause toggle ──────────────────
    function togglePlay() {
        if (audio.paused) {
            if (!listenOnly) setLyricsOpen(true);
            autoScrollResumeAt = 0;
            audio.play().then(() => {
                syncToTime();
                if (activeIdx >= 0) scrollToLine(lineEls[activeIdx]);
                playBtn.classList.add('is-playing');
                startWaveformAnimation();
            }).catch(err => {
                console.log('Anthem playback prevented:', err);
            });
        } else {
            audio.pause();
            playBtn.classList.remove('is-playing');
            stopWaveformAnimation();
        }
    }

    playArea.addEventListener('click', (e) => {
        // Don't trigger if clicking inside lyrics area
        if (e.target.closest('.anthem-lyrics-toggle') || e.target.closest('.anthem-lyrics-body')) return;
        togglePlay();
    });

    // ── Audio progress tracking ──────────────
    audio.addEventListener('timeupdate', () => {
        if (!audio.duration) return;
        const pct = (audio.currentTime / audio.duration) * 100;
        if (progressFill) progressFill.style.width = pct + '%';
        if (currentTimeEl) currentTimeEl.textContent = formatTime(audio.currentTime);
    });

    // ── Audio ended ──────────────────────────
    audio.addEventListener('ended', () => {
        playBtn.classList.remove('is-playing');
        stopWaveformAnimation();
        if (progressFill) progressFill.style.width = '0%';
        if (currentTimeEl) currentTimeEl.textContent = '0:00';
        setActive(-1);
        if (lyricsScroll) {
            lyricsScroll.classList.remove('is-syncing');
            lyricsScroll.scrollTo({ top: 0, behavior: 'auto' });
        }
    });

    // ── Lyrics dropdown toggle ───────────────
    if (lyricsToggle && lyricsBody) {
        lyricsToggle.addEventListener('click', (e) => {
            e.stopPropagation(); // prevent play area click
            const willOpen = !lyricsToggle.classList.contains('is-open');
            listenOnly = !willOpen;
            setLyricsOpen(willOpen);
            if (lyricsBody.classList.contains('is-open') && activeIdx >= 0) {
                autoScrollResumeAt = 0;
                scrollToLine(lineEls[activeIdx]);
            }
        });
    }
});

console.log('Words of Plainness - Anthem player loaded');
