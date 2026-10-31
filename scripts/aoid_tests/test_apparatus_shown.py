"""Tests for src/_data/apparatusShown.js, the apparatus the Articles page embeds (CODE-AOID2-41).

The Article 12 Second Edition changes (new spans s11 and s12, revised text of s5 and s6, revised panel comments
s1-s10, added anchors on s4-s6) are carried in apparatusData.json by marker fields: `text_first_edition`,
`panel_comment_first_edition` and an anchor's `second_edition: true`. With the switch OFF the embedded apparatus
must hold the First Edition values; with it ON it must hold the Second Edition values; and no marker field may
reach either output.

Run: python -m pytest scripts/aoid_tests
"""
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = json.loads((REPO / "src" / "_data" / "apparatusData.json").read_text(encoding="utf-8"))
MARKERS = ("text_first_edition", "panel_comment_first_edition", "comment_first_edition", "second_edition", "first_edition_only")
NEW_SPANS = ("s11", "s12")


def shown(on):
    env = {k: v for k, v in os.environ.items() if k != "WOP_AOID2_SECOND_EDITION"}
    if on:
        env["WOP_AOID2_SECOND_EDITION"] = "1"
    p = subprocess.run(
        ["node", "-e", "process.stdout.write(JSON.stringify(require('./src/_data/apparatusShown.js')))"],
        cwd=REPO, env=env, capture_output=True, encoding="utf-8", check=True,
    )
    return json.loads(p.stdout)


def keys_anywhere(o, found=None):
    found = set() if found is None else found
    if isinstance(o, dict):
        for k, v in o.items():
            found.add(k)
            keys_anywhere(v, found)
    elif isinstance(o, list):
        for v in o:
            keys_anywhere(v, found)
    return found


def test_switch_off_embeds_first_edition_article_12():
    a12 = shown(False)["A12"]
    assert list(a12) == [f"s{i}" for i in range(1, 11)]
    for sid, s in a12.items():
        src = DATA["A12"][sid]
        assert s["panel_comment"] == src["panel_comment_first_edition"], sid
        assert s["text"] == src.get("text_first_edition", src["text"]), sid
        for col in ("biblical", "restoration"):
            assert [a["ref"] for a in s[col]] == [a["ref"] for a in src[col] if not a.get("second_edition")], (sid, col)


def test_switch_on_embeds_second_edition_article_12():
    a12 = shown(True)["A12"]
    assert list(a12) == [f"s{i}" for i in range(1, 13)]
    for sid, s in a12.items():
        src = DATA["A12"][sid]
        assert s["panel_comment"] == src["panel_comment"], sid
        assert s["text"] == src["text"], sid
        for col in ("biblical", "restoration"):
            assert [a["ref"] for a in s[col]] == [a["ref"] for a in src[col]], (sid, col)
    assert "naked honesty" not in a12["s5"]["text"] and a12["s6"]["text"].endswith("remembered")


def test_no_marker_field_reaches_either_output():
    for on in (False, True):
        assert not (keys_anywhere(shown(on)) & set(MARKERS)), f"marker field embedded with switch {'ON' if on else 'OFF'}"


def test_every_article_12_span_with_a_revised_comment_keeps_its_first_edition_comment():
    for sid in (f"s{i}" for i in range(1, 11)):
        assert DATA["A12"][sid]["panel_comment_first_edition"], sid
    for sid in NEW_SPANS:
        assert "panel_comment_first_edition" not in DATA["A12"][sid]


def test_article_12_second_edition_comments_use_closed_em_dashes():
    for sid, s in shown(True)["A12"].items():
        assert " - " not in s["panel_comment"] and " — " not in s["panel_comment"], sid


# Article 9 s6-s9 (CODE-AOID2-44): revised panel comments, six revised anchor comments and one added anchor,
# all behind the switch. The anchor-comment marker `comment_first_edition` and the added-anchor marker
# `second_edition` are the CODE-AOID2-32/33 ones; the panel-comment marker is the CODE-AOID2-41 one.
A09_REVISED = ("s6", "s7", "s8", "s9")


