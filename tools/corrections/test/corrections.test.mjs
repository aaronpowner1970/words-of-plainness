// Self-test for the reader correction route (api/_corrections-core.js and api/corrections.js).
// No network: Cloudflare's siteverify and Resend are fakes. No real key or address is used anywhere.
// Run:  node --test tools/corrections/test/corrections.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const core = require('../../../api/_corrections-core.js');
const handler = require('../../../api/corrections.js');

const OPEN = {
  CORRECTIONS_ENABLED: 'true',
  TURNSTILE_SECRET_KEY: 'test-secret',
  RESEND_API_KEY: 'test-resend-key',
  CORRECTIONS_FROM: 'Corrections <from@example.test>',
  CORRECTIONS_TO: 'to@example.test',
};

const GOOD = {
  name: 'A Reader', email: 'reader@example.test', tradition: 'Anglican', page: 'Article 6',
  cited: 'Canon B 1', wrong: 'Wrong edition', source: 'https://example.test/canons',
  message: 'Please check the edition.', website: '', elapsed_ms: '30000', 'cf-turnstile-response': 'tok',
};

function fakeFetch({ verify = { success: true }, sendOk = true } = {}) {
  const calls = [];
  const fn = async (url, init) => {
    calls.push({ url, init });
    if (url.includes('siteverify')) return { status: 200, ok: true, json: async () => verify };
    if (url.includes('api.resend.com')) return { status: sendOk ? 200 : 422, ok: sendOk, json: async () => ({}) };
    throw new Error('unexpected url ' + url);
  };
  fn.calls = calls;
  return fn;
}

function captureLogs() {
  const lines = [];
  const orig = { error: console.error, log: console.log, warn: console.warn };
  for (const k of Object.keys(orig)) console[k] = (...a) => lines.push(a.join(' '));
  return { lines, restore: () => Object.assign(console, orig) };
}

test('flag unset: refused as not yet open, nothing sent', async () => {
  const f = fakeFetch();
  const env = { ...OPEN }; delete env.CORRECTIONS_ENABLED;
  const out = await core.handle(env, GOOD, { fetch: f });
  assert.equal(out.status, 503);
  assert.equal(out.body.step, 'closed');
  assert.match(out.body.message, /not yet open/);
  assert.equal(f.calls.length, 0);
});

test('flag set to anything but "true": still closed', async () => {
  for (const v of ['1', 'TRUE', 'yes', 'false', ' true']) {
    const f = fakeFetch();
    const out = await core.handle({ ...OPEN, CORRECTIONS_ENABLED: v }, GOOD, { fetch: f });
    assert.equal(out.body.step, 'closed', v);
    assert.equal(f.calls.length, 0);
  }
});

test('flag on but a setting missing: refused, nothing sent', async () => {
  const f = fakeFetch();
  const env = { ...OPEN }; delete env.RESEND_API_KEY;
  const log = captureLogs();
  const out = await core.handle(env, GOOD, { fetch: f });
  log.restore();
  assert.equal(out.body.step, 'config');
  assert.equal(f.calls.length, 0);
});

test('honeypot hit: rejected, nothing sent', async () => {
  const f = fakeFetch();
  const out = await core.handle(OPEN, { ...GOOD, website: 'http://spam.test' }, { fetch: f });
  assert.equal(out.status, 400);
  assert.equal(out.body.step, 'rejected');
  assert.equal(f.calls.length, 0);
});

test('too quick: rejected, nothing sent', async () => {
  const f = fakeFetch();
  for (const ms of ['0', '1500', '', 'abc']) {
    const out = await core.handle(OPEN, { ...GOOD, elapsed_ms: ms }, { fetch: f });
    assert.equal(out.body.step, 'rejected', ms);
  }
  assert.equal(f.calls.length, 0);
});

test('missing Turnstile token: rejected before any network call', async () => {
  const f = fakeFetch();
  const body = { ...GOOD }; delete body['cf-turnstile-response'];
  const out = await core.handle(OPEN, body, { fetch: f });
  assert.equal(out.status, 400);
  assert.equal(out.body.step, 'turnstile');
  assert.equal(f.calls.length, 0);
});

