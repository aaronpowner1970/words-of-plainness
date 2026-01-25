/**
 * Words of Plainness - Auth Modal Manager
 * Handles login/register modal functionality
 */

const AuthModal = (function() {
    'use strict';

    let modal = null;
    let currentTab = 'login';

    // =====================================================
    // INITIALIZATION
    // =====================================================

    function init() {
        createModal();
        bindEvents();
        updateAuthUI();

        // Listen for auth events
        window.addEventListener('wop:auth:login', updateAuthUI);
        window.addEventListener('wop:auth:logout', updateAuthUI);
        window.addEventListener('wop:auth:expired', () => {
            updateAuthUI();
            showMessage('Your session has expired. Please sign in again.', 'error');
            open('login');
        });
    }

    // =====================================================
    // MODAL CREATION
    // =====================================================

    function createModal() {
        const overlay = document.createElement('div');
        overlay.className = 'auth-modal-overlay';
        overlay.id = 'authModalOverlay';
        overlay.innerHTML = `
            <div class="auth-modal" role="dialog" aria-labelledby="authModalTitle">
                <div class="auth-modal-header">
                    <h2 class="auth-modal-title" id="authModalTitle">Welcome</h2>
                    <button class="auth-modal-close" aria-label="Close modal">&times;</button>
                </div>
                <div class="auth-modal-body">
                    <!-- Tabs -->
                    <div class="auth-tabs">
                        <button class="auth-tab active" data-tab="login">Sign In</button>
                        <button class="auth-tab" data-tab="register">Create Account</button>
                    </div>

                    <!-- Global Messages -->
                    <div class="auth-global-error" id="authGlobalError"></div>
                    <div class="auth-success-message" id="authSuccessMessage"></div>

                    <!-- Login Panel -->
                    <div class="auth-panel active" id="loginPanel">
                        <form id="loginForm" novalidate>
                            <div class="auth-form-group">
                                <label for="loginUsername">Username or Email</label>
                                <input type="text" id="loginUsername" name="username" placeholder="Enter username or email" required>
                                <div class="auth-form-error" id="loginUsernameError"></div>
                            </div>
                            <div class="auth-form-group">
                                <label for="loginPassword">Password</label>
                                <input type="password" id="loginPassword" name="password" placeholder="Enter your password" required>
                                <div class="auth-form-error" id="loginPasswordError"></div>
                            </div>
                            <button type="submit" class="auth-submit-btn">Sign In</button>
                        </form>
                    </div>

                    <!-- Register Panel -->
                    <div class="auth-panel" id="registerPanel">
                        <form id="registerForm" novalidate>
                            <div class="auth-form-group">
                                <label for="registerUsername">Username</label>
                                <input type="text" id="registerUsername" name="username" placeholder="Choose a username" required minlength="3">
                                <div class="auth-form-helper">Letters, numbers, and underscores only</div>
                                <div class="auth-form-error" id="registerUsernameError"></div>
                            </div>
                            <div class="auth-form-group">
                                <label for="registerDisplayName">Display Name</label>
                                <input type="text" id="registerDisplayName" name="display_name" placeholder="How should we call you?" required>
                                <div class="auth-form-helper">This will be shown with your public reflections</div>
                                <div class="auth-form-error" id="registerDisplayNameError"></div>
                            </div>
                            <div class="auth-form-group">
                                <label for="registerEmail">Email</label>
                                <input type="email" id="registerEmail" name="email" placeholder="your@email.com" required>
                                <div class="auth-form-error" id="registerEmailError"></div>
                            </div>
                            <div class="auth-form-group">
                                <label for="registerPassword">Password</label>
                                <input type="password" id="registerPassword" name="password" placeholder="Create a password" required minlength="8">
                                <div class="auth-form-helper">At least 8 characters</div>
                                <div class="auth-form-error" id="registerPasswordError"></div>
                            </div>
                            <div class="auth-form-group">
                                <label for="registerPasswordConfirm">Confirm Password</label>
                                <input type="password" id="registerPasswordConfirm" name="password_confirm" placeholder="Confirm your password" required>
                                <div class="auth-form-error" id="registerPasswordConfirmError"></div>
                            </div>
                            <div class="auth-checkbox-group">
                                <input type="checkbox" id="registerAgree" name="agree" required>
                                <label for="registerAgree">I agree to share my public reflections with the community in a spirit of edification and respect.</label>
                            </div>
                            <button type="submit" class="auth-submit-btn">Create Account</button>
                        </form>
                    </div>

                    <div class="auth-footer">
                        <p id="authFooterText">Don't have an account? <a href="#" data-switch="register">Create one free</a></p>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        modal = overlay;
    }

    // =====================================================
    // EVENT BINDING
    // =====================================================

    function bindEvents() {
        // Close button
        modal.querySelector('.auth-modal-close').addEventListener('click', close);

        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) close();
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('open')) {
                close();
            }
        });

        // Tab switching
        modal.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        // Footer link switching
        modal.querySelectorAll('[data-switch]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                switchTab(link.dataset.switch);
            });
        });

        // Form submissions
        document.getElementById('loginForm').addEventListener('submit', handleLogin);
        document.getElementById('registerForm').addEventListener('submit', handleRegister);

        // Clear errors on input
        modal.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', () => {
                input.classList.remove('error');
                const errorEl = document.getElementById(`${input.id}Error`);
                if (errorEl) {
                    errorEl.textContent = '';
                    errorEl.classList.remove('visible');
                }
                hideGlobalError();
            });
        });

        // Bind header auth buttons (event delegation)
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-sign-in, .btn-sign-in *')) {
                e.preventDefault();
                open('login');
            }
            if (e.target.matches('.btn-join-free, .btn-join-free *')) {
                e.preventDefault();
                open('register');
            }
            if (e.target.matches('.user-menu-toggle, .user-menu-toggle *')) {
                toggleUserMenu();
            }
            if (e.target.matches('[data-action="logout"]')) {
                e.preventDefault();
                handleLogout();
            }
        });

        // Close user menu when clicking outside
        document.addEventListener('click', (e) => {
            const userMenu = document.querySelector('.user-menu');
            if (userMenu && !userMenu.contains(e.target)) {
                userMenu.classList.remove('open');
            }
        });
    }

    // =====================================================
    // MODAL OPERATIONS
    // =====================================================

    function open(tab = 'login') {
        switchTab(tab);
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';

        // Focus first input
        setTimeout(() => {
            const panel = modal.querySelector('.auth-panel.active');
            const firstInput = panel.querySelector('input');
            if (firstInput) firstInput.focus();
        }, 100);
    }

    function close() {
        modal.classList.remove('open');
        document.body.style.overflow = '';
        clearForms();
        hideGlobalError();
        hideSuccessMessage();
    }

    function switchTab(tab) {
        currentTab = tab;

        // Update tabs
        modal.querySelectorAll('.auth-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });

        // Update panels
        modal.querySelectorAll('.auth-panel').forEach(p => {
            p.classList.toggle('active', p.id === `${tab}Panel`);
        });

        // Update title
        modal.querySelector('.auth-modal-title').textContent =
            tab === 'login' ? 'Welcome Back' : 'Join the Community';

        // Update footer
        const footer = modal.querySelector('#authFooterText');
        if (tab === 'login') {
            footer.innerHTML = `Don't have an account? <a href="#" data-switch="register">Create one free</a>`;
        } else {
            footer.innerHTML = `Already have an account? <a href="#" data-switch="login">Sign in</a>`;
        }

        hideGlobalError();
        hideSuccessMessage();
    }

    function clearForms() {
        modal.querySelectorAll('form').forEach(form => form.reset());
        modal.querySelectorAll('.auth-form-error').forEach(el => {
            el.textContent = '';
            el.classList.remove('visible');
        });
        modal.querySelectorAll('input').forEach(input => input.classList.remove('error'));
    }

    // =====================================================
    // FORM HANDLERS
    // =====================================================

    async function handleLogin(e) {
        e.preventDefault();
        const form = e.target;
        const btn = form.querySelector('.auth-submit-btn');

        const username = form.username.value.trim();
        const password = form.password.value;

        // Validation
        let valid = true;
        if (!username) {
            showFieldError('loginUsername', 'Username is required');
            valid = false;
        }
        if (!password) {
            showFieldError('loginPassword', 'Password is required');
            valid = false;
        }

        if (!valid) return;

        btn.classList.add('loading');
        btn.disabled = true;

        try {
            await WoPAPI.login({ username, password });
            showSuccessMessage('Welcome back! Signing you in...');
            // Explicitly update UI after successful login
            updateAuthUI();
            setTimeout(() => {
                close();
                updateAuthUI(); // Update again after modal closes
                window.dispatchEvent(new CustomEvent('wop:auth:ready'));
            }, 1000);
        } catch (error) {
            showGlobalError(error.message || 'Invalid username or password');

            // Show field-specific errors if available
            if (error.errors) {
                if (error.errors.username) showFieldError('loginUsername', error.errors.username);
                if (error.errors.password) showFieldError('loginPassword', error.errors.password);
            }
        } finally {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }

    async function handleRegister(e) {
        e.preventDefault();
        const form = e.target;
        const btn = form.querySelector('.auth-submit-btn');

        const username = form.username.value.trim();
        const display_name = form.display_name.value.trim();
        const email = form.email.value.trim();
        const password = form.password.value;
        const password_confirm = form.password_confirm.value;
        const agreed = form.agree.checked;

        // Validation
        let valid = true;
        if (!username) {
            showFieldError('registerUsername', 'Username is required');
            valid = false;
        } else if (username.length < 3) {
            showFieldError('registerUsername', 'Username must be at least 3 characters');
            valid = false;
        }
        if (!display_name) {
            showFieldError('registerDisplayName', 'Display name is required');
            valid = false;
        }
        if (!email) {
            showFieldError('registerEmail', 'Email is required');
            valid = false;
        }
        if (!password) {
            showFieldError('registerPassword', 'Password is required');
            valid = false;
        } else if (password.length < 8) {
            showFieldError('registerPassword', 'Password must be at least 8 characters');
            valid = false;
        }
        if (password !== password_confirm) {
            showFieldError('registerPasswordConfirm', 'Passwords do not match');
            valid = false;
        }
        if (!agreed) {
            showGlobalError('Please agree to share reflections respectfully');
            valid = false;
        }

        if (!valid) return;

        btn.classList.add('loading');
        btn.disabled = true;

        try {
            await WoPAPI.register({ username, display_name, email, password, password_confirm });
            showSuccessMessage('Account created! Welcome to Words of Plainness.');
            // Explicitly update UI after successful registration
            updateAuthUI();
            setTimeout(() => {
                close();
                updateAuthUI(); // Update again after modal closes
                window.dispatchEvent(new CustomEvent('wop:auth:ready'));
            }, 1500);
        } catch (error) {
            showGlobalError(error.message || 'Registration failed. Please try again.');

            // Show field-specific errors
            if (error.errors) {
                if (error.errors.username) showFieldError('registerUsername', error.errors.username);
                if (error.errors.display_name) showFieldError('registerDisplayName', error.errors.display_name);
                if (error.errors.email) showFieldError('registerEmail', error.errors.email);
                if (error.errors.password) showFieldError('registerPassword', error.errors.password);
            }
        } finally {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }

    async function handleLogout() {
        const userMenu = document.querySelector('.user-menu');
        if (userMenu) userMenu.classList.remove('open');

        await WoPAPI.logout();
        // Explicitly update UI after logout
        updateAuthUI();
        // Force page elements to update
        setTimeout(updateAuthUI, 100);
    }

    // =====================================================
    // UI HELPERS
    // =====================================================

    function showFieldError(inputId, message) {
        const input = document.getElementById(inputId);
        const errorEl = document.getElementById(`${inputId}Error`);

        if (input) input.classList.add('error');
        if (errorEl) {
            errorEl.textContent = Array.isArray(message) ? message.join(', ') : message;
            errorEl.classList.add('visible');
        }
    }

    function showGlobalError(message) {
        const el = document.getElementById('authGlobalError');
        if (el) {
            el.textContent = message;
            el.classList.add('visible');
        }
    }

    function hideGlobalError() {
        const el = document.getElementById('authGlobalError');
        if (el) {
            el.textContent = '';
            el.classList.remove('visible');
        }
    }

    function showSuccessMessage(message) {
        const el = document.getElementById('authSuccessMessage');
        if (el) {
            el.textContent = message;
            el.classList.add('visible');
        }
    }

    function hideSuccessMessage() {
        const el = document.getElementById('authSuccessMessage');
        if (el) {
            el.textContent = '';
            el.classList.remove('visible');
        }
    }

    function showMessage(message, type = 'info') {
        if (type === 'error') {
            showGlobalError(message);
        } else {
            showSuccessMessage(message);
        }
    }

    // =====================================================
    // AUTH UI UPDATE
    // =====================================================

    function updateAuthUI() {
        const isLoggedIn = WoPAPI.isAuthenticated();
        const user = WoPAPI.getStoredUser();

        console.log('[AuthModal] updateAuthUI called, isLoggedIn:', isLoggedIn, 'user:', user);

        // Desktop nav
        const authButtonsLoggedOut = document.querySelector('.nav-auth-buttons');
        const userMenu = document.querySelector('.user-menu');

        console.log('[AuthModal] Found elements - authButtons:', !!authButtonsLoggedOut, 'userMenu:', !!userMenu);

        if (authButtonsLoggedOut) {
            authButtonsLoggedOut.style.display = isLoggedIn ? 'none' : 'flex';
            console.log('[AuthModal] Set authButtons display to:', authButtonsLoggedOut.style.display);
        }

        if (userMenu) {
            userMenu.classList.toggle('visible', isLoggedIn);
            console.log('[AuthModal] Set userMenu visible class:', userMenu.classList.contains('visible'));

            if (isLoggedIn && user) {
                const avatar = userMenu.querySelector('.user-avatar');
                const displayName = userMenu.querySelector('.user-display-name');
                const dropdownName = userMenu.querySelector('.user-dropdown-name');
                const dropdownEmail = userMenu.querySelector('.user-dropdown-email');

                if (avatar) avatar.textContent = getInitials(user.display_name || user.email);
                if (displayName) displayName.textContent = user.display_name || 'User';
                if (dropdownName) dropdownName.textContent = user.display_name || 'User';
                if (dropdownEmail) dropdownEmail.textContent = user.email || '';
            }
        }

        // Mobile nav
        const mobileAuthButtons = document.querySelector('.mobile-auth-buttons');
        const mobileUserInfo = document.querySelector('.mobile-user-info');

        if (mobileAuthButtons) {
            mobileAuthButtons.style.display = isLoggedIn ? 'none' : 'flex';
        }

        if (mobileUserInfo) {
            mobileUserInfo.classList.toggle('visible', isLoggedIn);

            if (isLoggedIn && user) {
                const avatar = mobileUserInfo.querySelector('.user-avatar');
                const name = mobileUserInfo.querySelector('.name');
                const email = mobileUserInfo.querySelector('.email');

                if (avatar) avatar.textContent = getInitials(user.display_name || user.email);
                if (name) name.textContent = user.display_name || 'User';
                if (email) email.textContent = user.email || '';
            }
        }
    }

    function toggleUserMenu() {
        const userMenu = document.querySelector('.user-menu');
        if (userMenu) {
            userMenu.classList.toggle('open');
        }
    }

    function getInitials(name) {
        if (!name) return '?';
        return name.split(' ')
            .map(word => word[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
    }

    // =====================================================
    // PUBLIC API
    // =====================================================

    return {
        init,
        open,
        close,
        updateAuthUI
    };
})();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AuthModal.init();
});

// Make available globally
window.AuthModal = AuthModal;
