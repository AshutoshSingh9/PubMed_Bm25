import sys
import json
from retrieval.vector_store import ClinicalVectorStore
from retrieval.hybrid_search import HybridSearch
from retrieval.pubmed_retriever import PubMedRetriever
import config
import logging

# Mute noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)

def print_separator():
    print("\n" + "="*80 + "\n")

def main():
    print("Initializing Clinical Intelligence Backend...")
    try:
        vector_store = ClinicalVectorStore()
        searcher = HybridSearch(vector_store=vector_store)
        pubmed = PubMedRetriever()
        print("Backend Initialized Successfully!")
        print(f"Using Embedding Model: {config.EMBEDDING_MODEL}")
        print("PubMed Integration: Active")
    except Exception as e:
        print(f"Failed to initialize: {e}")
        sys.exit(1)

    print_separator()
    print("Welcome to the Console Search Tester.")
    print("Type 'exit' or 'quit' to close.")
    print_separator()

    while True:
        try:
            query = input("\nEnter clinical query: ").strip()
            if not query:
                continue
            if query.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
                
            optimized_q = pubmed.build_clinical_query([query])
            print(f"\n[LLM] Translated NLP Query into Academic PubMed Query: '{optimized_q}'")

            print(f"\n[1/2] Fetching live PubMed articles for '{optimized_q}'...")
            try:
                papers = pubmed.search(optimized_q, max_results=5, use_cache=False)
                if papers:
                    print(f"      Found {len(papers)} live papers. Indexing to Vector Store...")
                    vector_store.add_pubmed_papers(papers)
                else:
                    print("      No relevant PubMed papers found.")
            except Exception as e:
                print(f"      PubMed Fetch Error: {e}")

            print("\n[2/2] Running Hybrid Reciprocal Rank Fusion (RRF)...")
            # Fetch Top 8 matches
            results = searcher.search_detailed(query, top_k=8)

            fused = results.get("fused_results", [])
            print_separator()
            if not fused:
                print("No matches found in the database.")
            else:
                print(f"Top {len(fused)} Results (RRF):\n")
                for doc in fused:
                    rank = doc.get('rank', 'N/A')
                    score = doc.get('score', 0.0)
                    meta = doc.get('metadata', {})
                    text = doc.get('text', '')
                    
                    # Clean up abstract display
                    preview = text[:300] + "..." if len(text) > 300 else text
                    
                    print(f"Rank #{rank} | Match Score: {score:.1f}%")
                    print(f"Source: {meta.get('source', 'Unknown')} | PMID: {meta.get('pmid', 'N/A')}")
                    print(f"{preview}\n")
                    
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError processing query: {e}")

if __name__ == "__main__":
    main()
