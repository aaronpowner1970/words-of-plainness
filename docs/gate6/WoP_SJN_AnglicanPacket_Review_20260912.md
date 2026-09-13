# Anglican packet — review, and one thing I would stop for

**Cowork · 2026-09-12 · read against `anglican.json` in the repo, not the report**

---

## First, a correction of mine

My Roman Catholic review said 60 of 158 coder calls were wasted and called it "38%
waste," inside the cost section. Code measured it: the real saving on Anglican was
**$0.22, or 1.5% of the branch.** 38% was a share of *calls*, not of money, and putting
it in a cost paragraph implied a budget lever it never was. Code's framing is the right
one — 1c is call hygiene and a cleaner audit trail. Adopt it for that reason, not to
save money.

## The denominator holds arithmetically, and the honesty is the valuable part

141 released + 291 open + 24 excluded = 456, and **every one of the eight branches sums
to exactly 57.** Nothing is lost or double-counted.

The part worth keeping is Code saying plainly that 16 of the 24 are a harness
assumption, not a workbook fact — no column says "Gate 6 open"; the harness reads two
columns and applies its own predicate — and then not acting on it. That is the right
behaviour, and it leaves you one decision: **ratify the 13 atomic-vector cells and the 3
retired-witness cells as closed for Gate 6, or bring them back into the queue.** The 8
out-of-scope cells (RNR-H50) genuinely are a workbook fact.

## The empties are weaker than their label

This is the one I would stop for.

Every empty cell — Q-021 Spirit, Q-101 Truthful, Q-149 Blessed, Q-245 Wisdom, Q-253
Light — carries the same coverage shape in the packet:

    BSR-AN-01  FULL       39 of 39
    BSR-AN-02  FULL       25 of 25
    BSR-AN-03  FULL        1 of 1
    BSR-AN-04  FULL      124 of 124
    BSR-AN-05  RETRIEVED  80 of 368        <- 22% of the standard

And yet `empty_result_option.standards_reviewed` lists all five rows, and the rendered
state on offer is **NOT LOCATED — CURRENT STANDARD REVIEWED**.

For BSR-AN-05 that is not true. It was sampled, not reviewed. The pattern is structural,
not accidental: pass 1 reads AN-01 through AN-04 whole; AN-05 is fallback-only, 368
chunks, and is consulted only when pass 1 finds nothing — precisely on the cells heading
for empty. So the sampling always lands where the claim of emptiness is being made.

This is the Roman Catholic worry inverted. There, a filled cell might be weak. Here, an
empty cell might not be empty, and you would ratify it as one. "Empty is a valid result"
only holds if an empty is auditable, and right now these five are not.

Two fixes, both cheap. `standards_reviewed` should carry each standard's coverage rather
than a bare list, and a rendered state claiming a standard was *reviewed* should not be
offered for one that was sampled. Where a cell is about to go empty, the fallback row
should either be read exhaustively or the card should say in one line that it was not.

## Q-357 — I would reject it, not merely read it with suspicion

Code flagged the Article XVII candidate for Immutable and told you to be suspicious. I
would go further and not put it in front of yourself as a candidate at all.

The phrase is *"he hath constantly decreed by his counsel secret to us."* Article XVII is
**Of Predestination and Election**. What is asserted is the steadfastness of God's decree
of election, not the unchangeableness of God. The verifier saw this itself: floor
PARTIAL, hazard `SEMANTIC_FLOOR`, and in its own words *"not strong metaphysical
immutability."*

Two reasons beyond the floor. Article XVII is the most contested Article in Anglicanism,
and an Anglican reader meeting it in an attribute cell about unchangeableness will read
it as a category error before reading it as a citation. And the Articles do have language
nearer to immutability — Article I's "everlasting, without body, parts, or passions" —
so the cell is not being served by its best available witness. My recommendation is
NOT LOCATED — CURRENT STANDARD REVIEWED for Q-357.

## A structural asymmetry in verifier routing

