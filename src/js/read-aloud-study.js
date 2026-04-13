/* ============================================================
   READ ALOUD — Study Article Player
   
   Two modes:
   1. Pre-generated ElevenLabs audio → sticky player bar
   2. Browser Web Speech API fallback → per-section TTS
   
   Config via window.STUDY_AUDIO_CONFIG:
     { narrationUrl: '...', title: '...' }
   ============================================================ */

(function () {
    'use strict';

    var config = window.STUDY_AUDIO_CONFIG || {};
    var hasNarration = !!config.narrationUrl;
    var hasSpeechSynthesis = 'speechSynthesis' in window;
    var synth = hasSpeechSynthesis ? window.speechSynthesis : null;

    // Shared state
    var activeTtsBtn = null;
    var activeTtsSection = null;

    // ================================================================
    // MODE 1: Pre-generated Audio Player
    // ================================================================

    if (hasNarration) {
        initAudioPlayer();
    } else if (hasSpeechSynthesis) {
        initTtsButtons();
    }

    // ── Audio Player ────────────────────────────────────────

    function initAudioPlayer() {
        var audio = new Audio();
        audio.preload = 'metadata';
        audio.src = config.narrationUrl;

        var speeds = [0.75, 1, 1.25, 1.5];
        var currentSpeedIdx = 1;

        // Inject trigger button into page header
        var pageHeader = document.querySelector('.page-header');
        if (!pageHeader) return;

        var trigger = document.createElement('button');
        trigger.className = 'study-read-aloud-trigger';
        trigger.type = 'button';
        trigger.setAttribute('aria-label', 'Read aloud');
        trigger.innerHTML =
            '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
                '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
                '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>' +
            '</svg>' +
            '<span>Read Aloud</span>';
        pageHeader.appendChild(trigger);

        // Build player bar
        var bar = document.createElement('div');
        bar.className = 'study-player-bar';
        bar.setAttribute('role', 'region');
        bar.setAttribute('aria-label', 'Audio player');
        bar.innerHTML =
            '<button class="study-player-play" type="button" aria-label="Play">' +
                '<svg class="icon-play" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none"><polygon points="6 3 20 12 6 21 6 3"/></svg>' +
                '<svg class="icon-pause" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" stroke="none"><rect x="5" y="3" width="5" height="18"/><rect x="14" y="3" width="5" height="18"/></svg>' +
            '</button>' +
            '<div class="study-player-progress-wrap">' +
                '<span class="study-player-title">' + escapeHtml(config.title || 'Study Article') + '</span>' +
                '<input type="range" class="study-player-seek" min="0" max="100" value="0" step="0.1" aria-label="Seek">' +
                '<div class="study-player-time"><span class="sp-current">0:00</span><span class="sp-duration">--:--</span></div>' +
            '</div>' +
            '<button class="study-player-speed" type="button" aria-label="Playback speed">1×</button>' +
            '<button class="study-player-close" type="button" aria-label="Close player">' +
                '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            '</button>';

        document.body.appendChild(bar);

        // References
        var playBtn = bar.querySelector('.study-player-play');
        var seekBar = bar.querySelector('.study-player-seek');
        var curTime = bar.querySelector('.sp-current');
        var durTime = bar.querySelector('.sp-duration');
        var speedBtn = bar.querySelector('.study-player-speed');
        var closeBtn = bar.querySelector('.study-player-close');
        var isOpen = false;
        var isSeeking = false;

        function showBar() {
            bar.classList.add('visible');
            isOpen = true;
            trigger.innerHTML =
                '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<rect x="6" y="4" width="4" height="16"></rect>' +
                    '<rect x="14" y="4" width="4" height="16"></rect>' +
                '</svg>' +
                '<span>Listening</span>';
        }

        function hideBar() {
            audio.pause();
            bar.classList.remove('visible', 'playing');
            isOpen = false;
            trigger.innerHTML =
                '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
                    '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
                    '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>' +
                '</svg>' +
                '<span>Read Aloud</span>';
        }

        function formatTime(s) {
            if (!isFinite(s)) return '--:--';
            var m = Math.floor(s / 60);
            var sec = Math.floor(s % 60);
            return m + ':' + (sec < 10 ? '0' : '') + sec;
        }

        // Trigger button
        trigger.addEventListener('click', function () {
            if (!isOpen) {
                showBar();
                audio.play().catch(function () {});
            } else {
                hideBar();
            }
        });

        // Play / pause
        playBtn.addEventListener('click', function () {
            if (audio.paused) {
                audio.play().catch(function () {});
            } else {
                audio.pause();
            }
        });

        // Audio events
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
        });
        audio.addEventListener('pause', function () {
            bar.classList.remove('playing');
        });
        audio.addEventListener('ended', function () {
            bar.classList.remove('playing');
            seekBar.value = 0;
            curTime.textContent = '0:00';
        });

        // Seek bar
        seekBar.addEventListener('input', function () {
            isSeeking = true;
            curTime.textContent = formatTime(Number(seekBar.value));
        });
        seekBar.addEventListener('change', function () {
            audio.currentTime = Number(seekBar.value);
            isSeeking = false;
        });

        // Speed
        speedBtn.addEventListener('click', function () {
            currentSpeedIdx = (currentSpeedIdx + 1) % speeds.length;
            audio.playbackRate = speeds[currentSpeedIdx];
            speedBtn.textContent = speeds[currentSpeedIdx] + '\u00d7';
        });

        // Close
        closeBtn.addEventListener('click', function () {
            hideBar();
        });

        // Cleanup on unload
        window.addEventListener('beforeunload', function () {
            audio.pause();
        });

        // ALSO inject per-section TTS buttons as secondary option
        if (hasSpeechSynthesis) {
            initTtsButtons();
        }
    }

    // ================================================================
    // MODE 2: Browser TTS (per-section)
    // ================================================================

    // Voice selection (same priority list as card-chapter)
    var preferredVoice = null;
    function pickVoice() {
        if (!synth) return null;
        var voices = synth.getVoices();
        if (!voices.length) return null;
        var priorities = [
            function (v) { return v.lang.startsWith('en') && v.name.indexOf('Samantha') !== -1; },
            function (v) { return v.lang.startsWith('en') && v.name.indexOf('Daniel') !== -1; },
            function (v) { return v.lang.startsWith('en') && v.name.indexOf('Google US English') !== -1; },
            function (v) { return v.lang.startsWith('en') && v.name.indexOf('Google UK English') !== -1; },
            function (v) { return v.lang.startsWith('en') && v.name.indexOf('Microsoft') !== -1 && v.name.indexOf('Online') !== -1; },
            function (v) { return v.lang.startsWith('en'); }
        ];
        for (var i = 0; i < priorities.length; i++) {
            for (var j = 0; j < voices.length; j++) {
                if (priorities[i](voices[j])) return voices[j];
            }
        }
        return voices[0];
    }
    if (synth) {
        if (synth.getVoices().length) preferredVoice = pickVoice();
        synth.addEventListener('voiceschanged', function () { preferredVoice = pickVoice(); });
    }

    function initTtsButtons() {
        var sections = document.querySelectorAll('.content-section .content-wrapper');
        if (!sections.length) return;

        sections.forEach(function (wrapper) {
            if (wrapper.querySelector('.study-tts-btn')) return;

            var btn = document.createElement('button');
            btn.className = 'study-tts-btn';
            btn.type = 'button';
            btn.setAttribute('aria-label', 'Read this section aloud');
            btn.title = 'Read Aloud';
            btn.innerHTML =
                '<svg class="icon-play" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
                    '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
                '</svg>' +
                '<svg class="icon-stop" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<rect x="6" y="4" width="4" height="16"></rect>' +
                    '<rect x="14" y="4" width="4" height="16"></rect>' +
                '</svg>' +
                '<span class="study-tts-label">Read Aloud</span>';

            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var section = wrapper.closest('.content-section') || wrapper;
                handleTts(btn, section, wrapper);
            });

            // Insert after the section heading if present, else at top
            var heading = wrapper.querySelector('.study-section-heading');
            if (heading && heading.nextSibling) {
                heading.parentNode.insertBefore(btn, heading.nextSibling);
            } else {
                wrapper.insertBefore(btn, wrapper.firstChild);
            }
        });
    }

    function handleTts(btn, section, wrapper) {
        if (activeTtsBtn === btn) {
            stopTts();
            return;
        }
        stopTts();

        activeTtsBtn = btn;
        activeTtsSection = section;
        section.classList.add('study-tts-active');
        btn.classList.add('playing');
        btn.setAttribute('aria-label', 'Stop reading');
        btn.title = 'Stop';

        var totalWords = wrapWords(wrapper);
        var text = extractText(wrapper);
        if (!text) { stopTts(); return; }

        var utterance = new SpeechSynthesisUtterance(text);
        if (preferredVoice) utterance.voice = preferredVoice;
        utterance.rate = 0.95;
        utterance.pitch = 1.0;

        var currentWordIdx = 0;
        utterance.addEventListener('boundary', function (e) {
            if (e.name !== 'word') return;
            var prev = wrapper.querySelector('.study-tts-word.study-tts-highlight');
            if (prev) prev.classList.remove('study-tts-highlight');

            var wordEl = wrapper.querySelector('.study-tts-word[data-word-idx="' + currentWordIdx + '"]');
            if (wordEl) {
                wordEl.classList.add('study-tts-highlight');
                var rect = wordEl.getBoundingClientRect();
                if (rect.top < 80 || rect.bottom > window.innerHeight - 40) {
                    wordEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            currentWordIdx++;
        });

        utterance.addEventListener('end', function () { stopTts(); });
        utterance.addEventListener('error', function () { stopTts(); });

        synth.speak(utterance);
    }

    function stopTts() {
        if (synth) synth.cancel();
        if (activeTtsSection) {
            activeTtsSection.classList.remove('study-tts-active');
            var wrapper = activeTtsSection.querySelector('.content-wrapper');
            if (wrapper) unwrapWords(wrapper);
            activeTtsSection = null;
        }
        if (activeTtsBtn) {
            activeTtsBtn.classList.remove('playing');
            activeTtsBtn.setAttribute('aria-label', 'Read this section aloud');
            activeTtsBtn.title = 'Read Aloud';
            activeTtsBtn = null;
        }
    }

    // ── Word Wrapping for TTS Highlighting ──────────────────

    function wrapWords(container) {
        var walker = document.createTreeWalker(
            container,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function (node) {
                    var parent = node.parentElement;
                    if (!parent) return NodeFilter.FILTER_REJECT;
                    if (parent.closest('.study-tts-btn')) return NodeFilter.FILTER_REJECT;
                    if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );
        var textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);

        var wordIndex = 0;
        textNodes.forEach(function (textNode) {
            var text = textNode.textContent;
            var parts = text.split(/(\s+)/);
            if (parts.length <= 1 && !text.trim()) return;

            var frag = document.createDocumentFragment();
            parts.forEach(function (part) {
                if (!part) return;
                if (/^\s+$/.test(part)) {
                    frag.appendChild(document.createTextNode(part));
                } else {
                    var span = document.createElement('span');
                    span.className = 'study-tts-word';
                    span.dataset.wordIdx = wordIndex++;
                    span.textContent = part;
                    frag.appendChild(span);
                }
            });
            textNode.parentNode.replaceChild(frag, textNode);
        });
        return wordIndex;
    }

    function unwrapWords(container) {
        var spans = container.querySelectorAll('.study-tts-word');
        spans.forEach(function (span) {
            var text = document.createTextNode(span.textContent);
            span.parentNode.replaceChild(text, span);
        });
        container.normalize();
    }

    function extractText(container) {
        var clone = container.cloneNode(true);
        var btns = clone.querySelectorAll('.study-tts-btn');
        for (var i = 0; i < btns.length; i++) btns[i].remove();
        return clone.textContent.replace(/\s+/g, ' ').trim();
    }

    // ── Chrome Bug Workaround ───────────────────────────────

    if (synth) {
        var chromePauseTimer = null;
        var origSpeak = synth.speak.bind(synth);
        synth.speak = function (utterance) {
            if (chromePauseTimer) clearInterval(chromePauseTimer);
            chromePauseTimer = setInterval(function () {
                if (synth.speaking && !synth.paused) {
                    synth.pause();
                    synth.resume();
                }
            }, 10000);
            utterance.addEventListener('end', function () {
                if (chromePauseTimer) { clearInterval(chromePauseTimer); chromePauseTimer = null; }
            });
            utterance.addEventListener('error', function () {
                if (chromePauseTimer) { clearInterval(chromePauseTimer); chromePauseTimer = null; }
            });
            origSpeak(utterance);
        };
    }

    // ── Utilities ───────────────────────────────────────────

    function escapeHtml(s) {
        var el = document.createElement('span');
        el.textContent = s;
        return el.innerHTML;
    }

    // Stop TTS on page navigation
    window.addEventListener('beforeunload', function () {
        if (synth) synth.cancel();
    });
})();
