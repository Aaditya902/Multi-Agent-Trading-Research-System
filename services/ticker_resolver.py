"""
Resolves plain stock names/tickers to valid yfinance NSE/BSE symbols.
yfinance requires the ".NS" suffix for NSE-listed stocks.
"""

from __future__ import annotations

# ─── Known NSE ticker map ─────────────────────────────────────────────────────
# Key: what the user might type  →  Value: yfinance ticker
_NSE_TICKER_MAP: dict[str, str] = {
    # IT
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "INFOSYS": "INFY.NS",
    "HCLTECH": "HCLTECH.NS",
    "HCL": "HCLTECH.NS",
    "WIPRO": "WIPRO.NS",
    "TECHM": "TECHM.NS",
    "TECHMAHINDRA": "TECHM.NS",
    "MPHASIS": "MPHASIS.NS",
    "LTI": "LTIM.NS",
    "LTIM": "LTIM.NS",
    "COFORGE": "COFORGE.NS",

    # Banking & Finance
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "ICICI": "ICICIBANK.NS",
    "AXISBANK": "AXISBANK.NS",
    "AXIS": "AXISBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "KOTAK": "KOTAKBANK.NS",
    "SBI": "SBIN.NS",
    "SBIN": "SBIN.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "BANDHANBNK": "BANDHANBNK.NS",
    "PNB": "PNB.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "BAJAJFINANCE": "BAJFINANCE.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "HDFC": "HDFC.NS",

    # Energy & Oil
    "RELIANCE": "RELIANCE.NS",
    "ONGC": "ONGC.NS",
    "BPCL": "BPCL.NS",
    "IOC": "IOC.NS",
    "IOCL": "IOC.NS",
    "POWERGRID": "POWERGRID.NS",
    "NTPC": "NTPC.NS",
    "ADANIGREEN": "ADANIGREEN.NS",
    "ADANIPORTS": "ADANIPORTS.NS",
    "ADANIENT": "ADANIENT.NS",
    "ADANI": "ADANIENT.NS",
    "TATAPOWER": "TATAPOWER.NS",

    # Consumer & FMCG
    "HINDUNILVR": "HINDUNILVR.NS",
    "HUL": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "NESTLEIND": "NESTLEIND.NS",
    "NESTLE": "NESTLEIND.NS",
    "BRITANNIA": "BRITANNIA.NS",
    "DABUR": "DABUR.NS",
    "MARICO": "MARICO.NS",
    "GODREJCP": "GODREJCP.NS",
    "COLPAL": "COLPAL.NS",
    "TATACONSUM": "TATACONSUM.NS",

    # Auto
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATA": "TATAMOTORS.NS",
    "MARUTI": "MARUTI.NS",
    "M&M": "M&M.NS",
    "MM": "M&M.NS",
    "MAHINDRA": "M&M.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BAJAJAUTO": "BAJAJ-AUTO.NS",
    "EICHERMOT": "EICHERMOT.NS",
    "HEROMOOCO": "HEROMOTOCO.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",

    # Pharma
    "SUNPHARMA": "SUNPHARMA.NS",
    "DRREDDY": "DRREDDY.NS",
    "DRREDDYS": "DRREDDY.NS",
    "CIPLA": "CIPLA.NS",
    "DIVISLAB": "DIVISLAB.NS",
    "BIOCON": "BIOCON.NS",
    "LUPIN": "LUPIN.NS",
    "AUROPHARMA": "AUROPHARMA.NS",

    # Metals & Mining
    "TATASTEEL": "TATASTEEL.NS",
    "HINDALCO": "HINDALCO.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "SAIL": "SAIL.NS",
    "NMDC": "NMDC.NS",
    "VEDL": "VEDL.NS",
    "VEDANTA": "VEDL.NS",

    # Tech/Internet/New-Age
    "ZOMATO": "ZOMATO.NS",
    "NYKAA": "NYKAA.NS",
    "PAYTM": "PAYTM.NS",
    "POLICYBZR": "POLICYBZR.NS",
    "DELHIVERY": "DELHIVERY.NS",
    "IRCTC": "IRCTC.NS",

    # Indices (for market brief)
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
}


def resolve_ticker(user_input: str) -> str:
    """
    Convert a user-typed name/ticker to a yfinance-compatible symbol.

    Priority:
    1. Exact map lookup (case-insensitive)
    2. Append .NS if it looks like a bare NSE ticker
    3. Return as-is (let yfinance handle it)
    """
    key = user_input.strip().upper().replace(" ", "")
    if key in _NSE_TICKER_MAP:
        return _NSE_TICKER_MAP[key]

    # Already has exchange suffix
    if key.endswith(".NS") or key.endswith(".BO") or key.startswith("^"):
        return key

    # Default: assume NSE
    return f"{key}.NS"


def get_company_name(ticker: str) -> str:
    """Best-effort reverse lookup of company name from ticker."""
    _NAMES = {v: k for k, v in _NSE_TICKER_MAP.items()}
    return _NAMES.get(ticker.upper(), ticker.replace(".NS", "").replace(".BO", ""))


def get_nse_peers(ticker: str) -> list[str]:
    """Return known sector peers for major tickers."""
    _PEERS: dict[str, list[str]] = {
        "TCS.NS":        ["INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
        "INFY.NS":       ["TCS.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
        "HCLTECH.NS":    ["TCS.NS", "INFY.NS", "WIPRO.NS", "TECHM.NS"],
        "WIPRO.NS":      ["TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS"],
        "TECHM.NS":      ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],

        "HDFCBANK.NS":   ["ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "SBIN.NS"],
        "ICICIBANK.NS":  ["HDFCBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "SBIN.NS"],
        "AXISBANK.NS":   ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS"],
        "KOTAKBANK.NS":  ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "SBIN.NS"],
        "SBIN.NS":       ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "PNB.NS"],

        "RELIANCE.NS":   ["ONGC.NS", "BPCL.NS", "IOC.NS", "ADANIENT.NS"],

        "SUNPHARMA.NS":  ["DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS"],
        "DRREDDY.NS":    ["SUNPHARMA.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS"],
        "CIPLA.NS":      ["SUNPHARMA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS"],

        "TATAMOTORS.NS": ["MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
        "MARUTI.NS":     ["TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],

        "HINDUNILVR.NS": ["ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],
        "ITC.NS":        ["HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],

        "TATASTEEL.NS":  ["JSWSTEEL.NS", "HINDALCO.NS", "SAIL.NS", "VEDL.NS"],
    }
    return _PEERS.get(ticker.upper(), [])