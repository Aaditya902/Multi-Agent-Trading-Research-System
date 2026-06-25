"""
Financial Agent
Fetches company fundamentals via yfinance and evaluates
financial health, valuation, strengths, and risks.
"""

from __future__ import annotations

from logging_config import logger
from schemas.analysis_schemas import FinancialOutput, FinancialMetrics
from tools.yfinance_tool import fetch_stock_info, extract_financial_metrics
from services.ticker_resolver import resolve_ticker, get_company_name


# ── Valuation thresholds (Indian market context) ──────────────────────────────
_SECTOR_PE_BENCHMARKS: dict[str, float] = {
    "Information Technology": 28.0,
    "Financial Services":     20.0,
    "Energy":                 15.0,
    "Consumer Staples":       45.0,
    "Consumer Discretionary": 40.0,
    "Healthcare":             30.0,
    "Basic Materials":        12.0,
    "Industrials":            25.0,
    "Utilities":              18.0,
    "Communication Services": 22.0,
    "Real Estate":            35.0,
}
_DEFAULT_PE_BENCHMARK = 25.0


def run_financial_agent(ticker: str) -> FinancialOutput:
    """
    Main entry point for the Financial Agent.

    Steps:
      1. Resolve ticker
      2. Fetch yfinance info
      3. Extract typed FinancialMetrics
      4. Evaluate health / valuation / strengths / risks

    Args:
        ticker: Raw user-supplied ticker e.g. "HDFCBANK"

    Returns:
        FinancialOutput — fully populated
    """
    yf_ticker    = resolve_ticker(ticker)
    company_name = get_company_name(yf_ticker)

    logger.info(f"[FinancialAgent] Starting for {company_name} ({yf_ticker})")

    # ── Step 1: Fetch raw data ────────────────────────────────────────────────
    info    = fetch_stock_info(yf_ticker)
    metrics = extract_financial_metrics(info)
    sector  = info.get("sector", "Unknown")

    if not info:
        logger.warning(f"[FinancialAgent] Empty info for {yf_ticker}")
        return FinancialOutput(
            stock=ticker.upper(),
            financial_health="Unknown",
            strengths=["Insufficient data to assess financial health."],
            risks=["Data unavailable — manual research recommended."],
            valuation="Unknown",
            metrics=FinancialMetrics(),
        )

    # ── Step 2: Health assessment ─────────────────────────────────────────────
    health  = _assess_health(metrics)
    val     = _assess_valuation(metrics, sector)
    strengths = _identify_strengths(metrics, info)
    risks     = _identify_risks(metrics, info)

    output = FinancialOutput(
        stock=ticker.upper(),
        financial_health=health,
        strengths=strengths,
        risks=risks,
        valuation=val,
        metrics=metrics,
    )

    logger.info(
        f"[FinancialAgent] Done for {yf_ticker} — "
        f"health={health}, valuation={val}, "
        f"pe={metrics.pe_ratio}, roe={metrics.roe}"
    )
    return output


# ── Assessment helpers ────────────────────────────────────────────────────────

def _assess_health(m: FinancialMetrics) -> str:
    """
    Score financial health across 5 dimensions.
    Returns "Strong" | "Moderate" | "Weak"
    """
    score = 0
    total = 0

    # Profitability
    if m.profit_margin is not None:
        total += 1
        if m.profit_margin > 0.15:
            score += 2
        elif m.profit_margin > 0.05:
            score += 1
        # negative margin = 0 points

    # Return on Equity
    if m.roe is not None:
        total += 1
        if m.roe > 0.20:
            score += 2
        elif m.roe > 0.10:
            score += 1

    # Debt
    if m.debt_to_equity is not None:
        total += 1
        if m.debt_to_equity < 0.5:
            score += 2
        elif m.debt_to_equity < 1.5:
            score += 1

    # Free Cash Flow
    if m.free_cash_flow is not None:
        total += 1
        if m.free_cash_flow > 0:
            score += 2
        # negative FCF = 0 points

    # Revenue Growth
    if m.revenue_growth is not None:
        total += 1
        if m.revenue_growth > 0.10:
            score += 2
        elif m.revenue_growth > 0.0:
            score += 1

    if total == 0:
        return "Unknown"

    ratio = score / (total * 2)  # max score = total * 2
    if ratio >= 0.65:
        return "Strong"
    elif ratio >= 0.35:
        return "Moderate"
    return "Weak"


