"""
convert-to-sentence-timestamps.py  (WoP canonical rebuild — March 2026)

Reconstructed from the original elevenlabs-scripts pipeline.

HOW IT WORKS
============
1. Read per-chunk character-level alignment JSON files (from ElevenLabs
   with-timestamps API) from the alignment/ directory.

2. Measure the ASSEMBLED normalized MP3 duration using ffprobe.
   Also measure each CHUNK's pre-normalized duration using ffprobe.

3. Calculate each chunk's proportional share of the assembled file:
     chunk_share = chunk_pre_duration / sum_of_all_pre_durations
     chunk_actual_start = cumulative share of assembled duration

   This corrects for loudnorm re-encoding drift that accumulates when
   using raw pre-normalized chunk durations as offsets.

4. For each character in each chunk, calculate its global time:
     global_time = chunk_actual_start + (char_start_in_chunk / chunk_pre_duration) * chunk_actual_duration

5. Extract sentence start times by matching the first character of each
   sentence's text against the global character timeline.

6. For paragraph-level sync: output one timestamp per paragraph (the
   timestamp of each paragraph's first sentence's first character).

7. Write the final JSON in the mixed-key format that audio-sync.js expects:
     "p{N}"   -> paragraph start time (seconds)
     "s{N}"   -> paragraph index for sentence N (click-to-seek map)
     "cue{N}" -> cue trigger time (seconds)

OUTPUT
======
  src/_data/timestamps/chapter-09-yehoshua-the-man.json

USAGE
=====
  python tools/convert-to-sentence-timestamps.py

This script is self-contained and idempotent. Run it any time the
assembled MP3 or alignment data changes.

FFMPEG ASSEMBLY (canonical two-pass pipeline)
=============================================
ALWAYS use the two-pass approach for final MP3 assembly. Single-pass
concatenation produces Duration: N/A in the output header, which means
no Xing/Info seek table is written, which means browser seeking lands
in the wrong position. Two-pass fixes this:

  Pass 1 — decode to WAV (known duration, loudnorm applied):
    ffmpeg -y -f concat -safe 0 -i concat_new.txt \
      -af loudnorm=I=-16:TP=-1.5:LRA=11 intermediate.wav

  Pass 2 — encode to MP3 (duration known, Xing header written correctly):
    ffmpeg -y -i intermediate.wav \
      -codec:a libmp3lame -qscale:a 2 -id3v2_version 3 \
      NR_##_##_Title.mp3

  Cleanup:
    del intermediate.wav

Verify with ffprobe that start_time is near 0.000 (not negative)
and duration matches expected length before uploading to R2.
"""

import re
import json
import subprocess
import os

# ── Config ────────────────────────────────────────────────────────────────

CHUNKS_DIR     = r"C:\Users\aaron\Documents\working-folder\ch09-chunks"
ALIGNMENT_DIR  = os.path.join(CHUNKS_DIR, "alignment")
ASSEMBLED_MP3  = os.path.join(CHUNKS_DIR, "NR_09_01_Yehoshua_the_Man.mp3")
CHAPTER_PATH   = r"C:\Users\aaron\Documents\words-of-plainness\src\chapters\09-yehoshua-the-man.md"
OUTPUT_PATH    = r"C:\Users\aaron\Documents\words-of-plainness\src\_data\timestamps\chapter-09-yehoshua-the-man.json"

# Chunk manifest: (chunk_id, first_sentence, last_sentence, is_cue, cue_index)
CHUNKS = [
    ("01",  0,    27,   False, None),
    ("02",  28,   61,   False, None),
    ("03",  62,   85,   False, None),
    ("04",  None, None, True,  385),
    ("05",  86,   111,  False, None),
    ("06",  112,  150,  False, None),
    ("07",  None, None, True,  386),
    ("08",  151,  175,  False, None),
    ("09",  176,  199,  False, None),
    ("10",  None, None, True,  387),
    ("11",  200,  235,  False, None),
    ("12",  236,  277,  False, None),
    ("13",  278,  300,  False, None),
    ("14",  301,  330,  False, None),
    ("15",  331,  342,  False, None),
    ("16",  343,  384,  False, None),
    ("17",  None, None, True,  388),
]

# Paragraph map: paragraph_index -> first_sentence_index
PARAGRAPH_MAP = {
     0:   0,   1:   1,   2:   4,   3:  10,   4:  15,
     5:  23,   6:  30,   7:  33,   8:  36,   9:  38,
    10:  39,  11:  44,  12:  50,  13:  52,  14:  58,
    15:  59,  16:  60,  17:  62,  18:  63,  19:  66,
    20:  73,  21:  75,  22:  77,  23:  80,  24:  86,
    25:  87,  26:  90,  27:  94,  28:  99,  29: 103,
    30: 112,  31: 117,  32: 123,  33: 131,  34: 135,
    35: 137,  36: 138,  37: 140,  38: 141,  39: 144,
    40: 149,  41: 151,  42: 152,  43: 159,  44: 160,
    45: 163,  46: 166,  47: 168,  48: 169,  49: 170,
    50: 175,  51: 176,  52: 182,  53: 187,  54: 190,
    55: 195,  56: 200,  57: 201,  58: 214,  59: 222,
    60: 230,  61: 236,  62: 237,  63: 240,  64: 243,
    65: 246,  66: 247,  67: 250,  68: 254,  69: 255,
    70: 260,  71: 265,  72: 271,  73: 274,  74: 278,
    75: 279,  76: 281,  77: 285,  78: 288,  79: 291,
    80: 294,  81: 296,  82: 299,  83: 301,  84: 302,
    85: 303,  86: 312,  87: 313,  88: 319,  89: 325,
    90: 327,  91: 331,  92: 332,  93: 334,  94: 338,
    95: 340,  96: 343,  97: 344,  98: 350,  99: 352,
   100: 353, 101: 354, 102: 358, 103: 359, 104: 365,
   105: 366, 106: 369, 107: 370, 108: 372, 109: 373,
   110: 375, 111: 378, 112: 379, 113: 380, 114: 382,
   115: 384,
}

# ── Helpers ───────────────────────────────────────────────────────────────

