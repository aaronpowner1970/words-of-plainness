# Deploying Ministry Anthems + Ambient Reading Player

## Overview

Two features in a single deployment:

**Feature 1 — Music Page: Ministry Anthems**
Add "The Marks of Your Worth" and the Mini Symphony to the Music page playlist as a new section that plays before the chapter journey.

**Feature 2 — Chapter Pages: Ambient Reading Player**
Add a "Reading Atmosphere" control between "Listen to Chapter" and "Learning Tools" on every chapter page. Auto-shuffles through all ambient tracks. Persists across chapter navigation via localStorage.

---

## Audio Files (already in local repo)

| File | Location | Status |
|------|----------|--------|
| `the-marks-of-your-worth.mp3` | `src/assets/audio/` | Already deployed (homepage player) |
| `words-of-plainness-mini-symphony-01.mp3` | `src/assets/audio/` | In local repo, needs deployment |
| `ambient-music-01.mp3` | `src/assets/audio/` | In local repo, needs deployment |

No renaming needed. All filenames are final.

---

## Step 1: Create the Ministry Music Data File

**Create file:** `src/_data/ministryMusic.json`

```json
{
  "collection": [
    {
      "file": "the-marks-of-your-worth.mp3",
      "title": "The Marks of Your Worth",
      "label": "Ministry Anthem",
      "description": "The covenant dialogue at the heart of this ministry — Christ declares your worth through the marks He still bears.",
      "duration": "",
      "hasLyrics": true
    },
    {
      "file": "words-of-plainness-mini-symphony-01.mp3",
      "title": "Words of Plainness",
      "label": "Mini Symphony",
      "description": "An instrumental journey through the themes of the ministry.",
      "duration": "",
      "hasLyrics": false
    }
  ],
  "ambient": [
    {
      "file": "ambient-music-01.mp3",
      "title": "Reading Atmosphere",
      "duration": ""
    }
  ],
  "anthemLyrics": ""
}
```

**Notes:**
- `duration` fields: leave blank now, Claude Code will measure via ffprobe in Step 5.
- `anthemLyrics`: will be populated in Step 4 by extracting from the homepage player.
- `ambient` is an array — future tracks (ambient-music-02.mp3, etc.) just get appended here. The chapter player auto-discovers all entries.

---

## Step 2: Music Page — Add Ministry Anthems

### Claude Code Prompt

```
Update src/pages/music.njk to add a "Ministry Anthems" section before the
existing chapter-based playlist sections. Data comes from the global data file
at src/_data/ministryMusic.json.

PLAYLIST CHANGES:

1. The playlist flat array currently has two passes (primaries, then alternates).
   Add a new first pass that prepends ministryMusic.collection items. Each entry
   produces a track object matching the same shape as chapter tracks:
   - title: item.title
   - label: item.label
   - file: "/assets/audio/" + item.file
   - chapter: null (not chapter songs)
   - chapterNum: 0 (sort before chapter 1)
   - description: item.description
   - duration: item.duration || "—"
   - hasLyrics: item.hasLyrics
   - lyrics: if hasLyrics, use ministryMusic.anthemLyrics; otherwise null
   - isMinistry: true (new flag for template/JS identification)

2. Playlist order becomes:
   Section 0: Ministry Anthems (from ministryMusic.collection, in array order)
   Section 1: Core Discipleship Journey (chapter primaries, unchanged)
   Section 2: Alternate Arrangements (chapter alternates, unchanged)

TRACK LIST DISPLAY:

3. Add a new section header BEFORE "Core Discipleship Journey" header:
   - Header text: "Ministry Anthems"
   - Same styling as existing section headers

4. Ministry track rows:
   - Title and label: "The Marks of Your Worth — Ministry Anthem"
   - No chapter link (chapter is null)
   - Duration from data attribute
   - Download button (same as chapter tracks)

LYRICS PANEL:

5. Ministry track with hasLyrics=true: display lyrics in the lyrics panel
   using the same rendering as chapter lyrics. Source: track's lyrics property.

6. Ministry track with hasLyrics=false (the Symphony): show
   "♪ Instrumental" in italics, centered, in the lyrics panel.

SHUFFLE:

7. Ministry Anthems tracks participate fully in shuffle. When shuffle is
   active, they mix with chapter tracks. When shuffle is off, they play
   first (before chapter primaries).

AMBIENT TRACKS DO NOT APPEAR ON THE MUSIC PAGE AT ALL.
The ambient array in ministryMusic.json is consumed only by the chapter
page ambient player (separate feature). Music page ignores it entirely.

NO CHANGES to:
- Sticky player bar controls, progress bar, repeat mode behavior
- Chapter markdown files
- Homepage anthem player
- music-player.js shuffle/repeat/auto-advance logic (other than recognizing
  the new isMinistry flag and handling null chapter values gracefully)
```

