"""
Report Agent
The final agent in the pipeline — aggregates all 6 agent outputs
and generates an institutional-quality investment research report via Gemini.
"""

from __future__ import annotations
import os
import re
from datetime import datetime, timezone

from google import genai
from dotenv import load_dotenv

load_dotenv()

from logging_config import logger
from schemas.analysis_schemas import (
    NewsOutput, FinancialOutput, SentimentOutput,
    TechnicalOutput, SectorOutput, CorporateOutput,
    ReportOutput,
)
from prompts.report_prompt import build_report_prompt, build_comparison_prompt
from services.ticker_resolver import resolve_ticker, get_company_name

_CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Valid recommendation values
_VALID_RECOMMENDATIONS = {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"}


def run_report_agent(
    ticker: str,
    news: NewsOutput | None = None,
    financial: FinancialOutput | None = None,
    sentiment: SentimentOutput | None = None,
    technical: TechnicalOutput | None = None,
    sector: SectorOutput | None = None,
    corporate: CorporateOutput | None = None,
) -> ReportOutput:
    """
    Main entry point for the Report Agent.

    Accepts the outputs of all 6 specialist agents, builds a unified
    Gemini prompt, and returns a full Markdown research report.

    Args:
        ticker:    Raw user ticker
        news:      Output from NewsAgent
        financial: Output from FinancialAgent
        sentiment: Output from SentimentAgent
        technical: Output from TechnicalAgent
        sector:    Output from SectorAgent
        corporate: Output from CorporateAgent

    Returns:
        ReportOutput — with full report_markdown, recommendation, and confidence_score
    """
    yf_ticker    = resolve_ticker(ticker)
    company_name = get_company_name(yf_ticker)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    logger.info(f"[ReportAgent] Generating report for {company_name} ({yf_ticker})")

    # ── Build the Gemini prompt ───────────────────────────────────────────────
    prompt = build_report_prompt(
        ticker=yf_ticker,
        company_name=company_name,
        news=news,
        financial=financial,
        sentiment=sentiment,
        technical=technical,
        sector=sector,
        corporate=corporate,
    )

    # ── Call Gemini ───────────────────────────────────────────────────────────
    try:
        response = _CLIENT.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )
        report_markdown = response.text.strip()
        logger.info(f"[ReportAgent] Gemini returned {len(report_markdown)} chars for {yf_ticker}")

    except Exception as e:
        logger.error(f"[ReportAgent] Gemini call failed for {yf_ticker}: {e}")
        report_markdown = _build_fallback_report(
            ticker, company_name, news, financial, sentiment, technical, sector, corporate, generated_at
        )

    # ── Extract structured fields from the markdown ───────────────────────────
    recommendation  = _extract_recommendation(report_markdown)
    confidence      = _extract_confidence(report_markdown)
    exec_summary    = _extract_executive_summary(report_markdown)

    output = ReportOutput(
        stock=ticker.upper(),
        ticker=yf_ticker,
        report_markdown=report_markdown,
        recommendation=recommendation,
        confidence_score=confidence,
        executive_summary=exec_summary,
        generated_at=generated_at,
    )

    logger.info(
        f"[ReportAgent] Done for {yf_ticker} — "
        f"recommendation={recommendation}, confidence={confidence:.0f}%"
    )
    return output


def run_comparison_report(
    ticker1: str, report_markdown1: str,
    ticker2: str, report_markdown2: str,
) -> str:
    """
    Generate a side-by-side comparison report for two stocks.

    Args:
        ticker1, ticker2: Raw user tickers
        report_markdown1, report_markdown2: Individual stock reports

    Returns:
        Comparison report as Markdown string
    """
    yf1  = resolve_ticker(ticker1)
    yf2  = resolve_ticker(ticker2)
    name1 = get_company_name(yf1)
    name2 = get_company_name(yf2)

    logger.info(f"[ReportAgent] Generating comparison: {ticker1} vs {ticker2}")

    prompt = build_comparison_prompt(yf1, name1, report_markdown1, yf2, name2, report_markdown2)

    try:
        response = _CLIENT.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"[ReportAgent] Comparison Gemini call failed: {e}")
        return _build_simple_comparison(ticker1, name1, ticker2, name2)