def get_duration(path):
    """Return audio duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def words_of(text):
    return normalize_text(text).split()

# ── Step 1: Extract sentences from chapter markdown ───────────────────────

print("=== Step 1: Extracting sentences ===")
with open(CHAPTER_PATH, "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'\{%\s*sentence\s+(\d+)\s*%\}(.*?)\{%\s*endsentence\s*%\}'
sentences = {}
for idx_str, raw_text in re.findall(pattern, content, re.DOTALL):
    clean = re.sub(r'\{%.*?%\}', '', raw_text)
    clean = re.sub(r'\{\{.*?\}\}', '', clean)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'[\*_]', '', clean)
    sentences[int(idx_str)] = clean

print(f"  {len(sentences)} sentences extracted")

# ── Step 2: Measure durations ─────────────────────────────────────────────

print("\n=== Step 2: Measuring durations ===")

assembled_duration = get_duration(ASSEMBLED_MP3)
print(f"  Assembled MP3 duration: {assembled_duration:.3f}s")

chunk_pre_durations = []
for chunk_id, *_ in CHUNKS:
    path = os.path.join(CHUNKS_DIR, f"ch09_chunk_{chunk_id}.mp3")
    dur = get_duration(path)
    chunk_pre_durations.append(dur)

total_pre_duration = sum(chunk_pre_durations)
print(f"  Sum of pre-normalized chunk durations: {total_pre_duration:.3f}s")
print(f"  Normalization drift: {assembled_duration - total_pre_duration:+.3f}s")

# ── Step 3: Build global character timeline ───────────────────────────────
#
# Key insight: after loudnorm, each chunk's actual share of the assembled
# file is proportional to its pre-normalized duration. We scale accordingly.
#
# chunk_actual_start  = (sum of pre-durations before this chunk / total_pre_duration) * assembled_duration
# chunk_actual_dur    = (chunk_pre_duration / total_pre_duration) * assembled_duration
#
# Then for each character in a chunk:
# global_time = chunk_actual_start + (char_start_in_chunk / chunk_pre_duration) * chunk_actual_dur
#             = chunk_actual_start + (char_start_in_chunk / total_pre_duration) * assembled_duration
#
# This distributes the normalization drift proportionally across all chunks.

print("\n=== Step 3: Building global character timeline ===")

# Each entry: {"char": str, "global_time": float, "chunk_id": str}
global_chars = []

cumulative_pre = 0.0
for i, (chunk_id, first_sent, last_sent, is_cue, cue_idx) in enumerate(CHUNKS):
    pre_dur = chunk_pre_durations[i]

    # Scale factor: where does this chunk start in the assembled file?
    chunk_actual_start = (cumulative_pre / total_pre_duration) * assembled_duration
    chunk_actual_dur   = (pre_dur / total_pre_duration) * assembled_duration

    alignment_path = os.path.join(ALIGNMENT_DIR, f"chunk_{chunk_id}.json")
    with open(alignment_path, "r", encoding="utf-8") as f:
        alignment = json.load(f)

    chars  = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])

    for j, ch in enumerate(chars):
        char_start_in_chunk = starts[j] if j < len(starts) else 0.0
        # Scale this character's position into the assembled timeline
        global_time = chunk_actual_start + (char_start_in_chunk / pre_dur) * chunk_actual_dur
        global_chars.append({
            "char": ch,
            "global_time": round(global_time, 4),
            "chunk_id": chunk_id
        })

    cumulative_pre += pre_dur

print(f"  {len(global_chars)} characters in global timeline")
print(f"  First char: '{global_chars[0]['char']}' at {global_chars[0]['global_time']:.3f}s")
print(f"  Last char:  '{global_chars[-1]['char']}' at {global_chars[-1]['global_time']:.3f}s")

# Build a flat string and parallel time array for fast searching
global_text = "".join(c["char"] for c in global_chars)
global_times = [c["global_time"] for c in global_chars]

# ── Step 4: Align sentences to global character timeline ──────────────────
#
# CRITICAL: The global character timeline was built from the STRIPPED narration
# text — citations removed, Yehoshua pronounced as Yahoshua, etc. The chapter
# markdown sentence texts contain citations and use different spellings.
#
# Therefore we cannot match sentence text directly against the character
# timeline. Instead we use a STRUCTURAL approach:
#
# Each chunk covers a known range of sentences (first_sent to last_sent).
# Within a chunk, we know the character timeline is sequential and
# monotonically increasing. We find the first character of each sentence
# by tracking how many characters of narration text have been consumed
# up to that sentence boundary — using the NARRATION TEXT (stripped),
# not the markdown text.
#
# For each chunk we:
# 1. Take the narration text that was actually synthesized (CHUNK_TEXTS)
# 2. Locate sentence boundaries within that narration text by matching
#    the opening words of each sentence (after stripping citations)
# 3. Map those character positions to the chunk's character timeline
# 4. Apply the global offset to get absolute timestamps

print("\n=== Step 4: Aligning sentences to global timeline ===")

# Narration texts used for synthesis (citation-stripped, as sent to ElevenLabs)
# Keyed by chunk_id. These are the exact texts in the global character timeline.
CHUNK_TEXTS = {
    "01": """By the time the first sandals scuff dust into the air above ancient dirt roads, every household is already in motion, each person drawn forward by the same quiet force that still moves us today in our modern age of shoes and pavement: the need to eat, to provide, to compete, to endure another day. The dust and duty of life cannot be ignored. And it can become all-consuming if we allow it.

She did not think of herself as distracted. She thought of herself as responsible. The fire needed tending, the guests needed feeding, and no one else seemed to notice. She had no idea that one day the whole world would know her name. Martha, sister to Mary, both sisters of Lazarus of Bethany. Their home in Judea — conveniently near Jerusalem — was a favorite resting place for God who walked among humans.

Mary and Martha labored daily within this pressing reality of dust and duty, especially when He visited their home. They had heard the stories, considered the gospel message of the long awaited Messiah. They had prayed, experimented upon the word, embraced Him and His teachings, and bent their lives to His service. This is the question explored in chapter six: How would you know the truth of Him? If He were introduced to you as the Christ, how would you know it's true?

