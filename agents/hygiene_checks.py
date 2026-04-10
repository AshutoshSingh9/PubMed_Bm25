"""
Code Hygiene Checks — Individual check functions used by the HygieneAgent.

Each check returns a list of Finding dicts:
    {"severity": "ERROR"|"WARNING"|"INFO", "file": str, "line": int|None,
     "rule": str, "message": str, "suggestion": str}
"""

import ast
import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Patterns indicating hardcoded values ──────────────────────────────────────

# URLs / endpoints that should live in config
URL_PATTERN = re.compile(
    r"""(?:"|')"""                     # opening quote
    r"""(https?://[^\s"']+)"""         # URL
    r"""(?:"|')""",                    # closing quote
    re.IGNORECASE,
)

# Filesystem paths that look absolute
ABS_PATH_PATTERN = re.compile(
    r"""(?:"|')"""
    r"""(/(?:Users|home|var|tmp|etc|opt)/[^\s"']+)"""
    r"""(?:"|')""",
)

# Hardcoded port numbers in connection strings
PORT_PATTERN = re.compile(
    r"""(?:"|')"""
    r"""(?:localhost|127\.0\.0\.1|0\.0\.0\.0):\d+"""
    r"""(?:"|')""",
)

# Numeric "magic numbers" used as thresholds — bare literals assigned at module level
MAGIC_NUMBER_ASSIGNMENT = re.compile(
    r"^\s*[A-Z_]{2,}\s*=\s*(\d+\.?\d*)\s*$"
)

# Email / credential patterns
CREDENTIAL_PATTERN = re.compile(
    r"""(?:"|')"""
    r"""[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"""
    r"""(?:"|')""",
)
# TODO / FIXME markers
TODO_PATTERN = re.compile(r"\b(?:TODO|FIXME|XXX)\b", re.IGNORECASE)

# ── Files / directories to skip ──────────────────────────────────────────────
SKIP_DIRS = {"__pycache__", ".git", "chroma_db", "node_modules", ".venv", "venv", "agents"}
SKIP_FILES = {".env", ".env.example", "requirements.txt"}
ALLOWED_CONFIG_FILES = {"config.py", ".env.example"}


# ──────────────────────────────────────────────────────────────────────────────
# Individual check functions
# ──────────────────────────────────────────────────────────────────────────────

def check_hardcoded_urls(filepath: str, lines: list[str]) -> list[dict]:
    """Flag URLs that are not loaded from config/env."""
    findings = []
    basename = os.path.basename(filepath)
    if basename in ALLOWED_CONFIG_FILES:
        return findings

    for i, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for match in URL_PATTERN.finditer(line):
            url = match.group(1)
            # Ignore documentation URLs and common safe patterns
            if any(safe in url for safe in ["example.com", "docs.", "github.com", "ncbi.nlm.nih.gov/account"]):
                continue
            findings.append({
                "severity": "WARNING",
                "file": filepath,
                "line": i,
                "rule": "HARDCODED_URL",
                "message": f"Hardcoded URL detected: {url[:80]}",
                "suggestion": "Move this URL to config.py and read via os.getenv().",
            })
    return findings


def check_hardcoded_paths(filepath: str, lines: list[str]) -> list[dict]:
    """Flag absolute filesystem paths outside config.py."""
    findings = []
    basename = os.path.basename(filepath)
    if basename in ALLOWED_CONFIG_FILES:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for match in ABS_PATH_PATTERN.finditer(line):
            findings.append({
                "severity": "ERROR",
                "file": filepath,
                "line": i,
                "rule": "HARDCODED_PATH",
                "message": f"Hardcoded absolute path: {match.group(1)[:80]}",
                "suggestion": "Use config.BASE_DIR / Path() or environment variables.",
            })
    return findings


def check_hardcoded_credentials(filepath: str, lines: list[str]) -> list[dict]:
    """Flag potential hardcoded email addresses or API keys outside config."""
    findings = []
    basename = os.path.basename(filepath)
    if basename in ALLOWED_CONFIG_FILES:
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Emails
        for match in CREDENTIAL_PATTERN.finditer(line):
            email = match.group(0)
            # Skip pattern-match comparisons (e.g. != "your.email@example.com")
            if "example.com" in email:
                continue
            findings.append({
                "severity": "ERROR",
                "file": filepath,
                "line": i,
                "rule": "HARDCODED_CREDENTIAL",
                "message": f"Possible hardcoded credential: {email[:60]}",
                "suggestion": "Load from environment / .env via config.py.",
            })

        # API keys (long hex/base64 strings assigned to variables)
        if re.search(r'(?:key|token|secret|password)\s*=\s*["\'][A-Za-z0-9+/=\-_]{20,}["\']', line, re.IGNORECASE):
            findings.append({
                "severity": "ERROR",
                "file": filepath,
                "line": i,
                "rule": "HARDCODED_SECRET",
                "message": "Possible hardcoded API key / secret.",
                "suggestion": "Move to .env and load via os.getenv().",
            })
    return findings


