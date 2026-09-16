"""Guards enforced in code, never in a prompt (spec §5).

  registry-only     agents receive chunk text and locators; URLs are stripped before any prompt is built
  phrase assertion  a candidate phrase must be present verbatim (normalized) in the chunk it names
  length            phrase ≤15 words after normalization; rationale ≤40; source_note ≤40
  no cross-branch   a candidate's registry_id must belong to the cell's branch
  duplicates        identical locator + phrase collapses to one candidate
  fallback tier     fallback-only rows are admitted only in pass two (agents.py)
  non-citable spans a chunk may carry spans withheld from its agent-visible text (the Synodikon's
                    anathema-framed propositions); a phrase drawn from a withheld span is refused by
                    name even if the agent reconstructed it
  citation refusal  DIALOGUE_ONLY rows and named documents (the 1848 Encyclical) are refused as
                    citations with the policy's own reason (registry.citation_refusal)
  witness rows      a candidate on a TRANSLATION_WITNESS / witness row is flagged WITNESS; a cell may
                    not rest on such rows alone (packets.py, calibrate.py)
"""
from .config import PHRASE_MAX_WORDS, RATIONALE_MAX_WORDS, SOURCE_NOTE_MAX_WORDS
from .textutil import normalize, phrase_word_count, contains, scrub_urls


class GuardError(Exception):
    pass


AGENT_CHUNK_FIELDS = ("chunk_key", "registry_id", "standard_title", "authority_tier", "locator", "text", "language")


def agent_view(chunk, key):
    """The only representation of a chunk an agent ever sees. No URL, no hash, no withheld span:
    `text` is the agent-visible text, which for a guarded row already lacks the non-citable spans."""
    return {"chunk_key": key, "registry_id": chunk["registry_id"], "standard_title": chunk["standard_title"],
            "authority_tier": chunk["authority_tier"], "locator": chunk["locator"], "text": scrub_urls(chunk["text"]),
            "language": chunk.get("language", "en")}


def assert_no_urls(obj):
    """Defensive: nothing that reaches a prompt may contain a URL."""
    import json
    import re
    blob = json.dumps(obj, ensure_ascii=False)
    if re.search(r"https?://|www\.[a-z]", blob, re.I):
        raise GuardError("URL leaked into agent input")


def check_phrase(phrase, chunk_text):
    """Return (ok, reason). Verbatim containment after normalization; ≤15 words."""
    if not phrase or not phrase.strip():
        return False, "empty phrase"
    n = phrase_word_count(phrase)
    if n > PHRASE_MAX_WORDS:
        return False, f"phrase exceeds {PHRASE_MAX_WORDS} words ({n})"
    if not contains(chunk_text, phrase):
        return False, "phrase not present verbatim in the named chunk"
    return True, "verbatim"


def check_noncitable(phrase, chunk):
    """(ok, reason): the phrase must not lie inside a span the corpus builder withheld from this chunk."""
    spans = chunk.get("noncitable_spans") or []
    if not spans or not phrase:
        return True, "ok"
    p = normalize(phrase)
    for sp in spans:
        if p and p in normalize(sp["text"] if isinstance(sp, dict) else sp):
            kind = sp.get("kind", "non-citable") if isinstance(sp, dict) else "non-citable"
            return False, f"{kind.upper()}_SPAN: phrase lies inside a span withheld as non-citable (quoting it inverts or misstates the standard)"
    return True, "ok"


def check_length(text, cap, label):
    n = phrase_word_count(text)
    return (n <= cap), (f"{label} {n} words > {cap}" if n > cap else "ok")


def check_branch(candidate_rid, branch, registry):
    row = registry.by_id.get(candidate_rid)
    if not row:
        return False, f"{candidate_rid} is not an AUTHOR_RATIFIED registry row"
    if row["branch"] != branch:
        return False, f"{candidate_rid} belongs to {row['branch']}, not {branch} (cross-branch leakage)"
    return True, "ok"


def check_citable_row(candidate_rid, registry):
    """DIALOGUE_ONLY rows and named-refusal documents are never citations, whatever the agent found."""
    reason = registry.citation_refusal(candidate_rid)
    if reason:
        return False, reason
    return True, "ok"


def dedupe_key(candidate):
    return (candidate["registry_id"], normalize(candidate["locator"]), normalize(candidate["phrase"]))


