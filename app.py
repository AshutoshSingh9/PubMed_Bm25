"""
Clinical Intelligence System — Main Streamlit Application.

A multi-stage diagnostic reasoning engine that simulates three expert roles:
1. Diagnostician — generates differential diagnoses
2. Clinical Critic — evaluates reasoning quality
3. Safety Validator — ensures reliability and non-harm

Run: streamlit run app.py
"""

import sys
import logging
from pathlib import Path

import streamlit as st

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui.styles import get_custom_css
from ui.patient_form import render_patient_form
from ui.results_display import render_results
from pipeline.orchestrator import ClinicalPipeline
from pipeline.llm_provider import LLMProvider

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Intelligence System",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject Custom CSS ─────────────────────────────────────────────────────────
st.markdown(get_custom_css(), unsafe_allow_html=True)


# ── Session State Init ────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = None
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False


# ── Sidebar ────────────────────────────────────────────────────────────────────
def _render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0;">
                <span style="font-size:2.5rem;">🧬</span>
                <h2 style="margin:0.3rem 0 0 !important; font-size:1.2rem !important;">
                    Clinical Intelligence
                </h2>
                <p style="color: var(--text-muted) !important; font-size:0.8rem; margin:0 !important;">
                    Multi-Stage Diagnostic Engine
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # System status
        st.markdown("### ⚙️ System Status")

        llm = LLMProvider()
        health = llm.check_health()

        if health["status"] == "connected":
            st.success(f"🟢 Ollama: Connected")
            if health.get("model_available"):
                st.success(f"🟢 Model: {health['requested_model']}")
            else:
                st.warning(f"🟡 Model not pulled")
                st.code(f"ollama pull {health['requested_model']}", language="bash")
        else:
            st.error("🔴 Ollama: Disconnected")
            st.code("ollama serve", language="bash")
            if health.get("action_needed"):
                st.caption(health["action_needed"])

        st.markdown("---")

        # Pipeline info
        st.markdown("### 📊 Pipeline Stages")
        st.markdown(
            """
            1. **🔬 Diagnostician** — Differential diagnoses
            2. **🔍 Clinical Critic** — Reasoning review
            3. **🛡️ Safety Validator** — Harm prevention
            """
        )

        st.markdown("---")

        # Disclaimer
        st.markdown(
            """
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 10px; padding: 1rem; margin-top: 0.5rem;">
                <p style="color: #ef4444 !important; font-weight: 600; font-size: 0.85rem; margin: 0 0 0.3rem !important;">
                    ⚠️ Medical Disclaimer
                </p>
                <p style="color: var(--text-muted) !important; font-size: 0.75rem; margin: 0 !important; line-height: 1.4;">
                    This system is for <strong>educational and research purposes only</strong>.
                    It does NOT provide medical advice and should NOT be used for
                    clinical decision-making. Always consult a qualified healthcare professional.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Main Content ──────────────────────────────────────────────────────────────
def main():
    _render_sidebar()

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align: center; padding: 1rem 0 2rem;">
            <h1 style="font-size: 2.8rem !important; margin-bottom: 0.5rem !important;">
                🧬 Clinical Intelligence System
            </h1>
            <p style="color: var(--text-muted) !important; font-size: 1.1rem; max-width: 700px; margin: 0 auto;">
                AI-powered multi-stage diagnostic reasoning with biomedical RAG,
                genomic variant analysis, and clinical safety validation
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Two-Column Layout ─────────────────────────────────────────────
    col_form, col_results = st.columns([1, 1.5])

    with col_form:
        patient_data = render_patient_form()

        if patient_data:
            st.session_state.pipeline_running = True

    # ── Run Pipeline ──────────────────────────────────────────────────
    with col_results:
        if st.session_state.pipeline_running and patient_data:
            _run_pipeline(patient_data)
            st.session_state.pipeline_running = False

        elif st.session_state.results:
            render_results(st.session_state.results)
            if "hygiene" in st.session_state and st.session_state.hygiene:
                _render_hygiene_report(st.session_state.hygiene)

        else:
            # Empty state
            st.markdown(
                """
                <div style="text-align: center; padding: 4rem 2rem;">
                    <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.3;">🔬</div>
                    <h3 style="color: var(--text-muted) !important; font-weight: 400;">
                        Enter patient data and click<br>
                        <strong>"Run Clinical Analysis"</strong> to begin
                    </h3>
                    <p style="color: var(--text-muted) !important; font-size: 0.85rem; margin-top: 1rem; opacity: 0.5;">
                        The system will run 3 sequential analysis stages:<br>
                        Diagnostic Reasoning → Critical Evaluation → Safety Validation
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _run_pipeline(patient_data: dict):
    """Execute the clinical pipeline with progress indicators."""

    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_callback(stage: str, message: str, progress: float):
        progress_bar.progress(progress)
        status_text.markdown(
            f"<div class='glass-card pulse' style='text-align:center;'>"
            f"<span style='font-size: 0.95rem; color: var(--accent-cyan) !important; font-weight: 600;'>"
            f"⏳ {message}</span></div>",
            unsafe_allow_html=True,
        )

    try:
        pipeline = ClinicalPipeline(progress_callback=progress_callback)

        def main_run():
            return pipeline.run(
                symptoms=patient_data["symptoms"],
                patient_history=patient_data.get("medical_history", ""),
                age=patient_data.get("age"),
                sex=patient_data.get("sex"),
                genetic_data=patient_data.get("genetic_data", ""),
                additional_context=patient_data.get("additional_context", ""),
            )

        from agents.run_parallel import run_with_hygiene_thread
        
        # Run the pipeline and the hygiene agent in parallel
        parallel_results = run_with_hygiene_thread(main_run, print_report=False)
        results = parallel_results["pipeline"]
        hygiene = parallel_results["hygiene"]

        # Store results and clear progress
        st.session_state.results = results
        st.session_state.hygiene = hygiene
        progress_bar.empty()
        status_text.empty()

        # Display results
        render_results(results)
        
        # Render hygiene report
        _render_hygiene_report(hygiene)

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        logger.error(f"Pipeline failed: {e}", exc_info=True)

        st.error(f"❌ **Pipeline Error:** {e}")

        # Show helpful troubleshooting
        st.markdown(
            """
            ### 🔧 Troubleshooting

            1. **Ollama not running?**
               ```bash
               ollama serve
               ```

            2. **Model not pulled?**
               ```bash
               ollama pull llama3.1
               ```

            3. **Dependencies missing?**
               ```bash
               pip3 install -r requirements.txt
               ```
            """
        )

def _render_hygiene_report(hygiene_report: dict):
    if not hygiene_report:
        return
        
    st.markdown("---")
    st.markdown("### 🧹 Parallel Code Hygiene Audit")
    
    score = hygiene_report.get("health_score", 0)
    dyn_score = hygiene_report.get("dynamic_linking_score", 0)
    verdict = hygiene_report.get("verdict", "UNKNOWN")
    
    col1, col2, col3 = st.columns(3)
    
    color_score = "green" if score >= 90 else "orange" if score >= 70 else "red"
    color_dyn = "green" if dyn_score >= 90 else "orange" if dyn_score >= 70 else "red"
    
    col1.markdown(f"**Health Score**: <span style='color:{color_score};'>{score}/100</span>", unsafe_allow_html=True)
    col2.markdown(f"**Dynamic Linking**: <span style='color:{color_dyn};'>{dyn_score}%</span>", unsafe_allow_html=True)
    col3.markdown(f"**Verdict**: {verdict}")
    
    summary = hygiene_report.get("summary", {})
    st.caption(f"Scanned {summary.get('files_scanned', 0)} files in {summary.get('scan_time_seconds', 0):.3f}s. "
               f"Found {summary.get('errors', 0)} errors and {summary.get('warnings', 0)} warnings.")
               
    findings = hygiene_report.get("findings", [])
    if findings:
        with st.expander("View Hygiene Findings", expanded=verdict != "CLEAN"):
            for f in findings:
                severity_emoji = "🔴" if f['severity'] == "ERROR" else "⚠️" if f['severity'] == "WARNING" else "ℹ️"
                st.markdown(f"{severity_emoji} **{f['severity']}** &nbsp;&nbsp; `{f['file']}:{f['line']}` &nbsp;&nbsp; *(Rule: {f['rule']})*")
                st.markdown(f"_{f['message']}_")
                st.markdown(f"↳ **Suggested fix:** {f['suggestion']}")
                st.markdown("---")

if __name__ == "__main__":
    main()
