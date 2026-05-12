"""Unit tests for MemoryManager dual-write and context loading."""
import pytest
from datetime import date


@pytest.mark.unit
def test_load_context_empty_returns_empty(tmp_memory):
    memories, feedback = tmp_memory.load_run_context("morning", ["RELIANCE", "TCS"])
    assert isinstance(memories, list)
    assert isinstance(feedback, str)
    assert len(memories) == 0
    assert feedback == ""


@pytest.mark.unit
def test_save_predictions_writes_to_sqlite(tmp_memory, today):
    preds = {"stocks": [
        {"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "Strong results"},
    ]}
    tmp_memory.save_run_predictions("run-test", preds)
    sqlite_rows = tmp_memory.sqlite.get_predictions_for_week([today])
    assert len(sqlite_rows) == 1
    assert sqlite_rows[0]["ticker"] == "TCS"


@pytest.mark.unit
def test_save_predictions_writes_to_chroma(tmp_memory, today):
    preds = {"stocks": [
        {"ticker": "RELIANCE", "direction": "BUY", "confidence": "Medium", "reasoning": "Oil rally"},
    ]}
    tmp_memory.save_run_predictions("run-test", preds)
    results = tmp_memory.chroma.retrieve_relevant("RELIANCE prediction", collection="stock_events", n_results=5)
    assert any("RELIANCE" in r for r in results)


@pytest.mark.unit
def test_save_actuals_writes_to_sqlite(tmp_memory, today):
    actuals = [{"ticker": "HDFC", "close": 1800.0, "pct_change": 0.8}]
    tmp_memory.save_actuals(actuals)
    sqlite_rows = tmp_memory.sqlite.get_actuals_for_week([today])
    assert any(r["ticker"] == "HDFC" for r in sqlite_rows)


@pytest.mark.unit
def test_save_actuals_writes_to_chroma(tmp_memory):
    actuals = [{"ticker": "WIPRO", "close": 450.0, "pct_change": -1.2}]
    tmp_memory.save_actuals(actuals)
    results = tmp_memory.chroma.retrieve_relevant("WIPRO EOD close", collection="stock_events", n_results=5)
    assert any("WIPRO" in r for r in results)


@pytest.mark.unit
def test_weekly_lesson_loadable(tmp_memory):
    tmp_memory.save_weekly_lesson("2026-W19", "IT stocks were predictable. Banking was noisy.")
    _, feedback = tmp_memory.load_run_context("morning", ["TCS"])
    assert "IT stocks" in feedback or feedback != ""


@pytest.mark.unit
def test_watchlist_truncated_to_five(tmp_memory, today):
    """Query is built from at most 5 tickers — verify it doesn't crash with large watchlist."""
    big_watchlist = ["TCS", "INFY", "WIPRO", "HCL", "TECH", "RELIANCE", "HDFC", "ICICI"]
    memories, feedback = tmp_memory.load_run_context("morning", big_watchlist)
    assert isinstance(memories, list)


@pytest.mark.unit
def test_empty_predictions_dict_no_crash(tmp_memory):
    tmp_memory.save_run_predictions("run-empty", {})
    tmp_memory.save_run_predictions("run-empty2", {"stocks": []})
