---
name: publish-track
description: >
  End-to-end publication pipeline for Words of Plainness musical testimonies.
  Takes a raw Suno MP3 through mastering, ID3 tagging, three-tier archiving,
  ISRC catalog update, website deployment, and communications drafting.
  Use this skill whenever Aaron says "publish", "release", "deploy a track",
  "new song", "add testimony", "tag and archive", or any variation involving
  getting a WoP audio file from production into the world. Also triggers for
  "update catalog", "prep for DistroKid", "draft newsletter", or "draft Discord
  announcement" in a music publication context.
---

# Words of Plainness — Track Publication Skill

## Overview

This skill orchestrates the entire WoP publication pipeline from raw Suno MP3
to deployed website track and DistroKid-ready distribution file. It replaces
the previous standalone tools (wop_tag_automation.py, Mastering-to-Publication
Guide, Alternate Musical Testimony Guide, ministry-music-deployment-guide).

**Invoke via:** `/publish` from Claude Code terminal

## Before You Begin

1. Read `reference/naming-convention.md` for file naming rules
2. Read `reference/id3-defaults.md` for metadata constants
3. Read `reference/style-descriptors.md` for approved style vocabulary

These are short reference files — load them into context at skill start.

## Human Checkpoints

The pipeline pauses for human confirmation at these gates:

| Gate | What Aaron Does | Why |
|------|-----------------|-----|
| **G1** | Confirms track metadata after intake interview | Creative authority |
| **G2** | QA-listens to mastered file on headphones + speakers | Ears-on quality |
| **G3** | Reviews local site build (`npm run dev`) | Visual/audio verification |
| **G4** | Approves git commit & deploy | Deployment authority |
| **G5** | Reviews comms drafts before sending | Pastoral judgment |

Never skip a gate. Never auto-proceed past a gate without explicit confirmation.

---

## The 10-Step Pipeline

### Step 1: Intake & Interview

Receive the raw audio file path. Ask these questions based on a decision tree:

```
What type of track?
├── Chapter Testimony
│   ├── Chapter number? (01–62)
│   ├── Version? (1 = primary, 2+ = alternate)
│   └── Style descriptor? (see reference/style-descriptors.md)
├── Anthem (AN)
│   ├── Title?
│   └── Style descriptor?
├── Symphonic (SY)
│   ├── Title?
│   └── Style descriptor?
├── Ambient (AM)
│   ├── Title?
│   └── Style descriptor?
├── Special (SP)
│   ├── Title?
│   └── Style descriptor?
└── Overture (OV)
    ├── Title?
    └── Style descriptor?
```

Everything else comes from constants in `reference/id3-defaults.md`:
- Artist: "Words of Plainness"
- Album Artist: "Words of Plainness"
- Album: "Words of Plainness: Musical Testimonies"
- Composer: "Aaron J Powner"
- Copyright: "© 2026 Aaron J Powner"
- Genre: "Christian / Sacred"
- Year: 2026
- Comment: "A Christ-Centered Ministry — words-of-plainness.vercel.app"

**→ GATE G1: Present full metadata summary. Wait for Aaron's confirmation.**

### Step 2: Mastering via Masterchannel

Check for Masterchannel API credentials in environment:
- `MASTERCHANNEL_CLIENT_ID`
- `MASTERCHANNEL_CLIENT_SECRET`

**If credentials exist:** Run `scripts/masterchannel.py` to:
1. Authenticate → POST /token
2. Upload source file → POST /files
3. Create mastering job (engine=standard, genre=folk, loudness=-14 LUFS) → POST /jobs
4. Poll for completion or await webhook → GET /jobs/{id}
5. Download mastered WAV → GET /streams/{id}

**If no credentials (current default):** Tell Aaron:
> "Masterchannel API credentials not configured. Please master this track
> manually via masterchannel.ai and provide the mastered WAV path when ready."

Wait for mastered WAV path before proceeding.

**→ GATE G2: Aaron listens on headphones + speakers, confirms quality.**

