/**
 * Lantern narration route: core logic (no HTTP framework, so it can be tested).
 *
 * Files whose names start with an underscore in api/ are not deployed as
 * functions; api/lantern-narration.js is the function and requires this file.
 *
 * Environment variables:
 *   LANTERN_CONSOLE_PASSWORD — the password Aaron types on the Approve page
 *   GITHUB_CONTENTS_TOKEN    — fine-grained token, Contents read+write on the repo
 *   LANTERN_GITHUB_REPO      — optional, default aaronpowner1970/words-of-plainness
 *   LANTERN_GITHUB_API       — optional, default https://api.github.com (tests only)
 */

const crypto = require('crypto');

const REPO_DEFAULT = 'aaronpowner1970/words-of-plainness';
const MAX_BYTES = 4 * 1024 * 1024;
const EXT_KINDS = {
  m4a: 'mp4', mp4: 'mp4', mp3: 'mp3', aac: 'aac', webm: 'webm', ogg: 'ogg',
};
const COMPRESSED_HINT =
  'Please record in a compressed format (the Record button here, or Voice Memos as m4a), not WAV, and keep it under 4 MB.';

class Step extends Error {
  constructor(status, step, message) {
    super(message);
    this.status = status;
    this.step = step;
  }
}

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function safeEqual(a, b) {
  const ha = crypto.createHash('sha256').update(String(a)).digest();
  const hb = crypto.createHash('sha256').update(String(b)).digest();
  return crypto.timingSafeEqual(ha, hb);
}

function checkConfig(env) {
  for (const name of ['LANTERN_CONSOLE_PASSWORD', 'GITHUB_CONTENTS_TOKEN']) {
    if (!env[name]) {
      throw new Step(500, 'config', `The site is missing the setting ${name}, so nothing was saved. Aaron must add ${name} in Vercel (Project Settings, Environment Variables) and redeploy.`);
    }
  }
}

function checkPassword(env, given) {
  if (!given || !safeEqual(given, env.LANTERN_CONSOLE_PASSWORD)) {
    throw new Step(401, 'password', 'That password is not right, so nothing was saved.');
  }
}

function parseDate(date) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || '');
  const d = m && new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (!m || d.getUTCFullYear() !== +m[1] || d.getUTCMonth() !== +m[2] - 1 || d.getUTCDate() !== +m[3]) {
    throw new Step(400, 'date', 'The date is not a real date in the form YYYY-MM-DD.');
  }
  return date;
}

/** What the bytes themselves say they are. */
function sniff(buf) {
  if (buf.length < 12) return 'unknown';
  if (buf.toString('latin1', 0, 4) === 'RIFF' && buf.toString('latin1', 8, 12) === 'WAVE') return 'wav';
  if (buf.toString('latin1', 4, 8) === 'ftyp') return 'mp4';
  if (buf.toString('latin1', 0, 4) === 'OggS') return 'ogg';
  if (buf[0] === 0x1a && buf[1] === 0x45 && buf[2] === 0xdf && buf[3] === 0xa3) return 'webm';
  if (buf.toString('latin1', 0, 3) === 'ID3') return 'id3'; // mp3 or aac with a tag in front
  if (buf[0] === 0xff && (buf[1] & 0xf6) === 0xf0) return 'aac'; // ADTS
  if (buf[0] === 0xff && (buf[1] & 0xe0) === 0xe0) return 'mp3';
  return 'unknown';
}

function validateUpload(buf, filename) {
  if (!buf || !buf.length) throw new Step(400, 'receive', 'The server received an empty file, so nothing was saved.');
  const ext = (/\.([A-Za-z0-9]+)$/.exec(filename || '') || [])[1];
  const lower = ext ? ext.toLowerCase() : '';
  const kind = sniff(buf);
  if (lower === 'wav' || kind === 'wav') {
    throw new Step(415, 'format', `WAV files are too large for this page. ${COMPRESSED_HINT}`);
  }
  if (buf.length > MAX_BYTES) {
    throw new Step(413, 'size', `That file is ${(buf.length / 1048576).toFixed(1)} MB, over the 4 MB limit. ${COMPRESSED_HINT}`);
  }
  const want = EXT_KINDS[lower];
  if (!want) {
    throw new Step(415, 'format', `Files ending in .${lower || '(none)'} are not accepted. Use m4a, mp4, mp3, aac, webm or ogg.`);
  }
  const ok = kind === want || (kind === 'id3' && (want === 'mp3' || want === 'aac'));
  if (!ok) {
    throw new Step(415, 'format', `The file is named .${lower} but its contents do not look like that kind of audio, so nothing was saved.`);
  }
  return { ext: lower };
}

function etTime(date) {
  const parts = {};
  for (const p of new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', weekday: 'short', day: 'numeric', month: 'short',
    hour: 'numeric', minute: '2-digit', hour12: true,
  }).formatToParts(date)) parts[p.type] = p.value;
  return `${parts.weekday} ${parts.day} ${parts.month} ${parts.hour}:${parts.minute} ${parts.dayPeriod.toLowerCase()}`;
}

