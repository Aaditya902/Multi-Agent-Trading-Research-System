"""
Technical analysis tool using pandas-ta.
Computes RSI, MACD, SMA, EMA, and Bollinger Bands from yfinance OHLCV data.
"""

from __future__ import annotations
import pandas as pd
import pandas_ta as ta

from logging_config import logger
from schemas.analysis_schemas import TechnicalOutput


def compute_indicators(df: pd.DataFrame, ticker: str) -> TechnicalOutput:
    """
    Compute all technical indicators and return a typed TechnicalOutput.

    Args:
        df: yfinance OHLCV DataFrame (columns: Open, High, Low, Close, Volume)
        ticker: Ticker symbol for logging

    Returns:
        TechnicalOutput with all signals populated.
    """
    if df.empty or len(df) < 30:
        logger.warning(f"Insufficient data for technical analysis of {ticker} ({len(df)} rows)")
        return TechnicalOutput(
            stock=ticker,
            trend="Insufficient Data",
            macd_signal="Neutral",
            moving_average_signal="Neutral",
            bollinger_signal="Normal",
            technical_summary="Insufficient historical data for technical analysis.",
        )

    close = df["Close"].dropna()
    current_price = float(close.iloc[-1]) if not close.empty else None

    # ── RSI ──────────────────────────────────────────────────────────────────
    rsi_series = ta.rsi(close, length=14)
    rsi = float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else None

    # ── MACD ─────────────────────────────────────────────────────────────────
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_signal = "Neutral"
    if macd_df is not None and not macd_df.empty:
        macd_line = macd_df.get("MACD_12_26_9")
        signal_line = macd_df.get("MACDs_12_26_9")
        if macd_line is not None and signal_line is not None:
            m = float(macd_line.iloc[-1]) if not macd_line.dropna().empty else None
            s = float(signal_line.iloc[-1]) if not signal_line.dropna().empty else None
            if m is not None and s is not None:
                macd_signal = "Bullish" if m > s else "Bearish"

    # ── Moving Averages ───────────────────────────────────────────────────────
    sma_50_s  = ta.sma(close, length=50)
    sma_200_s = ta.sma(close, length=200)
    ema_20_s  = ta.ema(close, length=20)
    ema_50_s  = ta.ema(close, length=50)

    def last(s) -> float | None:
        return float(s.dropna().iloc[-1]) if s is not None and not s.dropna().empty else None

    sma_50  = last(sma_50_s)
    sma_200 = last(sma_200_s)
    ema_20  = last(ema_20_s)
    ema_50  = last(ema_50_s)

    # MA signal: golden cross / death cross
    ma_signal = "Neutral"
    if sma_50 is not None and sma_200 is not None:
        if sma_50 > sma_200:
            ma_signal = "Bullish"   # golden cross zone
        else:
            ma_signal = "Bearish"   # death cross zone

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_df = ta.bbands(close, length=20, std=2)
    bb_upper = bb_lower = bb_middle = None
    bb_signal = "Normal"
    if bb_df is not None and not bb_df.empty:
        bb_upper  = last(bb_df.get("BBU_20_2.0"))
        bb_lower  = last(bb_df.get("BBL_20_2.0"))
        bb_middle = last(bb_df.get("BBM_20_2.0"))
        if current_price is not None and bb_upper is not None and bb_lower is not None:
            if current_price >= bb_upper:
                bb_signal = "Overbought"
            elif current_price <= bb_lower:
                bb_signal = "Oversold"

    # ── Trend determination ───────────────────────────────────────────────────
    trend = _determine_trend(close, ema_20, ema_50, sma_50, sma_200)

    # ── Technical summary ────────────────────────────────────────────────────
    summary = _build_summary(ticker, trend, rsi, macd_signal, ma_signal, bb_signal, current_price)

    return TechnicalOutput(
        stock=ticker,
        trend=trend,
        rsi=round(rsi, 2) if rsi is not None else None,
        macd_signal=macd_signal,
        moving_average_signal=ma_signal,
        bollinger_signal=bb_signal,
        technical_summary=summary,
        sma_50=round(sma_50, 2) if sma_50 else None,
        sma_200=round(sma_200, 2) if sma_200 else None,
        ema_20=round(ema_20, 2) if ema_20 else None,
        ema_50=round(ema_50, 2) if ema_50 else None,
        bb_upper=round(bb_upper, 2) if bb_upper else None,
        bb_lower=round(bb_lower, 2) if bb_lower else None,
        bb_middle=round(bb_middle, 2) if bb_middle else None,
        current_price=round(current_price, 2) if current_price else None,
    )


def _determine_trend(
    close: pd.Series,
    ema_20: float | None,
    ema_50: float | None,
    sma_50: float | None,
    sma_200: float | None,
) -> str:
    """Determine primary trend using price vs key MAs."""
    current = float(close.iloc[-1])

    bullish_signals = 0
    bearish_signals = 0

    for ma in [ema_20, ema_50, sma_50, sma_200]:
        if ma is not None:
            if current > ma:
                bullish_signals += 1
            else:
                bearish_signals += 1

    # Also check 20-day price change
    if len(close) >= 20:
        pct_change = (current - float(close.iloc[-20])) / float(close.iloc[-20])
        if pct_change > 0.03:
            bullish_signals += 1
        elif pct_change < -0.03:
            bearish_signals += 1

    if bullish_signals > bearish_signals + 1:
        return "Uptrend"
    elif bearish_signals > bullish_signals + 1:
        return "Downtrend"
    return "Sideways"


def _build_summary(
    ticker: str,
    trend: str,
    rsi: float | None,
    macd_signal: str,
    ma_signal: str,
    bb_signal: str,
    price: float | None,
) -> str:
    parts = [f"{ticker} is in a {trend}."]

    if rsi is not None:
        if rsi > 70:
            parts.append(f"RSI at {rsi:.1f} indicates overbought conditions.")
        elif rsi < 30:
            parts.append(f"RSI at {rsi:.1f} indicates oversold conditions.")
        else:
            parts.append(f"RSI at {rsi:.1f} is in neutral territory.")

    parts.append(f"MACD is {macd_signal}. Moving average signal is {ma_signal}.")

    if bb_signal != "Normal":
        parts.append(f"Bollinger Bands show {bb_signal} conditions.")

    if price:
        parts.append(f"Current price: ₹{price:,.2f}.")

    return " ".join(parts)