This chapter presents a very different question from chapter six. How would you know Him personally? Not just the truth of His identity. How would you relate to Him socially? How would your soul respond to His personality and bearing? Would you be in the right frame of mind to feel His spiritual presence? Ready to see Him for who He is, rather than who you might expect based on two thousand year old records, traditions, and creeds? Would you be comfortable in His presence, or would you feel awkward?

We know that children ran toward Him. Men untrained in theology responded instantly to His call. Crowds listening to Him forgot to eat. The powerful among Israel came to speak to Him in secret. Desperate souls pressed through walls of people and tore through rooftops to obtain His personal blessing. His enemies were confused by Him and often failed to execute their own orders. A tax collector climbed a tree just to catch a glimpse of Him.""",

    "02": """If He walked into a church meeting dressed as a parishioner, but by His will your eyes were kept from recognizing Him — like the disciples on the road to Emmaus — would we be too distracted by hymns, and prayers, and wiggling children, and the normal business and gossip of congregational life? Would we know Him? How would we know Him?

You have a Mary and Martha decision to make. You can be like Mary, recognizing the value of His character and kneeling at His feet to learn from Him. You can be like Martha, honorably busy serving the needs of others, but not recognizing the special moment for what it was.

This isn't to say that we stop tending to the mortal essentials, but that we must be ready whenever He calls to stop, listen, and obey. We must also learn to be in the firm habit of setting down our cares and concerns regularly to make moments for Him.

The prophet Joshua also presented to the world this same challenge: "Choose for yourselves this day whom you will serve."

This is not all — not for a disciple. This isn't a one-and-done choice. Choose today. And then tomorrow, choose again. If you ever fail to make the same choice, then get back up, shake the dust off of your sandals and make the choice once again to serve the Lord.

What would it be like for Yehoshua to enter a room today or walk into a busy marketplace? Would He be noticed, or would He blend in? What would it be like to be near Him as just another member of a community? What would His presence say of Him to any that took notice? His attitude, His posture, His behavior? Before He ever opened His mouth, what would you learn of Him?

The value of this chapter is in the sincere character study of Jesus Christ, the human personality of the Word Made Flesh. This topic is the centerpiece of our effort to respond to His command, "Learn of Me."

Let us feast upon the scriptures to learn of our God Made Flesh. Don't delegate this task to others — not even to preachers or teachers. It is as much your responsibility to learn of Jesus Christ as to personally confess Him as your Lord and Savior or to follow Him as an expression of your love for Him. Our purpose here is contemplative: sit with Yehoshua the Man, study Him honestly. Who is He? What kind of person is He?

This chapter asks: "What is He like — what manner of man is this?"

The portrait that follows is organized around a single claim: that grace and truth are the most defining character traits of the Son of God — and that every other attribute, action, and reaction of Yehoshua flows from this foundation.

His character is not the absence of human feeling but the perfection of it: every impulse governed by love, every response shaped by wisdom, every choice submitted to the Father. He is the mirror we hold up to see ourselves honestly.""",

    "03": """Yehoshua spent roughly thirty years doing manual labor and only three years in ministry. That ratio itself is a testament to His humility. God in the flesh chose to quietly shape wood and stone in the privacy of an insignificant village before He ever shaped souls and performed miracles publicly.

Shortly before His triumphant reception in the city, Yehoshua had left Galilee to walk the road to Jerusalem when a young man came running to meet Him along the way, falling to his knees before the Master. The young man said, "Good teacher, what must I do to inherit eternal life?" Of course, Yehoshua knew the answer better than anyone. He had taught the gospel of salvation in many forms to many people. Still, rather than answering directly, Yehoshua reacted with graceful humility. "Why do you call me good? No one is good — except God alone." He did then teach the answer, but first redirected glory to the Father.

From His early years, He could have enjoyed the same celebrity status that welcomed Him to Jerusalem on the day of His triumphal entry — when a vast throng of believers accepted Him as their Messiah and King of the Jews. Even on that glorious day, when all seemed to be going well, He rode into the adoring masses riding a humble donkey instead of a warhorse.

Paul taught us to emulate Yehoshua's humility in his letter to the people of Philippi. "In your relationships with one another, have the same mindset as Christ Jesus: Who, being in very nature God, did not consider equality with God something to be used to his own advantage; rather, he made himself nothing by taking the very nature of a servant, being made in human likeness."

Yehoshua's example is what grace looks like in the form of humility. He did not have to proclaim His mastery of humility. He lived it in His everyday relationships.

