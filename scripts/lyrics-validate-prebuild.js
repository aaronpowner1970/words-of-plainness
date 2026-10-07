#!/usr/bin/env node
/**
 * Build hook for the lyric validator (Lyric-Sync Standard, G4).
 *
 * Runs tools/wop_validate_lyrics.py --build, which refreshes
 * src/_data/lyricsValidation.json. WARN-ONLY by default: this script never
 * fails the build. LYRICS_STRICT=1 makes a real validation failure fail it
 * (switched on in Run 3, once the catalog is clean).
 *
 * If Python or its packages (pyyaml, beautifulsoup4) are not available (for
 * example on the deploy host), the committed lyricsValidation.json is used
 * as-is and .eleventy.js warns when a VTT has changed since it was written.
 */
const { spawnSync } = require('child_process');
const path = require('path');

const script = path.join(__dirname, '..', 'tools', 'wop_validate_lyrics.py');
const strict = process.env.LYRICS_STRICT === '1';
let r;
for (const py of ['python', 'python3']) {
  r = spawnSync(py, [script, '--build'], { encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  if (!r.error) break;
}
if (r.error || (r.status !== 0 && /ModuleNotFoundError|ImportError/.test(r.stderr || ''))) {
  console.warn('[lyrics] validator could not run here (' + (r.error ? r.error.code : 'python packages missing') +
    '); using committed src/_data/lyricsValidation.json');
  process.exit(0);
}
if (r.stdout) process.stdout.write(r.stdout);
if (r.stderr) process.stderr.write(r.stderr);
process.exit(strict && r.status !== 0 ? r.status : 0);
