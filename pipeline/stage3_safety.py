"""
Stage 3 — Safety Validation.

Final audit for hallucinations, unsupported claims, missed critical
conditions, and potential harm. Classifies safety level and provides
a final APPROVE / FLAG / REJECT verdict.
"""

import json
import logging
from typing import Optional

import config
from pipeline.llm_provider import LLMProvider
from pipeline.response_parser import parse_safety_response
from pipeline.token_optimizer import truncate_context

logger = logging.getLogger(__name__)


class SafetyStage:
    """Stage 3: Safety and reliability audit of combined pipeline output."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or LLMProvider()
        self.prompt_template = config.load_prompt("safety_validator")

    def run(
        self,
        patient_data: str,
        stage1_output: dict,
        stage2_output: dict,
        retrieved_context: str = "",
    ) -> dict:
        """
        Execute safety validation on combined Stage 1 + Stage 2 outputs.

        Args:
            patient_data: Original patient presentation
            stage1_output: Parsed Stage 1 (diagnosis) output
            stage2_output: Parsed Stage 2 (critic) output
            retrieved_context: Retrieved biomedical context

        Returns:
            Parsed safety stage dict
        """
        logger.info("Stage 3 — Safety Validation: Starting...")

        # Format previous stages for injection
        stage1_json = json.dumps(stage1_output, indent=2, default=str)
        stage2_json = json.dumps(stage2_output, indent=2, default=str)

        # Build prompt
        prompt = self.prompt_template.replace("{patient_data}", patient_data)
        prompt = prompt.replace("{stage1_output}", stage1_json)
        prompt = prompt.replace("{stage2_output}", stage2_json)
        prompt = prompt.replace(
            "{retrieved_context}",
            truncate_context(retrieved_context, max_tokens=500),
        )

        system_msg = (
            "You are a clinical safety auditor. Respond ONLY with valid JSON. "
            "Prioritize patient safety above all. No text outside JSON."
        )

        raw_response = self.llm.generate(system_msg, prompt)
        logger.info(f"Stage 3 — Raw response length: {len(raw_response)} chars")

        result = parse_safety_response(raw_response)
        result["_stage"] = "safety"
        result["_raw_length"] = len(raw_response)

        safety = result.get("safety_stage", {})
        logger.info(
            f"Stage 3 — Complete: safety={safety.get('safety_level', 'N/A')}, "
            f"hallucination_risk={safety.get('hallucination_risk', 'N/A')}, "
            f"verdict={safety.get('final_verdict', 'N/A')}"
        )

        return result
