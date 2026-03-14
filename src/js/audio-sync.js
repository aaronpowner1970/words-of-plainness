/**
 * WORDS OF PLAINNESS - Audio Synchronization
 * ==========================================
 *
 * Paragraph-level highlighting synchronized with audio playback.
 * Sentence-level click-to-seek maps any sentence click to its paragraph timestamp.
 * Cue-based pause triggers (indices 385-388) open the RJW panel.
 *
 * Timestamp JSON format (produced by build_paragraph_timestamps.py):
 *   "p{N}"     : float   — start time of paragraph N in seconds
 *   "s{N}"     : integer — paragraph index for sentence N (click-to-seek mapping)
 *   "cue{N}"   : float   — start time of pause cue N in seconds
 */

const AudioSync = {
    // Paragraph timestamps: { paragraphIndex: startTimeSeconds }
    paragraphTimes: [],      // [[paragraphIndex, startTime], ...] sorted by startTime ascending

    // Sentence-to-paragraph lookup: { sentenceIndex: paragraphIndex }
    sentenceToPara: {},

    // Cue timestamps: { cueIndex: startTimeSeconds }
    cueTimes: {},

    audioPlayer: null,
    paragraphs: [],          // DOM elements with data-paragraph attribute
    sentences: [],           // DOM elements with data-index (for click-to-seek)
    currentParagraph: -1,
    autoScrollEnabled: true,
    pauseTriggers: {},       // { cueIndex: pausePointId }
    pauseFired: {},          // { cueIndex: true } — prevent re-firing

    /**
     * Initialize audio sync
     * @param {Object} timestamps - Timestamp data from chapter template
     * @param {HTMLAudioElement} audioPlayer - Audio element
     */
    init(timestamps, audioPlayer) {
        // Parse the mixed-format timestamp object
        // Keys starting with "p" = paragraph timestamps
        // Keys starting with "s" = sentence-to-paragraph mappings
        // Keys starting with "cue" = cue timestamps
        // Legacy numeric keys (old sentence-level format) = ignored for highlighting
        //   but used for click-to-seek fallback

        this.paragraphTimes = [];
        this.sentenceToPara = {};
        this.cueTimes = {};
        const legacyTimes = {};

        for (const [key, value] of Object.entries(timestamps || {})) {
            if (key.startsWith('p')) {
                const idx = parseInt(key.slice(1));
                if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
            } else if (key.startsWith('cue')) {
                const idx = parseInt(key.slice(3));
                if (!isNaN(idx)) this.cueTimes[idx] = parseFloat(value);
            } else if (key.startsWith('s')) {
                const sentIdx = parseInt(key.slice(1));
                if (!isNaN(sentIdx)) this.sentenceToPara[sentIdx] = parseInt(value);
            } else {
                // Legacy numeric key — plain sentence timestamp
                const idx = parseInt(key);
                if (!isNaN(idx)) legacyTimes[idx] = parseFloat(value);
            }
        }

        // Sort paragraph times by startTime ascending for binary-search-style lookup
        this.paragraphTimes.sort((a, b) => a[1] - b[1]);

        // If no paragraph keys found, fall back gracefully to legacy sentence format
        if (this.paragraphTimes.length === 0 && Object.keys(legacyTimes).length > 0) {
            console.log('AudioSync: No paragraph timestamps found — falling back to legacy sentence format');
            this.paragraphTimes = Object.entries(legacyTimes)
                .map(([k, v]) => [parseInt(k), v])
                .sort((a, b) => a[1] - b[1]);
        }

        this.audioPlayer = audioPlayer;
        this.paragraphs = document.querySelectorAll('[data-paragraph]');
        this.sentences  = document.querySelectorAll('.sentence[data-index]');

        if (!this.audioPlayer || this.paragraphTimes.length === 0) {
            console.log('AudioSync: No timestamps or audio player — sync disabled');
            return;
        }

        // Placeholder guard: bail if all paragraph timestamps are zero
        const allZero = this.paragraphTimes.every(([, t]) => t === 0);
        if (allZero) {
            console.log('AudioSync: All timestamps are placeholder zeros — sync disabled');
            return;
        }

        this.buildPauseTriggers();
        this.setupEventListeners();
        this.makeClickable();

        console.log(
            `AudioSync initialized: ${this.paragraphTimes.length} paragraphs, ` +
            `${Object.keys(this.cueTimes).length} cues, ` +
            `${Object.keys(this.sentenceToPara).length} sentence mappings`
        );
    },

    // Build pause trigger map from narration-only cue spans in the DOM.
    // Each cue span carries data-pause-id matching a frontmatter pause ID.
    buildPauseTriggers() {
        this.pauseTriggers = {};
        this.pauseFired   = {};

        document.querySelectorAll('.narration-only[data-pause-id]').forEach(el => {
            const idx     = parseInt(el.dataset.index);
            const pauseId = el.dataset.pauseId;
            if (!isNaN(idx) && pauseId) {
                this.pauseTriggers[idx] = pauseId;
            }
        });

        const count = Object.keys(this.pauseTriggers).length;
        if (count > 0) {
            console.log(`AudioSync: ${count} pause trigger(s) registered`, this.pauseTriggers);
        }
    },

    setupEventListeners() {
        this.audioPlayer.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audioPlayer.addEventListener('ended',      () => this.clearHighlight());
        this.audioPlayer.addEventListener('pause',      () => this.onPause());
    },

    makeClickable() {
        // Make sentence spans clickable for seek-to-paragraph
        this.sentences.forEach(sentence => {
            sentence.classList.add('clickable');
            sentence.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                this.onSentenceClick(sentence);
            });
        });
    },

    onTimeUpdate() {
        const currentTime    = this.audioPlayer.currentTime;
        const paragraphIndex = this.getParagraphAtTime(currentTime);
        const cueIndex       = this.getCueAtTime(currentTime);

        if (paragraphIndex !== this.currentParagraph) {
            this.highlightParagraph(paragraphIndex);
            this.currentParagraph = paragraphIndex;
        }

        if (cueIndex !== null) {
            this.checkPauseTrigger(cueIndex);
        }
    },

    // Return the paragraph index whose startTime is <= currentTime
    getParagraphAtTime(time) {
        let last = -1;
        for (const [paraIdx, startTime] of this.paragraphTimes) {
            if (startTime <= time) {
                last = paraIdx;
            } else {
                break;
            }
        }
        return last;
    },

    // Return the cue index if the current time falls within a cue window, else null
    // Cue window = [cueTime, cueTime + 15s] — long enough to cover the cue line
    getCueAtTime(time) {
        for (const [cueIdx, cueTime] of Object.entries(this.cueTimes)) {
            if (time >= cueTime && time < cueTime + 15) {
                return parseInt(cueIdx);
            }
        }
        return null;
    },

    // Stop playback and open the RJW panel when a cue is reached
    checkPauseTrigger(cueIndex) {
        const pauseId = this.pauseTriggers[cueIndex];
        if (!pauseId) return;
        if (this.pauseFired[cueIndex]) return;
        this.pauseFired[cueIndex] = true;

        console.log(`AudioSync: pause trigger fired for cue ${cueIndex} -> ${pauseId}`);

        // 1 second delay so the listener hears the cue begin before playback stops
        setTimeout(() => {
            if (window.ChapterManager) {
                window.ChapterManager.pause();
            } else {
                this.audioPlayer.pause();
            }
            if (window.RJW) {
                window.RJW.openModal(pauseId, 'reflect');
            }
        }, 1000);
    },

    resetPauseFired() {
        this.pauseFired = {};
    },

    highlightParagraph(paragraphIndex) {
        this.clearHighlight();
        if (paragraphIndex < 0) return;

        const el = document.querySelector(`[data-paragraph="${paragraphIndex}"]`);
        if (el) {
            el.classList.add('highlighted');
            if (this.autoScrollEnabled) {
                this.scrollToElement(el);
            }
        }
    },

    clearHighlight() {
        document.querySelectorAll('[data-paragraph].highlighted')
            .forEach(el => el.classList.remove('highlighted'));
    },

    scrollToElement(el) {
        const rect          = el.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        if (rect.top < viewportHeight * 0.3 || rect.bottom > viewportHeight * 0.7) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    // Click on any sentence -> find its paragraph -> seek to paragraph start time
    onSentenceClick(sentence) {
        const sentIdx  = parseInt(sentence.dataset.index);
        const paraIdx  = this.sentenceToPara[sentIdx];

        if (paraIdx === undefined) {
            console.warn(`AudioSync: no paragraph mapping for sentence ${sentIdx}`);
            return;
        }

        // Find the paragraph's start time
        const entry = this.paragraphTimes.find(([idx]) => idx === paraIdx);
        if (!entry) {
            console.warn(`AudioSync: no timestamp for paragraph ${paraIdx}`);
            return;
        }

        const time = entry[1];
        this.resetPauseFired();

        const playerEl = document.getElementById('audioPlayer');
        if (playerEl && !playerEl.classList.contains('visible')) {
            playerEl.classList.add('visible');
        }

        this.audioPlayer.currentTime = time;

        if (this.audioPlayer.paused) {
            this.audioPlayer.play();
            if (window.ChapterManager) {
                window.ChapterManager.isPlaying = true;
                const playIcon  = document.getElementById('playIcon');
                const pauseIcon = document.getElementById('pauseIcon');
                if (playIcon)  playIcon.style.display  = 'none';
                if (pauseIcon) pauseIcon.style.display = 'block';
            }
        }
    },

    onPause() {
        // Keep highlight visible when paused
    },

    toggleAutoScroll() {
        this.autoScrollEnabled = !this.autoScrollEnabled;
        return this.autoScrollEnabled;
    }
};

// Export
window.AudioSync = AudioSync;
