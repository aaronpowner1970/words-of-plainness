/**
 * WORDS OF PLAINNESS - Reading Progress
 * ======================================
 *
 * Reading progress stays in this browser. This site has no accounts and sends
 * no reading progress anywhere (CODE-SITE-18, SITE step 27, spec 3.7): what a
 * reader without an account had before is what every reader has now. Where a
 * reader left off is kept by the bookmark (chapter.js, localStorage
 * wop-bookmark-*), and the bookmark toast is shown here.
 */

const ReadingProgress = {
    chapterSlug: null,
    config: null,

    init(config) {
        this.config = config;
        this.chapterSlug = config.id;

        if (!this.chapterSlug) return;

        this.enhanceBookmark();
    },

    // =========================================
    // Bookmark toast
    // =========================================

    enhanceBookmark() {
        document.addEventListener('wop:bookmark-saved', () => {
            this.showToast();
        });
    },

    showToast() {
        const toast = document.getElementById('bookmarkToast');
        if (!toast) return;

        toast.classList.remove('hidden');
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hidden');
        }, 2000);
    }
};

window.ReadingProgress = ReadingProgress;
