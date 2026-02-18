# Words of Plainness — Card-Chapter Authoring Guide

**February 2026**

**Purpose:** Practical reference for producing card-chapter content. Defines the structure, voice, frontmatter schema, and production workflow for every discipleship card in Part II of the website. All authoring decisions documented here are final and should be treated as constraints.

**Audience:** The author (Aaron) and any future Claude session assisting with card-chapter production.

**Companion documents:** WoP_CardChapter_MasterList_Revised (card assignments and scope notes), WoP-Card-Chapter-Handoff-Feb2026.md (template architecture), WoP-Eleventy-Frontmatter-Reference.md (standard chapter schema), WoP-Eleventy-Content-Workflow (full production pipeline).

---

## 1. Content Template

Every card-chapter contains 3–5 discipleship cards. Each card teaches one practice through three tabs and a commitment selection.

### 1.1 Card Anatomy

Each card renders on the website as a tabbed interface:

| Component | Description |
|-----------|-------------|
| Card Header | Card number badge, card title, scripture references (linked) |
| Tab 1: How We Practice | Doctrinal teaching on the practice. First-person plural voice. |
| Tab 2: How It Blesses | Personal witness + scriptural promises. Bridge text transitions to commitment. |
| Tab 3: How Will You Practice? | Three tiered commitment options + optional custom input + N/A + reflection prompt. |

### 1.2 Tab Content Specifications

#### Tab 1: How We Practice (`practice`)

- **Voice:** First-person plural ("We practice…", "Latter-day Saints are taught…"). Solidarity, not instruction from above.
- **Content:** Doctrinal teaching on the practice. What we do, why we do it, how it connects to the gospel of Jesus Christ. Draw from the source manuscript, adding scriptural anchors.
- **Scripture density:** Heaviest of the three tabs. Typically 2–4 scripture references per card, woven into the teaching text as hyperlinked citations.
- **Word count target:** 150–300 words (2–3 paragraphs). Compressed and direct. Every sentence should teach or anchor.
- **HTML structure:** Begin with an `<h4>` subheading (3–7 words). Follow with `<p>` paragraphs. Scripture references use `<a class="scripture-link">` with full churchofjesuschrist.org URL.

#### Tab 2: How It Blesses (`blesses`)

- **Voice:** Mixed. Scriptural promises may use third person. Personal witness uses first person singular ("I have experienced…").
- **Content:** Two elements interleaved: (a) scriptural promises attached to the practice, and (b) brief personal witness from the authors. The witness should be specific, concrete, and pastoral — not generic testimony. End with a bridge-text paragraph transitioning the reader toward the commitment tab.
- **Scripture density:** Lighter than the Practice tab. Typically 1–2 references, used to ground the promises.
- **Word count target:** 150–250 words (2–3 paragraphs plus bridge text).
- **HTML structure:** Begin with an `<h4>` subheading. Follow with `<p>` paragraphs. Final paragraph uses `<p class="bridge-text">` for the transition to commitment.

#### Tab 3: How Will You Practice? (`commitments`)