/**
 * Duration from the file itself. Plain Ogg/MP4/MP3 carry it; a browser-made
 * WebM has no duration field, so for WebM we also read the last block's time.
 */
async function measureDuration(buf, ext) {
  let seconds = null;
  try {
    const mm = require('music-metadata');
    const meta = await mm.parseBuffer(buf, undefined, { duration: true });
    if (meta.format && Number.isFinite(meta.format.duration) && meta.format.duration > 0) {
      seconds = meta.format.duration;
    }
  } catch (_) { /* fall through to the next method */ }
  if (seconds === null && ext === 'webm') seconds = webmDurationFromBlocks(buf);
  if (seconds === null) {
    throw new Step(422, 'duration', 'The file saved cleanly in my reading, but I could not measure how long it is, so it was not saved. Try the Record button here or a m4a file.');
  }
  return Math.round(seconds * 10) / 10;
}

/** Walks EBML: last Cluster timestamp + last block offset (+20 ms for the frame). */
function webmDurationFromBlocks(buf) {
  const readId = (p) => {
    const b = buf[p];
    if (b === undefined) return null;
    let len = 1;
    for (let m = 0x80; m && !(b & m); m >>= 1) len++;
    if (len > 4) return null;
    return { id: buf.readUIntBE(p, len), len };
  };
  const readSize = (p) => {
    const b = buf[p];
    if (b === undefined) return null;
    let len = 1;
    let m = 0x80;
    while (m && !(b & m)) { m >>= 1; len++; }
    if (len > 8) return null;
    let v = b & (m - 1);
    let unknown = v === m - 1;
    for (let i = 1; i < len; i++) { v = v * 256 + buf[p + i]; if (buf[p + i] !== 0xff) unknown = false; }
    return { size: unknown ? Infinity : v, len };
  };
  let timescale = 1000000;
  let best = 0;
  let found = false;
  const ts = { v: 0 };
  const walk = (start, end) => {
    let p = start;
    while (p < end) {
      const id = readId(p); if (!id) return;
      const sz = readSize(p + id.len); if (!sz) return;
      const body = p + id.len + sz.len;
      const stop = sz.size === Infinity ? end : Math.min(end, body + sz.size);
      if (id.id === 0x18538067 || id.id === 0x1f43b675 || id.id === 0x1549a966 || id.id === 0xa0) {
        // Segment, Cluster, Info, BlockGroup: descend
        walk(body, stop);
      } else if (id.id === 0x2ad7b1) { // TimestampScale
        timescale = buf.readUIntBE(body, Math.min(sz.size, 8));
      } else if (id.id === 0xe7) { // Cluster Timestamp
        ts.v = buf.readUIntBE(body, Math.min(sz.size, 6));
      } else if (id.id === 0xa3 || id.id === 0xa1) { // SimpleBlock / Block
        const tn = readSize(body); // track number, vint
        const rel = buf.readInt16BE(body + tn.len);
        const t = ts.v + rel;
        if (t > best) best = t;
        found = true;
      }
      p = stop;
    }
  };
  try { walk(0, buf.length); } catch (_) { return null; }
  if (!found) return null;
  return (best * timescale) / 1e9 + 0.02;
}

function ghConfig(env) {
  return {
    api: (env.LANTERN_GITHUB_API || 'https://api.github.com').replace(/\/$/, ''),
    repo: env.LANTERN_GITHUB_REPO || REPO_DEFAULT,
    token: env.GITHUB_CONTENTS_TOKEN,
  };
}

async function gh(cfg, method, path, { body, raw } = {}) {
  const headers = {
    Authorization: `Bearer ${cfg.token}`,
    Accept: raw ? 'application/vnd.github.raw+json' : 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'wop-lantern-narration',
  };
  if (body) headers['Content-Type'] = 'application/json';
  const res = await fetch(`${cfg.api}/repos/${cfg.repo}${path}`, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  });
  return res;
}

const dirPath = (date) => `lantern/inbox/${date}`;
const encPath = (p) => p.split('/').map(encodeURIComponent).join('/');

async function listNarrations(cfg, date) {
  const res = await gh(cfg, 'GET', `/contents/${encPath(dirPath(date))}?ref=main`);
  if (res.status === 404) return [];
  if (!res.ok) throw new Step(502, 'lookup', `GitHub would not list the folder for ${date} (status ${res.status}).`);
  const items = await res.json();
  return (Array.isArray(items) ? items : []).filter((i) => i.type === 'file' && /^narration\.[a-z0-9]+$/i.test(i.name));
}

async function fetchRaw(cfg, path, ref) {
  const res = await gh(cfg, 'GET', `/contents/${encPath(path)}?ref=${encodeURIComponent(ref)}`, { raw: true });
  if (!res.ok) throw new Step(502, 'read-back', `I could not read the file back from GitHub (status ${res.status}).`);
  return Buffer.from(await res.arrayBuffer());
}

