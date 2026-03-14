/**
 * WORDS OF PLAINNESS — Audio Synchronization (Section Architecture)
 * =================================================================
 *
 * Section-based audio player. Each chapter is divided into prose sections
 * corresponding to RJW pause points. Each section has its own MP3 file and
 * its own timestamp JSON. After each prose section ends, a separate cue file
 * plays, then the RJW panel opens. The reader resumes to the next section.
 *
 * STATE MACHINE:
 *   IDLE → PLAYING_PROSE → PLAYING_CUE → RJW_OPEN → PLAYING_PROSE (next) → ...
 *
 * TIMESTAMP JSON FORMAT (per section, produced by convert-to-sentence-timestamps.py):
 *   "p{N}"  : float   — start time of paragraph N within this section file
 *   "s{N}"  : integer — paragraph index for sentence N (click-to-seek mapping)
 *
 * FRONTMATTER SECTIONS ARRAY:
 *   sections:
 *     - id: "pause-humility"
 *       prose: NR_09_S01_Invocation_Humility.mp3
 *       cue: NR_09_CUE_01_Humility.mp3
 *       paragraphs: [1, 23]
 *       timestamps: chapter-09-s01.json
 */

const AudioSync = {

    /* ── Configuration ──────────────────────────────────────────────── */

    CDN_BASE: 'https://media.wordsofplainness.org/web/',

    /* ── State ──────────────────────────────────────────────────────── */

    sections: [],           // Array of section objects from frontmatter
    allTimestamps: {},      // { sectionId: { p0: t, s0: paraIdx, ... } }

    currentSectionIndex: -1,
    state: 'IDLE',          // IDLE | PLAYING_PROSE | PLAYING_CUE | RJW_OPEN

    audioPlayer: null,      // The single <audio id="chapterAudio"> element

    // Per-section paragraph data (rebuilt on section load)
    paragraphTimes: [],     // [[paraIdx, startTime], ...] sorted ascending
    sentenceToPara: {},     // { sentenceIdx: paragraphIdx }
    paragraphRange: [0, 0], // [firstPara, lastPara] for this section

    currentParagraph: -1,
    autoScrollEnabled: true,

    /* ── Init ───────────────────────────────────────────────────────── */

    /**
     * Initialize section-based audio sync.
     * Called from ChapterManager.initAudioSync() when sections data is present.
     *
     * @param {Array}            sections   - Array of section objects from CHAPTER_CONFIG
     * @param {Object}           timestamps - Map of { sectionId: timestampObject }
     * @param {HTMLAudioElement} audioPlayer
     */
    initSections(sections, timestamps, audioPlayer) {
        if (!sections || sections.length === 0) {
            console.log('AudioSync: No sections defined — sync disabled');
            return;
        }
        if (!audioPlayer) {
            console.log('AudioSync: No audio player found — sync disabled');
            return;
        }

        this.sections       = sections;
        this.allTimestamps  = timestamps || {};
        this.audioPlayer    = audioPlayer;
        this.state          = 'IDLE';
        this.currentSectionIndex = -1;

        this.setupEventListeners();
        this.makeClickable();
        this.loadSection(0);

        console.log(
            `AudioSync (sections): ${sections.length} sections, ` +
            `${Object.keys(timestamps).length} timestamp sets loaded`
        );
    },

    /**
     * Legacy init path for chapters without sections (Chs 1–8).
     * Preserves backwards compatibility with existing sentence-level timestamps.
     */
    init(timestamps, audioPlayer) {
        if (!timestamps || !audioPlayer) return;

        // Detect section-based vs legacy format
        const keys = Object.keys(timestamps);
        const hasParagraphKeys = keys.some(k => k.startsWith('p'));

        if (!hasParagraphKeys && keys.length === 0) {
            console.log('AudioSync: Empty timestamps — sync disabled');
            return;
        }

        // Legacy paragraph-level format (single file, no sections)
        this.audioPlayer = audioPlayer;
        this._legacyInit(timestamps);
    },

    /* ── Section Loading ────────────────────────────────────────────── */

    loadSection(index) {
        if (index >= this.sections.length) {
            console.log('AudioSync: All sections complete');
            this.state = 'IDLE';
            return;
        }

        const section = this.sections[index];
        this.currentSectionIndex = index;
        this.currentParagraph = -1;
        this.state = 'PLAYING_PROSE';

        // allTimestamps is keyed by section.id (built in chapter.njk)
        const sectionTimestamps = this.allTimestamps[section.id] || {};
        this._buildSectionTimestamps(sectionTimestamps);
        this.paragraphRange = section.paragraphs || [0, 9999];

        // Swap audio src to this section's prose file
        const src = this.CDN_BASE + section.prose;
        this.audioPlayer.src = src;
        this.audioPlayer.load();

        console.log(`AudioSync: Loading section ${index + 1}/${this.sections.length} — ${section.id}`);
        console.log(`  Prose: ${section.prose}`);
        console.log(`  Paragraphs: ${this.paragraphRange[0]}–${this.paragraphRange[1]}`);
        console.log(`  Timestamps: ${Object.keys(sectionTimestamps).length} keys`);
    },

    _buildSectionTimestamps(timestamps) {
        // timestamps here is the section-level object (already looked up by key)
        this.paragraphTimes = [];
        this.sentenceToPara = {};

        for (const [key, value] of Object.entries(timestamps)) {
            if (key.startsWith('p')) {
                const idx = parseInt(key.slice(1));
                if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
            } else if (key.startsWith('s')) {
                const sentIdx = parseInt(key.slice(1));
                if (!isNaN(sentIdx)) this.sentenceToPara[sentIdx] = parseInt(value);
            }
        }

        this.paragraphTimes.sort((a, b) => a[1] - b[1]);

        // Set p_first to 0.0 so highlighting fires immediately when section starts
        if (this.paragraphTimes.length > 0) {
            const firstPara = this.paragraphTimes[0][0];
            this.paragraphTimes[0] = [firstPara, 0.0];
        }
    },

    /* ── Event Listeners ────────────────────────────────────────────── */

    setupEventListeners() {
        this.audioPlayer.addEventListener('timeupdate', () => this.onTimeUpdate());
        this.audioPlayer.addEventListener('ended',      () => this.onEnded());
        this.audioPlayer.addEventListener('pause',      () => { /* keep highlight */ });
        this.audioPlayer.addEventListener('play',       () => {
            // If resuming after RJW was dismissed without Continue, re-enter prose state
            if (this.state === 'RJW_OPEN') {
                this.state = 'PLAYING_PROSE';
            }
        });
    },

    makeClickable() {
        document.querySelectorAll('.sentence[data-index]').forEach(sentence => {
            sentence.classList.add('clickable');
            sentence.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                this.onSentenceClick(sentence);
            });
        });
    },

    /* ── Playback Events ────────────────────────────────────────────── */

    onTimeUpdate() {
        if (this.state !== 'PLAYING_PROSE') return;

        const currentTime    = this.audioPlayer.currentTime;
        const paragraphIndex = this.getParagraphAtTime(currentTime);

        if (paragraphIndex !== this.currentParagraph) {
            this.highlightParagraph(paragraphIndex);
            this.currentParagraph = paragraphIndex;
        }
    },

    onEnded() {
        this.clearHighlight();

        if (this.state === 'PLAYING_PROSE') {
            // Prose section finished — play the cue file
            this.playCue();
        } else if (this.state === 'PLAYING_CUE') {
            // Cue finished — open RJW panel
            this.openRJW();
        } else {
            this.state = 'IDLE';
        }
    },

    playCue() {
        const section = this.sections[this.currentSectionIndex];
        if (!section || !section.cue) {
            // No cue file — go straight to RJW
            this.openRJW();
            return;
        }

        this.state = 'PLAYING_CUE';

        // Lock playback speed to 1.0 for cue — always contemplative pace
        const savedRate = this.audioPlayer.playbackRate;
        this.audioPlayer.playbackRate = 1.0;

        const src = this.CDN_BASE + section.cue;
        this.audioPlayer.src = src;
        this.audioPlayer.load();
        this.audioPlayer.play().then(() => {
            console.log(`AudioSync: Playing cue — ${section.cue}`);
        }).catch(err => {
            console.warn('AudioSync: Cue playback failed:', err);
            this.openRJW();
        });

        // Restore speed after cue finishes (handled in onEnded → openRJW → advanceSection)
        this._savedPlaybackRate = savedRate;
    },

    openRJW() {
        this.state = 'RJW_OPEN';
        const section = this.sections[this.currentSectionIndex];

        // Pause the audio player and update UI
        if (window.ChapterManager) {
            window.ChapterManager.pause();
        } else {
            this.audioPlayer.pause();
        }

        // Restore playback rate for next section
        if (this._savedPlaybackRate) {
            this.audioPlayer.playbackRate = this._savedPlaybackRate;
            this._savedPlaybackRate = null;
        }

        if (window.RJW && section && section.id) {
            console.log(`AudioSync: Opening RJW panel — ${section.id}`);
            window.RJW.openModal(section.id, 'reflect');
        }
    },

    /**
     * Called by RJW.closeModal() when the reader clicks Continue.
     * Advances to the next section and begins playback.
     */
    advanceSection() {
        const nextIndex = this.currentSectionIndex + 1;
        if (nextIndex >= this.sections.length) {
            console.log('AudioSync: Chapter complete — no more sections');
            this.state = 'IDLE';
            return;
        }

        this.loadSection(nextIndex);

        // Small delay to allow src/load to settle before play
        setTimeout(() => {
            if (window.ChapterManager) {
                window.ChapterManager.play();
            } else {
                this.audioPlayer.play();
            }
        }, 300);
    },

    /**
     * Replay the current section's cue audio independently.
     * Can be triggered from a "Hear the prompt again" button in the RJW panel.
     */
    replayCue() {
        const section = this.sections[this.currentSectionIndex];
        if (!section || !section.cue) return;

        const src = this.CDN_BASE + section.cue;
        this.audioPlayer.src = src;
        this.audioPlayer.load();
        this.audioPlayer.playbackRate = 1.0;
        this.audioPlayer.play();
        this.state = 'PLAYING_CUE';
    },

    /* ── Paragraph Highlighting ─────────────────────────────────────── */

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

    highlightParagraph(paragraphIndex) {
        this.clearHighlight();
        if (paragraphIndex < 0) return;

        const el = document.querySelector(`[data-paragraph="${paragraphIndex}"]`);
        if (!el) return;

        // Skip heading spans (paraspan inside h2/h3)
        if (el.tagName === 'SPAN' && el.closest('h2, h3')) return;

        el.classList.add('highlighted');
        if (this.autoScrollEnabled) {
            this.scrollToElement(el);
        }
    },

    clearHighlight() {
        document.querySelectorAll('[data-paragraph].highlighted')
            .forEach(el => el.classList.remove('highlighted'));
    },

    scrollToElement(el) {
        const rect = el.getBoundingClientRect();
        const vh   = window.innerHeight;
        if (rect.top < vh * 0.3 || rect.bottom > vh * 0.7) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    /* ── Click-to-Seek ──────────────────────────────────────────────── */

    onSentenceClick(sentence) {
        const sentIdx = parseInt(sentence.dataset.index);
        const paraIdx = this.sentenceToPara[sentIdx];

        if (paraIdx === undefined) {
            // Sentence not in current section — find which section owns it
            this._seekToSentenceInSection(sentIdx);
            return;
        }

        // Sentence is in current section — seek within current file
        const entry = this.paragraphTimes.find(([idx]) => idx === paraIdx);
        if (!entry) return;

        this._seekTo(entry[1]);
    },

    _seekToSentenceInSection(sentIdx) {
        // Find which section contains this sentence
        for (let i = 0; i < this.sections.length; i++) {
            const section = this.sections[i];
            const sectionTimestamps = this.allTimestamps[section.id] || {};
            const sentKey = `s${sentIdx}`;

            if (sentKey in sectionTimestamps) {
                const paraIdx = sectionTimestamps[sentKey];
                const paraTime = sectionTimestamps[`p${paraIdx}`] || 0;

                if (i !== this.currentSectionIndex) {
                    this.loadSection(i);
                    setTimeout(() => this._seekTo(paraTime), 300);
                } else {
                    this._seekTo(paraTime);
                }
                return;
            }
        }
        console.warn(`AudioSync: sentence ${sentIdx} not found in any section`);
    },

    _seekTo(time) {
        this.state = 'PLAYING_PROSE';

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

    toggleAutoScroll() {
        this.autoScrollEnabled = !this.autoScrollEnabled;
        return this.autoScrollEnabled;
    },

    /* ── Legacy Single-File Support (Chs 1–8) ──────────────────────── */

    _legacyInit(timestamps) {
        this.paragraphTimes = [];
        this.sentenceToPara = {};

        for (const [key, value] of Object.entries(timestamps)) {
            if (key.startsWith('p')) {
                const idx = parseInt(key.slice(1));
                if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
            } else if (key.startsWith('s')) {
                const sentIdx = parseInt(key.slice(1));
                if (!isNaN(sentIdx)) this.sentenceToPara[sentIdx] = parseInt(value);
            } else {
                // Legacy numeric sentence keys
                const idx = parseInt(key);
                if (!isNaN(idx)) this.paragraphTimes.push([idx, parseFloat(value)]);
            }
        }

        this.paragraphTimes.sort((a, b) => a[1] - b[1]);

        if (this.paragraphTimes.length === 0) {
            console.log('AudioSync (legacy): No timestamps — sync disabled');
            return;
        }

        const allZero = this.paragraphTimes.every(([, t]) => t === 0);
        if (allZero) {
            console.log('AudioSync (legacy): All timestamps are placeholder zeros — sync disabled');
            return;
        }

        this.state = 'PLAYING_PROSE';
        this._setupLegacyListeners();
        this.makeClickable();

        console.log(`AudioSync (legacy): ${this.paragraphTimes.length} paragraph timestamps`);
    },

    _setupLegacyListeners() {
        this.audioPlayer.addEventListener('timeupdate', () => {
            if (this.state !== 'PLAYING_PROSE') return;
            const paragraphIndex = this.getParagraphAtTime(this.audioPlayer.currentTime);
            if (paragraphIndex !== this.currentParagraph) {
                this.highlightParagraph(paragraphIndex);
                this.currentParagraph = paragraphIndex;
            }
        });
        this.audioPlayer.addEventListener('ended', () => this.clearHighlight());
    },
};

window.AudioSync = AudioSync;
