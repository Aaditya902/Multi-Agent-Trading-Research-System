"""
Sentiment Agent
Runs FinBERT over news headlines and summaries to produce
a structured market sentiment output.
"""

from __future__ import annotations

from logging_config import logger
from schemas.analysis_schemas import SentimentOutput
from tools.finbert_tool import analyse_sentiment
from services.ticker_resolver import resolve_ticker


def run_sentiment_agent(
    ticker: str,
    headlines: list[str] | None = None,
    summaries: list[str] | None = None,
) -> SentimentOutput:
    """
    Main entry point for the Sentiment Agent.

    Accepts optional pre-fetched headlines/summaries from the News Agent
    (passed in via LangGraph state) to avoid duplicate RSS calls.
    Falls back to an empty list if none are provided.

    Args:
        ticker:    Raw user ticker e.g. "ZOMATO"
        headlines: List of news headline strings (from NewsOutput.headlines)
        summaries: List of article summary strings (from fetched articles)

    Returns:
        SentimentOutput — fully populated
    """
    yf_ticker = resolve_ticker(ticker)
    logger.info(f"[SentimentAgent] Starting for {yf_ticker}")

    # ── Combine all text inputs ───────────────────────────────────────────────
    texts: list[str] = []
    if headlines:
        texts.extend(h for h in headlines if h and h.strip())
    if summaries:
        texts.extend(s for s in summaries if s and s.strip())

    if not texts:
        logger.warning(f"[SentimentAgent] No text inputs for {yf_ticker} — returning neutral")
        return SentimentOutput(
            stock=ticker.upper(),
            sentiment="Neutral",
            score=0.0,
            explanation="No news text available for sentiment analysis.",
            positive_score=0.0,
            negative_score=0.0,
            neutral_score=1.0,
        )

    # ── Run FinBERT ───────────────────────────────────────────────────────────
    result = analyse_sentiment(texts)

    output = SentimentOutput(
        stock=ticker.upper(),
        sentiment=result["sentiment"],
        score=result["score"],
        explanation=result["explanation"],
        positive_score=result["positive_score"],
        negative_score=result["negative_score"],
        neutral_score=result["neutral_score"],
    )

    logger.info(
        f"[SentimentAgent] Done for {yf_ticker} — "
        f"sentiment={output.sentiment}, score={output.score:+.3f}"
    )
    return output


def run_sentiment_agent_from_news_output(
    ticker: str,
    news_output,  # NewsOutput — avoids circular import
) -> SentimentOutput:
    """
    Convenience wrapper: pulls headlines directly from a NewsOutput object.
    Used in the LangGraph workflow after news_agent completes.
    """
    headlines = getattr(news_output, "headlines", []) or []
    return run_sentiment_agent(ticker=ticker, headlines=headlines)