/**
 * WORDS OF PLAINNESS - Newsletter Subscription
 * ==============================================
 *
 * Handles newsletter subscribe forms (footer + connect page).
 * - Posts to Django API /newsletter/subscribe/
 * - Pre-fills from auth state
 * - Handles success, already-subscribed, and error states
 */

const Newsletter = {
    forms: [],

    init() {
        document.querySelectorAll('.newsletter-form').forEach(form => {
            this.setupForm(form);
        });
    },

    setupForm(form) {
        const nameInput = form.querySelector('input[name="name"]');
        const emailInput = form.querySelector('input[name="email"]');
        const submitBtn = form.querySelector('button[type="submit"]');

        // Pre-fill from auth
        if (window.API?.isAuthenticated() && window.API.user) {
            if (nameInput && !nameInput.value && window.API.user.name) {
                nameInput.value = window.API.user.name;
            }
            if (emailInput && !emailInput.value && window.API.user.email) {
                emailInput.value = window.API.user.email;
            }
        }

        // Clear field errors on input
        form.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', () => {
                const errorEl = form.querySelector(`[data-nl-error="${input.name}"]`);
                if (errorEl) {
                    errorEl.textContent = '';
                    errorEl.classList.add('hidden');
                }
            });
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleSubmit(form, nameInput, emailInput, submitBtn);
        });
    },

    async handleSubmit(form, nameInput, emailInput, submitBtn) {
        // Clear previous errors
        form.querySelectorAll('[data-nl-error]').forEach(el => {
            el.textContent = '';
            el.classList.add('hidden');
        });

        const email = emailInput?.value.trim();
        const name = nameInput?.value.trim();

        // Client-side validation
        if (!email || !email.includes('@')) {
            this.showFieldError(form, 'email', 'Please enter a valid email address.');
            return;
        }

        // Prevent double submit
        if (submitBtn.disabled) return;
        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Subscribing...';

        try {
            const data = { email };
            if (name) data.name = name;

            const result = await window.API.subscribeNewsletter(data);
            this.showSuccess(form, result.message || 'Thank you for subscribing!');

        } catch (error) {
            if (error.message === 'Failed to fetch') {
                this.showSuccess(form, 'Unable to subscribe right now. Please try again later.', true);
            } else if (error.fieldErrors && typeof error.fieldErrors === 'object') {
                let hasInline = false;
                for (const [field, msgs] of Object.entries(error.fieldErrors)) {
                    if (field === 'non_field_errors' || !Array.isArray(msgs)) continue;
                    const el = form.querySelector(`[data-nl-error="${field}"]`);
                    if (el) {
                        this.showFieldError(form, field, msgs.join(' '));
                        hasInline = true;
                    }
                }
                if (!hasInline) {
                    this.showSuccess(form, error.message, true);
                }
            } else {
                this.showSuccess(form, error.message, true);
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    },

    showFieldError(form, field, message) {
        const el = form.querySelector(`[data-nl-error="${field}"]`);
        if (el) {
            el.textContent = message;
            el.classList.remove('hidden');
        }
    },

    showSuccess(form, message, isError) {
        // Find the sibling message element
        const messageEl = form.parentElement.querySelector('.newsletter-message');
        if (messageEl) {
            messageEl.textContent = message;
            messageEl.classList.remove('hidden');
            if (isError) {
                messageEl.classList.add('newsletter-message--error');
                messageEl.classList.remove('newsletter-message--success');
            } else {
                messageEl.classList.add('newsletter-message--success');
                messageEl.classList.remove('newsletter-message--error');
                form.classList.add('hidden');
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Newsletter.init();
});

window.Newsletter = Newsletter;
