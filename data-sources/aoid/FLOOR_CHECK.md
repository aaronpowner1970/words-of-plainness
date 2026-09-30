# AoID floor-transfer check

Command: `npm run aoid:floors` (or `node scripts/aoid-verify-floors.js`). Exits non-zero on any FAILED item.

It enforces codex A4(a) and A4(d) (`WoP/methodology/Comparison_Principles_Codex.md`, v0.14): a span's written
scope note is its apparatus `panel_comment`, and where a floor was ratified before its span existed, the
panel_comment is transcribed verbatim from the ratified floor document in `floors/`. The ledger
`floor_ledger.yaml` lists every scored item, its floor document and heading, and its span.

For each `scored:` item, exactly one state:

- **TRANSFERRED**: the ledger names a span, it exists in `src/_data/apparatusData.json`, and its panel_comment equals the floor.
- **PENDING**: `span: null`. Lawful under A4(d); reported, exit zero.
- **FAILED**: span absent; no panel_comment; panel_comment differs from the floor; floor document or heading missing or ambiguous; floor text no longer matches its recorded `floor_sha256` (changed without a ruling); hash not yet recorded; or a malformed entry. Missing floors and malformed entries are also reported separately.

Span format in the ledger: `A03.s2` (article key, span key, as in apparatusData.json).

Floor text: the blockquote under the line beginning `**Panel comment (the floor)` in the section whose `## ` heading equals the ledger's `floor_heading`. Both the hash and the comparison use this normalisation: strip the leading `>`, join lines, collapse every whitespace run to one space, trim. Nothing else. Hash = SHA-256 of the UTF-8 result. Comparison is exact equality of the normalised texts.

When an item is first scored, add its ledger entry with `floor_sha256: ""`, then run `node scripts/aoid-verify-floors.js --record-hashes` once (it fills empty hashes only). A floor changes only by the author's ruling; re-export the floor, then update its hash by ruling.
