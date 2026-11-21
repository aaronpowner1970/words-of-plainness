// Plainness Favoring parity harness: v1.88 (frozen reference) against the rebuilt Lattice Lab.
// Spec: WoP_SITE_PlainnessFavoring_RebuildSpec_APPROVED_20261118.md, Section 5.
//
//   Reference only:  PARITY_REFERENCE=<path to v1.88> npm run parity:lattice
//   Against a rebuild: also set PARITY_CANDIDATE=<path or URL of the rebuilt Lab page>
//   Compare two runs:  npm run parity:lattice:compare -- <runA> <runB>
//
// All output goes to PARITY_OUT_ROOT (default wop-scratch\Plainness_Favoring\parity), never into git.
import path from 'node:path';
import { defineConfig } from '@playwright/test';
import { getConfig } from './lib/config.mjs';

const cfg = getConfig();

export default defineConfig({
  testDir: './specs',
  outputDir: path.join(cfg.runDir, '_playwright'),
  timeout: 5 * 60 * 1000,
  expect: { timeout: 10000 },
  fullyParallel: true,
  workers: Number(process.env.PARITY_WORKERS || 2),
  retries: 0,
  reporter: [['list'], ['json', { outputFile: path.join(cfg.runDir, 'playwright-results.json') }]],
  globalSetup: './global-setup.mjs',
  globalTeardown: './global-teardown.mjs',
  use: { headless: true, acceptDownloads: true, trace: 'off', video: 'off', screenshot: 'off' },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium', launchOptions: { args: ['--autoplay-policy=no-user-gesture-required'] } } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
