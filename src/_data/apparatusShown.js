/**
 * apparatusShown.js: the apparatus the Articles page embeds (CODE-AOID2-28).
 *
 * apparatusData.json holds every Article's apparatus, including the new Article 1 (key A14),
 * because the floor check (scripts/aoid-verify-floors.js) reads that file. The Second Edition
 * switch (src/_data/aoidSecondEdition.js) keeps A14 off the public page: with the switch OFF
 * the embedded data is the thirteen First Edition Articles exactly as before; with it ON it is
 * the whole file. The same holds for the Article 11 spans s20-s25 (CODE-AOID2-29), the Article 9 additions (CODE-AOID2-32), the Article 13 span s12 (CODE-AOID2-34) the Article 4 span s19 (CODE-AOID2-35) the Article 5 spans s17-s18 (CODE-AOID2-36) the Article 8 additions (CODE-AOID2-40) and the Article 12 additions (CODE-AOID2-41). AOID2 step 104 (CODE-AOID2-65) extends the same markers to Articles 3, 7, 10 and 13 and to anchor refs, texts and cross-reference titles.
 */
const all = require('./apparatusData.json');
const { on } = require('./aoidSecondEdition.js');

/* Article 11 spans added for the Second Edition (CODE-AOID2-29, step 79): s20-s25; and s26, the first disciples' baptism
   (CODE-AOID2-49). With the switch OFF they have no text on the page, so their apparatus is not embedded either.
   s9, s10 and s14 carry Second Edition text or comments (CODE-AOID2-49), marked as for Article 9: `text_first_edition`,
   `panel_comment_first_edition`, and an anchor's `second_edition: true`. */
const A11_SECOND_EDITION = ['s20', 's21', 's22', 's23', 's24', 's25', 's26'];

/* Article 9 (CODE-AOID2-32, step 79): spans s23-s29 are new, and s6-s9 carry Second Edition additions. The
   data marks them: an anchor with `second_edition: true`; a revised `text` with the First Edition wording in
   `text_first_edition`; a changed anchor `comment` with the First Edition one in `comment_first_edition`.
   With the switch OFF the First Edition values are restored and the additions dropped; the marker fields are
   never embedded. */
const A09_SECOND_EDITION = ['s23', 's24', 's25', 's26', 's27', 's28', 's29'];

/* Article 13 (CODE-AOID2-34, step 79): span s12 is new (the Great Commission, G12), so it is dropped with the switch OFF. */
const A13_SECOND_EDITION = ['s12'];

/* Article 4 (CODE-AOID2-35, step 79): span s19 is new (the apostolic witness, G1), so it is dropped with the switch OFF. */
const A04_SECOND_EDITION = ['s19'];

/* Article 5 (CODE-AOID2-36, step 79): spans s17 (G13) and s18 (G2) are new, so they are dropped with the switch OFF.
   Spans s9 and s14 carry revised `text` (CODE-AOID2-64, step 102), marked as for Article 9 (`text_first_edition`). */
const A05_SECOND_EDITION = ['s17', 's18'];

/* Article 8 (CODE-AOID2-40, step 82): spans s18-s21 are new, and s1, s9 and s11 carry revised text, marked as for
   Article 9 (`text_first_edition`). With the switch OFF the new spans are dropped and the First Edition text restored. */
const A08_SECOND_EDITION = ['s18', 's19', 's20', 's21'];

/* Article 12 (CODE-AOID2-41, step 82): spans s11 (G10) and s12 (G11) are new. s5 and s6 carry revised `text`
   (`text_first_edition`, as Article 9). s1-s10 carry a revised `panel_comment`, with the First Edition comment in
   `panel_comment_first_edition`: the first span-level marker for a changed panel comment. Anchors added to s4-s6 are
   marked `second_edition: true`. With the switch OFF the First Edition values are restored and the additions dropped;
   with it ON the marker fields are stripped, so none is ever embedded. */
const A12_SECOND_EDITION = ['s11', 's12'];

/* Article 9 (CODE-AOID2-46): an anchor with `first_edition_only: true` is the mirror of `second_edition: true`. It stays
   with the switch OFF and is dropped with the switch ON (A09 s4, D&C 35:17-18). The marker is never embedded. */
