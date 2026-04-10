import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import validate_config, NCBI_EMAIL

def test_validate_config_format():
    """Ensure validate_config returns a dictionary with expected keys."""
    status = validate_config()
    assert isinstance(status, dict)
    assert "ncbi_configured" in status
    assert "ollama_url" in status
    assert "embedding_model" in status
    assert "chroma_dir" in status

def test_imports_pass():
    """Ensure our primary config variables don't crash on load."""
    import config
    assert config.BASE_DIR.exists()
    assert config.PROMPTS_DIR.exists()
