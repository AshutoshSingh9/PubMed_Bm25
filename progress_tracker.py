"""
BioProj1 — Real-Time Progress Tracker Dashboard
================================================
Scans the codebase, analyzes implementation status of every module/file,
and serves a live-updating dashboard at http://localhost:8050

Usage:
    python progress_tracker.py

Features:
    • File-level implementation analysis (docstrings, TODOs, stubs, LOC)
    • Module-level and overall project progress
    • Dependency / integration readiness checks
    • Config & environment validation
    • Auto-refreshes every 3 seconds via polling
    • Stunning dark-themed glassmorphism UI
"""

import ast
import json
import os
import re
import sys
import time
import hashlib
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

# ── Project root ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent

# ── Module definitions with expected deliverables ──────────────────────────────
MODULE_SPEC = {
    "genomics": {
        "label": "Genomics",
        "icon": "🧬",
        "description": "Variant parsing, annotation & BLAST search",
        "files": {
            "genomics/__init__.py": {"weight": 0.05, "role": "Package init"},
            "genomics/variant_parser.py": {"weight": 0.30, "role": "FASTA/VCF/HGVS parser"},
            "genomics/variant_annotator.py": {"weight": 0.35, "role": "ClinVar-derived annotation"},
            "genomics/blast_search.py": {"weight": 0.30, "role": "NCBI BLAST integration"},
        },
        "milestones": [
            {"label": "HGVS pattern matching", "check": "genomics/variant_parser.py", "pattern": r"HGVS_PATTERN"},
            {"label": "VCF parsing", "check": "genomics/variant_parser.py", "pattern": r"VCF_LINE_PATTERN"},
            {"label": "Variant database", "check": "genomics/variant_annotator.py", "pattern": r"VARIANT_DATABASE"},
            {"label": "BLAST search method", "check": "genomics/blast_search.py", "pattern": r"def search"},
            {"label": "Prompt formatting", "check": "genomics/variant_parser.py", "pattern": r"def format_for_prompt"},
        ],
    },
    "pipeline": {
        "label": "Pipeline",
        "icon": "⚙️",
        "description": "3-stage clinical reasoning engine with LLM",
        "files": {
            "pipeline/__init__.py": {"weight": 0.03, "role": "Package init"},
            "pipeline/llm_provider.py": {"weight": 0.20, "role": "Ollama LLM abstraction"},
            "pipeline/response_parser.py": {"weight": 0.22, "role": "JSON extraction from LLM"},
            "pipeline/stage1_diagnostician.py": {"weight": 0.20, "role": "Diagnostic reasoning stage"},
            "pipeline/stage2_critic.py": {"weight": 0.20, "role": "Adversarial review stage"},
            "pipeline/token_optimizer.py": {"weight": 0.15, "role": "Token budget management"},
        },
        "milestones": [
            {"label": "LLM generate + stream", "check": "pipeline/llm_provider.py", "pattern": r"def generate_stream"},
            {"label": "JSON brace matching", "check": "pipeline/response_parser.py", "pattern": r"_find_json_object"},
            {"label": "Stage 1 runner", "check": "pipeline/stage1_diagnostician.py", "pattern": r"def run"},
            {"label": "Stage 2 runner", "check": "pipeline/stage2_critic.py", "pattern": r"def run"},
            {"label": "Prompt optimizer", "check": "pipeline/token_optimizer.py", "pattern": r"build_optimized_prompt"},
            {"label": "Health check", "check": "pipeline/llm_provider.py", "pattern": r"def check_health"},
        ],
    },
    "retrieval": {
        "label": "Retrieval",
        "icon": "🔍",
        "description": "PubMed search, embeddings, vector store & hybrid search",
        "files": {
            "retrieval/__init__.py": {"weight": 0.03, "role": "Package init"},
            "retrieval/embeddings.py": {"weight": 0.20, "role": "Bio_ClinicalBERT embeddings"},
            "retrieval/vector_store.py": {"weight": 0.27, "role": "ChromaDB vector store"},
            "retrieval/pubmed_retriever.py": {"weight": 0.25, "role": "PubMed Entrez retrieval"},
            "retrieval/hybrid_search.py": {"weight": 0.25, "role": "BM25 + semantic RRF"},
        },
        "milestones": [
            {"label": "Embedding model loading", "check": "retrieval/embeddings.py", "pattern": r"SentenceTransformer"},
            {"label": "Fallback model support", "check": "retrieval/embeddings.py", "pattern": r"fallback"},
            {"label": "ChromaDB persistence", "check": "retrieval/vector_store.py", "pattern": r"PersistentClient"},
            {"label": "PubMed Entrez search", "check": "retrieval/pubmed_retriever.py", "pattern": r"Entrez\.esearch"},
            {"label": "BM25 indexing", "check": "retrieval/hybrid_search.py", "pattern": r"BM25Okapi"},
            {"label": "Reciprocal Rank Fusion", "check": "retrieval/hybrid_search.py", "pattern": r"reciprocal_rank_fusion"},
        ],
    },
    "prompts": {
        "label": "Prompts",
        "icon": "📝",
        "description": "LLM prompt templates for each pipeline stage",
        "files": {
            "prompts/diagnostician.txt": {"weight": 0.34, "role": "Stage 1 prompt template"},
            "prompts/critic.txt": {"weight": 0.33, "role": "Stage 2 prompt template"},
            "prompts/safety_validator.txt": {"weight": 0.33, "role": "Stage 3 prompt template"},
        },
        "milestones": [
            {"label": "Diagnostician prompt", "check": "prompts/diagnostician.txt", "pattern": r"diagnosis_stage"},
            {"label": "Critic prompt", "check": "prompts/critic.txt", "pattern": r"critic_stage"},
            {"label": "Safety prompt", "check": "prompts/safety_validator.txt", "pattern": r"safety_stage"},
            {"label": "JSON output schemas", "check": "prompts/diagnostician.txt", "pattern": r"OUTPUT FORMAT"},
        ],
    },
    "config": {
        "label": "Config & Infra",
        "icon": "🛠️",
        "description": "Central configuration, dependencies & environment",
        "files": {
            "config.py": {"weight": 0.40, "role": "Central config loader"},
            "requirements.txt": {"weight": 0.30, "role": "Python dependencies"},
            ".env.example": {"weight": 0.30, "role": "Environment template"},
        },
        "milestones": [
            {"label": "Config validation", "check": "config.py", "pattern": r"validate_config"},
            {"label": "Prompt loader", "check": "config.py", "pattern": r"load_prompt"},
            {"label": "Dependencies listed", "check": "requirements.txt", "pattern": r"streamlit"},
            {"label": "Env template", "check": ".env.example", "pattern": r"OLLAMA_MODEL"},
        ],
    },
}

