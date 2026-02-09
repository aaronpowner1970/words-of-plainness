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
        this.linkScriptures();
        this.initReadingProgressSync();

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
        document.dispatchEvent(new Event('wop:audio-play'));
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

        document.dispatchEvent(new Event('wop:bookmark-saved'));
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
                document.getElementById('reflectionSection')?.scrollIntoView({ behavior: 'smooth' });
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
        const bookMappings = {
            '1 nephi': 'bofm/1-ne', '2 nephi': 'bofm/2-ne', '3 nephi': 'bofm/3-ne', '4 nephi': 'bofm/4-ne',
            'jacob': 'bofm/jacob', 'enos': 'bofm/enos', 'jarom': 'bofm/jarom', 'omni': 'bofm/omni',
            'words of mormon': 'bofm/w-of-m', 'mosiah': 'bofm/mosiah', 'alma': 'bofm/alma',
            'helaman': 'bofm/hel', 'mormon': 'bofm/morm', 'ether': 'bofm/ether', 'moroni': 'bofm/moro',
            'd&c': 'dc-testament/dc', 'doctrine and covenants': 'dc-testament/dc',
            'moses': 'pgp/moses', 'abraham': 'pgp/abr',
            'joseph smith—matthew': 'pgp/js-m', 'joseph smith—history': 'pgp/js-h',
            'articles of faith': 'pgp/a-of-f',
            'genesis': 'ot/gen', 'exodus': 'ot/ex', 'leviticus': 'ot/lev', 'numbers': 'ot/num',
            'deuteronomy': 'ot/deut', 'joshua': 'ot/josh', 'judges': 'ot/judg', 'ruth': 'ot/ruth',
            '1 samuel': 'ot/1-sam', '2 samuel': 'ot/2-sam', '1 kings': 'ot/1-kgs', '2 kings': 'ot/2-kgs',
            '1 chronicles': 'ot/1-chr', '2 chronicles': 'ot/2-chr',
            'ezra': 'ot/ezra', 'nehemiah': 'ot/neh', 'esther': 'ot/esth',
            'job': 'ot/job', 'psalms': 'ot/ps', 'psalm': 'ot/ps',
            'proverbs': 'ot/prov', 'ecclesiastes': 'ot/eccl', 'song of solomon': 'ot/song',
            'isaiah': 'ot/isa', 'jeremiah': 'ot/jer', 'lamentations': 'ot/lam',
            'ezekiel': 'ot/ezek', 'daniel': 'ot/dan', 'hosea': 'ot/hosea', 'joel': 'ot/joel',
            'amos': 'ot/amos', 'obadiah': 'ot/obad', 'jonah': 'ot/jonah', 'micah': 'ot/micah',
            'nahum': 'ot/nahum', 'habakkuk': 'ot/hab', 'zephaniah': 'ot/zeph',
            'haggai': 'ot/hag', 'zechariah': 'ot/zech', 'malachi': 'ot/mal',
            'matthew': 'nt/matt', 'mark': 'nt/mark', 'luke': 'nt/luke', 'john': 'nt/john',
            'acts': 'nt/acts', 'romans': 'nt/rom',
            '1 corinthians': 'nt/1-cor', '2 corinthians': 'nt/2-cor',
            'galatians': 'nt/gal', 'ephesians': 'nt/eph', 'philippians': 'nt/philip',
            'colossians': 'nt/col', '1 thessalonians': 'nt/1-thes', '2 thessalonians': 'nt/2-thes',
            '1 timothy': 'nt/1-tim', '2 timothy': 'nt/2-tim', 'titus': 'nt/titus',
            'philemon': 'nt/philem', 'hebrews': 'nt/heb', 'james': 'nt/james',
            '1 peter': 'nt/1-pet', '2 peter': 'nt/2-pet',
            '1 john': 'nt/1-jn', '2 john': 'nt/2-jn', '3 john': 'nt/3-jn',
            'jude': 'nt/jude', 'revelation': 'nt/rev'
        };

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
