// Before any scenario: fingerprint the reference, extract and hash its media, write the run manifest.
import path from 'node:path';
import { getConfig, fingerprint, ensureDir, writeJson } from './lib/config.mjs';
import { extractReferenceMedia } from './lib/media.mjs';
import { loadDmap } from './lib/dmap.mjs';

export default async function globalSetup() {
  const cfg = getConfig();
  ensureDir(cfg.runDir);
  const media = extractReferenceMedia(cfg.referencePath, cfg.mediaDir);
  const dmap = loadDmap();
  writeJson(path.join(cfg.runDir, 'run-manifest.json'), {
    run: cfg.run,
    startedAt: new Date().toISOString(),
    reference: fingerprint(cfg.referencePath),
    candidate: cfg.candidate ? { ...cfg.candidate, ...(cfg.candidate.kind === 'file' ? fingerprint(cfg.candidate.path) : {}) } : null,
    selfParity: cfg.selfParity,
    seed: cfg.seed,
    fonts: cfg.fonts,
    fixedTime: cfg.fixedTime,
    media: media.items.map(({ role, mime, bytes, sha256 }) => ({ role, mime, bytes, sha256 })),
    plannedDifferences: dmap.raw.items.map(i => ({ id: i.id, excuses: (i.excuses || []).length, placeholders: (i.excuses || []).filter(e => e.kind === 'placeholder').map(e => e.name) })),
  });
}
