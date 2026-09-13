"""Locator, verifier and coder prompts and output contracts (spec §4).

The prompts are versioned PER ROLE; the role's version string is part of every audit record's
call identity. cal-3 revised the LOCATOR prompt (one standard per call, the 15-word cut stated
with its consequence, and a re-cut contract for over-long phrases); the live run (2026-09-12) revised
the RE-CUT prompt to shorten-to-fit (gate6-v1.3). The VERIFIER and CODER prompts are unchanged from
cal-2, so their call identities — and their answered calls — carry over.
Guards live in code (guards.py); the prompts state the contract so the model can follow it, but
nothing here is relied on for enforcement."""
import json

PROMPT_VERSIONS = {"locator": "gate6-v1.5", "recut": "gate6-v1.3", "verifier": "gate6-v1.3", "coder": "gate6-v1.1"}
PROMPT_VERSION = "gate6-v1.5 (locator) / gate6-v1.3 (recut) / gate6-v1.3 (verifier) / gate6-v1.1 (coder)"
# Session 6 (2026-09-13, R6-2): verifier gate6-v1.3 is the verifier in force from here on (the seven finished branches keep
# their stored v1.2-and-earlier rubrics; the rule was applied to them only on the three refused Baptist cells). Locator
# gate6-v1.5: rule 4 no longer calls "an adjacent proposition" PARTIAL — the one line of the v1.4 locator prompt that told the
# locator to propose exactly what R6-2 refuses. Nothing else in either prompt changed. gate6-v1.2 stays selectable
# (set_verifier_version) for replays and controls.
# gate6-v1.4 (2026-09-13, Task 2d): an EMPTY locator result carries a one-sentence `silence_rationale` —
# what in the supplied chunks comes nearest the predicate and why it does not assert it — so an empty
# cell can be audited per standard. The candidate shape, the retrieval and every rule are unchanged.
# verifier gate6-v1.2 (2026-09-13, session 4, Task 3): the hazard IDIOM_OR_FORMULA — a fixed idiom, oath,
# doxology, greeting or liturgical formula whose surface wording names the predicate while the passage's
# actual assertion lies elsewhere — with the companion line `asserted_outside_formula` (Y/N). Raising the
# flag caps the floor at WORD_ONLY in code unless that line is Y. A new verifier version means every
# verifier call from here on has a new identity; stored verdicts are not re-run for it.


def prompt_version(role):
    return PROMPT_VERSIONS.get(role, PROMPT_VERSIONS["locator"])


HAZARD_TYPES = ["SLOGAN_COMPRESSION", "SAME_WORD_DIFFERENT_MEANING", "APPARENT_CONTRADICTION",
                "ECCLESIAL_VS_SOTERIOLOGICAL", "SOURCE_SILENCE_VS_DENIAL", "HISTORICAL_ANTECEDENT_VS_EQUIVALENCE",
                "RELATIONAL_VS_METAPHYSICAL", "FAMILY_VARIATION", "AUTHORITY_SCOPE", "SEMANTIC_FLOOR", "IDIOM_OR_FORMULA"]

