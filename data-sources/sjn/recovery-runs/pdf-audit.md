# PDF extraction audit (Task 1c) — 2026-09-13T09:24:02Z

Workbook Seeking_Jesus_Teaching_Predicate_Source_v2.25r4_GATE6_SCOPE_RATIFIED_20260913.xlsx; rows BSR-AN-04, BSR-AN-05, BSR-LU-02, BSR-RP-04, BSR-MW-03, BSR-MA-01, BSR-MA-02, BSR-EO-08, BSR-EO-09; fetch cache REUSED. No model calls.
LEGACY = the extraction path the earlier branches ran on; REPAIRED = the path since 2026-09-13; STORED = the chunk store now.

| row | measured source | verdict | chunks | LEGACY intra-word splits | LEGACY chunks with furniture inside text | LEGACY→REPAIRED chunks changed | intra-word joins made | store matches REPAIRED |
|---|---|---|---|---|---|---|---|---|
| BSR-AN-04 | PDF_TEXT_LAYER | **AFFECTED** | 124 | 0 | 11 | 7 (+2/−2 locators) | 0 | yes |
| BSR-AN-05 | PDF_TEXT_LAYER | **AFFECTED** | 368 | 24 | 101 | 120 (+0/−0 locators) | 12 | yes |
| BSR-LU-02 | NO_TEXT_BY_POLICY | **NO_TEXT** | 0 | 0 | 0 | — (+0/−0 locators) | 0 | n/a |
| BSR-RP-04 | PDF_TEXT_LAYER | **AFFECTED** | 1018 | 0 | 74 | 60 (+0/−0 locators) | 0 | yes |
| BSR-MW-03 | PDF_TEXT_LAYER | **CLEAN** | 43 | 0 | 0 | 0 (+0/−0 locators) | 0 | yes |
| BSR-MA-01 | HTML | **HTML_SOURCED** | 23 | 0 | 0 | 0 (+0/−0 locators) | 0 | yes |
| BSR-MA-02 | HTML | **HTML_SOURCED** | 18 | 0 | 0 | 0 (+0/−0 locators) | 0 | yes |
| BSR-EO-08 | PDF_TEXT_LAYER | **CLEAN** | 16 | 0 | 0 | 0 (+0/−0 locators) | 0 | yes |
| BSR-EO-09 | PDF_TEXT_LAYER | **CLEAN** | 6 | 0 | 0 | 0 (+0/−0 locators) | 0 | yes |

