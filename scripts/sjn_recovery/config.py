"""Paths and constants for the Gate 6 recovery team."""
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)

DATA_SOURCES = os.path.join(ROOT, "data-sources", "sjn")
RUNS_DIR = os.path.join(DATA_SOURCES, "recovery-runs")          # committed: manifest, audit logs, reports
PACKETS_DIR = os.path.join(DATA_SOURCES, "recovery-packets")    # committed: <branch>.json
CACHE_DIR = os.path.join(ROOT, ".cache", "sjn-recovery")        # gitignored
FETCH_CACHE = os.path.join(CACHE_DIR, "fetch")
CHUNK_DIR = os.path.join(CACHE_DIR, "chunks")
JOBS_DIR = os.path.join(CACHE_DIR, "jobs")
MANIFEST_PATH = os.path.join(RUNS_DIR, "corpus-manifest.json")
FETCH_AUDIT_PATH = os.path.join(RUNS_DIR, "fetch-audit.json")
CALIBRATION_DIR = os.path.join(RUNS_DIR, "calibration")
ARCHIVE_DIR = os.path.join(RUNS_DIR, "archived-fetches")     # committed one-time archived fetches + provenance
EMITTED_DIR = os.path.join(ROOT, "src", "_data", "sjn")

# ChromaDB: the ministry-rag persistent store gains the internal collection `sjn_confessions`.
CHROMA_PATH = os.environ.get("SJN_CHROMA_PATH", r"C:\Users\aaron\Documents\ministry-rag\chroma_db")
CHROMA_COLLECTION = "sjn_confessions"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = "nomic-embed-text"

BRANCHES = ["Roman Catholic", "Lutheran", "Reformed / Presbyterian", "Baptist", "Methodist / Wesleyan",
            "Anglican", "Mennonite / Anabaptist", "Eastern Orthodox"]           # §7 run order

# Guards (§5)
PHRASE_MAX_WORDS = 15
RATIONALE_MAX_WORDS = 40
SOURCE_NOTE_MAX_WORDS = 40
MAX_CANDIDATES = 3                  # packet cap per cell (tier by tier) and locator cap per standard

# Retrieval is PER STANDARD (cal-3, Fix 1): the locator is called once per AUTHOR_RATIFIED standard
# of the branch, with that standard's own chunks — whole when they fit the budget, otherwise the
# hybrid top ranking within that standard. Every standard therefore has a guaranteed candidate
# slot: its best candidate is always verified. Beyond the guaranteed slots, VERIFY_EXTRA_CANDIDATES
# further candidates per cell are verified, ranked by authority tier then the locator's floor claim.
LOCATOR_CONTEXT_CHARS = 60000       # per standard, per call (characters of chunk text)
RETRIEVAL_TOP_K_PER_STANDARD = 6
VERIFY_EXTRA_CANDIDATES = 3

# Verifier routing (APP CONFIG verifier_routing = SONNET_WITH_OPUS_SLICE). The primary model verifies
# every candidate; the secondary adjudicates only the slice: caveated rows, fallback-only rows, the
# guarded Synodikon row, and every cell where the primary rejected all candidates. The registry
# supplies the row lists; these are the defaults if the workbook says nothing.
OPUS_SLICE_ROWS_DEFAULT = ["BSR-EO-04", "BSR-EO-05", "BSR-EO-09"]
ROUTING_SONNET_WITH_OPUS_SLICE = "SONNET_WITH_OPUS_SLICE"

# Model aliases used by the Claude Code subagent backend and their public model ids.
MODEL_IDS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "fable": "claude-fable-5-1",
}

EMPTY_RESULT = "NOT LOCATED — CURRENT STANDARD REVIEWED"
# The honest rendered state for a cell that stays empty while a standard was only SAMPLED (Task 2b,
# 2026-09-13): "reviewed" may not be claimed for a standard the locator saw 22% of. Both strings are
# workbook State Vocabulary entries.
EMPTY_RESULT_INCOMPLETE = "NOT LOCATED — NOT YET RECOVERED"

# Task 2c (2026-09-13): where a cell would go empty and a standard was only sampled (coverage RETRIEVED),
# the locator continues over that standard's unretrieved chunks in further calls until the standard is
# exhausted or a candidate survives verification. Calls are issued in rounds so a survivor stops the
# spend early; each round issues up to this many batch calls per standard.
EXHAUST_CALLS_PER_ROUND = 4

# Task 3 (2026-09-13): the opus slice also covers a caveated accept that would reach the author's card —
# primary verdict ACCEPT_WITH_CAVEAT at a PARTIAL floor, or raising one of these hazards — because that is
# the shape of a planted near-miss and the thing the author actually sees. Fired only on candidates the
# allocation keeps (or shows as an English witness); rejections never need it.
CAVEAT_SLICE_HAZARDS = ("SEMANTIC_FLOOR", "SAME_WORD_DIFFERENT_MEANING")
ROUTE_CAVEATED_ACCEPT = "CAVEATED_ACCEPT"

# Registry hosts RETIRED by the author (2026-09-12). A retired host is never requested, for any purpose:
# not by the corpus builder, not by the fetch audit, not by an adapter's crawl. Rows still ratified on a
# retired host (BSR-EO-03 in v2.25r2) build as HOST_RETIRED with no corpus, and any cached chunks are dropped.
RETIRED_HOSTS = {
    "goarch.org": "retired 2026-09-12 — its bot check fails for human users in an ordinary browser, so a citation "
                  "there cannot be audited by a reader; BSR-EO-07 re-hosted to acrod.org (BSR-EO-14 goarchdiocese.ca)",
}


def newest_workbook():
    files = sorted(glob.glob(os.path.join(DATA_SOURCES, "*.xlsx")))
    if not files:
        raise FileNotFoundError("no workbook in data-sources/sjn/")
    return files[-1]


def ensure_dirs():
    for d in (RUNS_DIR, PACKETS_DIR, FETCH_CACHE, CHUNK_DIR, JOBS_DIR, CALIBRATION_DIR, ARCHIVE_DIR):
        os.makedirs(d, exist_ok=True)
