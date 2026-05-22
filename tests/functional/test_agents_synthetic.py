"""Synthetic agent tests.

All external API calls are replaced with deterministic stubs so these tests
run without yfinance, NSE, NewsAPI, or Zerodha Kite connectivity.
Real Gemini LLM is used so the ReAct loop and tool-calling are exercised end-to-end.
"""
import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from src.agents.base import is_quota_error

pytestmark = pytest.mark.usefixtures("gemini_quota_ok")

_SKIP_ERRS = ("quota", "rate limit", "resource exhausted", "429", "resource_exhausted", "permission_denied", "403")


def _skip_if_api_error(e: Exception) -> None:
    """Skip the test if the error is a transient API quota/access issue."""
    msg = str(e).lower()
    if any(k in msg for k in _SKIP_ERRS):
        pytest.skip(f"Gemini API unavailable: {str(e)[:120]}")

from src.agents.news_analyst import run_news_analyst
from src.agents.technical_analyst import run_technical_analyst
from src.agents.portfolio_risk import run_portfolio_risk
from src.agents.options_analyst import run_options_analyst
from src.agents.orchestrator import run_orchestrator


# ---------------------------------------------------------------------------
# Synthetic tools — deterministic, no network I/O
# ---------------------------------------------------------------------------

@tool
def _news_stock(ticker: str, hours: int = 24, max_articles: int = 5) -> str:
    """Fetch recent news for a stock ticker."""
    data = {
        "RELIANCE": "[Reuters] Reliance Q4 net profit beats estimates by 8%; JioMart revenue +23% YoY (2026-05-17)",
        "TCS": "[Bloomberg] TCS Q4 guidance in-line; headcount additions flat (2026-05-17)",
    }
    return data.get(ticker, f"No recent news found for {ticker}")


@tool
def _news_sector(sector: str, hours: int = 24) -> str:
    """Fetch recent sector-wide news."""
    return "[ET] IT sector faces margin pressure from wage hikes (2026-05-17)"


@tool
def _news_macro(hours: int = 24) -> str:
    """Fetch recent macro-economic news relevant to Indian markets."""
    return "[RBI] RBI holds repo rate at 6.25%; GDP growth forecast at 6.8% (2026-05-17)"


@tool
def _price_snapshot(tickers: list[str]) -> str:
    """Fetch prior-day closing price snapshot for a list of tickers."""
    rows = {
        "RELIANCE": "RELIANCE: close=₹2850 (+1.2%) 52w_high=₹3010 52w_low=₹2200 ma20=₹2780 ma50=₹2700 ma200=₹2500",
        "TCS": "TCS: close=₹3600 (-0.5%) 52w_high=₹4100 52w_low=₹3100 ma20=₹3650 ma50=₹3580 ma200=₹3400",
    }
    return "\n".join(rows.get(t, f"{t}: data unavailable") for t in tickers)


@tool
def _intraday_snapshot(tickers: list[str]) -> str:
    """Fetch live intraday price snapshot for a list of tickers."""
    return "\n".join(f"{t}: ₹2855 (+0.8%), volume=1.2M" for t in tickers)


@tool
def _eod_snapshot(tickers: list[str]) -> str:
    """Fetch end-of-day OHLCV snapshot for a list of tickers."""
    return "\n".join(f"{t}: O=₹2820 H=₹2870 L=₹2800 C=₹2850 (+1.2%) vol=2.1M" for t in tickers)


@tool
def _index_snapshot() -> str:
    """Fetch current index levels for Nifty50, Sensex, S&P500, Nasdaq."""
    return "Nifty50: 24850 (+0.6%)\nSensex: 81500 (+0.5%)\nS&P500: 5400 (+0.3%)\nNasdaq: 17200 (+0.4%)"


@tool
def _market_breadth() -> str:
    """Fetch NSE market breadth — advances, declines, unchanged."""
    return "Advances: 1450 | Declines: 780 | Unchanged: 120"


@tool
def _fetch_holdings() -> str:
    """Fetch current Zerodha portfolio holdings."""
    return (
        "RELIANCE: qty=10, avg=₹2700, ltp=₹2850, pnl=+₹1500\n"
        "TCS: qty=5, avg=₹3450, ltp=₹3600, pnl=+₹750"
    )