# ── Extraction helpers ─────────────────────────────────────────────────────────

def _extract_recommendation(markdown: str) -> str:
    """
    Parse the recommendation line from the generated Markdown.
    Tries multiple patterns in order of specificity.
    """
    patterns = [
        r"\*\*Recommendation:\*\*\s*(Strong Buy|Strong Sell|Buy|Sell|Hold)",
        r"Recommendation[:\s]+\**(Strong Buy|Strong Sell|Buy|Sell|Hold)\**",
        r"\b(Strong Buy|Strong Sell|Buy|Sell|Hold)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            raw = match.group(1).strip().title()
            # Normalise casing
            for valid in _VALID_RECOMMENDATIONS:
                if raw.lower() == valid.lower():
                    return valid
    return "Hold"   # default if not found


def _extract_confidence(markdown: str) -> float:
    """Parse the confidence score percentage from the Markdown."""
    patterns = [
        r"\*\*Confidence Score:\*\*\s*(\d+(?:\.\d+)?)\s*%",
        r"Confidence Score[:\s]+(\d+(?:\.\d+)?)\s*%",
        r"Confidence[:\s]+(\d+(?:\.\d+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            return max(0.0, min(100.0, val))
    return 65.0   # default mid-confidence if not found


def _extract_executive_summary(markdown: str) -> str:
    """
    Extract the Executive Summary section from the Markdown.
    Returns first meaningful paragraph under that heading.
    """
    pattern = r"##\s*Executive Summary\s*\n(.*?)(?=\n##|\Z)"
    match   = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
        # Return first non-empty 2 sentences
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        return ". ".join(sentences[:2]) + "." if sentences else text[:300]
    return ""


# ── Fallback report builder ────────────────────────────────────────────────────

def _build_fallback_report(
    ticker: str,
    company_name: str,
    news: NewsOutput | None,
    financial: FinancialOutput | None,
    sentiment: SentimentOutput | None,
    technical: TechnicalOutput | None,
    sector: SectorOutput | None,
    corporate: CorporateOutput | None,
    generated_at: str,
) -> str:
    """
    Structured Markdown report built entirely from agent data,
    used when Gemini is unavailable. No AI text — pure data assembly.
    """
    sections: list[str] = []
    sections.append(f"# {company_name} ({ticker.upper()}) — Equity Research Report\n")
    sections.append(f"*Generated: {generated_at} | Source: Multi-Agent Analysis (Offline Mode)*\n")

    # Executive Summary
    rec  = _rule_based_recommendation(financial, sentiment, technical)
    conf = _rule_based_confidence(financial, sentiment, technical)
    sections.append(f"## Executive Summary\n")
    parts = []
    if financial:
        parts.append(f"Financial health is **{financial.financial_health}** with **{financial.valuation}** valuation.")
    if sentiment:
        parts.append(f"Market sentiment is **{sentiment.sentiment}** (score: {sentiment.score:+.2f}).")
    if technical:
        parts.append(f"Price action shows a **{technical.trend}** with {technical.macd_signal} MACD signal.")
    sections.append(" ".join(parts) + f" Rule-based recommendation: **{rec}**.\n")

    # News
    if news:
        sections.append(f"## News & Catalysts Analysis\n")
        sections.append(f"{news.news_summary}\n")
        if news.bullish_news:
            sections.append("**Bullish Catalysts:**\n" + "\n".join(f"- {b}" for b in news.bullish_news) + "\n")
        if news.bearish_news:
            sections.append("**Bearish Catalysts:**\n" + "\n".join(f"- {b}" for b in news.bearish_news) + "\n")

    # Financial
    if financial:
        sections.append(f"## Financial Health Assessment\n")
        sections.append(f"**Health:** {financial.financial_health} | **Valuation:** {financial.valuation}\n")
        m = financial.metrics
        if m.current_price:
            sections.append(f"**Price:** ₹{m.current_price:,.2f} | **P/E:** {m.pe_ratio} | **ROE:** {m.roe}\n")
        if financial.strengths:
            sections.append("**Strengths:**\n" + "\n".join(f"- {s}" for s in financial.strengths) + "\n")
        if financial.risks:
            sections.append("**Risks:**\n" + "\n".join(f"- {r}" for r in financial.risks) + "\n")

    # Sentiment
    if sentiment:
        sections.append(f"## Market Sentiment\n")
        sections.append(
            f"FinBERT sentiment: **{sentiment.sentiment}** (score: {sentiment.score:+.3f}). "
            f"{sentiment.explanation}\n"
        )

    # Technical
    if technical:
        sections.append(f"## Technical Analysis\n")
        sections.append(
            f"**Trend:** {technical.trend} | **RSI:** {technical.rsi} | "
            f"**MACD:** {technical.macd_signal} | **MA Signal:** {technical.moving_average_signal}\n"
        )
        sections.append(f"{technical.technical_summary}\n")

    # Sector
    if sector:
        sections.append(f"## Sector & Competitive Position\n")
        sections.append(
            f"**Sector:** {sector.sector} | **Position:** {sector.relative_position} | "
            f"**Sector Strength:** {sector.sector_strength}\n"
        )

    # Corporate
    if corporate:
        sections.append(f"## Corporate Actions\n")
        sections.append(f"{corporate.summary}\n")
        for a in corporate.corporate_actions[:5]:
            sections.append(f"- **{a.action_type}** ({a.date or 'N/A'}): {a.details}\n")

    # Final Recommendation
    sections.append(f"## Final Recommendation\n")
    sections.append(f"**Recommendation:** {rec}  ")
    sections.append(f"**Confidence Score:** {conf:.0f}%  ")
    sections.append(f"**Target Horizon:** 6-12 months\n")
    sections.append(
        "_Note: This report was generated in offline mode (Gemini unavailable). "
        "Recommendations are rule-based and should be used for reference only._\n"
    )
    sections.append("\n---\n*Multi-Agent Indian Stock Research Platform. Not financial advice.*")

    return "\n".join(sections)


def _rule_based_recommendation(
    financial: FinancialOutput | None,
    sentiment: SentimentOutput | None,
    technical: TechnicalOutput | None,
) -> str:
    """Simplified rule-based recommendation when Gemini is offline."""
    score = 0

    if financial:
        if financial.financial_health == "Strong":
            score += 2
        elif financial.financial_health == "Weak":
            score -= 2
        if financial.valuation == "Undervalued":
            score += 1
        elif financial.valuation == "Overvalued":
            score -= 1

    if sentiment:
        if sentiment.sentiment == "Bullish":
            score += 1
        elif sentiment.sentiment == "Bearish":
            score -= 1

    if technical:
        if technical.trend == "Uptrend":
            score += 1
        elif technical.trend == "Downtrend":
            score -= 1
        if technical.macd_signal == "Bullish":
            score += 1
        elif technical.macd_signal == "Bearish":
            score -= 1

    if score >= 4:
        return "Strong Buy"
    elif score >= 2:
        return "Buy"
    elif score <= -4:
        return "Strong Sell"
    elif score <= -2:
        return "Sell"
    return "Hold"


def _rule_based_confidence(
    financial: FinancialOutput | None,
    sentiment: SentimentOutput | None,
    technical: TechnicalOutput | None,
) -> float:
    """Estimate confidence based on data completeness."""
    data_points = sum([
        financial is not None,
        sentiment is not None,
        technical is not None,
    ])
    base = 40.0 + (data_points * 10.0)

    if sentiment and abs(sentiment.score) > 0.3:
        base += 5.0
    if technical and technical.trend != "Sideways":
        base += 5.0

    return min(75.0, base)   # Cap offline confidence at 75%


def _build_simple_comparison(
    ticker1: str, name1: str,
    ticker2: str, name2: str,
) -> str:
    return (
        f"# {name1} vs {name2} — Comparison\n\n"
        f"Comparison report generation failed (Gemini unavailable).\n"
        f"Please review individual reports for {ticker1} and {ticker2} separately.\n\n"
        f"---\n*Multi-Agent Indian Stock Research Platform*"
    )