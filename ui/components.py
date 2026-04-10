"""
Reusable Streamlit UI Components — Cards, badges, bars, and panels.

Renders HTML/CSS components within Streamlit using st.markdown(unsafe_allow_html).
Provides a consistent visual language across the dashboard.
"""

import streamlit as st


def render_stage_header(number: int, title: str, icon: str = ""):
    """Render a styled stage section header."""
    st.markdown(
        f"""
        <div class="stage-header">
            <div class="stage-number">{number}</div>
            <h2 style="margin:0 !important; padding:0 !important;">{icon} {title}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_diagnosis_card(condition: dict, rank: int):
    """Render a single diagnosis condition card with confidence bar."""
    name = condition.get("name", "Unknown Condition")
    confidence = condition.get("confidence", 0)
    reasoning = condition.get("reasoning", "No reasoning provided.")

    # Confidence level class
    if confidence >= 0.7:
        level_class = "high"
        level_label = "High"
    elif confidence >= 0.4:
        level_class = "medium"
        level_label = "Medium"
    else:
        level_class = "low"
        level_label = "Low"

    st.markdown(
        f"""
        <div class="diagnosis-card animate-in" style="animation-delay: {rank * 0.1}s">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="condition-name">#{rank} {name}</div>
                <span style="color: var(--text-muted); font-size: 0.85rem; font-weight: 600;">
                    {confidence:.0%} ({level_label})
                </span>
            </div>
            <div class="confidence-bar-container">
                <div class="confidence-bar {level_class}" style="width: {confidence * 100}%"></div>
            </div>
            <div class="reasoning">{reasoning}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_safety_badge(safety_level: str):
    """Render a safety level badge (SAFE / RISKY / UNSAFE)."""
    badge_map = {
        "SAFE": ("badge-safe", "🟢"),
        "RISKY": ("badge-risky", "🟡"),
        "UNSAFE": ("badge-unsafe", "🔴"),
    }
    css_class, icon = badge_map.get(safety_level.upper(), ("badge-risky", "⚪"))

    st.markdown(
        f"""
        <span class="safety-badge {css_class}">
            {icon}&nbsp; {safety_level.upper()}
        </span>
        """,
        unsafe_allow_html=True,
    )


def render_verdict_badge(verdict: str):
    """Render a final verdict badge (APPROVE / FLAG / REJECT)."""
    badge_map = {
        "APPROVE": ("badge-approve", "✅"),
        "FLAG": ("badge-flag", "⚠️"),
        "REJECT": ("badge-reject", "❌"),
    }
    css_class, icon = badge_map.get(verdict.upper(), ("badge-flag", "❓"))

    st.markdown(
        f"""
        <span class="safety-badge {css_class}">
            {icon}&nbsp; {verdict.upper()}
        </span>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(value: str, label: str):
    """Render a single metric card with large value and small label."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_glass_card(content: str, extra_class: str = ""):
    """Render content inside a glass-morphism card."""
    st.markdown(
        f"""
        <div class="glass-card {extra_class}">
            {content}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_error_item(error: dict):
    """Render a critic error finding."""
    severity = error.get("severity", "MEDIUM")
    color_map = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#3b82f6"}
    color = color_map.get(severity, "#94a3b8")

    st.markdown(
        f"""
        <div class="diagnosis-card" style="border-left-color: {color} !important;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <span style="font-weight: 600; color: var(--text-primary) !important; font-size: 0.95rem;">
                    {error.get('error', 'Unknown error')}
                </span>
                <span style="color: {color}; font-weight: 700; font-size: 0.8rem; text-transform: uppercase;">
                    {severity}
                </span>
            </div>
            <div class="reasoning">
                💡 <strong>Correction:</strong> {error.get('correction', 'N/A')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_bias_item(bias: dict):
    """Render a detected cognitive bias."""
    st.markdown(
        f"""
        <div class="diagnosis-card" style="border-left-color: var(--accent-purple) !important;">
            <div class="condition-name">🧠 {bias.get('bias_type', 'Unknown Bias')}</div>
            <div class="reasoning">{bias.get('description', 'No description')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_missing_condition(condition: dict):
    """Render a missing condition that should have been considered."""
    st.markdown(
        f"""
        <div class="diagnosis-card" style="border-left-color: var(--accent-amber) !important;">
            <div class="condition-name">⚠️ {condition.get('name', 'Unknown')}</div>
            <div class="reasoning">{condition.get('reasoning', 'No reasoning')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
