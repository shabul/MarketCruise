from datetime import datetime
from typing import Annotated

import pandas as pd
import yfinance as yf
from langchain_core.tools import tool


def _nse(ticker: str) -> str:
    return ticker if ticker.endswith(".NS") else f"{ticker}.NS"


@tool
def fetch_price_snapshot(tickers: Annotated[list[str], "List of NSE ticker symbols"]) -> str:
    """Fetch prior-day close price, 52-week high/low, and 20/50/200 day moving averages for NSE stocks."""
    symbols = [_nse(t) for t in tickers]
    rows = []
    for sym, ticker in zip(symbols, tickers):
        try:
            hist = yf.download(sym, period="1y", interval="1d", progress=False, auto_adjust=True)
            if isinstance(hist.columns, pd.MultiIndex):
                close = hist["Close"][sym]
            else:
                close = hist["Close"]
            close = close.dropna()
            if close.empty:
                continue
            latest = float(close.iloc[-1])
            rows.append(
                f"{ticker}: close=₹{latest:.2f}, 52w_high=₹{close.max():.2f}, "
                f"52w_low=₹{close.min():.2f}, ma20=₹{close.tail(20).mean():.2f}, "
                f"ma50=₹{close.tail(50).mean():.2f}, ma200=₹{close.tail(200).mean():.2f}, "
                f"from_52w_high={((latest/close.max()-1)*100):.1f}%"
            )
        except Exception as e:
            rows.append(f"{ticker}: data unavailable ({e})")
    return "\n".join(rows) if rows else "No data fetched."


@tool
def fetch_intraday_snapshot(tickers: Annotated[list[str], "List of NSE ticker symbols"]) -> str:
    """Fetch current intraday price, % change, and volume for NSE stocks."""
    rows = []
    for ticker in tickers:
        sym = _nse(ticker)
        try:
            hist = yf.download(sym, period="2d", interval="5m", progress=False, auto_adjust=True)
            if hist.empty:
                continue
            today = datetime.now().date()
            if isinstance(hist.columns, pd.MultiIndex):
                close_col = hist["Close"][sym]
                vol_col = hist["Volume"][sym]
            else:
                close_col = hist["Close"]
                vol_col = hist["Volume"]
            today_close = close_col[close_col.index.date == today]
            prev_close_vals = close_col[close_col.index.date < today]
            if today_close.empty or prev_close_vals.empty:
                continue
            current = float(today_close.iloc[-1])
            prev_close = float(prev_close_vals.iloc[-1])
            volume = int(vol_col[vol_col.index.date == today].sum())
            pct = (current / prev_close - 1) * 100
            rows.append(f"{ticker}: ₹{current:.2f} ({pct:+.2f}%), volume={volume:,}")
        except Exception as e:
            rows.append(f"{ticker}: unavailable ({e})")
    return "\n".join(rows) if rows else "No intraday data."


@tool
def fetch_eod_snapshot(tickers: Annotated[list[str], "List of NSE ticker symbols"]) -> str:
    """Fetch today's end-of-day OHLCV and % change for NSE stocks."""
    rows = []
    for ticker in tickers:
        sym = _nse(ticker)
        try:
            hist = yf.download(sym, period="5d", interval="1d", progress=False, auto_adjust=True)
            if len(hist) < 2:
                continue
            if isinstance(hist.columns, pd.MultiIndex):
                today_row = {c: float(hist[c][sym].iloc[-1]) for c in ["Open","High","Low","Close","Volume"]}
                prev_close = float(hist["Close"][sym].iloc[-2])
            else:
                today_row = {c: float(hist[c].iloc[-1]) for c in ["Open","High","Low","Close","Volume"]}
                prev_close = float(hist["Close"].iloc[-2])
            pct = (today_row["Close"] / prev_close - 1) * 100
            rows.append(
                f"{ticker}: O=₹{today_row['Open']:.2f} H=₹{today_row['High']:.2f} "
                f"L=₹{today_row['Low']:.2f} C=₹{today_row['Close']:.2f} "
                f"({pct:+.2f}%) vol={int(today_row['Volume']):,}"
            )
        except Exception as e:
            rows.append(f"{ticker}: unavailable ({e})")
    return "\n".join(rows) if rows else "No EOD data."


@tool
def fetch_index_snapshot() -> str:
    """Fetch latest values for Nifty50, Sensex, S&P 500, and Nasdaq."""
    indices = {"Nifty50": "^NSEI", "Sensex": "^BSESN", "SP500": "^GSPC", "Nasdaq": "^IXIC"}
    rows = []
    for name, sym in indices.items():
        try:
            hist = yf.download(sym, period="5d", interval="1d", progress=False, auto_adjust=True)
            if len(hist) < 2:
                continue
            if isinstance(hist.columns, pd.MultiIndex):
                latest = float(hist["Close"][sym].iloc[-1])
                prev = float(hist["Close"][sym].iloc[-2])
            else:
                latest = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
            pct = (latest / prev - 1) * 100
            rows.append(f"{name}: {latest:,.2f} ({pct:+.2f}%)")
        except Exception as e:
            rows.append(f"{name}: unavailable ({e})")
    return "\n".join(rows) if rows else "Index data unavailable."
