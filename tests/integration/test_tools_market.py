"""Integration tests for market data tools — real yfinance calls."""
import pytest
from src.tools.market_tools import (
    fetch_price_snapshot,
    fetch_intraday_snapshot,
    fetch_eod_snapshot,
    fetch_index_snapshot,
)


@pytest.mark.integration
def test_price_snapshot_returns_data():
    result = fetch_price_snapshot.invoke({"tickers": ["RELIANCE", "TCS"]})
    assert "RELIANCE" in result
    assert "close=₹" in result
    assert "52w_high" in result
    assert "ma20" in result


@pytest.mark.integration
def test_price_snapshot_single_ticker():
    result = fetch_price_snapshot.invoke({"tickers": ["INFY"]})
    assert "INFY" in result
    assert "₹" in result


@pytest.mark.integration
def test_price_snapshot_invalid_ticker():
    result = fetch_price_snapshot.invoke({"tickers": ["INVALIDTICKER999XYZ"]})
    assert "unavailable" in result.lower() or "No data fetched" in result


@pytest.mark.integration
def test_price_snapshot_mixed_valid_invalid():
    result = fetch_price_snapshot.invoke({"tickers": ["TCS", "INVALIDXXX"]})
    assert "TCS" in result
    # TCS should have data; invalid ticker should mention unavailability or be absent


@pytest.mark.integration
def test_eod_snapshot_returns_data():
    result = fetch_eod_snapshot.invoke({"tickers": ["RELIANCE", "TCS"]})
    # Should have OHLCV format or "unavailable" (market may be closed)
    assert isinstance(result, str)
    assert len(result) > 5


@pytest.mark.integration
def test_eod_snapshot_format():
    result = fetch_eod_snapshot.invoke({"tickers": ["TCS"]})
    # Either real OHLCV data or graceful fallback
    assert "TCS" in result or "No EOD data" in result


@pytest.mark.integration
def test_intraday_snapshot_returns_string():
    result = fetch_intraday_snapshot.invoke({"tickers": ["RELIANCE"]})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_index_snapshot_returns_all_indices():
    result = fetch_index_snapshot.invoke({})
    # At least one index should be present
    assert any(idx in result for idx in ["Nifty50", "Sensex", "SP500", "Nasdaq"])


@pytest.mark.integration
def test_index_snapshot_contains_values():
    result = fetch_index_snapshot.invoke({})
    assert isinstance(result, str)
    # Should contain numeric values or unavailability message
    assert any(c.isdigit() for c in result) or "unavailable" in result.lower()


@pytest.mark.integration
def test_price_snapshot_from_config(real_config):
    watchlist = real_config["watchlist"][:5]
    result = fetch_price_snapshot.invoke({"tickers": watchlist})
    assert isinstance(result, str)
    found = sum(1 for t in watchlist if t in result)
    assert found >= 3, f"Expected at least 3/{len(watchlist)} tickers in result, got {found}"