My mother used to remind me that one does not announce one's own humility. Throughout my life, I have never felt safer than when I am with genuinely humble people. Sensing no competition, no threat, it allows me to let down my guard. Humility in others allows us to see deeper than the facade of ego to real depth of character. This is what it must have felt like to be near Yehoshua. To some it may have been frightening or suspicious; to disciples it feels like coming home.""",

    "04": "This is a good moment to pause. The reflection tabs in the margin invite you to sit with what you just read before we continue. Free registration saves all your reflection work to a personal report you can return to anytime from the user menu.",

    "05": """Many Christians identify Christ's ultimate act of obedience to the Father by the words of surrender in Gethsemane: "Not my will, but thine, be done." This moment will be studied in another chapter. Here, let us observe His daily examples of obedience as evidence of His character.

As a dutiful son, Yehoshua obeyed His mortal parents and respected His elders. Both obedience and discipline were required to learn the artisan skills of carpentry and stonework from Joseph. Mary would have benefited from His obedience in performing chores around the house, and running errands to neighbors and the market. He willingly obeyed the laws and traditions of attending to regular studies and worship at synagogue.

The concept of roots before fruits applies to this study of Christ's trait of obedience. Yehoshua's mortal character was not whole and complete from birth. His development was molded by perfect submission to the Father. He received grace from the Father as He "learned obedience" from suffering, sacrifice, and the day-to-day choices needed to submit to the will of the Father. He grew in wisdom, stature, and favor with both God and man.

He learned mortal obedience the same way God teaches from heaven: "line upon line, precept upon precept." His obedience was not automatic; it was chosen, costly, and deepened through mortal experience. His natural character was developed further by His mortal experience. This informs us about our own capacity to progress.

After the miracle of feeding the five thousand from a single boy's lunch, the crowd was astonished to the point that they were ready to make Him ruler of Israel immediately. "When Jesus therefore perceived that they would come and take him by force, to make him a king, he departed again into a mountain himself alone." He walked away from the easy path to kingship — offered freely. The people wanted Him for their earthly king. But the Father's plan was not a political throne in Galilee. The Son knew the path and obeyed. He traded the easy crown for Gethsemane, a betrayal, a trial, a cross, and a borrowed tomb in Jerusalem. He did not turn from the path. This is what obedience looks like in its highest form — not only the refusal of evil, but the refusal of good that is not God's will.""",

    "06": """I remember sitting with paychecks in hand while watching my young children play around me. For years as a young father, I worried about how it would affect them each time I chose to pay tithes and make charitable offerings. The widow's mite reminded me that God sees the cost of small obedience. And the Lord's challenge in Malachi sustained my resolve: "Prove me now herewith, saith the Lord of hosts, if I will not open you the windows of heaven, and pour you out a blessing, that there shall not be room enough to receive it." I was not perfect in this, but each time I chose obedience He kept His promise.

There are some who stand at the edge of this story and feel something other than inspiration. They hear of obedience and they hear constraint. They think of the covenant life of discipleship and they see doors closing — freedoms surrendered, individuality submerged, the self handed over to an institution or a set of rules that will define and diminish them. Rebellion is marketed as courage. Submission is marketed as weakness. And somewhere in the noise, the actual invitation of Yehoshua gets buried under the fears about whether it is safe to accept it.

It is worth pausing here and saying plainly: that is not what obedience to the Lord is. It is not the surrender of the true self — it is the rescue of the self from everything that was diminishing it. The disciples who followed Him did not become less; they became more than they had imagined they could be. The fishermen became apostles. The tax collector became an evangelist. The greatest persecutor of disciples became the greatest missionary the early Church produced. Obedience to the invitation of Yehoshua does not erase the person. It reveals the person — the truest, deepest, most fully realized version of who they were always meant to become.

The Lord does not stand at the gate of discipleship as a foreman with a longer list of tasks. He stands there as the one who has already borne the heaviest load in the history of creation — and who is offering, with open hands, to take yours. He is not asking you to carry what He has not already carried. He is asking you to stop carrying it alone.

There is a freedom on the other side of that surrender that the world cannot manufacture and cannot explain. The freedom the Savior offers is the freedom of the person who knows what they are, and why they are here, and to whom they belong — a knowledge that settles in one's heart like ballast in a storm.

And then God says within your heart, "Let there be light!"

The covenant life is lit from within in a way that the life of self-directed striving simply is not. There is a quality of joy available to the obedient disciple — not the surface happiness of favorable circumstances, but something deeper and steadier, a luminosity that persists even when circumstances are hard.

The yoke of Yehoshua is miraculously light upon the shoulders — fitting far better than any device or philosophy the world can fashion without God.

"Come unto me, all ye that labour and are heavy laden, and I will give you rest. Take my yoke upon you, and learn of me; for I am meek and lowly in heart: and ye shall find rest unto your souls. For my yoke is easy, and my burden is light."

Easy. Light. These are not the words of a taskmaster. They are the words of the One who designed the yoke so that it will not chafe, who knows exactly what it was made for, and who has been wearing it since before the world was formed. The burden is light because He is pulling at the same beam, and He does not tire.

You do not lose yourself in Him. You find yourself — lit up, set free, and finally moving in the direction you were built to travel.""",

    "07": "Pause here. What you just read is worth more than a passing thought — the reflection tabs in the margin are waiting for you. Free registration saves everything you write to a personal report in your user menu.",

    "08": """In the Gospel of Mark, Yehoshua's grace encountered a broken man. A leper — a man whose skin was rotting from a disfiguring disease — a man who searched for the Rabbi who could perform miracles. When he found the Master, he fell to his knees to confess, "If you are willing, you can make me clean." Yehoshua didn't hesitate in disgust. Instead, He was so moved with compassion for the man that He reached out His hand to touch him. The contact made Yehoshua ritually unclean under the Law. And then, He healed him.

This is what grace looks like when it encounters the broken — not pity from a safe distance, but a compassionate Savior choosing contact.

In the eleventh chapter of John, Yehoshua learned of the dire illness of His close personal friend, Lazarus. He didn't depart immediately to heal the friend, though He could have. He waited on purpose until after Lazarus had died.

Learning that the Master approached their home in Bethany, Martha and Mary both ran to Him, in turns, to fall down at His feet to sob, "Lord, if You had been here, my brother would not have died." Surrounded by the mourning sisters and a crowd of grieving Jews, He groaned in the spirit and was troubled. This is not the reaction of a distant and unrelatable deity.

He then asked, "Where have you laid him?" — and that question is extraordinary, because He already knew what He was about to do. He was about to raise Lazarus.

What happened next may be the most revealing moment in all of scripture.

Jesus wept.

This tender moment of compassion wasn't because Yehoshua felt sad about the death of His friend. Rather, it demonstrates His fully-developed compassion in the moment He chose to walk the full distance of human grief with a family in mourning, sharing in their pain. He didn't have to. He could have spoken the command at a distance as with the Roman centurion's dying servant. But He knew the value of entering the grief of the grieving — touch and presence — rather than healing from a distance.

Throughout His mortal ministry, the Lord was filled with compassion for souls who "fainted, and were scattered abroad, as sheep having no shepherd.""",

    "09": """This trait did not lessen or end with His death. In the Eastern Hemisphere, the resurrected Master comforted the weeping Mary at His empty tomb. He reassured the fearful disciples. He removed Peter's shame by allowing him to declare his love three times, once for each time he had previously denied Him. He walked with the grieving disciples on the road to Emmaus. He personally made a warm fire at a campsite and hand cooked a meal for His disciples who were returning from a frustrating day of fishing.

The resurrected Yehoshua also gloriously appeared to a multitude of disciples in the Western Hemisphere who had been waiting for Him. After delivering His gospel message, He cast His eyes round about again on the multitude, and beheld they were in tears, and did look steadfastly upon Him as if they would ask Him to tarry a little longer with them. "Behold, my bowels are filled with compassion towards you." He chose out of grace to stay for a while longer to visit and to heal the sick and afflicted. He blessed their children and prayed for them.

The word compassion in the Bible is translated from the Greek splagchnizomai. It signifies a profound gut-feeling of love and mercy that motivates actions to save and atone. It describes the visceral upheaval of seeing suffering — being shaken to the core by it, and then moving to act.

I have known what it is to be broken and in need of compassion — the instability and isolation of homelessness, the devastation of a broken marriage and being a single parent to three teenage daughters, the helpless feeling of being on the verge of losing everything, and the dark night of the soul when God seemed distant. But I have also known the healing relief of Christlike compassion of others who reached out to me in those dark days. I can name one pair of hands that reached for me. They belong to my dear wife, Michelle, who was brave enough to love me, generous enough to be a mother to my three daughters. I also gained a precious new daughter in the blending, and I was healed in the process.

When someone is in crisis beyond their own capacity to survive, sympathy is insufficient. The leper didn't need someone to quote Levitical laws. He needed someone to touch him with grace. There is a wide difference between knowing about the suffering of others and entering into it to support them. Grace at its most Christlike is compassion combined with the wisdom to know when and how to get involved.""",

    "10": "Take a moment here before moving on. Use the reflection tabs in the margin to sit with this — the chapter will wait. Free registration saves all your reflection work to a personal report you can find in the user menu.",

    "11": """A solitary Samaritan woman came to draw water at midday — an hour when no one else would be at the well — perhaps avoiding her peers. Yehoshua saw her and waited there. He greeted her with neither doctrine nor authority. He asked her for a drink, which would have seemed inappropriate within that cultural setting. Beginning with that simple request, He led her step by step, at exactly the pace she could follow. Water turned to worship. He resolved her past and shaped her future. He led her from natural curiosity to a confession of faith. She recognized the promised Messiah. And what did she do? She left her water pot and ran to tell her village, "Come, see a man, which told me all things that ever I did: is not this the Christ?" Grace received became grace shared in a matter of minutes. And it transformed her, from an isolated soul to student, and then from student to teacher.

This is His pattern. How Yehoshua taught reveals who He was. He didn't simply pour out truth — He calibrated it to the hearer. Parables for crowds who needed to discover truth at their own pace. Direct doctrine for disciples ready to receive it. Piercing questions for Pharisees hiding behind their authority. Silence as a teaching tool to instruct a Roman governor who had no interest in the answer. Every choice of method was an act of respectful grace for the person standing before Him.

Why did He teach at all? Because "out of the abundance of the heart the mouth speaketh." A heart full of grace overflows. Restoration scripture confirms this in an account of Lehi, an elderly prophet. In a vision, he tasted the fruit of the tree of life and his first impulse was not to analyze it but to turn to his family. "I began to be desirous that my household should partake of it also." The desire to share what is precious is the natural fruit of having received it. This is grace communicated.

I remember a moment when a teenage special education student said something so disrespectful in my science laboratory that every instinct told me to respond by matching his energy. Instead I bit my tongue, threw a desperate prayer heavenward, and waited. The Spirit softened my heart and opened my eyes — not just to find compassion for the student, but to see how to reach him. The unmet need motivating his behavior became the focus for the teaching moment. I learned that day what the Master practiced perfectly: truth that reaches a soul must first be calibrated to the soul it is reaching. This is not just a teaching technique; it flows from habits of grace that we learn from Yehoshua the man.""",

    "12": """The same hands that overturned tables in the temple at Jerusalem also washed feet in the prepared upper room. Why? It bears repeating: Yehoshua was full of grace and truth.

On the evening before His crucifixion, Yehoshua rose from His place at the last supper table to perform a task that had been neglected by others. He laid aside His outer garment, wrapped a towel around His waist, and poured water into a basin. The Master then knelt before His servants.

Washing of guests' feet was a degrading task assigned to the lowest household slave — work that Jewish law forbade compelling of a Hebrew servant. It was also an act of affectionate personal service that a wife would perform for her husband. The paradox is not that degradation equals affection, but that love can stoop to perform what status would despise.

Peter's horrified reaction reveals the depth of meaning in watching his Master do this task.

Yehoshua washed Peter's feet — who would deny Him. He washed the feet of Judas, who already had made plans to betray Him. The Master was not ignorant of these things, yet He knelt to serve, taking the posture and position of one that no one notices.

Earlier that same Passover week, Yehoshua entered the temple and saw that the Court of the Gentiles — the only part of the temple where people of all faiths and nationalities could worship the God of Israel — had been converted into a bustling marketplace filled with vendors, moneychangers, animals and the chaos, filth, and greed that go with these things. He found a place where He could sit down and make a whip of cords. His reaction was not sudden. It was measured and premeditated.

Those gentle hands — those that washed feet, broke bread with the hungry, healed lepers, shaped the world, and gestured to all to come and see — overturned the vendor tables, scattered their wares, cracked His whip in deliberate fury and His voice thundered quoted scriptures.

His anger was not aimed solely at the merchants, but its scope included the corrupt priests that profited from the corruption of the house of prayer. He courageously took a stand to confront an abusive system, not just functionaries. His anger focused on anything that came between souls and the Kingdom of Heaven. And no one could stop Him. The chief priests feared Him and could not act.

Meekness is not weakness, and courage is not rage. Both are manifestations of the same character trait, one that flows in different directions from the same source — the grace and truth at the core of His personality. The meek serve when dignity says don't bother. The courageous serve when safety says don't dare. Both require the same inner conquest — the surrender of ego before the work of love begins.

Yehoshua did not kneel because He was timid. He did not overturn tables because He lost control. He mastered His natural impulses and then acted from what remained: grace directed by truth. When truth called for gentleness, He was gentle without being weak. When truth called for confrontation, He confronted without being cruel. This is what mastery looks like — not the absence of strong emotion, but the governance of it by wisdom and love.

I recall several moments of conflict in which I said something I thought sounded righteous but wound up being self-righteous and hurtful. I repent humbly before God. I ask those I harmed for forgiveness.

I pray that I am developing a measure of Christlike character as His grace and truth work upon my spirit. I imitate Him imperfectly, but it is my covenant duty to try. There is comfort for me in holding up the character of Christ as a mirror to examine my soul. I remind myself often not to focus on how far I fall short of Him, but to hold to my faith that His grace sees me as I hope to be, and that His spirit works tirelessly upon me daily to close the gap.""",

    "13": """The Pharisees and their entourage of Scribes dragged her into the temple courts on a morning when Yehoshua sat teaching a gathering of the people. They interrupted His teaching and thrust her in the middle of His gathering.

They weren't interested in redeeming her soul at all. They were trying to build a case against Yehoshua. Their challenge: "Moses in the law commanded us, that such should be stoned: but what sayest thou?" She must have been shaking with fear and shame before the crowd.

The Master stooped to write on the ground with a finger. We don't know what He wrote. We do know that Yehoshua refused to answer on their terms.

When they pressed the Master, He rose and delivered one sentence that shattered their trap without breaking the law: "He that is without sin among you, let him first cast a stone at her." They departed one by one, eldest first — stung by their own conscience. When only the woman remained, He delivered a powerful sermon in divine brevity: "Neither do I condemn thee: go, and sin no more."

Mercy without justice is indulgence that leaves a sinner unchanged. Justice without mercy is cruelty that crushes the soul of the sinner. In Yehoshua, we find that the grace and truth in Him courageously names what must change while meekly protecting the soul that must make the change.

"I am the light of the world: he that followeth me shall not walk in darkness, but shall have the light of life." The context for this verse is Yehoshua's demonstration of the dynamic between justice and mercy — and more importantly, how this affected the life of the woman whom He did not condemn.

Again I hear the voice of my saintly mother: "Aaron, you never know what sorrow lies behind a smile; you never know how someone who has mistreated you was personally greeted and then treated in this life. Be like Jesus." Her voice echoes in my heart like that of Yehoshua, teaching me to neither announce my own virtues nor to assume another's vices.

In all our spiritual journeys, when faced with the opportunities to judge one another, let us walk in the grace of His light. Anything else is walking in the dark.""",

    "14": """Contrasting His own lifestyle to that of His cousin who taught in the wilderness, Yehoshua described Himself as eating and drinking with His followers.

His enemies claimed He took this to excess as "a glutton and a drunkard, a friend of tax collectors and sinners." They meant this as an insult. Read it again. Think: what kind of person draws that accusation? Not a broody stoic. Not the pale, sorrowful figure captured in medieval stained glass. His enemies saw a man who showed up at feasts, who turned water into wine at a wedding — His first recorded miracle was performed to keep a celebration going at the request of His own mother. Yehoshua was the kind of man that people wanted as a friend and companion. His presence made rooms feel different, better.

The man Yehoshua had joy.

This wasn't a shallow happiness — it was the deep kind of gladness that survives grief and sustains inner purpose. Luke named His emotion: "In that hour Jesus rejoiced in spirit." The occasion of such joy had nothing to do with miracles or outsmarting enemies. The seventy had just returned from their missions, and the Father had revealed truth to the hearts of the faithful. Yehoshua's joy was in the Father's work; in the lost sheep's safety; in the return of the prodigal. In one tender account, the resurrected Lord knelt among the children, blessed them one by one, and wept — not from sorrow but from joy so full it overflowed.

This is the nature of grace rejoicing. It is not the absence of sorrow nor a paradise of pleasure. Joy that comes from Christlike grace cannot be extinguished by opposition. Joy and sorrow live side by side in every honest life. The writer of Hebrews understood: Jesus, "who for the joy that was set before him endured the cross." Joy was His motive, not the reward.

"These things have I spoken unto you, that my joy might remain in you, and that your joy might be full." This is His invitation for you to receive the same grace that fueled His own gladness — and to let it overflow into the lives of others.

I remember a full day of shoveling manure with fellow saints for neighborhood gardens. We didn't dare hug or even shake hands, smiling brightly despite being thoroughly covered in muck. How odd it is that we can be covered in filth while filled with joy in the service of the Master and while caring for one another. This truly is the abundant life He promised.""",

    "15": """This chapter could not possibly detail all the marvelous personality traits that flow from Yehoshua's core of grace and truth. The Apostle John also felt the need to explain: "There are also many other things which Jesus did, the which, if they should be written every one, I suppose that even the world itself could not contain the books that should be written."

My purpose here is to introduce Yehoshua — the man behind the ministry — as a relatable person that we would be delighted to have as a friend. Better than being introduced by servants, the Master of grace and truth shared His own character portrait in the form of the Sermon on the Mount. The Beatitudes are instructions — and they are also something more. The first words of His first recorded sermon were a character sketch of Himself.

We gain marvelous confirmation of the nature of His own character by assuming that the Teacher practiced what He taught. He not only described what His disciples should become, He described what He already was — and what His grace makes possible in every willing heart.

That same grace that is the living core of His character is a power at work in every willing disciple. Studying His character is not meant to measure the distance between Him and us — it is meant to show us what we can become as His grace works its refining purpose in our mortal lives. Beholding the truth of His grace as the mechanism of our own transformation is the whole point of this chapter.""",

    "16": """You've sat with Yehoshua. You have studied the Man who is God. You've observed that His great heart — full of grace — beats with His life-giving truth throughout all parts of His character. We hear the phrase "He died for us" often, but let us not forget that He also lives for us. "He is the Lord of both the dead and the living." His heart still beats for you.

Now is an important moment for your own heart. Will it begin to beat for Him as well?

John recorded a profound prayer of Jesus — a prayer that is called The Great Intercessor's Prayer.

"My prayer is not for them alone. I pray also for those who will believe in me through their message."

You are inside His prayer. Jesus prayed for the person reading this chapter, by name in the eternal sense. This is not a simple metaphor. He saw you.

His heart still beats for you.

"I have given them the glory that you gave me, that they may be one as we are one — that they may be brought to complete unity." That same graceful character you just studied — the humility, the compassion, the mastery of every human impulse — is not to be held at a distance for admiration. It is a gift that has been freely given. Will it be received? The glory of Christ's character is the gift of grace to the willing disciple. But it must be received through the beholding.

His arms are open wide.

Christ prayed that we would behold His glory. And we are taught that beholding transforms the beholder into the same image, "from glory to glory." It has already begun in you.

His hands will bless you.

Christ prayed that His disciples may become "one; as thou, Father, art in me, and I in thee, that they also may be one in us — that they may be made perfect in one." The heart of Christ is not just for the individual — it is the bonding agent that makes us one with Him, one with the Father, and one with the heart of every other disciple.

His voice calls you home.

Christ closed His prayer with His most sincere longing for us: "that the love you have for me may be in them and that I myself may be in them." The Great Intercessor's Prayer doesn't end with a desire for nearness — His great heart desires a true oneness with you in spirit and in truth.

This oneness does not just happen. It is a journey — an epic story arc. As we learn of Him and follow, His grace transforms us, refines our own character over time.

God is calling: "Come to Zion."

His grace is sufficient for you.

The next chapter will show you what it cost Him. We will behold His mastery tested to its absolute limit as we follow Him to Gethsemane and to Golgotha.

We testify that the character of the person we have studied here is the Son of God in the Highest. "Salvation is found in no one else, for there is no other name under heaven given to mankind by which we must be saved."

In the name of Jesus Christ, Amen.""",

    "17": "Before we close — the reflection tabs in the margin are waiting. What you just read deserves more than a moment. Free registration saves all your reflection work to a personal report in your user menu.",
}