function receiptFrom({ name, buf, seconds, commit, when, replaced, existing, date }) {
  const sizeMb = Math.round((buf.length / 1048576) * 10) / 10;
  const sizeText = buf.length < 104858 ? `${Math.max(1, Math.round(buf.length / 1024))} KB` : `${sizeMb.toFixed(1)} MB`;
  const text = `${existing ? 'On file' : 'Received'}: ${name}, ${seconds.toFixed(1)} seconds, ${sizeText}, ${etTime(when)}`;
  return {
    ok: true, date, name, bytes: buf.length, sizeMb, seconds, sha256: sha256(buf),
    commit, time: etTime(when), timeIso: when.toISOString(), replaced: !!replaced, existing: !!existing, text,
  };
}

/** Save, read back, compare, and only then return a receipt. */
async function saveNarration(env, { date, filename, buf }) {
  checkConfig(env);
  parseDate(date);
  const { ext } = validateUpload(buf, filename);
  const seconds = await measureDuration(buf, ext);
  const cfg = ghConfig(env);
  const name = `narration.${ext}`;
  const path = `${dirPath(date)}/${name}`;

  let earlier;
  try { earlier = await listNarrations(cfg, date); } catch (e) { throw e; }
  const same = earlier.find((i) => i.name.toLowerCase() === name);
  const others = earlier.filter((i) => i !== same);
  const replaced = earlier.length > 0;

  const put = await gh(cfg, 'PUT', `/contents/${encPath(path)}`, {
    body: {
      message: `Lantern: ${replaced ? 'replace' : 'add'} narration for ${date}`,
      content: buf.toString('base64'),
      branch: 'main',
      ...(same ? { sha: same.sha } : {}),
    },
  });
  if (!put.ok) {
    const detail = put.status === 401 || put.status === 403 ? ' The GitHub token may be wrong, expired, or lacking Contents write access.' : '';
    throw new Step(502, 'write', `GitHub refused the save (status ${put.status}).${detail} Nothing is confirmed.`);
  }
  const putJson = await put.json();
  const commit = putJson && putJson.commit && putJson.commit.sha;
  if (!commit) throw new Step(502, 'write', 'GitHub accepted the save but gave no commit number, so it is not confirmed.');

  // Read back from the exact commit, not from the write response.
  const back = await fetchRaw(cfg, path, commit);
  if (back.length !== buf.length) {
    throw new Step(502, 'compare', `Read-back failed: GitHub holds ${back.length} bytes but ${buf.length} were sent. The recording is NOT confirmed. Send it again.`);
  }
  if (sha256(back) !== sha256(buf)) {
    throw new Step(502, 'compare', 'Read-back failed: the file GitHub holds is not byte-for-byte the file that was sent. The recording is NOT confirmed. Send it again.');
  }

  let warning;
  for (const o of others) {
    const del = await gh(cfg, 'DELETE', `/contents/${encPath(`${dirPath(date)}/${o.name}`)}`, {
      body: { message: `Lantern: remove superseded ${o.name} for ${date}`, sha: o.sha, branch: 'main' },
    });
    if (!del.ok) warning = `The new narration is confirmed, but the older ${o.name} for ${date} could not be removed (status ${del.status}). Remove it by hand.`;
  }

  const r = receiptFrom({ name, buf: back, seconds, commit, when: new Date(), replaced, existing: false, date });
  if (replaced) r.text += ' (replaced an earlier narration)';
  if (warning) r.warning = warning;
  return r;
}

/** What is already on file for a date, measured from the repo's own copy. */
async function lookupNarration(env, { date }) {
  checkConfig(env);
  parseDate(date);
  const cfg = ghConfig(env);
  const found = await listNarrations(cfg, date);
  if (!found.length) return { ok: true, date, onFile: false, text: `No narration on file for ${date}.` };
  const item = found[0];
  const path = `${dirPath(date)}/${item.name}`;
  const buf = await fetchRaw(cfg, path, 'main');
  const ext = item.name.split('.').pop().toLowerCase();
  const seconds = await measureDuration(buf, ext);
  const cres = await gh(cfg, 'GET', `/commits?path=${encodeURIComponent(path)}&sha=main&per_page=1`);
  let commit = null;
  let when = new Date();
  if (cres.ok) {
    const list = await cres.json();
    if (list[0]) { commit = list[0].sha; when = new Date(list[0].commit.committer.date); }
  }
  const r = receiptFrom({ name: item.name, buf, seconds, commit, when, replaced: false, existing: true, date });
  r.onFile = true;
  return r;
}

module.exports = {
  Step, MAX_BYTES, checkConfig, checkPassword, parseDate, sniff, validateUpload,
  measureDuration, saveNarration, lookupNarration, etTime, sha256,
};
