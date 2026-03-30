/**
 * WORDS OF PLAINNESS - Chapter Manager
 * =====================================
 * 
 * Core functionality for chapter pages including:
 * - Audio playback and controls
 * - Reading progress tracking
 * - Font size controls
 * - Bookmarking
 * - TOC navigation
 * - Floating action bar behavior
 * - Modal management
 * - Slides carousel
 * 
 * This will be fully implemented during Phase 2 by extracting
 * functionality from the existing Chapter 1 HTML.
 */

const ChapterManager = {
    config: null,
    audioPlayer: null,
    isPlaying: false,
    currentSpeed: 1,
    bookmarkPosition: null,
    
    /**
     * Initialize chapter functionality
     * @param {Object} config - Chapter configuration from template
     */
    init(config) {
        this.config = config;
        console.log('ChapterManager initializing...', config);
        
        this.initAudioPlayer();
        this.initAudioSync();
        this.initReadingProgress();
        this.initFontControls();
        this.initBookmark();
        this.initComplete();
        this.initShare();
        this.initFloatingActionBar();
        this.initTOC();
        this.initModals();
        this.initSlides();
        this.initBackToTop();
        this.initMobileFAB();
        this.initResumePrompt();
        this.initReflections();
        this.linkScriptures();
        this.initReadingProgressSync();
        this.checkHashRoute();

        console.log('ChapterManager initialized for:', config.title);
    },
    
    // Audio Sync (sentence highlighting + click-to-seek)
    initAudioSync() {
        if (typeof AudioSync === 'undefined') return;
        const audio = document.getElementById('chapterAudio');

        if (this.config.sections && this.config.sections.length > 0) {
            // Section-based architecture (Ch 9+): each section is its own audio file
            AudioSync.initSections(this.config.sections, this.config.sectionTimestamps || {}, audio);
        } else if (this.config.timestamps) {
            // Legacy single-file architecture (Chs 1-8)
            // Pass cueFile and cueId so the cue plays and RJW opens after narration ends
            AudioSync.init(this.config.timestamps, audio, this.config.cueFile, this.config.cueId);
        }
    },

    // Audio Player
    initAudioPlayer() {
        this.audioPlayer = document.getElementById('chapterAudio');
        const playPauseBtn = document.getElementById('audioPlayPause');
        const audioSeek = document.getElementById('audioSeek');
        const speedDownBtn = document.getElementById('audioSpeedDown');
        const speedUpBtn = document.getElementById('audioSpeedUp');
        const closeBtn = document.getElementById('audioClose');
        const rewindBtn = document.getElementById('audioRewind');
        const forwardBtn = document.getElementById('audioForward');

        // Listen button triggers
        document.getElementById('btnListenFloat')?.addEventListener('click', () => this.showAudioPlayer());

        playPauseBtn?.addEventListener('click', () => this.togglePlayPause());
        rewindBtn?.addEventListener('click', () => this.seek(-10));
        forwardBtn?.addEventListener('click', () => this.seek(10));
        speedDownBtn?.addEventListener('click', () => this.changeSpeed(-1));
        speedUpBtn?.addEventListener('click', () => this.changeSpeed(1));
        closeBtn?.addEventListener('click', () => this.hideAudioPlayer());
        
        this.audioPlayer?.addEventListener('timeupdate', () => this.updateProgress());
        this.audioPlayer?.addEventListener('loadedmetadata', () => this.updateDuration());
        this.audioPlayer?.addEventListener('ended', () => this.onAudioEnd());
        
        audioSeek?.addEventListener('input', (e) => this.seekTo(e.target.value));
    },
    
    showAudioPlayer() {
        document.getElementById('audioPlayer')?.classList.add('visible');
    },
    
    hideAudioPlayer() {
        this.pause();
        document.getElementById('audioPlayer')?.classList.remove('visible');
    },
    
    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    },
    
    play() {
        this.audioPlayer?.play();
        this.isPlaying = true;
        document.getElementById('playIcon').style.display = 'none';
        document.getElementById('pauseIcon').style.display = 'block';
        document.dispatchEvent(new Event('wop:audio-play'));
        if (window.Engagement) window.Engagement.track('audio_play', { section_id: window.AudioSync?.currentSectionId || null });
    },

    pause() {
        this.audioPlayer?.pause();
        this.isPlaying = false;
        document.getElementById('playIcon').style.display = 'block';
        document.getElementById('pauseIcon').style.display = 'none';
        document.dispatchEvent(new Event('wop:audio-pause'));
    },
    
    seek(seconds) {
        if (this.audioPlayer) {
            this.audioPlayer.currentTime += seconds;
        }
    },
    
    seekTo(percent) {
        if (this.audioPlayer && this.audioPlayer.duration) {
            this.audioPlayer.currentTime = (percent / 100) * this.audioPlayer.duration;
        }
    },
    
    changeSpeed(direction) {
        const speeds = [0.75, 1, 1.25, 1.5];
        const currentIndex = speeds.indexOf(this.currentSpeed);
        const newIndex = currentIndex + direction;

        if (newIndex < 0 || newIndex >= speeds.length) return;

        this.currentSpeed = speeds[newIndex];

        if (this.audioPlayer) {
            this.audioPlayer.playbackRate = this.currentSpeed;
        }

        document.getElementById('audioSpeed').textContent = this.currentSpeed + 'x';
    },
    
    updateProgress() {
        if (!this.audioPlayer) return;
        
        const percent = (this.audioPlayer.currentTime / this.audioPlayer.duration) * 100;
        document.getElementById('audioSeek').value = percent;
        
        document.getElementById('audioCurrentTime').textContent = this.formatTime(this.audioPlayer.currentTime);
    },
    
    updateDuration() {
        if (!this.audioPlayer) return;
        document.getElementById('audioDuration').textContent = this.formatTime(this.audioPlayer.duration);
    },
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },
    
    onAudioEnd() {
        this.isPlaying = false;
        document.getElementById('playIcon').style.display = 'block';
        document.getElementById('pauseIcon').style.display = 'none';
        if (window.Engagement) window.Engagement.track('audio_complete', { section_id: window.AudioSync?.currentSectionId || null, duration_seconds: Math.round(this.audioPlayer?.duration || 0) });
    },

    // Reading Progress
    initReadingProgress() {
        const progressFill = document.getElementById('readingProgressFill');

        window.addEventListener('scroll', () => {
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = (window.scrollY / scrollHeight) * 100;
            if (progressFill) {
                progressFill.style.width = progress + '%';
            }
        });
    },
    
    // Font Controls
    // Delegates entirely to WopFontSize (font-size.js) which is loaded
    // globally in base.njk and applies font size to <html> via rem.
    // The bottom-toolbar A- / A / A+ buttons on chapter pages are wired
    // by WopFontSize.init() via their IDs (wopFontDecrease / wopFontReset
    // / wopFontIncrease). The legacy #fontDecrease/#fontReset/#fontIncrease
    // IDs in bottom-toolbar.njk are kept as aliases and wired here.
    initFontControls() {
        document.getElementById('fontDecrease')?.addEventListener('click', () => WopFontSize.decrease());
        document.getElementById('fontReset')   ?.addEventListener('click', () => WopFontSize.reset());
        document.getElementById('fontIncrease')?.addEventListener('click', () => WopFontSize.increase());
    },
    
    // Bookmarking
    initBookmark() {
        const bookmarkBtn = document.getElementById('bookmarkBtn');
        const chapterId = this.config.id;

        // Restore active state if bookmark flag is already set
        try {
            if (localStorage.getItem(`wop-bookmark-flag-${chapterId}`) === 'true') {
                bookmarkBtn?.classList.add('active');
            }
        } catch (e) { /* silent */ }

        bookmarkBtn?.addEventListener('click', () => this.toggleBookmark());
    },

    toggleBookmark() {
        const chapterId = this.config.id;
        const btn = document.getElementById('bookmarkBtn');

        let isBookmarked = false;
        try {
            isBookmarked = localStorage.getItem(`wop-bookmark-flag-${chapterId}`) === 'true';
        } catch (e) { /* silent */ }

        const nowBookmarked = !isBookmarked;
        if (nowBookmarked && window.Engagement) window.Engagement.track('bookmark', {});

        if (nowBookmarked) {
            // Save scroll position (used by resume prompt)
            try {
                localStorage.setItem(`wop-bookmark-${chapterId}`, JSON.stringify({
                    position: window.scrollY,
                    timestamp: Date.now()
                }));
            } catch (e) { /* silent */ }
        } else {
            // Remove scroll position when unbookmarking
            try {
                localStorage.removeItem(`wop-bookmark-${chapterId}`);
            } catch (e) { /* silent */ }
        }

        try {
            localStorage.setItem(`wop-bookmark-flag-${chapterId}`, nowBookmarked ? 'true' : 'false');
        } catch (e) { /* silent */ }

        btn?.classList.toggle('active', nowBookmarked);
        document.dispatchEvent(new CustomEvent('wop:bookmark-changed', { detail: { chapterId, bookmarked: nowBookmarked } }));
    },

    // kept for any legacy callers — delegates to toggleBookmark
    saveBookmark() {
        this.toggleBookmark();
    },

    // ── MARK COMPLETE ──────────────────────────────────────
    initComplete() {
        const btn = document.getElementById('completeBtn');
        const chapterId = this.config.id;

        // Restore saved state on load
        try {
            if (localStorage.getItem(`wop-complete-${chapterId}`) === 'true') {
                btn?.classList.add('active');
            }
        } catch (e) { /* silent */ }

        btn?.addEventListener('click', () => this.toggleComplete());
    },

    toggleComplete() {
        const chapterId = this.config.id;
        const btn = document.getElementById('completeBtn');

        let isComplete = false;
        try {
            isComplete = localStorage.getItem(`wop-complete-${chapterId}`) === 'true';
        } catch (e) { /* silent */ }

        const nowComplete = !isComplete;
        if (nowComplete && window.Engagement) window.Engagement.track('complete', {});

        try {
            localStorage.setItem(`wop-complete-${chapterId}`, nowComplete ? 'true' : 'false');
        } catch (e) { /* silent */ }

        btn?.classList.toggle('active', nowComplete);
        document.dispatchEvent(new CustomEvent('wop:complete-changed', { detail: { chapterId, complete: nowComplete } }));
    },
    
    getBookmark() {
        const chapterId = this.config.id;
        const data = localStorage.getItem(`wop-bookmark-${chapterId}`);
        return data ? JSON.parse(data) : null;
    },

    // Share
    initShare() {
        const shareBtn = document.getElementById('shareBtn');

        shareBtn?.addEventListener('click', async () => {
            const shareData = {
                title: document.title,
                url: window.location.href
            };

            try {
                if (navigator.share) {
                    await navigator.share(shareData);
                } else {
                    await navigator.clipboard.writeText(window.location.href);
                    this.showShareFeedback(shareBtn);
                }
            } catch (err) {
                // User cancelled share dialog or clipboard failed
                if (err.name !== 'AbortError') {
                    await navigator.clipboard.writeText(window.location.href);
                    this.showShareFeedback(shareBtn);
                }
            }
        });
    },

    showShareFeedback(btn) {
        const originalText = btn.querySelector('span')?.textContent;
        const span = btn.querySelector('span');
        if (span) {
            span.textContent = 'Copied!';
            setTimeout(() => { span.textContent = originalText; }, 2000);
        }
    },

    // Floating Action Bar
    initFloatingActionBar() {
        const bar = document.getElementById('floatingActionBar');
        const dropdownBtn = document.getElementById('btnLearningTools');
        const dropdown = document.getElementById('featuresDropdown');

        // Bottom Learning Tools dropdown
        const bottomBtn = document.getElementById('btnLearningToolsBottom');
        const bottomDropdown = document.getElementById('bottomFeaturesDropdown');

        // Toggle top dropdown
        dropdownBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            bottomDropdown?.classList.remove('open');
            dropdown?.classList.toggle('open');
        });

        // Toggle bottom dropdown
        bottomBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown?.classList.remove('open');
            bottomDropdown?.classList.toggle('open');
        });

        // Close all dropdowns on outside click
        document.addEventListener('click', () => {
            dropdown?.classList.remove('open');
            bottomDropdown?.classList.remove('open');
        });

        // Handle dropdown items (top)
        dropdown?.querySelectorAll('[data-action]').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                this.handleFeatureAction(action);
                dropdown.classList.remove('open');
            });
        });

        // Handle dropdown items (bottom)
        bottomDropdown?.querySelectorAll('[data-action]').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                this.handleFeatureAction(action);
                bottomDropdown.classList.remove('open');
            });
        });
    },
    
    handleFeatureAction(action) {
        switch (action) {
            case 'overview':
                this.openModal('overviewModal');
                break;
            case 'testimony':
                this.openModal('testimonyModal');
                break;
            case 'infographic':
                this.openModal('infographicModal');
                break;
            case 'slides':
                this.openModal('slidesModal');
                break;
            case 'toc':
                this.openMobileTOC();
                break;
            case 'reflect':
                var pp = document.querySelector('.pause-point');
                if (pp) {
                    pp.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    document.getElementById('reflectionSection')?.scrollIntoView({ behavior: 'smooth' });
                }
                break;
        }
    },

    // Table of Contents
    initTOC() {
        const tocLinks = document.querySelectorAll('.toc-link');

        tocLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').slice(1);
                const target = document.getElementById(targetId);

                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }

                // Close mobile TOC if open
                this.closeMobileTOC();
            });
        });

        // Close button
        document.getElementById('tocMobileClose')?.addEventListener('click', () => this.closeMobileTOC());

        // Overlay click to close
        document.getElementById('tocMobileOverlay')?.addEventListener('click', () => this.closeMobileTOC());
    },
    
    openMobileTOC() {
        document.getElementById('tocMobilePanel')?.classList.add('open');
        document.getElementById('tocMobileOverlay')?.classList.add('visible');
    },
    
    closeMobileTOC() {
        document.getElementById('tocMobilePanel')?.classList.remove('open');
        document.getElementById('tocMobileOverlay')?.classList.remove('visible');
    },
    
    // Modals
    initModals() {
        const backdrop = document.getElementById('modalBackdrop');
        
        // Close buttons
        document.querySelectorAll('[data-modal-close]').forEach(btn => {
            btn.addEventListener('click', () => this.closeAllModals());
        });
        
        // Backdrop click
        backdrop?.addEventListener('click', () => this.closeAllModals());
        
        // Escape key + arrow key slide navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
            if (document.getElementById('slidesModal')?.classList.contains('open')) {
                if (e.key === 'ArrowLeft')  { e.preventDefault(); this.navigateSlide(-1); }
                if (e.key === 'ArrowRight') { e.preventDefault(); this.navigateSlide(1);  }
            }
        });
        
        // Resource cards
        document.querySelectorAll('[data-modal]').forEach(card => {
            card.addEventListener('click', () => {
                const modalId = card.dataset.modal + 'Modal';
                this.openModal(modalId);
            });
        });
    },
    
    openModal(modalId) {
        document.getElementById(modalId)?.classList.add('open');
        document.getElementById('modalBackdrop')?.classList.add('visible');
        document.body.style.overflow = 'hidden';
        if (window.Engagement) window.Engagement.track('modal_open', { modal_type: modalId.replace('Modal', '') });
    },
    
    closeAllModals() {
        // Exit browser fullscreen if active
        const fsElement = document.fullscreenElement || document.webkitFullscreenElement;
        if (fsElement) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
        }

        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('open');
        });
        document.getElementById('modalBackdrop')?.classList.remove('visible');
        document.body.style.overflow = '';

        // Pause any playing audio
        document.querySelectorAll('.modal audio').forEach(audio => {
            audio.pause();
        });
    },
    
    // Hash-based modal routing (for deep links from interactive gateway)
    checkHashRoute() {
        const hash = window.location.hash;
        const hashMap = {
            '#open-slides': 'slidesModal',
            '#open-testimony': 'testimonyModal',
            '#open-podcast': 'overviewModal',
            '#open-infographic': 'infographicModal'
        };
        const modalId = hashMap[hash];
        if (modalId) {
            // Small delay to ensure modals are fully initialized
            setTimeout(() => this.openModal(modalId), 300);
            // Clean hash from URL without scrolling
            history.replaceState(null, '', window.location.pathname);
        }
    },

    // Slides Carousel
    initSlides() {
        const prevBtn = document.getElementById('slidePrev');
        const nextBtn = document.getElementById('slideNext');
        const fullscreenBtn = document.getElementById('slidesFullscreen');

        this.currentSlide = 1;
        this.totalSlides = this.config.totalSlides || 10;

        prevBtn?.addEventListener('click', () => this.navigateSlide(-1));
        nextBtn?.addEventListener('click', () => this.navigateSlide(1));
        fullscreenBtn?.addEventListener('click', () => this.toggleSlidesFullscreen());

        // Mouse wheel navigation (only when slides modal is open)
        document.getElementById('slidesCarousel')?.addEventListener('wheel', (e) => {
            e.preventDefault();
            this.navigateSlide(e.deltaY > 0 ? 1 : -1);
        }, { passive: false });

        // Listen for fullscreen change (Escape key, browser controls, etc.)
        document.addEventListener('fullscreenchange', () => this.onFullscreenChange());
        document.addEventListener('webkitfullscreenchange', () => this.onFullscreenChange());

        this.updateSlideImage();
    },

    toggleSlidesFullscreen() {
        const modal = document.getElementById('slidesModal');
        if (!modal) return;

        const fsElement = document.fullscreenElement || document.webkitFullscreenElement;

        if (fsElement) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
        } else {
            if (modal.requestFullscreen) {
                modal.requestFullscreen();
            } else if (modal.webkitRequestFullscreen) {
                modal.webkitRequestFullscreen();
            }
        }
    },

    onFullscreenChange() {
        const btn = document.getElementById('slidesFullscreen');
        if (!btn) return;

        const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
        btn.querySelector('.icon-expand').style.display = isFullscreen ? 'none' : '';
        btn.querySelector('.icon-collapse').style.display = isFullscreen ? '' : 'none';
    },
    
    navigateSlide(direction) {
        this.currentSlide += direction;
        
        if (this.currentSlide < 1) this.currentSlide = this.totalSlides;
        if (this.currentSlide > this.totalSlides) this.currentSlide = 1;
        
        this.updateSlideImage();
    },
    
    updateSlideImage() {
        const slideNum = String(this.currentSlide).padStart(2, '0');
        // Slides use subdirectory convention: /assets/slides/chapter-01/slide-01.png
        // slidesPath should end with / (e.g. "chapter-01/")
        // Legacy flat prefix support retained: prefix_01.png (slidesPath without trailing /)
        const slidesPath = this.config.slidesPath;
        let path;
        if (slidesPath.endsWith('/')) {
            path = `${slidesPath}slide-${slideNum}.png`;
        } else {
            path = `${slidesPath}_${slideNum}.png`;
        }

        document.getElementById('currentSlide').src = path;
        document.getElementById('slideCurrentNum').textContent = this.currentSlide;
    },
    
    // Back to Top
    initBackToTop() {
        const btn = document.getElementById('backToTop');
        
        window.addEventListener('scroll', () => {
            if (window.scrollY > 500) {
                btn?.classList.add('visible');
            } else {
                btn?.classList.remove('visible');
            }
        });
        
        btn?.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    },
    
    // Mobile FAB Bottom Sheet
    initMobileFAB() {
        const fab = document.getElementById('fabLantern');
        const sheet = document.getElementById('fabSheet');
        const overlay = document.getElementById('fabSheetOverlay');
        const closeBtn = document.getElementById('fabSheetClose');

        const openSheet = () => {
            sheet?.classList.add('open');
            overlay?.classList.add('open');
            document.body.style.overflow = 'hidden';
        };

        const closeSheet = () => {
            sheet?.classList.remove('open');
            overlay?.classList.remove('open');
            document.body.style.overflow = '';
        };

        fab?.addEventListener('click', openSheet);
        overlay?.addEventListener('click', closeSheet);
        closeBtn?.addEventListener('click', closeSheet);

        sheet?.querySelectorAll('[data-action]').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                closeSheet();
                this.handleFABAction(action);
            });
        });
    },
    
    handleFABAction(action) {
        switch (action) {
            case 'listen':
                this.showAudioPlayer();
                break;
            case 'overview':
                this.openModal('overviewModal');
                break;
            case 'testimony':
                this.openModal('testimonyModal');
                break;
            case 'infographic':
                this.openModal('infographicModal');
                break;
            case 'slides':
                this.openModal('slidesModal');
                break;
            case 'toc':
                this.openMobileTOC();
                break;
            case 'reflect':
                var pp = document.querySelector('.pause-point');
                if (pp) {
                    pp.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    document.getElementById('reflectionSection')?.scrollIntoView({ behavior: 'smooth' });
                }
                break;
        }
    },

    // Resume Prompt (localStorage-based, for anonymous users only)
    initResumePrompt() {
        if (window.API?.isAuthenticated()) return;

        const bookmark = this.getBookmark();

        if (bookmark && bookmark.position > 500) {
            this.showResumePrompt(bookmark.position);
        }
    },
    
    showResumePrompt(position) {
        const prompt = document.getElementById('resumePrompt');
        const yesBtn = document.getElementById('resumeYes');
        const noBtn = document.getElementById('resumeNo');
        const reflectBtn = document.getElementById('resumeReflect');

        prompt.style.display = 'block';

        yesBtn?.addEventListener('click', () => {
            window.scrollTo({ top: position, behavior: 'smooth' });
            this.hideResumePrompt();
        });

        noBtn?.addEventListener('click', () => {
            this.hideResumePrompt();
        });

        reflectBtn?.addEventListener('click', () => {
            this.hideResumePrompt();
            document.getElementById('reflectionSection')?.scrollIntoView({ behavior: 'smooth' });
            setTimeout(() => document.getElementById('reflection1')?.focus(), 800);
        });

        // Auto-dismiss after 8 seconds
        setTimeout(() => this.hideResumePrompt(), 8000);
    },
    
    hideResumePrompt() {
        const prompt = document.getElementById('resumePrompt');
        prompt.style.display = 'none';
    },

    // Reflections
    initReflections() {
        if (typeof Reflections !== 'undefined' && this.config.id) {
            Reflections.init(this.config.id);
        }
    },

    // Reading Progress Sync
    initReadingProgressSync() {
        if (typeof ReadingProgress !== 'undefined') {
            ReadingProgress.init(this.config);
        }
    },

    // Scripture auto-linking
    linkScriptures() {
        if (!window.WOP_SCRIPTURE_BOOKS) {
            console.warn('WOP_SCRIPTURE_BOOKS not defined — scripture auto-linking disabled');
            return;
        }
        const bookMappings = window.WOP_SCRIPTURE_BOOKS || {};

        const bookNames = Object.keys(bookMappings).sort((a, b) => b.length - a.length);
        const bookPattern = bookNames.map(b => b.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
        const regex = new RegExp('(?<!<a[^>]*>)\\b(' + bookPattern + ')\\s+(\\d+):(\\d+)(?:[-–](\\d+))?\\b', 'gi');

        const baseUrl = 'https://www.churchofjesuschrist.org/study/scriptures';

        const content = document.querySelector('.chapter-body') || document.querySelector('.chapter-content');
        if (!content) return;

        const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, null);
        const textNodes = [];
        let node;
        while ((node = walker.nextNode())) {
            if (node.parentElement && node.parentElement.closest('a, script, style, .scripture-link')) continue;
            if (regex.test(node.textContent)) {
                textNodes.push(node);
            }
            regex.lastIndex = 0;
        }

        textNodes.forEach(textNode => {
            const frag = document.createDocumentFragment();
            let lastIndex = 0;
            let match;
            regex.lastIndex = 0;

            while ((match = regex.exec(textNode.textContent)) !== null) {
                if (match.index > lastIndex) {
                    frag.appendChild(document.createTextNode(textNode.textContent.slice(lastIndex, match.index)));
                }

                const bookKey = match[1].toLowerCase().trim();
                const chapter = match[2];
                const verseStart = match[3];
                const verseEnd = match[4];
                const bookPath = bookMappings[bookKey];

                if (bookPath) {
                    const verseParam = verseEnd
                        ? `p${verseStart}-p${verseEnd}`
                        : `p${verseStart}`;
                    const url = `${baseUrl}/${bookPath}/${chapter}?lang=eng&id=${verseParam}#${verseParam}`;

                    const link = document.createElement('a');
                    link.href = url;
                    link.className = 'scripture-link';
                    link.target = '_blank';
                    link.rel = 'noopener';
                    link.textContent = match[0];
                    frag.appendChild(link);
                } else {
                    frag.appendChild(document.createTextNode(match[0]));
                }

                lastIndex = match.index + match[0].length;
            }

            if (lastIndex < textNode.textContent.length) {
                frag.appendChild(document.createTextNode(textNode.textContent.slice(lastIndex)));
            }

            textNode.parentNode.replaceChild(frag, textNode);
        });
    }
};

