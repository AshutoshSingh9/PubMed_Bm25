"""
Results Display — Renders the 3-stage pipeline output in the Streamlit dashboard.

Displays diagnosis cards, critic findings, and safety assessment with
animated transitions and interactive expand/collapse sections.
"""

import json
import streamlit as st

from ui.components import (
    render_stage_header,
    render_diagnosis_card,
    render_safety_badge,
    render_verdict_badge,
    render_metric_card,
    render_glass_card,
    render_error_item,
    render_bias_item,
    render_missing_condition,
)


def render_results(results: dict):
    """
    Render the complete 3-stage pipeline results.

    Args:
        results: Combined output dict from ClinicalPipeline.run()
    """
    diagnosis = results.get("diagnosis_stage", {})
    critic = results.get("critic_stage", {})
    safety = results.get("safety_stage", {})
    metadata = results.get("metadata", {})

    # ── Summary Metrics ────────────────────────────────────────────────
    _render_summary_metrics(diagnosis, safety, metadata)

    st.markdown("---")

    # ── Tabbed View ────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔬 Diagnosis",
        "🔍 Critical Review",
        "🛡️ Safety Audit",
        "📄 Raw JSON",
    ])

    with tab1:
        _render_diagnosis_stage(diagnosis)

    with tab2:
        _render_critic_stage(critic)

    with tab3:
        _render_safety_stage(safety)

    with tab4:
        _render_raw_json(results)


def _render_summary_metrics(diagnosis: dict, safety: dict, metadata: dict):
    """Render top-level summary metrics row."""
    conditions = diagnosis.get("possible_conditions", [])
    red_flags = diagnosis.get("red_flags", [])
    safety_level = safety.get("safety_level", "UNKNOWN")
    verdict = safety.get("final_verdict", "UNKNOWN")
    elapsed = metadata.get("total_time_seconds", 0)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_metric_card(str(len(conditions)), "Conditions")
    with col2:
        render_metric_card(str(len(red_flags)), "Red Flags")
    with col3:
        render_metric_card(f"{elapsed}s", "Time")
    with col4:
        st.markdown("<div class='metric-card' style='padding-top:0.8rem;'>", unsafe_allow_html=True)
        render_safety_badge(safety_level)
        st.markdown("<div class='metric-label'>Safety</div></div>", unsafe_allow_html=True)
    with col5:
        st.markdown("<div class='metric-card' style='padding-top:0.8rem;'>", unsafe_allow_html=True)
        render_verdict_badge(verdict)
        st.markdown("<div class='metric-label'>Verdict</div></div>", unsafe_allow_html=True)


def _render_diagnosis_stage(diagnosis: dict):
    """Render Stage 1 — Diagnostic Reasoning results."""
    render_stage_header(1, "Diagnostic Reasoning", "🔬")

    # Reasoning summary
    summary = diagnosis.get("reasoning_summary", "")
    if summary:
        render_glass_card(f"<p style='color: var(--text-secondary) !important;'>{summary}</p>")

    # Differential diagnoses
    conditions = diagnosis.get("possible_conditions", [])
    if conditions:
        st.markdown("#### Differential Diagnoses")
        for i, condition in enumerate(conditions, 1):
            render_diagnosis_card(condition, i)
    else:
        st.info("No differential diagnoses generated.")

    # Recommended tests
    tests = diagnosis.get("recommended_tests", [])
    if tests:
        with st.expander(f"🧪 Recommended Tests ({len(tests)})", expanded=True):
            for test in tests:
                st.markdown(f"- {test}")

    # Red flags
    red_flags = diagnosis.get("red_flags", [])
    if red_flags:
        with st.expander(f"🚨 Red Flags ({len(red_flags)})", expanded=True):
            for flag in red_flags:
                st.markdown(
                    f"<div style='color: var(--accent-red) !important; "
                    f"padding: 0.3rem 0; font-weight: 500;'>⚠️ {flag}</div>",
                    unsafe_allow_html=True,
                )

    # Data limitations
    limitations = diagnosis.get("data_limitations", [])
    if limitations:
        with st.expander(f"📌 Data Limitations ({len(limitations)})"):
            for lim in limitations:
                st.markdown(f"- {lim}")


