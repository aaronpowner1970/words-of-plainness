# SJN Gate 7 — host verification for the three rows the sitting authorised

**Cowork · 2026-09-11 · follows the Gate 7 sitting (Decision Console Version 5), all nine cards decided**

Both approvals that authorised research have now been researched. Every URL below
was fetched and read, and the key clause quoted from the page itself. Where a
page could not be read, it is marked unverified and not recommended.

---

## Decisions as entered (AJP, 2026-09-11)

| card | decision |
|---|---|
| SETUP-01 | `SAME_STANDARD` — the gate is the spec's own metric; tier-respecting stays a diagnostic |
| AC-09 | `EXTEND_TO_CONSTITUTION_2` — BSR-RC-04 scope widens to Lateran IV constitutions 1–2 |
| AC-10 | `TIER_PER_CITED_DOCUMENT` — tier resolves to the document cited, not the registry row |
| AC-11 | `SONNET_WITH_OPUS_SLICE` — sonnet primary, opus on the hard slice |
| BSR-EO-01 | APPROVE as drafted → CONCILIAR |
| BSR-RC-06 | APPROVE → row floor CONFESSIONAL, Nicene and Athanasian resolve CONCILIAR |
| BSR-EO-06 | APPROVE → re-sourcing authorised |
| BSR-MW-03 | APPROVE → row kept, re-host (see the note on this reading below) |
| BSR-EO-03 | APPROVE → one-time archived fetch authorised |

---

## 1. BSR-MW-03 — the row is not dead. The 404 was a `www` artifact.

`https://www.globalmethodist.org/what-we-believe` returns 404. The apex host
does not: **`https://globalmethodist.org/what-we-believe`** (no `www`) serves the
full Transitional Book of Doctrines and Discipline as plain server-rendered HTML,
including the complete Articles of Religion. Apex and `www` are two different
sites — `www` is a current Duda build, the apex path is a surviving legacy page.

Article I, *Of Faith in the Holy Trinity*, as printed on that page:

> "There is but one living and true God, everlasting, without body or parts, of
> infinite power, wisdom, and **good**; the maker and preserver of all things,
> both visible and invisible."

**The registry's sample phrase is wrong and would fail verbatim assertion.** The
row currently carries *"of infinite power, wisdom, and goodness."* The GMC text
reads **"wisdom, and good"** — no *-ness*. This is a genuine feature of the GMC
Transitional Discipline, not a fetch artifact; it was cross-checked against an
independent conference copy at ngagmc.org, which reads identically. The variant
is a useful authenticity fingerprint, and it means any cell citing this row must
quote "good," not "goodness."

Three caveats to carry in the row note:

- **The qualifying page is orphaned.** It is not linked from the current site
  navigation. It is being served but could vanish in a cleanup, so the row wants
  re-validation rather than being treated as stable.
- **Every current official PDF is off-domain.** The 2024 Book of Doctrines and
  Discipline and the Catechism are hosted on `irp.cdn-website.com`, Duda's CDN.
  Under registry-only enforcement none of those URLs qualifies.
- **The on-domain text is the 2022 *Transitional* Discipline, superseded by the
  2024 BDD.** The Articles of Religion themselves are unchanged between editions,
  so the doctrinal content is current even though the edition label is not. The
  current edition exists only off-domain.

One on-domain Catechism PDF returned 403 and could not be read; it is not counted.

**Reading of the APPROVE.** The card offered two paths — approve *with a revised
URL* to keep the row, or exclude with reason OTHER to retire it. A plain APPROVE
is neither exactly, and it has been read as *keep the row and find the text*,
which the research then justified. If the intent was to retire the row and let
BSR-MW-04 carry the branch alone, say so before the merge and it will be
excluded instead.

---

## 2. BSR-EO-06 — no Orthodox jurisdiction publishes the conciliar definitions.

This is the honest finding, and it is worth stating plainly because it was the
premise of the card: the preferred host category does not exist. Checked and
read: oca.org, goarch.org, antiochian.org, sourozh.org. All of them publish
catechesis and church history that *quote clauses* from the councils; none
publishes the definitions themselves. The full acts and definitions are left to
the scholarly editions. That is consistent with there being no pan-Orthodox
official publisher of the Ecumenical Councils.

Verified candidates that do carry the definitions:

