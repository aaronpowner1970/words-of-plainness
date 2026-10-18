// Self-test for the narration upload route (api/_lantern-narration-core.js).
// Runs the real save/read-back code against a fake GitHub server on localhost.
// Needs ffmpeg on PATH to make the sample audio. Run:
//   node --test tools/lantern/test/narration.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const core = require('../../../api/_lantern-narration-core.js');
const handler = require('../../../api/lantern-narration.js');

const REPO = 'aaronpowner1970/words-of-plainness';
let server; let base; let tmp;
const state = { files: new Map(), commits: [], snapshots: new Map(), corrupt: null, reject: false };

const blobSha = (b) => crypto.createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex');
function commitNow(message) {
  const sha = crypto.randomBytes(20).toString('hex');
  state.snapshots.set(sha, new Map(state.files));
  state.commits.push({ sha, message, date: new Date().toISOString() });
  return sha;
}

function fakeGithub(req, res) {
  const u = new URL(req.url, 'http://x');
  const pre = `/repos/${REPO}`;
  if (!u.pathname.startsWith(pre) || req.headers.authorization !== 'Bearer test-token') { res.writeHead(401); return res.end('{}'); }
  const rest = decodeURIComponent(u.pathname.slice(pre.length));
  const chunks = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', () => {
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : null;
    const json = (code, o) => { res.writeHead(code, { 'content-type': 'application/json' }); res.end(JSON.stringify(o)); };
    if (rest === '/commits') return json(200, state.commits.slice().reverse().map((c) => ({ sha: c.sha, commit: { committer: { date: c.date } } })));
    if (!rest.startsWith('/contents/')) return json(404, {});
    const p = rest.slice('/contents/'.length);
    if (req.method === 'PUT') {
      if (state.reject) return json(403, { message: 'nope' });
      const buf = Buffer.from(body.content, 'base64');
      const old = state.files.get(p);
      if (old && body.sha !== old.sha) return json(409, {});
      state.files.set(p, { buf, sha: blobSha(buf) });
      return json(200, { content: { sha: blobSha(buf) }, commit: { sha: commitNow(body.message) } });
    }
    if (req.method === 'DELETE') {
      state.files.delete(p);
      return json(200, { commit: { sha: commitNow(body.message) } });
    }
    const ref = u.searchParams.get('ref');
    const snap = state.snapshots.get(ref) || state.files;
    if ((req.headers.accept || '').includes('raw')) {
      const f = snap.get(p);
      if (!f) return json(404, {});
      let out = f.buf;
      if (state.corrupt === 'truncate') out = out.subarray(0, out.length - 10);
      if (state.corrupt === 'flip') { out = Buffer.from(out); out[out.length - 1] ^= 0xff; }
      res.writeHead(200, { 'content-type': 'application/octet-stream' });
      return res.end(out);
    }
    const dir = [...snap.entries()].filter(([k]) => k.startsWith(`${p}/`)).map(([k, v]) => ({ type: 'file', name: k.slice(p.length + 1), sha: v.sha, path: k }));
    if (!dir.length) return json(404, {});
    return json(200, dir);
  });
}

const env = () => ({
  LANTERN_CONSOLE_PASSWORD: 'pw', GITHUB_CONTENTS_TOKEN: 'test-token', LANTERN_GITHUB_API: base,
});
const ff = (args, out) => {
  const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', ...args, out], { encoding: 'buffer' });
  assert.equal(r.status, 0, String(r.stderr));
  return fs.readFileSync(out);
};
const samples = {};

before(async () => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lantern-'));
  samples.m4a = ff(['-c:a', 'aac', '-b:a', '64k'], path.join(tmp, 'a.m4a'));
  samples.mp4 = ff(['-c:a', 'aac', '-b:a', '64k', '-f', 'mp4'], path.join(tmp, 'a.mp4'));
  samples.mp3 = ff(['-c:a', 'libmp3lame', '-b:a', '64k'], path.join(tmp, 'a.mp3'));
  samples.aac = ff(['-c:a', 'aac', '-b:a', '64k', '-f', 'adts'], path.join(tmp, 'a.aac'));
  samples.ogg = ff(['-c:a', 'libvorbis'], path.join(tmp, 'a.ogg'));
  // Browser-style WebM: written to a pipe so the header has no Duration, like MediaRecorder output.
  const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', '-c:a', 'libopus', '-f', 'webm', 'pipe:1'], { maxBuffer: 1 << 26 });
  assert.equal(r.status, 0);
  samples.webm = r.stdout;
  samples.wav = ff([], path.join(tmp, 'a.wav'));
  samples.big = Buffer.concat([samples.m4a, crypto.randomBytes(4.5 * 1024 * 1024)]);
  server = http.createServer(fakeGithub);
  await new Promise((r2) => server.listen(0, '127.0.0.1', r2));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => { server.close(); fs.rmSync(tmp, { recursive: true, force: true }); });