# Items that represent future work / known gaps
ROADMAP_ITEMS = [
    {"label": "Stage 3 — Safety Validator (pipeline module)", "status": "not_started", "module": "pipeline"},
    {"label": "Streamlit UI app.py", "status": "not_started", "module": "config"},
    {"label": "Unit tests (tests/ directory)", "status": "not_started", "module": "config"},
    {"label": ".env file configured", "status": "check_env", "module": "config"},
    {"label": "Data directory with sample inputs", "status": "check_dir", "path": "data", "module": "config"},
    {"label": "ChromaDB initialized", "status": "check_dir", "path": "chroma_db", "module": "retrieval"},
]


# ══════════════════════════════════════════════════════════════════════════════
# Analysis Engine
# ══════════════════════════════════════════════════════════════════════════════

def analyze_python_file(filepath: Path) -> dict:
    """Deep analysis of a Python source file."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        return {"exists": False}

    lines = source.split("\n")
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    total_lines = len(lines)

    # Parse AST
    classes, functions, has_docstring = [], [], False
    try:
        tree = ast.parse(source)
        has_docstring = (
            isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
            if tree.body else False
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_methods = [
                    n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)
                ]
                classes.append({"name": node.name, "methods": cls_methods, "line": node.lineno})
            elif isinstance(node, ast.FunctionDef) and not any(
                isinstance(p, ast.ClassDef) for p in ast.walk(tree)
                if hasattr(p, 'body') and node in getattr(p, 'body', [])
            ):
                functions.append({"name": node.name, "line": node.lineno})
    except SyntaxError:
        pass

    # Quality signals
    todos = len(re.findall(r"#\s*(TODO|FIXME|HACK|XXX|TEMP)", source, re.IGNORECASE))
    stubs = source.count("pass\n") + source.count("raise NotImplementedError")
    has_logging = "logging" in source or "logger" in source
    has_typing = "from typing" in source or ": str" in source or ": list" in source
    has_error_handling = "try:" in source and "except" in source
    imports = re.findall(r"^(?:import|from)\s+(\S+)", source, re.MULTILINE)

    # Docstring coverage for functions/classes
    docstring_count = len(re.findall(r'"""[\s\S]*?"""', source))

    return {
        "exists": True,
        "total_lines": total_lines,
        "loc": loc,
        "classes": classes,
        "functions": functions,
        "has_module_docstring": has_docstring,
        "docstring_count": docstring_count,
        "todos": todos,
        "stubs": stubs,
        "has_logging": has_logging,
        "has_typing": has_typing,
        "has_error_handling": has_error_handling,
        "imports": imports,
        "hash": hashlib.md5(source.encode()).hexdigest()[:8],
    }


def analyze_text_file(filepath: Path) -> dict:
    """Analyze a non-Python file (prompts, config, etc.)."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        return {"exists": False}

    lines = source.split("\n")
    non_empty = len([l for l in lines if l.strip()])

    return {
        "exists": True,
        "total_lines": len(lines),
        "loc": non_empty,
        "has_content": non_empty > 3,
        "size_bytes": len(source.encode()),
        "hash": hashlib.md5(source.encode()).hexdigest()[:8],
    }