def test_article_9_s6_to_s9_switch_off_keeps_first_edition_comments_and_anchors():
    a09 = shown(False)["A09"]
    for sid in A09_REVISED:
        src = DATA["A09"][sid]
        assert a09[sid]["panel_comment"] == src["panel_comment_first_edition"], sid
        assert not a09[sid]["panel_comment"].startswith("The Article confesses only"), sid
        for col in ("biblical", "restoration"):
            assert [a["ref"] for a in a09[sid][col]] == [a.get("ref_first_edition", a["ref"]) for a in src[col] if not a.get("second_edition")], (sid, col)
            for a in a09[sid][col]:
                srca = next(x for x in src[col] if x.get("ref_first_edition", x["ref"]) == a["ref"])
                assert a["comment"] == srca.get("comment_first_edition", srca["comment"]), (sid, a["ref"])
    assert "2 John 1:9" not in [a["ref"] for a in a09["s7"]["biblical"]]


def test_article_9_s6_to_s9_switch_on_opens_each_comment_with_its_floor_and_adds_2_john_1_9():
    a09 = shown(True)["A09"]
    for sid in A09_REVISED:
        first, second = a09[sid]["panel_comment"].split(chr(10) * 2)
        assert first.startswith("The Article confesses only what") and second, sid
    assert [a["ref"] for a in a09["s7"]["biblical"]].count("2 John 1:9") == 1
    assert next(a for a in a09["s7"]["biblical"] if a["ref"] == "2 John 1:9")["comment"] == (
        "Named in the s7 floor as its qualifier: precedence is not dismissal. John binds abiding in the doctrine of Christ "
        "to having God; the span ranks doctrine beneath the relationship without setting the two against each other."
    )
    assert next(a for a in a09["s28"]["restoration"] if a["ref"] == "Moroni 10:8–18")["comment"] == (
        "Read with Moroni 10:4–5, cited above with the Spirit as Teacher."
    )
    assert sum("comment_first_edition" in a for sid in A09_REVISED for col in ("biblical", "restoration") for a in DATA["A09"][sid][col]) >= 6

# Article 9 commentary corrections (CODE-AOID2-46): revised panel comments on s1-s22 (s8's was built in CODE-AOID2-44),
# revised anchor notes, one added anchor (2 Nephi 9:25-26 at s17), one removed anchor (D&C 35:17-18 at s4, marked
# `first_edition_only`), the s26 floor sentence, all behind the switch.
A09_CORRECTED = tuple(f"s{i}" for i in range(1, 23))


def test_article_9_corrections_switch_off_keeps_head_comments_and_anchors():
    a09 = shown(False)["A09"]
    for sid in A09_CORRECTED:
        src = DATA["A09"][sid]
        assert src["panel_comment_first_edition"], sid
        assert a09[sid]["panel_comment"] == src["panel_comment_first_edition"], sid
        for col in ("biblical", "restoration"):
            for a in a09[sid][col]:
                srca = next(x for x in src[col] if x.get("ref_first_edition", x["ref"]) == a["ref"])
                assert a["comment"] == srca.get("comment_first_edition", srca["comment"]), (sid, a["ref"])
    assert "D&C 35:17–18" in [a["ref"] for a in a09["s4"]["restoration"]]
    assert "2 Nephi 9:25–26" not in [a["ref"] for a in a09["s17"]["restoration"]]
    assert "s26" not in a09 and "s29" not in a09


