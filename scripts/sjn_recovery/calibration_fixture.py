"""Planted near-miss fixture builder (spec §6).

Each item names a registry standard, a locator pattern, a predicate family, a verbatim phrase (≤15 words)
and the reason it is a NEAR-MISS: the word or idea is present but the passage does not assert the
predicate of the required subject in the standard's own voice. Types:

  OPPONENT_QUOTATION       a view the standard reports in order to reject it
  CHRISTOLOGICAL_HUMAN     a statement about Christ's human nature / body / suffering
  CHURCH_PREDICATE         the predicate is asserted of the Church, sacraments or ministers
  SCRIPTURE_PREDICATE      the predicate is asserted of Scripture
  CREATURE_PREDICATE       the predicate is asserted of humanity, saints, angels, the elect
  SAME_WORD_DIFFERENT_SENSE the word appears in a different sense (justify, true = genuine, present)
  TITLE_ONLY               the word appears only inside a title ("Holy Trinity", "All-holy Spirit")

The builder resolves each locator against the built corpus and asserts the phrase verbatim (guards.py)
before the item is admitted. Output: data-sources/sjn/recovery-runs/calibration/planted-near-misses.json.
Authored by the Gate 6 build session (Claude Code) from the corpus text; every item is auditable
against its chunk. Nothing here writes to the workbook."""
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sjn_recovery.config import CALIBRATION_DIR, ensure_dirs  # noqa: E402
from sjn_recovery import store, guards  # noqa: E402