def compute_file_score(filepath: str, analysis: dict) -> float:
    """Compute a 0–100 implementation score for a file."""
    if not analysis.get("exists"):
        return 0.0

    if filepath.endswith(".py"):
        score = 0.0
        # Exists & has content
        score += 10
        # Has module docstring
        if analysis.get("has_module_docstring"):
            score += 10
        # Has classes or functions
        if analysis.get("classes") or analysis.get("functions"):
            score += 20
        # LOC threshold (real implementation)
        loc = analysis.get("loc", 0)
        if loc > 10:
            score += 10
        if loc > 50:
            score += 10
        if loc > 100:
            score += 5
        # Logging
        if analysis.get("has_logging"):
            score += 8
        # Type hints
        if analysis.get("has_typing"):
            score += 7
        # Error handling
        if analysis.get("has_error_handling"):
            score += 8
        # Docstrings beyond module-level
        if analysis.get("docstring_count", 0) >= 3:
            score += 7
        # Penalty for stubs
        score -= analysis.get("stubs", 0) * 5
        # Penalty for TODOs
        score -= analysis.get("todos", 0) * 2
        # Small init files get a pass
        if filepath.endswith("__init__.py") and loc >= 1:
            score = max(score, 85)

        return max(0.0, min(100.0, score))
    else:
        # Text/config files
        if analysis.get("has_content"):
            loc = analysis.get("loc", 0)
            if loc > 20:
                return 100.0
            elif loc > 10:
                return 85.0
            elif loc > 3:
                return 60.0
        return 20.0 if analysis.get("exists") else 0.0


def check_milestone(milestone: dict) -> bool:
    """Check if a milestone pattern is found in the specified file."""
    fp = PROJECT_ROOT / milestone["check"]
    if not fp.exists():
        return False
    try:
        content = fp.read_text(encoding="utf-8")
        return bool(re.search(milestone["pattern"], content))
    except Exception:
        return False


