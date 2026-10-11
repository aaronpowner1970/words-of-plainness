/* ============================================================
   AOID2 SECOND-EDITION SWITCH  (Phase C3a, CODE-AOID2-25)

   Template name:  aoidSecondEdition.on
   Default:        OFF. With the switch off the built site is identical
                   to the site as it stood before this work.
   Build ON:       set WOP_AOID2_SECOND_EDITION=1 for the build
                     PowerShell:  $env:WOP_AOID2_SECOND_EDITION = '1'; npx @11ty/eleventy
                     bash:        WOP_AOID2_SECOND_EDITION=1 npx @11ty/eleventy
                   Any other value (or unset) leaves it OFF. Vercel does not set
                   it, so production stays OFF until the Gate 1 text freeze
                   (decision AOID2-STEP75-SEQUENCE) and someone turns it on.

   What it switches ON (all of it, and nothing else):
     - Of Plainness (A01) becomes "Prologue: Of Plainness", joined to the
       front matter of /articles/, ahead of the counted Articles
     - the boundary sentence, placed right after the A01 s12 sentence
     - the edition note in the Prologue, and the Second Edition label
       in the page hero
     - the preserved First Edition page, /articles/first-edition/
       (the Articles as they stood at commit c8999d1)
     - "First Edition" labels on the PDFs, slide deck and Article films

   Every sentence comes from the approved-wording file below, read at build
   time and never retyped: data-sources/aoid/second-edition/ holds a
   byte-identical copy of
   wop-scratch/WoP_AOID2_Step75_Prologue_ApprovedWording_20261011.md.
   ============================================================ */

const fs = require('fs');
const path = require('path');

const WORDING = 'data-sources/aoid/second-edition/WoP_AOID2_Step75_Prologue_ApprovedWording_20261011.md';
const FIRST_EDITION_URL = '/articles/first-edition/';
const SCRIPTURE = 'https://www.churchofjesuschrist.org/study/scriptures/nt/';

const on = process.env.WOP_AOID2_SECOND_EDITION === '1';
if (!on) module.exports = { on: false };
else {
  const src = fs.readFileSync(path.join(process.cwd(), WORDING), 'utf8').replace(/\r\n/g, '\n');
  const lines = src.split('\n');

  const section = (re) => {
    const i = lines.findIndex((l) => re.test(l));
    if (i < 0) throw new Error('approved wording: section not found: ' + re);
    let j = i + 1;
    while (j < lines.length && !/^## /.test(lines[j])) j++;
    return lines.slice(i + 1, j);
  };
  const only = (arr, what) => {
    if (arr.length !== 1) throw new Error('approved wording: expected exactly one ' + what + ', found ' + arr.length);
    return arr[0];
  };
  const quote = (re, what) => only(section(re).filter((l) => l.startsWith('> ')), what).slice(2);

  const heading = only(section(/^## Prologue /).map((l) => (l.match(/^- Heading: (.+)$/) || [])[1]).filter(Boolean), 'Prologue heading');
  const hero = only(section(/^## Label /).map((l) => (l.match(/^Hero line: "(.+)"$/) || [])[1]).filter(Boolean), 'hero line');
  const boundary = quote(/^## Boundary sentence /, 'boundary sentence');
  const edition = quote(/^## Edition note /, 'edition note');

  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const mustHave = (s, part) => {
    if (s.split(part).length !== 2) throw new Error('approved wording: "' + part + '" not found exactly once');
  };

  // Boundary: the two references link at the verse, in the URL form the
  // disclosure pages use (churchofjesuschrist.org/study, ?lang=eng&id=pN#pN).
  mustHave(boundary, '1 Corinthians 12:3');
  mustHave(boundary, '1 John 4:2');
  const boundaryHtml = esc(boundary)
    .replace('1 Corinthians 12:3', '<a href="' + SCRIPTURE + '1-cor/12?lang=eng&amp;id=p3#p3" target="_blank" rel="noopener">1 Corinthians 12:3</a>')
    .replace('1 John 4:2', '<a href="' + SCRIPTURE + '1-jn/4?lang=eng&amp;id=p2#p2" target="_blank" rel="noopener">1 John 4:2</a>');

  // Edition note: "First Edition" links to the preserved first-edition page.
  mustHave(edition, 'First Edition');
  const editionHtml = esc(edition).replace('First Edition', '<a href="' + FIRST_EDITION_URL + '">First Edition</a>');

  module.exports = {
    on: true,
    firstEditionUrl: FIRST_EDITION_URL,
    prologueHeading: heading,
    heroLine: hero,
    boundary,
    boundaryHtml,
    edition,
    editionHtml,
  };
}
