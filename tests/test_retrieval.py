import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.pubmed_retriever import PubMedRetriever
from retrieval.hybrid_search import HybridSearch
from retrieval.vector_store import ClinicalVectorStore

# ── 1. PubMed Retriever Mocks ──

DUMMY_PUBMED_SEARCH = {
    "IdList": ["11111111", "22222222"]
}

DUMMY_MEDLINE_RECORDS = [
    {
        "PMID": "11111111",
        "TI": "Dummy Title 1",
        "AB": "Dummy Abstract 1",
        "AU": ["Author A", "Author B"],
        "DP": "2024 Jan 1",
        "JT": "Journal of Testing",
        "MH": ["Mesh Term 1"]
    },
    {
        "PMID": "22222222",
        "TI": "Dummy Title 2",
        "AB": "Dummy Abstract 2",
        "AU": ["Author C"],
        "DP": "2024 Feb 1",
        "JT": "Journal of Testing",
        "MH": ["Mesh Term 2"]
    }
]

@patch('retrieval.pubmed_retriever.Entrez.esearch')
@patch('retrieval.pubmed_retriever.Entrez.read')
@patch('retrieval.pubmed_retriever.Entrez.efetch')
@patch('retrieval.pubmed_retriever.Medline.parse')
@patch('retrieval.pubmed_retriever.time.sleep', return_value=None)
def test_pubmed_search(mock_sleep, mock_medline, mock_efetch, mock_read, mock_esearch):
    mock_esearch.return_value = MagicMock()
    mock_read.return_value = DUMMY_PUBMED_SEARCH
    mock_efetch.return_value = MagicMock()
    mock_medline.return_value = iter(DUMMY_MEDLINE_RECORDS)
    
    retriever = PubMedRetriever(email="test@example.com")
    papers = retriever.search("dummy condition", max_results=2)
    
    assert len(papers) == 2
    assert papers[0]["pmid"] == "11111111"
    assert papers[0]["title"] == "Dummy Title 1"
    assert papers[1]["pmid"] == "22222222"
    
def test_build_query():
    retriever = PubMedRetriever()
    query = retriever.build_clinical_query(["headache", "fever"], ["migraine"])
    assert '"headache" OR "fever"' in query
    assert '"migraine"' in query
    assert 'diagnosis OR treatment' in query

# ── 2. Vector Store Mock ──

@patch('retrieval.vector_store.chromadb.PersistentClient')
def test_vector_store(mock_chroma_client):
    mock_client = MagicMock()
    mock_chroma_client.return_value = mock_client
    
    mock_collection = MagicMock()
    mock_collection.count.return_value = 1
    mock_client.get_or_create_collection.return_value = mock_collection
    
    mock_collection.query.return_value = {
        "ids": [["doc1"]],
        "documents": [["Doc 1 text"]],
        "metadatas": [[{"title": "Meta Title"}]],
        "distances": [[0.2]]
    }
    
    store = ClinicalVectorStore()
    res = store.query("Test Query", top_k=1)
    
    assert len(res) == 1
    assert res[0]["id"] == "doc1"
    assert res[0]["text"] == "Doc 1 text"
    assert res[0]["metadata"]["title"] == "Meta Title"

# ── 3. Hybrid Search Rank Fusion ──

def test_hybrid_search_fusion():
    searcher = HybridSearch()
    scores = searcher._reciprocal_rank_fusion([{"text":"doc1", "metadata":{}, "score":1.0, "rank":1}, {"text":"doc2", "metadata":{}, "score":1.0, "rank":2}, {"text":"doc3", "metadata":{}, "score":1.0, "rank":3}], [{"text":"doc2", "metadata":{}, "score":1.0, "rank":1}, {"text":"doc1", "metadata":{}, "score":1.0, "rank":2}, {"text":"doc4", "metadata":{}, "score":1.0, "rank":3}], alpha=0.5)
    
    scores_dict = {s["text"]: s for s in scores}
    assert "doc1" in scores_dict
    assert "doc2" in scores_dict
    assert "doc3" in scores_dict
    assert "doc4" in scores_dict
    assert abs(scores_dict["doc1"]["rrf_score"] - scores_dict["doc2"]["rrf_score"]) < 1e-5
    assert scores_dict["doc1"]["rrf_score"] > scores_dict["doc3"]["rrf_score"]
