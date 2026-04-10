"""
Parallel Runner — Runs the Hygiene Agent alongside any main task.

Provides three execution strategies:
  1. asyncio   — `await run_hygiene_parallel(main_coro)`
  2. threading — `run_with_hygiene_thread(main_fn)`
  3. CLI       — `python -m agents.run_parallel`

Example integration in the pipeline orchestrator:
    from agents.run_parallel import run_hygiene_parallel

    async def main():
        pipeline = ClinicalPipeline()
        result = await pipeline.run_async(symptoms=[...])
        return result

    results = asyncio.run(run_hygiene_parallel(main()))
    # results["pipeline"]  → pipeline output
    # results["hygiene"]   → full hygiene report
"""

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from agents.hygiene_agent import HygieneAgent

logger = logging.getLogger("parallel_runner")


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 1: asyncio (preferred for async pipelines)
# ──────────────────────────────────────────────────────────────────────────────

async def run_hygiene_parallel(
    main_coroutine: Coroutine,
    project_root: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run the hygiene agent in parallel with an arbitrary async main task.

    Args:
        main_coroutine: The main coroutine to run (e.g., pipeline.run_async())
        project_root: Project root for the scanner

    Returns:
        {"pipeline": <main result>, "hygiene": <hygiene report>}
    """
    agent = HygieneAgent(project_root=project_root)

    # Run both concurrently
    pipeline_result, _findings = await asyncio.gather(
        main_coroutine,
        agent.scan_async(),
    )

    return {
        "pipeline": pipeline_result,
        "hygiene": agent.build_report(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 2: threading (for sync pipelines)
# ──────────────────────────────────────────────────────────────────────────────

def run_with_hygiene_thread(
    main_fn: Callable[[], Any],
    project_root: Optional[str] = None,
    print_report: bool = True,
) -> dict[str, Any]:
    """
    Run the hygiene agent on a background thread while main_fn runs on the main
    thread. Both execute in parallel.

    Args:
        main_fn: Synchronous callable (e.g., lambda: pipeline.run(symptoms=[...]))
        project_root: Project root for the scanner
        print_report: Whether to print the hygiene report to stdout

    Returns:
        {"pipeline": <main result>, "hygiene": <hygiene report>}
    """
    agent = HygieneAgent(project_root=project_root)
    hygiene_report: dict = {}

    def _hygiene_worker():
        nonlocal hygiene_report
        agent.scan()
        hygiene_report = agent.build_report()
        if print_report:
            agent.print_report()

    # Start hygiene thread
    t = threading.Thread(target=_hygiene_worker, name="hygiene-agent", daemon=True)
    t.start()

    # Run main on current thread
    pipeline_result = main_fn()

    # Wait for hygiene to finish (it's usually faster than the pipeline)
    t.join(timeout=30)

    return {
        "pipeline": pipeline_result,
        "hygiene": hygiene_report,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Strategy 3: standalone CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    """Run hygiene scan as a standalone parallel process."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Code Hygiene Agent in parallel (standalone mode).",
    )
    parser.add_argument(
        "--root", "-r",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root directory.",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        dest="use_json",
        help="Output JSON report.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    agent = HygieneAgent(project_root=args.root)
    agent.scan()
    agent.print_report(use_json=args.use_json)

    report = agent.build_report()
    sys.exit(1 if report["summary"]["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
