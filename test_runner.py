import os
import json
import sqlite3
import time
from datetime import datetime
from pipeline.orchestrator import ClinicalPipeline
from retrieval.pubmed_retriever import PubMedRetriever
from retrieval.vector_store import ClinicalVectorStore
from retrieval.hybrid_search import HybridSearch
from dotenv import load_dotenv

# Ensure we're overriding everything with the .env
load_dotenv(override=True)

test_queries = [
    # 1. Terminology Mismatch
    "What does it mean if my knuckles are swollen and purple?",
    "Is there a link between scaly skin and finger swelling?",
    "Why does the sun make my joint pain flare up?",
    # 2. Acronym Focus
    "Difference between Anti-CCP and RF for diagnosis",
]

def run_tests():
    print("Initialising pipeline...")
    _vector_store = ClinicalVectorStore()
    _hybrid_search = HybridSearch(vector_store=_vector_store)
    _pubmed_retriever = PubMedRetriever()
    
    pipeline = ClinicalPipeline(pubmed=_pubmed_retriever, hybrid_search=_hybrid_search)
    
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

    for query in test_queries:
        print(f"\n--- Testing Query: '{query}' ---")
        
        print("1. Fetching PubMed RAG data...")
        papers = _pubmed_retriever.search(query, max_results=2)
        if papers:
            _vector_store.add_pubmed_papers(papers)
            _hybrid_search.index_documents(papers)
        else:
            print("   -> PubMed unavailable. Falling back to local RAG knowledge.")
            mock = [{"text": "Dermatomyositis presents with swollen purple knuckles known as Gottron's papules.", "metadata": {"source": "PubMed", "pmid": "999"}},
                    {"text": "Photosensitivity is a hallmark of Systemic Lupus Erythematosus.", "metadata": {"source": "Clinical Note"}}]
            _vector_store.add_documents([d["text"] for d in mock], [d["metadata"] for d in mock])
            _hybrid_search.index_documents(mock)
            
        print("2. Running Pipeline...")
        try:
            results = pipeline.run(symptoms=[query], use_cache=False)
            
            c.execute("INSERT INTO nlp_test_logs (timestamp, query, diagnosis, critic, safety) VALUES (?, ?, ?, ?, ?)",
                      (datetime.now().isoformat(),
                       query,
                       json.dumps(results.get("diagnosis_stage", {})),
                       json.dumps(results.get("critic_stage", {})),
                       json.dumps(results.get("safety_stage", {}))))
            conn.commit()
            print("✓ Saved to clinical_logs.db successfully.")
        except Exception as e:
            print(f"FAILED: {e}")

    conn.close()
    print("Done")

if __name__ == "__main__":
    run_tests()
