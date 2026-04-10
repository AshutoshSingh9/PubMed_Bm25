import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.llm_provider import LLMProvider
from pipeline.response_parser import extract_json, parse_combined_response, DEFAULT_DIAGNOSIS
from pipeline.token_optimizer import estimate_tokens, truncate_context, build_optimized_prompt
from pipeline.orchestrator import ClinicalPipeline

# ── 1. LLM Provider Mocks ──

@patch('pipeline.llm_provider.ollama.Client')
def test_llm_provider_ollama(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    
    # Mock chat response
    mock_client.chat.return_value = {
        "message": {"content": "Mocked LLM Response"}
    }
    
    provider = LLMProvider(provider="ollama", model="dummy_model")
    res = provider.generate("System", "User")
    
    assert res == "Mocked LLM Response"
    mock_client.chat.assert_called_once()

# ── 2. Response Parser Tests ──

def test_extract_json_clean():
    text = '{"diagnosis_stage": {"key": "value"}}'
    data = extract_json(text)
    assert data is not None
    assert "diagnosis_stage" in data

def test_extract_json_fence():
    text = '''Some leading text...
```json
{
  "diagnosis_stage": {"key": "value"}
}
```
Trailing text...'''
    data = extract_json(text)
    assert data is not None
    assert "diagnosis_stage" in data

def test_extract_json_trailing_comma():
    text = '{"list": [1, 2, ], "obj": {"a": 1, }, }'
    data = extract_json(text)
    assert data is not None
    assert "list" in data
    assert data["list"] == [1, 2]

def test_parse_combined_response_fallback():
    text = "THIS IS NOT JSON AT ALL"
    data = parse_combined_response(text)
    assert "_parsing_error" in data
    assert "diagnosis_stage" in data
    assert "critic_stage" in data
    # Should fallback to DEFAULT
    assert data["diagnosis_stage"] == DEFAULT_DIAGNOSIS["diagnosis_stage"]

# ── 3. Token Optimizer ──

def test_token_estimate():
    text = "1234567" # 7 chars, ~3.5 chars per token = 2 tokens
    tk = estimate_tokens(text)
    assert tk == 2

def test_truncate_context():
    long_text = "A." * 4000 # 8000 chars -> ~2285 tokens
    trunc = truncate_context(long_text, max_tokens=10) # 35 chars
    assert len(trunc) < 100
    assert "Context truncated" in trunc

def test_build_optimized_prompt():
    ptmp = "{patient_data} {retrieved_context} {variant_data}"
    res = build_optimized_prompt(
        patient_data="Patient X",
        retrieved_context="Context Y",
        variant_context="Variant Z",
        prompt_template=ptmp,
        max_total_tokens=100
    )
    assert "Patient X Context Y Variant Z" in res

# ── 4. Clinical Pipeline Orchestrator ──

@patch('pipeline.orchestrator.LLMProvider')
def test_clinical_pipeline(mock_llm_cls):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"diagnosis_stage": {"possible_conditions": ["Flu"]}, "critic_stage": {}, "safety_stage": {}}'
    mock_llm_cls.return_value = mock_llm
    
    pipeline = ClinicalPipeline()
    res = pipeline.run("headache", age=30)
    
    assert res is not None
    assert "diagnosis_stage" in res
    assert "Flu" in res["diagnosis_stage"]["possible_conditions"]
    assert mock_llm.generate.call_count >= 1
