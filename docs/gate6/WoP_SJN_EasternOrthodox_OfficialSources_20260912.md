# Eastern Orthodox sources — official jurisdictional hosts do exist, in a genre we were not searching

**Cowork · 2026-09-12 · proposal following the Gate 7 sitting · every URL below was fetched and the clause quoted from the page**

---

## The reframe

We were looking for the conciliar definitions published by an Orthodox
jurisdiction, and that search fails — honestly and completely. Three independent
passes checked the Ecumenical Patriarchate, the Church of Greece and its
publishing arm, Moscow, Romania, Serbia, Bulgaria, Cyprus, Antioch, OCA, GOARCH,
ROCOR, and the Ukrainian and Bulgarian dioceses. **No canonical Orthodox
jurisdiction publishes a continuous text of the Chalcedonian horos or the
definition of Constantinople III, in any language.** The jurisdictions have
simply never digitised their own conciliar acts. So the Dei Filius move — register
the official-language original as controlling, an English version as the reading
witness — is not available for the councils.

But that search was looking in the wrong genre. Orthodoxy's own answer to *what
do you confess about God* is not a decree archive. It is the liturgy. The Creed
is said at every Liturgy and every baptism; the anaphora is prayed at every
Eucharist; the Synodikon is proclaimed from the ambon on the Sunday of Orthodoxy.
These are texts the whole Church confesses in the first person plural, published
by jurisdictions on their own domains — and their authority does not rest on a
translator's credit the way a scholarly edition does.

For this branch that is not a fallback. It is arguably a **higher** authority than
a decree text, because it is the confession the Church is making now, in worship,
rather than a document about a controversy settled in 451.

It also does what the project's posture asks: it lets the Orthodox branch speak in
its own voice, rather than being quoted to a learner out of a Protestant library.

---

## What this yields — verified, on official jurisdictional domains

### The find that matters most

**`goarch.org/-/the-divine-liturgy-of-saint-john-chrysostom`** — Greek Orthodox
Archdiocese of America. Plain HTML, no JavaScript, fetched successfully five times
across two independent passes. Named divisions including **The Holy Anaphora**.
In that section, verbatim and confirmed twice:

> "For You, O God, are ineffable, inconceivable, invisible, incomprehensible,
> existing forever, forever the same, You and Your only-begotten Son and Your Holy
> Spirit."

One sentence, on an official jurisdictional host, predicating **ineffable ·
inconceivable · invisible · incomprehensible · eternal · immutable** — and
predicating them of all three Persons. The apophatic and philosophical predicates
(H36–H51) were this branch's thinnest region and the reason Philaret was carrying
so much weight. This clause addresses most of them at once.

