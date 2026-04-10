"""
ChromaDB Vector Store — Persistent storage and retrieval of biomedical document embeddings.

Manages document indexing and semantic similarity search using ChromaDB as the
backend vector database, with biomedical embeddings from Bio_ClinicalBERT.
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

import config

logger = logging.getLogger(__name__)


class ClinicalVectorStore:
    """ChromaDB-backed vector store for clinical documents using ONNX models."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_dir: Optional[str] = None,
    ):
        self.collection_name = collection_name or config.CHROMA_COLLECTION
        self.persist_dir = persist_dir or str(config.CHROMA_DIR)
        
        # Use ChromaDB's robust Default Embedding Function (ONNX MiniLM) which bypasses PyTorch/HuggingFace bugs
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create the collection with the robust embedding function
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

        logger.info(
            f"Vector store initialized: collection='{self.collection_name}', "
            f"documents={self.collection.count()}, persist_dir='{self.persist_dir}'"
        )

    def add_documents(
        self,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> int:
        """
        Add documents to the vector store.
        """
        if not texts:
            return 0

        # Generate IDs if not provided
        if ids is None:
            existing_count = self.collection.count()
            ids = [f"doc_{existing_count + i}" for i in range(len(texts))]

        # Default metadata if not provided
        if metadatas is None:
            metadatas = [{"source": "manual"} for _ in texts]

        # Add to ChromaDB (It automatically generates embeddings via embedding_function)
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"Added {len(texts)} documents to vector store. Total: {self.collection.count()}")
        return len(texts)

    def query(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Query the vector store for similar documents.
        """
        top_k = top_k or config.RAG_TOP_K

        if self.collection.count() == 0:
            logger.warning("Vector store is empty. No results returned.")
            return []

        # Query ChromaDB (It automatically encodes the query text)
        query_params = {
            "query_texts": [query_text],
            "n_results": min(top_k, self.collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_params["where"] = where

        results = self.collection.query(**query_params)

        # Format results
        formatted = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                    "id": results["ids"][0][i] if results["ids"] else f"result_{i}",
                })

        return formatted

    def add_pubmed_papers(self, papers: list[dict]) -> int:
        """
        Index PubMed papers into the vector store.
        """
        if not papers:
            return 0

        texts = []
        metadatas = []
        ids = []

        for paper in papers:
            text = f"{paper['title']}\n\n{paper['abstract']}"
            texts.append(text)

            metadatas.append({
                "source": "pubmed",
                "pmid": paper.get("pmid", ""),
                "title": paper.get("title", ""),
                "journal": paper.get("journal", ""),
                "date": paper.get("date", ""),
            })

            ids.append(f"pubmed_{paper.get('pmid', id(paper))}")

        return self.add_documents(texts, metadatas, ids)

    def clear(self):
        """Delete and recreate the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Cleared vector store collection: {self.collection_name}")

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        return {
            "collection": self.collection_name,
            "document_count": self.collection.count(),
            "persist_dir": self.persist_dir,
            "embedding_model": "chroma-onnx-default",
        }
