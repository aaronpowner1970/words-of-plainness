/**
 * apparatusData.js — Eleventy JS data file
 * Reads all 13 per-article YAML files and returns the apparatus data object.
 * Available in templates as {{ apparatusData }}.
 *
 * Named apparatusData.js so the Eleventy key matches the template variable
 * exactly. (The older articles_apparatus.js was shadowed by articles_apparatus.json.)
 *
 * Build note: YAML source lives outside the repo in working-folder.
 * On Vercel the YAML_DIR won't exist; apparatusData returns {} and the panel
 * degrades gracefully (spans are still interactive, commentary unavailable).
 * To serve full apparatus on Vercel, commit a populated apparatusData.json
 * alongside this file — the JSON will take precedence over the JS.
 */

const fs   = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const YAML_DIR = path.join(
  'C:\\Users\\aaron\\Documents\\working-folder',
  'Articles_of_Interfaith_Discipleship_Essay_Cluster',
  'articles'
);

const ARTICLE_FILES = {
  A01: 'A01_Plainness.yaml',
  A02: 'A02_God.yaml',
  A03: 'A03_CreationAndLife.yaml',
  A04: 'A04_GodsWord.yaml',
  A05: 'A05_JesusChrist.yaml',
  A06: 'A06_Salvation.yaml',
  A07: 'A07_TheKingdomAtHand.yaml',
  A08: 'A08_FellowBelievers.yaml',
  A09: 'A09_FindingOurWay.yaml',
  A10: 'A10_LivingByGrace.yaml',
  A11: 'A11_CovenantsAndCommitments.yaml',
  A12: 'A12_ImmortalityAndEternalLife.yaml',
  A13: 'A13_OurConfidence.yaml',
};

module.exports = function buildApparatus() {
  if (!fs.existsSync(YAML_DIR)) {
    console.warn('[apparatusData.js] YAML dir not found — returning {}');
    return {};
  }

  const apparatus = {};

  for (const [aid, fname] of Object.entries(ARTICLE_FILES)) {
    const filePath = path.join(YAML_DIR, fname);
    if (!fs.existsSync(filePath)) {
      console.warn(`[apparatusData.js] Missing: ${fname}`);
      apparatus[aid] = {};
      continue;
    }

    let raw = fs.readFileSync(filePath, 'utf-8');
    raw = raw.replace(/\n---\s*$/, '').trim();

    let data;
    try {
      data = yaml.load(raw);
    } catch (e) {
      console.error(`[apparatusData.js] YAML parse error in ${fname}:`, e.message);
      apparatus[aid] = {};
      continue;
    }

    const spans = data.spans || [];
    apparatus[aid] = {};

    for (const s of spans) {
      apparatus[aid][s.id] = {
        text:          s.text          || '',
        type:          s.type          || '',
        named_concept: Boolean(s.named_concept),
        definition:    s.definition    || '',
        panel_comment: s.panel_comment || '',
        biblical: (s.biblical || []).map(a => ({
          ref:     a.ref     || '',
          text:    a.text    || '',
          comment: a.comment || '',
        })),
        restoration: (s.restoration || []).map(a => ({
          ref:     a.ref     || '',
          text:    a.text    || '',
          comment: a.comment || '',
        })),
        crossref: (s.crossref || []).map(c => ({
          label: c.label || '',
          title: c.title || '',
          href:  c.href  || '',
        })),
      };
    }
  }

  return apparatus;
};
