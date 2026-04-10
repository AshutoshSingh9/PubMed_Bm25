"""
Pipeline Orchestrator — Runs the full 3-stage clinical reasoning pipeline.

Coordinates retrieval (PubMed + vector DB), variant parsing, and sequential
LLM stages. Optimized for token efficiency and clean error handling.
Provides both full-run and stage-by-stage execution modes.
"""

import json
import logging
import time
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor

from pipeline.llm_provider import LLMProvider
from pipeline.stage1_diagnostician import DiagnosticStage
from pipeline.stage2_critic import CriticStage
from pipeline.stage3_safety import SafetyStage
from pipeline.token_optimizer import truncate_documents
from retrieval.pubmed_retriever import PubMedRetriever
from retrieval.hybrid_search import HybridSearch
from genomics.variant_parser import VariantParser
from genomics.variant_annotator import VariantAnnotator

logger = logging.getLogger(__name__)


class ClinicalPipeline:
    """
    Full 3-stage clinical intelligence pipeline.

    Flow:
        1. Retrieve context (PubMed + vector DB) in parallel with variant parsing
        2. Stage 1: Diagnostic reasoning
        3. Stage 2: Critical evaluation
        4. Stage 3: Safety validation
        5. Return combined structured output
    """

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        pubmed: Optional[PubMedRetriever] = None,
        hybrid_search: Optional[HybridSearch] = None,
        progress_callback: Optional[Callable] = None,
    ):
        self.llm = llm or LLMProvider()
        self.pubmed = pubmed or PubMedRetriever()
        self.hybrid_search = hybrid_search
        self.variant_parser = VariantParser()
        self.variant_annotator = VariantAnnotator()
        self.progress_callback = progress_callback

        # Initialize stages with shared LLM
        self.stage1 = DiagnosticStage(self.llm)
        self.stage2 = CriticStage(self.llm)
        self.stage3 = SafetyStage(self.llm)

    def _update_progress(self, stage: str, message: str, progress: float):
        """Send progress update via callback (for Streamlit UI)."""
        if self.progress_callback:
            self.progress_callback(stage, message, progress)
        logger.info(f"[{stage}] {message} ({progress:.0%})")

    def run(
        self,
        symptoms: list[str],
        patient_history: str = "",
        age: Optional[int] = None,
        sex: Optional[str] = None,
        genetic_data: str = "",
        additional_context: str = "",
        use_cache: bool = True,
    ) -> dict:
        """
        Execute the full 3-stage clinical pipeline.

        Args:
            symptoms: List of patient symptoms
            patient_history: Medical history text
            age: Patient age
            sex: Patient sex
            genetic_data: Raw genetic/variant data (FASTA, VCF, or text)
            additional_context: Any additional clinical context
            use_cache: Use optimized caches
            
        Returns:
            Combined dict with diagnosis_stage, critic_stage, safety_stage, and metadata
        """
        start_time = time.time()
        phase_timings = {}
        self._update_progress("init", "Preparing clinical analysis...", 0.0)

        # ── Build patient data string ──────────────────────────────────────
        patient_data = self._format_patient_data(
            symptoms, patient_history, age, sex, additional_context
        )

        # ── Parallel Retrieval Phase ───────────────────────────────────────
        self._update_progress("retrieval", "Retrieving context & parsing genetics...", 0.10)
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_context = executor.submit(self._retrieve_context, symptoms, use_cache)
            future_variant = executor.submit(self._parse_genetic_data, genetic_data, use_cache)
            
            retrieved_context = future_context.result()
            variant_context = future_variant.result()
        phase_timings["retrieval_and_genomics"] = time.time() - t0

        # ── Stage 1: Diagnostic Reasoning ──────────────────────────────────
        self._update_progress("stage1", "Stage 1: Generating differential diagnoses...", 0.30)
        t1 = time.time()
        stage1_result = self.stage1.run(patient_data, retrieved_context, variant_context)
        phase_timings["stage1"] = time.time() - t1

        # ── Stage 2: Critical Evaluation ───────────────────────────────────
        self._update_progress("stage2", "Stage 2: Evaluating diagnostic reasoning...", 0.55)
        t2 = time.time()
        stage2_result = self.stage2.run(patient_data, stage1_result, retrieved_context)
        phase_timings["stage2"] = time.time() - t2

        # ── Stage 3: Safety Validation ─────────────────────────────────────
        self._update_progress("stage3", "Stage 3: Validating safety...", 0.80)
        t3 = time.time()
        stage3_result = self.stage3.run(
            patient_data, stage1_result, stage2_result, retrieved_context
        )
        phase_timings["stage3"] = time.time() - t3

        # ── Combine Results ────────────────────────────────────────────────
        self._update_progress("complete", "Analysis complete!", 1.0)

        elapsed = time.time() - start_time

        combined = {
            "diagnosis_stage": stage1_result.get("diagnosis_stage", {}),
            "critic_stage": stage2_result.get("critic_stage", {}),
            "safety_stage": stage3_result.get("safety_stage", {}),
            "metadata": {
                "total_time_seconds": round(elapsed, 2),
                "phase_timings": {k: round(v, 2) for k, v in phase_timings.items()},
                "model": self.llm.get_info(),
                "symptoms_count": len(symptoms),
                "has_genetic_data": bool(genetic_data),
                "retrieval_available": self.pubmed.is_configured,
            },
        }

        logger.info(f"Pipeline complete in {elapsed:.1f}s")
        return combined

    def _format_patient_data(
        self,
        symptoms: list[str],
        history: str,
        age: Optional[int],
        sex: Optional[str],
        additional: str,
    ) -> str:
        """Build the patient data section for prompts."""
        parts = []

        # Demographics
        demo_parts = []
        if age:
            demo_parts.append(f"Age: {age}")
        if sex:
            demo_parts.append(f"Sex: {sex}")
        if demo_parts:
            parts.append("## Demographics")
            parts.append(", ".join(demo_parts))

        # Symptoms
        parts.append("\n## Presenting Symptoms")
        for s in symptoms:
            parts.append(f"- {s}")

        # History
        if history:
            parts.append(f"\n## Medical History\n{history}")

        # Additional
        if additional:
            parts.append(f"\n## Additional Context\n{additional}")

        return "\n".join(parts)

    def _retrieve_context(self, symptoms: list[str], use_cache: bool = True) -> str:
        """Retrieve biomedical context from PubMed and vector store."""
        context_parts = []
        
        def fetch_pubmed():
            if self.pubmed.is_configured:
                try:
                    query = self.pubmed.build_clinical_query(symptoms)
                    papers = self.pubmed.search(query, max_results=5, use_cache=use_cache)
                    # Truncate to top 3 for token efficiency
                    papers = truncate_documents(
                        [{"text": p["abstract"], **p} for p in papers],
                        max_docs=3,
                        max_abstract_chars=500,
                    )
                    return self.pubmed.format_context(
                        [{"abstract": p["text"], **p} for p in papers],
                        max_papers=3,
                    )
                except Exception as e:
                    logger.warning(f"PubMed retrieval failed: {e}")
            return None

        def fetch_vector():
            if self.hybrid_search:
                try:
                    query = " ".join(symptoms)
                    results = self.hybrid_search.search(query, top_k=3, use_cache=use_cache)
                    if results:
                        return self.hybrid_search.format_context(results, max_results=3)
                except Exception as e:
                    logger.warning(f"Vector store retrieval failed: {e}")
            return None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_pubmed = executor.submit(fetch_pubmed)
            future_vector = executor.submit(fetch_vector)
            
            res_pubmed = future_pubmed.result()
            res_vector = future_vector.result()
            
            if res_pubmed: context_parts.append(res_pubmed)
            if res_vector: context_parts.append(res_vector)

        return "\n\n".join(context_parts) if context_parts else ""

    def _parse_genetic_data(self, genetic_data: str, use_cache: bool = True) -> str:
        """Parse and annotate genetic data."""
        if not genetic_data or not genetic_data.strip():
            return ""

        try:
            parsed = self.variant_parser.parse_upload(genetic_data)

            # Annotate variants
            variants = parsed.get("variants", [])
            if variants:
                annotated = self.variant_annotator.annotate(variants, use_cache=use_cache)
                return self.variant_annotator.format_for_prompt(annotated)

            # Format sequences
            sequences = parsed.get("sequences", [])
            if sequences:
                return self.variant_parser.format_for_prompt(sequences=sequences)

            return self.variant_parser.format_for_prompt(variants=variants)

        except Exception as e:
            logger.warning(f"Genetic data parsing failed: {e}")
            return f"Genetic data provided but parsing failed: {e}"

    def get_system_status(self) -> dict:
        """Get the status of all pipeline components."""
        return {
            "llm": self.llm.check_health(),
            "pubmed": {
                "configured": self.pubmed.is_configured,
            },
            "vector_store": bool(self.hybrid_search),
            "genomics": {
                "variant_parser": "ready",
                "variant_annotator": f"{len(self.variant_annotator.list_genes())} genes loaded",
            },
        }