def test_article_9_corrections_switch_on_shows_approved_changes():
    a09 = shown(True)["A09"]
    for sid in A09_CORRECTED:
        assert a09[sid]["panel_comment"] == DATA["A09"][sid]["panel_comment"], sid
        assert a09[sid]["panel_comment"] != DATA["A09"][sid].get("panel_comment_first_edition"), sid
    assert "D&C 35:17–18" not in [a["ref"] for a in a09["s4"]["restoration"]]
    assert len(a09["s4"]["restoration"]) == len(DATA["A09"]["s4"]["restoration"]) - 1
    assert [a["ref"] for a in a09["s17"]["restoration"]].count("2 Nephi 9:25–26") == 1
    assert a09["s26"]["panel_comment"].split(chr(10) * 2)[0].endswith(
        "It connects to the one boundary the Prologue names. It does not settle how that witness is received or recognised."
    )
    assert "AOID2-BOUNDARY" not in a09["s26"]["panel_comment"]
    assert a09["s29"]["panel_comment"].count(chr(10) * 2) == 2 - 1



# --- AOID2 step 107 (CODE-AOID2-66): Article 9 rally point (span s30, author's note, floor A9-F14) ---
S30_TEXT = 'Whatever first turned you toward Christ, we rejoice that you seek Him. We may differ on how the map is rightly read, and on which way leads most surely to Him, but let none of us fail to come unto Jesus of Nazareth. Should any instrument we carry, even this one, turn us from Christ or teach us contempt for a fellow traveler, we have surely lost our bearing, and must take our sighting of Him anew.'
S30_NOTE = 'This Article proposes a rallying point for disciples of every Christian tradition. Its picture is not new: Christ the North Star, His Spirit the compass, the scriptures the map. Each part is drawn from scripture that Christians of every tradition receive, and the arrangement adds nothing to the gospel of Jesus Christ. I offer it not as a creed, nor as a correction to any church, but as a place where we may gather and look together toward the One who prayed that all who believe in Him might be one (John 17:20-23). Its only test is the one it sets for itself: does it bring us, together, to Him?'
S30_FLOOR = 'The Article confesses only what Philippians 1:15-18, Mark 9:38-40 and John 17:20-23 confess: wherever Christ is preached, His disciples rejoice; Christ forbade His disciples to stop one who worked in His name though he followed not with them; and Christ prayed that all who believe on Him might be one. This is the floor: the disciple rejoices in every turning toward Christ, differences over the way to Him are no warrant for forbidding one another, and whatever turns disciples from Christ or toward contempt for one another has lost its bearing. It does not settle which way leads most surely to Him, how the scriptures are rightly read or by what authority, what a church may require of its own members, or whether and how the traditions should be united; each tradition fills those in its own house.'
S30_ANCHORS = {
    "biblical": ["Philippians 1:15–18", "Mark 9:38–40", "John 17:20–23", "1 Corinthians 1:10–13", "Matthew 11:28", "Matthew 7:7"],
    "restoration": ["2 Nephi 26:33", "3 Nephi 11:29", "Moroni 10:32"],
}


def render_a09(on):
    script = (
        "const n=require('nunjucks');const e=new n.Environment(new n.FileSystemLoader('src/_includes'),{autoescape:false});"
        "process.stdout.write(e.render('aoid/a09.njk',{aoidSecondEdition:{on:%s}}))" % ("true" if on else "false")
    )
    return subprocess.run(["node", "-e", script], cwd=REPO, capture_output=True, encoding="utf-8", check=True).stdout


def test_article_9_rally_point_span_and_anchors_appear_only_with_the_switch_on():
    on, off = shown(True)["A09"], shown(False)["A09"]
    assert "s30" not in off
    s = on["s30"]
    assert (s["text"], s["type"], s["named_concept"]) == (S30_TEXT, "concept", False)
    assert s["panel_comment"] == S30_FLOOR and chr(10) not in s["panel_comment"]
    for col, refs in S30_ANCHORS.items():
        assert [a["ref"] for a in s[col]] == refs
        assert all(a["comment"] == S30_NOTES[a["ref"]] for a in s[col])  # filled by CODE-AOID2-68 (step 172)
    assert list(on)[-1] == "s30" and list(on)[-2] == "s29"
    assert not keys_anywhere(s) & set(MARKERS)