@tool
def _fetch_positions() -> str:
    """Fetch open intraday positions from Zerodha."""
    return "No open intraday positions."


@tool
def _fetch_trades() -> str:
    """Fetch today's completed trades from Zerodha."""
    return "No completed trades today."


@tool
def _portfolio_pnl() -> str:
    """Calculate total portfolio P&L from Zerodha holdings."""
    return "Portfolio Value: ₹46500 | Cost: ₹44250 | Unrealized P&L: +₹2250 (+5.1%)"


@tool
def _fii_dii() -> str:
    """Fetch FII and DII net buy/sell figures from NSE."""
    return "FII Net: +₹1250 Cr | DII Net: -₹320 Cr"


@tool
def _options_chain(symbol: str) -> str:
    """Fetch NSE options chain for a stock symbol."""
    return (
        f"{symbol} Options (expiry: 2026-05-29, spot: ₹2850)\n"
        f"PCR: 0.85 (neutral) | CE OI: 4.2M | PE OI: 3.6M\n"
        f"Top CE resistance strikes: 2900, 3000\n"
        f"Top PE support strikes: 2800, 2750"
    )


@tool
def _index_options(index: str) -> str:
    """Fetch NSE options chain for an index (NIFTY or BANKNIFTY)."""
    return (
        f"{index} Options (expiry: 2026-05-29, spot: 24850)\n"
        f"PCR: 1.05 (neutral) | CE OI: 12M | PE OI: 12.6M\n"
        f"Top CE resistance strikes: 25000, 25200\n"
        f"Top PE support strikes: 24600, 24400"
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _tool_call_count(messages: list) -> int:
    return sum(1 for m in messages if isinstance(m, ToolMessage))


# ---------------------------------------------------------------------------
# News Analyst
# ---------------------------------------------------------------------------

@pytest.mark.functional
async def test_news_analyst_synthetic_tool_calls(morning_state, monkeypatch):
    """News analyst makes at least one tool call and returns non-empty analysis."""
    monkeypatch.setattr(
        "src.agents.news_analyst._TOOLS",
        [_news_stock, _news_sector, _news_macro],
    )
    try:
        result = await run_news_analyst(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    assert "news_analysis" in result
    assert isinstance(result["news_analysis"], str)
    assert len(result["news_analysis"]) > 50, f"Analysis too short: {result['news_analysis'][:200]}"

    n_tool_calls = _tool_call_count(result["messages"])
    assert n_tool_calls > 0, (
        f"Expected ≥1 ToolMessage but got 0 out of {len(result['messages'])} messages"
    )


@pytest.mark.functional
async def test_news_analyst_synthetic_sentiment(morning_state, monkeypatch):
    """News analyst output contains a sentiment word."""
    monkeypatch.setattr(
        "src.agents.news_analyst._TOOLS",
        [_news_stock, _news_sector, _news_macro],
    )
    try:
        result = await run_news_analyst(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise
    text = result["news_analysis"].lower()
    sentiments = ["bullish", "bearish", "neutral", "positive", "negative"]
    assert any(w in text for w in sentiments), (
        f"Expected sentiment in analysis: {text[:300]}"
    )


# ---------------------------------------------------------------------------
# Technical Analyst
# ---------------------------------------------------------------------------

@pytest.mark.functional
async def test_technical_analyst_synthetic_tool_calls(morning_state, monkeypatch):
    """Technical analyst makes at least one tool call and mentions a watchlist ticker."""
    monkeypatch.setattr(
        "src.agents.technical_analyst._TOOLS",
        [_price_snapshot, _intraday_snapshot, _eod_snapshot, _index_snapshot, _market_breadth],
    )
    try:
        result = await run_technical_analyst(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    assert "technical_analysis" in result
    assert len(result["technical_analysis"]) > 50, f"Analysis too short: {result['technical_analysis'][:200]}"

    n_tool_calls = _tool_call_count(result["messages"])
    assert n_tool_calls > 0, (
        f"Expected ≥1 ToolMessage but got 0 out of {len(result['messages'])} messages"
    )

    text = result["technical_analysis"]
    found = sum(1 for t in morning_state["watchlist"] if t in text)
    assert found >= 1, f"Expected at least one watchlist ticker in analysis: {text[:300]}"


@pytest.mark.functional
async def test_technical_analyst_synthetic_price_data(morning_state, monkeypatch):
    """Technical analyst output references price levels from synthetic data."""
    monkeypatch.setattr(
        "src.agents.technical_analyst._TOOLS",
        [_price_snapshot, _intraday_snapshot, _eod_snapshot, _index_snapshot, _market_breadth],
    )
    try:
        result = await run_technical_analyst(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise
    text = result["technical_analysis"]
    has_price = "₹" in text or any(w in text.lower() for w in ["ma", "close", "nifty", "support", "resistance"])
    assert has_price, f"Expected price/TA content in: {text[:300]}"


# ---------------------------------------------------------------------------
# Portfolio Risk Agent
# ---------------------------------------------------------------------------

@pytest.mark.functional
async def test_portfolio_risk_synthetic_tool_calls(morning_state, monkeypatch):
    """Portfolio agent makes at least one tool call and returns a portfolio summary."""
    monkeypatch.setattr(
        "src.agents.portfolio_risk._TOOLS",
        [_fetch_holdings, _fetch_positions, _fetch_trades, _portfolio_pnl, _fii_dii],
    )
    try:
        result = await run_portfolio_risk(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    assert "portfolio_analysis" in result
    assert len(result["portfolio_analysis"]) > 20, f"Analysis too short: {result['portfolio_analysis'][:200]}"

    n_tool_calls = _tool_call_count(result["messages"])
    assert n_tool_calls > 0, (
        f"Expected ≥1 ToolMessage but got 0 out of {len(result['messages'])} messages"
    )


@pytest.mark.functional
async def test_portfolio_risk_synthetic_has_pnl(morning_state, monkeypatch):
    """Portfolio agent output mentions P&L data from synthetic holdings."""
    monkeypatch.setattr(
        "src.agents.portfolio_risk._TOOLS",
        [_fetch_holdings, _fetch_positions, _fetch_trades, _portfolio_pnl, _fii_dii],
    )
    try:
        result = await run_portfolio_risk(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise
    text = result["portfolio_analysis"]
    has_financial = "₹" in text or any(w in text.lower() for w in ["pnl", "p&l", "reliance", "tcs", "holdings"])
    assert has_financial, f"Expected financial content in: {text[:300]}"


# ---------------------------------------------------------------------------
# Options Analyst
# ---------------------------------------------------------------------------

@pytest.mark.functional
async def test_options_analyst_synthetic_tool_calls(morning_state, monkeypatch):
    """Options analyst makes at least one tool call and returns options analysis."""
    monkeypatch.setattr(
        "src.agents.options_analyst._TOOLS",
        [_options_chain, _index_options],
    )
    try:
        result = await run_options_analyst(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    assert "options_analysis" in result
    assert len(result["options_analysis"]) > 20, f"Analysis too short: {result['options_analysis'][:200]}"

    n_tool_calls = _tool_call_count(result["messages"])
    assert n_tool_calls > 0, (
        f"Expected ≥1 ToolMessage but got 0 out of {len(result['messages'])} messages"
    )


@pytest.mark.functional
async def test_options_analyst_synthetic_pcr(morning_state, monkeypatch):
    """Options analyst output references PCR from synthetic data."""
    monkeypatch.setattr(
        "src.agents.options_analyst._TOOLS",
        [_options_chain, _index_options],
    )
    try:
        result = await run_options_analyst(morning_state)
    except Exception as e:
        _skip_if_api_error(e)
        raise
    text = result["options_analysis"].lower()
    has_options_content = any(w in text for w in ["pcr", "put", "call", "oi", "strike", "support", "resistance"])
    assert has_options_content, f"Expected options content in: {text[:300]}"


# ---------------------------------------------------------------------------
# Orchestrator — no tools, uses seeded sub-agent outputs
# ---------------------------------------------------------------------------

@pytest.mark.functional
async def test_orchestrator_synthetic_final_analysis(morning_state):
    """Orchestrator produces a non-trivial final_analysis from seeded inputs."""
    state = dict(morning_state)
    state["news_analysis"] = (
        "RELIANCE: Bullish — Q4 net profit beat estimates by 8%; JioMart revenue +23% YoY.\n"
        "TCS: Neutral — Q4 guidance in-line; headcount additions flat."
    )
    state["technical_analysis"] = (
        "RELIANCE: close=₹2850 (+1.2%) 52w_high=₹3010 ma20=₹2780 ma50=₹2700 — above all MAs, bullish.\n"
        "TCS: close=₹3600 (-0.5%) 52w_high=₹4100 ma20=₹3650 — below MA20, slight weakness.\n"
        "Nifty50: 24850 (+0.6%). Market breadth positive: 1450 advances vs 780 declines."
    )
    state["portfolio_analysis"] = (
        "RELIANCE: 10 units @ ₹2700 avg, ltp=₹2850, pnl=+₹1500 (+5.6%).\n"
        "TCS: 5 units @ ₹3450 avg, ltp=₹3600, pnl=+₹750 (+4.3%).\n"
        "Portfolio Value: ₹46500 | Unrealized P&L: +₹2250 (+5.1%).\n"
        "FII Net: +₹1250 Cr — foreign buying supportive."
    )
    state["options_analysis"] = (
        "NIFTY PCR: 1.05 (neutral) — support at 24600, resistance at 25000.\n"
        "RELIANCE PCR: 0.85 (neutral) — PE support at 2800, CE resistance at 2900."
    )

    try:
        result = await run_orchestrator(state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    assert "final_analysis" in result
    assert len(result["final_analysis"]) > 100, f"Analysis too short: {result['final_analysis'][:300]}"
    assert len(result["messages"]) > 0


@pytest.mark.functional
async def test_orchestrator_synthetic_predictions_structure(morning_state):
    """Orchestrator predictions dict has the expected schema."""
    state = dict(morning_state)
    state["news_analysis"] = "RELIANCE: Bullish — earnings beat. TCS: Neutral — flat guidance."
    state["technical_analysis"] = "RELIANCE close=₹2850 (+1.2%) above MA20. TCS close=₹3600 (-0.5%) below MA20."
    state["portfolio_analysis"] = "RELIANCE 10@₹2700 pnl=+₹1500. Portfolio P&L: +5.1%."
    state["options_analysis"] = "NIFTY PCR: 1.05 neutral. RELIANCE PCR: 0.85 neutral."

    try:
        result = await run_orchestrator(state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    predictions = result["predictions"]
    assert isinstance(predictions, dict), f"predictions is not a dict: {type(predictions)}"
    assert "stocks" in predictions, f"predictions missing 'stocks' key: {predictions}"
    assert isinstance(predictions["stocks"], list)

    for stock in predictions["stocks"]:
        assert "ticker" in stock, f"stock entry missing 'ticker': {stock}"
        assert stock.get("direction") in ("BUY", "SELL", "HOLD", None), (
            f"Unexpected direction value: {stock.get('direction')}"
        )


@pytest.mark.functional
async def test_orchestrator_synthetic_final_analysis_content(morning_state):
    """Orchestrator final_analysis mentions watchlist stocks and market signals."""
    state = dict(morning_state)
    state["news_analysis"] = "RELIANCE: Bullish earnings beat. TCS: Neutral."
    state["technical_analysis"] = "RELIANCE: strong uptrend, above all MAs. TCS: mild weakness."
    state["portfolio_analysis"] = "RELIANCE P&L +5.6%. TCS P&L +4.3%. Overall positive."
    state["options_analysis"] = "PCR neutral across Nifty and portfolio stocks."

    try:
        result = await run_orchestrator(state)
    except Exception as e:
        _skip_if_api_error(e)
        raise

    text = result["final_analysis"].lower()
    has_market_content = any(w in text for w in [
        "reliance", "tcs", "bullish", "bearish", "buy", "sell", "hold",
        "market", "analysis", "risk", "signal",
    ])
    assert has_market_content, f"final_analysis lacks market content: {text[:400]}"