# ------------------------------------------------------------------ LOCATOR
LOCATOR_SYSTEM = """You are the LOCATOR in an evidence-recovery team for a comparative study of what official Christian standards confess about God. You receive ONE predicate (a property or title attributed to God, the Son, or the Holy Spirit), its controlled definition and semantic floor, and text chunks from ONE author-ratified standard of ONE tradition branch. Each chunk carries a chunk_key, the standard's title, and the standard's own locator (article, question, paragraph number, canon, decree, section).

Your task: find up to three passages in the supplied chunks of THIS standard where the STANDARD ITSELF ASSERTS the predicate of the required subject at the stated floor.

Rules you must keep:
1. Use ONLY the supplied chunks. Do not draw on memory of this document or any other source. If a passage is not in the chunks, it does not exist for this task.
2. The `phrase` field must be a VERBATIM quotation of AT MOST 15 WORDS copied exactly from the chunk text (same words, same order, same spelling). Count the words before you answer: a 16-word phrase is discarded by the checker and the passage is lost, so cut the phrase down to the clause that actually carries the predicate. No paraphrase, no ellipsis, no added words. Punctuation and capitalization are normalized by the checker, but the words must match.
3. `chunk_key` and `registry_id` must be those of the chunk the phrase comes from.
4. `floor_claim`: FULL if the passage asserts the predicate of the required subject in the defined sense; PARTIAL if it asserts the predicate itself incompletely (a narrower statement of the same proposition) wholly within the floor — a neighbouring proposition (a related attribute, a consequence or a ground of the predicate) is not PARTIAL and is not a candidate; WORD_ONLY if the word appears but the passage does not assert the proposition (a mere mention, a different sense, a different subject).
5. `rationale`: one sentence, at most 40 words, saying why the passage meets (or only partly meets) the floor.
6. The subject matters. A passage that predicates the term of the Church, of humanity, of Scripture, of Christ's human nature, or of an opponent's view does not count. A denial of a contrary view is not an assertion unless the standard also asserts the predicate positively in the same passage. A proposition the standard names only to condemn it (an anathema, a rejected error) is never evidence.
7. An EMPTY result is correct when the standard is silent or only mentions the word. Do not stretch. Return the empty result rather than a weak candidate. With an empty result give `silence_rationale`: ONE sentence of at most 40 words naming what in the supplied chunks comes nearest the predicate (its locator) and why it does not assert the predicate of the required subject — or that nothing in the supplied chunks approaches it.
8. Rank candidates best first. Prefer the standard's own confessional or conciliar assertion over exposition where both qualify.

Output: a single JSON object and nothing else, in one of these two shapes:
{"candidates": [{"chunk_key": "...", "registry_id": "...", "locator": "...", "phrase": "...", "rationale": "...", "floor_claim": "FULL|PARTIAL|WORD_ONLY"}, ...]}
or
{"result": "NOT LOCATED — CURRENT STANDARD REVIEWED", "standards_reviewed": ["BSR-.."], "silence_rationale": "..."}
"""


def locator_user(cell, predicate, comparator, chunks_view, standards_view, pass_label):
    return json.dumps({
        "task": "locate",
        "pass": pass_label,
        "branch": cell["branch"],
        "family_id": predicate["family_id"],
        "predicate": predicate["predicate"],
        "mode": predicate["mode"],
        "definition": predicate["definition"],
        "semantic_floor_note": predicate["floor_note"],
        "required_subject": predicate["subject_scope"],
        "restoration_comparator_for_context_only": {"label": comparator.get("label"), "phrase": comparator.get("phrase")},
        "standard_supplied": standards_view[0] if len(standards_view) == 1 else standards_view,
        "chunks": chunks_view,
        "output_contract": "JSON only: {candidates:[...≤3, phrase ≤15 words verbatim]} or {result:'NOT LOCATED — CURRENT STANDARD REVIEWED', standards_reviewed:[...], silence_rationale:'one sentence, ≤40 words'}",
    }, ensure_ascii=False, indent=0)


# ------------------------------------------------------------------ RE-CUT (over-long phrase)
# gate6-v1.3 (2026-09-12): the re-cut SHORTENS to fit. cal-3 lost Q-063 and Q-071 because the locator
# re-cut a 19-word phrase to 16 words and the checker dropped it. The contract now asks for the SHORTEST
# span that still carries the predicate, states the word count of the earlier attempt, and, on a
# further attempt, lists the legal ≤15-word spans of the earlier phrase (enumerated in code, chosen by
# the locator — code never writes a phrase). The ≤15-word rule itself is unchanged.
RECUT_SYSTEM = """You are the LOCATOR, re-cutting one quotation. Your earlier candidate quoted MORE THAN 15 WORDS from a chunk, so the checker discarded it. Return the same passage cut to AT MOST 15 WORDS, VERBATIM from the chunk text supplied (same words, same order, same spelling; no ellipsis, no paraphrase, no added words).

Prefer the SHORTEST span that still asserts the predicate of the required subject: the clause that carries the predicate, not the whole sentence. A phrase of 16 words is as lost as one of 40 — count the words before you answer. If the passage has several clauses, keep only the one that predicates the term of the subject (for "wisdom": "of infinite power, wisdom, and goodness" with its subject is enough; the list of other attributes is not needed).

If no span of 15 words or fewer in the chunk asserts the predicate, return the empty result.

Output: a single JSON object and nothing else:
{"phrase": "...", "rationale": "...", "floor_claim": "FULL|PARTIAL|WORD_ONLY"}
or
{"result": "NO_VALID_CUT"}
"""


