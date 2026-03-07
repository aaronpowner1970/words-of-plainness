# WoP File Naming Convention

## Structure

```
[PREFIX]_[TRACK]_[Title_With_Underscores]_[Style_Descriptor].[ext]
```

## Prefix Codes

| Prefix | Track Type | Example |
|--------|-----------|---------|
| `##` | Chapter testimony (01–62+) | `04_1_When_God_Becomes_Real.mp3` |
| `AN` | Anthem / Homepage hymn | `AN_1_Calling_the_Straying_Stranger_Home.mp3` |
| `SY` | Symphonic / Orchestral | `SY_1_Seek_and_You_Will_Find_Choral.mp3` |
| `AM` | Ambient / Instrumental | `AM_1_Veil_Meditation.mp3` |
| `SP` | Special / Collaboration | `SP_1_Ministry_Invitation.mp3` |
| `OV` | Overture / Interlude | `OV_1_Pilgrims_Prelude.mp3` |

## Track Number

The digit after the prefix underscore = version within that track group.

- **Version 1** = primary arrangement (always)
- **Version 2+** = alternate arrangements (genre variations, vocal treatments)

For chapter testimonies, zero-pad the chapter prefix to two digits: `01`, `02`, … `62`.

## Title

- Title_Case with underscores replacing spaces
- Keep titles consistent across all versions of the same song
- Omit articles only if title is excessively long

## Style Descriptor

A concise genre/style tag after the title. See `style-descriptors.md` for the
approved vocabulary. Helps identify the arrangement at a glance.

The primary version (version 1) MAY omit the style descriptor if the style
is captured in ID3 metadata. Alternates SHOULD always include descriptors.

## File Extensions

| Context | Format | Spec |
|---------|--------|------|
| Website deployment | `.mp3` | 320kbps, encoded from mastered WAV |
| DistroKid upload | `.wav` | 16-bit/44.1kHz minimum; 24-bit preferred |
| Archive master | `.wav` | Highest resolution from Masterchannel (typically 48kHz/24-bit) |

## Three-Tier Folder Structure

```
WoP-Audio/
├── 01-Archive-Masters/        ← Highest-res WAVs from Masterchannel
├── 02-Distribution-WAVs/      ← DistroKid-ready WAVs (16/44.1 or 24/44.1)
├── 03-Web-MP3s/               ← 320kbps MP3s for website
├── 04-Pre-Master-Sources/     ← Original Suno outputs + Audacity projects
└── 05-Metadata-Catalog/       ← ISRC spreadsheet, ID3 tag templates
```

## Complete Examples

| Filename | Description |
|----------|-------------|
| `01_1_Introduction_to_Plainness_Sacred_Americana.mp3` | Ch 1, Primary |
| `01_2_Introduction_to_Plainness_Cinematic_Inspirational.mp3` | Ch 1, Alt 1 |
| `01_3_Introduction_to_Plainness_Americana_Folk_Female_Vocal.mp3` | Ch 1, Alt 2 |
| `04_1_When_God_Becomes_Real.mp3` | Ch 4, Primary (style in metadata) |
| `04_3_When_God_Becomes_Real_Soul_Worship.mp3` | Ch 4, Alt 2 |
| `AN_1_Calling_the_Straying_Stranger_Home_Duet.mp3` | Anthem, Primary |
| `AN_2_Calling_the_Straying_Stranger_Home_Solo_Baritone.mp3` | Anthem, Alt |
| `SY_1_Seek_and_You_Will_Find_Choral_Anthem.mp3` | Symphonic |
| `AM_1_Veil_Meditation_Instrumental.mp3` | Ambient |
| `OV_1_Pilgrims_Prelude_Orchestral.mp3` | Overture |
| `SP_1_Come_Thou_Fount_Sacred_Harp.mp3` | Special |

## Rules

- **No spaces** in filenames — always underscores
- **Case-sensitive** — YAML front matter `file:` must exactly match filename on disk
- **Consistent titles** across all versions of the same song
- Chapter prefixes are always **two digits** (zero-padded)
- Non-chapter prefixes are always **two uppercase letters**
