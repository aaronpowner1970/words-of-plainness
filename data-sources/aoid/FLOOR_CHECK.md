# AoID floor-transfer check

Command: `npm run aoid:floors` (or `node scripts/aoid-verify-floors.js`). Exits non-zero on any FAILED item.

It enforces codex A4(a) and A4(d) (`WoP/methodology/Comparison_Principles_Codex.md`, v0.14): a span's written
scope note is its apparatus `panel_comment`, and where a floor was ratified before its span existed, the
panel_comment is transcribed verbatim from the ratified floor document in `floors/`. The ledger
`floor_ledger.yaml` lists every scored item, its floor document and heading, and its span.

For each `scored:` item, exactly one state:

- **TRANSFERRED**: the ledger names a span, it exists in `src/_data/apparatusData.json`, and the opening paragraph of its panel_comment equals the floor (see the opening-paragraph rule below).
- **PENDING**: `span: null`. Lawful under A4(d); reported, exit zero.
- **FAILED**: span absent; no panel_comment; panel_comment differs from the floor; floor document or heading missing or ambiguous; floor text no longer matches its recorded `floor_sha256` (changed without a ruling); hash not yet recorded; or a malformed entry. Missing floors and malformed entries are also reported separately.

Span format in the ledger: `A03.s2` (article key, span key, as in apparatusData.json). `span` is `null` (no span yet), one span, or a list of spans (`[A02.s12, A02.s2]`). Each span in a list is checked on its own against the item's one floor and reported on its own as TRANSFERRED, FAILED or PENDING; the totals count spans. A floor, heading or hash problem fails every span of the item. A span listed twice, or an empty list, is a malformed entry.

Floor text, default rule: the blockquote under the line beginning `**Panel comment (the floor)` in the section whose heading equals the ledger's `floor_heading`. The heading may be at level 2, 3 or 4 (`##`, `###` or `####`), and `floor_heading` is the heading text after the `#` marks and one space, exactly. The section ends at the next heading of the same or higher level. The section must hold exactly one label line, followed by one blockquote.

Floor text, with `floor_anchor` (optional ledger field): for floor documents that hold more than one blockquote in a section (a superseded wording kept on record, or two forms), or no label line. `floor_anchor` is a text that must occur in exactly one line of the section (the heading line counts as part of the section). The floor is then the first blockquote after that line, and the label line is not required. An anchor found on no line, or on more than one line, is a FAILED item with a message saying so. Entries without `floor_anchor` follow the default rule unchanged. The Stage 1 floors (`WoP_AOID2_ScopeNotes_Stage1_...`) carry no label lines, so each is entered with an anchor: its ID and full stop (for example `"A2-F2. "`, which occurs only on the heading line), or, where the section holds two forms or a later amendment, the line that precedes the ratified one (`"**Form A"` for A4-F3; `"**Amended by Aaron 2 Oct 2026"` for G8, whose 22 Sep blockquote comes first).

Opening-paragraph rule (AOID2-FLOOR-OPENING-PARAGRAPH, ruled by Aaron 8 Oct 2026): a span's panel comment carries its floor as the verbatim opening paragraph, and approved notes may follow it. The opening paragraph of a panel_comment is its text up to the first paragraph break (a blank line, "\n\n" in the JSON string, with any whitespace around it), or the whole comment if there is no break. A span is TRANSFERRED when the normalised opening paragraph equals the normalised floor. Everything after the first paragraph break is ignored. An opening paragraph that is longer than the floor FAILS even when it begins with the floor, with the message "floor is followed by further text in the same paragraph; a paragraph break is needed after the floor". Any other mismatch (notes before the floor, a truncated floor, a changed word) FAILS with "opening paragraph differs from floor" and the first difference. Recorded hashes cover the floor only and do not change.

Both the hash and the comparison use this normalisation: strip the leading `>`, join lines, collapse every whitespace run to one space, trim. Nothing else. Hash = SHA-256 of the UTF-8 result. The comparison is exact equality of the normalised opening paragraph and the normalised floor.

When an item is first scored, add its ledger entry with `floor_sha256: ""`, then run `node scripts/aoid-verify-floors.js --record-hashes` once (it fills empty hashes only). A floor changes only by the author's ruling; re-export the floor, then update its hash by ruling.
