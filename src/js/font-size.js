/**
 * WORDS OF PLAINNESS — Sitewide Font Size Control
 * =================================================
 * Applies a user-selected font size to the <html> element via
 * a CSS custom property (--wop-font-scale). All rem-based sizing
 * across every page inherits from this automatically.
 *
 * Used by:
 *  - The global font-size widget in base.njk (every page)
 *  - ChapterManager.initFontControls() (delegates here instead of
 *    targeting .chapter-content directly)
 *
 * Storage key : 'wop-font-size'  (float, rem, e.g. 1.0)
 * Range        : 0.875 – 1.375 rem, step 0.125
 * Default      : 1.0 (matches html { font-size: 16px } baseline)
 */

const WopFontSize = (() => {
    const KEY      = 'wop-font-size';
    const DEFAULT  = 1.0;
    const MIN      = 0.875;
    const MAX      = 1.375;
    const STEP     = 0.125;

    function clamp(v) {
        return Math.max(MIN, Math.min(MAX, v));
    }

    function apply(size) {
        document.documentElement.style.fontSize = size + 'rem';
    }

    function load() {
        try {
            return clamp(parseFloat(localStorage.getItem(KEY)) || DEFAULT);
        } catch (e) {
            return DEFAULT;
        }
    }

    function save(size) {
        try { localStorage.setItem(KEY, size); } catch (e) { /* silent */ }
    }

    function get() {
        // Read from the element itself — always the source of truth
        const raw = parseFloat(document.documentElement.style.fontSize);
        return isNaN(raw) ? load() : raw;
    }

    function set(size) {
        const clamped = clamp(size);
        apply(clamped);
        save(clamped);
    }

    function increase() { set(get() + STEP); }
    function decrease() { set(get() - STEP); }
    function reset()    { set(DEFAULT); }

    function init() {
        apply(load());

        // Wire the global widget buttons (present on every page via base.njk)
        document.getElementById('wopFontDecrease')?.addEventListener('click', decrease);
        document.getElementById('wopFontReset')   ?.addEventListener('click', reset);
        document.getElementById('wopFontIncrease')?.addEventListener('click', increase);
    }

    return { init, increase, decrease, reset, set, get, DEFAULT, MIN, MAX };
})();

// Expose globally so inline page scripts (e.g. /articles/) can call it via window.WopFontSize
window.WopFontSize = WopFontSize;

// Auto-init as soon as the DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', WopFontSize.init);
} else {
    WopFontSize.init();
}
