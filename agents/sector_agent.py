"""
Sector Analysis Agent
Identifies the stock's sector, fetches peer metrics via yfinance,
and uses Gemini to evaluate relative competitive position.
"""

from __future__ import annotations
import json
import os

from google import genai
from dotenv import load_dotenv

load_dotenv()

from logging_config import logger
from schemas.analysis_schemas import SectorOutput, PeerData
from tools.yfinance_tool import fetch_stock_info, extract_financial_metrics
from prompts.sector_prompt import build_sector_summary_prompt
from services.ticker_resolver import resolve_ticker, get_company_name, get_nse_peers

_CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def run_sector_agent(ticker: str) -> SectorOutput:
    """
    Main entry point for the Sector Analysis Agent.

    Steps:
      1. Resolve ticker + fetch its info (sector, key metrics)
      2. Identify peers via ticker_resolver
      3. Fetch peer metrics from yfinance
      4. Call Gemini to assess relative position
      5. Return typed SectorOutput

    Args:
        ticker: Raw user-supplied ticker e.g. "TCS"

    Returns:
        SectorOutput — fully populated
    """
    yf_ticker    = resolve_ticker(ticker)
    company_name = get_company_name(yf_ticker)

    logger.info(f"[SectorAgent] Starting for {company_name} ({yf_ticker})")

    # ── Step 1: Target company info ───────────────────────────────────────────
    target_info    = fetch_stock_info(yf_ticker)
    target_metrics = extract_financial_metrics(target_info)
    sector         = target_info.get("sector") or target_info.get("industry") or "Unknown"

    target_metrics_dict = {
        "pe_ratio":       target_metrics.pe_ratio,
        "market_cap":     target_metrics.market_cap,
        "revenue_growth": target_metrics.revenue_growth,
        "roe":            target_metrics.roe,
        "profit_margin":  target_metrics.profit_margin,
        "debt_to_equity": target_metrics.debt_to_equity,
    }

    # ── Step 2: Discover peers ────────────────────────────────────────────────
    peer_tickers = get_nse_peers(yf_ticker)

    if not peer_tickers:
        # Fallback: use yfinance recommended peers if available
        peer_tickers = _get_yf_peers(target_info) or []

    logger.debug(f"[SectorAgent] Peers for {yf_ticker}: {peer_tickers}")

    # ── Step 3: Fetch peer metrics ────────────────────────────────────────────
    peers: list[PeerData] = []
    for peer_tk in peer_tickers[:4]:   # cap at 4 peers to stay within rate limits
        try:
            peer_info    = fetch_stock_info(peer_tk)
            peer_metrics = extract_financial_metrics(peer_info)
            peers.append(PeerData(
                ticker=peer_tk,
                name=peer_info.get("longName") or peer_info.get("shortName") or peer_tk,
                pe_ratio=peer_metrics.pe_ratio,
                market_cap=peer_metrics.market_cap,
                revenue_growth=peer_metrics.revenue_growth,
                roe=peer_metrics.roe,
                profit_margin=peer_metrics.profit_margin,
            ))
        except Exception as e:
            logger.warning(f"[SectorAgent] Peer fetch failed for {peer_tk}: {e}")

    # ── Step 4: Compute sector averages ───────────────────────────────────────
    all_pe  = [p.pe_ratio      for p in peers if p.pe_ratio      is not None]
    all_grw = [p.revenue_growth for p in peers if p.revenue_growth is not None]

    if target_metrics.pe_ratio:
        all_pe.append(target_metrics.pe_ratio)
    if target_metrics.revenue_growth:
        all_grw.append(target_metrics.revenue_growth)

    sector_pe_avg  = round(sum(all_pe) / len(all_pe),   2) if all_pe  else None
    sector_grw_avg = round(sum(all_grw) / len(all_grw), 4) if all_grw else None

    # ── Step 5: Gemini competitive assessment ─────────────────────────────────
    gemini_result = _call_gemini_sector(
        ticker, company_name, sector,
        target_metrics_dict, peers,
        sector_pe_avg, sector_grw_avg,
    )

    output = SectorOutput(
        stock=ticker.upper(),
        sector=sector,
        peers=peers,
        peer_comparison=gemini_result.get("peer_comparison", []),
        sector_strength=gemini_result.get("sector_strength", "Average"),
        relative_position=gemini_result.get("relative_position", "Average"),
        sector_pe_avg=gemini_result.get("sector_pe_avg") or sector_pe_avg,
        sector_growth_avg=gemini_result.get("sector_growth_avg") or sector_grw_avg,
    )

    logger.info(
        f"[SectorAgent] Done for {yf_ticker} — "
        f"sector={sector}, position={output.relative_position}, "
        f"strength={output.sector_strength}, peers={len(peers)}"
    )
    return output


