"""
Corporate Actions Agent
Analyses recent dividends, stock splits, bonus issues, buybacks,
promoter holding changes, and upcoming earnings events via yfinance.
"""

from __future__ import annotations
from datetime import datetime, timedelta

import pandas as pd

from logging_config import logger
from schemas.analysis_schemas import CorporateOutput, CorporateAction
from tools.yfinance_tool import (
    fetch_actions, fetch_dividends, fetch_splits,
    fetch_major_holders, fetch_calendar, fetch_stock_info,
)
from services.ticker_resolver import resolve_ticker, get_company_name

# Look-back window for corporate actions
_LOOKBACK_DAYS = 365


def run_corporate_agent(ticker: str) -> CorporateOutput:
    """
    Main entry point for the Corporate Actions Agent.

    Steps:
      1. Resolve ticker
      2. Fetch dividends, splits, calendar, major holders
      3. Parse each into typed CorporateAction entries
      4. Score overall impact and generate summary

    Args:
        ticker: Raw user-supplied ticker e.g. "INFY"

    Returns:
        CorporateOutput — fully populated
    """
    yf_ticker    = resolve_ticker(ticker)
    company_name = get_company_name(yf_ticker)

    logger.info(f"[CorporateAgent] Starting for {company_name} ({yf_ticker})")

    actions: list[CorporateAction] = []

    # ── 1. Dividends ──────────────────────────────────────────────────────────
    actions.extend(_parse_dividends(fetch_dividends(yf_ticker)))

    # ── 2. Stock Splits ───────────────────────────────────────────────────────
    actions.extend(_parse_splits(fetch_splits(yf_ticker)))

    # ── 3. Upcoming Earnings Calendar ─────────────────────────────────────────
    actions.extend(_parse_calendar(fetch_calendar(yf_ticker)))

    # ── 4. Promoter / Major Holder Changes ────────────────────────────────────
    actions.extend(_parse_holders(fetch_major_holders(yf_ticker), yf_ticker))

    # ── 5. Buyback / Bonus check via info fields ───────────────────────────────
    actions.extend(_parse_buyback_bonus(fetch_stock_info(yf_ticker)))

    # ── Deduplicate and sort by date (most recent first) ──────────────────────
    actions = _sort_actions(actions)

    # ── Overall impact score ──────────────────────────────────────────────────
    overall_impact = _score_overall_impact(actions)
    summary        = _build_summary(ticker, actions, overall_impact)

    output = CorporateOutput(
        stock=ticker.upper(),
        corporate_actions=actions,
        impact=overall_impact,
        summary=summary,
    )

    logger.info(
        f"[CorporateAgent] Done for {yf_ticker} — "
        f"{len(actions)} actions found, overall_impact={overall_impact}"
    )
    return output


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_dividends(divs: pd.Series) -> list[CorporateAction]:
    """Parse dividend history into CorporateActions for the last 12 months."""
    result = []
    if divs is None or divs.empty:
        return result

    cutoff = datetime.utcnow() - timedelta(days=_LOOKBACK_DAYS)
    recent = divs[divs.index >= pd.Timestamp(cutoff, tz="UTC")]

    for date, amount in recent.items():
        result.append(CorporateAction(
            action_type="Dividend",
            date=date.strftime("%Y-%m-%d"),
            details=f"Dividend of ₹{amount:.2f} per share declared.",
            impact="Positive",
        ))

    if not recent.empty:
        # Check if dividends are growing
        if len(divs) >= 2:
            latest  = float(divs.iloc[-1])
            prev    = float(divs.iloc[-2])
            if latest > prev * 1.05:
                result.append(CorporateAction(
                    action_type="Announcement",
                    date=divs.index[-1].strftime("%Y-%m-%d"),
                    details=f"Dividend grew {((latest/prev)-1)*100:.1f}% YoY — signals strong cash generation.",
                    impact="Positive",
                ))

    return result


def _parse_splits(splits: pd.Series) -> list[CorporateAction]:
    """Parse stock split history into CorporateActions."""
    result = []
    if splits is None or splits.empty:
        return result

    cutoff = datetime.utcnow() - timedelta(days=_LOOKBACK_DAYS * 2)  # 2yr window for splits
    recent = splits[splits.index >= pd.Timestamp(cutoff, tz="UTC")]

    for date, ratio in recent.items():
        if ratio > 1:
            action_type = "Stock Split"
            details     = f"Stock split in ratio {ratio:.0f}:1 — share price adjusted proportionally."
            impact      = "Positive"   # typically bullish signal (accessibility, liquidity)
        else:
            action_type = "Reverse Split"
            details     = f"Reverse stock split {ratio}:1 — consolidation of shares."
            impact      = "Negative"

        result.append(CorporateAction(
            action_type=action_type,
            date=date.strftime("%Y-%m-%d"),
            details=details,
            impact=impact,
        ))

    return result


def _parse_calendar(calendar: dict) -> list[CorporateAction]:
    """Parse upcoming earnings dates from yfinance calendar."""
    result = []
    if not calendar:
        return result

    # yfinance calendar keys vary by version; handle both
    earnings_date = (
        calendar.get("Earnings Date")
        or calendar.get("earningsDate")
        or calendar.get("earnings_date")
    )

    if earnings_date:
        # Can be a list of dates or a single date
        if isinstance(earnings_date, list):
            earnings_date = earnings_date[0]

        try:
            if hasattr(earnings_date, "strftime"):
                date_str = earnings_date.strftime("%Y-%m-%d")
            else:
                date_str = str(earnings_date)[:10]

            result.append(CorporateAction(
                action_type="Earnings",
                date=date_str,
                details=f"Upcoming earnings announcement scheduled on {date_str}.",
                impact="Neutral",
            ))
        except Exception as e:
            logger.debug(f"[CorporateAgent] Calendar date parse error: {e}")

    # EPS estimates
    eps_current = calendar.get("EPS Estimate") or calendar.get("epsEstimate")
    if eps_current is not None:
        result.append(CorporateAction(
            action_type="Announcement",
            date="upcoming",
            details=f"Analyst consensus EPS estimate: ₹{eps_current:.2f} for upcoming quarter.",
            impact="Neutral",
        ))

    return result


