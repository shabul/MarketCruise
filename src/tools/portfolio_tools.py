import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool


_cache_path = Path("data/portfolio_cache.json")
_kite_client = None
_kite_connected = False


def _init_kite():
    global _kite_client, _kite_connected
    if _kite_client is not None:
        return
    api_key = os.environ.get("KITE_API_KEY")
    access_token = os.environ.get("KITE_ACCESS_TOKEN")
    if not api_key or not access_token:
        return
    try:
        from kiteconnect import KiteConnect
        _kite_client = KiteConnect(api_key=api_key)
        _kite_client.set_access_token(access_token)
        _kite_client.profile()
        _kite_connected = True
    except Exception:
        _kite_client = None
        _kite_connected = False


def _load_cache() -> dict:
    if _cache_path.exists():
        try:
            return json.loads(_cache_path.read_text())
        except Exception:
            pass
    return {"holdings": [], "positions": []}


def _write_cache(data: dict) -> None:
    _cache_path.parent.mkdir(parents=True, exist_ok=True)
    _cache_path.write_text(json.dumps(data, indent=2))


@tool
def fetch_holdings() -> str:
    """Fetch current stock holdings from Zerodha Kite. Falls back to cached data if API is unavailable."""
    _init_kite()
    if _kite_connected and _kite_client:
        try:
            holdings = _kite_client.holdings()
            result = [
                h for h in holdings if h.get("quantity", 0) > 0
            ]
            rows = [
                f"{h['tradingsymbol']}: qty={h['quantity']}, avg=₹{h['average_price']:.2f}, "
                f"ltp=₹{h['last_price']:.2f}, pnl=₹{(h['last_price']-h['average_price'])*h['quantity']:+.2f}"
                for h in result
            ]
            cache = _load_cache()
            cache["holdings"] = [
                {"ticker": h["tradingsymbol"], "quantity": h["quantity"],
                 "avg_price": h["average_price"], "last_price": h["last_price"]}
                for h in result
            ]
            _write_cache(cache)
            return "\n".join(rows) if rows else "No holdings found."
        except Exception:
            pass
    holdings = _load_cache().get("holdings", [])
    if not holdings:
        return "No holdings data available (Kite API disconnected, no cache)."
    rows = [
        f"{h['ticker']}: qty={h['quantity']}, avg=₹{h.get('avg_price',0):.2f} [cached]"
        for h in holdings
    ]
    return "\n".join(rows)


@tool
def fetch_positions() -> str:
    """Fetch today's open intraday positions from Zerodha Kite."""
    _init_kite()
    if _kite_connected and _kite_client:
        try:
            pos = _kite_client.positions()
            day = [p for p in pos.get("day", []) if p.get("quantity", 0) != 0]
            rows = [
                f"{p['tradingsymbol']}: qty={p['quantity']}, avg=₹{p['average_price']:.2f}, "
                f"ltp=₹{p['last_price']:.2f}, pnl=₹{p['pnl']:+.2f}"
                for p in day
            ]
            return "\n".join(rows) if rows else "No open intraday positions."
        except Exception:
            pass
    return "Positions unavailable (Kite API disconnected)."


@tool
def fetch_todays_trades() -> str:
    """Fetch completed buy/sell orders from today via Zerodha Kite."""
    _init_kite()
    if _kite_connected and _kite_client:
        try:
            orders = _kite_client.orders()
            today = date.today().isoformat()
            completed = [
                o for o in orders
                if o.get("status") == "COMPLETE"
                and str(o.get("exchange_update_timestamp", "")).startswith(today)
            ]
            rows = [
                f"{o['transaction_type']} {o['tradingsymbol']}: qty={o['filled_quantity']} "
                f"@ ₹{o['average_price']:.2f}"
                for o in completed
            ]
            return "\n".join(rows) if rows else "No completed trades today."
        except Exception:
            pass
    return "Trade data unavailable (Kite API disconnected)."


@tool
def calculate_portfolio_pnl() -> str:
    """Calculate current portfolio P&L from holdings data."""
    _init_kite()
    holdings_text = fetch_holdings.invoke({})
    if _kite_connected and _kite_client:
        try:
            holdings = _kite_client.holdings()
            total_value = sum(h["last_price"] * h["quantity"] for h in holdings if h.get("quantity", 0) > 0)
            total_cost = sum(h["average_price"] * h["quantity"] for h in holdings if h.get("quantity", 0) > 0)
            unrealized = total_value - total_cost
            pct = (unrealized / total_cost * 100) if total_cost else 0
            return (
                f"Portfolio Value: ₹{total_value:,.2f} | Cost: ₹{total_cost:,.2f} | "
                f"Unrealized P&L: ₹{unrealized:+,.2f} ({pct:+.2f}%)"
            )
        except Exception:
            pass
    return "P&L calculation unavailable."
