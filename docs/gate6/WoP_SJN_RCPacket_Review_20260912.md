# Roman Catholic packet — review, and two registry corrections before the rest

**Cowork · 2026-09-12 · read against the packet file and the repo, not the report**

---

## My allowlist audit was wrong. Code's correction is right.

I reported seven rows where R001 admitted a domain the registry never named, and
called three of them inverted. Code checked and found the workbook footprint was
**three rows**, not seven — because I parsed the draft CSV, and the merge script
runs `first_url()` when it writes `canonical_url`, so prose after the first URL never
reaches the workbook at all.

Verified directly in the packet: BSR-RC-06's `standard_title` reads

> "Creeds as received (Apostles', Nicene, Athanasian) **on vatican.va /
> vaticannews.va**"

so the leak came through the *title* field, which I never examined. Code's three —
RC-06 via title, AN-03 via URL prose, EO-06 via the v2.25 wording — are the real set.

That is the third time this week I have reported on an upstream input rather than the
artifact that governs. The Source Verification Standard was written one message
earlier and caught me on the next. Its clause 2 is the one that applies, and it holds.

## The packet is materially better than its summary

Read at the candidate level, this is doing what the project was built to do.
Q-017, Vatican I's *substantia spiritualis*:

- the verifier returned **ACCEPT_WITH_CAVEAT** with hazard flag
  `SAME_WORD_DIFFERENT_MEANING`, having noticed that Vatican I's "spiritual
  substance" and Latter-day Saint "spirit" are not the same concept;
- the coder assigned rendered state **Q**, not A, reasoning that Dei Filius
  "explicitly excludes materiality, directly opposing D&C 131:7–8's redefinition of
  spirit as refined matter, so the family's qualified-agreement code holds."

That is your container-word discipline arriving automatically, and the four-state
distinction being used for exactly what it exists for. The rubric, the grammatical
subject, the chunk context, the re-assertion check and the scope caveat all travel
with every candidate.

**On 34 of 34 filled with zero empties:** not alarming for this branch. Roman
Catholic has the largest corpus in the registry — the Catechism at 570 chunks and the
Compendium at 533 — and a Catholic source says something about nearly every divine
attribute. 180 rejections were kept across 34 cells, so the verifier was refusing at
roughly five per cell. But it is the one branch where a plausible-but-weak citation
is most likely to survive, and it is the cheapest possible moment to check. **Read
six or eight cards before the other seven branches run.**

---

## Two registry corrections, both needed before Anglican runs

### BSR-AN-03 — the strict rule has undone a ratified migration

Code's host guard now builds BSR-AN-03 from ccel.org, because that is what
`publisher_domain` says. But **AC-02 ratified MIGRATE_WHERE_OFFICIAL**, and the row's
own draft recommendation reads "LINEAGE → migrate to churchofengland.org". For the
Athanasian Creed an official host *does* exist — the Church of England's own BCP
pages — so the ratified policy says migrate, and the strict rule has just pinned the
row to the lineage host instead.

Four cal-3 candidates on three cells (Q-037, Q-293, Q-309) were fetched from
churchofengland.org while the row said ccel.org. The guard was right to stop that.
The fix is not to loosen the guard: it is to make the row say what AC-02 already
decided. Set `canonical_url` and `publisher_domain` to the churchofengland.org BCP
page and re-chunk.

This must land before the Anglican branch runs, or that branch is built on the host
your own ratified decision retired.

### Q-169 — vaticannews.va

A released cell cites vaticannews.va and now fails R001. That domain is the Holy
See's own news service, not a third-party republication, so the substance is fine and
only the registry is silent. It is not a controlled-storage case under AC-15 — that
clause is for a body's file store, not a second publishing outlet — so it needs
either its own row or an explicit second domain on BSR-RC-06.

---

## Four packet-shape changes: all sound, apply all four

1. **Witness rows sorting above non-witness on a tier tie** is a real defect.
   BSR-RC-03 is a TRANSLATION_WITNESS and appears as a candidate 26 times in this one
   packet, leading four cells. The rule already says a cell may not rest on a witness
   alone; leading with one is the same error one step earlier.
2. **Pairing a Latin controlling phrase with its English witness on the card** is how
   BSR-RC-02 and BSR-RC-03 were always meant to work together.
3. **Running the coder after tier allocation** — 60 of 158 coder calls were spent on
   candidates the cap then cut. That is 38% waste, and it repeats on every branch.
4. **The per-branch cap resets per invocation**, so the $25 cap was advisory. Fix
   before any unattended multi-branch run.

## Cost and the denominator

$15.80 for 34 cells, $0.465 against $0.405 projected — the overrun is the two 60k
retrieved corpora. Code counts **291 open cells, not 315**. That difference of 24 is
probably the cells already marked NOT LOCATED — CURRENT STANDARD REVIEWED, but it
should be stated rather than inferred, and it moves the full-run projection to about
$135.

---

## Author decisions (ratified 2026-09-12)

- **BSR-AN-03 → migrate to churchofengland.org.** Set `canonical_url` and
  `publisher_domain` to the Church of England's own BCP page and re-chunk. Cowork
  verifies the BCP page carries the Athanasian Creed before writing it — no
  unverified URL enters the registry.
- **Q-169 / vaticannews.va → its own registry row.** Registered as a distinct row
  with its own `authority_tier` and `reception_scope`, not folded into BSR-RC-06 and
  not admitted under AC-15. Cowork verifies the cited text before writing the row.

Both land in registry Draft3r3 and workbook v2.25r3, before the Anglican branch runs.
