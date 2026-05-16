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


@pytest.mark.unit
def test_predictions_with_new_fields(tmp_sqlite, today):
    preds = [{
        "ticker": "TCS", "direction": "BUY", "confidence": "High",
        "reasoning": "Strong IT", "entry_price": 3520.0,
        "stop_loss": 3250.0, "target": 4000.0, "timeframe": "1 week",
    }]
    tmp_sqlite.save_predictions("run-1", today, preds)
    result = tmp_sqlite.get_predictions_for_week([today])
    assert len(result) == 1
    tcs = result[0]
    assert tcs["entry_price"] == 3520.0
    assert tcs["stop_loss"] == 3250.0
    assert tcs["target"] == 4000.0
    assert tcs["timeframe"] == "1 week"


@pytest.mark.unit
def test_predictions_new_fields_nullable(tmp_sqlite, today):
    preds = [{"ticker": "SBIN", "direction": "SELL", "confidence": "Medium", "reasoning": "NPA"}]
    tmp_sqlite.save_predictions("run-2", today, preds)
    result = tmp_sqlite.get_predictions_for_week([today])
    sbin = next(r for r in result if r["ticker"] == "SBIN")
    assert sbin["entry_price"] is None
    assert sbin["stop_loss"] is None
    assert sbin["target"] is None
    assert sbin["timeframe"] is None


@pytest.mark.unit
def test_migration_is_idempotent(tmp_path):
    from src.memory.sqlite_store import SQLiteStore
    import sqlite3
    SQLiteStore(str(tmp_path / "test.db"))
    SQLiteStore(str(tmp_path / "test.db"))
    with sqlite3.connect(str(tmp_path / "test.db")) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()}
    assert {"entry_price", "stop_loss", "target", "timeframe"}.issubset(cols)


@pytest.mark.unit
def test_ticker_accuracy_summary_empty(tmp_sqlite):
    result = tmp_sqlite.get_ticker_accuracy_summary(["TCS", "RELIANCE"])
    assert result == []


@pytest.mark.unit
def test_ticker_accuracy_summary_no_tickers(tmp_sqlite):
    result = tmp_sqlite.get_ticker_accuracy_summary([])
    assert result == []


@pytest.mark.unit
def test_ticker_accuracy_summary_with_data(tmp_sqlite, today):
    tmp_sqlite.save_predictions("run-1", today, [{
        "ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "test",
    }])
    tmp_sqlite.save_actuals(today, [{"ticker": "TCS", "open": 3500.0, "close": 3600.0, "pct_change": 2.86}])
    result = tmp_sqlite.get_ticker_accuracy_summary(["TCS"])
    assert len(result) == 1
    assert result[0]["ticker"] == "TCS"
    assert result[0]["total"] == 1
    assert result[0]["correct"] == 1


# --- Hypotheses CRUD ---

@pytest.mark.unit
def test_hypothesis_create_and_get(tmp_sqlite, today):
    tmp_sqlite.save_hypothesis("h1", today, "TCS", "Breakout above 200-day MA", "RSI > 60",
                               entry_price=3500.0, stop_loss=3325.0, target=4025.0, expiry="2026-06-01")
    rows = tmp_sqlite.get_hypotheses()
    assert len(rows) == 1
    h = rows[0]
    assert h["id"] == "h1"
    assert h["ticker"] == "TCS"
    assert h["status"] == "open"
    assert h["entry_price"] == 3500.0
    assert h["target"] == 4025.0


@pytest.mark.unit
def test_hypothesis_migration_idempotent(tmp_path):
    from src.memory.sqlite_store import SQLiteStore
    SQLiteStore(str(tmp_path / "hyp.db"))
    SQLiteStore(str(tmp_path / "hyp.db"))
    with sqlite3.connect(str(tmp_path / "hyp.db")) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(hypotheses)").fetchall()}
    assert {"entry_price", "stop_loss", "target", "expiry", "status"}.issubset(cols)


@pytest.mark.unit
def test_hypothesis_status_filter(tmp_sqlite, today):
    tmp_sqlite.save_hypothesis("h1", today, "TCS", "Thesis A")
    tmp_sqlite.save_hypothesis("h2", today, "INFY", "Thesis B")
    tmp_sqlite.update_hypothesis("h2", status="won", closed_at="2026-05-16")
    open_rows = tmp_sqlite.get_hypotheses(status="open")
    assert len(open_rows) == 1
    assert open_rows[0]["id"] == "h1"
    won_rows = tmp_sqlite.get_hypotheses(status="won")
    assert len(won_rows) == 1
    assert won_rows[0]["id"] == "h2"


@pytest.mark.unit
def test_hypothesis_update(tmp_sqlite, today):
    tmp_sqlite.save_hypothesis("h1", today, "RELIANCE", "Earnings beat")
    ok = tmp_sqlite.update_hypothesis("h1", outcome="Target hit +5.12%", status="won")
    assert ok is True
    rows = tmp_sqlite.get_hypotheses()
    assert rows[0]["status"] == "won"
    assert rows[0]["outcome"] == "Target hit +5.12%"


@pytest.mark.unit
def test_hypothesis_delete(tmp_sqlite, today):
    tmp_sqlite.save_hypothesis("h1", today, "SBIN", "NPA resolution")
    ok = tmp_sqlite.delete_hypothesis("h1")
    assert ok is True
    not_found = tmp_sqlite.delete_hypothesis("h1")
    assert not_found is False
    assert tmp_sqlite.get_hypotheses() == []


@pytest.mark.unit
def test_hypothesis_update_nonexistent(tmp_sqlite):
    ok = tmp_sqlite.update_hypothesis("nonexistent", status="won")
    assert ok is False


@pytest.mark.unit
def test_get_predictions_for_date(tmp_sqlite, today):
    tmp_sqlite.save_predictions("run-x", today, [
        {"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "test"},
        {"ticker": "INFY", "direction": "SELL", "confidence": "Low", "reasoning": "weak"},
    ])
    rows = tmp_sqlite.get_predictions_for_date(today)
    assert len(rows) == 2
    tickers = {r["ticker"] for r in rows}
    assert tickers == {"TCS", "INFY"}


@pytest.mark.unit
def test_get_predictions_for_date_empty(tmp_sqlite):
    rows = tmp_sqlite.get_predictions_for_date("1970-01-01")
    assert rows == []
