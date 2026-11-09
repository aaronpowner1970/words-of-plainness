/**
 * Reader correction form: core logic (CODE-AOID2-110). No HTTP framework here, so it can be tested.
 * Files whose names start with an underscore in api/ are not deployed as functions;
 * api/corrections.js is the function and requires this file.
 *
 * SWITCHED OFF until Aaron turns it on. Every submission is refused with a polite "not yet open"
 * unless CORRECTIONS_ENABLED is exactly "true".
 *
 * Environment variables (names only; no value, and no address, is written anywhere in the repo):
 *   CORRECTIONS_ENABLED   "true" opens the form; anything else, or unset, keeps it closed
 *   TURNSTILE_SITE_KEY    Cloudflare Turnstile site key (public; read at build time by the page)
 *   TURNSTILE_SECRET_KEY  Cloudflare Turnstile secret, for the server-side siteverify call
 *   RESEND_API_KEY        Resend API key
 *   CORRECTIONS_FROM      the From address, on a domain verified in Resend
 *   CORRECTIONS_TO        where corrections are delivered (comma-separated for more than one)
 *
 * Privacy: nothing is stored. The only thing kept about a submitter is the email address they choose
 * to give, inside the delivered message (and as its Reply-To). No field content is ever logged; the
 * only log lines name a step and a status code.
 */

const SITEVERIFY = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const RESEND = 'https://api.resend.com/emails';
const SUBJECT_PREFIX = '[AOID2 correction]';
const MIN_MS = 4000; // a person takes longer than this to fill in the form
const HONEYPOT = 'website';
const LIMITS = { name: 200, email: 254, tradition: 80, page: 300, cited: 3000, wrong: 5000, source: 1000, message: 8000 };

// The sixteen family labels come from the Living Tree data the page is built from, so the form's list
// and the server's check can never drift apart. "Other" is the seventeenth choice.
function loadFamilies() {
  try {
    const data = require('../src/_data/livingTree.json'); // static path, so Vercel bundles the file
    return data.branches.filter((b) => b.kind === 'family').map((b) => b.label);
  } catch (e) {
    return [];
  }
}
const FAMILIES = loadFamilies();
const TRADITIONS = FAMILIES.concat(['Other']);

const MSG = {
  closed: 'Thank you for wanting to help. The correction form is not yet open, so nothing was sent. Please come back soon.',
  config: 'The correction form is not set up yet, so nothing was sent. Please come back soon.',
  rejected: 'We could not accept this submission, and nothing was sent.',
  invalid: 'Please check the form: ',
  turnstile: 'Please complete the check just above the Send button, then send again.',
  send: 'We could not send your correction just now, and nothing was stored. Please try again later.',
  sent: 'Thank you. Your correction has been sent.',
};

class Step extends Error {
  constructor(status, step, message) {
    super(message);
    this.status = status;
    this.step = step;
  }
}

const REQUIRED_CONFIG = ['TURNSTILE_SECRET_KEY', 'RESEND_API_KEY', 'CORRECTIONS_FROM', 'CORRECTIONS_TO'];

function isOpen(env) {
  return env.CORRECTIONS_ENABLED === 'true';
}

function str(v) {
  if (v === undefined || v === null) return '';
  if (Array.isArray(v)) v = v[0];
  return String(v).replace(/\r\n?/g, '\n').trim();
}

