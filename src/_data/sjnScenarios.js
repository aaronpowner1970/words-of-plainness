/**
 * Seeking Jesus of Nazareth — M5 scenario cards (hand-authored content, AUTHOR_RATIFIED).
 * Source of truth: src/_data/sjnScenariosContent.json (Cowork v2, ratified by AJP 2026-09-09).
 * This wrapper resolves scripture references in each card's `sources` to
 * churchofjesuschrist.org links using the site's book map, at build time.
 */
const draft = require("./sjnScenariosContent.json");
const scriptures = require("./scriptures.json");

function scriptureUrl(ref) {
    const m = String(ref || "").match(/^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/);
    if (!m) return null;
    const p = scriptures.books[m[1].toLowerCase().trim()];
    if (!p) return null;
    const base = `https://www.churchofjesuschrist.org/study/scriptures/${p}/${m[2]}`;
    return m[4] ? `${base}?lang=eng&id=p${m[3]}-p${m[4]}#p${m[3]}` : `${base}?lang=eng&id=p${m[3]}#p${m[3]}`;
}

module.exports = function () {
    return {
        status: draft.status,
        version: draft.version,
        four_clause: draft.four_clause,
        scenarios: draft.scenarios.map((s) => ({
            ...s,
            lens_label: s.lens === "latter_day_saint" ? "Latter-day Saint learner" : "Learner from another Christian tradition",
            source_links: (s.sources || []).map((ref) => ({ ref, url: scriptureUrl(ref) }))
        }))
    };
};