## BSR-AN-04 — The Episcopal Church BCP 1979, "An Outline of the Faith"
- registry fetch_mode: `PDF`; measured source: **PDF_TEXT_LAYER**; manifest status REBUILT (drift accepted)
- PDF: 1001 pages, 1,170,640 chars; soft-hyphen line breaks 0 (soft hyphens total 0); hard-hyphen line breaks 12
- furniture detected (first pass) — top: {'concerning the service': 13, 'new testament': 13, 'lessons and psalms': 12, 'additional directions': 6, 'morning prayer': 6, 'evening prayer': 6, 'epiphany': 5, 'after the': 4, 'rite one': 3, 'a collect for sundays': 3, 'the people stand or kneel': 3, 'rite two': 3, 'prayers': 3, 'the examination': 3}
- furniture detected (first pass) — bottom: {'# psalm #': 98, 'psalm # #': 95, '# daily office year one': 30, 'daily office year two #': 30, '# collects: traditional': 27, 'collects: traditional #': 26, 'collects: contemporary #': 25, '# collects: contemporary': 25, '# morning prayer ii': 15, 'morning prayer ii #': 14, '# holy eucharist i': 14, 'holy eucharist i #': 14, '# holy eucharist ii': 14, 'holy eucharist ii #': 14, '# morning prayer i': 13, 'morning prayer i #': 12, 'lectionary a': 12, '# burial i': 11, '# prayers': 11, 'lectionary c': 11, 'prayers #': 10, '# catechism': 10, 'lectionary b': 10, '# holy baptism': 9, 'burial i #': 9, 'catechism #': 9, 'holy baptism #': 8, '# burial ii': 8, 'burial ii #': 8, 'psalms #, # #': 8, '# historical documents': 8, 'evening prayer i #': 7, 'prayers of the people #': 7, '# marriage': 7, '# ordination: bishop': 7, 'ordination: bishop #': 7, '# consecration of a church': 7, 'consecration of a church #': 7, '# psalms #, #': 7, 'psalm #:# #': 7, 'historical documents #': 7, '*as a canticle': 7, 'ministration to the sick #': 6, '# evening prayer i': 6, 'evening prayer ii #': 6, '# evening prayer ii': 6, '# easter vigil': 6, 'easter vigil #': 6, '# prayers of the people': 6, 'marriage #': 6, '# ordination: priest': 6, 'ordination: priest #': 6, '# ordination: deacon': 6, 'ordination: deacon #': 6, '# psalm #:#, #': 6, '* for the invitatory': 6, 'compline #': 5, 'new ministry #': 5, 'generation to generation in the church, and in christ jesus': 4, '# order for evening': 4, '# compline': 4, 'additional directions #': 4, '# litany': 4, 'litany #': 4, '# good friday': 4, '# confirmation': 4, 'confirmation #': 4, 'thanksgiving for a child #': 4, '# reconciliation': 4, '# ministration to the sick': 4, '# new ministry': 4, '# daily office': 4, 'daily office #': 4, '*** intended for use in the evening': 4, 'noonday #': 3, 'order for evening #': 3, '# daily devotions': 3, '# additional directions': 3, '# ash wednesday': 3, 'ash wednesday #': 3, 'good friday #': 3, '# order for eucharist': 3, 'order for eucharist #': 3, '# thanksgiving for a child': 3, 'reconciliation #': 3, '# at time of death': 3, 'thanksgivings #': 3, 'tables #': 3, '** intended for use in the morning': 3}
- LEGACY chunks: 0 intra-word split candidate(s) []; 11 chunk(s) carry a furniture line inside their text
    - Outline of the Faith (BCP p. 846) — The Old Covenant: Q. Wha: …What did God promise them? 846 Catechism God promised that they would be his people to bring all the…
    - Outline of the Faith (BCP p. 848) — Sin and Redemption: Q. W: …hip with God, with other people, and with all creation. 848 Catechism…
    - Outline of the Faith (BCP p. 850) — The New Covenant: Q. Wha: …apostles; and, through them, to all who believe in him. 850 Catechism…
    - Outline of the Faith (BCP p. 852) — The Holy Spirit: Q. How : …h ourselves, with our neighbors, and with all creation. 852 Catechism…
    - Outline of the Faith (BCP p. 853) — The Holy Scriptures: Q. : …es, commonly called the Bible, are the books of the Old and New Testaments; other books, called the Apocrypha, are often included in …
