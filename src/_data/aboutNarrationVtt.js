// WebVTT for the /about/ narration, generated from about_narration_timing.json
// (the single source of truth). Cue identifier = target ID, cue text = target ID.
// Served at /about/narration.vtt and attached to the player as a metadata <track>.
const timing = require('./about_narration_timing.json');

function stamp(sec) {
    const ms = Math.round(sec * 1000);
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    const pad = (n, w) => String(n).padStart(w, '0');
    return `${pad(h, 2)}:${pad(m, 2)}:${pad(s, 2)}.${pad(ms % 1000, 3)}`;
}

module.exports = function () {
    const lines = ['WEBVTT', ''];
    for (const [id, t] of Object.entries(timing.targets)) {
        lines.push(id, `${stamp(t.start)} --> ${stamp(t.end)}`, id, '');
    }
    return lines.join('\n');
};