for (const ext of ['m4a', 'mp4', 'mp3', 'aac', 'ogg', 'webm']) {
  test(`accepts ${ext}: saves, reads back, measures about 3 seconds`, async () => {
    const date = `2026-11-0${['m4a', 'mp4', 'mp3', 'aac', 'ogg', 'webm'].indexOf(ext) + 1}`;
    const r = await core.saveNarration(env(), { date, filename: `voice.${ext}`, buf: samples[ext] });
    assert.equal(r.ok, true);
    assert.equal(r.name, `narration.${ext}`);
    assert.equal(r.bytes, samples[ext].length);
    assert.equal(r.sha256, core.sha256(samples[ext]));
    assert.ok(Math.abs(r.seconds - 3) < 0.35, `duration ${r.seconds}`);
    assert.match(r.commit, /^[0-9a-f]{40}$/);
    assert.equal(r.replaced, false);
    console.log(`  ${ext}: ${r.text} [${r.bytes} bytes, ${r.seconds}s]`);
    const again = await core.lookupNarration(env(), { date });
    assert.equal(again.onFile, true);
    assert.equal(again.bytes, samples[ext].length);
  });
}

test('second send for the same date is reported as a replacement and old file is removed', async () => {
  const date = '2026-12-01';
  await core.saveNarration(env(), { date, filename: 'x.m4a', buf: samples.m4a });
  const r = await core.saveNarration(env(), { date, filename: 'y.mp3', buf: samples.mp3 });
  assert.equal(r.replaced, true);
  assert.match(r.text, /replaced/);
  assert.ok(!state.files.has(`lantern/inbox/${date}/narration.m4a`));
  assert.ok(state.files.has(`lantern/inbox/${date}/narration.mp3`));
});

test('oversize file is refused with the plain message', async () => {
  await assert.rejects(core.saveNarration(env(), { date: '2026-12-02', filename: 'a.m4a', buf: samples.big }), (e) => e.step === 'size' && /4 MB/.test(e.message) && /compressed/.test(e.message));
  assert.ok(![...state.files.keys()].some((k) => k.includes('2026-12-02')));
});

test('WAV is refused with the plain message', async () => {
  await assert.rejects(core.saveNarration(env(), { date: '2026-12-03', filename: 'a.wav', buf: samples.wav }), (e) => e.step === 'format' && /compressed/.test(e.message));
  await assert.rejects(core.saveNarration(env(), { date: '2026-12-03', filename: 'a.m4a', buf: samples.wav }), (e) => e.step === 'format');
});

test('a read-back that is shorter or different is an error, never a receipt', async () => {
  for (const mode of ['truncate', 'flip']) {
    state.corrupt = mode;
    await assert.rejects(core.saveNarration(env(), { date: '2026-12-04', filename: 'a.m4a', buf: samples.m4a }), (e) => e.step === 'compare' && /NOT confirmed/.test(e.message));
  }
  state.corrupt = null;
});

test('GitHub refusing the write is an error naming the write step', async () => {
  state.reject = true;
  await assert.rejects(core.saveNarration(env(), { date: '2026-12-05', filename: 'a.m4a', buf: samples.m4a }), (e) => e.step === 'write');
  state.reject = false;
});

test('missing variables are named', async () => {
  for (const name of ['GITHUB_CONTENTS_TOKEN', 'LANTERN_CONSOLE_PASSWORD']) {
    const e = env(); delete e[name];
    await assert.rejects(core.saveNarration(e, { date: '2026-12-06', filename: 'a.m4a', buf: samples.m4a }), (x) => x.step === 'config' && x.message.includes(name));
  }
});

test('HTTP handler: wrong password 401, missing token names the variable, good request 200', async () => {
  const mk = (method, headers, query, body) => {
    const out = {};
    const res = { setHeader() {}, status(c) { out.status = c; return this; }, json(o) { out.body = o; return this; } };
    return { req: { method, headers, query, body }, res, out };
  };
  Object.assign(process.env, env());
  let m = mk('POST', { 'x-lantern-password': 'bad' }, { date: '2026-12-07', filename: 'a.m4a' }, samples.m4a);
  await handler(m.req, m.res); assert.equal(m.out.status, 401);
  m = mk('POST', { 'x-lantern-password': 'pw' }, { date: '2026-12-07', filename: 'a.m4a' }, samples.m4a);
  await handler(m.req, m.res); assert.equal(m.out.status, 200); assert.equal(m.out.body.ok, true);
  m = mk('GET', { 'x-lantern-password': 'pw' }, { date: '2026-12-07' });
  await handler(m.req, m.res); assert.equal(m.out.body.onFile, true);
  delete process.env.GITHUB_CONTENTS_TOKEN;
  m = mk('GET', { 'x-lantern-password': 'pw' }, { date: '2026-12-07' });
  await handler(m.req, m.res); assert.equal(m.out.status, 500); assert.match(m.out.body.error, /GITHUB_CONTENTS_TOKEN/);
});