| council | URL | clause as printed | divisions | translation |
|---|---|---|---|---|
| Chalcedon (451) | `ccel.org/ccel/schaff/npnf214.xi.xiii.html` | "in two natures, unconfusedly, immutably, indivisibly, inseparably [united]" | excellent — own chapter page titled *The Definition of Faith of the Council of Chalcedon*, inside a session-by-session URL series | NPNF2-14, Percival; credited at volume level, page credits Schaff only |
| Chalcedon (451) | `papalencyclicals.net/councils/ecum04.htm` | "acknowledged in two natures which undergo no confusion, no change, no division, no separation" | adequate — one page, internal headings, no per-section URLs | Tanner, credited outright on the page |
| Constantinople III (680–681) | `ccel.org/ccel/schaff/npnf214.xiii.x.html` | "two natural wills and two natural operations indivisibly, inconvertibly, inseparably, inconfusedly" | excellent — *The Definition of Faith*, with its own printed locator: "Found in the Acts, Session XVIII" | NPNF2-14, Percival |
| Constantinople III | `papalencyclicals.net/councils/ecum06.htm` | "two natural volitions or wills in him and two natural principles of action which undergo no division, no change, no partition, no confusion" | adequate | **uncredited** — unlike ecum04, the page names no translator |

New Advent is not recommended for either council: its pages truncate on retrieval
and name no translator.

**AC-02 is not violated by registering CCEL here.** AC-02 ratified
`MIGRATE_WHERE_OFFICIAL` — migrate ccel and newadvent *where an official host
exists*. For these two councils none does. The condition in the ratified decision
is what makes CCEL eligible, so this is the policy operating as written rather
than an exception to it.

### Two consequences of re-hosting that need to be seen before the merge

**Q-434's asserted phrase exists in none of the verified sources.** The released
cell quotes *"without change, without confusion, without division, without
separation"* from an OCA church-history page. Percival reads "unconfusedly,
immutably, indivisibly, inseparably." Tanner reads "no confusion, no change, no
division, no separation." OCA's own catechetical page reads "without mixture and
without change, without separation and without division." Every citation carries
a ≤15-word verbatim asserted phrase, so changing the host changes which wording
is available: **Q-434 must have its phrase re-cut from whichever translation is
registered, and re-verified in Gate 7.** It is currently a released cell resting
on wording its new source will not contain.

**A corpus-builder hazard specific to CCEL.** Each chapter page interleaves
Percival's editorial notes — Hefele, Anatolius — with the conciliar text. A
splitter that chunks the page naively will let an 1899 editor's note be cited as
the council's own assertion, which is precisely the rubric item 3 failure the
verifier exists to catch, arriving pre-baked in the corpus. For BSR-EO-06 the
corpus builder must exclude or mark non-citable every editorial-note block.

**One disclosure point.** CCEL is a Protestant-run classics library. Registering
it makes the Eastern Orthodox branch cite its own conciliar dogma from a
Protestant host, in a branch whose scope caveat already discloses a 19th-century
Russian catechism and a 1672 local synod. The caveat should name it.

---

## 3. BSR-EO-03 — the archived fetch has a second payoff

The approved one-time archived fetch of goarch.org may solve part of §2. A GOARCH
page, `goarch.org/-/the-dogmatic-tradition-of-the-orthodox-church`, surfaced in
search as containing the exact clause *"without confusion, without change,
without division, without separation"* — the wording Q-434 actually uses — but
returned 403 on every attempt and could not be read, so it is a lead, not a
finding.

If Code's Playwright path reaches it under the EO-03 approval, it would supply
both an Orthodox jurisdictional host and the wording the released cell already
quotes. Worth trying in the same pass; not worth blocking v2.24 on. Propose it as
a Gate 7 upgrade to BSR-EO-06 if it renders.

---

## What the merge to v2.24 needs

1. `CALL_RESOLUTIONS` entries for AC-09, AC-10, AC-11.
2. BSR-RC-04 scope → Lateran IV constitutions 1–2 (AC-09). Same host.
3. BSR-EO-01 `authority_tier` → CONCILIAR (approved as drafted).
4. BSR-RC-06 → row floor CONFESSIONAL with per-document resolution (AC-10).
5. BSR-MW-03 `canonical_url` → `https://globalmethodist.org/what-we-believe`;
   `sample_phrase` → "of infinite power, wisdom, and good"; row note carrying the
   three caveats above.
6. BSR-EO-06 → the ratified host(s) from the question still open below, with the
   editorial-note exclusion and the Q-434 re-cut recorded.
7. BSR-EO-03 `fetch_mode` → archived fetch, provenance recorded in the row note.
8. New APP CONFIG keys: `authority_tier_rank`, `gate6_threshold_metric =
   SAME_STANDARD`, `verifier_routing = SONNET_WITH_OPUS_SLICE`.

Then Code: per-standard retrieval slots, the opus-slice routing, cal-3 against
v2.24, live run.
