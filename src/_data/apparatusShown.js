/**
 * apparatusShown.js: the apparatus the Articles page embeds (CODE-AOID2-28).
 *
 * apparatusData.json holds every Article's apparatus, including the new Article 1 (key A14),
 * because the floor check (scripts/aoid-verify-floors.js) reads that file. The Second Edition
 * switch (src/_data/aoidSecondEdition.js) keeps A14 off the public page: with the switch OFF
 * the embedded data is the thirteen First Edition Articles exactly as before; with it ON it is
 * the whole file. The same holds for the Article 11 spans s20-s25 (CODE-AOID2-29).
 */
const all = require('./apparatusData.json');
const { on } = require('./aoidSecondEdition.js');

/* Article 11 spans added for the Second Edition (CODE-AOID2-29, step 79): s20-s25. With the switch OFF
   they have no text on the page, so their apparatus is not embedded either. */
const A11_SECOND_EDITION = ['s20', 's21', 's22', 's23', 's24', 's25'];

module.exports = on
  ? all
  : Object.fromEntries(
      Object.entries(all)
        .filter(([key]) => key !== 'A14')
        .map(([key, spans]) => (key === 'A11'
          ? [key, Object.fromEntries(Object.entries(spans).filter(([id]) => !A11_SECOND_EDITION.includes(id)))]
          : [key, spans]))
    );
