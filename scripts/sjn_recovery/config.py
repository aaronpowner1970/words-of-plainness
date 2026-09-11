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
CALIBRATION_DIR = os.path.join(RUNS_DIR, "calibration")
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
MAX_CANDIDATES = 3

# Locator context budget: whole standards are supplied when the branch corpus fits; otherwise
# hybrid retrieval supplies the top-k chunks per standard (retrieval.py). Characters of chunk text.
LOCATOR_CONTEXT_CHARS = 60000
RETRIEVAL_TOP_K_PER_STANDARD = 6

# Model aliases used by the Claude Code subagent backend and their public model ids.
MODEL_IDS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "fable": "claude-fable-5-1",
}

EMPTY_RESULT = "NOT LOCATED — CURRENT STANDARD REVIEWED"


def newest_workbook():
    files = sorted(glob.glob(os.path.join(DATA_SOURCES, "*.xlsx")))
    if not files:
        raise FileNotFoundError("no workbook in data-sources/sjn/")
    return files[-1]


def ensure_dirs():
    for d in (RUNS_DIR, PACKETS_DIR, FETCH_CACHE, CHUNK_DIR, JOBS_DIR, CALIBRATION_DIR):
        os.makedirs(d, exist_ok=True)
