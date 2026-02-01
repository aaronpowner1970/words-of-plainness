/**
 * WORDS OF PLAINNESS - Authentication Modal
 * ==========================================
 * 
 * Handles the sign in/sign up modal UI.
 */

const AuthModal = {
    modal: null,
    form: null,
    mode: 'signin', // 'signin' or 'signup'
    
    init() {
        this.modal = document.getElementById('authModal');
        this.form = document.getElementById('authForm');
        
        this.setupTriggers();
        this.setupForm();
        this.setupModeSwitching();
        
        console.log('AuthModal initialized');
    },
    
    setupTriggers() {
        // Sign in button in header
        document.getElementById('signInBtn')?.addEventListener('click', () => {
            this.open('signin');
        });

        // Join Free button in header
        document.getElementById('joinFreeBtn')?.addEventListener('click', () => {
            this.open('signup');
        });

        // Mobile menu auth buttons
        document.getElementById('mobileSignIn')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.closeMobileMenu();
            this.open('signin');
        });

        document.getElementById('mobileJoinFree')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.closeMobileMenu();
            this.open('signup');
        });

        document.getElementById('mobileSignOut')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.closeMobileMenu();
            window.API?.logout();
        });

        // Close button
        document.querySelector('[data-auth-close]')?.addEventListener('click', () => {
            this.close();
        });

        // Close on backdrop click
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal?.classList.contains('open')) {
                this.close();
            }
        });
    },
    
    setupForm() {
        this.form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit();
        });
    },
    
    setupModeSwitching() {
        document.getElementById('switchToSignup')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.switchMode('signup');
        });
        
        document.getElementById('switchToSignin')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.switchMode('signin');
        });
    },
    
    closeMobileMenu() {
        const toggle = document.getElementById('mobileMenuToggle');
        const menu = document.getElementById('mobileMenu');
        const overlay = document.getElementById('mobileMenuOverlay');
        toggle?.classList.remove('active');
        menu?.classList.remove('active');
        overlay?.classList.remove('active');
        toggle?.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    },

    open(mode = 'signin') {
        this.mode = mode;
        this.updateUI();
        this.modal?.classList.add('open');
        document.body.style.overflow = 'hidden';
        
        // Focus first input
        this.modal?.querySelector('input')?.focus();
    },
    
    close() {
        this.modal?.classList.remove('open');
        document.body.style.overflow = '';
        this.clearError();
        this.form?.reset();
    },
    
    switchMode(mode) {
        this.mode = mode;
        this.updateUI();
        this.clearError();
    },
    
    updateUI() {
        const title = document.getElementById('authTitle');
        const submitBtn = document.getElementById('authSubmit');
        const nameField = document.getElementById('authNameField');
        const usernameField = document.getElementById('authUsernameField');
        const passwordConfirmField = document.getElementById('authPasswordConfirmField');
        const emailLabel = document.getElementById('authEmailLabel');
        const emailInput = document.getElementById('authEmail');
        const switchText = document.getElementById('authSwitchText');

        if (this.mode === 'signup') {
            title.textContent = 'Create Account';
            submitBtn.textContent = 'Sign Up';
            nameField?.classList.remove('hidden');
            usernameField?.classList.remove('hidden');
            passwordConfirmField?.classList.remove('hidden');
            if (emailLabel) emailLabel.textContent = 'Email Address';
            if (emailInput) {
                emailInput.type = 'email';
                emailInput.placeholder = 'Enter your email address';
            }
            switchText.innerHTML = 'Already have an account? <a href="#" id="switchToSignin">Sign in</a>';
        } else {
            title.textContent = 'Sign In';
            submitBtn.textContent = 'Sign In';
            nameField?.classList.add('hidden');
            usernameField?.classList.add('hidden');
            passwordConfirmField?.classList.add('hidden');
            if (emailLabel) emailLabel.textContent = 'Username or Email';
            if (emailInput) {
                emailInput.type = 'text';
                emailInput.placeholder = 'Enter username or email';
            }
            switchText.innerHTML = 'Don\'t have an account? <a href="#" id="switchToSignup">Sign up</a>';
        }

        // Clear validation errors on mode switch
        this.clearError();
        const matchError = document.getElementById('authPasswordMatchError');
        matchError?.classList.add('hidden');

        // Re-attach switch listeners
        this.setupModeSwitching();
    },
    
    async handleSubmit() {
        const email = document.getElementById('authEmail')?.value;
        const password = document.getElementById('authPassword')?.value;
        const name = document.getElementById('authName')?.value;
        const username = document.getElementById('authUsername')?.value;
        const passwordConfirm = document.getElementById('authPasswordConfirm')?.value;

        // Client-side validation for signup
        if (this.mode === 'signup') {
            const matchError = document.getElementById('authPasswordMatchError');
            matchError?.classList.add('hidden');

            if (!username?.trim()) {
                this.showError('Username is required.');
                return;
            }
            if (!email?.trim() || !email.includes('@')) {
                this.showError('Please enter a valid email address.');
                return;
            }
            if (!password) {
                this.showError('Password is required.');
                return;
            }
            if (password !== passwordConfirm) {
                matchError?.classList.remove('hidden');
                this.showError('Passwords do not match.');
                return;
            }
        }

        const submitBtn = document.getElementById('authSubmit');
        submitBtn.disabled = true;
        submitBtn.textContent = this.mode === 'signin' ? 'Signing in...' : 'Creating account...';

        try {
            if (this.mode === 'signin') {
                await window.API.login(email, password);
            } else {
                await window.API.register({ username, email, password, password_confirm: passwordConfirm, display_name: name });
            }
            
            this.close();
            
            // Show success message
            this.showSuccess('Welcome! You are now signed in.');
            
        } catch (error) {
            let msg;
            if (error.message === 'Failed to fetch') {
                msg = 'Unable to connect. Please check your internet connection.';
            } else if (error.fieldErrors && typeof error.fieldErrors === 'object') {
                // Build per-field error lines from structured API response
                const lines = Object.entries(error.fieldErrors)
                    .filter(([, v]) => Array.isArray(v))
                    .map(([field, msgs]) => `${field}: ${msgs.join(' ')}`);
                msg = lines.length > 0 ? lines.join('\n') : error.message;
            } else {
                msg = error.message;
            }
            this.showError(msg);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = this.mode === 'signin' ? 'Sign In' : 'Sign Up';
        }
    },
    
    showError(message) {
        const errorEl = document.getElementById('authError');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    },
    
    clearError() {
        const errorEl = document.getElementById('authError');
        if (errorEl) {
            errorEl.textContent = '';
            errorEl.classList.add('hidden');
        }
    },
    
    showSuccess(message) {
        // Could use a toast notification here
        console.log('Auth success:', message);
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    AuthModal.init();
});

// Export
window.AuthModal = AuthModal;
