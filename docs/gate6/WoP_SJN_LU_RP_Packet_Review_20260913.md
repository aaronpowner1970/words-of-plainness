# Lutheran and Reformed/Presbyterian packets — review

**Cowork · 2026-09-13 · read against `lutheran.json`, `reformed-presbyterian.json`
and `pdf-audit.md` in the repo, not the report**

---

## I was wrong about BSR-AN-04, and wrong in a way my own standard names

I told you AN-04 was clean, and I put that in the prompt: *"BSR-AN-04 was clean when I
checked it, so this is source-dependent, not universal."* I had looked at **one chunk**
and generalised to the row.

The chunk I sampled was *Outline of the Faith, BCP p. 846*. The contamination Code found
is the even-page footer **"846 Catechism"** — the footer of the very page I sampled. I
looked directly at the affected row and pronounced it clean.

The Source Verification Standard covers this exactly: *a negative claim needs an
enumerated search space.* One chunk is not a search space. I also gave the wrong
mechanism for "cove nantal" — it is a soft hyphen (U+00AD) in the text layer, a kerning
split, not a page-furniture splice. Right consequence, wrong cause.

Worse than being wrong, I wrote it into an instruction that could have steered Code away
from looking. It looked anyway, and found three affected rows where I had named a
hypothesis about one. That is the system working in the direction it should.

**The audit is the strongest artifact this project has produced.** Three chunkings per
row — legacy, repaired, stored — with before-and-after text, and it went past the seven
rows I listed to cover EO-08 and EO-09 unasked. BSR-MW-03 verified clean in all three
chunkings with "of infinite power, wisdom, and good" intact and zero occurrences of
"goodness". That is the check that mattered most and it passed.

## Exhaustion vindicated the concern, and complicated it

7 of 9 Lutheran empty-track cells became filled. Those seven would have been ratified as
honest empties and were not empty. Sampled retrieval on a 1.6-million-character standard
was missing real evidence, and $16.49 bought back seven cells.

But read what it found. **The marginal cells are marginal for a reason**, and both cells
Code flagged for your first read are the weakest kind:

**Q-003, Living.** The Apology quoting Ezekiel 33:11 — *"As I live, saith the Lord God."*
Both models called the speech act an assertion, correctly: the Apology endorses the oath
in its own voice. But *"as I live"* is an oath formula — the divine equivalent of "I swear
on my life." What the Apology is arguing is that the promise is oath-bound and therefore
trustworthy. Divine life is what the idiom **presupposes**, not what the passage asserts.
Opus saw half of this and wrote that aseity "is presupposed rather than asserted" — the
same objection applies to the life-claim itself. This is the container-word problem in a
new form: not a word with two senses, but a fixed formula whose surface words are not its
proposition. I would lean reject; it is your call, and it needs a hazard class of its own.

**Q-403, No adequate likeness or comparison.** Here the two models materially disagreed
and I think the primary was right. Sonnet set the floor at **WORD_ONLY**, reasoning that
Romans 11:33's unsearchable judgments "does not address or deny any likeness/comparison
between Creator and creature; the predicate concerns a different proposition (analogical
predication)." Opus set **PARTIAL** and accepted with caveat, calling it "a narrower
proposition about the unsearchability of God's decree of election."

Narrower only licenses A-SF when the narrower claim is a *subset* of the predicate. The
unsearchability of God's decree is not a subset of the inadequacy of creaturely likeness —
it is a neighbouring claim about a different object: God's judgments, not God's being. And
the second candidate in the same cell, the Large Catechism's "not as wise as is the Divine
Majesty in His little finger," was refused WORD_ONLY on exactly the reasoning that should
have refused the first.

## Which turns the Task 3 result around

34 caveated accepts to opus, 34 calls, $3.33, **0 overturned**. My hypothesis was that
opus would catch weak accepts the primary let through. It caught none.

