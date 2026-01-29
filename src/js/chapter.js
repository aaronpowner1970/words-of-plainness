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
        this.initShare();
        this.initFloatingActionBar();
        this.initTOC();
        this.initModals();
        this.initSlides();
        this.initBackToTop();
        this.initMobileFAB();
        this.initResumePrompt();
        this.initReflections();

        console.log('ChapterManager initialized for:', config.title);
    },
    
    // Audio Sync (sentence highlighting + click-to-seek)
    initAudioSync() {
        if (typeof AudioSync !== 'undefined' && this.config.timestamps) {
            const audio = document.getElementById('chapterAudio');
            AudioSync.init(this.config.timestamps, audio);
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
    },
    
    pause() {
        this.audioPlayer?.pause();
        this.isPlaying = false;
        document.getElementById('playIcon').style.display = 'block';
        document.getElementById('pauseIcon').style.display = 'none';
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
    initFontControls() {
        const content = document.querySelector('.chapter-content');
        const decreaseBtn = document.getElementById('fontDecrease');
        const resetBtn = document.getElementById('fontReset');
        const increaseBtn = document.getElementById('fontIncrease');
        
        let fontSize = parseFloat(localStorage.getItem('wop-font-size')) || 1.125;
        this.applyFontSize(fontSize);
        
        decreaseBtn?.addEventListener('click', () => this.changeFontSize(-0.125));
        resetBtn?.addEventListener('click', () => this.setFontSize(1.125));
        increaseBtn?.addEventListener('click', () => this.changeFontSize(0.125));
    },
    
    changeFontSize(delta) {
        const content = document.querySelector('.chapter-content');
        if (!content) return;
        
        let current = parseFloat(content.style.fontSize) || 1.125;
        this.setFontSize(Math.max(0.875, Math.min(1.5, current + delta)));
    },
    
    setFontSize(size) {
        const content = document.querySelector('.chapter-content');
        if (!content) return;
        
        content.style.fontSize = size + 'rem';
        localStorage.setItem('wop-font-size', size);
    },
    
    applyFontSize(size) {
        const content = document.querySelector('.chapter-content');
        if (content) {
            content.style.fontSize = size + 'rem';
        }
    },
    
    // Bookmarking
    initBookmark() {
        const bookmarkBtn = document.getElementById('bookmarkBtn');
        
        bookmarkBtn?.addEventListener('click', () => this.saveBookmark());
    },
    
    saveBookmark() {
        const scrollPos = window.scrollY;
        const chapterId = this.config.id;
        
        localStorage.setItem(`wop-bookmark-${chapterId}`, JSON.stringify({
            position: scrollPos,
            timestamp: Date.now()
        }));
        
        // Visual feedback
        const btn = document.getElementById('bookmarkBtn');
        btn?.classList.add('saved');
        setTimeout(() => btn?.classList.remove('saved'), 2000);
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
        const dropdownBtn = document.getElementById('btnOtherFeatures');
        const dropdown = document.getElementById('featuresDropdown');
        
        // Toggle dropdown
        dropdownBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown?.classList.toggle('open');
        });
        
        // Close dropdown on outside click
        document.addEventListener('click', () => {
            dropdown?.classList.remove('open');
        });
        
        // Handle dropdown items
        dropdown?.querySelectorAll('[data-action]').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                this.handleFeatureAction(action);
                dropdown.classList.remove('open');
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
                document.getElementById('reflectionSection')?.scrollIntoView({ behavior: 'smooth' });
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
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
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
        // Support two naming conventions:
        // 1. Subdirectory: /assets/slides/chapter-02/slide-01.png (slidesPath ends with /)
        // 2. Flat prefix:  /assets/slides/WoP_Ch01_01.png (slidesPath ends without /)
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
    
    // Mobile FAB
    initMobileFAB() {
        const fab = document.getElementById('fabLantern');
        const menu = document.getElementById('fabMenu');
        
        fab?.addEventListener('click', () => {
            menu?.classList.toggle('open');
            fab?.classList.toggle('active');
        });
        
        menu?.querySelectorAll('[data-action]').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                this.handleFABAction(action);
                menu.classList.remove('open');
                fab?.classList.remove('active');
            });
        });
    },
    
    handleFABAction(action) {
        switch (action) {
            case 'listen':
                this.showAudioPlayer();
                break;
            case 'toc':
                this.openMobileTOC();
                break;
            case 'resources':
                document.getElementById('studyResources')?.scrollIntoView({ behavior: 'smooth' });
                break;
        }
    },
    
    // Resume Prompt
    initResumePrompt() {
        const bookmark = this.getBookmark();
        
        if (bookmark && bookmark.position > 500) {
            this.showResumePrompt(bookmark.position);
        }
    },
    
    showResumePrompt(position) {
        const prompt = document.getElementById('resumePrompt');
        const yesBtn = document.getElementById('resumeYes');
        const noBtn = document.getElementById('resumeNo');
        
        prompt.style.display = 'block';
        
        yesBtn?.addEventListener('click', () => {
            window.scrollTo({ top: position, behavior: 'smooth' });
            this.hideResumePrompt();
        });
        
        noBtn?.addEventListener('click', () => {
            this.hideResumePrompt();
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
    }
};

// Export for use in templates
window.ChapterManager = ChapterManager;