- REPAIRED: hyphenation at extraction: {'soft_hyphen_breaks_joined': 0, 'soft_hyphens_removed_midline': 0, 'joined_closed': 8, 'joined_compound': 3, 'joined_default': 2}
- REPAIRED: page furniture stripped at extraction: 1013 zone line(s); top [('lessons', 42), ('concerning the service', 13), ('new testament', 13), ('lessons and psalms', 12), ('additional directions', 6), ('morning prayer', 6), ('evening prayer', 6), ('epiphany', 5), ('after the', 4), ('rite one', 3), ('a collect for sundays', 3), ('the people stand or kneel', 3)]; bottom [('# psalm #', 98), ('psalm # #', 95), ('# daily office year one', 30), ('daily office year two #', 30), ('# collects: traditional', 27), ('collects: traditional #', 26), ('collects: contemporary #', 25), ('# collects: contemporary', 25), ('# morning prayer ii', 15), ('morning prayer ii #', 14), ('# holy eucharist i', 14), ('holy eucha
- REPAIRED chunks with a furniture line inside their text: 2 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 124 -> 124 chunks; 7 changed, 2 locator(s) added, 2 removed; text_hash 986a05bfd46d -> 9f812410836c
    - Outline of the Faith (BCP p. 848) — Sin and Redemp: `od, with other people, and with all creation. 848 Catechism` → `od, with other people, and with all creation.`
    - Outline of the Faith (BCP p. 850) — The New Covena: `and, through them, to all who believe in him. 850 Catechism` → `and, through them, to all who believe in him.`
    - Outline of the Faith (BCP p. 852) — The Holy Spiri: `s, with our neighbors, and with all creation. 852 Catechism` → `s, with our neighbors, and with all creation.`
    - Outline of the Faith (BCP p. 854) — The Church: Q.: ` to carry out Christ’s mission to all people. 854 Catechism` → ` to carry out Christ’s mission to all people.`
    - Outline of the Faith (BCP p. 856) — Prayer and Wor: `itence, oblation, intercession, and petition. 856 Catechism` → `itence, oblation, intercession, and petition.`
    - Outline of the Faith (BCP p. 860) — Other Sacramen: `the Holy Spirit to those being made bishops, 860 Catechism priests, and deacons, through prayer an` → `the Holy Spirit to those being made bishops, priests, and deacons, through prayer and the laying on of han`
- REPAIRED vs STORED: identical
- verdict: **AFFECTED**

## BSR-AN-05 — ACNA "To Be a Christian" (2020 approved edition)
- registry fetch_mode: `PDF`; measured source: **PDF_TEXT_LAYER**; manifest status REBUILT (drift accepted)
- PDF: 160 pages, 242,408 chars; soft-hyphen line breaks 55 (soft hyphens total 56); hard-hyphen line breaks 198
- furniture detected (first pass) — top: {'#': 146, 'index of scripture': 21, 'believing in christ': 17, 'becoming like christ': 13, 'appendix #': 13, 'belonging to christ': 12, 'the ten commandments': 10, 'the lord’s prayer': 6, 'concerning sacraments': 5, 'preface': 4, 'beginning with christ': 4, 'the apostles’ creed, article ii': 4, 'the apostles’ creed, article iii': 4, 'a rule of prayer': 4, 'salvation': 3, 'prayers for use with the catechism': 3}
- furniture detected (first pass) — bottom: {}
- LEGACY chunks: 24 intra-word split candidate(s) [('ro', 'mans', 3, 'ATTESTED'), ('chris', 'tian', 3, 'ATTESTED'), ('ar', 'ticles', 1, 'ATTESTED'), ('colos', 'sians', 2, 'ATTESTED'), ('tim', 'othy', 1, 'ATTESTED'), ('mat', 'thew', 9, 'ATTESTED'), ('gen', 'esis', 1, 'ATTESTED'), ('philip', 'pians', 2, 'ATTESTED'), ('le', 'viticus', 2, 'ATTESTED'), ('thes', 'salonians', 3, 'ATTESTED'), ('num', 'bers', 1, 'ATTESTED'), ('cove', 'nant', 6, 'ATTESTED'), ('deu', 'teronomy', 4, 'ATTESTED'), ('zecha', 'riah', 1, 'ATTESTED'), ('sam', 'uel', 1, 'ATTESTED'), ('deuter', 'onomy', 3, 'ATTESTED')]; 101 chunk(s) carry a furniture line inside their text
    - To Be a Christian, Q.3 — All the answers and questions shoul: … for you. This is the Gospel (“good news”) of Jesus Christ. beginning with christ t h e g o s p e l God created the world and made us to be i…
    - To Be a Christian, Q.8 — Who is Jesus Christ?: … 110; John 3:13–15; Philippians 2:5–11; Colossians 1:15–20) salvation…
    - To Be a Christian, Q.9 — Is there any other way of salvation: …Is there any other way of salvation? No. The apostle Peter said of Jesus, “There is salvation i…
    - To Be a Christian, Q.10 — How should you respond to the Gosp: …or and Lord, and prepare to be baptized. “Now is the day of salvation.” (2 Co rin thi ans 6:2; see also Psalm 32; Isaiah 55:6–7; …
    - To Be a Christian, Q.13 — How can you repent and put your fa: … Joel 2:32; Acts 16:30–34; Romans 10:11–13; Hebrews 12:1–2) beginning with christ…
- REPAIRED: hyphenation at extraction: {'soft_hyphen_breaks_joined': 55, 'soft_hyphens_removed_midline': 1, 'joined_closed': 142, 'joined_default': 56}
- REPAIRED: page furniture stripped at extraction: 269 zone line(s); top [('#', 146), ('index of scripture', 21), ('believing in christ', 17), ('becoming like christ', 13), ('appendix #', 13), ('belonging to christ', 12), ('the ten commandments', 10), ('the lord’s prayer', 6), ('concerning sacraments', 5), ('preface', 4), ('beginning with christ', 4), ('the apostles’ creed, article ii', 4)]; bottom []
- REPAIRED: intra-word splits repaired on vocabulary evidence: 12 join(s): 'Chris tian'->'Christian' [ATTESTED]; 'Chris tian'->'Christian' [ATTESTED]; 'Chris tian'->'Christian' [ATTESTED]; 'Chris tian'->'Christian' [ATTESTED]; 'Chris tian'->'Christian' [ATTESTED]; 'cove nant'->'covenant' [ATTESTED]; 'cove nant'->'covenant' [ATTESTED]; 'cove nant'->'covenant' [ATTESTED]; 'cove nant'->'covenant' [ATTESTED]; 'cove nant'->'covenant' [ATTESTED]; 'cove nant'->'covenant' [ATTESTED]; 'cove nantal'->'covenantal' [STEM of covenant]
- REPAIRED chunks with a furniture line inside their text: 38 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 368 -> 368 chunks; 120 changed, 0 locator(s) added, 0 removed; text_hash ad8cc138a1d4 -> 12dbaa057f89
    - To Be a Christian, Q.3 — All the answers and quest: ` is the Gospel (“good news”) of Jesus Christ. beginning with christ t h e g o s p e l God created the world and ` → ` is the Gospel (“good news”) of Jesus Christ. t h e g o s p e l God created the world and `
    - To Be a Christian, Q.6 — How does God save you?: `; see also Psalm 34; Zechariah 12:10–13:2; Ro mans 3:23–26)` → `; see also Psalm 34; Zechariah 12:10–13:2; Romans 3:23–26)`
    - To Be a Christian, Q.8 — Who is Jesus Christ?: `3–15; Philippians 2:5–11; Colossians 1:15–20) salvation` → `3–15; Philippians 2:5–11; Colossians 1:15–20)`
    - To Be a Christian, Q.13 — How can you repent and p: `ts 16:30–34; Romans 10:11–13; Hebrews 12:1–2) beginning with christ` → `ts 16:30–34; Romans 10:11–13; Hebrews 12:1–2)`
    - To Be a Christian, Q.17 — By what means will God t: `–3; Psalm 1; Acts 2:42–47; Hebrews 10:23–25) salvation A Prayer for God’s Love Almighty God, ` → `–3; Psalm 1; Acts 2:42–47; Hebrews 10:23–25) A Prayer for God’s Love Almighty God, you so loved the world that `
    - To Be a Christian, Q.24 — What is the Apostles’ Cr: `ather almighty, creator of heaven and earth. believing in christ I believe in Jesus Christ, his only Son, our ` → `ather almighty, creator of heaven and earth. I believe in Jesus Christ, his only Son, our `
- REPAIRED vs STORED: identical
- verdict: **AFFECTED**

## BSR-LU-02 — Augsburg Confession, LCMS file library
- registry fetch_mode: `PDF behind client viewer`; measured source: **NO_TEXT_BY_POLICY**; manifest status AUTHORITY_URL_ONLY
- policy: files.lcms.org is a client-side viewer (AC-08): registered as the LCMS adoption URL; no text extraction
- verdict: **NO_TEXT**

## BSR-RP-04 — PC(USA) Book of Confessions 2016 (Nicene, Apostles', Scots, Heidelberg, Second Helvetic, W
- registry fetch_mode: `PDF (large; normalize)`; measured source: **PDF_TEXT_LAYER**; manifest status REBUILT (drift accepted)
- PDF: 473 pages, 1,088,413 chars; soft-hyphen line breaks 0 (soft hyphens total 0); hard-hyphen line breaks 1439
- furniture detected (first pass) — top: {'book of confessions': 193, 'reference': 116, 'index': 59, 'presbyterian church': 41, 'the second helvetic confession': 34, 'endnotes for #.#–.#': 29, 'the heidelberg catechism': 23, 'the westminster confession of faith': 22, 'the larger catechism': 18, '[text]': 12, 'confessional nature of the church report': 10, 'the scots confession': 9, 'the confession of #': 8, 'the shorter catechism': 6, 'endnotes #.#–.#': 5, 'confession of belhar': 5, 'a brief statement of faith': 5, 'the': 3, 'assessment of proposed amendments': 3, 'the nicene creed': 3}
- furniture detected (first pass) — bottom: {'[text]': 12}
- LEGACY chunks: 0 intra-word split candidate(s) []; 74 chunk(s) carry a furniture line inside their text
    - Book of Confessions 1.3 (Nicene Creed): …ction of the dead, and the life of the world to come. Amen. [TEXT] The Apostles’ Creed Although not written by apostles, the A…
    - Book of Confessions 2.3 (Apostles' Creed): …e resurrection of the body; and the life everlasting. Amen. [TEXT] The Scots Confession Three documents from the period of the…
    - Book of Confessions 3.03 (Scots Confession): …ured faith in the promise of God revealed to Reprinted from The Scots Confession: 1560. Edited with an Introduction by G. D. Henderson. Rend…
    - Book of Confessions 3.18 (Scots Confession): … usurped title, lineal succession, appointed place, nor the numbers of men approving an error. For Cain was before Abel and Set…
    - Book of Confessions 3.20 (Scots Confession): …n or prerogative that they could not err by reason of their numbers. This, we judge, was the primary reason for general council…
- REPAIRED: hyphenation at extraction: {'soft_hyphen_breaks_joined': 0, 'soft_hyphens_removed_midline': 0, 'joined_default': 116, 'joined_closed': 1314, 'suspended_kept': 9}
- REPAIRED: page furniture stripped at extraction: 1094 zone line(s); top [('numbers', 231), ('book of confessions', 193), ('reference', 116), ('page', 116), ('index', 59), ('presbyterian church', 41), ('in the united states', 41), ('the united presbyterian church', 41), ('in the united states of america', 41), ('the second helvetic confession', 34), ('endnotes for #.#–.#', 29), ('the heidelberg catechism', 23)]; bottom []
- REPAIRED chunks with a furniture line inside their text: 26 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 1018 -> 1018 chunks; 60 changed, 0 locator(s) added, 0 removed; text_hash 7eb36c085dd1 -> 0461b5e70478
    - Book of Confessions 1.3 (Nicene Creed): `ead, and the life of the world to come. Amen. [TEXT] The Apostles’ Creed Although not written by ` → `ead, and the life of the world to come. Amen. The Apostles’ Creed Although not written by `
    - Book of Confessions 2.3 (Apostles' Creed): ` of the body; and the life everlasting. Amen. [TEXT] The Scots Confession Three documents from the period of the Refor` → ` of the body; and the life everlasting. Amen. Three documents from the period of the Refor`
    - Book of Confessions 3.25 (Scots Confession): `s cleave to the true knowledge of thee. Amen. [TEXT] The Heidelberg Catechism The Reformation was not a singular movement.` → `s cleave to the true knowledge of thee. Amen. The Reformation was not a singular movement.`
    - Book of Confessions 4.129 (Heidelberg Catechism): `1:; 2 Tim. 2: THE SECOND HELVETIC CONFESSION [TEXT] The Second Helvetic Confession The word “Helvetic” is Latin for “Swiss.” The` → `1:; 2 Tim. 2: THE SECOND HELVETIC CONFESSION The word “Helvetic” is Latin for “Swiss.” The`
    - Book of Confessions 5.260 (Second Helvetic Confess: `s. Amen. THE WESTMINSTER CONFESSION OF FAITH [TEXT] The Westminster Standards In 1643, the Englis` → `s. Amen. THE WESTMINSTER CONFESSION OF FAITH The Westminster Standards In 1643, the Englis`
    - Book of Confessions 6.006 (Westminster Confession : `ncludes “of John.” d UPCUSA ed. reads: “of.” THE WESTMINSTER CONFESSION OF FAITH Presbyterian` → `ncludes “of John.” d UPCUSA ed. reads: “of.” God to be necessary for the saving understanding of such things as are revealed in th`
- REPAIRED vs STORED: identical
- verdict: **AFFECTED**

## BSR-MW-03 — Global Methodist Church, 2024 Book of Doctrines and Discipline
- registry fetch_mode: `PDF - text layer present; controlled storage, admitted under the 12 Sep 2026 ruling`; measured source: **PDF_TEXT_LAYER**; manifest status UNCHANGED
- PDF: 156 pages, 492,462 chars; soft-hyphen line breaks 0 (soft hyphens total 0); hard-hyphen line breaks 14
- furniture detected (first pass) — top: {'# book of doctrines and discipline': 150, '#': 147}
- furniture detected (first pass) — bottom: {'go to previous page': 148}
- LEGACY chunks: 0 intra-word split candidate(s) []; 0 chunk(s) carry a furniture line inside their text
- REPAIRED: hyphenation at extraction: {'soft_hyphen_breaks_joined': 0, 'soft_hyphens_removed_midline': 0, 'joined_default': 2, 'joined_compound': 12, 'joined_closed': 1}
- REPAIRED: page furniture stripped at extraction: 445 zone line(s); top [('# book of doctrines and discipline', 150), ('#', 147)]; bottom [('go to previous page', 148)]
- REPAIRED chunks with a furniture line inside their text: 0 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 43 -> 43 chunks; 0 changed, 0 locator(s) added, 0 removed; text_hash fd0b21f34ad2 -> fd0b21f34ad2
- REPAIRED vs STORED: identical
- **Article I check**: 'of infinite power, wisdom, and good' in LEGACY ['Articles of Religion, Article I - Of Faith in the Holy Trinity']; in REPAIRED ['Articles of Religion, Article I - Of Faith in the Holy Trinity']; in STORED ['Articles of Religion, Article I - Of Faith in the Holy Trinity']; 'wisdom, and goodness' in REPAIRED: 0 (must be 0)
- verdict: **CLEAN**

## BSR-MA-01 — Confession of Faith in a Mennonite Perspective (1995), Article 1 and following
- registry fetch_mode: `HTML + PDF`; measured source: **HTML**; manifest status UNCHANGED
- LEGACY chunks: 0 intra-word split candidate(s) []; 0 chunk(s) carry a furniture line inside their text
- REPAIRED chunks with a furniture line inside their text: 0 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 23 -> 23 chunks; 0 changed, 0 locator(s) added, 0 removed; text_hash bd1327f512bd -> bd1327f512bd
- REPAIRED vs STORED: identical
- verdict: **HTML_SOURCED**

## BSR-MA-02 — Dordrecht Confession (1632)
- registry fetch_mode: `PDF`; measured source: **HTML**; manifest status UNCHANGED
- LEGACY chunks: 0 intra-word split candidate(s) []; 0 chunk(s) carry a furniture line inside their text
- REPAIRED chunks with a furniture line inside their text: 0 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 18 -> 18 chunks; 0 changed, 0 locator(s) added, 0 removed; text_hash c9a2f489950f -> c9a2f489950f
- REPAIRED vs STORED: identical
- verdict: **HTML_SOURCED**

## BSR-EO-08 — Anaphora of St Basil the Great (Romanian Orthodox Episcopate of America)
- registry fetch_mode: `PDF - text layer present`; measured source: **PDF_TEXT_LAYER**; manifest status REBUILT (drift accepted)
- PDF: 32 pages, 50,178 chars; soft-hyphen line breaks 0 (soft hyphens total 0); hard-hyphen line breaks 83
- furniture detected (first pass) — top: {'#': 32}
- furniture detected (first pass) — bottom: {'anexa vii - liturghia sf. vasile cel mare': 16, 'appendix vii - liturgy of st. basil the great': 15}
- LEGACY chunks: 0 intra-word split candidate(s) []; 0 chunk(s) carry a furniture line inside their text
- REPAIRED: hyphenation at extraction: {'soft_hyphen_breaks_joined': 0, 'soft_hyphens_removed_midline': 0, 'joined_closed': 45, 'joined_compound': 3, 'joined_default': 32}
- REPAIRED: page furniture stripped at extraction: 63 zone line(s); top [('#', 32)]; bottom [('anexa vii - liturghia sf. vasile cel mare', 16), ('appendix vii - liturgy of st. basil the great', 15)]
- REPAIRED chunks with a furniture line inside their text: 0 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 16 -> 16 chunks; 0 changed, 0 locator(s) added, 0 removed; text_hash d4337c98b3ce -> d4337c98b3ce
- REPAIRED vs STORED: identical
- verdict: **CLEAN**

## BSR-EO-09 — The Synodikon of Orthodoxy (Romanian Orthodox Episcopate of America)
- registry fetch_mode: `PDF - text layer; BLOCKING GUARD: anathema-framed clauses non-citable`; measured source: **PDF_TEXT_LAYER**; manifest status UNCHANGED
- PDF: 6 pages, 8,746 chars; soft-hyphen line breaks 0 (soft hyphens total 0); hard-hyphen line breaks 0
- furniture detected (first pass) — top: {'#': 6}
- furniture detected (first pass) — bottom: {}
- LEGACY chunks: 0 intra-word split candidate(s) []; 0 chunk(s) carry a furniture line inside their text
- REPAIRED: hyphenation at extraction: {'soft_hyphen_breaks_joined': 0, 'soft_hyphens_removed_midline': 0}
- REPAIRED: page furniture stripped at extraction: 6 zone line(s); top [('#', 6)]; bottom []
- REPAIRED chunks with a furniture line inside their text: 0 (prose mentions of a heading's words count here too)
- LEGACY → REPAIRED: 6 -> 6 chunks; 0 changed, 0 locator(s) added, 0 removed; text_hash e53307208999 -> e53307208999
- REPAIRED vs STORED: identical
- verdict: **CLEAN**

