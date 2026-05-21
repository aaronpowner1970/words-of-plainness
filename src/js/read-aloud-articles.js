/* ============================================================
   READ ALOUD — Articles of Interfaith Discipleship
   Per-article audio player using pre-generated ElevenLabs MP3s.

   - Injects a "Listen" trigger button into each .article-section
   - Shares one sticky player bar (reuses .study-player-bar CSS)
   - Swaps audio gracefully when switching articles
   - Triggered by data-audio="AP_A##_Slug.mp3" on each section
   ============================================================ */

(function () {
    'use strict';

    var CDN_BASE = 'https://media.wordsofplainness.org/web/';
    var speeds = [0.75, 1, 1.25, 1.5];
    var currentSpeedIdx = 1;

    var audio = null;
    var currentBtn = null;
    var isSeeking = false;

    // ── Build shared sticky player bar ──────────────────────

    var bar = document.createElement('div');
    bar.className = 'study-player-bar';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Article audio player');
    bar.innerHTML =
        '<button class="study-player-play" type="button" aria-label="Play">' +
            '<svg class="icon-play" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none">' +
                '<polygon points="6 3 20 12 6 21 6 3"/>' +
            '</svg>' +
            '<svg class="icon-pause" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none">' +
                '<rect x="5" y="3" width="5" height="18"/><rect x="14" y="3" width="5" height="18"/>' +
            '</svg>' +
        '</button>' +
        '<div class="study-player-progress-wrap">' +
            '<span class="study-player-title"></span>' +
            '<input type="range" class="study-player-seek" min="0" max="100" value="0" step="0.1" aria-label="Seek">' +
            '<div class="study-player-time">' +
                '<span class="sp-current">0:00</span>' +
                '<span class="sp-duration">--:--</span>' +
            '</div>' +
        '</div>' +
        '<button class="study-player-speed" type="button" aria-label="Playback speed">1×</button>' +
        '<button class="study-player-close" type="button" aria-label="Close player">' +
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">' +
                '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' +
            '</svg>' +
        '</button>';

    document.body.appendChild(bar);

    var playBtn  = bar.querySelector('.study-player-play');
    var seekBar  = bar.querySelector('.study-player-seek');
    var curTime  = bar.querySelector('.sp-current');
    var durTime  = bar.querySelector('.sp-duration');
    var speedBtn = bar.querySelector('.study-player-speed');
    var closeBtn = bar.querySelector('.study-player-close');
    var barTitle = bar.querySelector('.study-player-title');

    // ── Inject trigger buttons into each article ─────────────

    var sections = document.querySelectorAll('.article-section[data-audio]');

    sections.forEach(function (section) {
        var audioFile = section.dataset.audio;
        var titleEl   = section.querySelector('.article-title');
        var titleText = titleEl ? titleEl.textContent.trim() : 'Article';

        var btn = document.createElement('button');
        btn.className = 'article-read-aloud-btn';
        btn.type = 'button';
        btn.setAttribute('aria-label', 'Listen to ' + titleText);
        btn.dataset.audio = audioFile;
        btn.innerHTML =
            '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
                '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
                '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>' +
            '</svg>' +
            '<span class="ara-label">Listen</span>';

        // Insert: after h2.article-title, before .article-body
        if (titleEl) {
            var next = titleEl.nextElementSibling;
            if (next) {
                section.insertBefore(btn, next);
            } else {
                section.appendChild(btn);
            }
        }

        btn.addEventListener('click', function () {
            if (currentBtn === btn) {
                // Same article — toggle play/pause
                if (audio && !audio.paused) {
                    audio.pause();
                } else if (audio) {
                    audio.play().catch(function () {});
                    btn.querySelector('.ara-label').textContent = 'Listening\u2026';
                }
            } else {
                loadAndPlay(audioFile, titleText, btn);
            }
        });
    });

    // ── Load and play an article ──────────────────────────────

    function loadAndPlay(audioFile, title, btn) {
        // Deactivate previous
        if (currentBtn) {
            currentBtn.classList.remove('active');
            currentBtn.querySelector('.ara-label').textContent = 'Listen';
        }
        if (audio) {
            audio.pause();
            audio.src = '';
            audio.load();
        }

        // Create new Audio
        audio = new Audio(CDN_BASE + audioFile);
        audio.preload = 'metadata';
        audio.playbackRate = speeds[currentSpeedIdx];
        isSeeking = false;

        // Reset bar
        barTitle.textContent = title;
        seekBar.value = 0;
        curTime.textContent = '0:00';
        durTime.textContent = '--:--';
        bar.classList.remove('playing');
        bar.classList.add('visible');

        // Activate button
        currentBtn = btn;
        btn.classList.add('active');
        btn.querySelector('.ara-label').textContent = 'Listening\u2026';

        // Wire audio events
        audio.addEventListener('loadedmetadata', function () {
            seekBar.max = audio.duration;
            durTime.textContent = formatTime(audio.duration);
        });

        audio.addEventListener('timeupdate', function () {
            if (!isSeeking) {
                seekBar.value = audio.currentTime;
                curTime.textContent = formatTime(audio.currentTime);
            }
        });

        audio.addEventListener('play', function () {
            bar.classList.add('playing');
            if (currentBtn) currentBtn.classList.add('active');
        });

        audio.addEventListener('pause', function () {
            bar.classList.remove('playing');
            if (currentBtn) currentBtn.querySelector('.ara-label').textContent = 'Paused';
        });

        audio.addEventListener('ended', function () {
            bar.classList.remove('playing');
            seekBar.value = 0;
            curTime.textContent = '0:00';
            if (currentBtn) {
                currentBtn.classList.remove('active');
                currentBtn.querySelector('.ara-label').textContent = 'Listen';
                currentBtn = null;
            }
        });

        audio.play().catch(function () {});
    }

    // ── Bar controls ──────────────────────────────────────────

    playBtn.addEventListener('click', function () {
        if (!audio) return;
        if (audio.paused) {
            audio.play().catch(function () {});
            if (currentBtn) currentBtn.querySelector('.ara-label').textContent = 'Listening\u2026';
        } else {
            audio.pause();
        }
    });

    seekBar.addEventListener('mousedown',  function () { isSeeking = true; });
    seekBar.addEventListener('touchstart', function () { isSeeking = true; }, { passive: true });
    seekBar.addEventListener('input', function () {
        isSeeking = true;
        curTime.textContent = formatTime(Number(seekBar.value));
    });
    seekBar.addEventListener('change', function () {
        if (audio) audio.currentTime = Number(seekBar.value);
        isSeeking = false;
    });

    speedBtn.addEventListener('click', function () {
        currentSpeedIdx = (currentSpeedIdx + 1) % speeds.length;
        if (audio) audio.playbackRate = speeds[currentSpeedIdx];
        speedBtn.textContent = speeds[currentSpeedIdx] + '\u00d7';
    });

    closeBtn.addEventListener('click', function () {
        if (audio) { audio.pause(); audio.src = ''; audio.load(); }
        bar.classList.remove('visible', 'playing');
        if (currentBtn) {
            currentBtn.classList.remove('active');
            currentBtn.querySelector('.ara-label').textContent = 'Listen';
            currentBtn = null;
        }
    });

    window.addEventListener('beforeunload', function () {
        if (audio) audio.pause();
    });

    // ── Utilities ─────────────────────────────────────────────

    function formatTime(s) {
        if (!isFinite(s) || isNaN(s)) return '--:--';
        var m = Math.floor(s / 60);
        var sec = Math.floor(s % 60);
        return m + ':' + (sec < 10 ? '0' : '') + sec;
    }

})();
