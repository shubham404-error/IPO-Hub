import streamlit as st

def inject_styles():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
@import url('https://api.fontshare.com/v2/css?f[]=clash-display@400,500,600,700&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Clash Display', sans-serif !important;
}
.stApp { background: #0b0d10; }
.block-container {
    max-width: 1100px;
    padding: 4rem clamp(0.7rem, 2.5vw, 1.5rem) 3rem;
}
h1 {
    font-size: clamp(1.55rem, 5vw, 2.25rem) !important;
    line-height: 1.08 !important;
    margin-bottom: 0.25rem !important;
}
h2 { font-size: clamp(1.25rem, 4vw, 1.7rem) !important; }
h3 { font-size: clamp(1.05rem, 3.5vw, 1.3rem) !important; }
button, input, textarea, select {
    font-family: 'Inter', sans-serif !important;
}

/* Navigation lives in Streamlit's sidebar. The main content stays clean on mobile. */

/* Discovery cards */
.ipo-card-title {
    font-size: 1.05rem;
    font-weight: 750;
    line-height: 1.18;
    overflow-wrap: anywhere;
    word-break: break-word;
    margin: 0 0 0.22rem 0;
}
.ipo-card-meta {
    font-size: 0.75rem;
    line-height: 1.35;
    opacity: 0.65;
}
.ipo-card-value {
    font-size: 1.12rem;
    font-weight: 600;
    line-height: 1.2;
    overflow-wrap: anywhere;
    word-break: break-word;
}
.ipo-card-label {
    font-size: 0.68rem;
    line-height: 1.1;
    margin-bottom: 0.18rem;
    opacity: 0.62;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.ai-score-strip {
    border-top: 1px solid rgba(255,255,255,0.10);
    margin-top: 0.7rem;
    padding-top: 0.7rem;
}
.calc-hero {
    padding: 0.85rem 0.9rem;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 12px;
    background: rgba(255,255,255,0.025);
}
.small-note { font-size: 0.78rem; opacity: 0.65; }

[data-testid="stMetricValue"] {
    font-size: 1.12rem !important;
    line-height: 1.15 !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.68rem !important;
    white-space: normal !important;
}
[data-testid="stMetricDelta"] { font-size: 0.66rem !important; }
[data-testid="stVerticalBlock"] { gap: 0.7rem; }

.ipo-card-content { width: 100%; min-width: 0; }
.ipo-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem 1rem;
    margin-top: 0.95rem;
    width: 100%;
}
.ipo-metric { min-width: 0; }
.ipo-card-label { display: block; margin: 0 0 0.28rem 0; }
.ipo-card-value { display: block; margin: 0; }

.stButton > button {
    width: 100%;
    min-height: 2.65rem;
    border-radius: 10px;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 0.35rem 0.55rem;
}

.alloc-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:.4rem 0 1rem; }
.alloc-card, .strategy-row, .alloc-result { border:1px solid rgba(255,255,255,.10); border-radius:14px; background:rgba(255,255,255,.025); padding:.9rem; }
.alloc-label { font-size:.68rem; opacity:.62; letter-spacing:.05em; }
.alloc-big { font-size:1.15rem; font-weight:800; margin:.35rem 0; }
.alloc-source { font-size:.66rem; margin-top:.5rem; opacity:.5; }
.alloc-result { margin:.6rem 0 1rem; text-align:center; }
.alloc-result-number { font-size:2.35rem; font-weight:850; line-height:1.1; margin:.2rem 0; }
.strategy-row { display:flex; justify-content:space-between; align-items:center; margin:.55rem 0; gap:1rem; }

@media (max-width: 480px) {
    /* Streamlit's mobile toolbar is fixed above the app content.
       Reserve a full safe-area so the first heading can never sit underneath it. */
    .block-container {
        padding-top: 7rem !important;
        padding-left: 0.55rem;
        padding-right: 0.55rem;
    }

    [data-testid="stHeader"] {
        z-index: 1000 !important;
    }

    .alloc-grid { grid-template-columns:1fr; }
    .alloc-result-number { font-size:2rem; }
    .strategy-row { padding:.8rem; }

    .ipo-card-title { font-size: 1.02rem; }
    .ipo-card-value { font-size: 1.08rem; }
    .ipo-metric-grid { gap: 1rem 0.85rem; }
    [data-testid="stMetricValue"] { font-size: 1rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.62rem !important; }
    .stButton > button {
        min-height: 2.55rem;
        font-size: 0.78rem;
    }
}
</style>
""", unsafe_allow_html=True)
