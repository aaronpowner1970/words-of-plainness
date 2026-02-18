/**
 * Words of Plainness - Eleventy Configuration
 * 
 * This configuration file controls how Eleventy builds the site.
 * @see https://www.11ty.dev/docs/config/
 */

const fs = require('fs');
const path = require('path');
const scriptureData = require('./src/_data/scriptures.json');

module.exports = function(eleventyConfig) {

    // =========================================
    // DEV SERVER - Eleventy v2 built-in server
    // Enable HTTP range requests for audio seeking
    // =========================================

    eleventyConfig.setServerOptions({
        middleware: [
            function(req, res, next) {
                // Only intercept audio/video files
                if (!/\.(mp3|mp4|ogg|wav|m4a|webm)$/i.test(req.url)) {
                    return next();
                }

                const filePath = path.join(__dirname, '_site', decodeURIComponent(req.url.split('?')[0]));

                let stat;
                try {
                    stat = fs.statSync(filePath);
                } catch (e) {
                    return next();
                }

                const total = stat.size;
                const mimeTypes = {
                    '.mp3': 'audio/mpeg',
                    '.mp4': 'video/mp4',
                    '.ogg': 'audio/ogg',
                    '.wav': 'audio/wav',
                    '.m4a': 'audio/mp4',
                    '.webm': 'video/webm'
                };
                const ext = path.extname(filePath).toLowerCase();
                const contentType = mimeTypes[ext] || 'application/octet-stream';
                const range = req.headers.range;

                if (range) {
                    const parts = range.replace(/bytes=/, '').split('-');
                    const start = parseInt(parts[0], 10);
                    const end = parts[1] ? parseInt(parts[1], 10) : total - 1;

                    res.writeHead(206, {
                        'Content-Range': `bytes ${start}-${end}/${total}`,
                        'Accept-Ranges': 'bytes',
                        'Content-Length': end - start + 1,
                        'Content-Type': contentType
                    });
                    fs.createReadStream(filePath, { start, end }).pipe(res);
                } else {
                    res.writeHead(200, {
                        'Accept-Ranges': 'bytes',
                        'Content-Length': total,
                        'Content-Type': contentType
                    });
                    fs.createReadStream(filePath).pipe(res);
                }
            }
        ]
    });

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
        return collectionApi.getFilteredByGlob("src/chapters/*.{md,njk}")
            .filter(item => !path.basename(item.inputPath).startsWith("_"))
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

    // Scripture book mappings as JSON (for client-side injection)
    eleventyConfig.addFilter("scriptureBooksJson", function() {
        const data = require('./src/_data/scriptures.json');
        return JSON.stringify(data.books);
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
        
        const bookMappings = scriptureData.books;
        
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
            url += `?lang=eng&id=p${verseStart}-p${verseEnd}#p${verseStart}-p${verseEnd}`;
        } else {
            url += `?lang=eng&id=p${verseStart}#p${verseStart}`;
        }
        
        return url;
    }
    
    // =========================================
    // CONFIGURATION
    // =========================================
    
    // Ignore template/internal files and retired chapters (underscore-prefixed)
    eleventyConfig.ignores.add("src/chapters/_*");

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
