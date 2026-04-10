"""
Custom CSS Styles — Premium dark-mode glassmorphism theme for the clinical dashboard.

Injected via st.markdown() to override Streamlit's default styling with a
research-grade medical interface aesthetic.
"""


def get_custom_css() -> str:
    """Return the full custom CSS for the Streamlit app."""
    return """
    <style>
    /* ── Google Font ─────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Root Variables ──────────────────────────────────────────────── */
    :root {
        --bg-primary: #0a0e1a;
        --bg-secondary: #111827;
        --bg-card: rgba(17, 24, 39, 0.7);
        --bg-glass: rgba(255, 255, 255, 0.03);
        --border-glass: rgba(255, 255, 255, 0.08);
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --accent-blue: #3b82f6;
        --accent-cyan: #06b6d4;
        --accent-purple: #8b5cf6;
        --accent-green: #10b981;
        --accent-amber: #f59e0b;
        --accent-red: #ef4444;
        --gradient-primary: linear-gradient(135deg, #3b82f6, #8b5cf6);
        --gradient-safe: linear-gradient(135deg, #10b981, #06b6d4);
        --gradient-risky: linear-gradient(135deg, #f59e0b, #f97316);
        --gradient-unsafe: linear-gradient(135deg, #ef4444, #dc2626);
        --shadow-glow: 0 0 30px rgba(59, 130, 246, 0.15);
        --radius: 16px;
        --radius-sm: 10px;
    }

    /* ── Global ──────────────────────────────────────────────────────── */
    .stApp {
        background: var(--bg-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-primary) !important;
    }

    .stApp > header { background: transparent !important; }

    .main .block-container {
        max-width: 1200px !important;
        padding: 2rem 2rem 4rem !important;
    }

    /* ── Sidebar ─────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-glass) !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: var(--text-secondary) !important;
        font-size: 0.9rem !important;
    }

    /* ── Typography ──────────────────────────────────────────────────── */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.03em !important;
        background: var(--gradient-primary) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        margin-bottom: 0.5rem !important;
    }

    h2 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        font-size: 1.5rem !important;
    }

    h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
    }

    p, li, span, label, .stMarkdown {
        color: var(--text-secondary) !important;
    }

    /* ── Cards / Glass Panels ────────────────────────────────────────── */
    .glass-card {
        background: var(--bg-glass) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--radius) !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        transition: all 0.3s ease !important;
    }

    .glass-card:hover {
        border-color: rgba(59, 130, 246, 0.2) !important;
        box-shadow: var(--shadow-glow) !important;
    }

    /* ── Diagnosis Cards ─────────────────────────────────────────────── */
    .diagnosis-card {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--radius-sm) !important;
        padding: 1.2rem !important;
        margin: 0.6rem 0 !important;
        border-left: 4px solid var(--accent-blue) !important;
        transition: all 0.25s ease !important;
    }

    .diagnosis-card:hover {
        transform: translateX(4px) !important;
        border-left-color: var(--accent-cyan) !important;
    }

    .diagnosis-card .condition-name {
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        font-size: 1.05rem !important;
        margin-bottom: 0.3rem !important;
    }

    .diagnosis-card .reasoning {
        color: var(--text-secondary) !important;
        font-size: 0.88rem !important;
        line-height: 1.5 !important;
    }

    /* ── Confidence Bar ──────────────────────────────────────────────── */
    .confidence-bar-container {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 20px !important;
        height: 10px !important;
        margin: 0.5rem 0 !important;
        overflow: hidden !important;
    }

    .confidence-bar {
        height: 100% !important;
        border-radius: 20px !important;
        background: var(--gradient-primary) !important;
        transition: width 1s cubic-bezier(0.22, 1, 0.36, 1) !important;
    }

    .confidence-bar.high { background: var(--gradient-safe) !important; }
    .confidence-bar.medium { background: var(--gradient-risky) !important; }
    .confidence-bar.low { background: var(--gradient-unsafe) !important; }

    /* ── Safety Badges ───────────────────────────────────────────────── */
    .safety-badge {
        display: inline-flex !important;
        align-items: center !important;
        padding: 0.5rem 1.2rem !important;
        border-radius: 50px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        margin: 0.3rem !important;
    }

    .badge-safe {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #10b981 !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }

    .badge-risky {
        background: rgba(245, 158, 11, 0.15) !important;
        color: #f59e0b !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }

    .badge-unsafe {
        background: rgba(239, 68, 68, 0.15) !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }

    /* ── Verdict Badges ──────────────────────────────────────────────── */
    .badge-approve {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #10b981 !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }

    .badge-flag {
        background: rgba(245, 158, 11, 0.15) !important;
        color: #f59e0b !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }

    .badge-reject {
        background: rgba(239, 68, 68, 0.15) !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }

    /* ── Metric Cards ────────────────────────────────────────────────── */
    .metric-card {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--radius-sm) !important;
        padding: 1.2rem !important;
        text-align: center !important;
    }

    .metric-value {
        font-size: 2rem !important;
        font-weight: 800 !important;
        background: var(--gradient-primary) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }

    .metric-label {
        color: var(--text-muted) !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        margin-top: 0.3rem !important;
    }

    /* ── Stage Headers ───────────────────────────────────────────────── */
    .stage-header {
        display: flex !important;
        align-items: center !important;
        gap: 0.8rem !important;
        padding: 1rem 0 0.5rem !important;
        border-bottom: 1px solid var(--border-glass) !important;
        margin-bottom: 1rem !important;
    }

    .stage-number {
        background: var(--gradient-primary) !important;
        color: white !important;
        width: 36px !important;
        height: 36px !important;
        border-radius: 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        flex-shrink: 0 !important;
    }

    /* ── Input Fields ────────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
    }

    /* ── Buttons ──────────────────────────────────────────────────────── */
    .stButton > button {
        background: var(--gradient-primary) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 0.7rem 2rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        text-transform: none !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.35) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── Expander ─────────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-glass) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
    }

    /* ── Tabs ─────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        background: var(--bg-glass) !important;
        border-radius: var(--radius-sm) !important;
        padding: 4px !important;
        border: 1px solid var(--border-glass) !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        color: var(--text-muted) !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.2rem !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--gradient-primary) !important;
        color: white !important;
    }

    /* ── Progress Bar ────────────────────────────────────────────────── */
    .stProgress > div > div > div > div {
        background: var(--gradient-primary) !important;
        border-radius: 20px !important;
    }

    /* ── Divider ──────────────────────────────────────────────────────── */
    hr {
        border-color: var(--border-glass) !important;
        margin: 1.5rem 0 !important;
    }

    /* ── Animations ──────────────────────────────────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    .animate-in {
        animation: fadeInUp 0.5s ease-out forwards !important;
    }

    .pulse { animation: pulse 2s ease-in-out infinite !important; }

    /* ── Scrollbar ────────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb {
        background: var(--border-glass);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

    /* ── Hide Streamlit Defaults ─────────────────────────────────────── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    </style>
    """
