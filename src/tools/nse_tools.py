from datetime import date
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


@tool
def fetch_fii_dii() -> str:
    """Fetch latest FII and DII provisional net buy/sell data from NSE."""
    try:
        resp = _get_session().get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        parts = []
        for entry in data:
            cat = entry.get("category", "")
            if "FII" in cat.upper():
                parts.append(f"FII Net: ₹{entry.get('netVal')} Cr")
            elif "DII" in cat.upper():
                parts.append(f"DII Net: ₹{entry.get('netVal')} Cr")
        return " | ".join(parts) if parts else "FII/DII data unavailable."
    except Exception as e:
        return f"FII/DII fetch failed: {e}"


@tool
def fetch_market_breadth() -> str:
    """Fetch NSE market breadth: number of advancing, declining, and unchanged stocks."""
    try:
        resp = _get_session().get(
            "https://www.nseindia.com/api/market-data-pre-open?key=NIFTY", timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        advances = data.get("advances", "N/A")
        declines = data.get("declines", "N/A")
        unchanged = data.get("unchanged", "N/A")
        return f"Advances: {advances} | Declines: {declines} | Unchanged: {unchanged}"
    except Exception as e:
        return f"Market breadth unavailable: {e}"


@tool
def fetch_corporate_events(
    tickers: Annotated[list[str], "List of NSE ticker symbols to check for upcoming events"],
) -> str:
    """Fetch upcoming corporate events (earnings, results, dividends, board meetings) for given stocks."""
    try:
        resp = _get_session().get("https://www.nseindia.com/api/event-calendar", timeout=10)
        resp.raise_for_status()
        events = resp.json()
        today = date.today().isoformat()
        ticker_set = set(tickers)
        lines = []
        for ev in events:
            if ev.get("symbol") in ticker_set and ev.get("date", "") >= today:
                lines.append(f"- {ev['symbol']}: {ev.get('purpose','')} on {ev.get('date','')}")
        return "\n".join(lines) if lines else "No upcoming corporate events for selected stocks."
    except Exception as e:
        return f"Corporate events fetch failed: {e}"
