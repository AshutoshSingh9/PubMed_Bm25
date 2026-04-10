import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.error_sentinel import ErrorSentinel
from agents.hygiene_agent import HygieneAgent

# ── 1. Error Sentinel Tests ──

def dummy_failing_function():
    raise ValueError("Intentional crash")

def test_error_sentinel_catch_and_retry():
    sentinel = ErrorSentinel(max_retries=2)
    sentinel.start()
    
    try:
        sentinel.execute_with_retry("MockComponent", dummy_failing_function)
    except ValueError:
        pass  # Expected to bubble up after retries
        
    sentinel.stop()
    
    # Check that sentinel logged the history
    assert len(sentinel.error_history) > 0
    assert sentinel.error_history[0]["component"] == "MockComponent"
    assert "Intentional crash" in str(sentinel.error_history[0]["error"])

# ── 2. Hygiene Agent Tests ──

DUMMY_BAD_CODE = """import os
# TODO: fix this later
def do_something():
    API_KEY = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789"
    return API_KEY
    
# Missing docstrings
class BadClass:
    pass
"""

def test_hygiene_agent():
    # Use a temp directory to put our dummy bad file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        bad_file = tmp_path / "bad_code.py"
        bad_file.write_text(DUMMY_BAD_CODE)
        
        agent = HygieneAgent(project_root=str(tmp_path))
        agent.scan()
        report = agent.build_report()
        
        assert "findings" in report
        
        finding_messages = [f["message"] for f in report["findings"]]
        
        # Check if hardcoded API key was detected
        assert any("HARDCODED_SECRET" in str(f["rule"]) for f in report["findings"])
        # Check if TODO was detected
        assert any("TODO_MARKER" in str(f["rule"]) for f in report["findings"])
        
        # Score shouldn't be perfect
        assert report["health_score"] < 100
