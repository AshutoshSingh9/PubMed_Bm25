"""
Dashboard API — FastAPI backend for the Visual NLP Dashboard.
Exposes retrieval internals for visualization.
"""

import time
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from retrieval.vector_store import ClinicalVectorStore
from retrieval.hybrid_search import HybridSearch
from retrieval.pubmed_retriever import PubMedRetriever
from pipeline.orchestrator import ClinicalPipeline
from pydantic import BaseModel
import config
import sqlite3
import json
from datetime import datetime

app = FastAPI(title="Clinical Intelligence NLP Dashboard API")

# Initialize SQLite Database for Logging
def init_db():
    conn = sqlite3.connect("clinical_logs.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nlp_test_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  query TEXT,
                  diagnosis TEXT,
                  critic TEXT,
                  safety TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (lazy loaded)
_vector_store = None
_hybrid_search = None
_pubmed_retriever = None

def get_searcher():
    global _vector_store, _hybrid_search, _pubmed_retriever
    if _hybrid_search is None:
        _vector_store = ClinicalVectorStore()
        _hybrid_search = HybridSearch(vector_store=_vector_store)
        _pubmed_retriever = PubMedRetriever()
        
    return _hybrid_search

class SearchRequest(BaseModel):
    q: str
    alpha: Optional[float] = None
    top_k: int = 5

@app.post("/search")
async def search(req: SearchRequest):
    q = req.q
    alpha = req.alpha
    top_k = req.top_k
    start_time = time.time()
    searcher = get_searcher()
    
    if _pubmed_retriever.is_configured:
        # Fetch directly from PubMed
        try:
            optimized_q = _pubmed_retriever.build_clinical_query([q])
            papers = _pubmed_retriever.search(optimized_q, max_results=3, use_cache=False)
            if papers:
                _vector_store.add_pubmed_papers(papers)
                all_docs = _vector_store.query("", top_k=100) # Re-cache
        except Exception as e:
            print(f"PubMed Ingest Error: {e}")

    results = searcher.search_detailed(q, top_k=top_k, alpha=alpha)
    latency = (time.time() - start_time) * 1000
    
    results["stats"]["latency_ms"] = round(latency, 2)
    return results

class DiagnoseRequest(BaseModel):
    symptoms: list[str]

@app.post("/diagnose")
async def diagnose(req: DiagnoseRequest):
    searcher = get_searcher()
    pipeline = ClinicalPipeline(pubmed=_pubmed_retriever, hybrid_search=searcher)
    
    try:
        results = pipeline.run(
            symptoms=req.symptoms,
            use_cache=True
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            # Graceful Quota Handle
            return {
                "diagnosis_stage": {"error": "Google Gemini API Limit Reached (Max 5 Requests Per Minute). Please wait 60 seconds before searching again."},
                "critic_stage": {},
                "safety_stage": {}
            }
        
        # General unhandled LLM Exception
        return {
            "diagnosis_stage": {"error": f"LLM Generation Pipeline Failed: {error_msg}"},
            "critic_stage": {},
            "safety_stage": {}
        }
    
    # Save to SQLite Database
    try:
        conn = sqlite3.connect("clinical_logs.db")
        c = conn.cursor()
        c.execute("INSERT INTO nlp_test_logs (timestamp, query, diagnosis, critic, safety) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(),
                   ", ".join(req.symptoms),
                   json.dumps(results.get("diagnosis_stage", {})),
                   json.dumps(results.get("critic_stage", {})),
                   json.dumps(results.get("safety_stage", {}))))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log to DB: {e}")
        
    return results

@app.get("/stats")
async def stats():
    searcher = get_searcher()
    return {
        "vector_store": _vector_store.get_stats(),
        "config": {
            "alpha": searcher.alpha,
            "embedding_model": config.EMBEDDING_MODEL
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