# For each chunk, find where each sentence begins within the narration text,
# then look up that character position in the chunk's character timeline.

def find_in_narration(sentence_text, narration_text, search_from=0):
    """
    Find the character position of sentence_text's opening words
    within narration_text, starting from search_from.
    Returns (char_position, next_search_from) or (search_from, search_from+1) on failure.
    """
    sent_words = words_of(sentence_text)
    if not sent_words:
        return search_from, search_from

    # Build search target: first 1-2 meaningful words, normalized
    first_word = sent_words[0]
    second_word = sent_words[1] if len(sent_words) > 1 else None

    narr_lower = narration_text.lower()
    # Normalize: remove punctuation for matching
    import re as _re
    narr_norm = _re.sub(r'[^\w\s]', '', narr_lower)
    # Build word list with original positions
    # Simpler: just search for first_word as substring
    pos = search_from
    search_limit = min(search_from + 3000, len(narration_text))

    while pos < search_limit:
        # Find next word boundary
        while pos < search_limit and narration_text[pos] in ' \n\t\r':
            pos += 1
        word_start = pos
        while pos < len(narration_text) and narration_text[pos] not in ' \n\t\r':
            pos += 1
        word_end = pos

        candidate = normalize_text(narration_text[word_start:word_end])

        if candidate == first_word:
            # Check second word
            if second_word:
                p2 = pos
                while p2 < len(narration_text) and narration_text[p2] in ' \n\t\r':
                    p2 += 1
                p2e = p2
                while p2e < len(narration_text) and narration_text[p2e] not in ' \n\t\r':
                    p2e += 1
                candidate2 = normalize_text(narration_text[p2:p2e])
                if candidate2 == second_word:
                    return word_start, word_end
            else:
                return word_start, word_end

    return search_from, search_from + 1


