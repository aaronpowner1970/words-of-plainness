/**
 * WORDS OF PLAINNESS — Ambient Reading Player
 * =============================================
 * Self-contained ambient music player for chapter pages.
 * Coordinates with other audio elements through DOM event listeners only.
 * Does NOT modify any existing JS files or global state (except reading WOP_AMBIENT_TRACKS).
 */
(function() {
    'use strict';

    // =========================================
    // State
    // =========================================
    var tracks = [];
    var shuffled = [];
    var currentIndex = 0;
    var audio = null;
    var isActive = false;
    var autoPaused = false;
    var volume = 0.3;

    // DOM ref caches
    var desktopControl = null;
    var mobileControl = null;
    var watchedElements = [];

    // =========================================
    // Init
    // =========================================
    function init() {
        tracks = window.WOP_AMBIENT_TRACKS || [];
        if (!tracks.length) {
            hideControls();
            return;
        }

        // Create a dedicated audio element (separate from all existing ones)
        audio = document.createElement('audio');
        audio.preload = 'none';
        audio.id = 'ambientAudio';
        document.body.appendChild(audio);

        // Cache DOM refs
        desktopControl = document.getElementById('ambientControl');
        mobileControl = document.getElementById('ambientControlMobile');

        // Restore volume from localStorage
        var savedVol = localStorage.getItem('wop_ambient_volume');
        if (savedVol !== null) {
            volume = parseFloat(savedVol);
        }
        audio.volume = volume;

        // Bind all events
        bindEvents();

        // Auto-activate if was playing in a previous chapter/session
        if (localStorage.getItem('wop_ambient_playing') === 'true') {
            activate();
        }
    }

    function hideControls() {
        var dc = document.getElementById('ambientControl');
        var mc = document.getElementById('ambientControlMobile');
        if (dc) dc.style.display = 'none';
        if (mc) mc.style.display = 'none';
    }

    // =========================================
    // Events
    // =========================================
    function bindEvents() {
        // Audio ended → advance to next track
        audio.addEventListener('ended', function() {
            nextTrack();
        });

        // Desktop toggle
        var toggleDesktop = document.getElementById('ambientToggle');
        if (toggleDesktop) {
            toggleDesktop.addEventListener('click', function(e) {
                e.stopPropagation();
                toggle();
            });
        }

        // Mobile toggle
        var toggleMobile = document.getElementById('ambientToggleMobile');
        if (toggleMobile) {
            toggleMobile.addEventListener('click', function(e) {
                e.stopPropagation();
                toggle();
            });
        }

        // Desktop skip
        var skipDesktop = document.getElementById('ambientSkip');
        if (skipDesktop) {
            skipDesktop.addEventListener('click', function(e) {
                e.stopPropagation();
                nextTrack();
            });
        }

        // Mobile skip
        var skipMobile = document.getElementById('ambientSkipMobile');
        if (skipMobile) {
            skipMobile.addEventListener('click', function(e) {
                e.stopPropagation();
                nextTrack();
            });
        }

        // Desktop control click (on the control itself, not child buttons) — toggle
        if (desktopControl) {
            desktopControl.addEventListener('click', function(e) {
                // Only toggle if click wasn't on skip or toggle button
                if (!e.target.closest('.ambient-skip') && !e.target.closest('.ambient-toggle-btn')) {
                    toggle();
                }
            });
        }
        if (mobileControl) {
            mobileControl.addEventListener('click', function(e) {
                if (!e.target.closest('.ambient-skip') && !e.target.closest('.ambient-toggle-btn')) {
                    toggle();
                }
            });
        }

        // Auto-pause coordination with all chapter audio elements
        attachAudioListeners();
    }

    function attachAudioListeners() {
        // Known audio element IDs on chapter pages
        var ids = ['chapterAudio', 'overviewAudio', 'testimonyAudio', 'anthemAudio'];

        ids.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) {
                watchAudioElement(el);
            }
        });

        // MutationObserver for dynamically created audio elements (e.g., lazy-loaded modals)
        var observer = new MutationObserver(function(mutations) {
            for (var i = 0; i < mutations.length; i++) {
                var added = mutations[i].addedNodes;
                for (var j = 0; j < added.length; j++) {
                    var node = added[j];
                    if (node.nodeType !== 1) continue;
                    if (node.tagName === 'AUDIO' && node.id !== 'ambientAudio') {
                        watchAudioElement(node);
                    }
                    if (node.querySelectorAll) {
                        var audios = node.querySelectorAll('audio:not(#ambientAudio)');
                        for (var k = 0; k < audios.length; k++) {
                            watchAudioElement(audios[k]);
                        }
                    }
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    function watchAudioElement(el) {
        // Avoid double-watching
        if (watchedElements.indexOf(el) !== -1) return;
        watchedElements.push(el);

        el.addEventListener('play', function() {
            if (isActive && !audio.paused) {
                autoPaused = true;
                audio.pause();
            }
        });

        el.addEventListener('pause', function() {
            if (autoPaused) {
                autoPaused = false;
                if (isActive) {
                    audio.play().catch(function() {});
                }
            }
        });

        el.addEventListener('ended', function() {
            if (autoPaused) {
                autoPaused = false;
                if (isActive) {
                    audio.play().catch(function() {});
                }
            }
        });
    }

    // =========================================
    // Shuffle
    // =========================================
    function shuffleArray(arr) {
        var a = arr.slice();
        for (var i = a.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1));
            var temp = a[i];
            a[i] = a[j];
            a[j] = temp;
        }
        return a;
    }

    // =========================================
    // Playback
    // =========================================
    function activate() {
        isActive = true;
        shuffled = shuffleArray(tracks);
        currentIndex = 0;
        playCurrentTrack();
        updateUI();
        localStorage.setItem('wop_ambient_playing', 'true');
    }

    function deactivate() {
        isActive = false;
        autoPaused = false;
        audio.pause();
        updateUI();
        localStorage.setItem('wop_ambient_playing', 'false');
    }

    function toggle() {
        if (isActive) {
            deactivate();
        } else {
            activate();
        }
    }

    function playCurrentTrack() {
        if (!shuffled.length) return;
        var track = shuffled[currentIndex];
        audio.src = track.file;
        audio.volume = volume;
        audio.play().catch(function(err) {
            if (err.name === 'NotAllowedError') {
                // Autoplay blocked — stay in active state, will play on next user interaction
                console.log('Ambient: autoplay blocked by browser policy');
            }
        });
    }

    function nextTrack() {
        if (!shuffled.length || !isActive) return;
        currentIndex++;
        if (currentIndex >= shuffled.length) {
            // Reshuffle and restart from beginning
            shuffled = shuffleArray(tracks);
            currentIndex = 0;
        }
        playCurrentTrack();
        updateUI();
    }

    // =========================================
    // UI
    // =========================================
    function updateUI() {
        var controls = [desktopControl, mobileControl];
        var toggleBtns = [
            document.getElementById('ambientToggle'),
            document.getElementById('ambientToggleMobile')
        ];
        var labels = [
            document.getElementById('ambientLabel'),
            document.getElementById('ambientLabelMobile')
        ];

        controls.forEach(function(ctrl) {
            if (!ctrl) return;
            if (isActive) {
                ctrl.classList.add('active');
            } else {
                ctrl.classList.remove('active');
            }
        });

        toggleBtns.forEach(function(btn) {
            if (!btn) return;
            btn.setAttribute('aria-checked', isActive ? 'true' : 'false');
        });

        labels.forEach(function(label) {
            if (!label) return;
            if (isActive && shuffled.length) {
                label.textContent = shuffled[currentIndex].title;
            } else {
                label.textContent = 'Reading Atmosphere';
            }
        });
    }

    // =========================================
    // Bootstrap
    // =========================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