The honest reading is worse than "no finding." On Q-403 opus was the **more permissive**
model, and because it adjudicates, its permissiveness carried a weak candidate onto a card
that the primary had floored. On the reject-all route opus is plainly earning its keep — 8
rescues across the two branches. On the caveated-accept route it overturned nothing and in
at least one case made the outcome worse.

This is n=1 on the direction, so I am not calling it a pattern. But adjudication is the
wrong instrument here regardless. Where two models disagree on the floor, the project's
whole posture — fidelity over elegance, empty is a valid result — says take the **lower
floor**, not the adjudicator's. That is a one-line change, it costs nothing, and it turns
a disagreement into a conservative outcome instead of a coin toss. Keep opus on rejects;
stop letting it adjudicate accepts.

## Reformed/Presbyterian: row order became an editorial ruling

Code flagged the tie-break and was right to. It is worse than a sorting nicety.

All six rows are CONFESSIONAL **and** JURISDICTIONAL, so neither the tier rank nor the
reception axis discriminates. The tie is real, because Reformed Christianity genuinely has
no single confessional authority — three families sit side by side:

    BSR-RP-01/02/03   Westminster Confession, Shorter and Larger Catechisms   OPC
    BSR-RP-04         PC(USA) Book of Confessions 2016                        PC(USA)
    BSR-RP-05/06      Heidelberg, Belgic                                      CRCNA and RCA

Across the whole packet the rows appear in reasonable balance — RP-04 31 times, RP-01 26,
RP-03 21, RP-06 21, RP-05 16, RP-02 13. **But RP-01 leads 14 of 16 cards, and 9 cards read
RP-01, RP-02, RP-03 exactly.** On more than half the branch, all three candidate slots are
Westminster, and Heidelberg, Belgic and the Book of Confessions — which produced usable
candidates — were cut by the cap because Westminster sorted first on CSV row position.

A reader looking at the Reformed column would conclude Westminster *is* Reformed. That is
a representation decision, made by the order rows happen to sit in a file.

The fix is not a better sort key; there is no honest ranking among the three families. It
is a **diversity constraint on the slots**: within a tier tie, no `speaks_for` group takes
a second slot until every group with a surviving candidate has taken a first. That is a
general rule, not an RP patch — it applies to Anglican (three Church of England rows
against TEC and ACNA) and will matter most on Eastern Orthodox's fourteen rows across many
jurisdictions.

All four packets can be rebuilt under it for nothing, the way the Roman Catholic rebuild
was: every candidate and verdict is already stored.

## Two smaller things

**BSR-LU-02 returned no text at all.** A ratified registry row that yields nothing is
either a fetch to fix or a row to retire — Lutheran effectively ran on three of its four
rows, and the packet does not say so on its face.

**Exhaustion-sourced candidates should be marked on the card.** Both of the cells you were
told to read first came from exhaustion. That is not an argument against exhaustion; it is
a reason the author should be able to see at a glance that a candidate came from the tail
of a standard rather than from its substance.

## Cost, and the Eastern Orthodox problem

$39.09 for 55 cells. The two rates tell you what drives cost, and it is not the branch's
difficulty — it is **rows per cell**. Reformed's locator alone was $10.71 because six
standards are consulted per cell, three of them 60k-character retrieved contexts.

Remaining: Baptist 37, Methodist/Wesleyan 37, Mennonite/Anabaptist 41, Eastern Orthodox 44.
The first three are three- and four-row branches and should run near the Anglican rate,
perhaps $35 for all 115 cells. **Eastern Orthodox has fourteen rows.** Extrapolating from
Reformed's six, EO alone plausibly costs $75–90 before exhaustion, and more with it — more
than the other three branches combined.

That is worth deciding before EO runs rather than during: a per-cell cap on how many
standards are consulted, or a narrowed EO working set, or simply accepting the number with
eyes open. It is a real question about what fourteen rows are buying.
