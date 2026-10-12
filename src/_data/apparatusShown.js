/**
 * apparatusShown.js: the apparatus the Articles page embeds (CODE-AOID2-28).
 *
 * apparatusData.json holds every Article's apparatus, including the new Article 1 (key A14),
 * because the floor check (scripts/aoid-verify-floors.js) reads that file. The Second Edition
 * switch (src/_data/aoidSecondEdition.js) keeps A14 off the public page: with the switch OFF
 * the embedded data is the thirteen First Edition Articles exactly as before; with it ON it is
 * the whole file.
 */
const all = require('./apparatusData.json');
const { on } = require('./aoidSecondEdition.js');

module.exports = on
  ? all
  : Object.fromEntries(Object.entries(all).filter(([key]) => key !== 'A14'));
