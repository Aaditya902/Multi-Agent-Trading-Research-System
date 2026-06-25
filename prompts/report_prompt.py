"""
Gemini prompt template for the Report Agent.
Generates a full institutional-quality investment research report in Markdown.
"""

from __future__ import annotations
from schemas.analysis_schemas import (
    NewsOutput, FinancialOutput, SentimentOutput,
    TechnicalOutput, SectorOutput, CorporateOutput,
)


def build_report_prompt(
    ticker: str,
    company_name: str,
    news: NewsOutput | None,
    financial: FinancialOutput | None,
    sentiment: SentimentOutput | None,
    technical: TechnicalOutput | None,
    sector: SectorOutput | None,
    corporate: CorporateOutput | None,
) -> str:
    """Build the full prompt string for Gemini to generate the research report."""

    sections = []

    # ── News ──────────────────────────────────────────────────────────────────
    if news:
        bullish = "\n".join(f"  - {b}" for b in news.bullish_news) or "  - None identified"
        bearish = "\n".join(f"  - {b}" for b in news.bearish_news) or "  - None identified"
        sections.append(f"""
NEWS ANALYSIS DATA:
  Summary: {news.news_summary}
  Overall Impact: {news.overall_news_impact}
  Bullish Catalysts:
{bullish}
  Bearish Catalysts:
{bearish}
""")

    # ── Financial ─────────────────────────────────────────────────────────────
    if financial:
        m = financial.metrics
        strengths = "\n".join(f"  - {s}" for s in financial.strengths) or "  - None"
        risks = "\n".join(f"  - {r}" for r in financial.risks) or "  - None"
        price_str = f"Rs.{m.current_price:,.2f}" if m.current_price else "N/A"
        mktcap_str = f"Rs.{m.market_cap:,.0f}" if m.market_cap else "N/A"
        sections.append(f"""
FINANCIAL DATA:
  Health: {financial.financial_health}
  Valuation: {financial.valuation}
  Current Price: {price_str}
  Market Cap: {mktcap_str}
  P/E Ratio: {m.pe_ratio}
  EPS: {m.eps}
  ROE: {m.roe}
  Revenue Growth: {m.revenue_growth}
  Profit Margin: {m.profit_margin}
  Debt/Equity: {m.debt_to_equity}
  Free Cash Flow: {m.free_cash_flow}
  52W High: {m.fifty_two_week_high} | 52W Low: {m.fifty_two_week_low}
  Beta: {m.beta}
  Strengths:
{strengths}
  Key Risks:
{risks}
""")

    # ── Sentiment ─────────────────────────────────────────────────────────────
    if sentiment:
        sections.append(f"""
SENTIMENT DATA:
  Overall: {sentiment.sentiment} (Score: {sentiment.score:+.3f})
  Positive: {sentiment.positive_score:.2%} | Negative: {sentiment.negative_score:.2%} | Neutral: {sentiment.neutral_score:.2%}
  Explanation: {sentiment.explanation}
""")

    # ── Technical ─────────────────────────────────────────────────────────────
    if technical:
        sections.append(f"""
TECHNICAL DATA:
  Trend: {technical.trend}
  RSI: {technical.rsi}
  MACD Signal: {technical.macd_signal}
  Moving Average Signal: {technical.moving_average_signal}
  Bollinger Signal: {technical.bollinger_signal}
  SMA 50: {technical.sma_50} | SMA 200: {technical.sma_200}
  EMA 20: {technical.ema_20} | EMA 50: {technical.ema_50}
  Technical Summary: {technical.technical_summary}
""")

    # ── Sector ────────────────────────────────────────────────────────────────
    if sector:
        sections.append(f"""
SECTOR DATA:
  Sector: {sector.sector}
  Position vs Peers: {sector.relative_position}
  Sector Strength: {sector.sector_strength}
  Sector Avg P/E: {sector.sector_pe_avg}
  Sector Avg Growth: {sector.sector_growth_avg}
""")

    # ── Corporate Actions ─────────────────────────────────────────────────────
    if corporate:
        actions_str = "\n".join(
            f"  - [{a.action_type}] {a.details} (Impact: {a.impact})"
            for a in corporate.corporate_actions
        ) or "  - No recent corporate actions"
        sections.append(f"""
CORPORATE ACTIONS:
{actions_str}
  Overall Impact: {corporate.impact}
  Summary: {corporate.summary}
""")

    agent_data = "\n".join(sections) or "No agent data available."

    return f"""You are an elite institutional equity research analyst specialising in Indian capital markets (NSE/BSE).

Generate a comprehensive, professional investment research report for:
  Company: {company_name}
  Ticker: {ticker}

Use the following data gathered by specialised AI agents:

{agent_data}

Generate a detailed research report in EXACTLY this Markdown structure:

# {company_name} ({ticker}) — Equity Research Report

## Executive Summary
[2-3 sentence high-level summary. State recommendation clearly.]

## News & Catalysts Analysis
[Discuss recent news, bullish/bearish catalysts, media sentiment.]

## Financial Health Assessment
[Analyse fundamentals: revenue, margins, ROE, valuation vs sector.]

## Market Sentiment
[FinBERT sentiment results and what they imply for near-term price action.]

## Technical Analysis
[Trend, momentum, RSI, MACD, MA signals, support/resistance levels if inferable.]

## Sector & Competitive Position
[Industry context, peer comparison, market share, moat assessment.]

## Corporate Actions & Events
[Dividends, buybacks, splits, promoter activity, upcoming earnings.]

## Investment Opportunities
[3-5 specific reasons to invest. Be concrete.]

## Key Risks
[3-5 specific risks. Be concrete. Include sector, macro, and company-specific risks.]

## Investment Outlook (6-12 months)
[Forward-looking view on earnings, price action, catalysts to watch.]

## Final Recommendation

**Recommendation:** [Choose ONE: Strong Buy | Buy | Hold | Sell | Strong Sell]
**Confidence Score:** [0-100]%
**Target Horizon:** 6-12 months

[2-3 sentences justifying the recommendation with price catalysts.]

---
*Report generated by Multi-Agent Indian Stock Research Platform. For informational purposes only. Not financial advice.*

IMPORTANT RULES:
- Use ₹ (Indian Rupee) for all price references
- Reference Crore and Lakh for large INR amounts (e.g. ₹1,500 Cr)
- Be specific — avoid generic filler statements
- If data is missing, acknowledge it professionally
- Confidence Score: 85-100 = high conviction, 70-84 = moderate, 50-69 = low conviction
- Return ONLY the Markdown report, no preamble or meta-commentary
"""