def test_article_9_rally_point_span_and_note_render_only_with_the_switch_on():
    on, off = render_a09(True), render_a09(False)
    assert 'data-span="s30"' not in off and "article-author-note" not in off
    assert S30_NOTE not in off and S30_TEXT not in off
    assert on.count('data-span="s30"') == 1 and on.count(S30_TEXT) == 1 and on.count(S30_NOTE) == 1
    assert "(John 17:20-23)" in S30_NOTE
    # note first in the body, span after s22 and immediately before the reflection prompt
    assert on.index('<div class="article-body">') < on.index("article-author-note") < on.index('data-span="s1"')
    assert on.index('data-span="s22"') < on.index('data-span="s30"') < on.index('<div class="article-rjw">')
    assert on.count("article-author-note") == 1


def test_article_9_rally_point_floor_a9_f14_is_in_the_ledger_and_the_floor_document():
    ledger = (REPO / "data-sources" / "aoid" / "floor_ledger.yaml").read_text(encoding="utf-8")
    block = ledger.split("- item: A9-F14", 1)[1].split(chr(10) + "  - item:", 1)[0].split(chr(10) + "# ", 1)[0]
    assert "span: A09.s30" in block and "floor_ratified: 2026-10-31" in block
    assert "scored_on: null" in block and "scoring_records: []" in block
    doc = (REPO / "data-sources" / "aoid" / "floors" / "WoP_AOID2_A09_s30_RallyPoint_Floor_Ratified_20261031.md").read_text(encoding="utf-8")
    assert "> " + S30_FLOOR in doc.split(chr(10))

# --- AOID2 step 109 (CODE-AOID2-67): A9-F2 (s7) and A9-F3 (s8) re-centred 31 Oct 2026 ---
A9F2_NEW = 'The Article confesses only what 1 Corinthians 8:1-4 and Matthew 7:21-23 confess: knowledge puffeth up, but charity edifieth, and if any man love God, the same is known of him; and this though the knowledge was true, that an idol is nothing in the world and there is none other God but one; and not every one that saith unto Christ, Lord, Lord, shall enter the kingdom, for to some who spoke in His name He will say, I never knew you. This is the floor: to love God and be known of Him takes precedence over accuracy of doctrine. Precedence is not dismissal: doctrine is ranked, not discarded, and abiding in the doctrine of Christ (2 John 1:9) is not set against abiding in Him. It does not settle which doctrines are necessary to salvation, how much right belief God requires of each soul, or by what authority doctrine is defined; each tradition fills those in its own house.'
A9F3_NEW = "The Article confesses only what 1 Samuel 15:22, Luke 9:23, James 1:22 and John 10:27 confess: to obey is better than sacrifice, and to hearken than the fat of rams; if any man will come after Christ, let him deny himself, take up his cross daily, and follow Him; we are doers of the word, and not hearers only; and Christ's sheep hear His voice and follow Him. This is the floor: correct tenets and sound understanding are desirable, but faithfully following Christ is better. It does not settle how faith, grace and works are related in salvation, whether following Christ is the fruit or the condition of salvation, or which doctrines are necessary; each tradition fills those in its own house."


def anchor(span, col, ref):
    return [a for a in span[col] if a["ref"] == ref]


def test_article_9_s7_s8_recentred_floors_are_paragraph_one_only_with_the_switch_on():
    on, off = shown(True)["A09"], shown(False)["A09"]
    assert on["s7"]["panel_comment"].split(chr(10) * 2)[0] == A9F2_NEW
    assert on["s8"]["panel_comment"].split(chr(10) * 2)[0] == A9F3_NEW
    for sid in ("s7", "s8"):
        assert off[sid]["panel_comment"] == DATA["A09"][sid]["panel_comment_first_edition"]
        assert A9F2_NEW not in off[sid]["panel_comment"] and A9F3_NEW not in off[sid]["panel_comment"]
        # commentary paragraph 2 is kept with the switch on
        assert on[sid]["panel_comment"].split(chr(10) * 2)[1:] == DATA["A09"][sid]["panel_comment"].split(chr(10) * 2)[1:]