def char_pos_to_time(char_pos, narration_text, chunk_chars, chunk_times):
    """
    Given a character position in narration_text, find the corresponding
    position in the chunk alignment array and return its timestamp.

    The narration_text and chunk_chars represent the same spoken text but
    may differ in whitespace, newlines, or minor punctuation. We walk both
    simultaneously, skipping whitespace differences, to find the alignment
    position that corresponds to char_pos in the narration text.

    Fallback: if direct walk fails, use character-count ratio as estimate.
    """
    if not chunk_times:
        return 0.0
    if char_pos <= 0:
        return chunk_times[0]
    if char_pos >= len(narration_text):
        return chunk_times[-1]

    # Walk both strings together, skipping whitespace/newline differences
    n_pos = 0   # position in narration_text
    a_pos = 0   # position in chunk_chars alignment array

    while n_pos < char_pos and a_pos < len(chunk_chars):
        nc = narration_text[n_pos] if n_pos < len(narration_text) else ''
        ac = chunk_chars[a_pos] if a_pos < len(chunk_chars) else ''

        # Normalize: treat all whitespace/newline as equivalent
        nc_is_ws = nc in ' \t\n\r'
        ac_is_ws = ac in ' \t\n\r'

        if nc_is_ws and ac_is_ws:
            n_pos += 1
            a_pos += 1
        elif nc_is_ws:
            # narration has whitespace, alignment doesn't — skip narration ws
            n_pos += 1
        elif ac_is_ws:
            # alignment has whitespace, narration doesn't — skip alignment ws
            a_pos += 1
        elif nc.lower() == ac.lower():
            n_pos += 1
            a_pos += 1
        else:
            # Mismatch — advance both to recover
            n_pos += 1
            a_pos += 1

    a_pos = min(a_pos, len(chunk_times) - 1)
    return chunk_times[a_pos]


