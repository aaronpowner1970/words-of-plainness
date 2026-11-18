/* Reflection sources for the device-only journal (CODE-SITE-18, SITE step 27).

   The Articles reflection prompts, read at build time from the Article includes
   that /articles/ shows (src/_includes/aoid/a01.njk ... a13.njk), so that an
   Articles answer carried over from the old wop-rjw-* storage can be labelled
   with its prompt in a download even on a page that does not show that prompt.
   The page template src/pages/wop-reflection-sources.njk writes this, with the
   chapters' pause prompts, to /js/wop-reflection-sources.js.

   A prompt may hold the Second Edition switch's own if/else; the branch the
   current build shows is kept. Nothing here is reader-facing on its own. */
const fs = require('fs');
const path = require('path');
const { on } = require('./aoidSecondEdition.js');

const IF_ELSE = /\{%-?\s*if\s+aoidSecondEdition\.on\s*-?%\}([\s\S]*?)\{%-?\s*else\s*-?%\}([\s\S]*?)\{%-?\s*endif\s*-?%\}/g;
const IF_ONLY = /\{%-?\s*if\s+aoidSecondEdition\.on\s*-?%\}([\s\S]*?)\{%-?\s*endif\s*-?%\}/g;

function edition(text) {
    return text
        .replace(IF_ELSE, (m, a, b) => (on ? a : b))
        .replace(IF_ONLY, (m, a) => (on ? a : ''));
}

module.exports = function () {
    const dir = path.join(__dirname, '..', '_includes', 'aoid');
    const articles = {};
    for (let n = 1; n <= 13; n++) {
        const nn = String(n).padStart(2, '0');
        const file = path.join(dir, `a${nn}.njk`);
        if (!fs.existsSync(file)) continue;
        const text = fs.readFileSync(file, 'utf8');
        const prompt = text.match(/<p class="rjw-prompt">([\s\S]*?)<\/p>/);
        const title = text.match(/aria-label="Reflect on ([^"]*)"/);
        if (!prompt) continue;
        articles[`A${nn}`] = {
            title: title ? title[1] : '',
            prompt: edition(prompt[1]).trim()
        };
    }
    return { articles };
};
