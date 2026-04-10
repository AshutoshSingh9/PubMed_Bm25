"""
Token Optimizer — Manages context truncation to reduce LLM token usage.

Key strategy: Only pass top 2-3 documents with truncated abstracts.
This reduces token count by ~60% while preserving diagnostic relevance.
"""

import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Approximate token ratios (conservative for Llama 3.1)
CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (1 token ≈ 3.5 chars for English)."""
    return int(len(text) / CHARS_PER_TOKEN)


def truncate_context(
    context: str,
    max_tokens: int = 1500,
) -> str:
    """
    Truncate retrieved context to fit within token budget.

    Args:
        context: Full retrieved context string
        max_tokens: Maximum tokens to allow for context

    Returns:
        Truncated context string
    """
    max_chars = int(max_tokens * CHARS_PER_TOKEN)

    if len(context) <= max_chars:
        return context

    truncated = context[:max_chars]
    # Cut at the last complete sentence or paragraph
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    cut_point = max(last_period, last_newline)

    if cut_point > max_chars * 0.5:  # Only cut if we keep at least half
        truncated = truncated[:cut_point + 1]

    truncated += "\n\n[Context truncated for token efficiency]"

    original_tokens = estimate_tokens(context)
    final_tokens = estimate_tokens(truncated)
    logger.info(
        f"Context truncated: ~{original_tokens} → ~{final_tokens} tokens "
        f"({(1 - final_tokens/max(original_tokens,1))*100:.0f}% reduction)"
    )

    return truncated


def truncate_documents(
    documents: list[dict],
    max_docs: int = 3,
    max_abstract_chars: int = 500,
) -> list[dict]:
    """
    Limit and truncate documents for token efficiency.

    Args:
        documents: List of document/paper dicts
        max_docs: Maximum number of documents to keep
        max_abstract_chars: Max characters per abstract/text

    Returns:
        Truncated document list
    """
    truncated = []

    for doc in documents[:max_docs]:
        new_doc = doc.copy()

        # Truncate abstract/text field
        for text_field in ["abstract", "text"]:
            if text_field in new_doc and len(new_doc[text_field]) > max_abstract_chars:
                new_doc[text_field] = new_doc[text_field][:max_abstract_chars] + "..."

        truncated.append(new_doc)

    if len(documents) > max_docs:
        logger.info(f"Documents reduced: {len(documents)} → {max_docs}")

    return truncated


def build_optimized_prompt(
    patient_data: str,
    retrieved_context: str,
    variant_context: str,
    prompt_template: str,
    max_total_tokens: int = 3500,
) -> str:
    """
    Build the final prompt with token budget management.

    Allocates token budget across components:
    - Patient data: unlimited (always included fully)
    - Variant data: up to 500 tokens
    - Retrieved context: remaining budget
    - Prompt template: always included fully

    Args:
        patient_data: Patient symptoms and history
        retrieved_context: Retrieved biomedical context
        variant_context: Genetic/variant data context
        prompt_template: The system prompt template with placeholders
        max_total_tokens: Total token budget for the user message

    Returns:
        Optimized prompt string
    """
    # Fixed costs
    patient_tokens = estimate_tokens(patient_data)
    template_tokens = estimate_tokens(prompt_template)

    # Budget for variable components
    remaining = max_total_tokens - patient_tokens - template_tokens

    # Allocate: variant gets up to 500 tokens, rest goes to context
    variant_budget = min(500, remaining // 3)
    context_budget = remaining - variant_budget

    # Truncate
    optimized_variant = truncate_context(variant_context, max_tokens=variant_budget)
    optimized_context = truncate_context(retrieved_context, max_tokens=context_budget)

    # Fill template
    prompt = prompt_template.replace("{patient_data}", patient_data)
    prompt = prompt.replace("{retrieved_context}", optimized_context)
    prompt = prompt.replace("{variant_data}", optimized_variant)

    total = estimate_tokens(prompt)
    logger.info(
        f"Optimized prompt: ~{total} tokens "
        f"(patient={patient_tokens}, context≈{estimate_tokens(optimized_context)}, "
        f"variant≈{estimate_tokens(optimized_variant)})"
    )

    return prompt