The same page carries the Creed ("I believe in one God, Father Almighty, Creator
of heaven and earth" — note **Creator**, where OCA and Antiochian read *Maker*)
and the Sanctus.

### The most complete host

**`roea.org`** — Romanian Orthodox Episcopate of America. (Not `roeaoca.org`,
which does not resolve.) The only official domain found publishing the
**Synodikon of Orthodoxy**, and it publishes the **anaphora of St Basil**
separately. Both text-layer PDFs, no JavaScript, no blocking.

- Synodikon: `roea.org/wp-content/uploads/2026/04/The-Synodikon-of-Orthodoxy-I.pdf`
  — numbered sections 1–6, **section 2 titled "The Symbol of Faith"**.
- St Basil anaphora: `roea.org/wp-content/uploads/2026/04/ST-BASIL-LITURGY-PRAYERS.pdf`
  — division "The Prayer of Praise and Thanksgiving [Anaphora]", verbatim:
  > "who is without beginning, unseen, incomprehensible, infinite, immutable."

### The rest, verified

| host | what it gives | locators |
|---|---|---|
| `oca.org/orthodoxy/prayers/symbol-of-faith` | the Creed as a liturgical prayer — a different page from the Hopko series already registered as BSR-EO-02 | "The Creed: The Symbol of Faith" |
| `holycouncil.org/rest-of-christian-world` | Crete 2016, ¶19: "confess the Triune God, Father, Son, and Holy Spirit, in accordance with the Nicene-Constantinopolitan Creed" — synodal, flat-numbered, verified in Greek and English | ¶1–24 |
| `holycouncil.org/encyclical-holy-council` | closing doxology: "O Father almighty, and Word and Spirit, one nature united in three persons, God beyond being and beyond divinity" | §I–VII, ¶1–20 |
| `antiochpatriarchate.org/en/page/.../2320/` | the Chalcedon clause in English with the Greek *and* Latin inline: "in two natures, inconfusedly, unchangeably, indivisibly, inseparably (ἐν δύο φύσεσιν ἀσυγχύτως, ἀτρέπτως, ἀδιαιρέτως, ἀχωρίστως)" | none — unsigned article |
| `myriobiblos.gr` (Church of Greece library) · `immspartis.gr` (Metropolis of Monemvasia and Sparta) | the Creed in original Greek; immspartis sets it out in **twelve numbered articles** | article 1–12 |
| `antiochian.org/regulararticle/596` | the Creed from the official Archdiocesan Pocket Prayer Book | "The Symbol of Faith (The Creed)" |

---

## Three landmines that must be recorded, not discovered later

**1. The Synodikon's Trinitarian sentences are mostly anathemas.** Its full
grammatical form is *"To those who dare to say that the Son of God, and likewise
the Holy Spirit, are not one in essence with the Father … ANATHEMA!"* Quoting the
inner clause alone **inverts the doctrine**. This is precisely the rubric item 3
failure the verifier exists to catch, and here it would arrive pre-baked in the
corpus. If the Synodikon is registered, the row note must say so and the corpus
builder must treat anathema-framed clauses as non-citable.

**2. Translations diverge, so phrases must be cut from the file, never assumed.**
The ROEA St Basil text reads **"unseen"** and **"immutable"**, not *invisible* and
*unchangeable*. GOARCH's Creed reads **"Creator"** where OCA and Antiochian read
**"Maker"**. Every ≤15-word asserted phrase must come from the registered file.

**3. GOARCH blocks unpredictably, and the block is path-shaped.** The Chrysostom
Liturgy page answers reliably; `/-/the-divine-liturgy-of-saint-basil-the-great`,
`/-/the-symbol-of-our-faith`, `/-/the-nicene-constantinopolitan-creed` and
`/-/the-dogmatic-tradition-of-the-orthodox-church` all return 403. So GOARCH can
carry the Chrysostom row but must not be the branch's anchor. Its St Basil
anaphora — the richest text in the rite — is unreadable there, which is exactly
why ROEA's copy matters.

Also structural: **`antiochian.org` is an Angular single-page app** — a plain fetch
returns only `<head>`. It needs a rendered fetch. And its full Liturgy PDFs are
served from `antiochianprodsa.blob.core.windows.net`, **off the official domain**,
which needs a registry ruling under R001. The legacy `ww1.antiochian.org`, where
most search results point, no longer resolves at all.

---

## What this does not solve

Q-434 asks for *without separation* — a conciliar christological predicate that
the liturgy does not assert in those terms. The best official-host witness is the
Antioch Patriarchate page, which carries the clause in English, Greek and Latin
but as an unsigned fragment with no session or horos locator and a visible typo
("Chirst") in the text. It can serve as a witness; it cannot be the controlling
text.

So BSR-EO-06 keeps ccel.org, but its role narrows: **the conciliar horos text,
cited only where a cell genuinely needs the definition itself.** It stops being
the branch's general-purpose source, which is what it had become by accident.

Two near misses worth recording so nobody re-runs them: `pravenc.ru` carries the
complete Chalcedonian horos in Russian keyed to ACO 2.1(2).129–130 and Mansi, inside
a numbered session — but it is an encyclopedia published under patriarchal blessing,
not a jurisdiction's own act. A Serbian parish site carries **both** horoi with
Mansi and ACO citations — but it is one parish, the translator is unnamed, and the
Sixth-Council text is openly abridged with ellipses.

---

## Proposed registry shape for Eastern Orthodox

Keep: BSR-EO-01 Creed (CONCILIAR, ratified), EO-02 Hopko (CATECHETICAL),
EO-03 GOARCH exposition (archived fetch, ratified), EO-04 Philaret, EO-05 Dositheus.
Narrow: EO-06 ccel.org → conciliar horos text only.

Add, as new rows:

| proposed | host | tier | why |
|---|---|---|---|
| BSR-EO-07 | `goarch.org` Chrysostom Liturgy | CONFESSIONAL (liturgically confessed) · the Creed within it resolves CONCILIAR under AC-10 | the apophatic clause; an official host; reliable fetch |
| BSR-EO-08 | `roea.org` St Basil anaphora | CONFESSIONAL | the second anaphora, and the predicates GOARCH blocks |
| BSR-EO-09 | `roea.org` Synodikon | CONFESSIONAL | proclaimed liturgically; carries the Creed as a named section; anathema guard required |
| BSR-EO-10 | `holycouncil.org` Crete 2016 | CONCILIAR (participating churches only) | a modern synodal act with real paragraph locators |
| BSR-EO-11 | `antiochpatriarchate.org` | CONCILIAR (witness, translation) | the Chalcedon clause with Greek and Latin, for Q-434 |
| BSR-EO-12 | `immspartis.gr` | CONCILIAR (original language) | the Creed in Greek, twelve numbered articles — the Dei Filius precedent, applied where it actually fits |

AC-10's per-document tier resolution, ratified yesterday, is what makes this
coherent: a liturgical book is a CONFESSIONAL row, and the Creed printed inside it
resolves CONCILIAR because its authority comes from Nicaea and Constantinople, not
from the service book that prints it.

**Cost of adopting it.** The branch goes from 6 rows to 12, which is more corpus,
more caveat surface, and a longer scope caveat. It also changes cal-3's baseline:
Eastern Orthodox recall would almost certainly rise well above 0.50, and the nine
of ten EO cells currently resting on Philaret or Dositheus would have
higher-tier alternatives. Two of the registered rows need non-plain fetches
(Antiochian rendered; GOARCH path-sensitive), which is work for the corpus builder.

**Sequencing.** If adopted, this merges to v2.25 **before** cal-3 runs, so
calibration measures the registry the app will actually ship. The cal-3 prompt
already written would need its corpus section updated.

---

## Addendum, same day — the tradition's own warrant for this design

The proposal above argued from the outside that liturgical texts should count as
doctrinal sources for this branch. That argument is no longer necessary. The
Orthodox Church in America states it directly, on its own domain, in its published
account of where Orthodox doctrine comes from:

> "The living experience of the Christian sacramental and liturgical life is a
> primary source of Christian doctrine."
>
> — `oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/sources-of-christian-doctrine/the-liturgy`

The same page adds that liturgical texts "can be trusted absolutely to reveal the
genuine doctrine of the Orthodox Church."

Its parent index lists nine sources of Christian doctrine by name — Revelation,
Tradition, Bible, **The Liturgy**, The Councils, The Fathers, The Saints, Canons,
Church Art — placing the Liturgy alongside the Councils rather than beneath them.

**This changes the standing of the liturgical rows.** They are not a workaround
adopted because the conciliar acts are undigitised. They are what this tradition
itself names as a primary source. The scope caveat should say that in the
tradition's own words rather than apologising for the absence of decree texts.

One discipline follows from it: this quotation belongs in the registry's rationale
and in the branch scope caveat — **not** as a cell citation. Both pages sit inside
the *The Orthodox Faith* series already registered as BSR-EO-02 (CATECHETICAL,
Hopko), so as evidence they carry that tier. What they establish is the design
warrant, not a predicate of God.

The councils page in the same series confirms the gap from the other direction:

> "The dogmatic definitions … and the canon laws of the ecumenical councils are
> understood to be inspired by God and to be expressive of His will for men."

— followed by summaries of what each council settled, and **no verbatim
definition anywhere on the page**. The jurisdictions teach the councils' authority
without publishing the councils' texts. That is the whole finding, stated by the
jurisdiction itself.

### One additional host, and one more confirmed block

**`thecathedralnyc.org/our-faith/teachings`** — the Greek Orthodox Archdiocesan
Cathedral of the Holy Trinity, under the Greek Orthodox Archdiocese of America.
Loads as plain HTML. Reproduces the **Nicene Creed in full**, under a section
headed "The Creed," with sections Revelation · Incarnation of Jesus Christ ·
Scriptures · Tradition · Councils and Creed · The Creed. Carries an apophatic
assertion in the Church's own voice:

> "While the inner Being of God always remains unknown and unapproachable, God has
> manifested Himself to us."

and

> "There is only One God, in whom there are three distinct Persons."

Standing: a cathedral, not the Archdiocese — so it speaks at parish level, below
GOARCH proper. Worth registering only as a **fallback witness for the Creed while
GOARCH's own Creed pages stay blocked**, since OCA and Antiochian already publish
the Creed on their own archdiocesan domains and both outrank it. Proposed as
BSR-EO-13, fallback tier, or omitted.

**`goarch.org/-/the-fundamental-teachings-of-the-eastern-orthodox-church` returns
403**, tested directly. That is the fifth `/-/` path confirmed blocked and it
tightens the diagnosis: on goarch.org the `/-/` friendly-URL space is
substantially unavailable to automated fetching, while `/chapel/texts` and the
Chrysostom Liturgy page answer. The archived fetch ratified for BSR-EO-03 is the
route to the rest of that material.