def test_article_9_s7_s8_floor_verses_are_anchors_with_the_switch_on_and_the_first_edition_set_is_unchanged():
    on, off = shown(True)["A09"], shown(False)["A09"]
    for ref in ("1 Corinthians 8:1–4", "Matthew 7:21–23"):
        assert len(anchor(on["s7"], "biblical", ref)) == 1
    for ref in ("1 Samuel 15:22", "Luke 9:23", "James 1:22", "John 10:27"):
        assert len(anchor(on["s8"], "biblical", ref)) == 1
    assert anchor(on["s8"], "biblical", "1 Samuel 15:22")[0]["comment"].startswith("To obey is better than sacrifice")  # note added by CODE-AOID2-68 (step 172)
    assert "to obey is better than sacrifice" in anchor(on["s8"], "biblical", "1 Samuel 15:22")[0]["text"]
    assert "none other God but one" in anchor(on["s7"], "biblical", "1 Corinthians 8:1–4")[0]["text"]
    # switch off: the First Edition anchors, the 8:1-3 range and no Second Edition additions
    assert anchor(off["s7"], "biblical", "1 Corinthians 8:1–3") and not anchor(off["s7"], "biblical", "1 Corinthians 8:1–4")
    assert "none other God but one" not in anchor(off["s7"], "biblical", "1 Corinthians 8:1–3")[0]["text"]
    assert not anchor(off["s8"], "biblical", "1 Samuel 15:22")
    assert not keys_anywhere(on["s7"]) & {"ref_first_edition"} and not keys_anywhere(off["s7"]) & {"ref_first_edition"}
    assert not keys_anywhere(on["s8"]) & set(MARKERS) and not keys_anywhere(off["s8"]) & set(MARKERS)


def test_article_9_a9_f2_and_a9_f3_ledger_reads_the_recentred_floors_and_keeps_the_superseded_record():
    ledger = (REPO / "data-sources" / "aoid" / "floor_ledger.yaml").read_text(encoding="utf-8")
    doc = (REPO / "data-sources" / "aoid" / "floors" / "WoP_AOID2_A09_s6-s9_Floors_Draft_v1_20261017.md").read_text(encoding="utf-8").split(chr(10))
    for item, new in (("A9-F2", A9F2_NEW), ("A9-F3", A9F3_NEW)):
        block = ledger.split("- item: " + item + chr(10), 1)[1].split(chr(10) + "  - item:", 1)[0]
        assert "floor_amended: 2026-10-31" in block and "scored_on: null" in block
        assert "> " + new in doc
    assert any(l.startswith("> The Article confesses only what 1 Corinthians 8:1-3 and") for l in doc)
    assert any(l.startswith("> The Article confesses only what Luke 9:23, James 1:22") for l in doc)


