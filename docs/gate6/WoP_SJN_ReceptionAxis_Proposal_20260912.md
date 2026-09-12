# Two official Orthodox hosts disagree — and the registry has no column to say so

**Cowork · 2026-09-12 · follows the Eastern Orthodox official-sources proposal · every quotation below fetched from the page**

---

## What the ChatGPT pass contributed

Two things, and both are real.

**1. The 1848 Encyclical of the Eastern Patriarchs.** Cowork had not found this. It
was signed by the Patriarchs of Constantinople, Alexandria, Antioch and Jerusalem
**with their synods** — 29 bishops — and endorsed by St Philaret of Moscow. That is
broader reception than the 1672 Confession of Dositheus (one local synod) and
broader than Crete 2016 (which Antioch, Russia, Bulgaria and Georgia did not
attend). Worth chasing, and it was chased.

**2. The distinction between pan-Orthodox dogmatic authority and the
authoritative teaching of one autocephalous Church.** This is the more important
contribution, and it identifies a genuine gap in the registry — see below.

Its weaknesses are the same as the previous pass, milder: it cites GOARCH pages by
what they are *about* rather than by what they *contain*, and two of the pages it
recommends return 403. Its tier table is a design proposal with no URL verified
and no clause quoted. But the design proposal is sound.

---

## The 1848 Encyclical: authoritative, and not citable

**Its text is on no official Orthodox host.** Checked and fetched: the Ecumenical
Patriarchate, OCA, GOARCH, Antioch (both domains), Jerusalem, Alexandria, the
Church of Greece and its publishing arm, Moscow and its DECR, Cyprus, Romania,
Serbia, and three Orthodox seminaries. Not one carries the text.

Every circulating English version descends from a single **anonymous, uncredited
19th-century translation** re-hosted from a private site. Under R001 and the
verbatim-assertion rule, that cannot be a citable source: the phrase a cell would
assert would rest on a translation nobody will vouch for.

What *is* available on an official host is its **standing**. The OCA, on its own
domain:

> "Signed by all the patriarchs of the Orthodox Church, together with 29 bishops,
> and fully endorsed by Saint Philaret, Metropolitan of Moscow, the encyclical
> letter of 1848 is considered to be the most authoritative doctrinal statement in
> modern Orthodox Church history."

The Ecumenical Patriarchate footnotes the critical edition — **Karmiris,
*Τά Δογματικά καί Συμβολικά Μνημεῖα*, II (Athens 1953), 916** — which is where any
serious future citation would have to go, in print.

So: record the document, record its standing from the OCA page, record Karmiris as
the print locus, and **do not register it as a citable row**. Its native division
into §1–§23 (with roman sub-numerals in §5) is real and would support locators if
an official text ever appears.

---

## The finding that matters: two official hosts, one document, opposite rankings

`goarch.org/-/the-basic-sources-of-the-teachings-of-the-eastern-orthodox-church`
loads — plain HTML, verified directly — and states the Greek Orthodox
Archdiocese's own doctrine of sources:

> "The Symbol of Nicaea-Constantinopolitan (Nicene Creed) and the dogmatical
> utterances of the Ecumenical Synods are the primary and distinctive sources of
> the faith of the Orthodox Church."

and, of everything later:

> "The other sources, which are the decisions of synods which took place after the
> eighth century, are of secondary significance… These are secondary sources,
> pending ratification by an Ecumenical Synod, and may be accepted, corrected or
> not accepted."

Set that beside the OCA sentence above. **The same document — the 1848 Encyclical —
is "the most authoritative doctrinal statement in modern Orthodox Church history"
to one jurisdiction and a secondary source "pending ratification… may be accepted,
corrected or not accepted" to another.** Both statements are published by official
jurisdictions on their own domains.

This is not a problem to resolve. It is a fact about Orthodoxy that the app should
show. Picking a winner would be the project doing exactly what it exists not to do.

### What it does to three registry rows

GOARCH's criterion is *post-eighth-century synodal ⇒ secondary, pending
ratification*. Applied honestly:

| row | genre tier (ratified) | by GOARCH's own criterion |
|---|---|---|
| BSR-EO-05 Dositheus, 1672 | CONFESSIONAL — which the ratified rank places **above** CATECHETICAL | secondary, pending ratification, may be corrected or not accepted |
| BSR-EO-10 Crete 2016 (proposed) | CONCILIAR (participating churches) | secondary by the same test, and four churches absent |
| 1848 Encyclical | would be CONFESSIONAL | secondary by GOARCH, primary-in-modernity by OCA |

