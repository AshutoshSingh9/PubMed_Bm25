"""
Latency Optimizer Agent — Analyzes and optimizes pipeline latency.

Provides profiling wrappers and in-memory caches to speed up repeated queries
and parallelize blocking operations.
"""

import logging
import time
from functools import lru_cache
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

# --- Caching Layer ---

class LRUCacheLayer:
    """In-memory LRU cache for expensive retrieval and parsing functions."""
    
    _pubmed_cache = {}
    _variant_cache = {}
    
    @classmethod
    def cached_pubmed(cls, func: Callable) -> Callable:
        @lru_cache(maxsize=128)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
        
    @classmethod
    def cached_variant_parsing(cls, func: Callable) -> Callable:
        @lru_cache(maxsize=128)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper


# --- Agent ---

class LatencyOptimizer:
    """
    Agent that profiles pipeline execution and applies optimizations.
    """
    
    def __init__(self, pipeline: Any):
        self.pipeline = pipeline
        self.last_report = {}
        
    def run(self, *args, **kwargs) -> Dict:
        """
        Run the pipeline while capturing high-resolution latency metrics.
        Ensures use_cache is passed if applicable.
        """
        kwargs["use_cache"] = kwargs.get("use_cache", True)
        logger.info(f"LatencyOptimizer starting profiled run. Caching: {kwargs['use_cache']}")
        
        start_time = time.perf_counter()
        
        # Run the actual pipeline (which we will instrument to output phase timings)
        result = self.pipeline.run(*args, **kwargs)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        metadata = result.get("metadata", {})
        
        self.last_report = {
            "total_time_actual": round(total_time, 3),
            "reported_time": metadata.get("total_time_seconds", 0),
            "phase_timings": metadata.get("phase_timings", {}),
            "optimizations_enabled": kwargs["use_cache"]
        }
        
        logger.info(f"LatencyOptimizer run complete: {total_time:.2f}s")
        return result
        
    def get_report(self) -> str:
        """Format the latency breakdown into a readable report."""
        if not self.last_report:
            return "No profile data available. Run the pipeline first."
            
        r = self.last_report
        lines = [
            "### Latency Profiling Report",
            f"- **Total Time (Wall-Clock):** {r['total_time_actual']}s",
            f"- **Optimizations Enabled:** {r['optimizations_enabled']}",
            "",
            "#### Phase Breakdown"
        ]
        
        for phase, ms in r.get("phase_timings", {}).items():
            lines.append(f"- **{phase}**: {ms:.2f}s")
            
        return "\n".join(lines)