// Export for use in templates
window.ChapterManager = ChapterManager;

/* ═══════════════════════════════════════════════
   REFLECT · JOURNAL · WITNESS — PAUSE-POINT SYSTEM
   ═══════════════════════════════════════════════ */

/**
 * R·J·W Pause-Point System
 * Manages the Reflect / Journal / Witness modal panel.
 * PAUSES data is injected at build time via window.WOP_PAUSES
 * in chapter.njk from each chapter's frontmatter `pauses` array.
 */
const RJW = (function() {

    /* ── PAUSES DATA ──────────────────────────────────── */
    // Populated from frontmatter at build time.
    // window.WOP_PAUSES is an array; convert to an object keyed by id.
    function loadPauses() {
        const raw = window.WOP_PAUSES || [];
        const map = {};
        if (Array.isArray(raw)) {
            raw.forEach(function(p) { map[p.id] = p; });
        } else if (typeof raw === 'object') {
            // If already an object (shouldn't happen, but be safe)
            Object.assign(map, raw);
        }
        return map;
    }

    let PAUSES = {};

    /* ── STATE ────────────────────────────────────────── */
    let activePauseId = null;
    let activeTabKey  = null;
    let reflectMode   = 'universal';   // 'universal' | 'chapter'

    /* ── LOCAL STORAGE PERSISTENCE ────────────────────── */
    const STORAGE_PREFIX = 'wop-rjw-';

    function storageKey(pauseId, tabKey) {
        return STORAGE_PREFIX + pauseId + '::' + tabKey;
    }

    function loadStored(pauseId, tabKey) {
        try {
            return localStorage.getItem(storageKey(pauseId, tabKey)) || '';
        } catch (e) {
            return '';
        }
    }

    function saveStored(pauseId, tabKey, value) {
        try {
            localStorage.setItem(storageKey(pauseId, tabKey), value);
        } catch (e) {
            // localStorage full or unavailable — silent fail
        }
    }

    function loadStoredBool(pauseId, key) {
        try {
            return localStorage.getItem(storageKey(pauseId, key)) === 'true';
        } catch (e) {
            return false;
        }
    }

    function saveStoredBool(pauseId, key, value) {
        try {
            localStorage.setItem(storageKey(pauseId, key), value ? 'true' : 'false');
        } catch (e) {
            // silent
        }
    }

    function getChapterSlug() {
        return (typeof CHAPTER_CONFIG !== 'undefined' && CHAPTER_CONFIG.id) || '';
    }

    /* ── RENDER MODAL CONTENT ─────────────────────────── */
    function renderModal(pauseId, tabKey) {
        var data = PAUSES[pauseId];
        if (!data) return;
        var tabData = data[tabKey] || {};

        document.getElementById('rjwSectionTitle').textContent = data.title || '';

        // Highlight active tab button
        ['reflect','journal','witness'].forEach(function(k) {
            var btn = document.querySelector('.rjw-tab-btn.' + k);
            if (btn) btn.classList.toggle('active', k === tabKey);
        });

        // REFLECT TAB — populate both prompt blocks, show active mode
        if (tabKey === 'reflect') {
            var chapterPrompt = (data.reflect && data.reflect.prompt) ? data.reflect.prompt : '';
            document.getElementById('reflect-prompt-chapter').innerHTML = chapterPrompt;
            applyReflectMode();
        }

        // JOURNAL & WITNESS — fill single prompt block
        if (tabKey === 'journal') {
            document.getElementById('journal-prompt').innerHTML = tabData.prompt || '';
        }
        if (tabKey === 'witness') {
            document.getElementById('witness-prompt').innerHTML = tabData.prompt || '';
            var cardsEl = document.getElementById('witness-cards');
            cardsEl.innerHTML = '';
            if (tabData.cards && tabData.cards.length) {
                tabData.cards.forEach(function(c) {
                    cardsEl.innerHTML += '<div class="witness-card"><p>' + c.text + '</p><span class="witness-meta">— ' + c.meta + '</span></div>';
                });
            }
        }

        // Show correct pane
        document.querySelectorAll('.rjw-body .tab-pane').forEach(function(p) {
            p.classList.remove('active');
        });
        var pane = document.getElementById('tab-' + tabKey);
        if (pane) pane.classList.add('active');

        // Restore saved text
        var ta = document.getElementById(tabKey + '-ta');
        if (ta) ta.value = loadStored(pauseId, tabKey);

        // Restore checkbox states for witness
        if (tabKey === 'witness') {
            var cbDoc  = document.getElementById('cb-document');
            var cbComm = document.getElementById('cb-community');
            if (cbDoc)  cbDoc.checked  = loadStoredBool(pauseId, 'witness-include-document');
            if (cbComm) cbComm.checked = loadStoredBool(pauseId, 'witness-submit-community');
        }
    }

    /* ── REFLECT MODE TOGGLE ──────────────────────────── */
    function switchReflectMode(mode) {
        reflectMode = mode;
        applyReflectMode();
    }

    function applyReflectMode() {
        var universalBlock = document.getElementById('reflect-prompt-universal');
        var chapterBlock   = document.getElementById('reflect-prompt-chapter');
        var btnUniversal   = document.getElementById('toggle-universal');
        var btnChapter     = document.getElementById('toggle-chapter');

        var showUniversal = (reflectMode === 'universal');
        if (universalBlock) universalBlock.style.display = showUniversal ? '' : 'none';
        if (chapterBlock)   chapterBlock.style.display   = showUniversal ? 'none' : '';
        if (btnUniversal)   btnUniversal.classList.toggle('active', showUniversal);
        if (btnChapter)     btnChapter.classList.toggle('active', !showUniversal);
    }

    /* ── OPEN ─────────────────────────────────────────── */
    function openModal(pauseId, tabKey) {
        PAUSES = loadPauses();  // ensure latest data
        activePauseId = pauseId;
        activeTabKey  = tabKey;
        reflectMode   = 'universal';
        renderModal(pauseId, tabKey);
        document.getElementById('rjwOverlay').classList.add('open');
        document.getElementById('rjwPanel').classList.add('open');
        document.body.style.overflow = 'hidden';
        if (window.Engagement) window.Engagement.track('rjw_open', { pause_id: pauseId, tab: tabKey });
    }

    /* ── CLOSE — saves current text, NEVER clears it ──── */
    function closeModal() {
        persistCurrent();
        document.getElementById('rjwOverlay').classList.remove('open');
        document.getElementById('rjwPanel').classList.remove('open');
        document.body.style.overflow = '';

        // Advance to next section if using section-based audio architecture
        if (window.AudioSync && typeof window.AudioSync.advanceSection === 'function') {
            if (window.AudioSync.state === 'RJW_OPEN') {
                window.AudioSync.advanceSection();
            }
        }
    }

    /* ── SWITCH TAB ────────────────────────────────────── */
    function switchTab(tabKey) {
        if (!activePauseId) return;
        persistCurrent();
        activeTabKey = tabKey;
        renderModal(activePauseId, tabKey);
    }

    /* ── PERSIST ───────────────────────────────────────── */
    function persistCurrent() {
        if (!activePauseId || !activeTabKey) return;
        var ta = document.getElementById(activeTabKey + '-ta');
        if (ta) saveStored(activePauseId, activeTabKey, ta.value);
    }

    /* ── SAVE BUTTON ───────────────────────────────────── */
    function saveResponse(tabKey) {
        var ta = document.getElementById(tabKey + '-ta');
        if (ta && activePauseId) {
            saveStored(activePauseId, tabKey, ta.value);

            if (tabKey === 'witness') {
                var cbDoc  = document.getElementById('cb-document');
                var cbComm = document.getElementById('cb-community');
                saveStoredBool(activePauseId, 'witness-include-document',  cbDoc  ? cbDoc.checked  : false);
                saveStoredBool(activePauseId, 'witness-submit-community', cbComm ? cbComm.checked : false);
            }

            // Sync to backend if authenticated
            if (window.API && API.isAuthenticated() && ta.value.trim()) {
                var payload = {
                    pause_id: activePauseId,
                    chapter_slug: getChapterSlug(),
                    tab_type: tabKey,
                    response_text: ta.value,
                    include_in_document: false
                };
                if (tabKey === 'witness') {
                    var cbDocSync = document.getElementById('cb-document');
                    payload.include_in_document = cbDocSync ? cbDocSync.checked : false;
                }
                API.savePauseResponse(payload).catch(function(err) {
                    console.warn('[RJW] Backend save failed (will retry on next login):', err.message);
                });
            }
        }
        if (window.Engagement) window.Engagement.track('rjw_save', { pause_id: activePauseId, tab: tabKey });
        var ind = document.getElementById('save-' + tabKey);
        if (ind) {
            ind.classList.add('visible');
            setTimeout(function() { ind.classList.remove('visible'); }, 2200);
        }
    }

    function flushQueue() {
        var slug = getChapterSlug();
        if (!slug) return;  // not on a chapter page
        if (!window.API || !API.isAuthenticated()) return;

        var prefix = STORAGE_PREFIX;
        var keys = [];
        for (var i = 0; i < localStorage.length; i++) {
            var k = localStorage.key(i);
            if (k && k.indexOf(prefix) === 0) keys.push(k);
        }

        keys.forEach(function(key) {
            var val = '';
            try { val = localStorage.getItem(key) || ''; } catch(e) { return; }
            if (!val.trim() || val === 'true' || val === 'false') return;  // skip booleans and empty

            // Parse key: wop-rjw-{pauseId}::{tabKey}
            var remainder = key.substring(prefix.length);
            var parts = remainder.split('::');
            if (parts.length !== 2) return;
            var pauseId = parts[0];
            var tabKey = parts[1];
            if (['reflect','journal','witness'].indexOf(tabKey) === -1) return;

            var payload = {
                pause_id: pauseId,
                chapter_slug: slug,
                tab_type: tabKey,
                response_text: val,
                include_in_document: false
            };

            if (tabKey === 'witness') {
                try {
                    payload.include_in_document = localStorage.getItem(prefix + pauseId + '::witness-include-document') === 'true';
                } catch(e) { /* silent */ }
            }

            API.savePauseResponse(payload).catch(function(err) {
                console.warn('[RJW] Flush failed for', pauseId, tabKey, err.message);
            });
        });
    }

    /* ── CLEAR BUTTON ──────────────────────────────────── */
    function clearTA(tabKey) {
        var ta = document.getElementById(tabKey + '-ta');
        if (ta) ta.value = '';
        if (activePauseId) saveStored(activePauseId, tabKey, '');
    }

    /* ── KEYBOARD ──────────────────────────────────────── */
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
    });

    /* ── PUBLIC API ────────────────────────────────────── */
    return {
        openModal: openModal,
        closeModal: closeModal,
        switchTab: switchTab,
        switchReflectMode: switchReflectMode,
        saveResponse: saveResponse,
        clearTA: clearTA,
        flushQueue: flushQueue
    };

})();

// Export for global use
window.RJW = RJW;