148 final verdicts in this packet:

    ACCEPT_WITH_CAVEAT   84
    REJECT               37
    ACCEPT               27

    adjudicated by sonnet  129
    adjudicated by opus     19

`SONNET_WITH_OPUS_SLICE` routes to opus on outright rejects and on fallback-only rows. So
a **reject** gets a second opinion; a **weak accept** usually does not. But
ACCEPT_WITH_CAVEAT with a PARTIAL floor and a `SEMANTIC_FLOOR` or
`SAME_WORD_DIFFERENT_MEANING` hazard is exactly the shape of a planted near-miss — and it
is the outcome that actually reaches your cards. Q-357 is that shape, and it was
adjudicated by sonnet alone.

False-accept 0.000 is measured on the planted set, which routes differently. It does not
cover this path. Widening the opus slice to cover caveated accepts at a PARTIAL floor
closes the gap at what should be a few dollars a branch, since it fires only on
candidates that survive the cap.

## PDF extraction is splicing page furniture into the text

From Q-101's ACNA rejection, verbatim from the packet:

> "the exclusive, lifelong, **cove nantal** union of love between one man and one
> woman... Marriage is therefore holy and should **the ten commandments** "be held in
> honor among all.""

Two defects in one chunk: an intra-word space, and a running header spliced into the
middle of a sentence. This is not the line-break hyphenation you fixed earlier; it is
page furniture entering the body.

The consequence is silent, which is what makes it serious. A phrase assertion must match
verbatim in the chunk, so a valid phrase spanning a splice simply fails and is dropped —
no error, no rejection record, nothing for you to see.

Scope: I checked BSR-AN-04, also a PDF, and its chunks are clean, so this is
source-dependent rather than universal. But five more PDF rows are still to run —
**BSR-LU-02, BSR-RP-04, BSR-MW-03, BSR-MA-01, BSR-MA-02** — and MW-03 is the one where
you verified "of infinite power, wisdom, and **good**" against your own copy. Every PDF
row should be audited before its branch runs.

I would not re-run Anglican over this. AN-05 accounts for 7 of 148 verdicts and it is a
fallback row.

## What the packet does well

Q-101 is the case for the whole design. Two candidates, two correct rejections:

- Article I's *"one living and true God"* — refused `BELOW_FLOOR`, hazard
  `SAME_WORD_DIFFERENT_MEANING`, because "true" here means genuine as against false gods,
  not truthful. Both models caught it independently.
- ACNA's marriage question — refused `WRONG_SUBJECT`, because the grammatical subject is
  marriage and God appears only in a relative clause.

That is container-word discipline and the grammatical-subject rule doing exactly what
they exist for, without help. On the evidence read, Q-101 is a defensible empty.

**BSR-AN-03 migrated cleanly.** Rendered in Playwright, chunked between the QUICUNQUE
VULT heading and the Gloria's Amen — excluding the Morning Prayer rubric above and the
Crown copyright line below, which is the right cut. One chunk, FULL coverage, and it
appears 37 times across the packet, carrying candidates on 16 of 43 cells and leading 5.

`translation_pairs` is `{}`, confirming 1b never fired, and the ordering string records
1a as implemented. $14.46 at $0.336 per cell, below both the Roman Catholic rate and the
projection.

## On Code's three proposals

**Ratify the four derived pairs before Eastern Orthodox — agreed, and list them.** A
pairing derived from a shared title token is too thin to carry a citation, and EO-13 to
EO-06 rests on exactly that. The pairs need to be named in the report so they can be
ratified individually, not as a set.

**Rebuild the Roman Catholic packet — yes.** It costs nothing and four cells were led by
a witness row under the old ordering.

**Locator rationale on empties — yes**, and the coverage finding above is the sharper
version of it. A one-line rationale plus honest per-standard coverage is what makes an
empty ratifiable.

## Remaining

214 cells across six branches, roughly $72 at the Anglican rate and $100 at the Roman
Catholic rate. Eastern Orthodox alone and last, as Code proposes.