### Step 3: File Naming & Three-Tier Archive

Read `reference/naming-convention.md` for the full convention.

Generate the canonical filename from intake metadata:
```
[PREFIX]_[VERSION]_[Title_With_Underscores]_[Style_Descriptor]
```

Create three tiers using ffmpeg:

```bash
# Tier 1: Archive Master (keep original mastered WAV resolution)
cp mastered.wav "WoP-Audio/01-Archive-Masters/${FILENAME}.wav"

# Tier 2: Distribution Master (16-bit 44.1kHz WAV for DistroKid)
ffmpeg -i mastered.wav -ar 44100 -sample_fmt s16 -c:a pcm_s16le \
  "WoP-Audio/02-Distribution-WAVs/${FILENAME}.wav"

# Tier 3: Web Master (320kbps MP3 for website)
ffmpeg -i mastered.wav -codec:a libmp3lame -b:a 320k \
  "WoP-Audio/03-Web-MP3s/${FILENAME}.mp3"
```

Report all three file paths and sizes to Aaron.

### Step 4: ID3 Tagging

Tag ALL THREE tiers immediately — this is the only moment when all files
exist and all metadata is known.

Run `scripts/tag_and_archive.py` with the metadata collected in Step 1.
The script uses mutagen to embed:
- ID3v2.4 tags (title, artist, album artist, album, genre, composer,
  copyright, track number, year, comment)
- ISRC code (left blank placeholder — populated after DistroKid assigns one)
- Album art (if configured via `--art` flag; 3000×3000 JPEG recommended)

The script tags MP3 and WAV files identically for catalog consistency.

### Step 5: DistroKid Preparation

Copy the tagged distribution WAV to the DistroKid submission folder.

Generate a plain-text cheat sheet from `templates/distrokid-cheatsheet.md`
filled with this track's specific metadata. Output to clipboard or file
for Aaron to reference during manual DistroKid upload.

Key fields for the cheat sheet:
- Song title (exact)
- Artist name: "Words of Plainness"
- Album name (or "single" if standalone)
- Genre tags
- Lyrics (if available)
- Release date (Aaron chooses)
- Leave a Legacy: Yes ($29/single, $49/album)
- YouTube Content ID: Enable
- Shazam: Enable

### Step 6: Website MP3 Deployment

Copy the tagged 320kbps MP3 to the local repo at:
```
src/assets/audio/${FILENAME}.mp3
```

### Step 7: Website Configuration

Configuration depends on track type:

**Chapter testimony — primary (version 1):**
```yaml
# In src/chapters/[##]-[slug].md front matter:
audio:
  testimony:
    file: "${FILENAME}.mp3"
    title: "${SONG_TITLE}"
    description: "${DESCRIPTION}"
```

**Chapter testimony — alternate (version 2+):**
```yaml
# Append to audio.testimony.alternates array:
alternates:
  - file: "${FILENAME}.mp3"
    label: "${STYLE_DESCRIPTOR}"
```

**Ministry anthem or symphonic:**
```json
// Add to src/_data/ministryMusic.json → collection array:
{
  "file": "${FILENAME}.mp3",
  "title": "${SONG_TITLE}",
  "label": "${TRACK_TYPE_LABEL}",
  "description": "${DESCRIPTION}",
  "duration": "", // measure via ffprobe
  "hasLyrics": true/false
}
```

**Ambient track:**
```json
// Add to src/_data/ministryMusic.json → ambient array:
{
  "file": "${FILENAME}.mp3",
  "title": "${SONG_TITLE}",
  "duration": "" // measure via ffprobe
}
```

After configuration, measure duration via ffprobe and populate:
```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 src/assets/audio/${FILENAME}.mp3
```
Convert seconds to M:SS format.

Run `npm run dev` and report the local URL.

**→ GATE G3: Aaron reviews the local build. Confirms track plays, shows
correctly in playlist, lyrics display (if applicable).**

### Step 8: Git Commit & Deploy

