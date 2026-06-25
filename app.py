"""
Streamlit entry point.

Run with:
    streamlit run frontend/app.py

Make sure the FastAPI backend is running first:
    python app.py
"""

from __future__ import annotations
import os
import sys

# Ensure project root is on the path when launched from any directory
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from frontend.pages import (
    page_stock_analysis,
    page_stock_comparison,
    page_portfolio_analysis,
    page_market_brief,
)

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Indian Stock Research Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Tighten top padding */
  .block-container { padding-top: 1.5rem; }

  /* Make tabs a bit larger */
  .stTabs [data-baseweb="tab"] {
      font-size: 0.95rem;
      font-weight: 500;
      padding: 8px 18px;
  }

  /* Button hover */
  div.stButton > button:hover {
      border-color: #1f77b4;
      color: #1f77b4;
  }

  /* Metric delta colours */
  [data-testid="stMetricDelta"] { font-weight: 600; }

  /* Subtle card-like expander */
  .streamlit-expanderHeader {
      font-weight: 600;
      background: #f8f9fa;
      border-radius: 6px;
  }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Indian Stock Research")
    st.caption("Multi-Agent AI Platform | Powered by Gemini + LangGraph")
    st.divider()

    page = st.radio(
        "Navigate",
        options=[
            "🔍 Stock Analysis",
            "⚔️ Stock Comparison",
            "💼 Portfolio Analysis",
            "🇮🇳 Market Brief",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("#### ⚙️ Settings")
    backend_url = st.text_input(
        "Backend URL",
        value=os.getenv("BACKEND_URL", "http://localhost:8000"),
        help="URL of the FastAPI backend server",
    )
    os.environ["BACKEND_URL"] = backend_url

    st.divider()
    st.markdown("#### ℹ️ About")
    st.markdown("""
    This platform uses **6 AI agents** running in parallel:
    - 📰 News Agent (Google RSS)
    - 💹 Financial Agent (yfinance)
    - 😊 Sentiment Agent (FinBERT)
    - 📊 Technical Agent (pandas-ta)
    - 🌐 Sector Agent (peer comparison)
    - 🏢 Corporate Agent (dividends, splits)

    All powered by **Gemini** via LangGraph.
    """)

    st.divider()

    # Backend health check
    try:
        import httpx
        with httpx.Client(timeout=3.0) as c:
            r = c.get(f"{backend_url}/health")
        if r.status_code == 200:
            st.success("✅ Backend connected")
        else:
            st.warning(f"⚠️ Backend returned {r.status_code}")
    except Exception:
        st.error("❌ Backend offline")
        st.caption("Start with: `python app.py`")


# ── Page routing ──────────────────────────────────────────────────────────────
if "Stock Analysis" in page:
    page_stock_analysis()
elif "Stock Comparison" in page:
    page_stock_comparison()
elif "Portfolio" in page:
    page_portfolio_analysis()
elif "Market Brief" in page:
    page_market_brief()