# AOID2 step 172 (CODE-AOID2-68): Article 9 s8 and s30 approved commentary, Second Edition only. Expected text is copied from
# WoP_AOID2_Step110_A09_s8_s30_Commentary_20261031.md (APPROVED by Aaron 31 Oct 2026).
S8_NOTES = {'biblical': {'John 14:15': 'If ye love me, keep my commandments. In one sentence Christ joins the two spans: the love that s7 ranks first, and the keeping that s8 calls following. He does not set them against each other, and He does not let the one stand without the other.', '1 Samuel 15:22': 'To obey is better than sacrifice, and to hearken than the fat of rams. Saul spared the best of the flocks to offer them to the Lord (1 Samuel 15:15, 21): an offering correct in its form, made in place of the obedience asked of him. Samuel does not abolish sacrifice; he ranks it, as s8 ranks correct tenets beneath the following they serve. Read with James 1:22: the word is to be done, not only heard.', 'Luke 9:23': 'If any man will come after me, let him deny himself, and take up his cross daily, and follow me. This is Christ\'s own measure for the "following" of s8: not assent to a set of tenets, but a daily walk behind Him, with self set aside and the cross taken up.', 'James 1:22': 'But be ye doers of the word, and not hearers only, deceiving your own selves. To hear the word rightly and hold it soundly is desirable; James warns that hearing alone deceives the hearer. The "faithfully following" of s8 is the doing he asks for.', 'John 10:27': "My sheep hear my voice, and I know them, and they follow me. The Shepherd's own picture of s7 and s8 together: His sheep hear Him, He knows them, and they follow. Following is how His sheep are recognized, and it begins with hearing His voice.", 'Philippians 3:8': "I count all things but loss for the excellency of the knowledge of Christ Jesus my Lord. Paul, a Pharisee blameless as touching the law (Philippians 3:5-6), ranked all he had gained beneath knowing Christ. His word is stronger than s8's, which keeps correct tenets as desirable; but it shows where the gentler ranking points: the knowledge most worth having is of a Person."}, 'restoration': {'2 Nephi 31:10': 'And he said unto the children of men: Follow thou me. The invitation is given to every soul, and it names Christ, not a system, as the One to be followed. Nephi\'s next words join following to keeping: "can we follow Jesus save we shall be willing to keep the commandments of the Father?" The same joining John 14:15 makes.', '2 Nephi 25:26': "And we talk of Christ, we rejoice in Christ, we preach of Christ … that our children may know to what source they may look for a remission of their sins. Nephi's people kept the law of Moses (2 Nephi 25:24-25), yet they set Christ at the center of all their speech and teaching. The tenets kept, and Christ first: the order s8 names."}}
S8_NEW_ANCHORS = {'Matthew 7:16–20': ('biblical', "Ye shall know them by their fruits … Wherefore by their fruits ye shall know them. Spoken of false prophets (Matthew 7:15, cited at s13), the rule is applied here, as an illustrative reading, to doctrines: a doctrine's worth shows in its fruit, in whether it brings the disciple's heart into the likeness of Christ's, and whether it gathers His people into oneness or scatters them in schism. The test is applied evenly to every doctrine, beginning with our own."), 'John 16:12': ('biblical', 'I have yet many things to say unto you, but ye cannot bear them now. Christ Himself held back truths His disciples could not yet bear, weighing what a truth would do to those who heard it before He gave it. The worth of souls outranks the worth of doctrines: what a truth will do governs its timing and its use, never whether it is true.'), '1 Corinthians 3:1–2': ('biblical', 'I have fed you with milk, and not with meat: for hitherto ye were not able to bear it. Paul fed the Corinthians according to what they could bear, not according to all that he knew. With John 16:12, this is why correct tenets serve the following of Christ rather than rule it: a truth is given and used for the good of the soul who receives it.'), 'Titus 2:1, 7–8, 10': ('biblical', 'Speak thou the things which become sound doctrine … that they may adorn the doctrine of God our Saviour in all things. Paul does not hold doctrine cheap: he asks that it be sound, taught with integrity, and adorned by the life of the one who holds it. s8 keeps correct tenets as desirable for this reason, and Paul shows how they are honored: by a life that makes them beautiful. In verse 10 Paul writes to bondservants; his charge to adorn the doctrine is read here as the pattern it sets for every believer.'), 'D&C 18:10': ('restoration', 'Remember the worth of souls is great in the sight of God. This is the measure behind John 16:12 and 1 Corinthians 3:1-2: a truth is weighed by what it will do for the soul who receives it. The worth of souls outranks the worth of doctrines; it governs how a truth is given and used, never whether it is true.'), 'D&C 19:22': ('restoration', "For they cannot bear meat now, but milk they must receive. The Lord, instructing Martin Harris in what to preach, withheld some things lest the hearers perish. The same order as 1 Corinthians 3:1-2, given in the Lord's own voice.")}
S30_NOTES = {'Philippians 1:15–18': 'What then? notwithstanding, every way, whether in pretence, or in truth, Christ is preached; and I therein do rejoice. Paul did not commend the envy of those who preached against him, but he rejoiced that Christ was preached. s30 opens with the same joy: whatever first turned a soul toward Christ, the turning is cause for rejoicing.', 'Mark 9:38–40': "Forbid him not … For he that is not against us is on our part. The man followed not with the disciples, yet Christ would not let them stop him. Differences over who walks with whom are no warrant for forbidding one another. Christ's next words warn whoever causes one of His little ones to stumble (Mark 9:42).", 'John 17:20–23': 'That they all may be one; as thou, Father, art in me, and I in thee, that they also may be one in us. Christ prayed for all who would believe on Him through the apostles\' word, that the world may believe. s30 is offered as a place to gather toward that prayer. The oneness He asks is "in us"; how, or whether, the traditions should be joined is not settled here.', '1 Corinthians 1:10–13': 'Every one of you saith, I am of Paul; and I of Apollos; and I of Cephas; and I of Christ. Is Christ divided? Paul pleads for one mind; s30 does not claim it has been reached ("we may differ"). What it takes from him is his question. No messenger, and no instrument we carry, may stand where Christ stands.', 'Matthew 11:28': 'Come unto me, all ye that labour and are heavy laden, and I will give you rest. The invitation is to a Person. s30\'s "come unto Jesus of Nazareth" repeats it; every instrument, this Article included, serves that invitation and cannot take its place.', 'Matthew 7:7': 'Ask, and it shall be given you; seek, and ye shall find. The promise belongs to the seeker. s30 rejoices that you seek Him, and trusts His promise, not any instrument, to bring the seeker to Him.', '2 Nephi 26:33': 'He inviteth them all to come unto him … and he denieth none that come unto him. If the Lord denies none who come, no disciple may deny another who is coming. "Whatever first turned you toward Christ" rests here.', '3 Nephi 11:29': 'He that hath the spirit of contention is not of me, but is of the devil. The risen Christ spoke this just after forbidding disputations "concerning the points of my doctrine" (3 Nephi 11:28). Contention over doctrine, and the contempt it breeds, is the sign that an instrument has turned us from Him: the lost bearing s30 names.', 'Moroni 10:32': "Yea, come unto Christ, and be perfected in him. Moroni's last invitation is s30's: come unto Christ. The perfecting is in Him, by His grace; no instrument we carry can stand in for Him."}
S8_XREF_ADDED = [('Span 13: When the inward whisper points us away from what Christ taught and what Christ was, we know the compass has been disturbed, and we return our sighting to Him', '#s13'), ('Span 30: Whatever first turned you toward Christ, we rejoice that you seek Him', '#s30')]
S30_XREF = [('Span 13: When the inward whisper points us away from what Christ taught and what Christ was, we know the compass has been disturbed, and we return our sighting to Him', '#s13'), ("Span 19: the disciple’s walk does not require the approval of any person, tradition, or institution beyond the approval of Christ Himself, who is the only righteous and eternal Judge of human souls", '#s19'), ('Span 8: Correct tenets and sound understanding are desirable, but faithfully following Christ is better', '#s8')]
S8_INS1 = ' Samuel set the same order before Saul: "to obey is better than sacrifice" (1 Samuel 15:22).'
S8_INS2 = 'Doctrine is not idle in this ranking: it is to be adorned by the life (Titus 2:10), known by its fruit (Matthew 7:16-20), and given as souls can bear it (John 16:12; 1 Corinthians 3:2). '
S6_S7_SECOND = ("Span 6: Trusting Him as our Guide is more important than understanding Him", "Span 7: Personal relationship with the Divine takes precedence over accuracy of doctrine")
S6_S7_FIRST = ("Span 6: Trusting Him is more important than understanding Him", "Span 7: One's relationship with the Divine takes precedence over the accuracy of their doctrine")


