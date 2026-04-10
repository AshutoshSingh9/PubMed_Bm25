"""
Hygiene Agent — Autonomous code-quality checker that runs in parallel.

Scans every Python source file in the project for:
  • Hardcoded URLs, paths, credentials, and magic numbers
  • Tight coupling (classes that don't accept injectable dependencies)
  • Missing config.py references where env-driven values belong
  • Import anti-patterns (wildcard imports)
  • Bare / overly-broad except clauses
  • Missing docstrings on public APIs

Usage (standalone — kicked off in parallel with the main pipeline):
    python -m agents.hygiene_agent          # prints report to stdout
    python -m agents.hygiene_agent --json   # machine-readable JSON output

The agent is designed to be **non-blocking**: it never modifies source code,
never imports project modules (only reads files as text + AST), and is safe
to run concurrently via asyncio, threading, or multiprocessing.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from agents.hygiene_checks import (
    check_hardcoded_urls,
    check_hardcoded_paths,
    check_hardcoded_credentials,
    check_dynamic_linking,
    check_config_usage,
    check_import_hygiene,
    check_error_handling,
    check_docstring_coverage,
    check_todo_markers,
    SKIP_DIRS,
    SKIP_FILES,
)

logger = logging.getLogger("hygiene_agent")

# ── Severity ranks for sorting/filtering ──────────────────────────────────────
SEVERITY_RANK = {"ERROR": 0, "WARNING": 1, "INFO": 2}


# ──────────────────────────────────────────────────────────────────────────────
# Core Agent
# ──────────────────────────────────────────────────────────────────────────────

class HygieneAgent:
    """
    Parallel code-hygiene scanner.

    Collects Python source files, fans out checks across threads, and
    aggregates findings into a structured report.
    """

    # All registered checkers
    CHECKS = [
        ("hardcoded_urls", check_hardcoded_urls, "lines"),
        ("hardcoded_paths", check_hardcoded_paths, "lines"),
        ("hardcoded_credentials", check_hardcoded_credentials, "lines"),
        ("dynamic_linking", check_dynamic_linking, "source"),
        ("config_usage", check_config_usage, "lines"),
        ("import_hygiene", check_import_hygiene, "source"),
        ("error_handling", check_error_handling, "source"),
        ("docstring_coverage", check_docstring_coverage, "source"),
        ("todo_markers", check_todo_markers, "lines"),
    ]

    def __init__(self, project_root: Optional[str] = None, workers: int = 4):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.workers = workers
        self.findings: list[dict] = []
        self._start_time: float = 0
        self._files_scanned: int = 0

    # ── File Discovery ────────────────────────────────────────────────────

    def _collect_python_files(self) -> list[Path]:
        """Recursively collect all .py files, respecting skip lists."""
        py_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Prune skipped directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.endswith(".py") and f not in SKIP_FILES:
                    py_files.append(Path(root) / f)
        return sorted(py_files)

    # ── Per-File Analysis ─────────────────────────────────────────────────

    def _analyze_file(self, filepath: Path) -> list[dict]:
        """Run all registered checks against a single file."""
        try:
            source = filepath.read_text(encoding="utf-8")
        except Exception as e:
            return [{
                "severity": "ERROR",
                "file": str(filepath),
                "line": None,
                "rule": "READ_ERROR",
                "message": f"Could not read file: {e}",
                "suggestion": "Check file permissions.",
            }]

        lines = source.splitlines()
        file_findings: list[dict] = []

        for _name, check_fn, input_type in self.CHECKS:
            try:
                if input_type == "lines":
                    file_findings.extend(check_fn(str(filepath), lines))
                else:
                    file_findings.extend(check_fn(str(filepath), source))
            except Exception as e:
                logger.debug(f"Check '{_name}' failed on {filepath}: {e}")

        return file_findings

    # ── Parallel Scan ─────────────────────────────────────────────────────

    def scan(self) -> list[dict]:
        """
        Scan the entire project in parallel.

        Returns:
            Sorted list of Finding dicts.
        """
        self._start_time = time.time()
        py_files = self._collect_python_files()
        self._files_scanned = len(py_files)

        logger.info(f"Scanning {len(py_files)} Python files with {self.workers} workers...")

        all_findings: list[dict] = []

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self._analyze_file, f): f for f in py_files}
            for future in futures:
                try:
                    all_findings.extend(future.result())
                except Exception as e:
                    logger.error(f"Worker failed on {futures[future]}: {e}")

        # Sort: ERROR > WARNING > INFO, then by file
        all_findings.sort(key=lambda f: (SEVERITY_RANK.get(f["severity"], 9), f["file"], f.get("line", 0) or 0))

        self.findings = all_findings
        return all_findings

    async def scan_async(self) -> list[dict]:
        """Async wrapper — lets the agent run alongside other async tasks."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.scan)

    # ── Reporting ─────────────────────────────────────────────────────────

    def build_report(self) -> dict:
        """Build a structured report from the latest scan."""
        elapsed = time.time() - self._start_time if self._start_time else 0

        errors   = [f for f in self.findings if f["severity"] == "ERROR"]
        warnings = [f for f in self.findings if f["severity"] == "WARNING"]
        infos    = [f for f in self.findings if f["severity"] == "INFO"]

        # Group by rule
        by_rule: dict[str, int] = {}
        for f in self.findings:
            by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1

        # Dynamic linking score: % of files with no TIGHT_COUPLING findings
        files_with_coupling = {f["file"] for f in self.findings if f["rule"] == "TIGHT_COUPLING"}
        total_files = max(self._files_scanned, 1)
        dynamic_link_score = round((1 - len(files_with_coupling) / total_files) * 100, 1)

        # Overall health score (simple weighted formula)
        health = max(0, 100 - (len(errors) * 10) - (len(warnings) * 3) - (len(infos) * 0.5))

        verdict = "CLEAN"
        if len(errors) > 0:
            verdict = "NEEDS_FIXES"
        elif len(warnings) > 3:
            verdict = "MINOR_ISSUES"

        return {
            "verdict": verdict,
            "health_score": round(health, 1),
            "dynamic_linking_score": dynamic_link_score,
            "summary": {
                "files_scanned": self._files_scanned,
                "total_findings": len(self.findings),
                "errors": len(errors),
                "warnings": len(warnings),
                "infos": len(infos),
                "scan_time_seconds": round(elapsed, 3),
            },
            "by_rule": by_rule,
            "findings": self.findings,
        }

    def print_report(self, use_json: bool = False):
        """Pretty-print or JSON-dump the report to stdout."""
        report = self.build_report()

        if use_json:
            print(json.dumps(report, indent=2))
            return

        # ── Pretty terminal output ────────────────────────────────────────
        RESET = "\033[0m"
        BOLD  = "\033[1m"
        RED   = "\033[91m"
        YELLOW = "\033[93m"
        GREEN = "\033[92m"
        CYAN  = "\033[96m"
        DIM   = "\033[2m"

        severity_colors = {"ERROR": RED, "WARNING": YELLOW, "INFO": CYAN}

        print()
        print(f"{BOLD}{'═' * 72}{RESET}")
        print(f"{BOLD}  🩺  CODE HYGIENE REPORT{RESET}")
        print(f"{BOLD}{'═' * 72}{RESET}")

        # Summary
        s = report["summary"]
        print(f"\n  Files scanned  : {s['files_scanned']}")
        print(f"  Scan time      : {s['scan_time_seconds']:.3f}s")
        print(f"  Health score   : {self._score_color(report['health_score'])}{report['health_score']}/100{RESET}")
        print(f"  Dynamic linking: {self._score_color(report['dynamic_linking_score'])}{report['dynamic_linking_score']}%{RESET}")
        print(f"\n  {RED}✖ Errors: {s['errors']}{RESET}  "
              f"{YELLOW}▲ Warnings: {s['warnings']}{RESET}  "
              f"{CYAN}● Info: {s['infos']}{RESET}")

        # By-rule breakdown
        if report["by_rule"]:
            print(f"\n{BOLD}  Rule Breakdown:{RESET}")
            for rule, count in sorted(report["by_rule"].items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 30)
                print(f"    {rule:<25s} {count:>3d}  {DIM}{bar}{RESET}")

        # Findings (grouped by file)
        if report["findings"]:
            print(f"\n{BOLD}{'─' * 72}{RESET}")
            current_file = None
            for f in report["findings"]:
                if f["file"] != current_file:
                    current_file = f["file"]
                    rel = os.path.relpath(current_file, self.project_root)
                    print(f"\n  {BOLD}{rel}{RESET}")

                color = severity_colors.get(f["severity"], RESET)
                line_str = f"L{f['line']}" if f["line"] else "   "
                print(f"    {color}{f['severity']:<7s}{RESET} {DIM}{line_str:>5s}{RESET}  "
                      f"{f['message']}")
                print(f"           {DIM}→ {f['suggestion']}{RESET}")

        # Verdict
        print(f"\n{BOLD}{'═' * 72}{RESET}")
        v = report["verdict"]
        v_color = GREEN if v == "CLEAN" else (YELLOW if v == "MINOR_ISSUES" else RED)
        print(f"  Verdict: {v_color}{BOLD}{v}{RESET}")
        print(f"{BOLD}{'═' * 72}{RESET}\n")

    @staticmethod
    def _score_color(score: float) -> str:
        if score >= 90:
            return "\033[92m"  # green
        elif score >= 70:
            return "\033[93m"  # yellow
        return "\033[91m"      # red


# ── CLI Entrypoint ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Code Hygiene Agent — scans for hardcoded values and coupling issues.",
    )
    parser.add_argument(
        "--root", "-r",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project root directory (default: auto-detect).",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        dest="use_json",
        help="Output machine-readable JSON.",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel scanner threads.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    agent = HygieneAgent(project_root=args.root, workers=args.workers)
    agent.scan()
    agent.print_report(use_json=args.use_json)

    # Exit with non-zero if errors found
    report = agent.build_report()
    sys.exit(1 if report["summary"]["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
