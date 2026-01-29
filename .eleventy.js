/**
 * Words of Plainness - Eleventy Configuration
 * 
 * This configuration file controls how Eleventy builds the site.
 * @see https://www.11ty.dev/docs/config/
 */

module.exports = function(eleventyConfig) {
    
    // =========================================
    // PASSTHROUGH COPY
    // These files/folders are copied as-is to _site
    // =========================================
    
    eleventyConfig.addPassthroughCopy("src/assets");
    eleventyConfig.addPassthroughCopy("src/css");
    eleventyConfig.addPassthroughCopy("src/js");
    
    // =========================================
    // WATCH TARGETS
    // Rebuild when these files change
    // =========================================
    
    eleventyConfig.addWatchTarget("src/css/");
    eleventyConfig.addWatchTarget("src/js/");
    
    // =========================================
    // COLLECTIONS
    // Group content for listing/navigation
    // =========================================
    
    // Chapters collection - sorted by chapter number
    eleventyConfig.addCollection("chapters", function(collectionApi) {
        return collectionApi.getFilteredByGlob("src/chapters/*.md")
            .sort((a, b) => a.data.chapter - b.data.chapter);
    });
    
    // =========================================
    // FILTERS
    // Transform data in templates
    // =========================================
    
    // JSON stringify for passing data to JavaScript
    eleventyConfig.addFilter("dump", obj => JSON.stringify(obj, null, 2));
    
    // JSON stringify without pretty printing (for inline use)
    eleventyConfig.addFilter("json", obj => JSON.stringify(obj));
    
    // Current year/date for templates
    eleventyConfig.addFilter("now", (value, format) => {
        if (format === "YYYY") return new Date().getFullYear();
        return new Date().toISOString();
    });

    // Format reading time
    eleventyConfig.addFilter("readingTime", minutes => {
        if (minutes < 1) return "< 1 min read";
        return `~${minutes} min read`;
    });
    
    // =========================================
    // SHORTCODES
    // Reusable content snippets
    // =========================================
    
    // Sentence span for audio sync
    // Usage: {% sentence 0 %}Content here{% endsentence %}
    eleventyConfig.addPairedShortcode("sentence", function(content, index) {
        return `<span class="sentence" data-index="${index}">${content.trim()}</span>`;
    });
    
    // Scripture link (build-time)
    // Usage: {% scripture "Alma 42:8" %}
    eleventyConfig.addShortcode("scripture", function(reference) {
        const url = generateScriptureUrl(reference);
        return `<a href="${url}" class="scripture-link" target="_blank" rel="noopener">${reference}</a>`;
    });
    
    // =========================================
    // HELPER FUNCTIONS
    // =========================================
    
    /**
     * Generate churchofjesuschrist.org scripture URL from reference
     * @param {string} reference - e.g., "Alma 42:8", "2 Nephi 31:3", "John 3:16"
     * @returns {string} Full URL to scripture
     */
    function generateScriptureUrl(reference) {
        const baseUrl = "https://www.churchofjesuschrist.org/study/scriptures";
        
        // Book mappings
        const bookMappings = {
            // Book of Mormon
            "1 nephi": "bofm/1-ne",
            "2 nephi": "bofm/2-ne",
            "jacob": "bofm/jacob",
            "enos": "bofm/enos",
            "jarom": "bofm/jarom",
            "omni": "bofm/omni",
            "words of mormon": "bofm/w-of-m",
            "mosiah": "bofm/mosiah",
            "alma": "bofm/alma",
            "helaman": "bofm/hel",
            "3 nephi": "bofm/3-ne",
            "4 nephi": "bofm/4-ne",
            "mormon": "bofm/morm",
            "ether": "bofm/ether",
            "moroni": "bofm/moro",
            
            // Doctrine and Covenants
            "d&c": "dc-testament/dc",
            "doctrine and covenants": "dc-testament/dc",
            
            // Pearl of Great Price
            "moses": "pgp/moses",
            "abraham": "pgp/abr",
            "joseph smith—matthew": "pgp/js-m",
            "joseph smith—history": "pgp/js-h",
            "articles of faith": "pgp/a-of-f",
            
            // Old Testament
            "genesis": "ot/gen",
            "exodus": "ot/ex",
            "leviticus": "ot/lev",
            "numbers": "ot/num",
            "deuteronomy": "ot/deut",
            "joshua": "ot/josh",
            "judges": "ot/judg",
            "ruth": "ot/ruth",
            "1 samuel": "ot/1-sam",
            "2 samuel": "ot/2-sam",
            "1 kings": "ot/1-kgs",
            "2 kings": "ot/2-kgs",
            "1 chronicles": "ot/1-chr",
            "2 chronicles": "ot/2-chr",
            "ezra": "ot/ezra",
            "nehemiah": "ot/neh",
            "esther": "ot/esth",
            "job": "ot/job",
            "psalms": "ot/ps",
            "psalm": "ot/ps",
            "proverbs": "ot/prov",
            "ecclesiastes": "ot/eccl",
            "song of solomon": "ot/song",
            "isaiah": "ot/isa",
            "jeremiah": "ot/jer",
            "lamentations": "ot/lam",
            "ezekiel": "ot/ezek",
            "daniel": "ot/dan",
            "hosea": "ot/hosea",
            "joel": "ot/joel",
            "amos": "ot/amos",
            "obadiah": "ot/obad",
            "jonah": "ot/jonah",
            "micah": "ot/micah",
            "nahum": "ot/nahum",
            "habakkuk": "ot/hab",
            "zephaniah": "ot/zeph",
            "haggai": "ot/hag",
            "zechariah": "ot/zech",
            "malachi": "ot/mal",
            
            // New Testament
            "matthew": "nt/matt",
            "mark": "nt/mark",
            "luke": "nt/luke",
            "john": "nt/john",
            "acts": "nt/acts",
            "romans": "nt/rom",
            "1 corinthians": "nt/1-cor",
            "2 corinthians": "nt/2-cor",
            "galatians": "nt/gal",
            "ephesians": "nt/eph",
            "philippians": "nt/philip",
            "colossians": "nt/col",
            "1 thessalonians": "nt/1-thes",
            "2 thessalonians": "nt/2-thes",
            "1 timothy": "nt/1-tim",
            "2 timothy": "nt/2-tim",
            "titus": "nt/titus",
            "philemon": "nt/philem",
            "hebrews": "nt/heb",
            "james": "nt/james",
            "1 peter": "nt/1-pet",
            "2 peter": "nt/2-pet",
            "1 john": "nt/1-jn",
            "2 john": "nt/2-jn",
            "3 john": "nt/3-jn",
            "jude": "nt/jude",
            "revelation": "nt/rev"
        };
        
        // Parse reference: "Alma 42:8" or "2 Nephi 31:3-5"
        const match = reference.match(/^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/i);
        
        if (!match) {
            console.warn(`Could not parse scripture reference: ${reference}`);
            return `${baseUrl}`;
        }
        
        const [, book, chapter, verseStart, verseEnd] = match;
        const bookKey = book.toLowerCase().trim();
        const bookPath = bookMappings[bookKey];
        
        if (!bookPath) {
            console.warn(`Unknown book: ${book}`);
            return `${baseUrl}`;
        }
        
        // Build URL with verse anchor
        let url = `${baseUrl}/${bookPath}/${chapter}`;
        if (verseEnd) {
            url += `?id=p${verseStart}-p${verseEnd}#p${verseStart}`;
        } else {
            url += `?id=p${verseStart}#p${verseStart}`;
        }
        
        return url;
    }
    
    // =========================================
    // CONFIGURATION
    // =========================================
    
    // Ignore template files that aren't actual content
    eleventyConfig.ignores.add("src/chapters/_template.md");

    return {
        dir: {
            input: "src",
            output: "_site",
            includes: "_includes",
            data: "_data"
        },
        templateFormats: ["njk", "md", "html"],
        markdownTemplateEngine: "njk",
        htmlTemplateEngine: "njk"
    };
};
