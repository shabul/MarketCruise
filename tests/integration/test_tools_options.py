"""Integration tests for options tools — NSE API with graceful fallback."""
import pytest

from src.tools.options_tools import fetch_options_chain, fetch_index_options


@pytest.mark.integration
def test_fetch_options_chain_returns_string():
    result = fetch_options_chain.invoke({"symbol": "RELIANCE"})
    assert isinstance(result, str)
    assert len(result) > 5


@pytest.mark.integration
def test_fetch_options_chain_never_raises():
    try:
        result = fetch_options_chain.invoke({"symbol": "TCS"})
        assert isinstance(result, str)
    except Exception as e:
        pytest.fail(f"fetch_options_chain raised instead of returning error string: {e}")


@pytest.mark.integration
def test_fetch_options_chain_graceful_fallback_on_bad_symbol():
    result = fetch_options_chain.invoke({"symbol": "NOTAREALSTOCK12345"})
    assert isinstance(result, str)
    # Either returns data or a graceful error string — never raises
    has_data = "PCR" in result or "expiry" in result.lower()
    has_error = "unavailable" in result.lower() or "failed" in result.lower()
    assert has_data or has_error


@pytest.mark.integration
def test_fetch_index_options_nifty():
    result = fetch_index_options.invoke({"index": "NIFTY"})
    assert isinstance(result, str)
    has_data = "PCR" in result
    has_error = "unavailable" in result.lower()
    assert has_data or has_error, f"Unexpected result: {result}"


@pytest.mark.integration
def test_fetch_index_options_banknifty():
    result = fetch_index_options.invoke({"index": "BANKNIFTY"})
    assert isinstance(result, str)
    assert len(result) > 5