def check_roadmap_item(item: dict) -> str:
    """Evaluate a roadmap item's status dynamically."""
    if item["status"] == "check_env":
        return "done" if (PROJECT_ROOT / ".env").exists() else "not_started"
    elif item["status"] == "check_dir":
        return "done" if (PROJECT_ROOT / item["path"]).exists() else "not_started"
    elif item["status"] == "not_started":
        # Check if a relevant file exists for pipeline stage 3
        if "Stage 3" in item["label"]:
            # Look for safety stage file
            candidates = list(PROJECT_ROOT.glob("pipeline/*safety*")) + list(PROJECT_ROOT.glob("pipeline/*stage3*"))
            return "done" if candidates else "not_started"
        elif "app.py" in item["label"] or "Streamlit" in item["label"]:
            return "done" if (PROJECT_ROOT / "app.py").exists() else "not_started"
        elif "tests" in item["label"]:
            tests_dir = PROJECT_ROOT / "tests"
            if tests_dir.exists() and any(tests_dir.glob("*.py")):
                return "done"
            return "not_started"
    return item["status"]


def run_full_analysis() -> dict:
    """Run complete project analysis and return structured data."""
    timestamp = datetime.now().isoformat(timespec="seconds")
    modules = {}
    total_loc = 0
    total_files = 0
    total_classes = 0
    total_functions = 0
    total_todos = 0

    for mod_key, mod_spec in MODULE_SPEC.items():
        file_results = {}
        mod_score = 0.0
        mod_milestones_done = 0

        for fpath, fmeta in mod_spec["files"].items():
            full_path = PROJECT_ROOT / fpath
            if fpath.endswith(".py"):
                analysis = analyze_python_file(full_path)
            else:
                analysis = analyze_text_file(full_path)

            score = compute_file_score(fpath, analysis)
            file_results[fpath] = {
                **analysis,
                "score": round(score, 1),
                "role": fmeta["role"],
                "weight": fmeta["weight"],
            }
            mod_score += score * fmeta["weight"]

            if analysis.get("exists"):
                total_files += 1
                total_loc += analysis.get("loc", 0)
                total_todos += analysis.get("todos", 0)
                for cls in analysis.get("classes", []):
                    total_classes += 1
                    total_functions += len(cls.get("methods", []))
                total_functions += len(analysis.get("functions", []))

        # Milestones
        milestones = []
        for ms in mod_spec.get("milestones", []):
            done = check_milestone(ms)
            milestones.append({"label": ms["label"], "done": done})
            if done:
                mod_milestones_done += 1

        ms_total = len(mod_spec.get("milestones", []))
        ms_pct = (mod_milestones_done / ms_total * 100) if ms_total else 100

        modules[mod_key] = {
            "label": mod_spec["label"],
            "icon": mod_spec["icon"],
            "description": mod_spec["description"],
            "files": file_results,
            "score": round(mod_score, 1),
            "milestones": milestones,
            "milestone_pct": round(ms_pct, 1),
        }

    # Roadmap
    roadmap = []
    for item in ROADMAP_ITEMS:
        status = check_roadmap_item(item)
        roadmap.append({"label": item["label"], "status": status, "module": item["module"]})

    roadmap_done = sum(1 for r in roadmap if r["status"] == "done")
    roadmap_pct = (roadmap_done / len(roadmap) * 100) if roadmap else 0

    # Overall
    mod_scores = [m["score"] for m in modules.values()]
    overall = round(sum(mod_scores) / len(mod_scores), 1) if mod_scores else 0

    return {
        "timestamp": timestamp,
        "overall_score": overall,
        "total_loc": total_loc,
        "total_files": total_files,
        "total_classes": total_classes,
        "total_functions": total_functions,
        "total_todos": total_todos,
        "modules": modules,
        "roadmap": roadmap,
        "roadmap_pct": round(roadmap_pct, 1),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard HTML
# ══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BioProj1 — Progress Tracker</title>
<meta name="description" content="Real-time progress tracker for the Clinical Intelligence System project">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: rgba(17, 24, 39, 0.7);
    --bg-glass: rgba(255, 255, 255, 0.03);
    --border: rgba(255, 255, 255, 0.06);
    --border-glow: rgba(99, 102, 241, 0.3);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-indigo: #818cf8;
    --accent-violet: #a78bfa;
    --accent-cyan: #22d3ee;
    --accent-emerald: #34d399;
    --accent-amber: #fbbf24;
    --accent-rose: #fb7185;
    --gradient-hero: linear-gradient(135deg, #818cf8 0%, #a78bfa 50%, #22d3ee 100%);
    --gradient-card: linear-gradient(145deg, rgba(99,102,241,0.08) 0%, rgba(167,139,250,0.04) 100%);
    --shadow-glow: 0 0 40px rgba(99, 102, 241, 0.08);
    --radius: 16px;
    --radius-sm: 10px;
    --transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    overflow-x: hidden;
    line-height: 1.6;
  }

  /* ── Animated Background ── */
  .bg-grid {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
      radial-gradient(ellipse 800px 600px at 20% 10%, rgba(99,102,241,0.07) 0%, transparent 70%),
      radial-gradient(ellipse 600px 500px at 80% 80%, rgba(34,211,238,0.05) 0%, transparent 70%),
      radial-gradient(ellipse 500px 400px at 50% 50%, rgba(167,139,250,0.04) 0%, transparent 70%);
  }
  .bg-grid::after {
    content: ''; position: absolute; inset: 0;
    background-image: linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
    background-size: 60px 60px;
  }

  /* ── Layout ── */
  .container { max-width: 1360px; margin: 0 auto; padding: 0 24px; position: relative; z-index: 1; }

  /* ── Header ── */
  .header {
    padding: 40px 0 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
  }
  .header-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }
  .header h1 {
    font-size: 28px; font-weight: 800; letter-spacing: -0.5px;
    background: var(--gradient-hero); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .header-subtitle { color: var(--text-secondary); font-size: 14px; margin-top: 4px; font-weight: 400; }
  .live-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.25);
    color: var(--accent-emerald); padding: 6px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .live-dot {
    width: 8px; height: 8px; background: var(--accent-emerald); border-radius: 50%;
    animation: pulse-dot 1.5s ease-in-out infinite;
  }
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52,211,153,0.4); }
    50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(52,211,153,0); }
  }

  /* ── Overall Score Ring ── */
  .hero-score {
    display: flex; align-items: center; gap: 40px; padding: 32px 0;
    flex-wrap: wrap;
  }
  .score-ring-container { position: relative; width: 180px; height: 180px; flex-shrink: 0; }
  .score-ring-bg, .score-ring-fg { position: absolute; inset: 0; }
  .score-ring-bg circle, .score-ring-fg circle {
    fill: none; cx: 90; cy: 90; r: 78;
    stroke-width: 10; stroke-linecap: round;
    transform: rotate(-90deg); transform-origin: center;
  }
  .score-ring-bg circle { stroke: rgba(255,255,255,0.05); }
  .score-ring-fg circle {
    stroke: url(#scoreGradient);
    stroke-dasharray: 490; /* 2πr */
    stroke-dashoffset: 490;
    transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .score-value {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }
  .score-number { font-size: 48px; font-weight: 900; letter-spacing: -2px;
    background: var(--gradient-hero); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .score-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }

  .hero-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px 32px; }
  .stat-item { display: flex; flex-direction: column; gap: 2px; }
  .stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
  .stat-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-value.emerald { color: var(--accent-emerald); }
  .stat-value.cyan { color: var(--accent-cyan); }
  .stat-value.amber { color: var(--accent-amber); }
  .stat-value.violet { color: var(--accent-violet); }

  /* ── Cards ── */
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    backdrop-filter: blur(20px);
    transition: var(--transition);
    box-shadow: var(--shadow-glow);
  }
  .card:hover {
    border-color: var(--border-glow);
    box-shadow: 0 0 60px rgba(99,102,241,0.12);
    transform: translateY(-2px);
  }
  .card-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 20px; flex-wrap: wrap; gap: 8px;
  }
  .card-title {
    display: flex; align-items: center; gap: 10px;
    font-size: 18px; font-weight: 700;
  }
  .card-title .icon { font-size: 22px; }
  .card-desc { color: var(--text-secondary); font-size: 13px; margin-top: 2px; }

  /* ── Module Grid ── */
  .module-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; margin-bottom: 32px; }

  /* ── Progress Bar ── */
  .progress-bar-track {
    width: 100%; height: 8px; background: rgba(255,255,255,0.05);
    border-radius: 4px; overflow: hidden; position: relative;
  }
  .progress-bar-fill {
    height: 100%; border-radius: 4px;
    background: var(--gradient-hero);
    transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
  }
  .progress-bar-fill::after {
    content: ''; position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.2) 50%, transparent 100%);
    animation: shimmer 2s ease-in-out infinite;
  }
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }

  .module-score-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 700;
    padding: 4px 12px; border-radius: 8px;
    background: rgba(129,140,248,0.12); color: var(--accent-indigo);
  }
  .module-score-badge.high { background: rgba(52,211,153,0.12); color: var(--accent-emerald); }
  .module-score-badge.mid { background: rgba(251,191,36,0.12); color: var(--accent-amber); }
  .module-score-badge.low { background: rgba(251,113,133,0.12); color: var(--accent-rose); }

  /* ── File List ── */
  .file-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
  .file-row {
    display: flex; align-items: center; gap: 12px; padding: 10px 14px;
    background: var(--bg-glass); border: 1px solid var(--border);
    border-radius: var(--radius-sm); transition: var(--transition);
  }
  .file-row:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); }
  .file-name {
    font-family: 'JetBrains Mono', monospace; font-size: 12.5px;
    color: var(--accent-cyan); font-weight: 500; min-width: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .file-role { flex: 1; font-size: 12px; color: var(--text-muted); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .file-score-pill {
    font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
    padding: 2px 8px; border-radius: 6px; white-space: nowrap;
  }
  .file-score-pill.high { background: rgba(52,211,153,0.15); color: var(--accent-emerald); }
  .file-score-pill.mid { background: rgba(251,191,36,0.15); color: var(--accent-amber); }
  .file-score-pill.low { background: rgba(251,113,133,0.15); color: var(--accent-rose); }
  .file-loc { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); white-space: nowrap; }

  /* ── Milestones ── */
  .milestones { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
  .milestone-chip {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 11px; padding: 4px 10px; border-radius: 6px;
    border: 1px solid var(--border); transition: var(--transition);
  }
  .milestone-chip.done { background: rgba(52,211,153,0.08); border-color: rgba(52,211,153,0.2); color: var(--accent-emerald); }
  .milestone-chip.pending { background: rgba(255,255,255,0.02); color: var(--text-muted); }
  .milestone-icon { font-size: 12px; }

  /* ── Roadmap ── */
  .roadmap-section { margin-bottom: 40px; }
  .roadmap-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-top: 16px; }
  .roadmap-item {
    display: flex; align-items: center; gap: 12px; padding: 14px 16px;
    background: var(--bg-glass); border: 1px solid var(--border);
    border-radius: var(--radius-sm); transition: var(--transition);
  }
  .roadmap-item:hover { border-color: rgba(255,255,255,0.1); }
  .roadmap-icon { font-size: 18px; flex-shrink: 0; }
  .roadmap-label { font-size: 13px; color: var(--text-secondary); }
  .roadmap-item.done .roadmap-label { color: var(--accent-emerald); }

  /* ── Section Titles ── */
  .section-title {
    font-size: 20px; font-weight: 700; margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
  }
  .section-title .accent-line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--border-glow), transparent);
  }

  /* ── Footer ── */
  .footer {
    padding: 32px 0; margin-top: 20px;
    border-top: 1px solid var(--border);
    text-align: center; color: var(--text-muted); font-size: 12px;
  }
  .footer .timestamp { font-family: 'JetBrains Mono', monospace; color: var(--text-secondary); }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .module-grid { grid-template-columns: 1fr; }
    .hero-score { flex-direction: column; align-items: center; text-align: center; }
    .hero-stats { grid-template-columns: repeat(2, 1fr); text-align: left; }
    .header h1 { font-size: 22px; }
    .container { padding: 0 16px; }
  }

  /* ── Transitions for data updates ── */
  .fade-update { animation: fadeUpdate 0.5s ease; }
  @keyframes fadeUpdate {
    0% { opacity: 0.6; } 100% { opacity: 1; }
  }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="container" id="app">

  <!-- Header -->
  <header class="header">
    <div class="header-top">
      <div>
        <h1>🧬 Clinical Intelligence System</h1>
        <p class="header-subtitle">BioProj1 — Real-Time Implementation Progress</p>
      </div>
      <div class="live-badge"><span class="live-dot"></span> Live Tracking</div>
    </div>
  </header>

  <!-- Hero Score -->
  <section class="hero-score" id="hero-section">
    <div class="score-ring-container">
      <svg class="score-ring-bg" viewBox="0 0 180 180"><circle/></svg>
      <svg class="score-ring-fg" viewBox="0 0 180 180">
        <defs><linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#818cf8"/>
          <stop offset="50%" stop-color="#a78bfa"/>
          <stop offset="100%" stop-color="#22d3ee"/>
        </linearGradient></defs>
        <circle id="score-circle"/>
      </svg>
      <div class="score-value">
        <span class="score-number" id="overall-score">—</span>
        <span class="score-label">Overall</span>
      </div>
    </div>
    <div class="hero-stats">
      <div class="stat-item"><span class="stat-value emerald" id="stat-files">—</span><span class="stat-label">Files Implemented</span></div>
      <div class="stat-item"><span class="stat-value cyan" id="stat-loc">—</span><span class="stat-label">Lines of Code</span></div>
      <div class="stat-item"><span class="stat-value violet" id="stat-classes">—</span><span class="stat-label">Classes + Functions</span></div>
      <div class="stat-item"><span class="stat-value amber" id="stat-todos">—</span><span class="stat-label">TODOs Remaining</span></div>
    </div>
  </section>

  <!-- Module Cards -->
  <div class="section-title">Module Breakdown <span class="accent-line"></span></div>
  <div class="module-grid" id="module-grid"></div>

  <!-- Roadmap -->
  <section class="roadmap-section">
    <div class="section-title">Roadmap & Integration Readiness <span class="accent-line"></span></div>
    <div style="margin-bottom:12px;">
      <div class="progress-bar-track" style="height:6px;">
        <div class="progress-bar-fill" id="roadmap-bar" style="width:0%"></div>
      </div>
      <div style="display:flex; justify-content:space-between; margin-top:6px;">
        <span style="font-size:12px; color:var(--text-muted);">Integration checklist</span>
        <span style="font-size:12px; font-family:'JetBrains Mono',monospace; color:var(--accent-indigo);" id="roadmap-pct">0%</span>
      </div>
    </div>
    <div class="roadmap-grid" id="roadmap-grid"></div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <p>Auto-refreshes every 3s &nbsp;·&nbsp; Last scan: <span class="timestamp" id="timestamp">—</span></p>
  </footer>
