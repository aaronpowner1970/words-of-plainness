/**
 * Lantern Post: narration upload with read-back.
 *
 * POST /api/lantern-narration?date=YYYY-MM-DD&filename=narration.m4a
 *   headers: x-lantern-password, content-type: application/octet-stream
 *   body: the raw audio bytes (not base64, not a form)
 *   Saves lantern/inbox/<date>/narration.<ext> on main through the GitHub
 *   contents API, reads it back from that commit, and returns a receipt only if
 *   the byte length and SHA-256 match what was received.
 *
 * GET /api/lantern-narration?date=YYYY-MM-DD   (same password header)
 *   Reports what is already on file for that date, measured from the repo copy.
 *
 * Environment variables: LANTERN_CONSOLE_PASSWORD, GITHUB_CONTENTS_TOKEN.
 * Core logic and the rest of the settings: api/_lantern-narration-core.js.
 */

const core = require('./_lantern-narration-core');

async function readBody(req) {
  if (Buffer.isBuffer(req.body)) return req.body;
  if (typeof req.body === 'string') return Buffer.from(req.body, 'latin1');
  const chunks = [];
  let total = 0;
  for await (const c of req) {
    total += c.length;
    if (total > core.MAX_BYTES + 1024 * 1024) break; // stop reading absurd bodies
    chunks.push(c);
  }
  return Buffer.concat(chunks);
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Robots-Tag', 'noindex');
  const send = (status, body) => res.status(status).json(body);
  try {
    if (req.method !== 'POST' && req.method !== 'GET') {
      return send(405, { ok: false, step: 'method', error: 'Use POST to send a file or GET to check one.' });
    }
    // Configuration first: a missing variable is named, never hidden.
    core.checkConfig(process.env);
    core.checkPassword(process.env, req.headers['x-lantern-password']);
    const date = req.query && req.query.date;
    if (req.method === 'GET') {
      return send(200, await core.lookupNarration(process.env, { date }));
    }
    const declared = Number(req.headers['content-length'] || 0);
    if (declared > core.MAX_BYTES + 64 * 1024) {
      core.validateUpload(Buffer.alloc(core.MAX_BYTES + 1), req.query && req.query.filename);
    }
    const buf = await readBody(req);
    return send(200, await core.saveNarration(process.env, {
      date, filename: req.query && req.query.filename, buf,
    }));
  } catch (e) {
    if (e instanceof core.Step) return send(e.status, { ok: false, step: e.step, error: e.message });
    console.error('lantern-narration unexpected error:', e && e.message);
    return send(500, { ok: false, step: 'unexpected', error: 'Something unexpected went wrong on the server, and nothing is confirmed. Try again; if it repeats, tell Claude the time.' });
  }
};
