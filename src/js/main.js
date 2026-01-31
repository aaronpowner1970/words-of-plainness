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

    function openMobileMenu() {
        toggle?.classList.add('active');
        menu?.classList.add('active');
        overlay?.classList.add('active');
        toggle?.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileMenu() {
        toggle?.classList.remove('active');
        menu?.classList.remove('active');
        overlay?.classList.remove('active');
        toggle?.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    }

    function toggleMobileMenu(e) {
        e.preventDefault();
        e.stopPropagation();
        if (menu?.classList.contains('active')) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    }

    // Toggle button (hamburger / X)
    toggle?.addEventListener('click', toggleMobileMenu);

    // Close button inside menu header
    closeBtn?.addEventListener('click', closeMobileMenu);

    // Close on overlay tap
    overlay?.addEventListener('click', closeMobileMenu);

    // Close on menu link tap
    menu?.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', closeMobileMenu);
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && menu?.classList.contains('active')) {
            closeMobileMenu();
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