function oneLine(s) {
  return s.replace(/[\r\n\t]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
}

const EMAIL_RE = /^[^\s@<>(),;:"]+@[^\s@<>(),;:"]+\.[^\s@<>(),;:"]+$/;

function readFields(body) {
  const f = {
    name: oneLine(str(body.name)),
    email: oneLine(str(body.email)),
    tradition: oneLine(str(body.tradition)),
    page: oneLine(str(body.page)),
    cited: str(body.cited),
    wrong: str(body.wrong),
    source: oneLine(str(body.source)),
    message: str(body.message),
  };
  const problems = [];
  for (const [k, max] of Object.entries(LIMITS)) {
    if (f[k].length > max) problems.push(`one answer is too long (keep it under ${max} characters)`);
  }
  if (!f.message) problems.push('the box "Your correction, in your own words" is required');
  if (f.email && !EMAIL_RE.test(f.email)) problems.push('the email address does not look complete');
  if (f.tradition && !TRADITIONS.includes(f.tradition)) problems.push('choose a tradition from the list');
  if (f.source && !/^https?:\/\/\S+$/i.test(f.source)) problems.push('the source link should start with http:// or https://');
  if (problems.length) throw new Step(400, 'invalid', MSG.invalid + Array.from(new Set(problems)).join('; ') + '.');
  return f;
}

function subjectFor(f) {
  const bits = [f.tradition || 'No tradition given'];
  if (f.page) bits.push(f.page);
  return oneLine(`${SUBJECT_PREFIX} ${bits.join(' - ')}`).slice(0, 160);
}

function textFor(f) {
  const show = (v) => (v ? v : '(not given)');
  return [
    'A reader sent a correction through the Words of Plainness correction form.',
    '',
    `Name: ${show(f.name)}`,
    `Email for a reply: ${show(f.email)}`,
    `Tradition: ${show(f.tradition)}`,
    `Article or page: ${show(f.page)}`,
    `Supporting source: ${show(f.source)}`,
    '',
    'What we cited:',
    show(f.cited),
    '',
    'What is wrong:',
    show(f.wrong),
    '',
    'Their correction, in their own words:',
    f.message,
    '',
  ].join('\n');
}

async function verifyTurnstile(env, token, fetchFn) {
  const form = new URLSearchParams({ secret: env.TURNSTILE_SECRET_KEY, response: token });
  let res;
  try {
    res = await fetchFn(SITEVERIFY, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    });
  } catch (e) {
    console.error('corrections: siteverify unreachable');
    throw new Step(502, 'turnstile', MSG.send);
  }
  let out = {};
  try { out = await res.json(); } catch (e) { out = {}; }
  if (!out || out.success !== true) {
    console.error('corrections: siteverify refused', res.status);
    throw new Step(400, 'turnstile', MSG.turnstile);
  }
  return out;
}

async function sendMail(env, f, fetchFn) {
  const to = env.CORRECTIONS_TO.split(',').map((s) => s.trim()).filter(Boolean);
  const payload = { from: env.CORRECTIONS_FROM, to, subject: subjectFor(f), text: textFor(f) };
  if (f.email) payload.reply_to = f.email;
  let res;
  try {
    res = await fetchFn(RESEND, {
      method: 'POST',
      headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    console.error('corrections: resend unreachable');
    throw new Step(502, 'send', MSG.send);
  }
  if (!res.ok) {
    console.error('corrections: resend refused', res.status);
    throw new Step(502, 'send', MSG.send);
  }
}

/**
 * Decide one submission. Returns { status, body }. Never throws.
 *   env   process.env (or a test object)
 *   body  the parsed form fields
 *   opts  { fetch } (tests pass a fake)
 */
async function handle(env, body, opts = {}) {
  const fetchFn = opts.fetch || globalThis.fetch;
  try {
    if (!isOpen(env)) throw new Step(503, 'closed', MSG.closed);
    for (const name of REQUIRED_CONFIG) {
      if (!env[name]) {
        console.error('corrections: missing setting', name);
        throw new Step(503, 'config', MSG.config);
      }
    }
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Step(400, 'rejected', MSG.rejected);
    if (str(body[HONEYPOT])) throw new Step(400, 'rejected', MSG.rejected);
    const elapsed = Number(str(body.elapsed_ms));
    if (!Number.isFinite(elapsed) || elapsed < MIN_MS) throw new Step(400, 'rejected', MSG.rejected);
    const f = readFields(body);
    const token = str(body['cf-turnstile-response']);
    if (!token) throw new Step(400, 'turnstile', MSG.turnstile);
    await verifyTurnstile(env, token, fetchFn);
    await sendMail(env, f, fetchFn);
    return { status: 200, body: { ok: true, step: 'sent', message: MSG.sent } };
  } catch (e) {
    if (e instanceof Step) return { status: e.status, body: { ok: false, step: e.step, message: e.message } };
    console.error('corrections: unexpected error');
    return { status: 500, body: { ok: false, step: 'unexpected', message: MSG.send } };
  }
}

module.exports = { handle, isOpen, subjectFor, textFor, TRADITIONS, FAMILIES, MIN_MS, HONEYPOT, SUBJECT_PREFIX, MSG };