</div>

<script>
const API = '/api/status';
let prevHash = '';

function scoreBadgeClass(score) {
  if (score >= 80) return 'high';
  if (score >= 50) return 'mid';
  return 'low';
}

function renderModuleCard(key, mod) {
  const badgeCls = scoreBadgeClass(mod.score);
  let filesHtml = '';
  for (const [fpath, f] of Object.entries(mod.files)) {
    const fname = fpath.split('/').pop();
    const cls = scoreBadgeClass(f.score);
    const loc = f.loc != null ? f.loc : '—';
    filesHtml += `
      <div class="file-row">
        <span class="file-name" title="${fpath}">${fname}</span>
        <span class="file-role">${f.role}</span>
        <span class="file-loc">${loc} LOC</span>
        <span class="file-score-pill ${cls}">${f.score}%</span>
      </div>`;
  }

  let msHtml = '';
  for (const ms of mod.milestones) {
    const cls = ms.done ? 'done' : 'pending';
    const icon = ms.done ? '✓' : '○';
    msHtml += `<span class="milestone-chip ${cls}"><span class="milestone-icon">${icon}</span> ${ms.label}</span>`;
  }

  return `
    <div class="card fade-update">
      <div class="card-header">
        <div>
          <div class="card-title"><span class="icon">${mod.icon}</span> ${mod.label}</div>
          <div class="card-desc">${mod.description}</div>
        </div>
        <span class="module-score-badge ${badgeCls}">${mod.score}%</span>
      </div>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" style="width:${mod.score}%"></div>
      </div>
      <div class="file-list">${filesHtml}</div>
      <div class="milestones">${msHtml}</div>
    </div>`;
}

