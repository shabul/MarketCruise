"""Integration tests for NSE public API tools. NSE is flaky — all tests tolerate error strings."""
import pytest
from src.tools.nse_tools import fetch_fii_dii, fetch_market_breadth, fetch_corporate_events


@pytest.mark.integration
def test_fii_dii_returns_string():
    result = fetch_fii_dii.invoke({})
    assert isinstance(result, str)
    assert len(result) > 5


@pytest.mark.integration
def test_fii_dii_content():
    result = fetch_fii_dii.invoke({})
    has_data = "FII Net" in result and "DII Net" in result
    has_error = "unavailable" in result.lower() or "failed" in result.lower()
    assert has_data or has_error, f"Unexpected FII/DII response: {result}"


@pytest.mark.integration
def test_market_breadth_returns_string():
    result = fetch_market_breadth.invoke({})
    assert isinstance(result, str)
    assert len(result) > 5


@pytest.mark.integration
def test_market_breadth_content():
    result = fetch_market_breadth.invoke({})
    has_data = "Advances" in result
    has_error = "unavailable" in result.lower() or "failed" in result.lower()
    assert has_data or has_error, f"Unexpected breadth response: {result}"


@pytest.mark.integration
def test_corporate_events_returns_string():
    result = fetch_corporate_events.invoke({"tickers": ["TCS", "RELIANCE", "INFY"]})
    assert isinstance(result, str)
    assert len(result) > 5


@pytest.mark.integration
def test_corporate_events_no_crash_empty_list():
    result = fetch_corporate_events.invoke({"tickers": []})
    assert isinstance(result, str)


@pytest.mark.integration
def test_all_nse_tools_never_raise():
    """NSE API can be flaky — verify tools always return strings, never raise."""
    try:
        r1 = fetch_fii_dii.invoke({})
        r2 = fetch_market_breadth.invoke({})
        r3 = fetch_corporate_events.invoke({"tickers": ["TCS"]})
        assert all(isinstance(r, str) for r in [r1, r2, r3])
    except Exception as e:
        pytest.fail(f"NSE tool raised an exception instead of returning error string: {e}")
