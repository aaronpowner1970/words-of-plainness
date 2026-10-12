/**
 * apparatusShown.js: the apparatus the Articles page embeds (CODE-AOID2-28).
 *
 * apparatusData.json holds every Article's apparatus, including the new Article 1 (key A14),
 * because the floor check (scripts/aoid-verify-floors.js) reads that file. The Second Edition
 * switch (src/_data/aoidSecondEdition.js) keeps A14 off the public page: with the switch OFF
 * the embedded data is the thirteen First Edition Articles exactly as before; with it ON it is
 * the whole file. The same holds for the Article 11 spans s20-s25 (CODE-AOID2-29) and the Article 9 additions (CODE-AOID2-32).
 */
const all = require('./apparatusData.json');
const { on } = require('./aoidSecondEdition.js');

/* Article 11 spans added for the Second Edition (CODE-AOID2-29, step 79): s20-s25. With the switch OFF
   they have no text on the page, so their apparatus is not embedded either. */
const A11_SECOND_EDITION = ['s20', 's21', 's22', 's23', 's24', 's25'];

/* Article 9 (CODE-AOID2-32, step 79): spans s23-s29 are new, and s6-s9 carry Second Edition additions. The
   data marks them: an anchor with `second_edition: true`; a revised `text` with the First Edition wording in
   `text_first_edition`; a changed anchor `comment` with the First Edition one in `comment_first_edition`.
   With the switch OFF the First Edition values are restored and the additions dropped; the marker fields are
   never embedded. */
const A09_SECOND_EDITION = ['s23', 's24', 's25', 's26', 's27', 's28', 's29'];

const firstEditionAnchor = (a) => {
  const { second_edition, comment_first_edition, ...rest } = a;
  return comment_first_edition === undefined ? rest : { ...rest, comment: comment_first_edition };
};
const firstEditionSpan = (s) => {
  const out = {};
  for (const [k, v] of Object.entries(s)) {
    if (k === 'text_first_edition') continue;
    if (k === 'text' && s.text_first_edition !== undefined) out.text = s.text_first_edition;
    else if (k === 'biblical' || k === 'restoration') out[k] = v.filter((a) => !a.second_edition).map(firstEditionAnchor);
    else out[k] = v;
  }
  return out;
};
const secondEditionAnchor = (a) => {
  const { second_edition, comment_first_edition, ...rest } = a;
  return rest;
};
const secondEditionSpan = (s) => {
  const { text_first_edition, ...rest } = s;
  const out = { ...rest };
  for (const k of ['biblical', 'restoration']) if (Array.isArray(rest[k])) out[k] = rest[k].map(secondEditionAnchor);
  return out;
};
const mapSpans = (spans, f) => Object.fromEntries(Object.entries(spans).map(([id, s]) => [id, f(s)]));

module.exports = on
  ? Object.fromEntries(Object.entries(all).map(([key, spans]) => [key, key === 'A09' ? mapSpans(spans, secondEditionSpan) : spans]))
  : Object.fromEntries(
      Object.entries(all)
        .filter(([key]) => key !== 'A14')
        .map(([key, spans]) => {
          if (key === 'A11') return [key, Object.fromEntries(Object.entries(spans).filter(([id]) => !A11_SECOND_EDITION.includes(id)))];
          if (key === 'A09') return [key, mapSpans(Object.fromEntries(Object.entries(spans).filter(([id]) => !A09_SECOND_EDITION.includes(id))), firstEditionSpan)];
          return [key, spans];
        })
    );
