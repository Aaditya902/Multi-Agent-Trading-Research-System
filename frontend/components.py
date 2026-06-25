"""
Reusable Streamlit UI components.
All visual building blocks live here — pages import from this module.
"""

from __future__ import annotations
import streamlit as st

# ── Colour palette ─────────────────────────────────────────────────────────────
_REC_COLOURS = {
    "Strong Buy":  "#00C851",
    "Buy":         "#7CB342",
    "Hold":        "#FF8800",
    "Sell":        "#FF4444",
    "Strong Sell": "#CC0000",
}
_SENTIMENT_COLOURS = {
    "Bullish": "#00C851",
    "Neutral": "#FF8800",
    "Bearish": "#FF4444",
}
_TREND_COLOURS = {
    "Uptrend":   "#00C851",
    "Sideways":  "#FF8800",
    "Downtrend": "#FF4444",
}


def _sanitise_for_pdf(text: str) -> str:
    """Replace non-latin-1 characters so Helvetica can render them."""
    replacements = {
        "\u2014": "-",    # em dash
        "\u2013": "-",    # en dash
        "\u2019": "'",    # right single quote
        "\u2018": "'",    # left single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2022": "*",    # bullet
        "\u20b9": "Rs.",  # Indian rupee sign
        "\u00a0": " ",    # non-breaking space
        "\u2026": "...",  # ellipsis
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def render_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()


def recommendation_badge(recommendation: str | None) -> None:
    if not recommendation:
        st.info("No recommendation available.")
        return
    colour = _REC_COLOURS.get(recommendation, "#888888")
    st.markdown(
        f"""<div style="display:inline-block;background:{colour};color:white;
        padding:8px 20px;border-radius:20px;font-size:1.1rem;font-weight:700;
        letter-spacing:0.5px;">{recommendation}</div>""",
        unsafe_allow_html=True,
    )


def confidence_gauge(score: float | None) -> None:
    if score is None:
        return
    colour = "#00C851" if score >= 80 else "#FF8800" if score >= 60 else "#FF4444"
    label  = "High Conviction" if score >= 80 else "Moderate Conviction" if score >= 60 else "Low Conviction"
    st.markdown(f"**Confidence: {score:.0f}% — {label}**")
    st.markdown(
        f"""<div style="background:#e0e0e0;border-radius:8px;height:14px;width:100%;">
          <div style="background:{colour};width:{score}%;height:14px;border-radius:8px;"></div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")


def metric_card(label: str, value: str, delta: str = "", help: str = "") -> None:
    st.metric(label=label, value=value, delta=delta or None, help=help or None)


def sentiment_badge(sentiment: str | None, score: float | None = None) -> None:
    if not sentiment:
        return
    colour    = _SENTIMENT_COLOURS.get(sentiment, "#888888")
    score_txt = f" ({score:+.2f})" if score is not None else ""
    st.markdown(
        f"""<span style="background:{colour};color:white;padding:4px 12px;
        border-radius:12px;font-weight:600;">{sentiment}{score_txt}</span>""",
        unsafe_allow_html=True,
    )
    st.markdown("")


def trend_badge(trend: str | None) -> None:
    if not trend:
        return
    colour = _TREND_COLOURS.get(trend, "#888888")
    arrow  = "Up" if trend == "Uptrend" else "Down" if trend == "Downtrend" else "Side"
    st.markdown(
        f"""<span style="background:{colour};color:white;padding:4px 12px;
        border-radius:12px;font-weight:600;">{arrow} {trend}</span>""",
        unsafe_allow_html=True,
    )
    st.markdown("")


def error_banner(errors: dict) -> None:
    if not errors:
        return
    agent_list = ", ".join(errors.keys())
    st.warning(
        f"Partial results — the following agents encountered errors: "
        f"`{agent_list}`. The report was generated from available data.",
        icon="warning",
    )


def financial_metrics_table(metrics: dict) -> None:
    if not metrics:
        st.info("Financial data unavailable.")
        return

    def fmt(val, prefix="", suffix="", scale=1, decimals=2):
        if val is None:
            return "N/A"
        try:
            return f"{prefix}{float(val)*scale:,.{decimals}f}{suffix}"
        except Exception:
            return str(val)

    def fmt_cr(val):
        if val is None:
            return "N/A"
        try:
            cr = float(val) / 1e7
            if cr >= 1_00_000:
                return f"Rs.{cr/1e5:,.1f}L Cr"
            return f"Rs.{cr:,.0f} Cr"
        except Exception:
            return "N/A"

    rows = [
        ("Current Price",  fmt(metrics.get("current_price"),       "Rs.", "", 1, 2)),
        ("Market Cap",     fmt_cr(metrics.get("market_cap"))),
        ("P/E Ratio",      fmt(metrics.get("pe_ratio"),            "",  "x")),
        ("EPS",            fmt(metrics.get("eps"),                 "Rs.")),
        ("ROE",            fmt(metrics.get("roe"),                 "",  "%", 100)),
        ("Revenue Growth", fmt(metrics.get("revenue_growth"),      "",  "%", 100)),
        ("Profit Margin",  fmt(metrics.get("profit_margin"),       "",  "%", 100)),
        ("Debt / Equity",  fmt(metrics.get("debt_to_equity"),      "",  "x")),
        ("Free Cash Flow", fmt_cr(metrics.get("free_cash_flow"))),
        ("Dividend Yield", fmt(metrics.get("dividend_yield"),      "",  "%", 100)),
        ("52W High",       fmt(metrics.get("fifty_two_week_high"), "Rs.")),
        ("52W Low",        fmt(metrics.get("fifty_two_week_low"),  "Rs.")),
        ("Beta",           fmt(metrics.get("beta"))),
    ]
    col1, col2 = st.columns(2)
    for i, (label, value) in enumerate(rows):
        (col1 if i % 2 == 0 else col2).metric(label, value)


def technical_indicators_grid(tech: dict) -> None:
    if not tech:
        st.info("Technical data unavailable.")
        return
    c1, c2, c3 = st.columns(3)
    rsi = tech.get("rsi")
    rsi_str   = f"{rsi:.1f}" if rsi else "N/A"
    rsi_delta = "Overbought" if rsi and rsi > 70 else "Oversold" if rsi and rsi < 30 else "Neutral"
    c1.metric("RSI (14)", rsi_str, rsi_delta)
    c2.metric("MACD Signal", tech.get("macd_signal", "N/A"))
    c3.metric("MA Signal",   tech.get("moving_average_signal", "N/A"))
    c1.metric("SMA 50",  f"Rs.{tech['sma_50']:,.1f}"  if tech.get("sma_50")  else "N/A")
    c2.metric("SMA 200", f"Rs.{tech['sma_200']:,.1f}" if tech.get("sma_200") else "N/A")
    c3.metric("BB Signal", tech.get("bollinger_signal", "N/A"))
    c1.metric("EMA 20", f"Rs.{tech['ema_20']:,.1f}" if tech.get("ema_20") else "N/A")
    c2.metric("EMA 50", f"Rs.{tech['ema_50']:,.1f}" if tech.get("ema_50") else "N/A")
    c3.metric("Trend",  tech.get("trend", "N/A"))


def sector_peer_table(peers: list[dict]) -> None:
    if not peers:
        st.info("No peer data available.")
        return
    import pandas as pd
    rows = []
    for p in peers:
        rows.append({
            "Ticker":        p.get("ticker", ""),
            "Company":       p.get("name",   ""),
            "P/E":           f"{p['pe_ratio']:.1f}x"          if p.get("pe_ratio")       else "N/A",
            "Rev Growth":    f"{p['revenue_growth']*100:.1f}%" if p.get("revenue_growth") else "N/A",
            "ROE":           f"{p['roe']*100:.1f}%"            if p.get("roe")            else "N/A",
            "Profit Margin": f"{p['profit_margin']*100:.1f}%"  if p.get("profit_margin")  else "N/A",
            "vs Target":     p.get("vs_target", ""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def corporate_actions_list(actions: list[dict]) -> None:
    if not actions:
        st.info("No recent corporate actions found.")
        return
    impact_icon = {"Positive": "Green", "Negative": "Red", "Neutral": "Yellow"}
    for action in actions:
        atype = action.get("action_type", "Event")
        date  = action.get("date") or "N/A"
        imp   = action.get("impact", "Neutral")
        with st.expander(f"[{imp}] {atype} - {date}"):
            st.write(action.get("details", ""))
            st.caption(f"Impact: **{imp}**")


def sector_allocation_chart(sector_allocation: dict) -> None:
    if not sector_allocation:
        return
    try:
        import plotly.express as px
        fig = px.pie(
            names=list(sector_allocation.keys()),
            values=list(sector_allocation.values()),
            title="Sector Allocation",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_layout(margin=dict(t=40,b=0,l=0,r=0), showlegend=True, height=350)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Chart unavailable: {e}")


def download_report_button(report_markdown: str, filename: str = "report.pdf") -> None:
    """Convert Markdown to PDF and render a download button. Falls back to .md."""
    if not report_markdown:
        return
    try:
        from fpdf import FPDF

        class _PDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 10)
                self.cell(0, 8, "Indian Stock Research Platform",
                          align="C", new_x="LMARGIN", new_y="NEXT")
                self.ln(2)
            def footer(self):
                self.set_y(-12)
                self.set_font("Helvetica", "I", 8)
                self.cell(0, 8, f"Page {self.page_no()}", align="C")

        pdf = _PDF()
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Helvetica", size=10)

        for line in report_markdown.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                pdf.set_font("Helvetica", "B", 14)
                pdf.multi_cell(0, 8, _sanitise_for_pdf(line[2:]))
                pdf.set_font("Helvetica", size=10)
            elif line.startswith("## "):
                pdf.set_font("Helvetica", "B", 12)
                pdf.multi_cell(0, 7, _sanitise_for_pdf(line[3:]))
                pdf.set_font("Helvetica", size=10)
            elif line.startswith("### "):
                pdf.set_font("Helvetica", "B", 11)
                pdf.multi_cell(0, 6, _sanitise_for_pdf(line[4:]))
                pdf.set_font("Helvetica", size=10)
            elif line.startswith("- ") or line.startswith("* "):
                pdf.multi_cell(0, 6, _sanitise_for_pdf(f"  * {line[2:]}"))
            elif line.startswith("**") and line.endswith("**"):
                pdf.set_font("Helvetica", "B", 10)
                pdf.multi_cell(0, 6, _sanitise_for_pdf(line.replace("**", "")))
                pdf.set_font("Helvetica", size=10)
            elif line == "---":
                pdf.ln(2)
                pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
                pdf.ln(2)
            elif line:
                clean = line.replace("**", "").replace("*", "").replace("`", "")
                pdf.multi_cell(0, 6, _sanitise_for_pdf(clean))
            else:
                pdf.ln(3)

        pdf_bytes = bytes(pdf.output())
        st.download_button(
            label="Download Report (PDF)",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
        )
    except Exception:
        st.download_button(
            label="Download Report (.md)",
            data=report_markdown.encode("utf-8"),
            file_name=filename.replace(".pdf", ".md"),
            mime="text/markdown",
        )