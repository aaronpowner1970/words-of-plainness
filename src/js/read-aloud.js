/* ============================================================
   READ ALOUD — Hybrid TTS for Card-Chapter Tabs
   
   Priority:
   1. Pre-generated ElevenLabs audio + word-level highlighting
      (loaded from CDN manifest if available)
   2. Browser Web Speech API fallback with word highlighting
   
   Injected into card-chapter pages via card-chapter.njk layout.
   ============================================================ */

(function () {
    'use strict';

    // ---- Feature detection ----
    var hasSpeechSynthesis = 'speechSynthesis' in window;
    var synth = hasSpeechSynthesis ? window.speechSynthesis : null;

    var activeBtn = null;     // currently playing button
    var activePanel = null;   // panel being read
    var activeAudio = null;   // HTMLAudioElement for pre-generated audio
    var activeHighlightTimer = null;
    var manifest = null;      // pre-generated audio manifest (null = not loaded)
    var manifestLoaded = false;
    var CDN_BASE = 'https://media.wordsofplainness.org/web/';

    // ---- Load Manifest ----
    // Try to fetch the card-audio manifest for this chapter from CDN
    function loadManifest() {
        var chapterId = document.body.dataset.chapter || '';
        if (!chapterId) { manifestLoaded = true; return; }

        // chapterId is like "chapter-12-beatitudes" — extract slug
        var slug = chapterId.replace(/^chapter-/, '');
        var manifestUrl = CDN_BASE + 'card-audio-' + slug + '.json';

        var xhr = new XMLHttpRequest();
        xhr.open('GET', manifestUrl, true);
        xhr.timeout = 5000;
        xhr.onload = function () {
            if (xhr.status === 200) {
                try {
                    manifest = JSON.parse(xhr.responseText);
                    console.log('[ReadAloud] Pre-generated audio manifest loaded:', Object.keys(manifest.tabs).length, 'tabs');
                } catch (e) {
                    manifest = null;
                }
            }
            manifestLoaded = true;
        };
        xhr.onerror = function () { manifestLoaded = true; };
        xhr.ontimeout = function () { manifestLoaded = true; };
        xhr.send();
    }

    // ---- Get manifest entry for a panel ----
    function getManifestEntry(panel) {
        if (!manifest || !manifest.tabs) return null;

        // Intro section uses special key
        if (panel.classList.contains('cc-intro')) {
            return manifest.tabs['intro'] || null;
        }

        var cardNum = panel.getAttribute('data-card');
        var tabName = panel.getAttribute('data-panel');
        var key = 'card' + cardNum + '_' + tabName;
        return manifest.tabs[key] || null;
    }

    // ---- Pre-generated Audio Playback ----
    function playPreGenerated(btn, panel, entry) {
        stopReading();

        activeBtn = btn;
        activePanel = panel;
        panel.classList.add('cc-tts-active');
        btn.classList.add('playing');
        btn.setAttribute('aria-label', 'Stop reading');
        btn.title = 'Stop Reading';

        var words = entry.words || [];
        if (words.length > 0) {
            wrapWordsInPanel(panel);
        }

        // Create audio element
        var audioUrl = CDN_BASE + entry.file;
        activeAudio = new Audio(audioUrl);
        activeAudio.preload = 'auto';

        // Word-level highlighting via timeupdate
        var currentWordIdx = -1;
        activeAudio.addEventListener('timeupdate', function () {
            var t = activeAudio.currentTime;

            // Find which word we're on
            var newIdx = -1;
            for (var i = 0; i < words.length; i++) {
                if (t >= words[i].start && t < words[i].end + 0.05) {
                    newIdx = i;
                    break;
                }
                // If we've passed this word but haven't reached the next
                if (t >= words[i].start && (i + 1 >= words.length || t < words[i + 1].start)) {
                    newIdx = i;
                    break;
                }
            }

            if (newIdx !== currentWordIdx && newIdx >= 0) {
                currentWordIdx = newIdx;

                // Clear previous highlight
                var prev = panel.querySelector('.cc-tts-word.cc-tts-highlight');
                if (prev) prev.classList.remove('cc-tts-highlight');

                // Highlight current word
                var wordEl = panel.querySelector('.cc-tts-word[data-word-idx="' + currentWordIdx + '"]');
                if (wordEl) {
                    wordEl.classList.add('cc-tts-highlight');
                    var rect = wordEl.getBoundingClientRect();
                    if (rect.top < 80 || rect.bottom > window.innerHeight - 40) {
                        wordEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }
        });

        activeAudio.addEventListener('ended', function () {
            stopReading();
        });

        activeAudio.addEventListener('error', function () {
            console.warn('[ReadAloud] Pre-generated audio failed, falling back to browser TTS');
            stopReading();
            // Fall back to browser TTS
            if (hasSpeechSynthesis) {
                startBrowserTTS(btn, panel);
            }
        });

        activeAudio.play().catch(function (err) {
            console.warn('[ReadAloud] Audio play failed:', err);
            stopReading();
        });
    }

    // ---- Browser TTS Voice Selection ----
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
        synth.addEventListener('voiceschanged', function () {
            preferredVoice = pickVoice();
        });
    }

    // ---- Text Extraction ----
    function extractText(panel) {
        var clone = panel.cloneNode(true);
        var btns = clone.querySelectorAll('.cc-read-aloud-btn');
        for (var i = 0; i < btns.length; i++) btns[i].remove();
        return clone.textContent.replace(/\s+/g, ' ').trim();
    }

    // ---- Word Wrapping for Highlighting ----
    function wrapWordsInPanel(panel) {
        var walker = document.createTreeWalker(
            panel,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function (node) {
                    var parent = node.parentElement;
                    if (!parent) return NodeFilter.FILTER_REJECT;
                    if (parent.closest('.cc-read-aloud-btn')) return NodeFilter.FILTER_REJECT;
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
                    span.className = 'cc-tts-word';
                    span.dataset.wordIdx = wordIndex++;
                    span.textContent = part;
                    frag.appendChild(span);
                }
            });
            textNode.parentNode.replaceChild(frag, textNode);
        });

        return wordIndex;
    }

    function unwrapWordsInPanel(panel) {
        var wordSpans = panel.querySelectorAll('.cc-tts-word');
        wordSpans.forEach(function (span) {
            var text = document.createTextNode(span.textContent);
            span.parentNode.replaceChild(text, span);
        });
        panel.normalize();
    }

    // ---- Stop Reading (unified) ----
    function stopReading() {
        // Stop pre-generated audio
        if (activeAudio) {
            activeAudio.pause();
            activeAudio.removeAttribute('src');
            activeAudio = null;
        }

        // Stop browser TTS
        if (synth) synth.cancel();

        // Clear highlight timer
        if (activeHighlightTimer) {
            clearInterval(activeHighlightTimer);
            activeHighlightTimer = null;
        }

        // Restore panel
        if (activePanel) {
            unwrapWordsInPanel(activePanel);
            activePanel.classList.remove('cc-tts-active');
            activePanel = null;
        }

        if (activeBtn) {
            activeBtn.classList.remove('playing');
            activeBtn.setAttribute('aria-label', 'Read aloud');
            activeBtn.title = 'Read Aloud';
            activeBtn = null;
        }
    }

    // ---- Browser TTS Playback ----
    function startBrowserTTS(btn, panel) {
        if (!synth) return;

        stopReading();

        activeBtn = btn;
        activePanel = panel;
        panel.classList.add('cc-tts-active');
        btn.classList.add('playing');
        btn.setAttribute('aria-label', 'Stop reading');
        btn.title = 'Stop Reading';

        var totalWords = wrapWordsInPanel(panel);
        var text = extractText(panel);

        if (!text) { stopReading(); return; }

        var utterance = new SpeechSynthesisUtterance(text);
        if (preferredVoice) utterance.voice = preferredVoice;
        utterance.rate = 0.95;
        utterance.pitch = 1.0;

        var currentWordIdx = 0;
        utterance.addEventListener('boundary', function (e) {
            if (e.name !== 'word') return;

            var prev = panel.querySelector('.cc-tts-word.cc-tts-highlight');
            if (prev) prev.classList.remove('cc-tts-highlight');

            var wordEl = panel.querySelector('.cc-tts-word[data-word-idx="' + currentWordIdx + '"]');
            if (wordEl) {
                wordEl.classList.add('cc-tts-highlight');
                var rect = wordEl.getBoundingClientRect();
                if (rect.top < 80 || rect.bottom > window.innerHeight - 40) {
                    wordEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            currentWordIdx++;
        });

        utterance.addEventListener('end', function () { stopReading(); });
        utterance.addEventListener('error', function () { stopReading(); });

        synth.speak(utterance);
    }

    // ---- Chrome Bug Workaround ----
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

    // ---- Unified Play Handler ----
    function handlePlay(btn, panel) {
        if (activeBtn === btn) {
            stopReading();
            return;
        }

        // Check for pre-generated audio
        var entry = getManifestEntry(panel);
        if (entry && entry.file) {
            playPreGenerated(btn, panel, entry);
        } else if (hasSpeechSynthesis) {
            startBrowserTTS(btn, panel);
        }
        // If neither available, button won't appear (see injectButtons)
    }

    // ---- Button Injection ----
    function injectButtons() {
        var panels = document.querySelectorAll(
            '.cc-intro, .card-panel[data-panel="practice"], .card-panel[data-panel="blesses"]'
        );

        panels.forEach(function (panel) {
            if (panel.querySelector('.cc-read-aloud-btn')) return;

            // Only inject if we have pre-generated audio OR browser TTS
            var entry = getManifestEntry(panel);
            var hasPreGen = entry && entry.file;
            if (!hasPreGen && !hasSpeechSynthesis) return;

            var btn = document.createElement('button');
            btn.className = 'cc-read-aloud-btn';
            btn.type = 'button';
            btn.setAttribute('aria-label', 'Read aloud');
            btn.title = hasPreGen ? 'Read Aloud (narrated)' : 'Read Aloud';

            btn.innerHTML =
                '<svg class="icon-play" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>' +
                    '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>' +
                    '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>' +
                '</svg>' +
                '<svg class="icon-stop" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<rect x="6" y="4" width="4" height="16"></rect>' +
                    '<rect x="14" y="4" width="4" height="16"></rect>' +
                '</svg>' +
                '<span class="cc-ra-label">Read Aloud</span>';

            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                handlePlay(btn, panel);
            });

            panel.insertBefore(btn, panel.firstChild);
        });
    }

    // ---- Stop on Tab Switch ----
    document.querySelectorAll('.card-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
            if (activeBtn) stopReading();
        });
    });

    // ---- Stop on Page Navigation ----
    window.addEventListener('beforeunload', function () {
        if (synth) synth.cancel();
        if (activeAudio) { activeAudio.pause(); activeAudio = null; }
    });

    // ---- Initialize ----
    function init() {
        loadManifest();
        // Inject buttons after a short delay to allow manifest to load
        // But don't block — inject with browser TTS first, upgrade later
        injectButtons();

        // Re-inject after manifest loads (may upgrade tooltip text)
        var checkManifest = setInterval(function () {
            if (manifestLoaded) {
                clearInterval(checkManifest);
                // Remove and re-inject to pick up manifest data
                document.querySelectorAll('.cc-read-aloud-btn').forEach(function (btn) {
                    btn.remove();
                });
                injectButtons();
            }
        }, 200);

        // Safety timeout — stop checking after 6 seconds
        setTimeout(function () { clearInterval(checkManifest); }, 6000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