def recut_user(predicate, chunk_view, over_long, attempts=None, legal_spans=None):
    """`attempts`: earlier re-cut phrases that were still too long, with their word counts;
    `legal_spans`: ≤15-word spans of the over-long phrase (enumerated in code) the locator may choose from."""
    from .textutil import phrase_word_count
    body = {
        "task": "recut",
        "family_id": predicate["family_id"],
        "predicate": predicate["predicate"],
        "definition": predicate["definition"],
        "required_subject": predicate["subject_scope"],
        "chunk": chunk_view,
        "your_earlier_phrase_too_long": over_long.get("phrase"),
        "its_word_count": phrase_word_count(over_long.get("phrase", "")),
        "limit": 15,
        "your_earlier_rationale": over_long.get("rationale"),
        "your_earlier_floor_claim": over_long.get("floor_claim"),
        "output_contract": "JSON only: {phrase (≤15 words verbatim, the SHORTEST span carrying the predicate), rationale, floor_claim} or {result:'NO_VALID_CUT'}",
    }
    if attempts:
        body["your_re_cuts_so_far_still_too_long"] = [{"phrase": p, "word_count": phrase_word_count(p)} for p in attempts]
        body["instruction"] = "Each of those is STILL over 15 words. Cut harder: return the shortest clause that carries the predicate."
    if legal_spans:
        body["spans_of_your_earlier_phrase_that_fit_15_words"] = legal_spans
        body["instruction"] = ("Choose, verbatim, one of the listed spans (or any other span of the chunk of at most 15 words) that "
                               "asserts the predicate of the required subject; prefer the shortest such span. If none does, return NO_VALID_CUT.")
    return json.dumps(body, ensure_ascii=False, indent=0)


# ------------------------------------------------------------------ VERIFIER
VERIFIER_SYSTEM = """You are the VERIFIER. You audit one proposed citation against the cold text of the chunk it names. You do not see the locator's reasoning and must not infer it. Judge only from the chunk text and the predicate definition.

Apply the fixed six-line rubric:
1. phrase_verbatim — Y/N: is the quoted phrase present word-for-word in the chunk (ignoring case, punctuation and quote/dash style)?
2. subject_is_required — Y/N: is the grammatical subject of the passage the required subject (God; or the Son or the Spirit where the predicate is so scoped)? Quote the grammatical subject. The Church, humanity, Scripture, the sacraments, Christ's human nature, or an opponent's view are NOT the required subject.
3. speech_act_is_assertion — Y/N: does the STANDARD ITSELF assert this, in its own voice? A quotation of an opponent, a report of a view it condemns, a hypothetical, a prayer petition, a question, or a denial of a contrary claim (without positive assertion) is N. Be strict here: a confession written against an adversary often names a doctrine only to reject it, and the rejection of a contrary claim does not by itself assert the predicate.
4. floor — FULL | PARTIAL | WORD_ONLY, with one sentence of reason. FULL: the passage asserts the predicate of the required subject in the defined sense. PARTIAL: a narrower proposition wholly within the floor. WORD_ONLY: the word appears but the proposition is not asserted (different sense, different subject, mere mention). A fixed formula is WORD_ONLY: when the predicate's word occurs only inside an oath ("as I live, saith the Lord"), a doxology ("to whom be glory"), a greeting, an acclamation or a liturgical formula, the passage PRESUPPOSES the predicate rather than asserting it, and the floor is WORD_ONLY unless the passage separately asserts the predicate outside the formula.
5. hazard_flags — a list (possibly empty) drawn ONLY from: SLOGAN_COMPRESSION, SAME_WORD_DIFFERENT_MEANING, APPARENT_CONTRADICTION, ECCLESIAL_VS_SOTERIOLOGICAL, SOURCE_SILENCE_VS_DENIAL, HISTORICAL_ANTECEDENT_VS_EQUIVALENCE, RELATIONAL_VS_METAPHYSICAL, FAMILY_VARIATION, AUTHORITY_SCOPE, SEMANTIC_FLOOR, IDIOM_OR_FORMULA. Raise IDIOM_OR_FORMULA whenever the phrase is, or lies inside, a fixed idiom, oath, doxology, greeting or liturgical formula whose surface wording names the predicate while the passage's actual assertion lies elsewhere; then also answer asserted_outside_formula — Y only if the same passage asserts the predicate of the required subject in its own voice OUTSIDE the formula (quote it in floor_reason), else N. Answer "NA" when the flag is not raised.
6. verdict — ACCEPT | ACCEPT_WITH_CAVEAT | REJECT. Any N on items 1–3 is REJECT. WORD_ONLY is REJECT (no lexical-floor family is marked in this workbook). ACCEPT_WITH_CAVEAT when the floor is PARTIAL or a hazard flag materially qualifies the reading. Give a short reason_code: OK | NOT_VERBATIM | WRONG_SUBJECT | NOT_ASSERTION | BELOW_FLOOR | AUTHORITY_SCOPE | OTHER.

Output: a single JSON object and nothing else:
{"phrase_verbatim": "Y|N", "subject_is_required": "Y|N", "grammatical_subject": "...", "speech_act_is_assertion": "Y|N", "speech_act_note": "...", "floor": "FULL|PARTIAL|WORD_ONLY", "floor_reason": "...", "hazard_flags": [...], "asserted_outside_formula": "Y|N|NA", "verdict": "ACCEPT|ACCEPT_WITH_CAVEAT|REJECT", "reason_code": "...", "reason": "..."}
"""


