"""
Response Parser — Extracts and validates structured JSON from LLM responses.

Handles the messy reality of LLM outputs: markdown code fences, trailing text,
partial JSON, and malformed responses. Ensures the pipeline always returns
a valid structured result.
"""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ── Default Structures (fallbacks when parsing fails) ──────────────────────────

DEFAULT_DIAGNOSIS = {
    "diagnosis_stage": {
        "possible_conditions": [],
        "recommended_tests": [],
        "red_flags": [],
        "data_limitations": ["LLM response could not be parsed"],
        "reasoning_summary": "Parsing failed. See raw output.",
    }
}

DEFAULT_CRITIC = {
    "critic_stage": {
        "errors_found": [],
        "missing_conditions": [],
        "biases_detected": [],
        "confidence_assessment": {
            "overall_calibration": "UNKNOWN",
            "adjustments": [],
        },
        "revision_required": False,
        "review_summary": "Critic stage parsing failed.",
    }
}

DEFAULT_SAFETY = {
    "safety_stage": {
        "safety_level": "RISKY",
        "hallucination_risk": "HIGH",
        "critical_conditions_check": {"checked": [], "missed": []},
        "unsupported_claims": [],
        "harm_assessment": {
            "risk_level": "MEDIUM",
            "potential_harms": ["Could not validate — parsing failed"],
        },
        "issues": ["Response parsing failed; manual review required"],
        "recommendations": ["Have a medical professional review the raw output"],
        "final_verdict": "FLAG",
        "verdict_reasoning": "Automated parsing failed; flagging for manual review.",
    }
}


def extract_json(text: str) -> Optional[dict]:
    """
    Extract JSON from LLM response text.

    Handles:
        - Clean JSON
        - JSON inside ```json ... ``` code fences
        - JSON with trailing text
        - Multiple JSON objects (returns first valid one)

    Args:
        text: Raw LLM response text

    Returns:
        Parsed dict or None if no valid JSON found
    """
    if not text or not text.strip():
        return None

    # Strategy 1: Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code fence
    code_fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
    matches = code_fence_pattern.findall(text)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Strategy 3: Find JSON by brace matching
    json_str = _find_json_object(text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Strategy 4: Try to fix common issues
    cleaned = _clean_json_text(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    logger.warning("Could not extract valid JSON from LLM response.")
    return None


def _find_json_object(text: str) -> Optional[str]:
    """Find the first complete JSON object in text using brace matching."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _clean_json_text(text: str) -> str:
    """Attempt to clean common JSON issues from LLM output."""
    # Remove markdown code fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)

    # Remove leading/trailing text outside JSON
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]

    # Fix trailing commas (common LLM error)
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    return text.strip()


def parse_diagnosis_response(text: str) -> dict:
    """Parse Stage 1 (Diagnostician) response."""
    parsed = extract_json(text)
    if parsed and "diagnosis_stage" in parsed:
        return parsed
    if parsed:
        # Maybe the JSON is the inner content without the wrapper
        return {"diagnosis_stage": parsed}
    logger.warning("Using default diagnosis structure due to parsing failure.")
    result = DEFAULT_DIAGNOSIS.copy()
    result["diagnosis_stage"]["_raw_response"] = text[:2000]
    return result


def parse_critic_response(text: str) -> dict:
    """Parse Stage 2 (Critic) response."""
    parsed = extract_json(text)
    if parsed and "critic_stage" in parsed:
        return parsed
    if parsed:
        return {"critic_stage": parsed}
    logger.warning("Using default critic structure due to parsing failure.")
    result = DEFAULT_CRITIC.copy()
    result["critic_stage"]["_raw_response"] = text[:2000]
    return result


def parse_safety_response(text: str) -> dict:
    """Parse Stage 3 (Safety) response."""
    parsed = extract_json(text)
    if parsed and "safety_stage" in parsed:
        return parsed
    if parsed:
        return {"safety_stage": parsed}
    logger.warning("Using default safety structure due to parsing failure.")
    result = DEFAULT_SAFETY.copy()
    result["safety_stage"]["_raw_response"] = text[:2000]
    return result


def parse_combined_response(text: str) -> dict:
    """
    Parse a combined 3-stage response (master prompt single-call output).

    Attempts to extract all three stages from a single JSON response,
    falling back to stage-specific defaults for any missing stage.
    """
    parsed = extract_json(text)

    result = {}

    if parsed:
        # Extract each stage, using defaults for missing ones
        result["diagnosis_stage"] = parsed.get(
            "diagnosis_stage",
            DEFAULT_DIAGNOSIS["diagnosis_stage"]
        )
        result["critic_stage"] = parsed.get(
            "critic_stage",
            DEFAULT_CRITIC["critic_stage"]
        )
        result["safety_stage"] = parsed.get(
            "safety_stage",
            DEFAULT_SAFETY["safety_stage"]
        )
    else:
        result = {
            **DEFAULT_DIAGNOSIS,
            **DEFAULT_CRITIC,
            **DEFAULT_SAFETY,
        }
        result["_parsing_error"] = True
        result["_raw_response"] = text[:3000]

    return result