D = "BSR-EO-05"
ITEMS = [
    # ---------------- Dositheus (its own slice: condemnations of Cyril Lucaris's positions; Church/saints predicates)
    (D, r"^Decree 3$", "RNR-H26", "God, in predestinating, or condemning, had in no wise regard to the works", "OPPONENT_QUOTATION",
     "Reported as what 'the most wicked heretics' say; the decree calls it profane and impious."),
    (D, r"^Decree 3$", "RNR-H11", "the Divine Will is thus solely and without cause the author of their condemnation", "OPPONENT_QUOTATION",
     "A rejected claim posed inside a rhetorical question ('what greater calumny')."),
    (D, r"^Decree 14$", "RNR-H44", "to have fallen from his perfection and impassibility", "CREATURE_PREDICATE",
     "Impassibility is predicated of unfallen man, not of God."),
    (D, r"^Decree 15$", "RNR-H12", "hallowed by the invocation of the Holy Spirit", "CHURCH_PREDICATE",
     "The sacrament is hallowed; holiness is not predicated of God here."),
    (D, r"^Decree 17$", "RNR-H43", "are severed and divided by the hands and teeth, though in accident only", "CHRISTOLOGICAL_HUMAN",
     "About the eucharistic Body under the accidents of bread; not divine simplicity."),
    (D, r"^Decree 17$", "RNR-H43", "there is not a part of the Body and Blood of the Lord", "CHRISTOLOGICAL_HUMAN",
     "'Not a part' concerns the sacramental Body, not God being without parts."),
    (D, r"^Decree 17$", "RNR-H02", "it is one and the same Christ that is truly and really present", "SAME_WORD_DIFFERENT_SENSE",
     "'Truly present' is about eucharistic presence, not God's truth or faithfulness."),
    (D, r"^Decree 16$", "RNR-H46", "are, of necessity, subject to eternal punishment", "CREATURE_PREDICATE",
     "Eternal is predicated of punishment of the unregenerate, not of God."),
    (D, r"^Decree 2$", "RNR-H13", "it is impossible for her to in any wise err", "CHURCH_PREDICATE",
     "Infallibility is predicated of the Church ('her')."),
    (D, r"^Decree 2$", "RNR-H02", "or to at all deceive, or be deceived", "CHURCH_PREDICATE",
     "Truthfulness predicated of the Church, not of God."),
    (D, r"^Decree 10$", "RNR-H33", "is a living image of God upon the earth", "CHURCH_PREDICATE",
     "The Bishop is called a living image of God; the family concerns the Son as image of the Father."),
    (D, r"^Decree 10$", "RNR-H29", "the fountain of the Divine Mysteries and graces", "CHURCH_PREDICATE",
     "The High Priest is the fountain of the Mysteries; not God as fountain of being."),
    (D, r"^Decree 10$", "RNR-H32", "there remaineth in them neither understanding nor light, but only darkness and blindness", "CREATURE_PREDICATE",
     "Light is denied of heretics; nothing is predicated of the Son as Light."),
    (D, r"^Decree 11$", "RNR-H26", "they could not be judged by the Church", "CHURCH_PREDICATE",
     "The Church judges; the family is God as Judge."),
    (D, r"^Decree 13$", "RNR-H11", "the faith which is in us, justifieth through works, with Christ", "SAME_WORD_DIFFERENT_SENSE",
     "'Justifieth' is soteriological (faith justifies), not the justice of God."),
    (D, r"^Decree 9$", "RNR-H11", "by [observing] the Divine commandments, justifieth us with Christ", "SAME_WORD_DIFFERENT_SENSE",
     "Faith working by love justifies; not a predicate of God."),
    (D, r"^Decree 17$", "RNR-H41", "under which they are visible and tangible", "CHRISTOLOGICAL_HUMAN",
     "The accidents of bread and wine are visible; not a statement about God's invisibility."),
    (D, r"^Question 4$", "RNR-H12", "of the most holy Theotokos, and of all the saints, also of the holy Angels", "CREATURE_PREDICATE",
     "Holy is predicated of the Theotokos, saints and angels."),
    (D, r"^Decree 16$", "RNR-H12", "conferred in the name of the Holy Trinity", "TITLE_ONLY",
     "'Holy' appears only inside the title 'Holy Trinity'; nothing is asserted about holiness."),
    (D, r"^Decree 16$", "RNR-H02", "then remission of sin throuhgh the Spirit is true also", "SAME_WORD_DIFFERENT_SENSE",
     "'True' = real/valid, predicated of remission of sin (source spelling preserved)."),
    (D, r"^Decree 10$", "RNR-H12", "by the imposition of hands and the invocation of the All-holy Spirit", "TITLE_ONLY",
     "'All-holy' is a fixed title of the Spirit inside a description of ordination; not an assertion of the predicate."),
    (D, r"^Decree 16$", "RNR-H46", "it delivereth him from the eternal punishment, to which he was liable", "CREATURE_PREDICATE",
     "Baptism delivers from eternal punishment; eternity is not predicated of God."),
    (D, r"^Decree 4$", "RNR-H41", "the invisible are the angelic powers, rational souls, and demons", "CREATURE_PREDICATE",
     "Invisibility is predicated of angels, souls and demons, not of God."),
    # ---------------- Lutheran (Formula of Concord catalogues of rejected doctrines; Augsburg condemnations; Apology)
    ("BSR-LU-01", r"Epitome: XII\. Other Sects, ¶25", "RNR-H02", "That Christ is not true, essential, natural God", "OPPONENT_QUOTATION",
     "A New Arian error listed in order to be condemned."),
    ("BSR-LU-01", r"Epitome: XII\. Other Sects, ¶25", "RNR-H46", "there is not one only, eternal, divine essence of the Father Son, and Holy Ghost", "OPPONENT_QUOTATION",
     "Anti-Trinitarian error listed for condemnation; eternal essence is denied by the opponent, not asserted."),
    ("BSR-LU-01", r"Epitome: XII\. Other Sects, ¶25", "RNR-H07", "all three of equal power, wisdom, majesty, and glory", "OPPONENT_QUOTATION",
     "Part of the reported Anti-Trinitarian view (three separate essences of equal power); not the standard's assertion."),
    ("BSR-LU-01", r"Solid Declaration: XII\. Other Sects", "RNR-H02", "That the Father alone is true God.", "OPPONENT_QUOTATION",
     "Listed Anti-Trinitarian error; the standard rejects it."),
    ("BSR-LU-01", r"Solid Declaration: XII\. Other Sects", "RNR-H12", "are holy and the children of God even without and before Baptism", "OPPONENT_QUOTATION",
     "Anabaptist error about children; holiness predicated of children in a rejected view."),
    ("BSR-LU-01", r"Solid Declaration: XII\. Other Sects", "RNR-H38", "regard Christ according to the flesh, or His assumed humanity, as a creature", "OPPONENT_QUOTATION",
     "Schwenckfeldian error reported; 'creature' concerns Christ's flesh in a condemned view."),
    ("BSR-LU-01", r"Epitome: XII\. Other Sects, ¶1", "RNR-H02", "That Christ is not true God", "OPPONENT_QUOTATION",
     "Anabaptist error listed for condemnation."),
    ("BSR-LU-01", r"Augsburg Confession: Article I\. Of God", "RNR-H09", "the Manichaeans, who assumed two principles, one Good and the other Evil", "OPPONENT_QUOTATION",
     "Manichaean view condemned; 'Good' is a rejected principle, not a predicate of God asserted here."),
    ("BSR-LU-01", r"Augsburg Confession: Article I\. Of God", "RNR-H30", "“Word” signifies a spoken word", "OPPONENT_QUOTATION",
     "Samosatene view condemned; the standard denies this reading of 'Word'."),
    ("BSR-LU-01", r"Augsburg Confession: Article III\. Of the Son of God", "RNR-H42", "did assume the human nature in the womb of the blessed Virgin Mary", "CHRISTOLOGICAL_HUMAN",
     "The incarnation of the Son in a body says nothing about God being without body."),
    ("BSR-LU-01", r"Apology of the Augsburg Confession: Article II", "RNR-H46", "no one is condemned to eternal death on account of original sin", "OPPONENT_QUOTATION",
     "The adversaries' claim, reported to be refuted; eternal death is not a predicate of God."),
    ("BSR-LU-01", r"Augsburg Confession: Article II\. Of Original Sin", "RNR-H46", "bringing eternal death upon those not born again through Baptism", "CREATURE_PREDICATE",
     "Eternal is predicated of death/punishment, not of God."),
    ("BSR-LU-01", r"Apology of the Augsburg Confession: Article IV-b", "RNR-H26", "the Law condemns all men", "SAME_WORD_DIFFERENT_SENSE",
     "The Law condemns; God as Judge is not the subject."),
    # ---------------- Roman Catholic (Catechism: Church marks; Christ's humanity; 'true God' as genuineness)
    ("BSR-RC-01", r"^CCC 811$", "RNR-H12", "we profess to be one, holy, catholic and apostolic", "CHURCH_PREDICATE",
     "Holy is a mark of the Church."),
    ("BSR-RC-01", r"^CCC 823$", "RNR-H12", "is held, as a matter of faith, to be unfailingly holy", "CHURCH_PREDICATE",
     "The Church is unfailingly holy; not a predicate of God."),
    ("BSR-RC-01", r"^CCC 464$", "RNR-H02", "Jesus Christ is true God and true man", "SAME_WORD_DIFFERENT_SENSE",
     "'True God' = genuinely God (Christological), not God's truthfulness/authenticity as the family defines it."),
    ("BSR-RC-01", r"^CCC 467$", "RNR-H42", "composed of rational soul and body", "CHRISTOLOGICAL_HUMAN",
     "Chalcedon on Christ's humanity; nothing about God being incorporeal."),
    ("BSR-RC-01", r"^CCC 472$", "RNR-H08", "is endowed with a true human knowledge", "CHRISTOLOGICAL_HUMAN",
     "Christ's human soul's knowledge; not divine wisdom."),
    ("BSR-RC-01", r"^CCC 824$", "RNR-H12", "United with Christ, the Church is sanctified by him", "CHURCH_PREDICATE",
     "Holiness of the Church."),
    # ---------------- Anglican
    ("BSR-AN-01", r"Article XXVIII", "RNR-H03", "only after an heavenly and spiritual manner", "SAME_WORD_DIFFERENT_SENSE",
     "'Spiritual manner' of receiving the Body of Christ; not God named as spirit."),
    ("BSR-AN-01", r"Article II \(2\)", "RNR-H44", "who truly suffered, was crucified, dead, and buried", "CHRISTOLOGICAL_HUMAN",
     "Christ's suffering in his manhood; not a statement that God is without passions."),
    ("BSR-AN-04", r"BCP p\. 854.*Why is the Church described as holy", "RNR-H12", "The Church is holy, because the Holy Spirit dwells in it", "CHURCH_PREDICATE",
     "Holiness predicated of the Church."),
    ("BSR-AN-04", r"BCP p\. 845.*What are we by nature", "RNR-H33", "We are part of God’s creation, made in the image of God", "CREATURE_PREDICATE",
     "Humanity in God's image; the family concerns the Son as image of the Father."),
    ("BSR-AN-02", r"Rehearse the Articles", "RNR-H12", "The holy Catholick Church", "CHURCH_PREDICATE",
     "Creed clause about the Church."),
    # ---------------- Reformed / Presbyterian
    ("BSR-RP-06", r"^Article 27:", "RNR-H12", "a holy congregation and gathering of true Christian believers", "CHURCH_PREDICATE",
     "Holy is predicated of the Church."),
    ("BSR-RP-06", r"^Article 19:", "RNR-H42", "retains all that belongs to a real body", "CHRISTOLOGICAL_HUMAN",
     "Christ's human nature has a real body; nothing about God without body."),
    ("BSR-RP-06", r"^Article 29:", "RNR-H02", "what is the true church", "SAME_WORD_DIFFERENT_SENSE",
     "'True church' — genuineness of the Church, not God's truth."),
    ("BSR-RP-05", r"^Q&A 54 ", "RNR-H46", "preserves for himself a community chosen for eternal life and united in true faith", "CREATURE_PREDICATE",
     "Eternal life of the elect; eternity is not predicated of God."),
    ("BSR-RP-01", r"^Chapter 4\.2 ", "RNR-H12", "endued with knowledge, righteousness, and true holiness, after his own image", "CREATURE_PREDICATE",
     "Holiness of created humanity."),
    ("BSR-RP-01", r"^Chapter 4\.2 ", "RNR-H45", "which was subject unto change", "CREATURE_PREDICATE",
     "Man's will subject to change; the opposite pole of immutability, predicated of man."),
    ("BSR-RP-01", r"^Chapter 25\.1 ", "RNR-H41", "The catholic or universal church, which is invisible", "CHURCH_PREDICATE",
     "Invisibility predicated of the invisible church."),
    ("BSR-RP-01", r"^Chapter 8\.2 ", "RNR-H44", "with all the essential properties, and common infirmities thereof", "CHRISTOLOGICAL_HUMAN",
     "Christ's assumed human nature with its infirmities; not divine impassibility."),
    ("BSR-RP-06", r"^Article 27:", "RNR-H50", "this holy church is not confined, bound, or limited to a certain place", "CHURCH_PREDICATE",
     "Non-circumscription predicated of the Church, not of God."),
    # ---------------- Baptist
    ("BSR-BA-01", r"^I\. The Scriptures$", "RNR-H02", "all Scripture is totally true and trustworthy", "SCRIPTURE_PREDICATE",
     "Truth predicated of Scripture."),
    ("BSR-BA-01", r"^I\. The Scriptures$", "RNR-H13", "truth, without any mixture of error, for its matter", "SCRIPTURE_PREDICATE",
     "Truthfulness predicated of the Bible."),
    ("BSR-BA-01", r"^III\. Man$", "RNR-H33", "Man is the special creation of God, made in His own image", "CREATURE_PREDICATE",
     "Image predicated of man."),
    ("BSR-BA-01", r"^III\. Man$", "RNR-H12", "bring man into His holy fellowship", "TITLE_ONLY",
     "'Holy fellowship' is a descriptor of fellowship; holiness is not asserted of God as a proposition."),
    ("BSR-BA-03", r"^Fact 1$", "RNR-H30", "the Bible is the divinely inspired word of God", "SAME_WORD_DIFFERENT_SENSE",
     "'Word of God' names Scripture, not the Son as Logos."),
    # ---------------- Methodist / Wesleyan
    ("BSR-MW-01", r"^Article II ", "RNR-H44", "who truly suffered, was crucified, dead, and buried", "CHRISTOLOGICAL_HUMAN",
     "Christ suffered in his manhood; not divine impassibility."),
    ("BSR-MW-01", r"^Article III ", "RNR-H42", "took again his body, with all things appertaining to the perfection of man's nature", "CHRISTOLOGICAL_HUMAN",
     "Christ's risen body; nothing about God being without body."),
    ("BSR-MW-02", r"^Article V ", "RNR-H12", "We believe it is one, holy, apostolic and catholic", "CHURCH_PREDICATE",
     "Marks of the Church."),
    ("BSR-MW-02", r"^Article XII ", "RNR-H46", "the righteous to life eternal and the wicked to endless condemnation", "CREATURE_PREDICATE",
     "Eternal life/condemnation of people."),
    # ---------------- Mennonite / Anabaptist
    ("BSR-MA-01", r"^Article 6\.", "RNR-H33", "We believe that God has created human beings in the divine image", "CREATURE_PREDICATE",
     "Image predicated of human beings; the family concerns the Son."),
    ("BSR-MA-01", r"^Article 6\.", "RNR-H09", "human beings were created good, in the image of God", "CREATURE_PREDICATE",
     "Goodness predicated of created humanity."),
    ("BSR-MA-01", r"^Article 9\.", "RNR-H33", "The church, the body of Christ, is called to become ever more like Jesus Christ", "CHURCH_PREDICATE",
     "Likeness to Christ predicated of the church."),
    # ---------------- Eastern Orthodox (non-Dositheus)
    ("BSR-EO-04", r"^Q\.269 ", "RNR-H12", "hinder not the Church from being holy", "CHURCH_PREDICATE",
     "Holiness of the Church."),
    ("BSR-EO-04", r"^Q\.271 ", "RNR-H13", "the Catholic Church can not sin, nor err, nor utter falsehood in place of truth", "CHURCH_PREDICATE",
     "Infallibility/truthfulness of the Church."),
    ("BSR-EO-04", r"^Q\.254 ", "RNR-H41", "is at the same time invisible, so far as she is also partially in heaven", "CHURCH_PREDICATE",
     "Invisibility of the Church."),
    ("BSR-EO-01", r'"Church"$', "RNR-H12", "In one, holy, catholic and apostolic Church", "CHURCH_PREDICATE",
     "Creed clause about the Church."),
    ("BSR-EO-01", r'"Man"$', "RNR-H33", "created in the image and likeness of God", "CREATURE_PREDICATE",
     "Image predicated of man."),
    ("BSR-EO-06", r"Fourth Ecumenical", "RNR-H42", "becoming a real man in every way, but without sin", "CHRISTOLOGICAL_HUMAN",
     "Christ's real humanity; nothing about God being incorporeal."),
]