---

## Step 3: Chapter Pages — Ambient Reading Player

### Claude Code Prompt

```
Add an ambient "Reading Atmosphere" player to the chapter page layout. This
is a new feature that lets readers play shuffled background music while
reading chapter content.

DATA SOURCE:
The ambient track list comes from src/_data/ministryMusic.json, specifically
the "ambient" array. Each entry has: file, title, duration. The chapter
template should read this data and inject it as a JSON array for the JS.

PLACEMENT — DESKTOP:
Insert the Reading Atmosphere control BETWEEN the existing "Listen to Chapter"
button/player and the "Learning Tools" accordion. It should feel like a
sibling control in the same toolbar area — same visual weight and alignment.

The control has two states:

COLLAPSED STATE (default):
- A single row showing: ♪ icon + "Reading Atmosphere" label + on/off toggle
- Matches the visual style of "Listen to Chapter" and "Learning Tools"
  (same font, padding, border treatment)
- Toggle is OFF by default (unless localStorage says it was playing)

EXPANDED/ACTIVE STATE (when toggled on):
- Music starts playing immediately
- The row updates to show: ♪ icon + track title + skip-next button (⏭) +
  on/off toggle
- Subtle "playing" indicator (animated bars or pulsing dot)
- Optional small volume slider (secondary, can be hidden behind a tap)

PLACEMENT — MOBILE:
Add "🎵 Reading Atmosphere" as a new row inside the Learning Tools expanded
panel, with the same on/off toggle and skip-next button. When activated, it
plays just like desktop. The collapsed Learning Tools button text does NOT
change — the ambient player is discovered when the panel opens.

AUDIO BEHAVIOR:

1. SHUFFLE: On activation, shuffle the entire ambient array (Fisher-Yates)
   and begin playing from the first track. When a track ends, auto-advance
   to the next. When the shuffled playlist is exhausted, reshuffle and
   continue. This creates an infinite ambient loop.

2. SKIP-NEXT: The ⏭ button advances to the next track in the shuffled order.
   With only one track (ambient-music-01.mp3), skip restarts the same track.
   When more tracks exist, it moves to the next.

3. NARRATION AUTO-PAUSE: Listen for the chapter's Read Aloud audio element.
   When narration starts playing (the 'play' event on the narration <audio>),
   auto-pause the ambient player and store its position. When narration
   pauses or ends, auto-resume ambient from where it left off. This gives
   narration clean priority without the reader needing to manage two players.

   Implementation: the ambient JS should find the narration audio element
   (look for the existing audio element used by audio-sync.js / Read Aloud)
   and attach play/pause/ended event listeners.

4. TESTIMONY/OVERVIEW INTERACTION: Same auto-pause behavior if the reader
   plays the testimony or overview audio from Learning Tools. Any chapter
   audio source pauses ambient; ambient resumes when chapter audio stops.

PERSISTENCE (localStorage):

5. Store these values in localStorage:
   - wop_ambient_playing: boolean (is ambient currently active?)
   - wop_ambient_volume: number (0-1, default 0.3)
   Do NOT store track position or current track index — ambient is background
   texture, not a linear listening experience. On page load, if
   wop_ambient_playing is true, auto-start a fresh shuffle.

6. CROSS-CHAPTER PERSISTENCE: When the reader navigates to the next chapter
   (full page reload), the new page checks localStorage on load. If
   wop_ambient_playing is true, the ambient player auto-activates and begins
   playing (fresh shuffle). The brief silence during page navigation is
   natural — like turning a page. No attempt to resume mid-track.

VOLUME:

7. Default volume: 0.3 (30%). This is background music for reading — it
   should sit well below spoken narration volume. Volume preference persists
   in localStorage.

STYLING:

8. The ambient control should feel like a natural part of the chapter's
   existing control toolbar — not a separate feature bolted on. Match:
   - Font family, size, color of existing "Listen to Chapter" and
     "Learning Tools" elements
   - Border/background treatment (transparent bg, subtle border like
     learning-tools-toggle)
   - Hover states consistent with existing controls
   - The "playing" state should have a subtle warm accent (gold/amber from
     the site's palette) to indicate active without being distracting

9. The ambient player must not affect the layout of the chapter prose below
   it. It occupies the same vertical space as one control row. No content
   shift when toggling on/off.

FILES TO CREATE/MODIFY:

- NEW: src/js/ambient-player.js — all ambient player logic (shuffle,
  playback, auto-pause coordination, localStorage persistence)
- NEW: src/css/ambient-player.css — ambient control styling
- MODIFY: src/_includes/layouts/chapter.njk — insert ambient control HTML
  between Listen to Chapter and Learning Tools, load CSS/JS, inject ambient
  track data as window.WOP_AMBIENT_TRACKS
- MODIFY: src/_includes/layouts/base.njk — add ambient-player.css link
  (after chapter.css or in the head), add ambient-player.js script
  (after chapter.js)

Do NOT modify:
- Any chapter markdown files
- The Music page (music.njk, music-player.js, music.css)
- The homepage anthem player
- The existing audio-sync.js or chapter.js (ambient-player.js coordinates
  with them via event listeners on shared audio elements, not by modifying
  their code)
```