Dositheus is the sharp case. The ratified `authority_tier_rank` currently makes a
1672 local synod outrank a synodally-approved catechism received across Orthodoxy —
and an official Orthodox jurisdiction says the opposite. That asymmetry was flagged
on 11 September as "genre and reception diverge here." This is the evidence.

The ratified decisions that **hold** are worth stating too: GOARCH names the Creed
and the Councils as primary, which confirms BSR-EO-01 at CONCILIAR and confirms
narrowing BSR-EO-06 to the conciliar horoi. Those calls were right.

---

## Proposal: a second column, not a re-ranked first one

`authority_tier` answers *what kind of document is this*. It should not be
re-litigated — it was ratified yesterday and it is doing its job.

What the registry lacks is a column answering *who receives it*. Add:

**`reception_scope`** — one of:

| value | meaning | examples |
|---|---|---|
| `UNIVERSAL` | received by the whole tradition, uncontested | Nicene Creed; the Seven Councils for Orthodoxy |
| `MULTILATERAL_SYNODAL` | issued by several autonomous bodies acting together | 1848 Encyclical (four patriarchates) |
| `PARTICIPATING_BODIES` | a synodal act some constituent churches did not join | Crete 2016 |
| `JURISDICTIONAL` | authoritative within the issuing body | BF&M 2000 (SBC); UMC Articles; ACNA catechism; OCA and GOARCH catechesis |
| `DIALOGUE_ONLY` | a commission text its own publisher disclaims | the Assembly of Bishops' agreed statements |

**`reception_note`** — free text, used only where reception is *contested*, and
carrying the disagreement in the disputing bodies' own words. For Dositheus and for
1848 that note would quote both the OCA and the GOARCH sentences above.

**This is registry-wide, not an Orthodox patch.** It is the same axis that separates
the Baptist Faith and Message (one convention) from the Nicene Creed (all
Christendom), the UMC Articles (one denomination) from Chalcedon, and the ACNA
catechism — already fallback-tiered by AC-04 for precisely this reason — from the
Thirty-Nine Articles. AC-04 was this column, invented ad hoc for one row. Making it
a column generalises a decision the author has already made once.

It also feeds Gate 8 and Gate 9 directly: a learner comparing traditions needs to
know whether a cell speaks for a whole communion or for one synod, and that is
exactly what the copy requirement ("state what the standard SAYS") cannot convey
without it.

---

## Two further rows worth registering, and one trap

**Register as source-doctrine warrants** — not as predicate sources, but as each
jurisdiction's published statement of its own criterion, which the scope caveat
should quote:

- `goarch.org/-/the-basic-sources-of-the-teachings-of-the-eastern-orthodox-church`
- `oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/sources-of-christian-doctrine/the-liturgy` and `/the-councils`

**The trap.** The Assembly of Canonical Orthodox Bishops publishes this disclaimer
at `assemblyofbishops.org/ministries/ecumenical-and-interfaith-dialogues/`:

> "The texts promulgated by the Commissions, Consultations and Dialogues are not to
> be understood as official positions of the Orthodox Church or of the Assembly of
> Canonical Orthodox Bishops, but rather they reflect the considered theological
> understanding of these Commissions, Consultations and Dialogues…"

**It does not appear on the individual document pages.** The Filioque agreed
statement at its own URL carries no notice at all. So a cell citing that page would
present a dialogue commission's text as Orthodox teaching, with nothing on the page
to say otherwise. If that row is ever registered it must carry the disclaimer
verbatim in its row note, and `reception_scope = DIALOGUE_ONLY` is what prevents it
being cited as doctrine at all.

---

## The decision

1. **Add `reception_scope` and `reception_note` to the registry sheet**, populated
   for all 36 ratified rows plus whatever is added. Registry-wide.
2. **Adopt the six Eastern Orthodox liturgical and synodal rows** from the
   11 September proposal, now with reception values.
3. **1848 Encyclical** — record its standing and the Karmiris locus; do not
   register it as citable until an official host publishes the text.
4. **Leave `authority_tier_rank` exactly as ratified.**

This is one console sitting. It merges to v2.25 before cal-3 runs, so calibration
measures the registry the app will ship — and `reception_scope` arrives before Gate 7
opens 315 cells, rather than after, which is the difference between a column and a
migration.
