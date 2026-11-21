// Media inside v1.88: every data: URI is decoded, hashed and written outside git.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { ensureDir, writeJson } from './config.mjs';

const sha = buf => crypto.createHash('sha256').update(buf).digest('hex');
const EXT = { 'audio/mpeg': 'mp3', 'video/mp4': 'mp4', 'image/png': 'png' };

// Roles follow the markup: the logo <img>, the full reading (#readingAudio), the cube film <video>,
// and the ten line clips (lineClips array in the script, in line order).
export function extractReferenceMedia(referencePath, mediaDir) {
  const html = fs.readFileSync(referencePath, 'utf8');
  const re = /data:([\w/+.-]+);base64,([A-Za-z0-9+/=\s]+)/g;
  const found = [];
  let m;
  while ((m = re.exec(html))) {
    const before = html.slice(Math.max(0, m.index - 160), m.index);
    found.push({ mime: m[1], b64: m[2], before, index: m.index });
  }
  const items = [];
  let clip = 0;
  for (const f of found) {
    let role;
    if (/<img[^>]*class="tl-logo"[^>]*src="$/.test(f.before)) role = 'logo';
    else if (/id="readingAudio" src="$/.test(f.before)) role = 'reading';
    else if (/<video[^>]*src="$/.test(f.before)) role = 'film';
    else if (f.mime === 'audio/mpeg') role = 'clip' + String(++clip).padStart(2, '0');
    else role = 'other' + items.length;
    const buf = Buffer.from(f.b64.replace(/\s+/g, ''), 'base64');
    items.push({ role, mime: f.mime, bytes: buf.length, sha256: sha(buf), buf });
  }
  ensureDir(mediaDir);
  for (const it of items) {
    const file = path.join(mediaDir, `${it.role}.${EXT[it.mime] || 'bin'}`);
    if (!fs.existsSync(file) || sha(fs.readFileSync(file)) !== it.sha256) fs.writeFileSync(file, it.buf);
    it.file = file;
    delete it.buf;
  }
  const manifest = { reference: referencePath, extracted: items.length, items };
  writeJson(path.join(mediaDir, 'media-hashes.json'), manifest);
  return manifest;
}

export function hashBuffer(buf) { return sha(buf); }