test('Turnstile token refused by siteverify: rejected, nothing sent', async () => {
  const f = fakeFetch({ verify: { success: false, 'error-codes': ['invalid-input-response'] } });
  const log = captureLogs();
  const out = await core.handle(OPEN, GOOD, { fetch: f });
  log.restore();
  assert.equal(out.body.step, 'turnstile');
  assert.equal(f.calls.length, 1);
  assert.match(f.calls[0].url, /siteverify/);
});

test('required free-text field empty: refused', async () => {
  const f = fakeFetch();
  const out = await core.handle(OPEN, { ...GOOD, message: '   ' }, { fetch: f });
  assert.equal(out.body.step, 'invalid');
  assert.equal(f.calls.length, 0);
});

test('tradition must be one of the sixteen families or Other', async () => {
  assert.equal(core.FAMILIES.length, 16);
  assert.ok(core.TRADITIONS.includes('Other'));
  const out = await core.handle(OPEN, { ...GOOD, tradition: 'Made Up' }, { fetch: fakeFetch() });
  assert.equal(out.body.step, 'invalid');
});

test('valid submission: siteverify then Resend, with the right From, To, Reply-To and subject', async () => {
  const f = fakeFetch();
  const out = await core.handle(OPEN, GOOD, { fetch: f });
  assert.equal(out.status, 200);
  assert.equal(out.body.ok, true);
  assert.equal(f.calls.length, 2);
  const verify = new URLSearchParams(f.calls[0].init.body);
  assert.equal(verify.get('secret'), 'test-secret');
  assert.equal(verify.get('response'), 'tok');
  assert.equal(verify.get('remoteip'), null, 'no IP address is sent');
  const mail = JSON.parse(f.calls[1].init.body);
  assert.equal(f.calls[1].init.headers.authorization, 'Bearer test-resend-key');
  assert.equal(mail.from, OPEN.CORRECTIONS_FROM);
  assert.deepEqual(mail.to, ['to@example.test']);
  assert.equal(mail.reply_to, 'reader@example.test');
  assert.ok(mail.subject.startsWith('[AOID2 correction] '));
  assert.match(mail.text, /Please check the edition\./);
});

test('no email given: no Reply-To', async () => {
  const f = fakeFetch();
  const out = await core.handle(OPEN, { ...GOOD, email: '' }, { fetch: f });
  assert.equal(out.status, 200);
  const mail = JSON.parse(f.calls[1].init.body);
  assert.equal('reply_to' in mail, false);
});

test('Resend refuses: reported as not sent', async () => {
  const log = captureLogs();
  const out = await core.handle(OPEN, GOOD, { fetch: fakeFetch({ sendOk: false }) });
  log.restore();
  assert.equal(out.status, 502);
  assert.equal(out.body.step, 'send');
});

test('no field content is ever logged', async () => {
  const log = captureLogs();
  await core.handle(OPEN, GOOD, { fetch: fakeFetch({ verify: { success: false } }) });
  await core.handle(OPEN, GOOD, { fetch: fakeFetch({ sendOk: false }) });
  await core.handle({ ...OPEN, RESEND_API_KEY: '' }, GOOD, { fetch: fakeFetch() });
  log.restore();
  const all = log.lines.join('\n');
  for (const v of ['A Reader', 'reader@example.test', 'Article 6', 'Canon B 1', 'Wrong edition', 'example.test/canons', 'Please check', 'tok', 'test-secret', 'test-resend-key']) {
    assert.equal(all.includes(v), false, 'logged: ' + v);
  }
});

test('the deployed handler with the flag unset (as now in production) refuses JSON and form posts', async () => {
  const saved = process.env.CORRECTIONS_ENABLED;
  delete process.env.CORRECTIONS_ENABLED;
  try {
    for (const ct of ['application/json', 'application/x-www-form-urlencoded']) {
      const res = { headers: {}, code: 0, payload: null,
        setHeader(k, v) { this.headers[k.toLowerCase()] = v; },
        status(c) { this.code = c; return this; },
        json(o) { this.payload = o; return this; },
        send(s) { this.payload = s; return this; } };
      await handler({ method: 'POST', headers: { 'content-type': ct }, body: GOOD }, res);
      assert.equal(res.code, 503, ct);
      assert.match(JSON.stringify(res.payload), /not yet open/);
      assert.equal(res.headers['cache-control'], 'no-store');
    }
  } finally {
    if (saved !== undefined) process.env.CORRECTIONS_ENABLED = saved;
  }
});
