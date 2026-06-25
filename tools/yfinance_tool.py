"""
yfinance data fetching tool.
All functions return typed dicts or Pydantic models — never raw yfinance objects.
"""

from __future__ import annotations
import yfinance as yf
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from logging_config import logger
from schemas.analysis_schemas import FinancialMetrics


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def fetch_stock_info(ticker: str) -> dict:
    """Fetch company info dict from yfinance with retry."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        logger.debug(f"Fetched info for {ticker}: {len(info)} keys")
        return info
    except Exception as e:
        logger.error(f"yfinance info fetch failed for {ticker}: {e}")
        return {}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def fetch_historical_data(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch OHLCV historical data."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"No historical data returned for {ticker}")
        else:
            logger.debug(f"Fetched {len(df)} rows of history for {ticker}")
        return df
    except Exception as e:
        logger.error(f"yfinance history fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def extract_financial_metrics(info: dict) -> FinancialMetrics:
    """Parse raw yfinance info dict into a typed FinancialMetrics model."""

    def safe_float(key: str) -> float | None:
        val = info.get(key)
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    return FinancialMetrics(
        current_price=safe_float("currentPrice") or safe_float("regularMarketPrice"),
        market_cap=safe_float("marketCap"),
        revenue=safe_float("totalRevenue"),
        revenue_growth=safe_float("revenueGrowth"),
        eps=safe_float("trailingEps"),
        pe_ratio=safe_float("trailingPE"),
        roe=safe_float("returnOnEquity"),
        profit_margin=safe_float("profitMargins"),
        debt_to_equity=safe_float("debtToEquity"),
        free_cash_flow=safe_float("freeCashflow"),
        dividend_yield=safe_float("dividendYield"),
        fifty_two_week_high=safe_float("fiftyTwoWeekHigh"),
        fifty_two_week_low=safe_float("fiftyTwoWeekLow"),
        beta=safe_float("beta"),
    )


def fetch_dividends(ticker: str) -> pd.Series:
    """Fetch dividend history."""
    try:
        stock = yf.Ticker(ticker)
        return stock.dividends
    except Exception as e:
        logger.error(f"Dividend fetch failed for {ticker}: {e}")
        return pd.Series(dtype=float)


def fetch_splits(ticker: str) -> pd.Series:
    """Fetch stock split history."""
    try:
        stock = yf.Ticker(ticker)
        return stock.splits
    except Exception as e:
        logger.error(f"Splits fetch failed for {ticker}: {e}")
        return pd.Series(dtype=float)


def fetch_actions(ticker: str) -> pd.DataFrame:
    """Fetch combined corporate actions (dividends + splits)."""
    try:
        stock = yf.Ticker(ticker)
        return stock.actions
    except Exception as e:
        logger.error(f"Actions fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def fetch_major_holders(ticker: str) -> pd.DataFrame:
    """Fetch institutional/promoter holding data."""
    try:
        stock = yf.Ticker(ticker)
        return stock.major_holders
    except Exception as e:
        logger.error(f"Major holders fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def fetch_calendar(ticker: str) -> dict:
    """Fetch upcoming earnings dates and events."""
    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        return cal if isinstance(cal, dict) else {}
    except Exception as e:
        logger.error(f"Calendar fetch failed for {ticker}: {e}")
        return {}


def get_current_price(ticker: str) -> float | None:
    """Quick price fetch — uses fast_info for speed."""
    try:
        stock = yf.Ticker(ticker)
        return stock.fast_info.get("lastPrice") or stock.fast_info.get("regularMarketPrice")
    except Exception as e:
        logger.error(f"Price fetch failed for {ticker}: {e}")
        return None