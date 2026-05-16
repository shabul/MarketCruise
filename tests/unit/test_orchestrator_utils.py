"""Unit tests for orchestrator utilities and base agent helpers."""
import pytest
from src.agents.orchestrator import _extract_predictions
from src.agents.base import estimate_cost, is_quota_error


@pytest.mark.unit
def test_extract_valid_single_stock():
    text = """Market looks bullish.
```json
{"stocks": [{"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "Strong Q4"}]}
```
End of report."""
    result = _extract_predictions(text)
    assert result["stocks"][0]["ticker"] == "TCS"
    assert result["stocks"][0]["direction"] == "BUY"


@pytest.mark.unit
def test_extract_multi_stock():
    text = """Analysis complete.
```json
{"stocks": [
  {"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "IT strong"},
  {"ticker": "SBIN", "direction": "SELL", "confidence": "Low", "reasoning": "NPA risk"},
  {"ticker": "RELIANCE", "direction": "HOLD", "confidence": "Medium", "reasoning": "Neutral"}
]}
```"""
    result = _extract_predictions(text)
    assert len(result["stocks"]) == 3
    tickers = {s["ticker"] for s in result["stocks"]}
    assert tickers == {"TCS", "SBIN", "RELIANCE"}


@pytest.mark.unit
def test_extract_no_json_block():
    text = "Market is volatile. No clear signals today."
    result = _extract_predictions(text)
    assert result == {"stocks": []}


@pytest.mark.unit
def test_extract_malformed_json():
    text = "```json\n{this is not valid json}\n```"
    result = _extract_predictions(text)
    assert result == {"stocks": []}


@pytest.mark.unit
def test_extract_empty_stocks_list():
    text = '```json\n{"stocks": []}\n```'
    result = _extract_predictions(text)
    assert result == {"stocks": []}


@pytest.mark.unit
def test_estimate_cost_flash():
    cost = estimate_cost("gemini-2.0-flash", 1_000_000, 1_000_000)
    assert abs(cost - 0.50) < 0.001


@pytest.mark.unit
def test_estimate_cost_flash_small():
    cost = estimate_cost("gemini-2.0-flash", 1000, 500)
    assert cost > 0
    assert cost < 0.001


@pytest.mark.unit
def test_estimate_cost_pro():
    cost = estimate_cost("gemini-1.5-pro", 1_000_000, 1_000_000)
    assert abs(cost - 6.25) < 0.01


@pytest.mark.unit
def test_estimate_cost_unknown_model():
    cost = estimate_cost("some-unknown-model", 1000, 500)
    assert cost == 0.0


@pytest.mark.unit
def test_is_quota_error_429():
    assert is_quota_error(Exception("HTTP 429 Too Many Requests"))


@pytest.mark.unit
def test_is_quota_error_resource_exhausted():
    assert is_quota_error(Exception("Resource exhausted, please try again"))


@pytest.mark.unit
def test_is_quota_error_rate_limit():
    assert is_quota_error(Exception("Rate limit exceeded for this model"))


@pytest.mark.unit
def test_is_quota_error_normal_exception():
    assert not is_quota_error(ValueError("bad input shape"))
    assert not is_quota_error(Exception("connection timeout"))
    assert not is_quota_error(Exception("invalid API key"))


@pytest.mark.unit
def test_extract_richer_prediction_format():
    text = '''Analysis complete.
```json
{"stocks": [{"ticker": "TCS", "direction": "BUY", "confidence": "High",
  "reasoning": "Strong Q4", "entry_price": 3500.0, "stop_loss": 3250.0,
  "target": 4000.0, "timeframe": "1 week"}]}
```'''
    result = _extract_predictions(text)
    assert len(result["stocks"]) == 1
    stock = result["stocks"][0]
    assert stock["ticker"] == "TCS"
    assert stock["entry_price"] == 3500.0
    assert stock["stop_loss"] == 3250.0
    assert stock["target"] == 4000.0
    assert stock["timeframe"] == "1 week"
