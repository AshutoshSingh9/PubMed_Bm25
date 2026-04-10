"""
Stage 2 — Critical Evaluation.

Acts as an adversarial clinical reviewer to identify logical flaws,
overconfidence, cognitive biases, and missed diagnoses in Stage 1 output.
"""

import json
import logging
from typing import Optional

import config
from pipeline.llm_provider import LLMProvider
from pipeline.response_parser import parse_critic_response
from pipeline.token_optimizer import truncate_context

logger = logging.getLogger(__name__)


class CriticStage:
    """Stage 2: Critically evaluate Stage 1 diagnostic reasoning."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or LLMProvider()
        self.prompt_template = config.load_prompt("critic")

    def run(
        self,
        patient_data: str,
        stage1_output: dict,
        retrieved_context: str = "",
    ) -> dict:
        """
        Execute critical evaluation of Stage 1 output.

        Args:
            patient_data: Original patient presentation
            stage1_output: Parsed output from Stage 1
            retrieved_context: Retrieved biomedical context

        Returns:
            Parsed critic stage dict
        """
        logger.info("Stage 2 — Critical Evaluation: Starting...")

        # Format Stage 1 output for injection
        stage1_json = json.dumps(stage1_output, indent=2, default=str)

        # Build prompt from template
        prompt = self.prompt_template.replace("{patient_data}", patient_data)
        prompt = prompt.replace("{stage1_output}", stage1_json)
        prompt = prompt.replace(
            "{retrieved_context}",
            truncate_context(retrieved_context, max_tokens=800),
        )

        system_msg = (
            "You are a strict clinical reviewer. Respond ONLY with valid JSON. "
            "Be adversarial but constructive. No text outside JSON."
        )

        raw_response = self.llm.generate(system_msg, prompt)
        logger.info(f"Stage 2 — Raw response length: {len(raw_response)} chars")

        result = parse_critic_response(raw_response)
        result["_stage"] = "critic"
        result["_raw_length"] = len(raw_response)

        critic = result.get("critic_stage", {})
        logger.info(
            f"Stage 2 — Complete: {len(critic.get('errors_found', []))} errors, "
            f"{len(critic.get('missing_conditions', []))} missing conditions, "
            f"{len(critic.get('biases_detected', []))} biases, "
            f"revision_required={critic.get('revision_required', 'N/A')}"
        )

        return result