def build_comparison_prompt(
    ticker1: str, name1: str, report1: str,
    ticker2: str, name2: str, report2: str,
) -> str:
    """Prompt to generate a side-by-side comparison report."""
    return f"""You are an expert Indian equity analyst.

Compare these two stocks and generate a head-to-head investment comparison report.

STOCK 1: {name1} ({ticker1})
{report1[:3000]}

STOCK 2: {name2} ({ticker2})
{report2[:3000]}

Generate a comparison report in this Markdown format:

# {name1} vs {name2} — Comparative Analysis

## Head-to-Head Overview
[Summary table: key metrics side by side]

## Financial Comparison
[Revenue, margins, P/E, ROE, growth rates]

## Technical Comparison
[Trend, momentum, relative strength]

## Risk Comparison
[Which stock carries more risk and why]

## Sector Position
[How each ranks within the sector]

## Investment Verdict

| Metric | {ticker1} | {ticker2} |
|--------|-----------|-----------|
| Recommendation | ? | ? |
| Confidence | ?% | ?% |
| Best For | ? | ? |

**Winner for Growth Investors:** [ticker]
**Winner for Value Investors:** [ticker]
**Overall Preferred Pick:** [ticker] — [brief reason]

---
*Comparative analysis by Multi-Agent Indian Stock Research Platform.*

Return ONLY the Markdown report.
"""