def _assess_valuation(m: FinancialMetrics, sector: str) -> str:
    """
    Compare P/E to sector benchmark.
    Returns "Overvalued" | "Fairly Valued" | "Undervalued"
    """
    if m.pe_ratio is None or m.pe_ratio <= 0:
        return "Unknown"

    benchmark = _SECTOR_PE_BENCHMARKS.get(sector, _DEFAULT_PE_BENCHMARK)
    ratio = m.pe_ratio / benchmark

    if ratio > 1.30:
        return "Overvalued"
    elif ratio < 0.75:
        return "Undervalued"
    return "Fairly Valued"


def _identify_strengths(m: FinancialMetrics, info: dict) -> list[str]:
    strengths: list[str] = []

    if m.roe is not None and m.roe > 0.18:
        strengths.append(f"Strong return on equity of {m.roe:.1%}, indicating efficient capital use.")

    if m.profit_margin is not None and m.profit_margin > 0.12:
        strengths.append(f"Healthy profit margin of {m.profit_margin:.1%}.")

    if m.revenue_growth is not None and m.revenue_growth > 0.10:
        strengths.append(f"Robust revenue growth of {m.revenue_growth:.1%} YoY.")

    if m.debt_to_equity is not None and m.debt_to_equity < 0.5:
        strengths.append(f"Low debt-to-equity ratio of {m.debt_to_equity:.2f} — conservative balance sheet.")

    if m.free_cash_flow is not None and m.free_cash_flow > 0:
        fcf_cr = m.free_cash_flow / 1e7  # convert to Crores
        strengths.append(f"Positive free cash flow of ₹{fcf_cr:,.0f} Cr — strong cash generation.")

    if m.dividend_yield is not None and m.dividend_yield > 0.02:
        strengths.append(f"Attractive dividend yield of {m.dividend_yield:.2%}.")

    if m.beta is not None and m.beta < 0.8:
        strengths.append(f"Low beta of {m.beta:.2f} — defensive stock with below-market volatility.")

    company_name = info.get("longName", "")
    if info.get("recommendationKey") in ("buy", "strong_buy"):
        strengths.append(f"Analyst consensus leans positive ({info.get('recommendationKey', '').replace('_', ' ').title()}).")

    if not strengths:
        strengths.append("Limited data available for strength assessment.")

    return strengths[:6]


def _identify_risks(m: FinancialMetrics, info: dict) -> list[str]:
    risks: list[str] = []

    if m.pe_ratio is not None and m.pe_ratio > 50:
        risks.append(f"High P/E ratio of {m.pe_ratio:.1f}x — significant growth already priced in.")

    if m.debt_to_equity is not None and m.debt_to_equity > 1.5:
        risks.append(f"Elevated debt-to-equity of {m.debt_to_equity:.2f} — leveraged balance sheet.")

    if m.profit_margin is not None and m.profit_margin < 0.05:
        risks.append(
            f"Thin profit margin of {m.profit_margin:.1%} — vulnerable to cost pressures."
            if m.profit_margin >= 0
            else f"Negative profit margin of {m.profit_margin:.1%} — company is loss-making."
        )

    if m.revenue_growth is not None and m.revenue_growth < 0:
        risks.append(f"Revenue declined {m.revenue_growth:.1%} YoY — demand headwinds present.")

    if m.free_cash_flow is not None and m.free_cash_flow < 0:
        risks.append("Negative free cash flow — company is consuming cash reserves.")

    if m.beta is not None and m.beta > 1.5:
        risks.append(f"High beta of {m.beta:.2f} — significantly more volatile than the market.")

    if m.roe is not None and m.roe < 0.08:
        risks.append(f"Low ROE of {m.roe:.1%} — capital allocation efficiency concerns.")

    if m.fifty_two_week_high and m.current_price:
        drawdown = (m.fifty_two_week_high - m.current_price) / m.fifty_two_week_high
        if drawdown > 0.25:
            risks.append(f"Stock is {drawdown:.0%} below its 52-week high — under significant selling pressure.")

    if not risks:
        risks.append("No major financial risk flags identified at current metrics.")

    return risks[:6]