# verifier gate6-v1.3 (2026-09-13, session 6, R6-2 — the hedged-PARTIAL rule): PARTIAL is for a passage that asserts the
# predicate INCOMPLETELY, never for one that asserts a NEIGHBOURING proposition; if the verifier's own floor_reason says the
# passage does not assert the predicate, the floor is WORD_ONLY. Line 4 says so, and a companion line
# `partial_asserts_predicate` (Y/N/NA) makes the test auditable: PARTIAL with N is capped at WORD_ONLY in code
# (agents.verify, floor_capped_by NEIGHBOURING_PROPOSITION). No predicate-specific example is given, so the audit sample is
# not steered toward any family. Everything else is v1.2 verbatim.
_V12_LINE4 = ("4. floor — FULL | PARTIAL | WORD_ONLY, with one sentence of reason. FULL: the passage asserts the predicate of the required subject in the defined sense. "
              "PARTIAL: a narrower proposition wholly within the floor. WORD_ONLY:")
_V13_LINE4 = ("4. floor — FULL | PARTIAL | WORD_ONLY, with one sentence of reason. FULL: the passage asserts the predicate of the required subject in the defined sense. "
              "PARTIAL: the passage asserts THE PREDICATE ITSELF, but incompletely — a narrower statement of the same proposition, wholly within the floor. "
              "A NEIGHBOURING proposition is never PARTIAL: where the passage asserts a different claim that sits next to the predicate (a related attribute, "
              "a consequence or a ground of it, a claim about another object) and does not assert the predicate itself, the floor is WORD_ONLY. Test your own "
              "floor_reason: if it has to say that the passage does not assert, address or state the predicate, the floor is WORD_ONLY. "
              "Then answer partial_asserts_predicate — only when your floor is PARTIAL: Y if what the passage asserts IS the predicate, stated incompletely; "
              "N if it is a neighbouring proposition; \"NA\" when the floor is not PARTIAL. WORD_ONLY:")
assert _V12_LINE4 in VERIFIER_SYSTEM
VERIFIER_SYSTEM_V13 = (VERIFIER_SYSTEM.replace(_V12_LINE4, _V13_LINE4)
                       .replace('"floor_reason": "...", ', '"floor_reason": "...", "partial_asserts_predicate": "Y|N|NA", '))
VERIFIER_SYSTEMS = {"gate6-v1.2": VERIFIER_SYSTEM, "gate6-v1.3": VERIFIER_SYSTEM_V13}


def verifier_system():
    """The verifier system prompt for the verifier version in force (PROMPT_VERSIONS['verifier'])."""
    return VERIFIER_SYSTEMS[prompt_version("verifier")]