def test_article_9_s8_notes_and_new_anchors_appear_only_with_the_switch_on():
    on, off = shown(True)["A09"]["s8"], shown(False)["A09"]["s8"]
    for col, notes in S8_NOTES.items():
        for ref, note in notes.items():
            assert anchor(on, col, ref)[0]["comment"] == note, ref
    for ref, (col, note) in S8_NEW_ANCHORS.items():
        assert [a["comment"] for a in anchor(on, col, ref)] == [note], ref
        assert not anchor(off, col, ref), ref
    assert "sincerity, sound speech," in anchor(on, "biblical", "Titus 2:1, 7–8, 10")[0]["text"]
    # switch off: the existing anchors that exist in the First Edition keep their comments, no note is present
    off_text = json.dumps(off, ensure_ascii=False)
    for col, notes in S8_NOTES.items():
        for note in notes.values():
            assert note not in off_text
    for _, (_, note) in S8_NEW_ANCHORS.items():
        assert note not in off_text
    assert not keys_anywhere(on) & set(MARKERS) and not keys_anywhere(off) & set(MARKERS)


def test_article_9_s8_panel_comment_insertions_are_in_paragraph_two_second_edition_only():
    on, off = shown(True)["A09"]["s8"], shown(False)["A09"]["s8"]
    p_on, p_off = on["panel_comment"].split(chr(10) * 2), off["panel_comment"].split(chr(10) * 2)
    assert p_on[0] == A9F3_NEW and len(p_on) == 2
    assert p_on[1].count(S8_INS1) == 1 and p_on[1].count(S8_INS2) == 1
    assert '(Luke 9:23).' + S8_INS1 + ' His sheep' in p_on[1]
    assert S8_INS2 + '"Faithfully" keeps faith inside the following' in p_on[1]
    # taking both insertions out gives the paragraph as it stood
    assert p_on[1].replace(S8_INS1, "").replace(S8_INS2, "") == DATA["A09"]["s8"]["panel_comment"].split(chr(10) * 2)[1].replace(S8_INS1, "").replace(S8_INS2, "")
    assert off["panel_comment"] == DATA["A09"]["s8"]["panel_comment_first_edition"]
    assert S8_INS1 not in off["panel_comment"] and S8_INS2 not in off["panel_comment"]