def _parse_holders(holders_df: pd.DataFrame, ticker: str) -> list[CorporateAction]:
    """
    Parse major holder data to flag promoter concentration.
    yfinance returns a 2-column DataFrame (Value, %) for major holders.
    """
    result = []
    if holders_df is None or holders_df.empty:
        return result

    try:
        # Convert to dict for easier access
        holders_dict: dict = {}
        for _, row in holders_df.iterrows():
            try:
                pct_str = str(row.iloc[0])
                label   = str(row.iloc[1]).lower()
                pct_val = float(pct_str.strip("%")) if "%" in pct_str else float(pct_str)
                holders_dict[label] = pct_val
            except Exception:
                continue

        insider_pct = holders_dict.get("% held by insiders", 0.0)
        inst_pct    = holders_dict.get("% held by institutions", 0.0)

        if insider_pct > 0:
            impact = "Positive" if insider_pct > 50 else "Neutral"
            result.append(CorporateAction(
                action_type="Promoter Holding",
                date=None,
                details=f"Promoter/insider holding at {insider_pct:.1f}% — {'high conviction by management' if insider_pct > 50 else 'moderate insider stake'}.",
                impact=impact,
            ))

        if inst_pct > 0:
            result.append(CorporateAction(
                action_type="Institutional Holding",
                date=None,
                details=f"Institutional ownership at {inst_pct:.1f}%.",
                impact="Positive" if inst_pct > 30 else "Neutral",
            ))

    except Exception as e:
        logger.debug(f"[CorporateAgent] Holders parse error for {ticker}: {e}")

    return result


def _parse_buyback_bonus(info: dict) -> list[CorporateAction]:
    """
    Infer buyback/bonus signals from yfinance info fields.
    yfinance doesn't have a direct buyback API; we infer from shares outstanding change.
    """
    result = []
    if not info:
        return result

    # Share buyback signal: float shares < shares outstanding
    float_shares     = info.get("floatShares")
    shares_outstg    = info.get("sharesOutstanding")
    shares_short     = info.get("sharesShort")

    if float_shares and shares_outstg:
        try:
            buyback_ratio = 1 - (float_shares / shares_outstg)
            if buyback_ratio > 0.05:
                result.append(CorporateAction(
                    action_type="Buyback",
                    date=None,
                    details=(
                        f"Approx. {buyback_ratio:.1%} of shares held by company/promoters — "
                        f"possible buyback or treasury shares. Reduces float, positive for EPS."
                    ),
                    impact="Positive",
                ))
        except Exception:
            pass

    # Short interest signal
    if shares_short and shares_outstg:
        try:
            short_ratio = shares_short / shares_outstg
            if short_ratio > 0.05:
                result.append(CorporateAction(
                    action_type="Announcement",
                    date=None,
                    details=(
                        f"Short interest at {short_ratio:.1%} of shares outstanding — "
                        f"elevated bearish positioning by institutions."
                    ),
                    impact="Negative",
                ))
        except Exception:
            pass

    # Payout ratio — signals bonus issue potential
    payout = info.get("payoutRatio")
    if payout is not None and 0 < payout < 0.3:
        result.append(CorporateAction(
            action_type="Announcement",
            date=None,
            details=(
                f"Low dividend payout ratio of {payout:.1%} — "
                f"company retains significant earnings. Bonus issue or special dividend possible."
            ),
            impact="Positive",
        ))

    return result


# ── Scoring and summary helpers ───────────────────────────────────────────────

def _sort_actions(actions: list[CorporateAction]) -> list[CorporateAction]:
    """Sort by date descending; actions with no date go last."""
    def sort_key(a: CorporateAction) -> str:
        return a.date or "0000-00-00"
    return sorted(actions, key=sort_key, reverse=True)


def _score_overall_impact(actions: list[CorporateAction]) -> str:
    """Tally positive/negative actions to determine overall impact."""
    if not actions:
        return "Neutral"

    pos = sum(1 for a in actions if a.impact == "Positive")
    neg = sum(1 for a in actions if a.impact == "Negative")

    if pos > neg + 1:
        return "Positive"
    elif neg > pos + 1:
        return "Negative"
    return "Neutral"


def _build_summary(
    ticker: str,
    actions: list[CorporateAction],
    overall_impact: str,
) -> str:
    if not actions:
        return (
            f"No significant corporate actions identified for {ticker.upper()} "
            f"in the review period. Monitor upcoming earnings announcements."
        )

    types_found = list(dict.fromkeys(a.action_type for a in actions))  # preserve order, dedup
    types_str   = ", ".join(types_found[:4])

    dividends = [a for a in actions if a.action_type == "Dividend"]
    splits    = [a for a in actions if a.action_type in ("Stock Split", "Reverse Split")]
    earnings  = [a for a in actions if a.action_type == "Earnings"]

    parts = [f"{len(actions)} corporate action(s) identified: {types_str}."]

    if dividends:
        parts.append(f"Recent dividend activity ({len(dividends)} payment(s)) signals healthy cash flows.")
    if splits:
        parts.append(f"Stock split/restructuring detected — check ratio and date for context.")
    if earnings:
        parts.append(f"Earnings event upcoming — expect heightened price volatility around the date.")

    parts.append(f"Overall corporate action impact: {overall_impact}.")
    return " ".join(parts)