sentence_timestamps = {}

# Read chunk alignment data once
chunk_alignment_cache = {}
for chunk_id, *_ in CHUNKS:
    path = os.path.join(ALIGNMENT_DIR, f"chunk_{chunk_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunk_alignment_cache[chunk_id] = {
        "chars": data.get("characters", []),
        "starts": data.get("character_start_times_seconds", []),
    }

# Process each prose chunk
for chunk_id, first_sent, last_sent, is_cue, cue_idx in CHUNKS:
    if is_cue:
        continue

    narration_text = CHUNK_TEXTS.get(chunk_id, "")
    alignment = chunk_alignment_cache[chunk_id]
    chunk_chars = alignment["chars"]
    chunk_starts = alignment["starts"]

    # Get the global offset for this chunk
    # Find the chunk index
    chunk_index = next(i for i, (cid, *_) in enumerate(CHUNKS) if cid == chunk_id)
    pre_dur = chunk_pre_durations[chunk_index]
    cumulative_pre_before = sum(chunk_pre_durations[:chunk_index])
    chunk_actual_start = (cumulative_pre_before / total_pre_duration) * assembled_duration
    chunk_actual_dur   = (pre_dur / total_pre_duration) * assembled_duration

    narr_ptr = 0
    for sent_idx in range(first_sent, last_sent + 1):
        sent_text = sentences.get(sent_idx, "")
        char_pos, narr_ptr = find_in_narration(sent_text, narration_text, narr_ptr)

        # Map char_pos to time within chunk
        chunk_time = char_pos_to_time(char_pos, narration_text, chunk_chars, chunk_starts)

        # Scale to assembled timeline
        global_time = chunk_actual_start + (chunk_time / pre_dur) * chunk_actual_dur
        sentence_timestamps[sent_idx] = round(global_time, 3)