function renderRoadmap(items) {
  return items.map(item => {
    const done = item.status === 'done';
    const icon = done ? '✅' : '⬜';
    const cls = done ? 'done' : '';
    return `
      <div class="roadmap-item ${cls}">
        <span class="roadmap-icon">${icon}</span>
        <span class="roadmap-label">${item.label}</span>
      </div>`;
  }).join('');
}

function update(data) {
  // Hash check — skip DOM update if nothing changed
  const hash = JSON.stringify(data);
  if (hash === prevHash) return;
  prevHash = hash;

  // Score ring
  const pct = data.overall_score;
  const circle = document.getElementById('score-circle');
  const circumference = 2 * Math.PI * 78;
  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = circumference - (circumference * pct / 100);
  document.getElementById('overall-score').textContent = Math.round(pct) + '%';

  // Stats
  document.getElementById('stat-files').textContent = data.total_files;
  document.getElementById('stat-loc').textContent = data.total_loc.toLocaleString();
  document.getElementById('stat-classes').textContent = data.total_classes + data.total_functions;
  document.getElementById('stat-todos').textContent = data.total_todos;

  // Modules
  const grid = document.getElementById('module-grid');
  grid.innerHTML = Object.entries(data.modules).map(([k, m]) => renderModuleCard(k, m)).join('');

  // Roadmap
  document.getElementById('roadmap-grid').innerHTML = renderRoadmap(data.roadmap);
  document.getElementById('roadmap-bar').style.width = data.roadmap_pct + '%';
  document.getElementById('roadmap-pct').textContent = data.roadmap_pct + '%';

  // Timestamp
  document.getElementById('timestamp').textContent = data.timestamp;
}