---

## Step 4: Populate Anthem Lyrics

### Claude Code Prompt

```
The anthem lyrics for "The Marks of Your Worth" are already in the homepage
player (src/index.njk, inside the anthem block's lyrics container).

Extract the lyrics HTML from the anthem player and copy it into the
"anthemLyrics" field of src/_data/ministryMusic.json.

Adapt the format to match the chapter lyrics pattern:
- <p class="section"><strong>[Section Name]</strong></p> for headers
- <p class="verse">Line 1<br>Line 2<br>Line 3</p> for stanzas

If the homepage lyrics use a different HTML structure, adapt them to match
so the Music page lyrics panel renders them consistently.

Properly escape the HTML for JSON (double quotes as \", newlines as \n).
```

---

## Step 5: Measure Durations

### Claude Code Prompt

```
Measure the duration of these audio files in src/assets/audio/:
- the-marks-of-your-worth.mp3
- words-of-plainness-mini-symphony-01.mp3
- ambient-music-01.mp3

Use ffprobe:
  ffprobe -v error -show_entries format=duration -of csv=p=0 [filename]

Convert seconds to M:SS format. Update the duration fields in
src/_data/ministryMusic.json for all three entries (both collection
items and the ambient item).
```

---

## Step 6: Test Locally

```bash
npm run dev
```

### Music Page Checklist
- [ ] "Ministry Anthems" section appears first in track list
- [ ] "The Marks of Your Worth" is track #1
- [ ] "Words of Plainness — Mini Symphony" is track #2
- [ ] Anthem shows lyrics in lyrics panel
- [ ] Symphony shows "♪ Instrumental" in lyrics panel
- [ ] Chapter tracks follow in existing order
- [ ] Shuffle mixes ministry tracks with chapter tracks
- [ ] No ambient tracks appear on Music page

