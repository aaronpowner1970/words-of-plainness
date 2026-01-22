/* ============================================
   WORDS OF PLAINNESS - Main JavaScript
   A Christ-Centered Ministry
   ============================================ */

document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    initScrollEffects();
    initVideoBackground();
    initSmoothScroll();
});

/* --- Navigation --- */
function initNavigation() {
    const navToggle = document.querySelector('.nav-toggle');
    const mobileMenu = document.querySelector('.mobile-menu');
    const mobileMenuClose = document.querySelector('.mobile-menu-close');
    const mobileMenuLinks = document.querySelectorAll('.mobile-menu a');
    
    // Toggle mobile menu
    if (navToggle && mobileMenu) {
        navToggle.addEventListener('click', function() {
            this.classList.toggle('active');
            mobileMenu.classList.toggle('active');
            document.body.style.overflow = mobileMenu.classList.contains('active') ? 'hidden' : '';
        });
    }
    
    // Close button
    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', function() {
            closeMobileMenu();
        });
    }
    
    // Close menu when clicking a link
    mobileMenuLinks.forEach(link => {
        link.addEventListener('click', function() {
            closeMobileMenu();
        });
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && mobileMenu && mobileMenu.classList.contains('active')) {
            closeMobileMenu();
        }
    });
    
    // Close menu when clicking outside
    if (mobileMenu) {
        mobileMenu.addEventListener('click', function(e) {
            if (e.target === this) {
                closeMobileMenu();
            }
        });
    }
    
    function closeMobileMenu() {
        if (navToggle) navToggle.classList.remove('active');
        if (mobileMenu) mobileMenu.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    // Set active nav link based on current page
    setActiveNavLink();
}

function setActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-links a, .mobile-nav-list > li > a');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.includes(href) && href !== '/' && href !== 'index.html') {
            link.classList.add('active');
        } else if ((currentPath === '/' || currentPath.endsWith('index.html')) && 
                   (href === '/' || href === 'index.html' || href === './')) {
            link.classList.add('active');
        }
    });
}

/* --- Scroll Effects --- */
function initScrollEffects() {
    const header = document.querySelector('.header');
    let lastScroll = 0;
    
    if (!header) return;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        // Add scrolled class for background change
        if (currentScroll > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    }, { passive: true });
    
    // Intersection Observer for fade-in animations
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe elements with fade-in class
    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });
}

/* --- Video Background --- */
function initVideoBackground() {
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
    
    // Video ended - show static image or loop
    heroVideo.addEventListener('ended', function() {
        // Option 1: Loop (uncomment if you want continuous loop)
        // this.currentTime = 0;
        // this.play();
        
        // Option 2: Pause on last frame (current behavior)
        this.pause();
    });
}

/* --- Smooth Scroll --- */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if just "#"
            if (href === '#') return;
            
            const target = document.querySelector(href);
            
            if (target) {
                e.preventDefault();
                
                const headerHeight = document.querySelector('.header')?.offsetHeight || 0;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/* --- Utility Functions --- */

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Check if element is in viewport
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// Format date for display
function formatDate(date) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(date).toLocaleDateString('en-US', options);
}

/* --- Newsletter Form (if present) --- */
const newsletterForm = document.querySelector('.newsletter-form');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const emailInput = this.querySelector('input[type="email"]');
        const submitBtn = this.querySelector('button[type="submit"]');
        const email = emailInput?.value;
        
        if (!email) return;
        
        // Disable button during submission
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Subscribing...';
        }
        
        // Simulate form submission (replace with actual API call)
        setTimeout(() => {
            alert('Thank you for subscribing! You will receive updates from Words of Plainness.');
            if (emailInput) emailInput.value = '';
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Subscribe';
            }
        }, 1000);
    });
}

/* --- Contact Form (if present) --- */
const contactForm = document.querySelector('.contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const submitBtn = this.querySelector('button[type="submit"]');
        
        // Basic validation
        let isValid = true;
        this.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('error');
            } else {
                field.classList.remove('error');
            }
        });
        
        if (!isValid) {
            alert('Please fill in all required fields.');
            return;
        }
        
        // Disable button during submission
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending...';
        }
        
        // Simulate form submission (replace with actual API call)
        setTimeout(() => {
            alert('Thank you for your message! Brother Aaron will respond as soon as possible.');
            this.reset();
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send Message';
            }
        }, 1000);
    });
}

/* --- Search Functionality (placeholder) --- */
function initSearch() {
    const searchInput = document.querySelector('.search-input');
    const searchResults = document.querySelector('.search-results');
    
    if (!searchInput || !searchResults) return;
    
    searchInput.addEventListener('input', debounce(function() {
        const query = this.value.trim().toLowerCase();
        
        if (query.length < 2) {
            searchResults.innerHTML = '';
            searchResults.style.display = 'none';
            return;
        }
        
        // Placeholder: Replace with actual search API call
        searchResults.innerHTML = '<p class="search-loading">Searching...</p>';
        searchResults.style.display = 'block';
        
        // Simulated results
        setTimeout(() => {
            searchResults.innerHTML = `
                <p class="search-info">Search functionality will be connected to your writings database.</p>
            `;
        }, 500);
    }, 300));
}

// Initialize search if present
initSearch();
