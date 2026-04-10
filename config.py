"""
Central Configuration for the Clinical Intelligence System.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists and override existing environment variables
load_dotenv(override=True)

# ── Project Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db")))

# ── NCBI / PubMed ─────────────────────────────────────────────────────────────
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
PUBMED_MAX_RESULTS = int(os.getenv("PUBMED_MAX_RESULTS", "10"))

# ── LLM Configuration ─────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Ollama (Local) ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ── Execution & Caching ────────────────────────────────────────────────────────
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
ENABLE_PARALLEL_RETRIEVAL = os.getenv("ENABLE_PARALLEL_RETRIEVAL", "true").lower() == "true"

# ── Embeddings ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "menadsa/S-Bio_ClinicalBERT")
EMBEDDING_FALLBACK = os.getenv("EMBEDDING_FALLBACK_MODEL", "all-MiniLM-L6-v2")

# ── ChromaDB ───────────────────────────────────────────────────────────────────
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "clinical_documents")

# ── Retrieval ──────────────────────────────────────────────────────────────────
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.4"))  # 0=full semantic, 1=full BM25

# ── Safety Thresholds ──────────────────────────────────────────────────────────
CONFIDENCE_HIGH = 0.7
CONFIDENCE_MEDIUM = 0.4
MAX_DIAGNOSES = 10

# ── Prompt Files ───────────────────────────────────────────────────────────────
def load_prompt(stage: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_file = PROMPTS_DIR / f"{stage}.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

# ── Validation ─────────────────────────────────────────────────────────────────
def validate_config() -> dict:
    """Check configuration and return status of each component."""
    status = {
        "ncbi_configured": bool(NCBI_EMAIL and NCBI_EMAIL != "your.email@example.com"),
        "ollama_url": OLLAMA_BASE_URL,
        "ollama_model": OLLAMA_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "chroma_dir": str(CHROMA_DIR),
        "chroma_dir_exists": CHROMA_DIR.exists(),
    }
    return status
