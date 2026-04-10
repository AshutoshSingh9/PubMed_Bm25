"""
Stage 1 — Diagnostic Reasoning.

Analyzes patient symptoms, history, and genetic data to generate
ranked differential diagnoses with recommended tests and red flags.
"""

import logging
from typing import Optional

import config
from pipeline.llm_provider import LLMProvider
from pipeline.response_parser import parse_diagnosis_response
from pipeline.token_optimizer import build_optimized_prompt

logger = logging.getLogger(__name__)


class DiagnosticStage:
    """Stage 1: Generate differential diagnoses from patient data."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or LLMProvider()
        self.prompt_template = config.load_prompt("diagnostician")

    def run(
        self,
        patient_data: str,
        retrieved_context: str = "",
        variant_context: str = "",
    ) -> dict:
        """
        Execute diagnostic reasoning.

        Args:
            patient_data: Formatted patient symptoms and history
            retrieved_context: Retrieved biomedical literature context
            variant_context: Parsed genetic/variant data context

        Returns:
            Parsed diagnosis stage dict
        """
        logger.info("Stage 1 — Diagnostic Reasoning: Starting...")

        # Build optimized prompt
        user_prompt = build_optimized_prompt(
            patient_data=patient_data,
            retrieved_context=retrieved_context or "No biomedical literature retrieved.",
            variant_context=variant_context or "No genetic/variant data provided.",
            prompt_template=self.prompt_template,
        )

        # Call LLM
        system_msg = (
            "You are a clinical diagnostician. Respond ONLY with valid JSON. "
            "No explanatory text outside the JSON structure."
        )

        raw_response = self.llm.generate(system_msg, user_prompt)
        logger.info(f"Stage 1 — Raw response length: {len(raw_response)} chars")

        # Parse response
        result = parse_diagnosis_response(raw_response)
        result["_stage"] = "diagnosis"
        result["_raw_length"] = len(raw_response)

        # Validate minimum structure
        diag = result.get("diagnosis_stage", {})
        conditions = diag.get("possible_conditions", [])
        logger.info(
            f"Stage 1 — Complete: {len(conditions)} conditions, "
            f"{len(diag.get('recommended_tests', []))} tests, "
            f"{len(diag.get('red_flags', []))} red flags"
        )

        return result
