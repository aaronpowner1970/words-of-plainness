/**
 * WORDS OF PLAINNESS - Main Scripts
 * ==================================
 * 
 * Global JavaScript functionality used across all pages.
 * These scripts will be extracted from existing code during migration.
 */

// Mobile menu toggle
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('mobileMenuToggle');
    const menu = document.getElementById('mobileMenu');
    const overlay = document.getElementById('mobileMenuOverlay');
    const closeBtn = document.getElementById('mobileMenuClose');

    function setMenuOpen(open) {
        requestAnimationFrame(() => {
            const action = open ? 'add' : 'remove';
            toggle?.classList[action]('active');
            menu?.classList[action]('active');
            overlay?.classList[action]('active');
            toggle?.setAttribute('aria-expanded', String(open));
            document.body.style.overflow = open ? 'hidden' : '';
        });
    }

    // Toggle button (hamburger / X)
    toggle?.addEventListener('click', () => {
        setMenuOpen(!menu?.classList.contains('active'));
    });

    // Close button inside menu header
    closeBtn?.addEventListener('click', () => setMenuOpen(false));

    // Close on overlay tap
    overlay?.addEventListener('click', () => setMenuOpen(false));

    // Close on menu link tap
    menu?.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => setMenuOpen(false));
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && menu?.classList.contains('active')) {
            setMenuOpen(false);
        }
    });
});

// Header scroll behavior
document.addEventListener('DOMContentLoaded', () => {
    const header = document.querySelector('.site-header');
    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > lastScroll && currentScroll > 100) {
            header?.classList.add('header-hidden');
        } else {
            header?.classList.remove('header-hidden');
        }
        
        lastScroll = currentScroll;
    });
});

// Video background for hero section
document.addEventListener('DOMContentLoaded', () => {
    const heroVideo = document.querySelector('.hero-video');
    const heroImage = document.querySelector('.hero-image');

    if (!heroVideo) return;

    // Check if we should show video (desktop) or image (mobile)
    function checkVideoDisplay() {
        const isMobile = window.innerWidth < 768;

        if (isMobile) {
            heroVideo.style.display = 'none';
            if (heroImage) heroImage.style.display = 'block';
        } else {
            heroVideo.style.display = 'block';
            if (heroImage) heroImage.style.display = 'none';

            // Attempt to play video
            heroVideo.play().catch(function(error) {
                console.log('Video autoplay prevented:', error);
                // Show fallback image if video can't play
                heroVideo.style.display = 'none';
                if (heroImage) heroImage.style.display = 'block';
            });
        }
    }

    // Check on load and resize
    checkVideoDisplay();

    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(checkVideoDisplay, 250);
    });

    // Video ended - pause on last frame (plays once, no loop)
    heroVideo.addEventListener('ended', function() {
        this.pause();
    });
});

console.log('Words of Plainness - Main scripts loaded');