def build():
    ensure_dirs()
    items, failures = [], []
    cache = {}
    for n, (rid, loc_re, fam, phrase, typ, why) in enumerate(ITEMS, 1):
        if rid not in cache:
            cache[rid] = store.load_chunks(rid)
        matches = [c for c in cache[rid] if re.search(loc_re, c["locator"])]
        hit = None
        for c in matches:
            ok, _ = guards.check_phrase(phrase, c["text"])
            if ok:
                hit = c; break
        if not hit:
            failures.append((n, rid, loc_re, phrase[:60], f"{len(matches)} locator matches, phrase not verbatim in any"))
            continue
        items.append({"id": f"PNM-{n:03d}", "registry_id": rid, "branch": hit["branch"], "locator": hit["locator"], "family_id": fam,
                      "phrase": phrase, "type": typ, "why": why, "floor_claim": "FULL", "chunk_hash": hit["text_hash"]})
    out = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "items": items,
           "authoring": "Hand-authored from corpus text by the Gate 6 build session; each phrase re-asserted verbatim against its chunk at build.",
           "types": ["OPPONENT_QUOTATION", "CHRISTOLOGICAL_HUMAN", "CHURCH_PREDICATE", "SCRIPTURE_PREDICATE", "CREATURE_PREDICATE",
                     "SAME_WORD_DIFFERENT_SENSE", "TITLE_ONLY"]}
    path = os.path.join(CALIBRATION_DIR, "planted-near-misses.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    from collections import Counter
    print(f"{len(items)} items written to {path}; {len(failures)} failures")
    print("by slice:", Counter(("Dositheus" if i["registry_id"] == D else i["branch"]) for i in items))
    print("by type:", Counter(i["type"] for i in items))
    for f in failures:
        print("  FAIL", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(build())