After G3 confirmation:

```bash
git add .
git commit -m "feat: ${COMMIT_TYPE} — ${SONG_TITLE} (${STYLE_DESCRIPTOR})

${COMMIT_BODY}"
git push origin main
vercel --prod
```

Commit types:
- `new chapter testimony` — primary chapter song
- `alternate arrangement` — chapter alternate
- `ministry anthem` — anthem/symphonic addition
- `ambient track` — ambient/instrumental addition

**→ GATE G4: Aaron confirms deploy looks good on production.**

### Step 9: Catalog Update & QA Report

Run `scripts/catalog_update.py` to:
1. Add or update the track's row in WoP_ISRC_Catalog.xlsx
2. Mark pipeline checkboxes: Album Art, Archive WAV, Distro WAV, Web MP3,
   Website Live
3. Leave ISRC and DistroKid columns empty (filled after manual upload)

Generate a structured QA report:
```
═══════════════════════════════════════════
  PUBLICATION REPORT — ${SONG_TITLE}
═══════════════════════════════════════════
  Track:     ${FILENAME}
  Type:      ${TRACK_TYPE}
  Style:     ${STYLE_DESCRIPTOR}
  
  Archive:   ✓ WoP-Audio/01-Archive-Masters/${FILENAME}.wav
  DistroKid: ✓ WoP-Audio/02-Distribution-WAVs/${FILENAME}.wav
  Website:   ✓ src/assets/audio/${FILENAME}.mp3
  Catalog:   ✓ Row ${ROW} updated
  
  Live URL:  https://words-of-plainness.vercel.app/music/
  Verify:    ${CHAPTER_URL_IF_APPLICABLE}
  
  TODO:
  - [ ] DistroKid upload (use cheat sheet)
  - [ ] Add ISRC to catalog after DistroKid assigns
  - [ ] Pre-save campaign link
═══════════════════════════════════════════
```

### Step 10: Communications Drafts

**→ GATE G5: Ask Aaron if he wants newsletter/Discord drafts.**

If yes, generate from templates:
- `templates/newsletter.md` → Email newsletter segment
- `templates/discord.md` → Discord announcement post

Fill templates with track-specific details. Present for Aaron's review.
These are drafts — Aaron sends them with pastoral judgment about timing
and audience.

---

## Partial Runs

The skill supports partial invocation for specific pipeline stages:

| Command | Steps Executed |
|---------|---------------|
| `/publish` | Full pipeline (Steps 1–10) |
| `/publish tag` | Steps 1, 3, 4 only (name + tag + archive) |
| `/publish deploy` | Steps 6–8 only (website deploy, assumes tagged MP3 ready) |
| `/publish catalog` | Step 9 only (update spreadsheet) |
| `/publish comms` | Step 10 only (generate comms from existing track data) |
| `/publish cheatsheet` | Step 5 only (DistroKid cheat sheet) |

---

## Dependencies

Required Python packages (install if missing):
```bash
pip install mutagen openpyxl Pillow
```

Required system tools:
```bash
ffmpeg ffprobe  # Audio conversion and measurement
lame            # MP3 encoding fallback
```

Required Node.js (for website build):
```bash
npm run dev     # Eleventy local dev server
vercel --prod   # Production deployment
```

---

## File Map

```
.claude/skills/publish-track/
├── SKILL.md                          ← You are here
├── scripts/
│   ├── tag_and_archive.py            ← ID3 tagging + three-tier file creation
│   ├── catalog_update.py             ← ISRC spreadsheet read/write
│   └── masterchannel.py              ← Masterchannel API integration (scaffold)
├── templates/
│   ├── newsletter.md                 ← Email newsletter template
│   ├── discord.md                    ← Discord announcement template
│   └── distrokid-cheatsheet.md       ← Manual upload reference
└── reference/
    ├── naming-convention.md          ← File naming rules + prefix codes
    ├── style-descriptors.md          ← Approved style vocabulary
    └── id3-defaults.md               ← Metadata constants
```
