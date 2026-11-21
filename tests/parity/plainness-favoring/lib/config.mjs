// Run configuration for the Plainness Favoring parity harness (SITE step 46, run A).
//
// Environment variables
//   PARITY_REFERENCE   required. Path to the frozen v1.88 file. Read in place; never copied.
//   PARITY_CANDIDATE   optional. Path or http(s) URL of the rebuilt Lab page. Unset: reference only.
//   PARITY_OUT_ROOT    optional. Where every output goes. Default: wop-scratch\Plainness_Favoring\parity.
//                      Refused if it resolves inside the repo, so test output cannot be committed.
//   PARITY_RUN         optional. Run label; output lands in <out root>\runs\<label>. Default: timestamp.
//   PARITY_SEED        optional. Seed for the Math.random replacement. Default 18112026.
//   PARITY_FONTS       optional. "stub" (default) answers the reference's Google Fonts request with an
//                      empty stylesheet on both sides, so layout never depends on the network; "live"
//                      lets it through.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const HARNESS_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const REPO_ROOT = path.resolve(HARNESS_DIR, '..', '..', '..');
const DEFAULT_OUT_ROOT = 'C:\\Users\\aaron\\Documents\\wop-scratch\\Plainness_Favoring\\parity';

function inside(child, parent) {
  const rel = path.relative(parent.toLowerCase(), child.toLowerCase());
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

export function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

export function fingerprint(file) {
  const st = fs.statSync(file);
  return { path: file, bytes: st.size, modified: st.mtime.toISOString(), sha256: sha256File(file) };
}

let cached = null;
export function getConfig() {
  if (cached) return cached;
  const refRaw = process.env.PARITY_REFERENCE;
  if (!refRaw) throw new Error('PARITY_REFERENCE is not set. Point it at plainness-lattice-v1.88.html (it is read in place, never copied).');
  const referencePath = path.resolve(refRaw);
  if (!fs.existsSync(referencePath)) throw new Error(`PARITY_REFERENCE does not exist: ${referencePath}`);
  if (inside(referencePath, REPO_ROOT)) throw new Error('PARITY_REFERENCE is inside the repo. The frozen reference must stay outside git.');

  const outRoot = path.resolve(process.env.PARITY_OUT_ROOT || DEFAULT_OUT_ROOT);
  if (inside(outRoot, REPO_ROOT)) throw new Error(`PARITY_OUT_ROOT resolves inside the repo (${outRoot}). Test output must never land in git.`);

  if (!process.env.PARITY_RUN) {
    process.env.PARITY_RUN = 'run-' + new Date().toISOString().replace(/[:.]/g, '').replace('T', '-').slice(0, 15);
  }
  const run = process.env.PARITY_RUN;
  if (!/^[\w.-]+$/.test(run)) throw new Error('PARITY_RUN may use letters, digits, dot, dash and underscore only.');
  const runDir = path.join(outRoot, 'runs', run);

  let candidate = null;
  const candRaw = process.env.PARITY_CANDIDATE || '';
  if (candRaw) {
    if (/^https?:\/\//i.test(candRaw)) {
      candidate = { kind: 'url', url: candRaw, label: candRaw };
    } else {
      const p = path.resolve(candRaw);
      if (!fs.existsSync(p)) throw new Error(`PARITY_CANDIDATE does not exist: ${p}`);
      candidate = { kind: 'file', path: p, url: pathToFileURL(p).href, label: p };
    }
  }
  const referenceSha = sha256File(referencePath);
  // Self-parity: the candidate is byte-identical to the reference. The planned-differences
  // map is still applied, but its placeholder and required-difference checks are skipped,
  // because there is no rebuild for them to find.
  const selfParity = !!candidate && candidate.kind === 'file' && sha256File(candidate.path) === referenceSha;

  cached = {
    referencePath,
    referenceUrl: pathToFileURL(referencePath).href,
    referenceSha,
    candidate,
    selfParity,
    outRoot,
    run,
    runDir,
    mediaDir: path.join(outRoot, 'media'),
    seed: Number(process.env.PARITY_SEED || 18112026),
    fonts: (process.env.PARITY_FONTS || 'stub').toLowerCase(),
    fixedTime: '2026-11-18T12:00:00.000Z',
  };
  return cached;
}

export function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function writeJson(file, value) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', 'utf8');
}
