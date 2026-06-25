"""
Four Streamlit page renderers — one per tab.
Each page calls the FastAPI backend via httpx and renders the response.
"""

from __future__ import annotations
import os

import httpx
import streamlit as st

from frontend.components import (
    render_header, recommendation_badge, confidence_gauge,
    error_banner, financial_metrics_table, technical_indicators_grid,
    sentiment_badge, trend_badge, sector_peer_table,
    corporate_actions_list, sector_allocation_chart,
    download_report_button, metric_card,
)

_BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
_TIMEOUT = httpx.Timeout(180.0)   # analyses can take up to 3 minutes


# ─────────────────────────────────────────────────────────────────────────────
# Shared API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _post(path: str, payload: dict) -> dict | None:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_BACKEND}/api/v1{path}", json=payload)
        if resp.status_code == 200:
            return resp.json()
        st.error(f"API error {resp.status_code}: {resp.json().get('detail', resp.text[:200])}")
        return None
    except httpx.ConnectError:
        st.error(
            "❌ Cannot connect to the backend. "
            "Make sure the FastAPI server is running: `python app.py`"
        )
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def _get(path: str) -> dict | None:
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(f"{_BACKEND}/api/v1{path}")
        if resp.status_code == 200:
            return resp.json()
        st.error(f"API error {resp.status_code}: {resp.json().get('detail', resp.text[:200])}")
        return None
    except httpx.ConnectError:
        st.error("❌ Cannot connect to the backend. Start with: `python app.py`")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Page 1 — Stock Analysis
# ─────────────────────────────────────────────────────────────────────────────

def page_stock_analysis() -> None:
    render_header(
        "🔍 Stock Analysis",
        "Enter any NSE/BSE stock symbol to generate an institutional-quality research report.",
    )

    # ── Input ─────────────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        ticker = st.text_input(
            "Stock Symbol",
            placeholder="e.g. TCS, RELIANCE, HDFCBANK, ZOMATO",
            label_visibility="collapsed",
        ).strip().upper()
    with col_btn:
        analyse = st.button("Analyse", type="primary", use_container_width=True)

    # ── Quick picks ───────────────────────────────────────────────────────────
    st.caption("Quick picks:")
    quick_cols = st.columns(8)
    quick_tickers = ["TCS", "RELIANCE", "INFY", "HDFCBANK", "TATAMOTORS", "ZOMATO", "SUNPHARMA", "WIPRO"]
    for i, qt in enumerate(quick_tickers):
        if quick_cols[i].button(qt, key=f"quick_{qt}"):
            ticker  = qt
            analyse = True

    if not analyse or not ticker:
        _render_analysis_placeholder()
        return

    # ── Run analysis ──────────────────────────────────────────────────────────
    with st.spinner(f"Running multi-agent analysis for **{ticker}** — this takes 30–60 seconds…"):
        data = _post("/analyze", {"ticker": ticker})

    if not data:
        return

    # ── Results ───────────────────────────────────────────────────────────────
    error_banner(data.get("errors", {}))

    # Top summary row
    st.markdown(f"### {ticker} — Analysis Result")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.markdown("**Recommendation**")
        recommendation_badge(data.get("recommendation"))
    with c2:
        confidence_gauge(data.get("confidence_score"))
    with c3:
        status_icon = "✅" if data.get("status") == "success" else "⚠️"
        st.metric("Status", f"{status_icon} {data.get('status', '—').title()}")

    if data.get("executive_summary"):
        st.info(f"📋 **Executive Summary:** {data['executive_summary']}")

    # ── Tabbed detail sections ─────────────────────────────────────────────────
    tabs = st.tabs(["📄 Full Report", "💹 Financials", "📊 Technical", "🌐 Sector", "🏢 Corporate", "😊 Sentiment"])

    with tabs[0]:
        if data.get("report_markdown"):
            st.markdown(data["report_markdown"])
            st.divider()
            fname = f"{ticker}_research_report.pdf"
            download_report_button(data["report_markdown"], fname)
        else:
            st.warning("Report not available.")

    with tabs[1]:
        _render_financial_tab(data)

    with tabs[2]:
        _render_technical_tab(data)

    with tabs[3]:
        _render_sector_tab(data)

    with tabs[4]:
        _render_corporate_tab(data)

    with tabs[5]:
        _render_sentiment_tab(data)


