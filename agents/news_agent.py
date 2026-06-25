"""
News Agent
Fetches recent news for a stock via Google News RSS,
then uses Gemini to summarise and classify bullish/bearish catalysts.
"""

from __future__ import annotations
import json
import os

from google import genai
from dotenv import load_dotenv

load_dotenv()

from logging_config import logger
from schemas.analysis_schemas import NewsOutput
from tools.news_rss_tool import fetch_google_news, extract_headlines
from prompts.news_prompt import build_news_summary_prompt
from services.ticker_resolver import resolve_ticker, get_company_name

# ── Gemini client (new google-genai SDK) ──────────────────────────────────────
_CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def run_news_agent(ticker: str) -> NewsOutput:
    """
    Main entry point for the News Agent.

    Steps:
      1. Resolve ticker → yfinance symbol
      2. Fetch headlines from Google News RSS
      3. Send to Gemini for structured summary
      4. Return typed NewsOutput

    Args:
        ticker: Raw user-supplied ticker e.g. "TCS", "RELIANCE"

    Returns:
        NewsOutput — fully populated
    """
    yf_ticker    = resolve_ticker(ticker)
    company_name = get_company_name(yf_ticker)

    logger.info(f"[NewsAgent] Starting for {company_name} ({yf_ticker})")

    # ── Step 1: Fetch raw articles ─────────────────────────────────────────────
    articles  = fetch_google_news(company_name, yf_ticker, max_articles=20)
    headlines = extract_headlines(articles)

    if not headlines:
        logger.warning(f"[NewsAgent] No headlines found for {yf_ticker} — returning neutral output")
        return NewsOutput(
            stock=ticker.upper(),
            news_summary="No recent news found for this stock.",
            bullish_news=[],
            bearish_news=[],
            overall_news_impact="Neutral",
            headlines=[],
        )

    # ── Step 2: Gemini structured summary ─────────────────────────────────────
    prompt = build_news_summary_prompt(yf_ticker, company_name, headlines)

    try:
        response = _CLIENT.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )
        raw_text = response.text.strip()

        # Strip markdown fences if Gemini returns them
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)

        output = NewsOutput(
            stock=ticker.upper(),
            news_summary=parsed.get("news_summary", ""),
            bullish_news=parsed.get("bullish_news", []),
            bearish_news=parsed.get("bearish_news", []),
            overall_news_impact=parsed.get("overall_news_impact", "Neutral"),
            headlines=headlines[:10],
        )
        logger.info(
            f"[NewsAgent] Done for {yf_ticker} — "
            f"impact={output.overall_news_impact}, "
            f"bullish={len(output.bullish_news)}, bearish={len(output.bearish_news)}"
        )
        return output

    except json.JSONDecodeError as e:
        logger.error(f"[NewsAgent] JSON parse error for {yf_ticker}: {e}")
        return _fallback_output(ticker, headlines, articles)

    except Exception as e:
        logger.error(f"[NewsAgent] Gemini call failed for {yf_ticker}: {e}")
        return _fallback_output(ticker, headlines, articles)


def _fallback_output(ticker: str, headlines: list[str], articles: list[dict]) -> NewsOutput:
    """
    Rule-based fallback when Gemini is unavailable.
    Classifies headlines using simple positive/negative keyword matching.
    """
    positive_kw = {"profit", "growth", "surge", "record", "beat", "upgrade", "buy",
                   "gain", "rally", "rise", "strong", "dividend", "order", "expand"}
    negative_kw = {"loss", "fall", "miss", "weak", "downgrade", "sell", "slump",
                   "risk", "debt", "fine", "fraud", "decline", "cut", "delay"}

    bullish, bearish = [], []
    for h in headlines:
        words = set(h.lower().split())
        if words & positive_kw:
            bullish.append(h)
        elif words & negative_kw:
            bearish.append(h)

    if len(bullish) > len(bearish):
        impact = "Positive"
    elif len(bearish) > len(bullish):
        impact = "Negative"
    else:
        impact = "Neutral"

    summary = (
        f"Keyword analysis of {len(headlines)} headlines: "
        f"{len(bullish)} positive, {len(bearish)} negative signals detected."
    )

    return NewsOutput(
        stock=ticker.upper(),
        news_summary=summary,
        bullish_news=bullish[:5],
        bearish_news=bearish[:5],
        overall_news_impact=impact,
        headlines=headlines[:10],
    )