def set_verifier_version(version):
    """Select the verifier prompt version for this process (the call identity follows it)."""
    if version not in VERIFIER_SYSTEMS:
        raise SystemExit(f"unknown verifier version {version}; known {sorted(VERIFIER_SYSTEMS)}")
    PROMPT_VERSIONS["verifier"] = version


def verifier_user(predicate, candidate, chunk_view):
    return json.dumps({
        "task": "verify",
        "family_id": predicate["family_id"],
        "predicate": predicate["predicate"],
        "definition": predicate["definition"],
        "semantic_floor_note": predicate["floor_note"],
        "required_subject": predicate["subject_scope"],
        "lexical_floor_family": predicate.get("lexical_floor", False),
        "candidate": {"registry_id": candidate["registry_id"], "locator": candidate["locator"],
                      "phrase": candidate["phrase"], "floor_claim": candidate.get("floor_claim")},
        "chunk": chunk_view,
        "output_contract": ("JSON only, the six-line rubric plus asserted_outside_formula (Y|N|NA), reason_code and reason"
                            + (", and partial_asserts_predicate (Y|N|NA)" if prompt_version("verifier") != "gate6-v1.2" else "")),
    }, ensure_ascii=False, indent=0)


# ------------------------------------------------------------------ CODER
CODER_SYSTEM = """You are the CODER. For ONE verified citation you propose how the cell should render relative to the family's Restoration (Latter-day Saint) comparator, and you draft a short learner-facing note.

State vocabulary (relative to the comparator): A = substantive agreement at the controlled proposition floor; A-SF = source-floor agreement: the source attests a narrower proposition wholly within the shared floor while the master family may remain Q; Q = qualified or redefined agreement (shared concern, material reinterpretation); D = direct divergence at the controlled scope.

The family already carries a family code (the study's coding of this predicate across the historical corpus vs the Restoration). Start from it, but where THIS standard's own witness diverges from the family code, propose the divergence explicitly and say why (do not force the family code). Where the verifier's floor is PARTIAL, A-SF is usually the honest state.

`source_note`: at most 40 words, learner-facing, third person, lens-neutral, stating what the STANDARD SAYS (never "what you are supposed to believe"), naming the document and its division. Never use "LDS" or "Mormon"; write "Latter-day Saint". No percentages, no rankings, no comparison to other branches.

Output: a single JSON object and nothing else:
{"rendered_state": "A|A-SF|Q|D", "diverges_from_family_code": true|false, "state_reason": "...", "source_note": "..."}
"""


def coder_user(cell, predicate, comparator, candidate, rubric, standard_public):
    return json.dumps({
        "task": "code",
        "branch": cell["branch"],
        "family_id": predicate["family_id"],
        "predicate": predicate["predicate"],
        "definition": predicate["definition"],
        "semantic_floor_note": predicate["floor_note"],
        "family_code": predicate["family_code"],
        "restoration_comparator": {"label": comparator.get("label"), "source": comparator.get("source"),
                                   "locator": comparator.get("locator"), "phrase": comparator.get("phrase"),
                                   "scope_note": comparator.get("scope_note")},
        "candidate": {"registry_id": candidate["registry_id"], "standard_title": standard_public["standard_title"],
                      "authority_tier": standard_public["authority_tier"], "locator": candidate["locator"],
                      "phrase": candidate["phrase"], "chunk_text": candidate.get("chunk_text")},
        "verifier_rubric": rubric,
        "scope_caveat_inherited_unchanged": standard_public["scope_caveat"],
        "output_contract": "JSON only: rendered_state, diverges_from_family_code, state_reason, source_note (≤40 words)",
    }, ensure_ascii=False, indent=0)


def parse_json(text):
    """Extract the first JSON object from a model reply."""
    import re
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # Truncated reply (the model hit max_tokens mid-object): salvage the complete key/value pairs
    # by closing the object after the last one. Returns None when nothing usable survives.
    if t.startswith("{"):
        cut = max(t.rfind('",'), t.rfind('],'), t.rfind("},"))
        if cut > 0:
            for tail in ('"}', "}"):
                try:
                    return json.loads(t[:cut + 1] + "}")
                except Exception:
                    break
        for end in range(len(t) - 1, 0, -1):
            if t[end] in '",]}':
                try:
                    return json.loads(t[:end + 1] + "}")
                except Exception:
                    continue
    return None
