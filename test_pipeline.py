import asyncio
from pipeline.orchestrator import ClinicalPipeline
from retrieval.pubmed_retriever import PubMedRetriever
from retrieval.vector_store import ClinicalVectorStore
from retrieval.hybrid_search import HybridSearch

_vector_store = ClinicalVectorStore()
_hybrid_search = HybridSearch(vector_store=_vector_store)
_pubmed_retriever = PubMedRetriever()

pipeline = ClinicalPipeline(pubmed=_pubmed_retriever, hybrid_search=_hybrid_search)
try:
    results = pipeline.run(symptoms=["headache"], use_cache=True)
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
