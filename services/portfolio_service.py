"""
Portfolio Intelligence Service.
Computes diversification, risk, concentration, and generates suggestions.
"""

from __future__ import annotations
import math
from tools.yfinance_tool import fetch_stock_info, extract_financial_metrics
from services.ticker_resolver import resolve_ticker, get_company_name
from schemas.portfolio_schemas import (
    PortfolioInsight, StockWeight, SectorAllocation,
    PortfolioDiversification, PortfolioRisk, ConcentrationRisk,
)
from logging_config import logger


def analyse_portfolio(tickers: list[str]) -> PortfolioInsight:
    """
    Run portfolio intelligence analysis on a list of tickers.
    Equal-weighted for now (UI can extend to custom weights).
    """
    n = len(tickers)
    equal_weight = 100.0 / n

    stock_weights: list[StockWeight] = []
    sector_map: dict[str, list[str]] = {}
    betas: list[float] = []

    for raw_ticker in tickers:
        yf_ticker = resolve_ticker(raw_ticker)
        company = get_company_name(yf_ticker)

        try:
            info = fetch_stock_info(yf_ticker)
            metrics = extract_financial_metrics(info)
            sector = info.get("sector") or info.get("industry") or "Unknown"
            beta = metrics.beta
        except Exception as e:
            logger.warning(f"Could not fetch info for {yf_ticker}: {e}")
            sector = "Unknown"
            beta = None
            metrics = None

        stock_weights.append(StockWeight(
            ticker=raw_ticker.upper(),
            weight_pct=equal_weight,
            sector=sector,
            current_price=metrics.current_price if metrics else None,
        ))

        sector_map.setdefault(sector, []).append(raw_ticker.upper())
        if beta is not None:
            betas.append(beta)

    # ── Sector allocation ─────────────────────────────────────────────────────
    sector_allocations = [
        SectorAllocation(
            sector=sec,
            weight_pct=round(len(tks) * equal_weight, 2),
            tickers=tks,
        )
        for sec, tks in sorted(sector_map.items(), key=lambda x: -len(x[1]))
    ]

    # ── Concentration (Herfindahl-Hirschman Index) ────────────────────────────
    sector_weights = [len(tks) / n for tks in sector_map.values()]
    hhi = sum(w ** 2 for w in sector_weights)  # 0 = max diversity, 1 = max concentration
    top_sector_pct = max(len(tks) * equal_weight for tks in sector_map.values())

    if hhi > 0.6:
        conc_level = "Very High"
    elif hhi > 0.35:
        conc_level = "High"
    elif hhi > 0.18:
        conc_level = "Medium"
    else:
        conc_level = "Low"

    concentration = ConcentrationRisk(
        level=conc_level,
        top_holding_pct=equal_weight,          # all equal weight for now
        top_sector_pct=round(top_sector_pct, 1),
        herfindahl_index=round(hhi, 4),
    )

    # ── Diversification score ─────────────────────────────────────────────────
    sector_count = len(sector_map)
    # Shannon entropy-based score
    entropy = -sum(w * math.log(w + 1e-9) for w in sector_weights)
    max_entropy = math.log(max(sector_count, 1))
    div_ratio = (entropy / max_entropy) if max_entropy > 0 else 0.5
    div_score = round(min(100.0, div_ratio * 100 * (min(n, 10) / 10)), 1)

    diversification = PortfolioDiversification(
        score=div_score,
        sector_count=sector_count,
        stock_count=n,
        interpretation=_div_interpretation(div_score),
    )

    # ── Risk score ────────────────────────────────────────────────────────────
    avg_beta = sum(betas) / len(betas) if betas else 1.0
    risk_score = round(min(100.0, avg_beta * 50 + (1 - div_ratio) * 30 + (1 if n < 5 else 0) * 20), 1)
    risk_level = (
        "Very High" if risk_score > 75 else
        "High" if risk_score > 55 else
        "Moderate" if risk_score > 35 else
        "Low"
    )

    risk = PortfolioRisk(
        score=risk_score,
        level=risk_level,
        avg_beta=round(avg_beta, 2),
        interpretation=f"Portfolio beta ≈ {avg_beta:.2f}. {risk_level} overall risk profile.",
    )

    # ── Suggestions ───────────────────────────────────────────────────────────
    suggestions = _generate_suggestions(sector_map, n, div_score, risk_level, top_sector_pct)

    return PortfolioInsight(
        stocks=stock_weights,
        sector_allocation=sector_allocations,
        diversification=diversification,
        risk=risk,
        concentration=concentration,
        suggestions=suggestions,
        overall_recommendation=f"Portfolio has {risk_level} risk and {_div_label(div_score)} diversification. {suggestions[0] if suggestions else ''}",
    )


def _div_interpretation(score: float) -> str:
    if score >= 75:
        return "Well diversified across multiple sectors."
    if score >= 50:
        return "Moderately diversified. Some sector concentration exists."
    if score >= 25:
        return "Poorly diversified. Consider adding exposure to other sectors."
    return "Highly concentrated. Significant single-sector risk."


def _div_label(score: float) -> str:
    if score >= 75:
        return "good"
    if score >= 50:
        return "moderate"
    return "poor"


def _generate_suggestions(
    sector_map: dict,
    n: int,
    div_score: float,
    risk_level: str,
    top_sector_pct: float,
) -> list[str]:
    suggestions = []
    top_sector = max(sector_map, key=lambda s: len(sector_map[s]))

    if top_sector_pct > 50:
        suggestions.append(
            f"Portfolio is overexposed to {top_sector} ({top_sector_pct:.0f}%). "
            f"Consider diversifying into other sectors."
        )
    if n < 5:
        suggestions.append(
            "Portfolio has fewer than 5 stocks — concentration risk is high. "
            "Consider adding 3-5 more stocks from different sectors."
        )
    if "Unknown" in sector_map:
        suggestions.append(
            "Some stocks could not be classified by sector. Verify these tickers are correct."
        )
    if risk_level in ("High", "Very High"):
        suggestions.append(
            "Overall portfolio beta is elevated. Consider adding defensive stocks "
            "(FMCG, Pharma, or utilities) to reduce volatility."
        )
    if div_score < 40:
        missing = [s for s in ["Information Technology", "Financial Services", "Healthcare", "Consumer Staples", "Energy"]
                   if s not in sector_map][:2]
        if missing:
            suggestions.append(
                f"Portfolio lacks exposure to: {', '.join(missing)}. "
                f"Adding stocks from these sectors would improve diversification."
            )
    if not suggestions:
        suggestions.append(
            "Portfolio appears reasonably balanced. Monitor sector weights quarterly."
        )
    return suggestions