def vet_candidate(cand, chunk_by_key, branch, registry, allow_fallback):
    """Apply every code guard to a locator candidate. Returns (ok, reason, chunk)."""
    key = cand.get("chunk_key")
    chunk = chunk_by_key.get(key)
    if chunk is None:
        return False, f"unknown chunk_key {key!r} (candidate cites text it was not given)", None
    if cand.get("registry_id") != chunk["registry_id"]:
        return False, "registry_id does not match the cited chunk", chunk
    ok, why = check_branch(chunk["registry_id"], branch, registry)
    if not ok:
        return False, why, chunk
    ok, why = check_citable_row(chunk["registry_id"], registry)
    if not ok:
        return False, why, chunk
    if registry.is_fallback(chunk["registry_id"]) and not allow_fallback:
        return False, "fallback-only standard cited in pass one", chunk
    ok, why = check_noncitable(cand.get("phrase", ""), chunk)
    if not ok:
        return False, why, chunk
    ok, why = check_phrase(cand.get("phrase", ""), chunk["text"])
    if not ok:
        return False, why, chunk
    ok, why = check_length(cand.get("rationale", ""), RATIONALE_MAX_WORDS, "rationale")
    if not ok:
        cand["rationale"] = " ".join(cand["rationale"].split()[:RATIONALE_MAX_WORDS])
    if cand.get("floor_claim") not in ("FULL", "PARTIAL", "WORD_ONLY"):
        return False, f"floor_claim {cand.get('floor_claim')!r} not in FULL|PARTIAL|WORD_ONLY", chunk
    return True, "ok", chunk


def vet_source_note(note):
    ok, why = check_length(note or "", SOURCE_NOTE_MAX_WORDS, "source_note")
    return ok, why


# ---------------------------------------------------------------- clause 4 (2026-09-16): a creed's silence is not a finding
# "Creeds are not exhaustive. That a creed does not contain a predicate is never evidence that the tradition denies it."
# The verifier prompt (gate6-v1.4) states the rule; this is the hard stop, so it does not depend on the model reading it.
# A DIVERGENCE proposal (rendered_state D) is refused when its only support is a creed's silence — either the verifier
# raised SOURCE_SILENCE_VS_DENIAL on the candidate, or the coder's own state_reason says the creed does not contain the
# predicate. The proposal is kept on the card with its refusal; the state falls back to the family's own code.
import re as _re                                                      # noqa: E402

CREEDAL_SILENCE_STOP = "CREEDAL_SILENCE_IS_NOT_DENIAL"
HAZARD_SOURCE_SILENCE = "SOURCE_SILENCE_VS_DENIAL"
_CREED_WORD = _re.compile(r"\b(creed|symbol of faith|nicene|niceno|athanasian|apostles'? creed|quicunque)\b", _re.I)
_SILENCE = _re.compile(r"\b(silent|silence|does not (?:contain|mention|say|include|state|address|speak)|"
                       r"nowhere (?:mentions|states|says)|no mention|not (?:in|found in|present in|contained in)|omits|"
                       r"absent from|says nothing|makes no)\b", _re.I)


def creedal_silence_stop(proposal, rubric, family_code=None):
    """None when the proposal stands; otherwise the fields that refuse it (merged into the coder proposal)."""
    if str(proposal.get("rendered_state") or "").upper() != "D":
        return None
    reason = " ".join(str(proposal.get(k) or "") for k in ("state_reason", "source_note"))
    hazard = HAZARD_SOURCE_SILENCE in ((rubric or {}).get("hazard_flags") or [])
    creedal = bool(_CREED_WORD.search(reason)) and bool(_SILENCE.search(reason))
    if not (creedal or (hazard and _CREED_WORD.search(reason))):
        return None
    return {"rendered_state": family_code or None, "rendered_state_proposed": proposal.get("rendered_state"),
            "divergence_refused_by": CREEDAL_SILENCE_STOP,
            "divergence_refusal_reason": ("clause 4: a creed's silence is never evidence that the tradition denies the "
                                          "predicate, so it cannot support a divergence. "
                                          + (f"The verifier raised {HAZARD_SOURCE_SILENCE} on this candidate. " if hazard else "")
                                          + "The proposal is kept for the author; the state falls back to the family code."),
            "divergence_refusal_support": {"hazard_raised": hazard, "reason_names_a_creed": bool(_CREED_WORD.search(reason)),
                                           "reason_asserts_silence": bool(_SILENCE.search(reason))}}
