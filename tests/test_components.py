import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_pipeline_import():
    """Ensure we can import the pipeline orchestrator without errors."""
    from pipeline.orchestrator import ClinicalPipeline
    assert ClinicalPipeline is not None

def test_genomics_import():
    """Ensure genomic modules load properly."""
    from genomics.variant_parser import VariantParser
    parser = VariantParser()
    assert parser is not None

def test_retrieval_import():
    """Ensure retrieval abstraction is sound."""
    from retrieval.pubmed_retriever import PubMedRetriever
    assert PubMedRetriever is not None