/* AOID2 step 104 (CODE-AOID2-65): the commentary corrections reach anchors and cross-references too. An anchor may carry
   `ref_first_edition`, `text_first_edition` and `comment_first_edition`, and a cross-reference `title_first_edition`: the
   First Edition value, held beside the corrected one on the `panel_comment_first_edition` pattern. With the switch OFF the
   First Edition value replaces the field (key order kept); with it ON the marker is stripped. No marker is ever embedded. */
const ANCHOR_FIELDS = ['ref', 'text', 'comment'];
const isAnchorMarker = (k) => k === 'second_edition' || k === 'first_edition_only' || ANCHOR_FIELDS.some((f) => k === f + '_first_edition');
const firstEditionAnchor = (a) => {
  const out = {};
  for (const [k, v] of Object.entries(a)) {
    if (isAnchorMarker(k)) continue;
    out[k] = ANCHOR_FIELDS.includes(k) && a[k + '_first_edition'] !== undefined ? a[k + '_first_edition'] : v;
  }
  return out;
};
const firstEditionCrossref = (c) => {
  const out = {};
  for (const [k, v] of Object.entries(c)) {
    if (k === 'title_first_edition') continue;
    out[k] = k === 'title' && c.title_first_edition !== undefined ? c.title_first_edition : v;
  }
  return out;
};
const firstEditionSpan = (s) => {
  const out = {};
  for (const [k, v] of Object.entries(s)) {
    if (k === 'text_first_edition' || k === 'panel_comment_first_edition') continue;
    if (k === 'text' && s.text_first_edition !== undefined) out.text = s.text_first_edition;
    else if (k === 'panel_comment' && s.panel_comment_first_edition !== undefined) out.panel_comment = s.panel_comment_first_edition;
    else if (k === 'biblical' || k === 'restoration') out[k] = v.filter((a) => !a.second_edition).map(firstEditionAnchor);
    else if (k === 'crossref' && Array.isArray(v)) out[k] = v.map(firstEditionCrossref);
    else out[k] = v;
  }
  return out;
};
const secondEditionAnchor = (a) => {
  const out = {};
  for (const [k, v] of Object.entries(a)) if (!isAnchorMarker(k)) out[k] = v;
  return out;
};
const secondEditionCrossref = (c) => {
  const { title_first_edition, ...rest } = c;
  return rest;
};
const secondEditionSpan = (s) => {
  const { text_first_edition, panel_comment_first_edition, ...rest } = s;
  const out = { ...rest };
  for (const k of ['biblical', 'restoration']) if (Array.isArray(rest[k])) out[k] = rest[k].filter((a) => !a.first_edition_only).map(secondEditionAnchor);
  if (Array.isArray(rest.crossref)) out.crossref = rest.crossref.map(secondEditionCrossref);
  return out;
};
const mapSpans = (spans, f) => Object.fromEntries(Object.entries(spans).map(([id, s]) => [id, f(s)]));

module.exports = on
  ? Object.fromEntries(Object.entries(all).map(([key, spans]) => [key, ['A03', 'A05', 'A07', 'A08', 'A09', 'A10', 'A11', 'A12', 'A13'].includes(key) ? mapSpans(spans, secondEditionSpan) : spans]))
  : Object.fromEntries(
      Object.entries(all)
        .filter(([key]) => key !== 'A14')
        .map(([key, spans]) => {
          if (key === 'A11') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A11_SECOND_EDITION.includes(id))), firstEditionSpan)];
          if (key === 'A08') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A08_SECOND_EDITION.includes(id))), firstEditionSpan)];
          if (key === 'A12') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A12_SECOND_EDITION.includes(id))), firstEditionSpan)];
          if (key === 'A09') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A09_SECOND_EDITION.includes(id))), firstEditionSpan)];
          if (key === 'A04') return [key, Object.fromEntries(Object.entries(spans).filter(([id]) => !A04_SECOND_EDITION.includes(id)))];
          if (key === 'A05') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A05_SECOND_EDITION.includes(id))), firstEditionSpan)];
          if (key === 'A13') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A13_SECOND_EDITION.includes(id))), firstEditionSpan)];
          if (key === 'A03' || key === 'A07' || key === 'A10') return [key, mapSpans(spans, firstEditionSpan)];
          return [key, spans];
        })
    );