print(f"  {len(sentence_timestamps)} sentence timestamps aligned")

# Detailed dump of chunk 01 sentences (s0-s27) to diagnose drift
print("\n  --- Chunk 01 sentence timestamps (s0-s27) ---")
for idx in range(28):
    if idx in sentence_timestamps:
        t = sentence_timestamps[idx]
        preview = sentences.get(idx, "")[:35]
        print(f"    s{idx:>3}: {t:>8.3f}s  {preview}")

# Spot check
for idx in [0, 1, 4, 10, 62, 85, 86, 150, 151, 199, 200, 343, 384]:
    if idx in sentence_timestamps:
        t = sentence_timestamps[idx]
        mins = int(t // 60)
        secs = t % 60
        preview = sentences.get(idx, "")[:40]
        print(f"    s{idx:>3}: {t:>8.3f}s ({mins}:{secs:05.2f}) {preview}")

# ── Step 5: Calculate cue timestamps ─────────────────────────────────────

print("\n=== Step 5: Calculating cue timestamps ===")

cue_timestamps = {}
cumulative_pre = 0.0
for i, (chunk_id, first_sent, last_sent, is_cue, cue_idx) in enumerate(CHUNKS):
    pre_dur = chunk_pre_durations[i]
    if is_cue:
        chunk_actual_start = (cumulative_pre / total_pre_duration) * assembled_duration
        chunk_actual_dur   = (pre_dur / total_pre_duration) * assembled_duration
        # Place trigger 2 seconds before end of cue chunk
        cue_time = round(chunk_actual_start + chunk_actual_dur - 2.0, 3)
        cue_timestamps[cue_idx] = cue_time
        print(f"  CUE {cue_idx}: {cue_time:.3f}s")
    cumulative_pre += pre_dur

# ── Step 6: Build paragraph timestamps ───────────────────────────────────

print("\n=== Step 6: Building paragraph timestamps ===")

para_timestamps = {}
for para_idx, first_sent in sorted(PARAGRAPH_MAP.items()):
    if first_sent in sentence_timestamps:
        para_timestamps[para_idx] = sentence_timestamps[first_sent]
    else:
        print(f"  WARNING: s{first_sent} (para {para_idx}) not found")

# p0 is the Invocation heading (never highlighted — heading span).
# p1 is the first prose paragraph. Its ElevenLabs timestamp reflects the
# silence at the start of the assembled MP3 before the narrator begins.
# Set p1 to 0.0 so highlighting fires immediately when play is pressed.
para_timestamps[1] = 0.0

print(f"  {len(para_timestamps)} paragraph timestamps built")

# ── Step 7: Build sentence-to-paragraph lookup ────────────────────────────

para_indices = sorted(PARAGRAPH_MAP.keys())
sentence_to_para = {}
for i, para_idx in enumerate(para_indices):
    first_sent = PARAGRAPH_MAP[para_idx]
    next_first = PARAGRAPH_MAP[para_indices[i + 1]] if i + 1 < len(para_indices) else 9999
    for s in range(first_sent, next_first):
        sentence_to_para[s] = para_idx

# ── Step 8: Write output JSON ─────────────────────────────────────────────

print("\n=== Step 8: Writing output JSON ===")

output = {}
for para_idx, t in sorted(para_timestamps.items()):
    output[f"p{para_idx}"] = round(t, 3)
for sent_idx, para_idx in sorted(sentence_to_para.items()):
    output[f"s{sent_idx}"] = para_idx
for cue_idx, t in sorted(cue_timestamps.items()):
    output[f"cue{cue_idx}"] = round(t, 3)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"  {len([k for k in output if k.startswith('p')])} paragraph timestamps")
print(f"  {len([k for k in output if k.startswith('s')])} sentence-to-paragraph mappings")
print(f"  {len([k for k in output if k.startswith('cue')])} cue timestamps")
print(f"  Saved to {OUTPUT_PATH}")

# ── Step 9: Sanity check ──────────────────────────────────────────────────

print("\n=== Sanity Check ===")
checks = [
    ("p0",    "Invocation heading"),
    ("p1",    "By the time the first sandals"),
    ("p17",   "Mastery of Humility heading"),
    ("p23",   "My mother used to remind me"),
    ("p24",   "Mastery of Obedience heading"),
    ("p40",   "You do not lose yourself"),
    ("p41",   "Mastery of Compassion heading"),
    ("p48",   "Jesus wept"),
    ("p56",   "Mastery of Teaching heading"),
    ("p83",   "Mastery of Joy heading"),
    ("p96",   "Benediction heading"),
    ("p115",  "In the name of Jesus Christ"),
    ("cue385", "pause-humility"),
    ("cue386", "pause-obedience"),
    ("cue387", "pause-compassion"),
    ("cue388", "pause-closing"),
]
for key, label in checks:
    if key in output:
        val = output[key]
        if isinstance(val, float):
            mins = int(val // 60)
            secs = val % 60
            print(f"  {key:>8} = {val:>8.3f}s  ({mins}:{secs:06.3f})  {label}")

print("\nDone. Commit src/_data/timestamps/chapter-09-yehoshua-the-man.json")
