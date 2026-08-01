// Re-exports chapter-status.yaml under a JavaScript-safe key
// (`chapterStatus`) so Nunjucks templates can access it as
// `chapterStatus.volume_1` without needing bracket notation for the
// hyphenated original filename.
const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

module.exports = function () {
    const yamlPath = path.join(__dirname, "chapter-status.yaml");
    const raw = fs.readFileSync(yamlPath, "utf8");
    return yaml.load(raw);
};
