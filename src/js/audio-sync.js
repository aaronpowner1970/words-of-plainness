/**
 * WORDS OF PLAINNESS - Audio Synchronization
 * ==========================================
 * 
 * Handles sentence-level highlighting synchronized with audio playback.
 * Uses timestamps data provided by the chapter template.
 */

const AudioSync = {
    timestamps: {},
    audioPlayer: null,
    sentences: [],
    currentSentence: -1,
    autoScrollEnabled: true,
    
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
        this.audioPlayer = audioPlayer;
        this.sentences = document.querySelectorAll('.sentence[data-index]');

        if (!this.audioPlayer || Object.keys(this.timestamps).length === 0) {
            console.log('AudioSync: No timestamps or audio player');
            return;
        }
        
        this.setupEventListeners();
        this.makeClickable();
        
        console.log(`AudioSync initialized with ${this.sentences.length} sentences`);
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
        }
    },
    
    getSentenceAtTime(time) {
        let lastSentence = -1;

        // Find the sentence whose start time is <= current time
        for (const [index, ts] of Object.entries(this.timestamps)) {
            const start = (typeof ts === 'object') ? ts.start : ts;
            if (start <= time) {
                lastSentence = parseInt(index);
            } else {
                break;
            }
        }

        return lastSentence;
    },
    
    highlightSentence(index) {
        // Remove previous highlight
        this.clearHighlight();

        // Add new highlight to ALL elements sharing this data-index
        const sentences = document.querySelectorAll(`.sentence[data-index="${index}"]`);
        sentences.forEach(s => s.classList.add('highlighted'));

        if (sentences.length > 0 && this.autoScrollEnabled) {
            this.scrollToSentence(sentences[0]);
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
