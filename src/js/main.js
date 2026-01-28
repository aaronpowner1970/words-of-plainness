/**
 * WORDS OF PLAINNESS - Main Scripts
 * ==================================
 * 
 * Global JavaScript functionality used across all pages.
 * These scripts will be extracted from existing code during migration.
 */

// Mobile menu toggle
document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
    const mobileMenuClose = document.getElementById('mobileMenuClose');
    
    function openMobileMenu() {
        mobileMenu?.classList.add('open');
        mobileMenuOverlay?.classList.add('visible');
        document.body.style.overflow = 'hidden';
    }
    
    function closeMobileMenu() {
        mobileMenu?.classList.remove('open');
        mobileMenuOverlay?.classList.remove('visible');
        document.body.style.overflow = '';
    }
    
    mobileMenuToggle?.addEventListener('click', openMobileMenu);
    mobileMenuClose?.addEventListener('click', closeMobileMenu);
    mobileMenuOverlay?.addEventListener('click', closeMobileMenu);
    
    // Close menu on link click
    mobileMenu?.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', closeMobileMenu);
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

console.log('Words of Plainness - Main scripts loaded');
