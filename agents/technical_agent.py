"""
Technical Analysis Agent
Fetches OHLCV price history via yfinance and computes
RSI, MACD, SMA/EMA, Bollinger Bands using pandas-ta.
"""

from __future__ import annotations

from logging_config import logger
from schemas.analysis_schemas import TechnicalOutput
from tools.yfinance_tool import fetch_historical_data
from tools.technical_tool import compute_indicators
from services.ticker_resolver import resolve_ticker, get_company_name


def run_technical_agent(ticker: str) -> TechnicalOutput:
    """
    Main entry point for the Technical Analysis Agent.

    Steps:
      1. Resolve ticker to yfinance symbol
      2. Fetch 1-year daily OHLCV history
      3. Compute all indicators via pandas-ta
      4. Return typed TechnicalOutput

    Args:
        ticker: Raw user-supplied ticker e.g. "TATAMOTORS"

    Returns:
        TechnicalOutput — fully populated with all indicator signals
    """
    yf_ticker    = resolve_ticker(ticker)
    company_name = get_company_name(yf_ticker)

    logger.info(f"[TechnicalAgent] Starting for {company_name} ({yf_ticker})")

    # ── Fetch price history ───────────────────────────────────────────────────
    df = fetch_historical_data(yf_ticker, period="1y", interval="1d")

    if df.empty:
        logger.warning(f"[TechnicalAgent] No price data for {yf_ticker}")
        return TechnicalOutput(
            stock=ticker.upper(),
            trend="Unknown",
            macd_signal="Neutral",
            moving_average_signal="Neutral",
            bollinger_signal="Normal",
            technical_summary=(
                f"No historical price data available for {yf_ticker}. "
                "Technical analysis could not be performed."
            ),
        )

    logger.debug(f"[TechnicalAgent] {len(df)} rows fetched for {yf_ticker}")

    # ── Compute indicators ────────────────────────────────────────────────────
    output = compute_indicators(df, ticker.upper())

    # ── Enrich summary with actionable signal count ───────────────────────────
    output = _enrich_output(output)

    logger.info(
        f"[TechnicalAgent] Done for {yf_ticker} — "
        f"trend={output.trend}, rsi={output.rsi}, "
        f"macd={output.macd_signal}, ma={output.moving_average_signal}"
    )
    return output


def _enrich_output(output: TechnicalOutput) -> TechnicalOutput:
    """
    Append an actionable signal count summary to technical_summary.
    Counts bullish vs bearish signals across all indicators.
    """
    bullish_signals = 0
    bearish_signals = 0

    # Trend
    if output.trend == "Uptrend":
        bullish_signals += 2
    elif output.trend == "Downtrend":
        bearish_signals += 2

    # RSI
    if output.rsi is not None:
        if output.rsi < 30:
            bullish_signals += 1   # Oversold = potential reversal up
        elif output.rsi > 70:
            bearish_signals += 1   # Overbought = potential reversal down

    # MACD
    if output.macd_signal == "Bullish":
        bullish_signals += 1
    elif output.macd_signal == "Bearish":
        bearish_signals += 1

    # Moving Averages
    if output.moving_average_signal == "Bullish":
        bullish_signals += 1
    elif output.moving_average_signal == "Bearish":
        bearish_signals += 1

    # Bollinger Bands
    if output.bollinger_signal == "Oversold":
        bullish_signals += 1
    elif output.bollinger_signal == "Overbought":
        bearish_signals += 1

    total = bullish_signals + bearish_signals
    if total == 0:
        signal_text = "No clear directional bias from indicators."
    else:
        bull_pct = (bullish_signals / total) * 100
        if bull_pct >= 70:
            signal_text = f"Strong bullish confluence: {bullish_signals}/{total} indicators point upward."
        elif bull_pct >= 50:
            signal_text = f"Mild bullish bias: {bullish_signals}/{total} indicators favour upside."
        elif bull_pct <= 30:
            signal_text = f"Strong bearish confluence: {bearish_signals}/{total} indicators point downward."
        else:
            signal_text = f"Mixed signals: {bullish_signals} bullish vs {bearish_signals} bearish indicators."

    # Append signal count to existing summary
    enriched_summary = f"{output.technical_summary} {signal_text}"
    return output.model_copy(update={"technical_summary": enriched_summary})