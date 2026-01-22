/**
 * Scripture Hyperlink Generator for Words of Plainness
 * =====================================================
 * Automatically converts scripture references to clickable links
 * pointing to churchofjesuschrist.org
 * 
 * Features:
 * - Detects references like "John 3:16", "2 Nephi 25:26", "D&C 93:1"
 * - Supports verse ranges: "Matthew 5:3-12"
 * - Case-insensitive matching
 * - Works with abbreviations (D&C, 1 Ne, etc.)
 * - Coexists with audio sync features (stopPropagation on links)
 * 
 * Usage:
 * 1. Include this script on any page
 * 2. Call ScriptureLinker.init() after DOM loads
 * 3. Optionally specify a container: ScriptureLinker.init('#content')
 */

const ScriptureLinker = (function() {
    'use strict';

    // ===========================================
    // BOOK MAPPING DICTIONARY
    // Maps book names/abbreviations to URL paths
    // ===========================================
    const BOOK_MAP = {
        // ----- OLD TESTAMENT -----
        'genesis': 'ot/gen',
        'gen': 'ot/gen',
        'exodus': 'ot/ex',
        'ex': 'ot/ex',
        'leviticus': 'ot/lev',
        'lev': 'ot/lev',
        'numbers': 'ot/num',
        'num': 'ot/num',
        'deuteronomy': 'ot/deut',
        'deut': 'ot/deut',
        'joshua': 'ot/josh',
        'josh': 'ot/josh',
        'judges': 'ot/judg',
        'judg': 'ot/judg',
        'ruth': 'ot/ruth',
        '1 samuel': 'ot/1-sam',
        '1 sam': 'ot/1-sam',
        '2 samuel': 'ot/2-sam',
        '2 sam': 'ot/2-sam',
        '1 kings': 'ot/1-kgs',
        '1 kgs': 'ot/1-kgs',
        '2 kings': 'ot/2-kgs',
        '2 kgs': 'ot/2-kgs',
        '1 chronicles': 'ot/1-chr',
        '1 chr': 'ot/1-chr',
        '2 chronicles': 'ot/2-chr',
        '2 chr': 'ot/2-chr',
        'ezra': 'ot/ezra',
        'nehemiah': 'ot/neh',
        'neh': 'ot/neh',
        'esther': 'ot/esth',
        'esth': 'ot/esth',
        'job': 'ot/job',
        'psalms': 'ot/ps',
        'psalm': 'ot/ps',
        'ps': 'ot/ps',
        'proverbs': 'ot/prov',
        'prov': 'ot/prov',
        'ecclesiastes': 'ot/eccl',
        'eccl': 'ot/eccl',
        'song of solomon': 'ot/song',
        'song': 'ot/song',
        'isaiah': 'ot/isa',
        'isa': 'ot/isa',
        'jeremiah': 'ot/jer',
        'jer': 'ot/jer',
        'lamentations': 'ot/lam',
        'lam': 'ot/lam',
        'ezekiel': 'ot/ezek',
        'ezek': 'ot/ezek',
        'daniel': 'ot/dan',
        'dan': 'ot/dan',
        'hosea': 'ot/hosea',
        'joel': 'ot/joel',
        'amos': 'ot/amos',
        'obadiah': 'ot/obad',
        'obad': 'ot/obad',
        'jonah': 'ot/jonah',
        'micah': 'ot/micah',
        'nahum': 'ot/nahum',
        'habakkuk': 'ot/hab',
        'hab': 'ot/hab',
        'zephaniah': 'ot/zeph',
        'zeph': 'ot/zeph',
        'haggai': 'ot/hag',
        'hag': 'ot/hag',
        'zechariah': 'ot/zech',
        'zech': 'ot/zech',
        'malachi': 'ot/mal',
        'mal': 'ot/mal',

        // ----- NEW TESTAMENT -----
        'matthew': 'nt/matt',
        'matt': 'nt/matt',
        'mark': 'nt/mark',
        'luke': 'nt/luke',
        'john': 'nt/john',
        'acts': 'nt/acts',
        'romans': 'nt/rom',
        'rom': 'nt/rom',
        '1 corinthians': 'nt/1-cor',
        '1 cor': 'nt/1-cor',
        '2 corinthians': 'nt/2-cor',
        '2 cor': 'nt/2-cor',
        'galatians': 'nt/gal',
        'gal': 'nt/gal',
        'ephesians': 'nt/eph',
        'eph': 'nt/eph',
        'philippians': 'nt/philip',
        'philip': 'nt/philip',
        'phil': 'nt/philip',
        'colossians': 'nt/col',
        'col': 'nt/col',
        '1 thessalonians': 'nt/1-thes',
        '1 thes': 'nt/1-thes',
        '2 thessalonians': 'nt/2-thes',
        '2 thes': 'nt/2-thes',
        '1 timothy': 'nt/1-tim',
        '1 tim': 'nt/1-tim',
        '2 timothy': 'nt/2-tim',
        '2 tim': 'nt/2-tim',
        'titus': 'nt/titus',
        'philemon': 'nt/philem',
        'philem': 'nt/philem',
        'hebrews': 'nt/heb',
        'heb': 'nt/heb',
        'james': 'nt/james',
        '1 peter': 'nt/1-pet',
        '1 pet': 'nt/1-pet',
        '2 peter': 'nt/2-pet',
        '2 pet': 'nt/2-pet',
        '1 john': 'nt/1-jn',
        '1 jn': 'nt/1-jn',
        '2 john': 'nt/2-jn',
        '2 jn': 'nt/2-jn',
        '3 john': 'nt/3-jn',
        '3 jn': 'nt/3-jn',
        'jude': 'nt/jude',
        'revelation': 'nt/rev',
        'rev': 'nt/rev',

        // ----- BOOK OF MORMON -----
        '1 nephi': 'bofm/1-ne',
        '1 ne': 'bofm/1-ne',
        '2 nephi': 'bofm/2-ne',
        '2 ne': 'bofm/2-ne',
        'jacob': 'bofm/jacob',
        'enos': 'bofm/enos',
        'jarom': 'bofm/jarom',
        'omni': 'bofm/omni',
        'words of mormon': 'bofm/w-of-m',
        'w of m': 'bofm/w-of-m',
        'mosiah': 'bofm/mosiah',
        'alma': 'bofm/alma',
        'helaman': 'bofm/hel',
        'hel': 'bofm/hel',
        '3 nephi': 'bofm/3-ne',
        '3 ne': 'bofm/3-ne',
        '4 nephi': 'bofm/4-ne',
        '4 ne': 'bofm/4-ne',
        'mormon': 'bofm/morm',
        'morm': 'bofm/morm',
        'ether': 'bofm/ether',
        'moroni': 'bofm/moro',
        'moro': 'bofm/moro',

        // ----- DOCTRINE AND COVENANTS -----
        'doctrine and covenants': 'dc-testament/dc',
        'doctrine & covenants': 'dc-testament/dc',
        'd&c': 'dc-testament/dc',
        'dc': 'dc-testament/dc',

        // ----- PEARL OF GREAT PRICE -----
        'moses': 'pgp/moses',
        'abraham': 'pgp/abr',
        'abr': 'pgp/abr',
        'joseph smith—matthew': 'pgp/js-m',
        'joseph smith-matthew': 'pgp/js-m',
        'js-m': 'pgp/js-m',
        'js—m': 'pgp/js-m',
        'joseph smith—history': 'pgp/js-h',
        'joseph smith-history': 'pgp/js-h',
        'js-h': 'pgp/js-h',
        'js—h': 'pgp/js-h',
        'articles of faith': 'pgp/a-of-f',
        'a of f': 'pgp/a-of-f'
    };

    // Sort book names by length (longest first) for accurate matching
    const SORTED_BOOK_NAMES = Object.keys(BOOK_MAP).sort((a, b) => b.length - a.length);

    // Build regex pattern for scripture detection
    // Matches: "Book Chapter:Verse" or "Book Chapter:VerseStart-VerseEnd"
    function buildPattern() {
        // Escape special regex characters in book names
        const escapedNames = SORTED_BOOK_NAMES.map(name => 
            name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        );
        
        // Pattern breakdown:
        // - Book name (case insensitive)
        // - Optional space
        // - Chapter number
        // - Colon
        // - Verse number
        // - Optional verse range (-EndVerse)
        // - Optional additional verses (,Verse or ,Verse-Verse)
        const bookPattern = escapedNames.join('|');
        return new RegExp(
            `\\b(${bookPattern})\\s*(\\d+):(\\d+)(?:[-–—](\\d+))?(?:\\s*,\\s*(\\d+)(?:[-–—](\\d+))?)*`,
            'gi'
        );
    }

    const SCRIPTURE_PATTERN = buildPattern();

    /**
     * Generate the churchofjesuschrist.org URL for a scripture reference
     */
    function generateUrl(book, chapter, verseStart, verseEnd) {
        const bookPath = BOOK_MAP[book.toLowerCase()];
        if (!bookPath) return null;

        let url = `https://www.churchofjesuschrist.org/study/scriptures/${bookPath}/${chapter}?lang=eng`;
        
        if (verseStart) {
            if (verseEnd && verseEnd !== verseStart) {
                // Verse range: highlight all verses, anchor to first
                url += `&id=p${verseStart}-p${verseEnd}#p${verseStart}`;
            } else {
                // Single verse
                url += `&id=p${verseStart}#p${verseStart}`;
            }
        }

        return url;
    }

    /**
     * Parse a scripture reference string and return URL
     */
    function parseReference(refText) {
        // Reset regex lastIndex
        SCRIPTURE_PATTERN.lastIndex = 0;
        const match = SCRIPTURE_PATTERN.exec(refText);
        
        if (!match) return null;

        const book = match[1];
        const chapter = match[2];
        const verseStart = match[3];
        const verseEnd = match[4] || verseStart;

        return generateUrl(book, chapter, verseStart, verseEnd);
    }

    /**
     * Process a text node and replace scripture references with links
     */
    function processTextNode(textNode, container) {
        const text = textNode.textContent;
        SCRIPTURE_PATTERN.lastIndex = 0;
        
        if (!SCRIPTURE_PATTERN.test(text)) return;

        // Reset and find all matches
        SCRIPTURE_PATTERN.lastIndex = 0;
        const fragment = document.createDocumentFragment();
        let lastIndex = 0;
        let match;

        while ((match = SCRIPTURE_PATTERN.exec(text)) !== null) {
            // Add text before match
            if (match.index > lastIndex) {
                fragment.appendChild(
                    document.createTextNode(text.slice(lastIndex, match.index))
                );
            }

            // Create link for the match
            const fullMatch = match[0];
            const book = match[1];
            const chapter = match[2];
            const verseStart = match[3];
            const verseEnd = match[4] || verseStart;

            const url = generateUrl(book, chapter, verseStart, verseEnd);

            if (url) {
                const link = document.createElement('a');
                link.href = url;
                link.textContent = fullMatch;
                link.className = 'scripture-link';
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.title = `Read ${fullMatch} at churchofjesuschrist.org`;
                
                // CRITICAL: Stop propagation to prevent triggering parent handlers
                // (e.g., audio seek on chapter pages)
                link.addEventListener('click', function(e) {
                    e.stopPropagation();
                });

                fragment.appendChild(link);
            } else {
                // No URL found, keep original text
                fragment.appendChild(document.createTextNode(fullMatch));
            }

            lastIndex = match.index + fullMatch.length;
        }

        // Add remaining text
        if (lastIndex < text.length) {
            fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
        }

        // Replace original text node with fragment
        textNode.parentNode.replaceChild(fragment, textNode);
    }

    /**
     * Walk the DOM tree and process all text nodes
     */
    function walkDOM(node) {
        // Skip certain elements
        const skipTags = ['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'CODE', 'PRE', 'A'];
        
        if (node.nodeType === Node.TEXT_NODE) {
            // Check if parent is not a link already
            if (node.parentNode && node.parentNode.tagName !== 'A') {
                processTextNode(node);
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (skipTags.includes(node.tagName)) return;
            
            // Process child nodes (convert to array first since we modify the DOM)
            const children = Array.from(node.childNodes);
            children.forEach(child => walkDOM(child));
        }
    }

    /**
     * Initialize the scripture linker
     * @param {string|Element} container - Optional selector or element to limit scope
     */
    function init(container) {
        let root;
        
        if (typeof container === 'string') {
            root = document.querySelector(container);
        } else if (container instanceof Element) {
            root = container;
        } else {
            root = document.body;
        }

        if (!root) {
            console.warn('ScriptureLinker: Container not found');
            return;
        }

        walkDOM(root);
        console.log('ScriptureLinker: Initialized');
    }

    /**
     * Process a single element (useful for dynamically added content)
     */
    function process(element) {
        if (element instanceof Element) {
            walkDOM(element);
        }
    }

    /**
     * Get URL for a reference string (utility function)
     */
    function getUrl(reference) {
        return parseReference(reference);
    }

    // Public API
    return {
        init: init,
        process: process,
        getUrl: getUrl,
        BOOK_MAP: BOOK_MAP
    };
})();

// Auto-initialize when DOM is ready (can be disabled by setting window.SCRIPTURE_LINKER_MANUAL = true)
if (typeof window !== 'undefined' && !window.SCRIPTURE_LINKER_MANUAL) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            ScriptureLinker.init();
        });
    } else {
        // DOM already loaded
        ScriptureLinker.init();
    }
}