# ── Helpers ───────────────────────────────────────────────────────────────────

def _call_gemini_sector(
    ticker: str,
    company_name: str,
    sector: str,
    target_metrics_dict: dict,
    peers: list[PeerData],
    sector_pe_avg: float | None,
    sector_grw_avg: float | None,
) -> dict:
    """Call Gemini for competitive position assessment; return parsed dict."""
    prompt = build_sector_summary_prompt(
        ticker, company_name, sector, target_metrics_dict, peers
    )
    try:
        response = _CLIENT.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[SectorAgent] Gemini call failed: {e} — using rule-based fallback")
        return _rule_based_position(target_metrics_dict, peers, sector_pe_avg)


def _rule_based_position(
    target: dict,
    peers: list[PeerData],
    sector_pe_avg: float | None,
) -> dict:
    """
    Fallback when Gemini is unavailable.
    Scores the target vs peers on PE, growth, ROE, and margin.
    """
    if not peers:
        return {
            "sector_strength": "Average",
            "relative_position": "Average",
            "peer_comparison": [],
        }

    score = 0  # positive = target is better than peers

    # P/E: lower is generally better for value
    target_pe = target.get("pe_ratio")
    peer_pes  = [p.pe_ratio for p in peers if p.pe_ratio]
    if target_pe and peer_pes:
        avg_peer_pe = sum(peer_pes) / len(peer_pes)
        if target_pe < avg_peer_pe * 0.9:
            score += 1   # cheaper than peers
        elif target_pe > avg_peer_pe * 1.1:
            score -= 1

    # Revenue growth: higher is better
    target_grw  = target.get("revenue_growth")
    peer_growths = [p.revenue_growth for p in peers if p.revenue_growth]
    if target_grw and peer_growths:
        avg_peer_grw = sum(peer_growths) / len(peer_growths)
        score += 1 if target_grw > avg_peer_grw else -1

    # ROE: higher is better
    target_roe  = target.get("roe")
    peer_roes   = [p.roe for p in peers if p.roe]
    if target_roe and peer_roes:
        avg_peer_roe = sum(peer_roes) / len(peer_roes)
        score += 1 if target_roe > avg_peer_roe else -1

    # Profit margin: higher is better
    target_pm  = target.get("profit_margin")
    peer_pms   = [p.profit_margin for p in peers if p.profit_margin]
    if target_pm and peer_pms:
        avg_peer_pm = sum(peer_pms) / len(peer_pms)
        score += 1 if target_pm > avg_peer_pm else -1

    relative_position = "Leader" if score >= 2 else "Laggard" if score <= -2 else "Average"
    sector_strength   = "Strong" if score > 0 else "Weak" if score < 0 else "Average"

    peer_comparison = [
        {
            "ticker": p.ticker,
            "name": p.name,
            "vs_target": "Similar",
            "key_difference": "See individual stock reports for detailed comparison.",
        }
        for p in peers
    ]

    return {
        "sector_strength": sector_strength,
        "relative_position": relative_position,
        "peer_comparison": peer_comparison,
    }


def _get_yf_peers(info: dict) -> list[str]:
    """Extract peer tickers from yfinance info if available."""
    # yfinance doesn't reliably expose peers; placeholder for future extension
    return []