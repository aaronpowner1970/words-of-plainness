/**
 * Words of Plainness - Reflections Integration
 * Syncs reflections between local storage and API
 */

const ReflectionsManager = (function() {
    'use strict';

    let chapterSlug = '';
    let isInitialized = false;
    let communityReflections = [];

    // =====================================================
    // INITIALIZATION
    // =====================================================

    function init(slug) {
        chapterSlug = slug;
        isInitialized = true;

        // Load initial state
        loadReflection();

        // If logged in, sync with server
        if (WoPAPI.isAuthenticated()) {
            syncWithServer();
            loadCommunityReflections();
        }

        // Listen for auth events
        window.addEventListener('wop:auth:login', onLogin);
        window.addEventListener('wop:auth:logout', onLogout);
        window.addEventListener('wop:auth:ready', onAuthReady);

        // Update UI based on auth state
        updateReflectionUI();
    }

    // =====================================================
    // AUTH EVENT HANDLERS
    // =====================================================

    function onLogin() {
        syncWithServer();
        loadCommunityReflections();
        updateReflectionUI();
    }

    function onLogout() {
        communityReflections = [];
        updateReflectionUI();
        renderCommunityReflections();
    }

    function onAuthReady() {
        syncWithServer();
        loadCommunityReflections();
    }

    // =====================================================
    // LOCAL STORAGE
    // =====================================================

    function getLocalStorageKey() {
        return `wop-reflection-${chapterSlug}`;
    }

    function loadFromLocalStorage() {
        const saved = localStorage.getItem(getLocalStorageKey());
        return saved ? JSON.parse(saved) : null;
    }

    function saveToLocalStorage(data) {
        localStorage.setItem(getLocalStorageKey(), JSON.stringify(data));
    }

    function clearLocalStorage() {
        localStorage.removeItem(getLocalStorageKey());
    }

    // =====================================================
    // REFLECTION LOADING
    // =====================================================

    function loadReflection() {
        const data = loadFromLocalStorage();
        if (data) {
            populateForm(data);
        }
    }

    function populateForm(data) {
        const textareas = document.querySelectorAll('.step-textarea');
        if (textareas.length >= 3) {
            textareas[0].value = data.assess || '';
            textareas[1].value = data.align || '';
            textareas[2].value = data.act || '';
        }
    }

    function getFormData() {
        const textareas = document.querySelectorAll('.step-textarea');
        return {
            assess: textareas[0]?.value || '',
            align: textareas[1]?.value || '',
            act: textareas[2]?.value || '',
            savedAt: new Date().toISOString()
        };
    }

    // =====================================================
    // SAVING
    // =====================================================

    async function saveReflection() {
        const data = getFormData();

        // Always save locally first
        saveToLocalStorage(data);

        // If logged in, also save to server
        if (WoPAPI.isAuthenticated()) {
            try {
                showSaveStatus('saving');

                await WoPAPI.saveReflection({
                    chapter_slug: chapterSlug,
                    content: JSON.stringify(data),
                    is_public: isPublicChecked()
                });

                showSaveStatus('saved');
                showNotification('Reflection saved!', 'success');

                // Reload community reflections if made public
                if (isPublicChecked()) {
                    setTimeout(() => loadCommunityReflections(), 1000);
                }
            } catch (error) {
                showSaveStatus('error');
                showNotification('Saved locally. Server sync failed.', 'warning');
                console.error('Failed to save to server:', error);
            }
        } else {
            showNotification('Saved locally. Sign in to sync across devices.', 'info');
        }
    }

    async function clearReflection() {
        if (!confirm('Are you sure you want to clear your reflection?')) {
            return;
        }

        const textareas = document.querySelectorAll('.step-textarea');
        textareas.forEach(ta => ta.value = '');

        clearLocalStorage();
        showNotification('Reflection cleared.', 'info');
    }

    // =====================================================
    // SERVER SYNC
    // =====================================================

    async function syncWithServer() {
        if (!WoPAPI.isAuthenticated()) return;

        try {
            const serverReflections = await WoPAPI.getMyReflections();
            const reflectionsList = serverReflections.results || serverReflections;
            const serverReflection = reflectionsList.find(r => r.chapter_slug === chapterSlug);

            if (serverReflection) {
                const serverData = JSON.parse(serverReflection.content);
                const localData = loadFromLocalStorage();

                // Compare timestamps to determine which is newer
                if (!localData || new Date(serverData.savedAt) > new Date(localData.savedAt)) {
                    populateForm(serverData);
                    saveToLocalStorage(serverData);
                }
            }
        } catch (error) {
            console.error('Failed to sync with server:', error);
        }
    }

    // =====================================================
    // COMMUNITY REFLECTIONS
    // =====================================================

    async function loadCommunityReflections() {
        if (!WoPAPI.isAuthenticated()) return;

        try {
            const response = await WoPAPI.getChapterReflections(chapterSlug);
            communityReflections = response.results || response;
            renderCommunityReflections();
        } catch (error) {
            console.error('Failed to load community reflections:', error);
        }
    }

    function renderCommunityReflections() {
        const container = document.getElementById('communityReflections');
        if (!container) return;

        if (!WoPAPI.isAuthenticated()) {
            container.innerHTML = `
                <div class="community-signin-prompt">
                    <p>Sign in to see and share reflections with the community.</p>
                    <button class="btn btn-outline-gold btn-sign-in">Sign In</button>
                </div>
            `;
            return;
        }

        if (communityReflections.length === 0) {
            container.innerHTML = `
                <div class="community-empty">
                    <p>No public reflections yet. Be the first to share!</p>
                </div>
            `;
            return;
        }

        const currentUser = WoPAPI.getStoredUser();

        container.innerHTML = communityReflections.map(reflection => {
            const data = JSON.parse(reflection.content);
            const isOwn = currentUser && reflection.user_id === currentUser.id;
            const appreciated = reflection.user_appreciated;

            return `
                <div class="community-reflection ${isOwn ? 'own' : ''}" data-id="${reflection.id}">
                    <div class="reflection-author">
                        <span class="author-avatar">${getInitials(reflection.display_name)}</span>
                        <span class="author-name">${escapeHtml(reflection.display_name)}</span>
                        ${isOwn ? '<span class="own-badge">You</span>' : ''}
                    </div>
                    <div class="reflection-content">
                        ${data.assess ? `<div class="reflection-answer"><strong>Where I Am:</strong> ${escapeHtml(data.assess)}</div>` : ''}
                        ${data.align ? `<div class="reflection-answer"><strong>Seeking Grace:</strong> ${escapeHtml(data.align)}</div>` : ''}
                        ${data.act ? `<div class="reflection-answer"><strong>My Commitment:</strong> ${escapeHtml(data.act)}</div>` : ''}
                    </div>
                    <div class="reflection-footer">
                        <span class="reflection-date">${formatDate(reflection.created_at)}</span>
                        ${!isOwn ? `
                            <button class="appreciate-btn ${appreciated ? 'appreciated' : ''}"
                                    onclick="ReflectionsManager.appreciate(${reflection.id})"
                                    ${appreciated ? 'disabled' : ''}>
                                <span class="appreciate-icon">${appreciated ? '❤️' : '🤍'}</span>
                                <span class="appreciate-count">${reflection.appreciation_count || 0}</span>
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    async function appreciate(reflectionId) {
        try {
            await WoPAPI.appreciateReflection(reflectionId);

            // Update local state
            const reflection = communityReflections.find(r => r.id === reflectionId);
            if (reflection) {
                reflection.user_appreciated = true;
                reflection.appreciation_count = (reflection.appreciation_count || 0) + 1;
            }

            renderCommunityReflections();
        } catch (error) {
            showNotification('Could not appreciate this reflection.', 'error');
            console.error('Failed to appreciate:', error);
        }
    }

    // =====================================================
    // UI UPDATES
    // =====================================================

    function updateReflectionUI() {
        const isLoggedIn = WoPAPI.isAuthenticated();

        // Update the public checkbox visibility
        const publicOption = document.getElementById('reflectionPublicOption');
        if (publicOption) {
            publicOption.style.display = isLoggedIn ? 'flex' : 'none';
        }

        // Update the note text
        const noteEl = document.querySelector('.reflection-note');
        if (noteEl) {
            if (isLoggedIn) {
                noteEl.textContent = 'Your reflection syncs across devices. Check "Share publicly" to inspire others.';
            } else {
                noteEl.innerHTML = 'Saved locally in your browser. <a href="#" class="btn-sign-in" style="color: var(--gold-primary);">Sign in</a> to sync across devices.';
            }
        }

        // Update community section visibility
        const communitySection = document.getElementById('communitySection');
        if (communitySection) {
            communitySection.style.display = 'block';
        }
    }

    function isPublicChecked() {
        const checkbox = document.getElementById('reflectionPublic');
        return checkbox ? checkbox.checked : false;
    }

    function showSaveStatus(status) {
        const statusEl = document.getElementById('saveStatus');
        if (!statusEl) return;

        statusEl.className = `save-status ${status}`;

        switch(status) {
            case 'saving':
                statusEl.textContent = 'Saving...';
                break;
            case 'saved':
                statusEl.textContent = 'Saved';
                setTimeout(() => statusEl.className = 'save-status', 2000);
                break;
            case 'error':
                statusEl.textContent = 'Sync error';
                break;
        }
    }

    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `reflection-notification ${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Remove after delay
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // =====================================================
    // HELPERS
    // =====================================================

    function getInitials(name) {
        if (!name) return '?';
        return name.split(' ')
            .map(word => word[0])
            .join('')
            .toUpperCase()
            .slice(0, 2);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;

        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    // =====================================================
    // PUBLIC API
    // =====================================================

    return {
        init,
        saveReflection,
        clearReflection,
        loadCommunityReflections,
        appreciate,
        updateReflectionUI
    };
})();

// Add notification styles dynamically
(function() {
    const style = document.createElement('style');
    style.textContent = `
        .reflection-notification {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%) translateY(20px);
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            z-index: 3000;
            opacity: 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .reflection-notification.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        .reflection-notification.success {
            background: #2ecc71;
            color: #fff;
        }

        .reflection-notification.error {
            background: #e74c3c;
            color: #fff;
        }

        .reflection-notification.warning {
            background: #f39c12;
            color: #fff;
        }

        .reflection-notification.info {
            background: var(--brown-rich);
            color: var(--cream);
            border: 1px solid var(--gold-primary);
        }

        /* Community Reflections Styles */
        .community-reflections-section {
            margin-top: var(--space-xl);
            padding-top: var(--space-lg);
            border-top: 1px solid rgba(196, 148, 58, 0.2);
        }

        .community-reflections-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-md);
        }

        .community-reflections-header h4 {
            font-family: var(--font-serif);
            font-size: 1.2rem;
            color: var(--gold-primary);
            margin: 0;
        }

        .community-signin-prompt,
        .community-empty {
            text-align: center;
            padding: var(--space-lg);
            background: rgba(0, 0, 0, 0.15);
            border-radius: var(--radius-md);
        }

        .community-signin-prompt p,
        .community-empty p {
            margin: 0 0 var(--space-sm) 0;
            opacity: 0.8;
        }

        .community-reflection {
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(196, 148, 58, 0.15);
            border-radius: var(--radius-md);
            padding: var(--space-md);
            margin-bottom: var(--space-sm);
        }

        .community-reflection.own {
            border-color: rgba(196, 148, 58, 0.4);
            background: rgba(196, 148, 58, 0.08);
        }

        .reflection-author {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: var(--space-sm);
        }

        .author-avatar {
            width: 28px;
            height: 28px;
            background: var(--gold-primary);
            color: var(--brown-deep);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .author-name {
            font-weight: 600;
            font-size: 0.9rem;
        }

        .own-badge {
            font-size: 0.7rem;
            background: var(--gold-primary);
            color: var(--brown-deep);
            padding: 0.15rem 0.5rem;
            border-radius: 10px;
            margin-left: 0.25rem;
        }

        .reflection-content {
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .reflection-answer {
            margin-bottom: 0.5rem;
        }

        .reflection-answer strong {
            color: var(--gold-primary);
            font-size: 0.85rem;
        }

        .reflection-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: var(--space-sm);
            padding-top: var(--space-xs);
            border-top: 1px solid rgba(196, 148, 58, 0.1);
        }

        .reflection-date {
            font-size: 0.8rem;
            opacity: 0.6;
        }

        .appreciate-btn {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            background: none;
            border: 1px solid rgba(196, 148, 58, 0.3);
            border-radius: 20px;
            padding: 0.3rem 0.75rem;
            color: var(--cream);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .appreciate-btn:hover:not(:disabled) {
            border-color: var(--gold-primary);
            background: rgba(196, 148, 58, 0.1);
        }

        .appreciate-btn.appreciated {
            border-color: #e74c3c;
            background: rgba(231, 76, 60, 0.1);
        }

        .appreciate-btn:disabled {
            cursor: default;
        }

        /* Save Status */
        .save-status {
            font-size: 0.8rem;
            margin-left: var(--space-sm);
            opacity: 0;
            transition: opacity 0.2s;
        }

        .save-status.saving,
        .save-status.saved,
        .save-status.error {
            opacity: 1;
        }

        .save-status.saving {
            color: var(--cream);
        }

        .save-status.saved {
            color: #2ecc71;
        }

        .save-status.error {
            color: #e74c3c;
        }

        /* Public Checkbox */
        #reflectionPublicOption {
            display: none;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: var(--space-sm);
        }

        #reflectionPublicOption input {
            accent-color: var(--gold-primary);
        }

        #reflectionPublicOption label {
            font-size: 0.9rem;
            cursor: pointer;
        }
    `;
    document.head.appendChild(style);
})();

// Make available globally
window.ReflectionsManager = ReflectionsManager;
