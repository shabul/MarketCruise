"""Unit tests for SQLiteStore — no external I/O."""
import sqlite3
import pytest


@pytest.mark.unit
def test_schema_created_on_init(tmp_sqlite):
    with sqlite3.connect(tmp_sqlite.db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"runs", "predictions", "actuals", "hypotheses", "usage_log"}.issubset(tables)


@pytest.mark.unit
def test_run_lifecycle(tmp_sqlite):
    tmp_sqlite.start_run("run-1", "morning")
    tmp_sqlite.finish_run("run-1", "Final report text", "completed")
    runs = tmp_sqlite.get_recent_runs()
    assert len(runs) == 1
    r = runs[0]
    assert r["run_id"] == "run-1"
    assert r["run_type"] == "morning"
    assert r["status"] == "completed"
    assert r["report_text"] == "Final report text"
    assert r["finished_at"] is not None


@pytest.mark.unit
def test_predictions_round_trip(tmp_sqlite, today):
    preds = [
        {"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "Strong IT"},
        {"ticker": "SBIN", "direction": "SELL", "confidence": "Medium", "reasoning": "NPA concerns"},
    ]
    tmp_sqlite.save_predictions("run-1", today, preds)
    result = tmp_sqlite.get_predictions_for_week([today])
    assert len(result) == 2
    tickers = {r["ticker"] for r in result}
    assert tickers == {"TCS", "SBIN"}
    tcs = next(r for r in result if r["ticker"] == "TCS")
    assert tcs["direction"] == "BUY"
    assert tcs["confidence"] == "High"


@pytest.mark.unit
def test_actuals_round_trip(tmp_sqlite, today):
    actuals = [
        {"ticker": "TCS", "open": 3900.0, "close": 3950.0, "pct_change": 1.28},
        {"ticker": "SBIN", "open": 800.0, "close": 790.0, "pct_change": -1.25},
    ]
    tmp_sqlite.save_actuals(today, actuals)
    result = tmp_sqlite.get_actuals_for_week([today])
    assert len(result) == 2
    tickers = {r["ticker"] for r in result}
    assert tickers == {"TCS", "SBIN"}


@pytest.mark.unit
def test_usage_log_and_summary(tmp_sqlite):
    from datetime import datetime, timezone
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tmp_sqlite.log_usage("gemini-2.0-flash", "morning_analysis", "news_analyst", 1000, 500, 0.0003)
    tmp_sqlite.log_usage("gemini-2.0-flash", "morning_analysis", "technical_analyst", 800, 400, 0.00024)
    tmp_sqlite.log_usage("gemini-1.5-flash", "weekly_feedback", "orchestrator", 2000, 1000, 0.0005)
    summary = tmp_sqlite.get_usage_summary(today_utc)
    assert len(summary) >= 2
    flash_rows = [r for r in summary if r["model"] == "gemini-2.0-flash"]
    assert len(flash_rows) >= 1
    flash_total = sum(r["input_tokens"] for r in flash_rows)
    assert flash_total == 1800


@pytest.mark.unit
def test_get_recent_runs_ordering(tmp_sqlite):
    import time
    tmp_sqlite.start_run("run-a", "morning")
    time.sleep(0.01)
    tmp_sqlite.start_run("run-b", "midday")
    time.sleep(0.01)
    tmp_sqlite.start_run("run-c", "evening")
    runs = tmp_sqlite.get_recent_runs(limit=3)
    assert runs[0]["run_id"] == "run-c"
    assert runs[1]["run_id"] == "run-b"
    assert runs[2]["run_id"] == "run-a"


@pytest.mark.unit
def test_get_recent_runs_limit(tmp_sqlite):
    for i in range(5):
        tmp_sqlite.start_run(f"run-{i}", "morning")
    runs = tmp_sqlite.get_recent_runs(limit=3)
    assert len(runs) == 3


@pytest.mark.unit
def test_predictions_for_week_empty(tmp_sqlite):
    result = tmp_sqlite.get_predictions_for_week(["2020-01-01", "2020-01-02"])
    assert result == []


@pytest.mark.unit
def test_actuals_insert_or_replace(tmp_sqlite, today):
    actuals = [{"ticker": "TCS", "close": 3900.0, "pct_change": 0.5}]
    tmp_sqlite.save_actuals(today, actuals)
    actuals2 = [{"ticker": "TCS", "close": 3950.0, "pct_change": 1.2}]
    tmp_sqlite.save_actuals(today, actuals2)
    result = tmp_sqlite.get_actuals_for_week([today])
    tcs_rows = [r for r in result if r["ticker"] == "TCS"]
    assert len(tcs_rows) >= 1
