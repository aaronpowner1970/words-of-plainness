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
        const switchText = document.getElementById('authSwitchText');
        
        if (this.mode === 'signup') {
            title.textContent = 'Create Account';
            submitBtn.textContent = 'Sign Up';
            nameField?.classList.remove('hidden');
            switchText.innerHTML = 'Already have an account? <a href="#" id="switchToSignin">Sign in</a>';
        } else {
            title.textContent = 'Sign In';
            submitBtn.textContent = 'Sign In';
            nameField?.classList.add('hidden');
            switchText.innerHTML = 'Don\'t have an account? <a href="#" id="switchToSignup">Sign up</a>';
        }
        
        // Re-attach switch listeners
        this.setupModeSwitching();
    },
    
    async handleSubmit() {
        const email = document.getElementById('authEmail')?.value;
        const password = document.getElementById('authPassword')?.value;
        const name = document.getElementById('authName')?.value;
        
        const submitBtn = document.getElementById('authSubmit');
        submitBtn.disabled = true;
        submitBtn.textContent = this.mode === 'signin' ? 'Signing in...' : 'Creating account...';
        
        try {
            if (this.mode === 'signin') {
                await window.API.login(email, password);
            } else {
                await window.API.register(email, password, name);
            }
            
            this.close();
            
            // Show success message
            this.showSuccess('Welcome! You are now signed in.');
            
        } catch (error) {
            this.showError(error.message);
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
