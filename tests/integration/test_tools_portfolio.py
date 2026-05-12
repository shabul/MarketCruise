"""Integration tests for Zerodha Kite portfolio tools."""
import os
import pytest
from src.tools.portfolio_tools import (
    fetch_holdings,
    fetch_positions,
    fetch_todays_trades,
    calculate_portfolio_pnl,
)


@pytest.mark.integration
def test_fetch_holdings_returns_string():
    result = fetch_holdings.invoke({})
    assert isinstance(result, str)
    assert len(result) > 5


@pytest.mark.integration
def test_fetch_holdings_with_kite_token():
    if not os.environ.get("KITE_ACCESS_TOKEN"):
        pytest.skip("KITE_ACCESS_TOKEN not set")
    result = fetch_holdings.invoke({})
    # Either real holdings data or "No holdings found"
    has_holdings = "₹" in result or "qty=" in result
    no_holdings = "No holdings" in result or "unavailable" in result.lower()
    assert has_holdings or no_holdings, f"Unexpected holdings response: {result[:200]}"


@pytest.mark.integration
def test_fetch_holdings_cache_fallback(monkeypatch):
    """If token is missing, falls back to cache (or returns unavailable)."""
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)
    # Reset the global kite state so it re-initializes
    import src.tools.portfolio_tools as pt
    pt._kite_client = None
    pt._kite_connected = False
    result = fetch_holdings.invoke({})
    assert isinstance(result, str)
    assert len(result) > 0
    # Restore
    pt._kite_client = None
    pt._kite_connected = False


@pytest.mark.integration
def test_fetch_positions_returns_string():
    result = fetch_positions.invoke({})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_fetch_todays_trades_returns_string():
    result = fetch_todays_trades.invoke({})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_calculate_pnl_returns_string():
    result = calculate_portfolio_pnl.invoke({})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_pnl_contains_rupee_or_unavailable():
    result = calculate_portfolio_pnl.invoke({})
    has_value = "₹" in result or "Portfolio Value" in result
    unavailable = "unavailable" in result.lower()
    assert has_value or unavailable, f"Unexpected P&L response: {result}"


@pytest.mark.integration
def test_all_portfolio_tools_never_raise():
    """Verify all portfolio tools return strings and don't raise."""
    try:
        r1 = fetch_holdings.invoke({})
        r2 = fetch_positions.invoke({})
        r3 = fetch_todays_trades.invoke({})
        r4 = calculate_portfolio_pnl.invoke({})
        for r in [r1, r2, r3, r4]:
            assert isinstance(r, str)
    except Exception as e:
        pytest.fail(f"Portfolio tool raised instead of returning error string: {e}")