def _render_analysis_placeholder() -> None:
    st.markdown("""
    <div style="padding:40px;text-align:center;background:#f8f9fa;border-radius:12px;border:1px dashed #ccc;">
        <h3 style="color:#888">Enter a stock symbol above to start your analysis</h3>
        <p style="color:#aaa">The platform will run 6 AI agents in parallel and generate a full research report.</p>
    </div>
    """, unsafe_allow_html=True)


def _render_financial_tab(data: dict) -> None:
    # financial_output stored in the report agent's DB; we display from top-level fields
    # For richer display we'd re-fetch the individual agent outputs from /report/{id}
    req_id = data.get("request_id")
    if req_id:
        report_data = _get(f"/report/{req_id}")
        if report_data:
            # The full DB report doesn't include agent sub-fields in AnalysisResponse
            # So we extract what we stored in the markdown
            pass

    st.subheader("Financial Metrics")
    st.info(
        "Detailed financial metrics are embedded in the **Full Report** tab. "
        "Re-fetch the individual agent outputs via the API `/report/{id}` endpoint for raw data."
    )
    # Show what we have from top-level response
    if data.get("report_markdown"):
        # Extract financial section from markdown
        md = data["report_markdown"]
        start = md.find("## Financial Health")
        end   = md.find("\n## ", start + 1) if start > 0 else -1
        if start > 0:
            section = md[start:end] if end > 0 else md[start:start+2000]
            st.markdown(section)


def _render_technical_tab(data: dict) -> None:
    st.subheader("Technical Indicators")
    if data.get("report_markdown"):
        md    = data["report_markdown"]
        start = md.find("## Technical")
        end   = md.find("\n## ", start + 1) if start > 0 else -1
        if start > 0:
            section = md[start:end] if end > 0 else md[start:start+2000]
            st.markdown(section)
        else:
            st.info("Technical section not found in report.")


def _render_sector_tab(data: dict) -> None:
    st.subheader("Sector & Competitive Position")
    if data.get("report_markdown"):
        md    = data["report_markdown"]
        start = md.find("## Sector")
        end   = md.find("\n## ", start + 1) if start > 0 else -1
        if start > 0:
            section = md[start:end] if end > 0 else md[start:start+2000]
            st.markdown(section)
        else:
            st.info("Sector section not found in report.")


def _render_corporate_tab(data: dict) -> None:
    st.subheader("Corporate Actions & Events")
    if data.get("report_markdown"):
        md    = data["report_markdown"]
        start = md.find("## Corporate")
        end   = md.find("\n## ", start + 1) if start > 0 else -1
        if start > 0:
            section = md[start:end] if end > 0 else md[start:start+2000]
            st.markdown(section)
        else:
            st.info("Corporate actions section not found in report.")


def _render_sentiment_tab(data: dict) -> None:
    st.subheader("Market Sentiment")
    if data.get("report_markdown"):
        md    = data["report_markdown"]
        start = md.find("## Market Sentiment")
        end   = md.find("\n## ", start + 1) if start > 0 else -1
        if start > 0:
            section = md[start:end] if end > 0 else md[start:start+2000]
            st.markdown(section)
        else:
            st.info("Sentiment section not found in report.")


# ─────────────────────────────────────────────────────────────────────────────
# Page 2 — Stock Comparison
# ─────────────────────────────────────────────────────────────────────────────

