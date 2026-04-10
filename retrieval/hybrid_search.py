"""
Hybrid Search — Combines BM25 keyword search with semantic vector search.

Uses Reciprocal Rank Fusion (RRF) to merge rankings from both retrieval methods,
balancing exact keyword matching with semantic understanding for clinical queries.
"""

import logging
import functools
import re
from typing import Optional

import numpy as np
from rank_bm25 import BM25Okapi

import config
from retrieval.vector_store import ClinicalVectorStore

logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid retrieval combining BM25 keyword search with ChromaDB semantic search."""

    def __init__(
        self,
        vector_store: Optional[ClinicalVectorStore] = None,
        alpha: Optional[float] = None,
    ):
        """
        Args:
            vector_store: ClinicalVectorStore instance for semantic search
            alpha: Weight for BM25 (0.0 = full semantic, 1.0 = full BM25)
        """
        self.vector_store = vector_store
        self.alpha = alpha if alpha is not None else config.HYBRID_ALPHA
        self.bm25_index = None
        self.bm25_corpus = []
        self.bm25_metadata = []

    def index_documents(self, documents: list[dict]):
        """
        Index documents for BM25 search.

        Args:
            documents: List of dicts with 'text' and optional 'metadata' keys
        """
        self.bm25_corpus = []
        self.bm25_metadata = []

        for doc in documents:
            text = doc.get("text", "")
            self.bm25_corpus.append(text)
            self.bm25_metadata.append(doc.get("metadata", {}))

        # Tokenize for BM25
        tokenized_corpus = [self._tokenize(doc) for doc in self.bm25_corpus]
        if not tokenized_corpus:
            self.bm25_index = None
        else:
            self.bm25_index = BM25Okapi(tokenized_corpus)

        logger.info(f"BM25 index built with {len(self.bm25_corpus)} documents.")

    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "of", "by", "is", "are", "was", "were", "be", "been", "being", "patient",
        "presents", "history", "years", "old", "who", "has", "had", "have",
        "without", "day", "days"
    }

    def _tokenize(self, text: str) -> list[str]:
        """Stopword-filtered tokenization for BM25."""
        tokens = re.findall(r'\b\w+\b', text.lower())
        return [t for t in tokens if t not in self.STOPWORDS]

    @functools.lru_cache(maxsize=128)
    def _execute_search(self, query: str, top_k: int, alpha: float) -> list[dict]:
        bm25_results = self._bm25_search(query, top_k * 2)
        semantic_results = self._semantic_search(query, top_k * 2)

        # Merge using Reciprocal Rank Fusion
        fused = self._reciprocal_rank_fusion(bm25_results, semantic_results, alpha)

        return fused[:top_k]

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        alpha: Optional[float] = None,
        use_cache: bool = True,
    ) -> list[dict]:
        """
        Perform hybrid search combining BM25 and semantic scores.

        Args:
            query: Search query
            top_k: Number of results
            alpha: Override default BM25 weight
            use_cache: Use LRU cache for search results

        Returns:
            List of dicts with: text, score, bm25_score, semantic_score, metadata
        """
        top_k = top_k or config.RAG_TOP_K
        alpha = alpha if alpha is not None else self.alpha

        try:
            if use_cache:
                return self._execute_search(query, top_k, alpha)
            else:
                return self._execute_search.__wrapped__(self, query, top_k, alpha)
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    def search_detailed(
        self,
        query: str,
        top_k: Optional[int] = None,
        alpha: Optional[float] = None,
    ) -> dict:
        """
        Perform hybrid search and return full intermediate steps for visualization.

        Returns:
            Dict with: query, tokens, bm25_results, semantic_results, fused_results
        """
        top_k = top_k or config.RAG_TOP_K
        alpha = alpha if alpha is not None else self.alpha
        
        tokenized_query = self._tokenize(query)
        bm25_results = self._bm25_search(query, top_k * 2)
        semantic_results = self._semantic_search(query, top_k * 2)
        fused = self._reciprocal_rank_fusion(bm25_results, semantic_results, alpha)

        return {
            "query": query,
            "tokens": tokenized_query,
            "bm25_results": bm25_results,
            "semantic_results": semantic_results,
            "fused_results": fused[:top_k],
            "stats": {
                "bm25_count": len(bm25_results),
                "semantic_count": len(semantic_results),
                "alpha": alpha,
            }
        }

    def _bm25_search(self, query: str, top_k: int) -> list[dict]:
        """Perform BM25 keyword search."""
        if self.bm25_index is None or not self.bm25_corpus:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25_index.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0:
                results.append({
                    "text": self.bm25_corpus[idx],
                    "score": float(scores[idx]),
                    "rank": rank + 1,
                    "metadata": self.bm25_metadata[idx],
                    "source": "bm25",
                })

        return results

    def _semantic_search(self, query: str, top_k: int) -> list[dict]:
        """Perform semantic vector search via ChromaDB."""
        if self.vector_store is None:
            return []

        results = self.vector_store.query(query, top_k=top_k)

        filtered_results = []
        rank = 1
        for result in results:
            # Enforce a minimum semantic similarity threshold (cosine similarity > 10%)
            if result.get("score", 0) > 0.10:
                result["rank"] = rank
                result["source"] = "semantic"
                filtered_results.append(result)
                rank += 1

        return filtered_results

    def _reciprocal_rank_fusion(
        self,
        bm25_results: list[dict],
        semantic_results: list[dict],
        alpha: float,
        k: int = 60,
    ) -> list[dict]:
        """
        Merge two ranked lists using Reciprocal Rank Fusion (RRF).

        RRF score = alpha * (1 / (k + bm25_rank)) + (1-alpha) * (1 / (k + semantic_rank))

        Args:
            bm25_results: BM25 ranked results
            semantic_results: Semantic ranked results
            alpha: BM25 weight (0.0 to 1.0)
            k: RRF constant (default 60, standard in literature)

        Returns:
            Merged and re-ranked results
        """
        doc_scores: dict = {}

        # Score BM25 results
        for result in bm25_results:
            doc_key = result["text"][:200]  # Use text prefix as key
            if doc_key not in doc_scores:
                doc_scores[doc_key] = {
                    "text": result["text"],
                    "metadata": result["metadata"],
                    "bm25_score": 0.0,
                    "semantic_score": 0.0,
                    "rrf_score": 0.0,
                }
            doc_scores[doc_key]["bm25_score"] = result["score"]
            doc_scores[doc_key]["rrf_score"] += alpha * (1.0 / (k + result["rank"]))

        # Score semantic results
        for result in semantic_results:
            doc_key = result["text"][:200]
            if doc_key not in doc_scores:
                doc_scores[doc_key] = {
                    "text": result["text"],
                    "metadata": result["metadata"],
                    "bm25_score": 0.0,
                    "semantic_score": 0.0,
                    "rrf_score": 0.0,
                }
            doc_scores[doc_key]["semantic_score"] = result.get("score", 0.0)
            doc_scores[doc_key]["rrf_score"] += (1 - alpha) * (1.0 / (k + result["rank"]))

        # Sort by fused RRF score
        fused = sorted(doc_scores.values(), key=lambda x: x["rrf_score"], reverse=True)

        # Add final composite score (normalized to 0-100%)
        max_possible_score = 1.0 / (k + 1)
        for result in fused:
            # Map the RRF score to a percentage based on the theoretical maximum
            normalized = (result["rrf_score"] / max_possible_score) * 100.0
            result["score"] = min(100.0, normalized)

        return fused

    def format_context(self, results: list[dict], max_results: int = 5) -> str:
        """Format search results into a context string for LLM prompt injection."""
        if not results:
            return "No relevant clinical documents retrieved."

        parts = []
        for i, result in enumerate(results[:max_results], 1):
            text_preview = result["text"][:600]
            if len(result["text"]) > 600:
                text_preview += "..."

            source_info = result.get("metadata", {}).get("source", "document")
            pmid = result.get("metadata", {}).get("pmid", "")
            pmid_str = f" (PMID: {pmid})" if pmid else ""

            parts.append(
                f"--- Context {i} [{source_info}{pmid_str}] (relevance: {result['score']:.3f}) ---\n"
                f"{text_preview}\n"
            )

        return "\n".join(parts)