### Chapter Page Checklist (test on Ch1 and Ch6)
- [ ] "Reading Atmosphere" control appears between Listen to Chapter and Learning Tools
- [ ] Toggle ON starts ambient playback at 30% volume
- [ ] Toggle OFF pauses ambient playback
- [ ] Skip-next button works (restarts track with only one ambient file)
- [ ] Playing state shows visual indicator (animated bars or pulsing dot)
- [ ] Starting Read Aloud auto-pauses ambient
- [ ] Stopping/pausing Read Aloud auto-resumes ambient
- [ ] Playing Testimony from Learning Tools auto-pauses ambient
- [ ] Playing Overview from Learning Tools auto-pauses ambient
- [ ] Navigate to next chapter: ambient auto-starts on new page if it was playing
- [ ] Navigate to next chapter: ambient stays off if it was off
- [ ] Volume preference persists across chapters
- [ ] Mobile: ambient control appears inside Learning Tools expanded panel
- [ ] Mobile: same play/pause/skip/auto-pause behavior as desktop
- [ ] No layout shift when toggling ambient on/off
- [ ] No JavaScript console errors

---

## Step 7: Commit & Deploy

### Claude Code Prompt

```
Stage and commit all changes for the Ministry Anthems + Ambient Reader:

New files:
- src/_data/ministryMusic.json
- src/js/ambient-player.js
- src/css/ambient-player.css
- src/assets/audio/words-of-plainness-mini-symphony-01.mp3
- src/assets/audio/ambient-music-01.mp3

Modified files:
- src/pages/music.njk (Ministry Anthems section)
- src/js/music-player.js (if changes needed for isMinistry flag)
- src/css/music.css (if new styles for Ministry Anthems)
- src/_includes/layouts/chapter.njk (ambient control HTML + data injection)
- src/_includes/layouts/base.njk (ambient CSS/JS links)

Commit message:
"feat: Ministry Anthems on Music page + ambient reading player on chapters

Music page:
- New ministryMusic.json data file for non-chapter audio
- Ministry Anthems (anthem + symphony) plays before chapter journey
- Anthem lyrics in lyrics panel, symphony shows instrumental indicator

Chapter pages:
- Reading Atmosphere ambient player between Listen and Learning Tools
- Auto-shuffle through ambient tracks with skip-next
- Narration/testimony/overview auto-pauses ambient
- localStorage persistence across chapter navigation
- Mobile: ambient control inside Learning Tools panel"

Push to main and deploy.
```

---

## Step 8: Post-Deploy Verification

1. Hard refresh Music page (`Ctrl+Shift+R`)
2. Verify anthem plays first and shows lyrics
3. Verify shuffle includes ministry tracks
4. Navigate to any chapter page
5. Toggle Reading Atmosphere on — confirm playback starts
6. Start Read Aloud — confirm ambient auto-pauses
7. Stop Read Aloud — confirm ambient auto-resumes
8. Click Next Chapter — confirm ambient restarts on new page
9. Verify homepage anthem player still works independently

---

## Architecture Summary

```
MUSIC PAGE PLAYLIST:
  [Anthem, Symphony] → [Ch1...Ch6 primaries] → [Ch1...Ch6 alternates]
  Data: ministryMusic.json (collection) + collections.chapters YAML
  Ambient tracks: NOT included

CHAPTER PAGES:
  Ambient player between "Listen to Chapter" and "Learning Tools"
  Data: ministryMusic.json (ambient array) → window.WOP_AMBIENT_TRACKS
  Behavior: auto-shuffle, loop forever, auto-pause for narration
  Persistence: localStorage (wop_ambient_playing, wop_ambient_volume)

HOMEPAGE:
  Anthem player: unchanged, independent
```

## Future-Proofing

- **New ministry songs:** Add entries to `ministryMusic.json` → `collection` array. Music page auto-updates.
- **New ambient tracks:** Add entries to `ministryMusic.json` → `ambient` array. Drop MP3 in `src/assets/audio/`. Chapter player auto-discovers and shuffles them in. No template changes.
- **Chapter-specific ambient:** If you ever want certain chapters to use specific ambient tracks, add an `ambientOverride` field to chapter front matter that filters the ambient array. Not needed now but the architecture supports it.