async function poll() {
  try {
    const res = await fetch(API);
    if (res.ok) {
      const data = await res.json();
      update(data);
    }
  } catch (e) {
    console.warn('Poll failed:', e);
  }
  setTimeout(poll, 3000);
}

poll();
</script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════════════════════════
# HTTP Server
# ══════════════════════════════════════════════════════════════════════════════

class DashboardHandler(SimpleHTTPRequestHandler):
    """Serves the dashboard and API endpoints."""

    def log_message(self, format, *args):
        """Suppress default request logging to keep terminal clean."""
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/status":
            data = run_full_analysis()
            payload = json.dumps(data, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))

        else:
            self.send_error(404)


def main():
    port = int(os.environ.get("TRACKER_PORT", "8050"))
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)

    print()
    print("  ╔══════════════════════════════════════════════════════════╗")
    print("  ║  🧬  BioProj1 — Real-Time Progress Tracker             ║")
    print("  ╠══════════════════════════════════════════════════════════╣")
    print(f"  ║  Dashboard → http://localhost:{port}                     ║")
    print(f"  ║  API       → http://localhost:{port}/api/status           ║")
    print("  ║  Auto-refresh: every 3s                                 ║")
    print("  ╠══════════════════════════════════════════════════════════╣")
    print("  ║  Press Ctrl+C to stop                                   ║")
    print("  ╚══════════════════════════════════════════════════════════╝")
    print()

    # Quick initial scan
    data = run_full_analysis()
    print(f"  Overall progress: {data['overall_score']}%  |  "
          f"{data['total_files']} files  |  "
          f"{data['total_loc']} LOC  |  "
          f"{data['total_todos']} TODOs")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  ⏹  Tracker stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
