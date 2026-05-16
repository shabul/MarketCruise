from typing import Annotated

import requests
from langchain_core.tools import tool

_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com",
}

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_NSE_HEADERS)
        try:
            _session.get("https://www.nseindia.com", timeout=10)
        except Exception:
            pass
    return _session


def _parse_options_chain(data: dict, label: str) -> str:
    records = data.get("records", {})
    expiry_dates = records.get("expiryDates", [])
    nearest_expiry = expiry_dates[0] if expiry_dates else None
    underlying = records.get("underlyingValue", "N/A")

    ce_oi: dict[float, int] = {}
    pe_oi: dict[float, int] = {}
    for row in records.get("data", []):
        if row.get("expiryDate") != nearest_expiry:
            continue
        strike = row.get("strikePrice", 0)
        if "CE" in row:
            ce_oi[strike] = row["CE"].get("openInterest", 0)
        if "PE" in row:
            pe_oi[strike] = row["PE"].get("openInterest", 0)

    total_ce = sum(ce_oi.values())
    total_pe = sum(pe_oi.values())
    pcr = round(total_pe / total_ce, 2) if total_ce else 0
    top_ce = sorted(ce_oi.items(), key=lambda x: x[1], reverse=True)[:3]
    top_pe = sorted(pe_oi.items(), key=lambda x: x[1], reverse=True)[:3]

    lines = [
        f"{label} Options (expiry: {nearest_expiry}, spot: {underlying})",
        f"PCR: {pcr} ({'bearish hedging' if pcr < 0.7 else 'bullish' if pcr > 1.2 else 'neutral'})"
        f" | CE OI: {total_ce:,} | PE OI: {total_pe:,}",
        f"Top CE resistance strikes: {', '.join(str(int(s)) for s, _ in top_ce)}",
        f"Top PE support strikes: {', '.join(str(int(s)) for s, _ in top_pe)}",
    ]
    return "\n".join(lines)


@tool
def fetch_options_chain(
    symbol: Annotated[str, "NSE stock symbol (e.g. RELIANCE, TCS)"],
) -> str:
    """
    Fetch options chain summary for an NSE stock: PCR, top OI strikes, support/resistance.
    Falls back gracefully if NSE API is unavailable.
    """
    try:
        resp = _get_session().get(
            f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}",
            timeout=10,
        )
        resp.raise_for_status()
        return _parse_options_chain(resp.json(), symbol)
    except Exception as e:
        return f"{symbol} options data unavailable: {e}"


@tool
def fetch_index_options(
    index: Annotated[str, "Index name: NIFTY or BANKNIFTY"],
) -> str:
    """
    Fetch options chain summary for Nifty or BankNifty index options.
    Falls back gracefully if NSE API is unavailable.
    """
    try:
        resp = _get_session().get(
            f"https://www.nseindia.com/api/option-chain-indices?symbol={index}",
            timeout=10,
        )
        resp.raise_for_status()
        return _parse_options_chain(resp.json(), index)
    except Exception as e:
        return f"{index} index options unavailable: {e}"
