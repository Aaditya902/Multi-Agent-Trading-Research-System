"""
Market Brief Service.
Fetches NIFTY/SENSEX data, top gainers/losers, and generates the daily brief via Gemini.
"""

from __future__ import annotations
import os
from datetime import date

import yfinance as yf

from tools.news_rss_tool import fetch_market_news
from prompts.sector_prompt import build_market_brief_prompt
from logging_config import logger


_NIFTY50_TICKER  = "^NSEI"
_SENSEX_TICKER   = "^BSESN"

# Top 20 NIFTY stocks to scan for gainers/losers
_NIFTY_SAMPLE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "BAJFINANCE.NS", "WIPRO.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "ONGC.NS",
    "TECHM.NS", "MARUTI.NS", "TATASTEEL.NS", "HCLTECH.NS", "NTPC.NS",
]


def _fetch_index_data(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if hist.empty or len(hist) < 2:
            return {"change_pct": None, "close": None}
        prev_close = float(hist["Close"].iloc[-2])
        last_close = float(hist["Close"].iloc[-1])
        change_pct = ((last_close - prev_close) / prev_close) * 100
        return {
            "ticker": ticker,
            "close": round(last_close, 2),
            "prev_close": round(prev_close, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception as e:
        logger.warning(f"Index data fetch failed for {ticker}: {e}")
        return {"ticker": ticker, "change_pct": None, "close": None}


def _fetch_movers(tickers: list[str]) -> tuple[list[dict], list[dict]]:
    movers: list[dict] = []
    for tk in tickers:
        try:
            hist = yf.Ticker(tk).history(period="2d")
            if hist.empty or len(hist) < 2:
                continue
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
            pct = ((last - prev) / prev) * 100
            movers.append({"symbol": tk.replace(".NS", ""), "change_pct": round(pct, 2), "close": round(last, 2)})
        except Exception:
            pass

    gainers = sorted([m for m in movers if m["change_pct"] > 0], key=lambda x: -x["change_pct"])
    losers  = sorted([m for m in movers if m["change_pct"] < 0], key=lambda x: x["change_pct"])
    return gainers[:5], losers[:5]


def generate_market_brief(gemini_model) -> dict:
    """
    Generate the daily Indian market brief.

    Args:
        gemini_model: Initialised google.generativeai GenerativeModel instance

    Returns:
        dict with keys: date, report_markdown, nifty_change_pct, sensex_change_pct,
                        top_gainers, top_losers
    """
    logger.info("Generating market brief …")
    today = date.today().isoformat()

    nifty_data  = _fetch_index_data(_NIFTY50_TICKER)
    sensex_data = _fetch_index_data(_SENSEX_TICKER)
    gainers, losers = _fetch_movers(_NIFTY_SAMPLE)
    news = fetch_market_news(max_articles=15)

    prompt = build_market_brief_prompt(nifty_data, sensex_data, gainers, losers, news)

    try:
        response = gemini_model.generate_content(prompt)
        report_md = response.text.strip()
    except Exception as e:
        logger.error(f"Gemini market brief generation failed: {e}")
        report_md = f"# Indian Market Brief — {today}\n\nData fetched but report generation failed: {e}"

    return {
        "date": today,
        "report_markdown": report_md,
        "nifty_change_pct": nifty_data.get("change_pct"),
        "sensex_change_pct": sensex_data.get("change_pct"),
        "top_gainers": gainers,
        "top_losers": losers,
    }