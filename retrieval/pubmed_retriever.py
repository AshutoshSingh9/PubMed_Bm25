"""
PubMed Retriever — Fetches biomedical literature from NCBI PubMed via Bio.Entrez.

Provides structured paper data (title, abstract, PMID, authors, date) to feed
into the RAG pipeline as clinical context for the diagnostic stages.
"""

import logging
import time
import functools
from typing import Optional

from Bio import Entrez, Medline

import config

logger = logging.getLogger(__name__)


class PubMedRetriever:
    """Retrieves biomedical papers from PubMed using NCBI Entrez API."""

    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        self.email = email or config.NCBI_EMAIL
        self.api_key = api_key or config.NCBI_API_KEY
        self.max_results = config.PUBMED_MAX_RESULTS

        # NCBI requires an email
        if self.email and self.email != "your.email@example.com":
            Entrez.email = self.email
            if self.api_key:
                Entrez.api_key = self.api_key
            self._configured = True
        else:
            self._configured = False
            logger.warning(
                "NCBI email not configured. PubMed retrieval is disabled. "
                "Set NCBI_EMAIL in your .env file."
            )

    @property
    def is_configured(self) -> bool:
        return self._configured

    @functools.lru_cache(maxsize=128)
    def _execute_search(self, query: str, max_results: int):
        """Hidden cached search execution."""
        # Step 1: Search for PMIDs
        logger.info(f"Searching PubMed: '{query}' (max={max_results})")
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            sort="relevance",
            usehistory="y",
        )
        search_results = Entrez.read(handle)
        handle.close()

        id_list = search_results.get("IdList", [])
        if not id_list:
            logger.info("No PubMed results found.")
            return []

        logger.info(f"Found {len(id_list)} PubMed IDs: {id_list[:5]}...")

        # Step 2: Fetch full records in Medline format
        time.sleep(0.34)  # Rate limit: ~3 req/sec without API key
        handle = Entrez.efetch(
            db="pubmed",
            id=id_list,
            rettype="medline",
            retmode="text",
        )
        records = list(Medline.parse(handle))
        handle.close()

        # Step 3: Parse into structured dicts
        papers = []
        for record in records:
            paper = {
                "title": record.get("TI", "No title"),
                "abstract": record.get("AB", "No abstract available"),
                "pmid": record.get("PMID", ""),
                "authors": ", ".join(record.get("AU", [])),
                "date": record.get("DP", "Unknown date"),
                "journal": record.get("JT", "Unknown journal"),
                "mesh_terms": record.get("MH", []),
            }
            papers.append(paper)

        logger.info(f"Retrieved {len(papers)} papers from PubMed.")
        return papers

    def search(self, query: str, max_results: Optional[int] = None, use_cache: bool = True) -> list[dict]:
        """
        Search PubMed for papers matching a clinical query.

        Args:
            query: Clinical search query (e.g., "chest pain differential diagnosis")
            max_results: Max number of papers to return (default from config)
            use_cache: If true, uses LRU cache to avoid redundant network calls

        Returns:
            List of dicts with keys: title, abstract, pmid, authors, date, journal
        """
        if not self._configured:
            logger.warning("PubMed retrieval skipped — NCBI not configured.")
            return []

        max_results = max_results or self.max_results

        try:
            if use_cache:
                return self._execute_search(query, max_results)
            else:
                return self._execute_search.__wrapped__(self, query, max_results)
        except Exception as e:
            logger.error(f"PubMed retrieval failed: {e}")
            return []

    def format_context(self, papers: list[dict], max_papers: int = 5) -> str:
        """
        Format retrieved papers into a context string for LLM prompt injection.

        Args:
            papers: List of paper dicts from search()
            max_papers: Max papers to include in context

        Returns:
            Formatted string for prompt injection
        """
        if not papers:
            return "No biomedical literature retrieved."

        context_parts = []
        for i, paper in enumerate(papers[:max_papers], 1):
            abstract_preview = paper["abstract"][:500]
            if len(paper["abstract"]) > 500:
                abstract_preview += "..."

            context_parts.append(
                f"--- Paper {i} (PMID: {paper['pmid']}) ---\n"
                f"Title: {paper['title']}\n"
                f"Journal: {paper['journal']} ({paper['date']})\n"
                f"Authors: {paper['authors']}\n"
                f"Abstract: {abstract_preview}\n"
            )

        return "\n".join(context_parts)

    def build_clinical_query(self, symptoms: list[str], conditions: list[str] = None) -> str:
        """
        Build an optimized PubMed query from symptoms and conditions using Groq LLM.
        Directly optimizes conversational language into academic search parameters.
        """
        combined = " ".join(symptoms)
        if conditions:
            combined += " " + " ".join(conditions)
            
        try:
            from groq import Groq
            import config
            client = Groq(api_key=config.GROQ_API_KEY)
            resp = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Extract 2-4 essential medical/clinical keywords from the query to search PubMed. Omit all verbs, adverbs, and conversational filler (e.g., summarize, findings, doctor, order, recent, trials, patient). Output ONLY the academic keywords separated by spaces. Example output: 'glioblastoma immunotherapy' or 'gut microbiome alzheimer'"},
                    {"role": "user", "content": combined}
                ],
                temperature=0.0
            ) # Fast translation (~300ms)
            optimized = resp.choices[0].message.content.strip().replace('"', '').replace("'", "")
            logger.info(f"LLM Optimized PubMed Query: '{optimized}' (Original: {combined})")
            return optimized
        except Exception as e:
            logger.warning(f"Groq query optimization failed: {e}. Falling back to syntax combination.")
            # Fallback
            symptom_query = " OR ".join(f'"{s}"' for s in symptoms if s)
            return symptom_query
