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

// Database Search FAB & Modal
document.addEventListener('DOMContentLoaded', function() {
  const fab = document.getElementById('searchFab');
  const modal = document.getElementById('searchModal');
  const closeBtn = document.getElementById('searchModalClose');
  const backdrop = document.getElementById('searchModalBackdrop');

  function openModal() {
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  fab?.addEventListener('click', openModal);
  closeBtn?.addEventListener('click', closeModal);
  backdrop?.addEventListener('click', closeModal);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.classList.contains('is-open')) {
      closeModal();
    }
  });
});

// Walkthrough Cards - Expand/Collapse (Accordion)
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.walkthrough-card');

    function closeAllCards() {
        cards.forEach(c => {
            c.classList.remove('is-open');
            const h = c.querySelector('.walkthrough-header');
            h?.setAttribute('aria-expanded', 'false');
        });
    }

    cards.forEach(card => {
        const header = card.querySelector('.walkthrough-header');

        header?.addEventListener('click', () => {
            const isOpen = card.classList.contains('is-open');

            // Close all cards first (accordion behavior)
            closeAllCards();

            // If this card wasn't open, open it
            if (!isOpen) {
                card.classList.add('is-open');
                header.setAttribute('aria-expanded', 'true');
            }
        });
    });

    // Handle deep linking - open card if URL has matching hash
    function openCardFromHash() {
        const hash = window.location.hash;
        if (hash) {
            const targetCard = document.querySelector(`.walkthrough-card${hash}`);
            if (targetCard) {
                // Open the card
                targetCard.classList.add('is-open');
                const header = targetCard.querySelector('.walkthrough-header');
                header?.setAttribute('aria-expanded', 'true');

                // Smooth scroll to card after a brief delay for layout
                setTimeout(() => {
                    targetCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            }
        }
    }

    // Check hash on load
    openCardFromHash();

    // Listen for hash changes
    window.addEventListener('hashchange', openCardFromHash);
});

console.log('Words of Plainness - Main scripts loaded');
