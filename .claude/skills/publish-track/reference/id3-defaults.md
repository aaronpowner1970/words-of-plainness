# WoP ID3 Metadata Defaults

These constants apply to every Words of Plainness track unless explicitly
overridden during the intake interview.

## Required Tags

| ID3 Field | Default Value | Notes |
|-----------|--------------|-------|
| **Title** | *(from intake)* | Song title exactly as displayed |
| **Artist** | `Words of Plainness` | Consistent across all tracks |
| **Album Artist** | `Words of Plainness` | TPE2 tag — groups catalog |
| **Album** | `Words of Plainness: Musical Testimonies` | Or specific EP name for phased releases |
| **Track Number** | *(from catalog position)* | Position within release |
| **Year** | `2026` | Update annually |
| **Genre** | `Christian / Sacred` | Primary genre for consistency |
| **Composer** | `Aaron J Powner` | Lyricist / Creative Director |
| **Copyright** | `© 2026 Aaron J Powner` | Update year as needed |
| **Comment** | `A Christ-Centered Ministry — words-of-plainness.vercel.app` | Ministry URL in every file |

## Custom Tags

| Tag | Frame | Value | Notes |
|-----|-------|-------|-------|
| ISRC | `TXXX:ISRC` | *(assigned by DistroKid)* | Leave blank until assigned, then backfill |

## Album Art

- **Size:** 3000×3000px minimum (Spotify recommendation)
- **Format:** JPEG or PNG, RGB color space
- **ID3 Frame:** APIC, type=3 (Cover front)
- **Embed in:** All three tiers (archive, distro, web)

## ID3 Version

Use **ID3v2.4** (UTF-8 encoding, `encoding=3` in mutagen) for all files.
This ensures maximum compatibility with modern players and streaming platforms.

## Credits Convention

For DistroKid "credits" or liner notes fields:

```
Produced and written by Aaron Powner
Creative Direction: Words of Plainness Ministry
Music production assisted by AI tools under human creative direction
```

## Tag Mapping to mutagen Frames

| Field | mutagen Frame | Example |
|-------|--------------|---------|
| Title | `TIT2` | `TIT2(encoding=3, text="When God Becomes Real")` |
| Artist | `TPE1` | `TPE1(encoding=3, text="Words of Plainness")` |
| Album Artist | `TPE2` | `TPE2(encoding=3, text="Words of Plainness")` |
| Album | `TALB` | `TALB(encoding=3, text="Words of Plainness: Musical Testimonies")` |
| Genre | `TCON` | `TCON(encoding=3, text="Christian / Sacred")` |
| Composer | `TCOM` | `TCOM(encoding=3, text="Aaron J Powner")` |
| Copyright | `TCOP` | `TCOP(encoding=3, text="© 2026 Aaron J Powner")` |
| Track # | `TRCK` | `TRCK(encoding=3, text="1")` |
| Year | `TDRC` | `TDRC(encoding=3, text="2026")` |
| Comment | `COMM` | `COMM(encoding=3, lang="eng", desc="", text="...")` |
| ISRC | `TXXX` | `TXXX(encoding=3, desc="ISRC", text="USXX12600001")` |
| Cover Art | `APIC` | `APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=bytes)` |