def test_article_9_s8_cross_references_switch_on_and_off():
    on, off = shown(True)["A09"]["s8"]["crossref"], shown(False)["A09"]["s8"]["crossref"]
    assert [c["title"] for c in on[:2]] == list(S6_S7_SECOND) and [c["href"] for c in on[:2]] == ["#s6", "#s7"]
    assert [(c["title"], c["href"]) for c in on[2:]] == S8_XREF_ADDED
    assert [c["title"] for c in off] == list(S6_S7_FIRST) and [c["href"] for c in off] == ["#s6", "#s7"]
    assert "#s13" not in [c["href"] for c in off] and "#s30" not in [c["href"] for c in off]
    for c in on + off:
        assert set(c) == {"label", "title", "href"}, c


def test_article_9_s30_notes_cross_references_and_clean_text_fields():
    on, off = shown(True)["A09"], shown(False)["A09"]
    assert "s30" not in off
    s = on["s30"]
    assert [(c["title"], c["href"]) for c in s["crossref"]] == S30_XREF
    assert all(set(c) == {"label", "title", "href"} for c in s["crossref"])
    for col in ("biblical", "restoration"):
        for a in s[col]:
            assert a["comment"] == S30_NOTES[a["ref"]], a["ref"]
            assert not a["text"].startswith("¶") and "¶" not in a["text"], a["ref"]
    assert s["panel_comment"] == S30_FLOOR