def page_stock_comparison() -> None:
    render_header(
        "⚔️ Stock Comparison",
        "Compare two stocks head-to-head with a Gemini-powered analysis.",
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        s1 = st.text_input("Stock 1", placeholder="e.g. TCS").strip().upper()
    with col2:
        s2 = st.text_input("Stock 2", placeholder="e.g. INFY").strip().upper()
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        compare = st.button("Compare", type="primary", use_container_width=True)

    # Popular comparison pairs
    st.caption("Popular pairs:")
    pair_cols = st.columns(4)
    pairs = [("TCS", "INFY"), ("HDFCBANK", "ICICIBANK"), ("RELIANCE", "ONGC"), ("TATAMOTORS", "MARUTI")]
    for i, (p1, p2) in enumerate(pairs):
        if pair_cols[i].button(f"{p1} vs {p2}", key=f"pair_{i}"):
            s1, s2, compare = p1, p2, True

    if not compare:
        _render_comparison_placeholder()
        return

    if not s1 or not s2:
        st.warning("Please enter both stock symbols.")
        return

    if s1 == s2:
        st.error("Please enter two different stock symbols.")
        return

    with st.spinner(f"Comparing **{s1}** vs **{s2}** — running parallel analysis (~60–90 seconds)…"):
        data = _post("/compare", {"stock1": s1, "stock2": s2})

    if not data:
        return

    # ── Results header ────────────────────────────────────────────────────────
    st.markdown(f"### {s1} vs {s2} — Comparison")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**{s1} Recommendation**")
        recommendation_badge(data.get("recommendation_stock1"))
    with c2:
        st.markdown("<div style='text-align:center;font-size:2rem;padding-top:8px'>⚔️</div>",
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f"**{s2} Recommendation**")
        recommendation_badge(data.get("recommendation_stock2"))

    st.divider()

    # ── Comparison report ─────────────────────────────────────────────────────
    if data.get("comparison_report"):
        st.markdown(data["comparison_report"])
        st.divider()
        download_report_button(
            data["comparison_report"],
            f"{s1}_vs_{s2}_comparison.pdf",
        )


def _render_comparison_placeholder() -> None:
    st.markdown("""
    <div style="padding:40px;text-align:center;background:#f8f9fa;border-radius:12px;border:1px dashed #ccc;">
        <h3 style="color:#888">Select or enter two stocks to compare</h3>
        <p style="color:#aaa">Both stocks are analysed in parallel before generating the head-to-head report.</p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page 3 — Portfolio Analysis
# ─────────────────────────────────────────────────────────────────────────────

def page_portfolio_analysis() -> None:
    render_header(
        "💼 Portfolio Analysis",
        "Enter your holdings to get sector allocation, risk score, and diversification insights.",
    )

    st.markdown("#### Add Your Holdings")

    # ── Manual entry ──────────────────────────────────────────────────────────
    tickers_raw = st.text_area(
        "Enter stock symbols (one per line or comma-separated)",
        placeholder="TCS\nRELIANCE\nHDFCBANK\nINFY\nSUNPHARMA",
        height=140,
        label_visibility="visible",
    )

    # ── Pre-built sample portfolios ───────────────────────────────────────────
    st.caption("Or load a sample portfolio:")
    samp_cols = st.columns(3)
    samples = {
        "🖥️ Tech Heavy":    ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
        "🏦 BFSI Focused":  ["HDFCBANK", "ICICIBANK", "AXISBANK", "SBIN", "BAJFINANCE"],
        "🌈 Diversified":   ["TCS", "RELIANCE", "HDFCBANK", "SUNPHARMA", "ITC", "TATAMOTORS"],
    }
    for i, (label, tks) in enumerate(samples.items()):
        if samp_cols[i].button(label, key=f"sample_{i}"):
            tickers_raw = "\n".join(tks)

    analyse = st.button("Analyse Portfolio", type="primary")

    if not analyse:
        _render_portfolio_placeholder()
        return

    # ── Parse tickers ─────────────────────────────────────────────────────────
    raw = tickers_raw.replace(",", "\n").replace(";", "\n")
    tickers = [t.strip().upper() for t in raw.splitlines() if t.strip()]
    tickers = list(dict.fromkeys(tickers))   # deduplicate, preserve order

    if not tickers:
        st.warning("Please enter at least one stock symbol.")
        return
    if len(tickers) > 20:
        st.warning("Maximum 20 stocks per portfolio analysis.")
        tickers = tickers[:20]

    st.info(f"Analysing portfolio of **{len(tickers)} stocks**: {', '.join(tickers)}")

    with st.spinner("Running portfolio intelligence analysis…"):
        data = _post("/portfolio/analyze", {"stocks": tickers})

    if not data:
        return

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("### Portfolio Intelligence Report")

    # Top KPI row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stocks",                 len(data.get("stocks", [])))
    m2.metric("Diversification Score",  f"{data.get('diversification_score', 0):.0f} / 100")
    m3.metric("Risk Score",             f"{data.get('risk_score', 0):.0f} / 100")
    m4.metric("Concentration Risk",     data.get("concentration_risk", "—"))

    # Diversification bar
    st.markdown("**Diversification**")
    confidence_gauge(data.get("diversification_score"))

    # Risk bar
    st.markdown("**Risk**")
    risk = data.get("risk_score", 0)
    risk_colour = "#00C851" if risk < 35 else "#FF8800" if risk < 55 else "#FF4444"
    st.markdown(
        f"""<div style="background:#e0e0e0;border-radius:8px;height:14px;width:100%;">
          <div style="background:{risk_colour};width:{risk}%;height:14px;border-radius:8px;"></div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Two-column layout: chart + suggestions
    col_chart, col_sugg = st.columns([1, 1])

    with col_chart:
        sector_allocation_chart(data.get("sector_allocation", {}))

    with col_sugg:
        st.markdown("#### 💡 Recommendations")
        suggestions = data.get("suggestions", [])
        if suggestions:
            for s in suggestions:
                st.markdown(f"- {s}")
        else:
            st.success("Portfolio looks well balanced!")

        if data.get("detailed_report"):
            st.divider()
            st.markdown(f"**Overall:** {data['detailed_report']}")

    # Sector breakdown table
    st.markdown("#### Sector Breakdown")
    if data.get("sector_allocation"):
        import pandas as pd
        sec_df = pd.DataFrame([
            {"Sector": k, "Weight %": f"{v:.1f}%"}
            for k, v in sorted(data["sector_allocation"].items(), key=lambda x: -x[1])
        ])
        st.dataframe(sec_df, use_container_width=True, hide_index=True)


def _render_portfolio_placeholder() -> None:
    st.markdown("""
    <div style="padding:40px;text-align:center;background:#f8f9fa;border-radius:12px;border:1px dashed #ccc;">
        <h3 style="color:#888">Enter your portfolio holdings above</h3>
        <p style="color:#aaa">You'll get sector allocation, risk score, diversification analysis, and actionable suggestions.</p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page 4 — Market Brief
# ─────────────────────────────────────────────────────────────────────────────

def page_market_brief() -> None:
    render_header(
        "🇮🇳 Market Brief",
        "Daily AI-generated Indian market summary — NIFTY 50, SENSEX, top movers, and sector highlights.",
    )

    col_btn, col_note = st.columns([1, 3])
    with col_btn:
        fetch = st.button("🔄 Fetch Today's Brief", type="primary")
    with col_note:
        st.caption("Cached once per day — subsequent requests return instantly.")

    if not fetch:
        _render_brief_placeholder()
        return

    with st.spinner("Fetching market data and generating today's brief…"):
        data = _get("/market-brief")

    if not data:
        return

    # ── Index metrics ─────────────────────────────────────────────────────────
    st.markdown(f"### Market Brief — {data.get('date', 'Today')}")

    c1, c2 = st.columns(2)
    nifty_chg  = data.get("nifty_change_pct")
    sensex_chg = data.get("sensex_change_pct")

    c1.metric(
        "NIFTY 50",
        "—" if nifty_chg is None else f"{nifty_chg:+.2f}%",
        delta=f"{nifty_chg:+.2f}%" if nifty_chg else None,
    )
    c2.metric(
        "SENSEX",
        "—" if sensex_chg is None else f"{sensex_chg:+.2f}%",
        delta=f"{sensex_chg:+.2f}%" if sensex_chg else None,
    )

    # ── Top movers ────────────────────────────────────────────────────────────
    gainers = data.get("top_gainers", [])
    losers  = data.get("top_losers",  [])

    if gainers or losers:
        gc, lc = st.columns(2)
        with gc:
            st.markdown("#### 🟢 Top Gainers")
            for g in gainers:
                st.markdown(
                    f"**{g.get('symbol')}** — "
                    f"<span style='color:#00C851'>+{g.get('change_pct', 0):.2f}%</span> "
                    f"(₹{g.get('close', 0):,.1f})",
                    unsafe_allow_html=True,
                )
        with lc:
            st.markdown("#### 🔴 Top Losers")
            for l in losers:
                st.markdown(
                    f"**{l.get('symbol')}** — "
                    f"<span style='color:#FF4444'>{l.get('change_pct', 0):.2f}%</span> "
                    f"(₹{l.get('close', 0):,.1f})",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Full Gemini report ────────────────────────────────────────────────────
    if data.get("report_markdown"):
        st.markdown(data["report_markdown"])
        st.divider()
        download_report_button(
            data["report_markdown"],
            f"market_brief_{data.get('date', 'today')}.pdf",
        )


def _render_brief_placeholder() -> None:
    st.markdown("""
    <div style="padding:40px;text-align:center;background:#f8f9fa;border-radius:12px;border:1px dashed #ccc;">
        <h3 style="color:#888">Click "Fetch Today's Brief" to load the market summary</h3>
        <p style="color:#aaa">Covers NIFTY 50, SENSEX, sector performance, top gainers & losers.</p>
    </div>
    """, unsafe_allow_html=True)