/**
 * Seeking Jesus of Nazareth — client-facing derivation of the pipeline output.
 *
 * Reads src/_data/sjn/*.json (emitted by scripts/sjn-build-data.py, guarded by
 * scripts/sjn-verify-data.js) and produces the slim structures the /seeking-jesus/
 * templates and script need. Never hand-copies a number: every value here is
 * derived from the emitted files at build time.
 */
const fs = require("fs");
const path = require("path");

const DIR = path.join(__dirname, "sjn");
const load = (name) => JSON.parse(fs.readFileSync(path.join(DIR, name), "utf8"));

const CODE_LABELS = {
    A: { label: "Shared", long: "Shared (A)", plain: "Both traditions affirm this of God in the same sense." },
    Q: { label: "Shared, but differently understood", long: "Shared, but differently understood (Q)",
         plain: "Both use the word and share the concern, but the picture behind it differs." },
    D: { label: "Different", long: "Different (D)", plain: "At the level the creeds intend, the two teachings cannot both be true." },
    ADDITION: { label: "Restoration addition", long: "Restoration addition",
                plain: "A teaching the creeds and confessions studied do not contain as a positive doctrine." }
};

// Characters that must be escaped when JSON is inlined in a <script> element.
const SCRIPT_UNSAFE = [["<", "\\u003c"], [" ", "\\u2028"], [" ", "\\u2029"]];

module.exports = function () {
    const meta = load("meta.json");
    const P = load("predicates.json");
    const R = load("ranges.json");
    const G = load("godhead.json");
    const GL = load("glossary.json");
    const C = load("clarifications.json");
    const V = load("vectors.json");
    const I = load("inferences.json");
    const scriptures = require("./scriptures.json");

    const fourClause = {};
    const predicates = P.predicates.map((p) => {
        const key = p.corpus === "restoration" ? "ADDITION" : p.code;
        fourClause[key] = p.sentence.text;
        const h = p.citation ? p.citation.historical : null;
        const r = p.citation ? p.citation.restoration : null;
        return {
            id: p.id,
            n: parseInt(p.id.replace(/^RNR-[HA]/, ""), 10),
            corpus: p.corpus,
            family: p.family,
            predicate: p.predicate,
            mode: p.mode,
            code: key,
            code_label: CODE_LABELS[key].label,
            tier: p.authority_tier,
            lens: p.lens,
            summary: p.summary,
            caution: p.caution,
            sentence: p.sentence.text,
            card_mode: p.card_mode,
            vector: p.vector ? { caption: p.vector.caption, layers: p.vector.atomic_layer_summary } : null,
            ratified: ["APPROVE", "REVISE"].includes((p.ratification || {}).decision),
            confidence: p.inherited ? p.inherited.confidence : (p.restoration ? p.restoration.confidence : ""),
            provenance: p.inherited ? p.inherited.coding_provenance : (p.restoration ? p.restoration.authority_role : ""),
            floor: p.inherited ? p.inherited.source_definition : (p.restoration ? p.restoration.normalized_family : ""),
            scope: p.inherited ? p.inherited.semantic_floor_note : "",
            historical: h ? {
                branch: h.branch, institution: h.institution, document: h.document, locator: h.locator,
                url: h.text_url || h.authority_url || null, phrase: h.phrase,
                packet_only: !h.text_url && !h.phrase
            } : null,
            restoration: r ? {
                label: r.label, source: r.source, locator: r.locator, url: r.primary_url, phrase: r.phrase,
                supplemental_url: r.supplemental_url, supplemental_phrase: r.supplemental_phrase
            } : (p.restoration ? {
                label: p.restoration.locator, source: p.restoration.authority_role, locator: p.restoration.locator,
                url: p.restoration.source_url, phrase: null, evidence_note: p.restoration.evidence_note,
                domain: p.restoration.domain, novelty_caution: p.restoration.novelty_caution
            } : null)
        };
    });

    const families = [...new Set(predicates.map((p) => p.family))];
    const byId = Object.fromEntries(predicates.map((p) => [p.id, p]));

    const counts = {
        inherited: predicates.filter((p) => p.corpus === "inherited").length,
        additions: predicates.filter((p) => p.corpus === "restoration").length,
        A: predicates.filter((p) => p.code === "A").length,
        Q: predicates.filter((p) => p.code === "Q").length,
        D: predicates.filter((p) => p.code === "D").length,
        kataphatic: predicates.filter((p) => p.corpus === "inherited" && /kataphatic/i.test(p.mode)).length,
        apophatic: predicates.filter((p) => p.corpus === "inherited" && !/kataphatic/i.test(p.mode)).length
    };

    const client = {
        version: meta.app_master_version,
        build_date: meta.build_date,
        run_at: meta.pipeline_run_at,
        canonical_hash: meta.canonical_hash,
        pipeline_status: meta.status,
        badge: R.sjn_stat_contract ? R.sjn_stat_contract.badge : "Provisional: internal coding, external validation pending",
        code_labels: CODE_LABELS,
        four_clause: fourClause,
        counts,
        families,
        predicates,
        stats: R.ranges,
        inference_stats: R.inference_stats,
        inferences: I.inferences.map((i) => ({ id: i.id, theme: i.theme, metric: i.metric, stat: i.stat,
            observation: i.direct_observation, inference: i.defensible_inference, does_not_support: i.does_not_support })),
        godhead: G.panels,
        hazards: GL.hazard_types,
        glossary: GL.terms,
        rendered_states: GL.rendered_states,
        vectors: V.families.map((v) => ({ id: v.family_id, predicate: v.predicate, caption: v.caption, layers: v.atomic_layer_summary })),
        clarifications: {
            enabled: C.policy && C.policy.enabled,
            runtime_mode: C.policy && C.policy.clarification_runtime_mode,
            max_auto_cues: C.policy && C.policy.clarification_max_auto_cues_per_view,
            cases: C.cases.filter((c) => c.public_release).map((c) => ({
                id: c.id, title: c.public_title, label: c.short_label, tradition: c.primary_tradition_family,
                hazard: c.primary_hazard, hazards: c.additional_hazards, priority: c.auto_priority,
                question: c.learner_question, distinction: c.key_distinction, resolution: c.resolution_summary,
                variation: c.internal_variation, significance: c.interfaith_significance, does_not_prove: c.does_not_prove,
                cue: c.learner_cue_copy, category: c.explorer_category,
                related: c.anchor ? c.anchor.related_predicate_ids : [],
                sources: c.sources.map((s) => ({ id: s.key, role: s.source_role, document: s.document, locator: s.locator,
                    url: s.url, phrase: s.phrase, institution: s.institution, claim: s.claim_supported }))
            })),
            triggers: C.triggers.filter((t) => t.active === "YES").map((t) => ({
                id: t.id, case_id: t.case_id, type: t.type, value: t.value, match: t.match_mode,
                tradition: t.required_tradition, topic: t.required_topic, auto: t.auto_cue_eligible, priority: t.priority
            }))
        },
        scripture_books: scriptures.books
    };
    client.byId = byId;
    // Pre-serialized, script-safe JSON for inline <script> embedding.
    const { byId: _omit, ...serializable } = client;
    let json = JSON.stringify(serializable);
    for (const [ch, esc] of SCRIPT_UNSAFE) json = json.split(ch).join(esc);
    client.json_html = json;
    return client;
};