- **Voice:** Second person ("You can…", "I will…" as the reader's own pledge). Personal invitation.
- **Content:** Three commitment options at graduated tiers, plus an optional custom text input and an N/A option (both built into the template). An optional reflection prompt appears as italic text above a textarea.
- **Audio narration:** Silent. The Commitment tab is the reader's private reflective space. Do not narrate this tab.

### 1.3 Commitment Tier Definitions

Commitments are the heart of the adaptive system. The reader's cumulative choices across all cards build their "My Reflections & Goals" profile. Tier language must be gospel-framed but use natural language — accessible without hiding the spiritual context.

| Tier | Tag | Audience | Language Pattern |
|------|-----|----------|------------------|
| Covenant | `covenant` | Baptized, temple-attending Latter-day Saints | "I will [specific covenant practice] [this week / daily / at the next opportunity]." |
| Seeker | `seeker` | Believers exploring deeper commitment | "I will [moderate practice] [specific timeframe] and [notice / reflect on] what I experience." |
| Explore | `explore` | Curious, open-minded, or spiritually undecided | "I will [accessible activity framed in gospel language] [low-pressure timeframe]." |

**Key principles for writing commitments:**

**Specificity:** Every commitment should name a concrete action and a timeframe. "I will be more prayerful" is too vague. "I will pray morning and evening this week" is actionable.

**Graduated stretch:** Covenant is the fullest expression. Seeker is a meaningful step. Explore is a genuine first step, not a throwaway. Each tier should feel like it matters.

**Gospel-framed natural language:** The explore tier does not avoid spiritual vocabulary — it makes spiritual vocabulary accessible. "Set aside time this week to rest and reflect" is gospel-framed (Sabbath principle) but uses natural language a non-member could embrace.

**Order in frontmatter:** Always covenant first, seeker second, explore third. The template renders them in this order.

### 1.4 Reflection Prompts

Each card may include an optional reflection prompt — a single question that appears as italic text above a textarea. Prompts should be introspective, open-ended, and non-judgmental.

- **Good:** "What is one thing you are grateful for today?" — Open, personal, emotionally accessible.
- **Good:** "Is there something weighing on your conscience that you would like to release?" — Direct but gentle, invites honest engagement.
- **Avoid:** "Do you keep the Sabbath?" — Binary yes/no questions produce defensiveness, not reflection.

If a card does not warrant a reflection prompt, set the field to an empty string. The template will skip rendering it.

---

## 2. Voice and Tone Guidelines

Card-chapter content is pastoral, compressed, direct, warm, and action-oriented. It is not academic, therapeutic, or apologetic.

### 2.1 Voice by Tab

| Tab | Voice | Example |
|-----|-------|---------|
| How We Practice | First-person plural ("we") | "We kneel when possible. We address our Heavenly Father directly." |
| How It Blesses | Mixed: scripture (third person) + witness (first singular) | "The Savior promised rest. I have felt that rest." |
| Commitment | Second person ("you" / "I will") | "I will pray morning and evening this week." |

### 2.2 Tone Markers

**Shepherding, not managerial.** The author is a fellow disciple walking alongside the reader, not an administrator issuing directives.

**Instructive, not tentative.** Teach with confidence. Do not hedge doctrine with phrases like "some believe" or "it is thought that." The author's theology is presented as authoritative within the Latter-day Saint tradition.

**Compassionate, not permissive.** Meet the reader where they are without lowering the standard. The three-tier system handles accessibility — the content itself does not compromise.

**Confident, not defensive.** Do not anticipate objections or insert disclaimers. Present the practice, testify of its blessings, invite commitment.

### 2.3 Card Content vs. Standard Chapter Prose

Card content is more compressed than standard prose chapters. Where a prose chapter might develop an idea across four paragraphs, a card develops it in two. Where a prose chapter builds cumulative theological weight through extended argument, a card distills to the actionable core. Think of cards as the concentrated essence of a teaching, not a summary of it.

### 2.4 Church Style Guide

| Avoid | Use |
|-------|-----|
| Mormon | Latter-day Saint (or the full Church name) |
| LDS | The Church (or the full name) |
| Mormon Church | The Church of Jesus Christ of Latter-day Saints |
| Mormonism | The restored gospel of Jesus Christ |

Exception: The manuscript title "Mormon Christianity" and the original "Claimer" may retain the historical term where it appears as part of established titles or quotations.

---

## 3. Frontmatter Schema Reference

Card-chapters use `.njk` files (not `.md`) with YAML frontmatter. All content lives in the frontmatter; there is no Markdown body. The card-chapter layout (`card-chapter.njk`) consumes these fields.

### 3.1 Page-Level Fields

| Field | Type | Notes |
|-------|------|-------|
| `title` | String | Chapter title as displayed in hero section |
| `chapter` | Number | Sequential chapter number (7–26 for Part II) |
| `slug` | String | URL-friendly identifier: `"10-keeping-the-sabbath"` |
| `chapterId` | String | Used for localStorage key + lyrics include path |
| `layout` | String | Always: `layouts/card-chapter.njk` |
| `permalink` | String | URL path: `/chapters/10-keeping-the-sabbath/` |
| `scripture.text` | String | Opening scripture quote displayed in hero |
| `scripture.reference` | String | Citation: `"D&C 59:9"` |
| `scripture.url` | String | Path after `/study/scriptures/` |
| `prevChapter.url` | String | Previous chapter URL path |
| `prevChapter.title` | String | Previous chapter display title (include "Chapter #:") |
| `nextChapter.url` | String | Next chapter URL path |
| `nextChapter.title` | String | Next chapter display title |
| `discordChannelId` | String | Discord channel ID string, or empty string |

### 3.2 Optional Asset Fields

| Field | Type | Notes |
|-------|------|-------|
| `audio.testimony.title` | String | Musical testimony song title |
| `audio.testimony.description` | String | Brief thematic description |
| `audio.testimony.file` | String | Filename only (template prepends `/assets/audio/`) |
| `lyrics` | Boolean | Set `true` if `lyrics/chapter-{chapterId}.njk` exists |
| `infographic` | String | Filename only (template prepends `/assets/images/`) |
| `slides.path` | String | Folder under `/assets/slides/` with trailing slash: `"chapter-10/"` |
| `slides.count` | Number | Total slide PNGs (`slide-01.png` through `slide-XX.png`) |
| `pdf` | String | Filename only (template prepends `/assets/pdf/`) |

**Slides path convention:** Card-chapters use the same convention as standard chapters: `chapter-##/` (not `WoP_Ch##/`). Files are named `slide-01.png`, `slide-02.png`, etc.

### 3.3 Card Array Fields

The `cards` array is the core content container. Each entry becomes one discipleship card on the page.

| Field | Type | Notes |
|-------|------|-------|
| `cards[].title` | String | Card title displayed in header |
| `cards[].scriptures[].display` | String | Human-readable reference: `"D&C 59:9–12"` |
| `cards[].scriptures[].url` | String | URL path: `"dc-testament/dc/59?id=p9#p9"` |
| `cards[].practice` | String (HTML) | Tab 1 content. Use YAML pipe for multiline. Rendered via safe filter. |
| `cards[].blesses` | String (HTML) | Tab 2 content. Same format as practice. |
| `cards[].commitments[].text` | String | Commitment description text |
| `cards[].commitments[].tier` | String | One of: `covenant`, `seeker`, `explore` |
| `cards[].reflection` | String | Reflection prompt text, or empty string to skip |

### 3.4 Scripture URL Construction

Scripture URLs in card frontmatter use the path after `/study/scriptures/` on churchofjesuschrist.org.

| Volume | URL Pattern | Example |
|--------|-------------|---------|
| Old Testament | `ot/[book]/[chapter]?id=p[verse]#p[verse]` | `ot/isa/58?id=p13#p13` |
| New Testament | `nt/[book]/[chapter]?id=p[verse]#p[verse]` | `nt/matt/6?id=p6#p6` |
| Book of Mormon | `bofm/[book]/[chapter]?id=p[verse]#p[verse]` | `bofm/alma/34?id=p27#p27` |
| D&C | `dc-testament/dc/[section]?id=p[verse]#p[verse]` | `dc-testament/dc/59?id=p9#p9` |
| Pearl of Great Price | `pgp/[book]/[chapter]?id=p[verse]#p[verse]` | `pgp/moses/3?id=p2#p2` |

**Verse ranges:** For a range like Isaiah 58:13–14, the URL points to the first verse: `ot/isa/58?id=p13#p13`. The `display` field shows the full range.

**In-text links:** Scripture references inside `practice` and `blesses` HTML use full `<a>` tags:

```html
<a class="scripture-link" href="https://www.churchofjesuschrist.org/study/scriptures/dc-testament/dc/59?id=p9#p9" target="_blank">D&C 59:9–12</a>
```

---

## 4. Production Workflow

Card-chapters are built in complete units — all cards for one chapter at once. No half-built chapters.

### 4.1 Step-by-Step Process

#### Step 1: Consult the Master List

Open `WoP_CardChapter_MasterList_Revised`. Identify the chapter to build, its card assignments, scope notes, and source manuscript chapter(s). Read the scope notes carefully — they define what content belongs in each card.

#### Step 2: Read the Source Manuscript

Read the full manuscript chapter(s) mapped to this card-chapter. Identify the key teachings, scripture references, quotations from Church leaders, and personal witness material. Note the manuscript's footnotes for citation conversion.

#### Step 3: Draft All Cards

Draft all cards for the chapter in a single working session. For each card:

(a) Write the Practice tab first. Distill the manuscript's teaching on this specific practice into 150–300 words. Add an `<h4>` subheading. Weave in 2–4 scripture references with full hyperlinks.

(b) Write the Blesses tab second. Combine scriptural promises with a brief personal witness. Close with bridge text.

(c) Write the commitments third. Three tiers: covenant, seeker, explore. Specific, actionable, timeframed.

(d) Write the reflection prompt last (or leave empty if the card does not warrant one).

#### Step 4: Assemble Frontmatter

Build the `.njk` file with complete YAML frontmatter. Use the schema in Section 3. Verify all scripture URLs by testing at least one link per card. Save as `src/chapters/##-chapter-slug.njk`.

#### Step 5: Add Assets (When Ready)

Assets can be added after the content file is deployed:

- **Musical testimony:** One song per card-chapter covering all cards (not one per card). Add `audio.testimony` fields when the song is produced.
- **Study slides:** Place in `src/assets/slides/chapter-##/` as `slide-01.png` through `slide-XX.png`.
- **Infographic:** Place in `src/assets/images/` as `chapter-##-infographic.png`.
- **PDF:** Place in `src/assets/pdf/` as `WoP_Ch##_Title.pdf`.
- **Lyrics partial:** Create `src/_includes/lyrics/chapter-{chapterId}.njk` if testimony has lyrics.

#### Step 6: Audio Narration

Narrate the Practice and Blesses tabs only. The Commitment tab is silent (reader's private reflective space). Audio narration for card-chapters does not use the sentence-level timestamp sync system — it is tab-level audio only. Production follows the standard ElevenLabs workflow documented in the Content Workflow.

#### Step 7: Quality Checks

Before deployment, verify:

**Content:** Each card has all three tabs populated. Commitment tiers are in correct order (covenant, seeker, explore). Scripture references are accurate. Personal witness is specific and concrete.

**Frontmatter:** YAML syntax is valid. All required fields present. Scripture URLs resolve correctly. Asset filenames match disk (run `Get-ChildItem` to verify).

**Rendering:** Run `npm run serve` and test locally. Tabs switch correctly. Commitments save to localStorage. Cumulative summary updates. Learning tools render if assets are present.

#### Step 8: Deploy

Commit and push to main. Vercel auto-deploys. Verify the live page.

### 4.2 Batch Size

All cards for one chapter are drafted, assembled, and deployed as a complete unit. This ensures the chapter is coherent as a whole and the cumulative summary works correctly. Never deploy a partial chapter.

---

## 5. Reference Implementation

### 5.1 Annotated Walkthrough: Ch 9 (Prayer & Repentance)

The deployed chapter at `src/chapters/13-prayer-and-repentance.njk` (to be renumbered to Ch 9) serves as the canonical reference. Key patterns to note:

#### Page-Level Frontmatter

The opening scripture (D&C 19:38) sets the spiritual frame for the entire chapter. Navigation links use placeholder URLs (to be updated during renumbering). The `discordChannelId` is empty (to be assigned when the Discord channel is created).

#### Card 1: Personal Daily Prayer

**Practice tab:** Opens with `<h4>Speaking to God as Father</h4>`. Two paragraphs. First paragraph teaches what Latter-day Saints do (kneel, address Father, close in Christ's name). Second paragraph anchors in Alma 34:27. Voice: "We kneel… We address…"

**Blesses tab:** Opens with `<h4>A Witness of Daily Prayer</h4>`. Three paragraphs. First two are personal witness (specific season of spiritual dryness, specific morning of breakthrough). Third is bridge text with `class="bridge-text"`. The witness is concrete: "I had nothing eloquent to offer — only 'Father, I need Thee.'"

**Commitments:** Covenant: "I will pray morning and evening this week, on my knees when possible." Seeker: "I will offer one honest prayer each day." Explore: "I will pause once a day to quietly reflect on gratitude." Note the gradient: covenant is full practice, seeker is partial but sincere, explore is accessible but genuinely spiritual.

**Reflection:** "What is one thing you are grateful for today?" — Simple, open-ended, universally accessible.

#### Card 2: Repentance as a Way of Living

**Practice tab:** Two paragraphs. First teaches the daily practice of repentance (not emergency measure). References President Nelson by name. Second describes the full process (recognition, sorrow, confession, abandonment, restitution) then the simpler daily version. Connects to sacrament renewal.

**Blesses tab:** Opens with `<h4>The Freedom of Turning</h4>`. Specific witness about carrying a grudge — not generic "repentance is good." The Spirit's role described as "piercing clarity," not condemnation. Closes with Matthew 11:28 as a linked citation and bridge text.

#### Card 3: Fasting and Prayer

**Practice tab:** Teaches both monthly fast and purpose-driven fasting. Links fasting to financial generosity (fast offerings). Anchors in Matthew 4:4 and Alma 5:46.

**Blesses tab:** Opens with `<h4>What Hunger Taught Me</h4>`. Honest about early failure ("miserable" fasts). Turning point: brother's cancer diagnosis. Specific, vulnerable, pastoral.

#### Card 4: Spiritual Self-Assessment

**Practice tab:** Teaches three assessment channels: temple recommend interviews, Pauline self-examination (2 Corinthians 13:5), Alma's questions (Alma 5:14). Frames interviews as invitation, not inquisition. Opens the practice to non-members: "whether you participate in formal worthiness interviews or not."

### 5.2 Worked Example: Ch 10, Card 1 (The Sabbath Covenant)

*Source: Manuscript Chapter 19, "Keeping the Sabbath."*

*Scope note from master list: Origin in Creation, Hebrew "shabbāth." Shifted to Sunday after Resurrection. D&C 59:9–12 confirms Lord's Day. Purpose: holy day, not just rest day.*

#### Frontmatter (Card 1 only, within the cards array)

```yaml
- title: "The Sabbath Covenant"
  scriptures:
    - display: "D&C 59:9–12"
      url: "dc-testament/dc/59?id=p9#p9"
    - display: "Exodus 20:8–11"
      url: "ot/ex/20?id=p8#p8"
```

#### Practice Tab

`<h4>A Holy Day from the Beginning</h4>`

Even God rests from His labors. The scriptural accounts of Creation record that He "rested on the seventh day from all his work which he had made" (Moses 3:2–3). If the immortal and perfect Creator observed periodic rest, how much more do His mortal children need a renewing and sanctifying day set apart for Him. In Hebrew, the word is *shabbāth* — "rest."

From Adam until the Resurrection, the seventh day (Saturday) was the Sabbath. After Christ rose on the first day of the week, Sunday became the Lord's Day. Modern revelation confirms this pattern: "Thou shalt go to the house of prayer and offer up thy sacraments upon my holy day; for verily this is a day appointed unto you to rest from your labors, and to pay thy devotions unto the Most High" (D&C 59:9–10). The Sabbath is not merely rest from work. It is a covenant — a weekly declaration that God is Lord of our time.

*Drafting notes: Two paragraphs, ~200 words. Opens with the Creation anchor from the manuscript's first paragraph. Second paragraph condenses the Saturday-to-Sunday transition and D&C 59 block quote into narrative. Footnotes 469–471 converted to inline citations. Voice: first-person plural where needed ("His mortal children" rather than "you").*

#### Blesses Tab

`<h4>The Week That Begins with God</h4>`

For years I treated Sunday as the day I could not do things. No shopping, no entertainment, no work — a long list of restrictions. It felt like endurance, not worship. The shift came when I stopped asking "What can't I do?" and began asking "What does God want to give me today?"

The Sabbath, kept with intent, has become the hinge of my week. Everything before it leads toward it; everything after it flows from it. I study. I pray with less hurry. I sit with my family without a schedule pressing in. The Lord promised through Isaiah, "If thou turn away thy foot from the sabbath, from doing thy pleasure on my holy day; and call the sabbath a delight, the holy of the Lord, honourable … then shalt thou delight thyself in the Lord" (Isaiah 58:13–14). That promise is real. I have tasted it.

`<p class="bridge-text">Whether the Sabbath is already part of your rhythm or something entirely new, the commitment below invites you to set this day apart in a way that fits where you are.</p>`

*Drafting notes: ~200 words. Opens with honest personal witness about the restrictive mindset. Transition moment is a reframe question. Anchors in Isaiah 58:13–14 (from the manuscript). Bridge text is warm but does not assume the reader's current practice level.*

#### Commitments

| Tier | Text |
|------|------|
| covenant | I will set apart the full Sabbath this week — attending Church meetings, studying the gospel, and resting from worldly labors. |
| seeker | I will dedicate two hours this Sunday to worship, scripture study, or quiet reflection — and notice how it affects my week. |
| explore | I will set aside one block of time this weekend for rest and reflection, away from screens and routine demands. |

#### Reflection Prompt

*"What would change in your week if one day truly belonged to God?"*

*Drafting notes: Covenant commitment names the full Sabbath observance pattern. Seeker commitment asks for a meaningful but bounded time investment. Explore commitment is accessible to anyone — "rest and reflection" is the Sabbath principle in natural language. Reflection prompt is introspective and open-ended.*

---

## 6. Special Authoring Notes

### 6.1 Covenant Practices Group (Ch 21–25)

Group 5 card-chapters (Witnessing, Tithes & Offerings, Word of Wisdom, Congregational Service, Community Service) cover practices that are more distinctively Latter-day Saint. These chapters use broadly accessible introductions in their opening content. The three-tab card format naturally presents how Latter-day Saints specifically embrace these practices without requiring prior acceptance of distinctive theological claims.

Practically, this means the Practice tab's opening paragraph should ground the topic in broadly Christian or universal moral language before moving into specifically Latter-day Saint practice.

### 6.2 Ch 24 Split: Experience vs. Structure

Chapter 24 (Serving in Our Congregations) covers the experience of congregational participation: belonging, receiving callings, ministering, following prophets. Card 1 is titled "A Community of Saints" (not "Christ's Church Organization") to emphasize relational experience. The institutional and structural content (First Presidency, Quorums, stakes, wards, lay clergy) belongs in Chapter 32 (Part IV, standard prose).

### 6.3 Musical Testimony Scope

Each card-chapter receives one musical testimony that reflects upon the 3–5 main discipleship practices in the chapter. This is one song per card-chapter, not one song per card. The song should weave together the themes of the chapter's cards into a unified musical witness.

### 6.4 The "How This Chapter Works" Section

The three-column explainer section at the top of every card-chapter is hardcoded in the `card-chapter.njk` layout. It uses consistent icons and language across all card-chapters. This is intentional — it orients every reader the same way regardless of which chapter they enter first. Do not attempt to customize this per chapter.

---

## 7. Authoring Decisions Summary

These decisions are final and should be treated as constraints in all card-chapter production.

| Decision | Detail |
|----------|--------|
| Voice | Practice tab: "we" (solidarity). Commitment tab: "you" (personal invitation). |
| Scripture density | Heavier in Practice tabs, lighter in Blessings and Commitment tabs. |
| "How It Blesses" content | Scriptural promises anchored by brief personal witness from the authors. |
| Commitment tier language | Gospel-framed but natural language. Accessible without hiding the spiritual context. |
| Audio narration | Practice + Blessings tabs narrated. Commitment tab silent (reader's private space). |
| Batch size | All cards for one chapter at once. Complete units, no half-built chapters. |
| Covenant Practices framing | Group 5 card-chapters use broadly accessible introductions; LDS specificity in the card tabs. |
| Ch 24 split | Experience in Part II card-chapter. Institutional structure in Part IV prose (Ch 32). |
| Musical testimony | One song per card-chapter covering all cards, not one per card. |
| Slides path convention | `chapter-##/` folder naming (matching standard chapters). |
| Reflection prompts | Optional per card. Open-ended, introspective, non-binary. |
| Cards per chapter | 3–5, as specified in the master list. |

---

## 8. Recommended Build Order

After this guide is approved:

| Step | Chapter | Rationale |
|------|---------|-----------|
| 1 | Ch 10: Keeping the Sabbath (3 cards) | Smallest scope, single source, clean test of full pipeline |
| 2 | Ch 23: Keeping the Word of Wisdom (3 cards) | Second clean 3-card chapter, single source |
| 3 | Ch 13: Humility, Honor & Gratitude (3 cards) | Third 3-card chapter, builds confidence before dense chapters |
| 4 | Ch 8: Repentance & Discipleship (5 cards) | First dense chapter, multi-source (manuscript + VR) |
| 5 | Ch 17: Building Celestial Marriages (5 cards) | Dense chapter with sensitive content, tests full authoring range |

**Technical prerequisite:** Renumber deployed Ch 13 (Prayer & Repentance) to Ch 9 before building new card-chapters. This requires updating the `.njk` filename, frontmatter (chapter number, slug, chapterId, permalink), URL redirect from old path, and cross-references in any deployed chapters.

---

*— End of Authoring Guide —*
