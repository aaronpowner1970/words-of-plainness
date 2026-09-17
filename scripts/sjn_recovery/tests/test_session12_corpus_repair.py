"""Session 12, phase 3 (Codex F.10): the chunker repairs and the relocation of stored candidates onto re-chunked text.

  3a BSR-RC-07  Part Four's split bold number/question and the Appendix
  3b BSR-AN-04  the Outline ends at the "Historical Documents of the Church" title page; what follows is chunked as what it is
  3c BSR-AN-05  the drafting guidelines never take question numbers; front matter is its own chunk and is guarded
  3d BSR-RP-05  the CRC editorial notes are held out of the Q&A text and guarded
  3e BSR-LU-01  the Small Catechism pages' forcespan text is read whole
  packets.relocate  a candidate follows the chunk-id mapping to the chunk that now carries its phrase

Synthetic inputs throughout; the registry tests skip without the workbook."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sjn_recovery import sources, rulings, packets  # noqa: E402
from sjn_recovery.registry import Registry, bare_tier, SECOND_TIER  # noqa: E402


class _Fetcher:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        html = self.pages.get(url, "")

        class FR:
            ok = bool(html); status = 200 if html else 404; error = "" if html else "missing"; final_url = url
            redirects = []; cross_host_redirect = ""; content_type = "text/html"
        FR.html = html
        return FR()


def _ctx(row, pages=None, pdf_text=None):
    ctx = sources.Ctx(dict({"branch": "X", "standard_title": "T", "authority_tier": "CATECHETICAL", "scope_caveat": "",
                            "reception_scope": "JURISDICTIONAL", "canonical_url": "https://example.org/doc"}, **row),
                      _Fetcher(pages or {}), log=lambda m: None, admitted_hosts=None)
    if pdf_text is not None:
        ctx.pdf = lambda url: pdf_text
    return ctx


@pytest.fixture(scope="module")
def reg():
    try:
        return Registry()
    except Exception as e:
        pytest.skip(f"registry unavailable: {e}")


# ---------------------------------------------------------------- 3a
COMPENDIUM = "https://www.vatican.va/archive/compendium_ccc/documents/archive_2005_compendium-ccc_en.html"


def test_compendium_reads_split_bold_questions_and_chunks_the_appendix():
    html = ("<html><body><a href='#APPENDIX'>APPENDIX</a>"
            "<p><b>1. What is the first question?</b></p><p>12-13</p><p>First answer.</p>"
            "<p><b>Part Four</b></p><p><b>2.</b>&nbsp;<b>What is prayer?</b></p><p>2558</p><p>Prayer is the raising of the mind.</p>"
            "<p><b>3</b>.<b>What are the expressions?</b></p><p>Three forms.</p>"
            "<table><tbody><tr><td colspan='2'><p><b><a name='APPENDIX'>APPENDIX</a></b></p><p><b><a name='A'>A) COMMON PRAYERS</a></b></p></td></tr>"
            "<tr><td width='50%'><b>The Sign of the Cross</b><p>In the name of the Father</p></td>"
            "<td width='50%'><b>Signum Crucis</b><p>In nomine Patris</p></td></tr></tbody></table>"
            "<p><b><a name='B'>B) FORMULAS OF CATHOLIC DOCTRINE</a></b></p><p><b>The Golden Rule (</b><i>Matthew</i><b>7:12):</b></p>"
            "<p>Do to others as you would have them do to you.</p><p><b>The four last things:</b></p><p>1. Death<br/>2. Judgment</p>"
            "</body></html>")
    out, notes = sources.compendium(_ctx({"registry_id": "BSR-RC-07"}, {COMPENDIUM: html}))
    by = {c["locator"]: c for c in out}
    assert by["Compendium Q.1"]["text"] == "1. What is the first question? First answer."            # Part One-Three shape unchanged
    assert by["Compendium Q.2"]["text"] == "2. What is prayer? Prayer is the raising of the mind."    # "<b>2.</b> <b>Q</b>"
    assert by["Compendium Q.3"]["text"] == "3. What are the expressions? Three forms."               # "<b>3</b>.<b>Q</b>"
    assert "Sign of the Cross" not in by["Compendium Q.3"]["text"]                                     # the Appendix no longer runs on
    assert by["Compendium Appendix A (Common Prayers) — The Sign of the Cross"]["language"] == "en"
    assert by["Compendium Appendix A (Common Prayers) — Signum Crucis (Latin)"]["language"] == "la"
    assert by["Compendium Appendix B (Formulas of Catholic Doctrine) — The Golden Rule (Matthew 7:12)"]["text"] == \
        "The Golden Rule (Matthew 7:12): Do to others as you would have them do to you."
    assert "Compendium Appendix B (Formulas of Catholic Doctrine) — The four last things" in by


# ---------------------------------------------------------------- 3b
def test_the_outline_ends_at_the_historical_documents_title_page():
    ff = "\f"
    pages = ["x"] * 3
    pages.append("An Outline of the Faith\ncommonly called the Catechism\nHuman Nature\nQ.\nWhat are we by nature?\nA.\nWe are part of God's creation.\n")
    pages.append("Q.\nWhat, then, is our assurance as Christians?\nA.\nOur assurance as Christians is that nothing shall separate us. Amen.\n")
    pages.append("Historical\nDocuments\nof the Church\n")
    pages.append("Definition of the Union of the Divine\nand Human Natures in the Person of Christ\nCouncil of Chalcedon, 451 A.D., Act V\n"
                 "Therefore, following the holy fathers, we all with one accord teach men to acknowledge one\nand the same Son.\n"
                 "Quicunque Vult\ncommonly called\nThe Creed of Saint Athanasius\n"
                 "Whosoever will be saved, before all things it is necessary that he hold the Catholic Faith.\n"
                 "The Father incomprehensible, the Son incomprehensible, and the Holy Ghost\nincomprehensible.\n")
    pages.append("Preface\nThe First Book of Common Prayer (1549)\nThere was never any thing.\n")
    out, notes = sources.tec_outline_of_faith(_ctx({"registry_id": "BSR-AN-04"}, pdf_text=ff.join(pages)))
    locs = [c["locator"] for c in out]
    last_q = next(c for c in out if "assurance as Christians" in c["locator"])
    assert last_q["locator"].startswith("Outline of the Faith (BCP p. 5)")
    assert last_q["text"].endswith("Amen.") and "Chalcedon" not in last_q["text"] and "Whosoever" not in last_q["text"]
    assert "Historical Documents of the Church (BCP p. 7) — Definition of the Union of the Divine and Human Natures in the Person of Christ " \
           "Council of Chalcedon, 451 A.D., Act V" in locs
    creed = next(c for c in out if c["locator"].startswith("Historical Documents of the Church (BCP p. 7) — Quicunque Vult"))
    assert "The Father incomprehensible, the Son incomprehensible, and the Holy Ghost incomprehensible." in creed["text"]
    assert not any("First Book of Common Prayer" in c["text"] for c in out)                          # nothing past the stored window


# ---------------------------------------------------------------- 3c
def test_acna_guidelines_are_front_matter_and_the_questions_keep_their_numbers():
    lines = ["Our guidelines in drafting have been as follows:", "1. Everything taught should be compatible with all schools,",
             "so that all may use it.", "2. Everything taught should be brief.", "introduction", "3. All the answers should be easy",
             "to remember.", "The Reverend Canon J. I. Packer", "part i", "b e g i n n i n g", "This catechism is designed to teach you.",
             "s a l va t i o n", "1.", "What is the human condition?", "Humanity has been cut off from God.", "2.", "What is the Gospel?",
             "The Gospel is the good news.", "3. How does sin affect you?", "Sin alienates me from God.", "4.", "What is the way of death?",
             "A life without God's love."]
    out, notes = sources.acna_to_be_a_christian(_ctx({"registry_id": "BSR-AN-05"}, pdf_text="\n".join(lines)))
    locs = [c["locator"] for c in out]
    assert locs[2:] == ["To Be a Christian, Q.1 — What is the human condition?", "To Be a Christian, Q.2 — What is the Gospel?",
                        "To Be a Christian, Q.3 — How does sin affect you?", "To Be a Christian, Q.4 — What is the way of death?"]
    front = out[:2]
    # session 13 (R6-46.1): only the chunk before "Part I" is front matter; Part I's introductory chunk is integral text
    assert front[0]["division"] == sources.ACNA_FRONT_MATTER and front[1]["division"] == sources.ACNA_PART_I_INTRO
    assert front[0]["text"].startswith("1. Everything taught") and "Packer" in front[0]["text"]
    assert front[1]["text"].startswith("part i") and "Humanity" not in front[1]["text"]
    assert "front matter" not in front[1]["locator"]


def test_the_an05_guard_takes_front_matter_to_official_exposition_and_never_a_question(reg):
    assert rulings.adoption_guards()["BSR-AN-05"]["ruling"] == "R6-36_an05_adoption"
    front = {"text": "1. Everything taught should be compatible with all schools.", "locator": "To Be a Christian, front matter — introduction",
             "division": sources.ACNA_FRONT_MATTER}
    q = {"text": "What is the human condition? Humanity has been cut off from God.", "locator": "To Be a Christian, Q.1 — What is the human condition?",
         "division": "question"}
    assert reg.apparatus_guard("BSR-AN-05", front)
    assert bare_tier(reg.effective_tier("BSR-AN-05", front, "Everything taught should be compatible")) == SECOND_TIER
    assert reg.apparatus_guard("BSR-AN-05", q) is None
    assert reg.effective_tier("BSR-AN-05", q, "Humanity has been cut off from God") == "CATECHETICAL"
    part_i = {"text": "part i b e g i n n i n g This catechism is designed to teach you.", "division": sources.ACNA_PART_I_INTRO,
              "locator": "To Be a Christian, Part I, Beginning with Christ — introductory matter before Q.1"}
    assert reg.apparatus_guard("BSR-AN-05", part_i) is None                       # session 13, R6-46.1: integral, never guarded
    from sjn_recovery import store
    for c in store.load_chunks("BSR-AN-05"):
        assert bool(reg.apparatus_guard("BSR-AN-05", c)) == (c["division"] == sources.ACNA_FRONT_MATTER), c["locator"]


# ---------------------------------------------------------------- 3d
def test_heidelberg_editorial_notes_are_their_own_guarded_chunks(reg):
    html = ("<html><body><h4>Lord’s Day 29</h4><div>Q &amp; A 79</div><p>Q. Why then does Christ call the bread his body?</p>"
            "<p>A. Christ has good reason for these words.</p><h4>Lord’s Day 30</h4><div>Q &amp; A 80*</div>"
            "<p>Q. How does the Lord’s Supper differ from the Mass?</p><p>A. The Lord’s Supper declares to us.</p><p>[But the Mass teaches.]**</p>"
            "<p>*Q&amp;A 80 was altogether absent from the first edition.</p><p>**In response to a mandate from Synod 1998, a study.</p>"
            "<p>The Reformed Church in America retains the original full text.</p>"
            "<div>Q &amp; A 81</div><p>Q. Who should come to the Lord’s table?</p></body></html>")
    url = "https://www.crcna.org/welcome/beliefs/confessions/heidelberg-catechism"
    out, _ = sources.heidelberg_crcna(_ctx({"registry_id": "BSR-RP-05", "canonical_url": url}, {url: html}))
    by = {c["locator"]: c for c in out}
    assert list(by) == ["Q&A 79 (Lord’s Day 29)", "Q&A 80 (Lord’s Day 30)", "Q&A 80 (Lord’s Day 30) — CRC editorial note(s)", "Q&A 81 (Lord’s Day 30)"]
    assert by["Q&A 80 (Lord’s Day 30)"]["text"].endswith("[But the Mass teaches.]**")
    note = by["Q&A 80 (Lord’s Day 30) — CRC editorial note(s)"]
    assert note["division"] == sources.CRC_EDITORIAL_NOTE and "Reformed Church in America retains" in note["text"]
    assert reg.apparatus_guard("BSR-RP-05", note)
    assert bare_tier(reg.effective_tier("BSR-RP-05", note, "altogether absent from the first edition")) == SECOND_TIER
    assert reg.apparatus_guard("BSR-RP-05", by["Q&A 80 (Lord’s Day 30)"]) is None
    assert bare_tier(reg.effective_tier("BSR-RP-05", by["Q&A 80 (Lord’s Day 30)"], "The Lord’s Supper declares to us")) == "CONFESSIONAL"


# ---------------------------------------------------------------- 3e
def test_book_of_concord_forcespan_pages_keep_the_catechism_text():
    html = ("<html><body><div id='main-content'><main><div class='next-previous-box'><a>&lt;&lt; I. Ten Commandments</a></div>"
            "<h2>II. The Creed</h2><h4>As the head of the family should teach it in a simple way to his household.</h4>"
            "<h4><strong><span class='bocanchor'><span class='bocanchor-content'>1</span></span><span class='forcespan'>The First Article.</span></strong></h4>"
            "<p><em>Of Creation</em>.</p>"
            "<h4><span class='bocanchor'><span class='bocanchor-content'>1b</span></span><span class='forcespan'>I believe in God the Father Almighty, Maker of heaven and earth.</span></h4>"
            "<p><em>What does this mean?</em></p>"
            "<p>&ndash;Answer: <span class='bocanchor'><span class='bocanchor-content'>1c</span></span><span class='forcespan'>I believe that\nGod has made me and all creatures.</span></p>"
            "<h4><strong><span class='bocanchor'><span class='bocanchor-content'>2</span></span><span class='forcespan'>The Second Article.</span></strong></h4>"
            "<p>&ndash;Answer: <span class='bocanchor'><span class='bocanchor-content'>2c</span></span><span class='forcespan'>I believe that Jesus Christ is my Lord.</span></p>"
            "<div class='next-previous-box'><a>III. The Lord's Prayer &gt;&gt;</a></div></main></div></body></html>")
    paras = sources._boc_forcespan_paras(html)
    assert paras[0] == (1, "As the head of the family should teach it in a simple way to his household.")   # the rubric is kept
    assert (None, "I believe in God the Father Almighty, Maker of heaven and earth.") in paras                # "1b" continues ¶1
    assert (None, "–Answer: I believe that God has made me and all creatures.") in paras
    assert (2, "The Second Article.") in paras
    assert not any("<<" in t or ">>" in t or t == "II. The Creed" for _, t in paras)


# ---------------------------------------------------------------- relocation
def test_a_candidate_follows_the_mapping_only_to_a_chunk_that_carries_its_phrase():
    old_loc, new_loc = "Outline (p. 862) — Q. assurance", "Historical Documents (p. 864) — Quicunque Vult"
    idx = {("BSR-AN-04", old_loc): {"text": "Our assurance is that nothing shall separate us. Amen.", "locator": old_loc},
           ("BSR-AN-04", new_loc): {"text": "The Father incomprehensible, the Son incomprehensible.", "locator": new_loc}}
    moves = {("BSR-AN-04", old_loc): {"new_locators": [old_loc, new_loc], "rule": "TEXT_CHANGED", "mapping_file": "m.json"}}
    cand = {"registry_id": "BSR-AN-04", "locator": old_loc, "phrase": "The Father incomprehensible, the Son incomprehensible"}
    chunk, rel = packets.relocate(cand, idx, moves)
    assert chunk["locator"] == new_loc and rel["locator_at_run"] == old_loc and rel["locator_now"] == new_loc
    stays = dict(cand, phrase="nothing shall separate us")
    chunk, rel = packets.relocate(stays, idx, moves)
    assert chunk["locator"] == old_loc and rel is None
    lost = dict(cand, phrase="a phrase in neither chunk")
    chunk, rel = packets.relocate(lost, idx, moves)
    assert chunk["locator"] == old_loc and rel is None                     # never repaired: the build re-assertion then drops it
    unmapped = dict(cand, registry_id="BSR-AN-03")
    assert packets.relocate(unmapped, idx, moves) == (None, None)
