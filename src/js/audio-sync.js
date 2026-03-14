/**
 * WORDS OF PLAINNESS - Audio Synchronization
 * ==========================================
 * 
 * Handles sentence-level highlighting synchronized with audio playback.
 * Uses timestamps data provided by the chapter template.
 */

const AudioSync = {
    timestamps: {},
    timestampsSorted: [],     // [[sentenceIndex, startTime], ...] sorted by startTime
    audioPlayer: null,
    sentences: [],
    currentSentence: -1,
    autoScrollEnabled: true,
    pauseTriggers: {},        // { sentenceIndex: pausePointId }
    pauseFired: {},           // { sentenceIndex: true } — prevent re-firing
    
    /**
     * Initialize audio sync
     * @param {Object} timestamps - Sentence index to time mapping
     * @param {HTMLAudioElement} audioPlayer - Audio element
     */
    init(timestamps, audioPlayer) {
        // Normalize timestamps: convert array of {index, start, end} to lookup map
        if (Array.isArray(timestamps)) {
            this.timestamps = {};
            timestamps.forEach(t => {
                this.timestamps[t.index] = { start: t.start, end: t.end };
            });
        } else {
            this.timestamps = timestamps || {};
        }

        // Build a sorted array of [sentenceIndex, startTime] pairs ordered
        // by startTime ascending. Object.entries() uses insertion order which
        // is not reliable for numeric string keys — especially when cue indices
        // (385-388) are appended after prose indices but have mid-chapter times.
        // getSentenceAtTime() must iterate in time order, not insertion order.
        this.timestampsSorted = Object.entries(this.timestamps)
            .map(([k, v]) => [parseInt(k), (typeof v === 'object') ? v.start : v])
            .sort((a, b) => a[1] - b[1]);

        this.audioPlayer = audioPlayer;
        this.sentences = document.querySelectorAll('.sentence[data-index]');

        if (!this.audioPlayer || Object.keys(this.timestamps).length === 0) {
            console.log('AudioSync: No timestamps or audio player — sync disabled');
            return;
        }

        // Placeholder guard: if all timestamp values are 0, sync is not yet calibrated.
        // Bail out to prevent bogus scroll-to-bottom and broken click-to-seek.
        const values = Object.values(this.timestamps);
        const allZero = values.every(v => {
            const t = (typeof v === 'object') ? v.start : v;
            return t === 0 || t === 0.0;
        });
        if (allZero) {
            console.log('AudioSync: All timestamps are placeholder zeros — sync disabled');
            return;
        }
        
        this.buildPauseTriggers();
        this.setupEventListeners();
        this.makeClickable();
        
        console.log(`AudioSync initialized with ${this.sentences.length} sentences, ${this.timestampsSorted.length} timestamps`);
    },
    
    // Build pause trigger map from narration-only cue spans in the DOM.
    // Each cue span carries data-pause-id matching a frontmatter pause ID.
    // Called once during init, after timestamps are loaded.
    buildPauseTriggers() {
        this.pauseTriggers = {};
        this.pauseFired = {};
        document.querySelectorAll('.narration-only[data-pause-id]').forEach(el => {
            const idx = parseInt(el.dataset.index);
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
        this.audioPlayer.addEventListener('ended', () => this.clearHighlight());
        this.audioPlayer.addEventListener('pause', () => this.onPause());
    },
    
    makeClickable() {
        this.sentences.forEach(sentence => {
            sentence.classList.add('clickable');
            sentence.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                this.onSentenceClick(sentence);
            });
        });
    },
    
    onTimeUpdate() {
        const currentTime = this.audioPlayer.currentTime;
        const sentenceIndex = this.getSentenceAtTime(currentTime);
        
        if (sentenceIndex !== this.currentSentence) {
            this.highlightSentence(sentenceIndex);
            this.currentSentence = sentenceIndex;
            this.checkPauseTrigger(sentenceIndex);
        }
    },

    // If the newly-reached sentence is a pause cue, stop playback and
    // open the RJW panel. The fired guard prevents re-triggering if the
    // listener seeks back into the same sentence.
    checkPauseTrigger(sentenceIndex) {
        const pauseId = this.pauseTriggers[sentenceIndex];
        if (!pauseId) return;
        if (this.pauseFired[sentenceIndex]) return;
        this.pauseFired[sentenceIndex] = true;

        console.log(`AudioSync: pause trigger fired for ${sentenceIndex} -> ${pauseId}`);

        // Let the cue line play for 1 second before pausing — long enough
        // for the listener to hear it begin, short enough to not cut it off.
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

    // Reset fired guards when the user manually seeks — allows re-triggering
    // if they replay a section.
    resetPauseFired() {
        this.pauseFired = {};
    },
    
    getSentenceAtTime(time) {
        // Use timestampsSorted (sorted by startTime ascending) so we never
        // break early due to out-of-order entries. Walk the full sorted array
        // and return the last sentence whose startTime is <= currentTime.
        let lastSentence = -1;
        for (const [sentenceIndex, startTime] of this.timestampsSorted) {
            if (startTime <= time) {
                lastSentence = sentenceIndex;
            } else {
                // Since array is sorted by time, all subsequent entries will
                // also be > time. Safe to stop here.
                break;
            }
        }
        return lastSentence;
    },
    
    highlightSentence(index) {
        // Remove previous highlight
        this.clearHighlight();
        
        // Add new highlight to ALL elements sharing this index
        const matches = document.querySelectorAll(`.sentence[data-index="${index}"]`);
        if (matches.length > 0) {
            matches.forEach(el => el.classList.add('highlighted'));
            
            if (this.autoScrollEnabled) {
                this.scrollToSentence(matches[0]);
            }
        }
    },
    
    clearHighlight() {
        this.sentences.forEach(s => s.classList.remove('highlighted'));
    },
    
    scrollToSentence(sentence) {
        const rect = sentence.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        
        // Only scroll if sentence is not in the middle third of viewport
        if (rect.top < viewportHeight * 0.3 || rect.bottom > viewportHeight * 0.7) {
            sentence.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    },
    
    onSentenceClick(sentence) {
        const index = parseInt(sentence.dataset.index);
        const ts = this.timestamps[index];
        const time = (typeof ts === 'object') ? ts.start : ts;

        if (time !== undefined && this.audioPlayer) {
            // Reset pause-fired guards on manual seek so triggers re-arm.
            this.resetPauseFired();

            // Show the audio player if it's hidden
            const playerEl = document.getElementById('audioPlayer');
            if (playerEl && !playerEl.classList.contains('visible')) {
                playerEl.classList.add('visible');
            }

            this.audioPlayer.currentTime = time;

            // Start playing if paused
            if (this.audioPlayer.paused) {
                this.audioPlayer.play();
                // Sync play/pause icons in ChapterManager
                if (window.ChapterManager) {
                    window.ChapterManager.isPlaying = true;
                    const playIcon = document.getElementById('playIcon');
                    const pauseIcon = document.getElementById('pauseIcon');
                    if (playIcon) playIcon.style.display = 'none';
                    if (pauseIcon) pauseIcon.style.display = 'block';
                }
            }
        }
    },
    
    onPause() {
        // Optionally keep highlight visible when paused
    },
    
    toggleAutoScroll() {
        this.autoScrollEnabled = !this.autoScrollEnabled;
        return this.autoScrollEnabled;
    }
};

// Export
window.AudioSync = AudioSync;