def _render_critic_stage(critic: dict):
    """Render Stage 2 — Critical Evaluation results."""
    render_stage_header(2, "Critical Evaluation", "🔍")

    # Review summary
    summary = critic.get("review_summary", "")
    if summary:
        render_glass_card(f"<p style='color: var(--text-secondary) !important;'>{summary}</p>")

    # Confidence assessment
    conf = critic.get("confidence_assessment", {})
    if conf:
        calibration = conf.get("overall_calibration", "UNKNOWN")
        color_map = {
            "WELL_CALIBRATED": "var(--accent-green)",
            "OVERCONFIDENT": "var(--accent-amber)",
            "UNDERCONFIDENT": "var(--accent-blue)",
        }
        color = color_map.get(calibration, "var(--text-muted)")

        render_glass_card(
            f"<div style='text-align:center;'>"
            f"<span style='font-size:0.8rem; text-transform:uppercase; letter-spacing:0.1em; "
            f"color: var(--text-muted) !important;'>Confidence Calibration</span><br>"
            f"<span style='font-size:1.4rem; font-weight:700; color:{color} !important;'>"
            f"{calibration.replace('_', ' ')}</span></div>"
        )

        adjustments = conf.get("adjustments", [])
        if adjustments:
            for adj in adjustments:
                st.markdown(f"- {adj}")

    # Errors found
    errors = critic.get("errors_found", [])
    if errors:
        st.markdown(f"#### Errors Found ({len(errors)})")
        for error in errors:
            if isinstance(error, dict):
                render_error_item(error)
            else:
                st.markdown(f"- {error}")

    # Missing conditions
    missing = critic.get("missing_conditions", [])
    if missing:
        st.markdown(f"#### Missing Conditions ({len(missing)})")
        for condition in missing:
            if isinstance(condition, dict):
                render_missing_condition(condition)
            else:
                st.markdown(f"- {condition}")

    # Biases
    biases = critic.get("biases_detected", [])
    if biases:
        st.markdown(f"#### Cognitive Biases Detected ({len(biases)})")
        for bias in biases:
            if isinstance(bias, dict):
                render_bias_item(bias)
            else:
                st.markdown(f"- {bias}")

    # Revision needed
    revision = critic.get("revision_required", None)
    if revision is not None:
        if revision:
            st.warning("📝 **Revision recommended** based on critical review findings.")
        else:
            st.success("✅ **No revision required** — diagnostic reasoning is sound.")


def _render_safety_stage(safety: dict):
    """Render Stage 3 — Safety Validation results."""
    render_stage_header(3, "Safety Validation", "🛡️")

    # Safety level + Verdict row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Safety Level**")
        render_safety_badge(safety.get("safety_level", "UNKNOWN"))
    with col2:
        st.markdown("**Hallucination Risk**")
        risk = safety.get("hallucination_risk", "UNKNOWN")
        risk_colors = {"LOW": "var(--accent-green)", "MEDIUM": "var(--accent-amber)", "HIGH": "var(--accent-red)"}
        color = risk_colors.get(risk, "var(--text-muted)")
        st.markdown(
            f"<span style='font-size:1.2rem; font-weight:700; color:{color} !important;'>{risk}</span>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown("**Final Verdict**")
        render_verdict_badge(safety.get("final_verdict", "UNKNOWN"))

    # Verdict reasoning
    reasoning = safety.get("verdict_reasoning", "")
    if reasoning:
        render_glass_card(f"<p style='color: var(--text-secondary) !important;'>💬 {reasoning}</p>")

    # Critical conditions check
    crit_check = safety.get("critical_conditions_check", {})
    if crit_check:
        checked = crit_check.get("checked", [])
        missed = crit_check.get("missed", [])

        if checked:
            with st.expander(f"✅ Critical Conditions Checked ({len(checked)})", expanded=False):
                for c in checked:
                    st.markdown(f"- ✅ {c}")

        if missed:
            with st.expander(f"❌ Critical Conditions Missed ({len(missed)})", expanded=True):
                for m in missed:
                    st.markdown(
                        f"<div style='color: var(--accent-red) !important; font-weight:600;'>❌ {m}</div>",
                        unsafe_allow_html=True,
                    )

    # Unsupported claims
    claims = safety.get("unsupported_claims", [])
    if claims:
        with st.expander(f"⚠️ Unsupported Claims ({len(claims)})", expanded=True):
            for claim in claims:
                if isinstance(claim, dict):
                    st.markdown(
                        f"**Claim:** {claim.get('claim', 'N/A')}\n\n"
                        f"**Concern:** {claim.get('concern', 'N/A')}"
                    )
                    st.markdown("---")
                else:
                    st.markdown(f"- {claim}")

    # Harm assessment
    harm = safety.get("harm_assessment", {})
    if harm:
        potential_harms = harm.get("potential_harms", [])
        if potential_harms:
            with st.expander(f"⚡ Harm Assessment — {harm.get('risk_level', 'N/A')} Risk"):
                for h in potential_harms:
                    st.markdown(f"- {h}")

    # General issues
    issues = safety.get("issues", [])
    if issues:
        with st.expander(f"📋 Issues ({len(issues)})"):
            for issue in issues:
                st.markdown(f"- {issue}")

    # Recommendations
    recs = safety.get("recommendations", [])
    if recs:
        with st.expander(f"💡 Recommendations ({len(recs)})", expanded=True):
            for rec in recs:
                st.markdown(f"- {rec}")


def _render_raw_json(results: dict):
    """Render the raw JSON output with syntax highlighting."""
    st.markdown("### 📄 Raw Pipeline Output")
    st.markdown(
        "<p style='color: var(--text-muted) !important; font-size:0.85rem;'>"
        "Complete structured JSON output from all three pipeline stages."
        "</p>",
        unsafe_allow_html=True,
    )

    # Clean internal metadata
    clean = {k: v for k, v in results.items() if not k.startswith("_")}
    for stage_key in ["diagnosis_stage", "critic_stage", "safety_stage"]:
        if stage_key in clean and isinstance(clean[stage_key], dict):
            clean[stage_key] = {
                k: v for k, v in clean[stage_key].items() if not k.startswith("_")
            }

    st.code(json.dumps(clean, indent=2, default=str), language="json")

    # Download button
    json_str = json.dumps(clean, indent=2, default=str)
    st.download_button(
        label="⬇️ Download JSON",
        data=json_str,
        file_name="clinical_analysis_results.json",
        mime="application/json",
        use_container_width=True,
    )