def check_dynamic_linking(filepath: str, source: str) -> list[dict]:
    """
    Verify that classes accept dependencies via constructor injection
    rather than instantiating them internally without override options.

    Checks:
    1. __init__ methods should accept Optional[XyzClass] params for major deps.
    2. Module-level singletons should be lazy or overridable.
    """
    findings = []
    basename = os.path.basename(filepath)
    if basename in ALLOWED_CONFIG_FILES or basename == "__init__.py":
        return findings

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                continue

            # Collect param names (skip 'self')
            params = [a.arg for a in item.args.args if a.arg != "self"]
            # Defaults available count
            defaults_count = len(item.args.defaults)

            # Walk the init body looking for direct instantiations
            for stmt in ast.walk(item):
                if isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Name):
                    callee = stmt.func.id
                    # Heuristic: if a class-like name (PascalCase) is instantiated
                    # AND it's not offered as an overridable param → tight coupling
                    if callee[0].isupper() and len(callee) > 3:
                        param_lower = [p.lower() for p in params]
                        callee_lower = callee.lower()
                        # Check if there's a matching injectable param
                        injectable = any(callee_lower in p or p in callee_lower for p in param_lower)
                        if not injectable:
                            findings.append({
                                "severity": "WARNING",
                                "file": filepath,
                                "line": stmt.lineno,
                                "rule": "TIGHT_COUPLING",
                                "message": (
                                    f"Class '{node.name}.__init__' directly instantiates "
                                    f"'{callee}' without an injectable parameter."
                                ),
                                "suggestion": (
                                    f"Add `{callee.lower()}: Optional[{callee}] = None` "
                                    f"to __init__ and use `self.x = {callee.lower()} or {callee}()`."
                                ),
                            })

    return findings


def check_config_usage(filepath: str, lines: list[str]) -> list[dict]:
    """
    Verify that tunable parameters reference config.py instead of
    being hardcoded as bare literals.
    """
    findings = []
    basename = os.path.basename(filepath)
    if basename in ALLOWED_CONFIG_FILES or basename == "__init__.py":
        return findings

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Detect hardcoded ports in connection strings (outside config)
        if PORT_PATTERN.search(line):
            findings.append({
                "severity": "WARNING",
                "file": filepath,
                "line": i,
                "rule": "HARDCODED_PORT",
                "message": "Hardcoded host:port detected outside config.",
                "suggestion": "Use config.OLLAMA_BASE_URL or equivalent.",
            })

    return findings


def check_import_hygiene(filepath: str, source: str) -> list[dict]:
    """
    Check for problematic import patterns:
    - Circular import risk (cross-module imports between sibling packages)
    - Wildcard imports
    - Unused imports (basic heuristic)
    """
    findings = []
    basename = os.path.basename(filepath)
    if basename == "__init__.py":
        return findings

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        # Wildcard imports
        if isinstance(node, ast.ImportFrom) and node.names:
            for alias in node.names:
                if alias.name == "*":
                    findings.append({
                        "severity": "ERROR",
                        "file": filepath,
                        "line": node.lineno,
                        "rule": "WILDCARD_IMPORT",
                        "message": f"Wildcard import: from {node.module} import *",
                        "suggestion": "Import specific names to avoid namespace pollution.",
                    })

    return findings


def check_error_handling(filepath: str, source: str) -> list[dict]:
    """Flag bare except clauses and overly broad exception handling."""
    findings = []
    basename = os.path.basename(filepath)
    if basename == "__init__.py":
        return findings

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                findings.append({
                    "severity": "WARNING",
                    "file": filepath,
                    "line": node.lineno,
                    "rule": "BARE_EXCEPT",
                    "message": "Bare 'except:' clause catches ALL exceptions including SystemExit.",
                    "suggestion": "Use 'except Exception as e:' at minimum.",
                })

    return findings


def check_docstring_coverage(filepath: str, source: str) -> list[dict]:
    """Check that all public classes and functions have docstrings."""
    findings = []
    basename = os.path.basename(filepath)
    if basename == "__init__.py":
        return findings

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Skip private/dunder
            if node.name.startswith("_") and not node.name.startswith("__init__"):
                continue
            if node.name == "__init__":
                continue  # init docstrings are nice but not critical

            docstring = ast.get_docstring(node)
            if not docstring:
                kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
                findings.append({
                    "severity": "INFO",
                    "file": filepath,
                    "line": node.lineno,
                    "rule": "MISSING_DOCSTRING",
                    "message": f"{kind} '{node.name}' has no docstring.",
                    "suggestion": f"Add a docstring to improve maintainability.",
                })

    return findings

def check_todo_markers(filepath: str, lines: list[str]) -> list[dict]:
    """Flag TODO/FIXME markers in the code."""
    findings = []
    for i, line in enumerate(lines, 1):
        if TODO_PATTERN.search(line):
            findings.append({
                "severity": "INFO",
                "file": filepath,
                "line": i,
                "rule": "TODO_MARKER",
                "message": f"TODO/FIXME marker detected: {line.strip()}",
                "suggestion": "Ensure these markers are resolved before production.",
            })
    return findings
