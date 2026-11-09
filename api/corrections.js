/**
 * Reader correction form (CODE-AOID2-110). SWITCHED OFF unless CORRECTIONS_ENABLED is "true".
 *
 * POST /api/corrections
 *   JSON (from the page's script) or application/x-www-form-urlencoded (the same form with no script).
 *   Checks, in order: the switch, the settings, the honeypot, a minimum time to fill in, the fields,
 *   the Cloudflare Turnstile token (verified server-side), then delivers through Resend.
 *   JSON in, JSON out; a plain form post gets a short HTML page back.
 *
 * Environment variables and privacy rules: see api/_corrections-core.js.
 */

const core = require('./_corrections-core');

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function wantsHtml(req) {
  const ct = String((req.headers && req.headers['content-type']) || '');
  return ct.startsWith('application/x-www-form-urlencoded') || ct.startsWith('multipart/form-data');
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Robots-Tag', 'noindex');
  let out;
  if (req.method !== 'POST') {
    out = { status: 405, body: { ok: false, step: 'method', message: 'Use the form on the corrections page to send a correction.' } };
    res.setHeader('Allow', 'POST');
  } else {
    let body = req.body;
    if (typeof body === 'string') {
      try { body = JSON.parse(body); } catch (e) { body = Object.fromEntries(new URLSearchParams(body)); }
    }
    out = await core.handle(process.env, body || {});
  }
  if (req.method === 'POST' && wantsHtml(req)) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(out.status).send(
      '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex">' +
      '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Corrections</title></head>' +
      '<body style="font-family:Georgia,serif;max-width:36rem;margin:3rem auto;padding:0 1rem;line-height:1.6">' +
      `<p>${esc(out.body.message)}</p><p><a href="/corrections/">Back to the form</a></p></body></html>`
    );
  }
  return res.status(out.status).json(out.body);
};
