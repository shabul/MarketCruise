"""Unit tests for the compute_accuracy logic in feedback_graph."""
import pytest


def _compute_accuracy(predictions: list[dict], actuals_by_ticker: dict) -> dict:
    """Mirror of feedback_graph.compute_accuracy for isolated testing."""
    total, correct = 0, 0
    by_ticker: dict = {}

    for p in predictions:
        ticker = p["ticker"]
        actual = actuals_by_ticker.get(ticker)
        if not actual:
            continue
        total += 1
        pct = actual.get("pct_change", 0) or 0
        direction = p.get("direction", "").upper()
        hit = (
            (direction == "BUY"  and pct >  0.5) or
            (direction == "SELL" and pct < -0.5) or
            (direction == "HOLD" and abs(pct) <= 1.0)
        )
        if hit:
            correct += 1
        by_ticker.setdefault(ticker, {"correct": 0, "total": 0})
        by_ticker[ticker]["total"] += 1
        if hit:
            by_ticker[ticker]["correct"] += 1

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 3) if total else 0,
        "by_ticker": by_ticker,
    }


@pytest.mark.unit
def test_buy_hit_when_strongly_positive():
    preds = [{"ticker": "TCS", "direction": "BUY"}]
    actuals = {"TCS": {"pct_change": 2.5}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 1
    assert r["accuracy"] == 1.0


@pytest.mark.unit
def test_buy_hit_at_threshold():
    preds = [{"ticker": "TCS", "direction": "BUY"}]
    actuals = {"TCS": {"pct_change": 0.6}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 1


@pytest.mark.unit
def test_buy_miss_at_threshold():
    preds = [{"ticker": "TCS", "direction": "BUY"}]
    actuals = {"TCS": {"pct_change": 0.4}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 0


@pytest.mark.unit
def test_buy_miss_when_negative():
    preds = [{"ticker": "SBIN", "direction": "BUY"}]
    actuals = {"SBIN": {"pct_change": -1.5}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 0
    assert r["accuracy"] == 0.0


@pytest.mark.unit
def test_sell_hit_when_negative():
    preds = [{"ticker": "SBIN", "direction": "SELL"}]
    actuals = {"SBIN": {"pct_change": -2.0}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 1


@pytest.mark.unit
def test_sell_miss_when_positive():
    preds = [{"ticker": "SBIN", "direction": "SELL"}]
    actuals = {"SBIN": {"pct_change": 1.5}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 0


@pytest.mark.unit
def test_hold_hit_when_small_move():
    preds = [{"ticker": "HDFC", "direction": "HOLD"}]
    actuals = {"HDFC": {"pct_change": 0.3}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 1


@pytest.mark.unit
def test_hold_hit_exactly_at_boundary():
    preds = [{"ticker": "HDFC", "direction": "HOLD"}]
    actuals = {"HDFC": {"pct_change": 1.0}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 1


@pytest.mark.unit
def test_hold_miss_when_large_move():
    preds = [{"ticker": "HDFC", "direction": "HOLD"}]
    actuals = {"HDFC": {"pct_change": 3.5}}
    r = _compute_accuracy(preds, actuals)
    assert r["correct"] == 0


@pytest.mark.unit
def test_zero_predictions_no_divide_by_zero():
    r = _compute_accuracy([], {})
    assert r["accuracy"] == 0
    assert r["total"] == 0


@pytest.mark.unit
def test_missing_actuals_skipped():
    preds = [
        {"ticker": "TCS", "direction": "BUY"},
        {"ticker": "INFY", "direction": "BUY"},
    ]
    actuals = {"TCS": {"pct_change": 2.0}}  # INFY has no actual
    r = _compute_accuracy(preds, actuals)
    assert r["total"] == 1
    assert "INFY" not in r["by_ticker"]


@pytest.mark.unit
def test_accuracy_aggregated_by_ticker():
    preds = [
        {"ticker": "TCS", "direction": "BUY"},
        {"ticker": "TCS", "direction": "BUY"},
        {"ticker": "TCS", "direction": "SELL"},
    ]
    actuals = {"TCS": {"pct_change": 2.0}}
    r = _compute_accuracy(preds, actuals)
    assert r["by_ticker"]["TCS"]["total"] == 3
    assert r["by_ticker"]["TCS"]["correct"] == 2
