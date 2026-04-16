/* ============================================================
   READ ALOUD — "How This Page Works" section on /narrations/

   Hybrid playback (mirrors card-chapter Read Aloud pattern):
     1. Pre-generated ElevenLabs audio from R2 CDN
        URL: https://media.wordsofplainness.org/web/RA_narrations_how_it_works.mp3
        A HEAD request confirms availability before playback.
     2. Browser Web Speech API fallback if CDN audio is 404/unreachable.

   Button injects into .narration-how-it-works as a floated pill in the
   top-right corner of the section. Pauses the chapter narration player
   (<audio id="narrationAudio">) on start so the two audio sources don't
   compete.
   ============================================================ */

(function () {
    'use strict';

    var CDN_URL = 'https://media.wordsofplainness.org/web/RA_narrations_how_it_works.mp3';

    var section = document.querySelector('.narration-how-it-works');
    if (!section) return;

    var hasSpeechSynthesis = 'speechSynthesis' in window;
    var synth = hasSpeechSynthesis ? window.speechSynthesis : null;

    // ── State ──
    var button = null;
    var activeAudio = null;     // HTMLAudioElement when CDN audio is playing
    var cdnAvailable = null;    // null = unknown, true/false = confirmed
    var isPlaying = false;

    // ── Voice selection (same priority list as card-chapter read-aloud) ──
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

    // ── CDN availability check (HEAD request) ──
    function checkCDN(callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('HEAD', CDN_URL, true);
        xhr.timeout = 4000;
        xhr.onload = function () { callback(xhr.status === 200); };
        xhr.onerror = function () { callback(false); };
        xhr.ontimeout = function () { callback(false); };
        try { xhr.send(); } catch (e) { callback(false); }
    }

    // ── Pause chapter narration player if it's playing ──
    function pauseChapterPlayer() {
        var chapterAudio = document.getElementById('narrationAudio');
        if (chapterAudio && !chapterAudio.paused) {
            chapterAudio.pause();
        }
    }

    // ── CDN playback ──
    function playCDN() {
        stopReading();
        pauseChapterPlayer();

        button.classList.add('loading');
        button.title = 'Loading\u2026';

        activeAudio = new Audio(CDN_URL);
        activeAudio.preload = 'auto';

        activeAudio.addEventListener('playing', function () {
            button.classList.remove('loading');
            button.classList.add('playing');
            button.setAttribute('aria-label', 'Stop reading');
            button.title = 'Stop';
            isPlaying = true;
        });
        activeAudio.addEventListener('ended', function () { stopReading(); });
        activeAudio.addEventListener('error', function () {
            console.warn('[NarrationsHowRA] CDN audio failed; falling back to browser TTS');
            stopReading();
            if (hasSpeechSynthesis) startTTS();
        });

        activeAudio.play().catch(function (err) {
            console.warn('[NarrationsHowRA] Audio play failed:', err);
            stopReading();
            if (hasSpeechSynthesis) startTTS();
        });
    }

    // ── Browser TTS playback with word highlighting ──
    function startTTS() {
        if (!synth) return;
        stopReading();
        pauseChapterPlayer();

        button.classList.add('playing');
        button.setAttribute('aria-label', 'Stop reading');
        button.title = 'Stop';

        wrapWords(section);
        var text = extractText(section);
        if (!text) { stopReading(); return; }

        var utterance = new SpeechSynthesisUtterance(text);
        if (preferredVoice) utterance.voice = preferredVoice;
        utterance.rate = 0.95;
        utterance.pitch = 1.0;

        var currentWordIdx = 0;
        utterance.addEventListener('boundary', function (e) {
            if (e.name !== 'word') return;
            var prev = section.querySelector('.narration-tts-word.narration-tts-highlight');
            if (prev) prev.classList.remove('narration-tts-highlight');
            var wordEl = section.querySelector('.narration-tts-word[data-word-idx="' + currentWordIdx + '"]');
            if (wordEl) {
                wordEl.classList.add('narration-tts-highlight');
                var rect = wordEl.getBoundingClientRect();
                if (rect.top < 80 || rect.bottom > window.innerHeight - 40) {
                    wordEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            currentWordIdx++;
        });
        utterance.addEventListener('end', function () { stopReading(); });
        utterance.addEventListener('error', function () { stopReading(); });

        isPlaying = true;
        synth.speak(utterance);
    }

    function stopReading() {
        if (activeAudio) {
            activeAudio.pause();
            activeAudio.removeAttribute('src');
            try { activeAudio.load(); } catch (e) {}
            activeAudio = null;
        }
        if (synth) synth.cancel();
        unwrapWords(section);
        if (button) {
            button.classList.remove('playing', 'loading');
            button.setAttribute('aria-label', 'Read aloud');
            button.title = 'Read Aloud';
        }
        isPlaying = false;
    }

    function togglePlay() {
        if (isPlaying) { stopReading(); return; }

        if (cdnAvailable === true) {
            playCDN();
        } else if (cdnAvailable === false) {
            if (hasSpeechSynthesis) startTTS();
        } else {
            // CDN check not yet complete — run it now, then route.
            button.classList.add('loading');
            checkCDN(function (ok) {
                cdnAvailable = ok;
                button.classList.remove('loading');
                if (ok) playCDN();
                else if (hasSpeechSynthesis) startTTS();
            });
        }
    }

    // ── Word wrapping (TTS highlighting only; wraps <p> contents) ──
    function wrapWords(container) {
        var paragraphs = container.querySelectorAll('p');
        var wordIndex = 0;
        paragraphs.forEach(function (p) {
            var walker = document.createTreeWalker(
                p,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function (node) {
                        if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
                        return NodeFilter.FILTER_ACCEPT;
                    }
                }
            );
            var textNodes = [];
            while (walker.nextNode()) textNodes.push(walker.currentNode);
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
                        span.className = 'narration-tts-word';
                        span.dataset.wordIdx = wordIndex++;
                        span.textContent = part;
                        frag.appendChild(span);
                    }
                });
                textNode.parentNode.replaceChild(frag, textNode);
            });
        });
        return wordIndex;
    }

    function unwrapWords(container) {
        var spans = container.querySelectorAll('.narration-tts-word');
        spans.forEach(function (span) {
            var text = document.createTextNode(span.textContent);
            span.parentNode.replaceChild(text, span);
        });
        container.normalize();
    }

    function extractText(container) {
        var parts = [];
        container.querySelectorAll('p').forEach(function (p) {
            parts.push(p.textContent.replace(/\s+/g, ' ').trim());
        });
        return parts.join(' ');
    }

    // ── Chrome 15-second pause bug workaround ──
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

    // ── Stop on navigation ──
    window.addEventListener('beforeunload', function () {
        if (synth) synth.cancel();
        if (activeAudio) { activeAudio.pause(); activeAudio = null; }
    });

    // ── Inject button ──
    function injectButton() {
        // Don't inject if neither pathway can work. CDN unknown yet, but
        // if speech synthesis exists we have a guaranteed fallback — inject.
        if (!hasSpeechSynthesis && cdnAvailable === false) return;

        button = document.createElement('button');
        button.className = 'narration-how-ra-btn';
        button.type = 'button';
        button.setAttribute('aria-label', 'Read aloud');
        button.title = 'Read Aloud';
        button.innerHTML =
            '<svg class="icon-play" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
                '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
                '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>' +
            '</svg>' +
            '<svg class="icon-stop" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<rect x="6" y="4" width="4" height="16"></rect>' +
                '<rect x="14" y="4" width="4" height="16"></rect>' +
            '</svg>' +
            '<span class="narration-how-ra-label">Read Aloud</span>';
        button.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            togglePlay();
        });

        // Insert as first child so float:right places it in top-right corner.
        section.insertBefore(button, section.firstChild);
    }

    // ── Init ──
    function init() {
        // Kick off the CDN check in the background; inject the button immediately.
        checkCDN(function (ok) { cdnAvailable = ok; });
        injectButton();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
