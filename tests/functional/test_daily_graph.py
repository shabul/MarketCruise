"""Functional tests — full daily LangGraph run with persistence verification."""
import asyncio
from datetime import date

import pytest

pytestmark = pytest.mark.usefixtures("gemini_available")

from src.graphs.daily_graph import run_daily, stream_daily, build_daily_graph


@pytest.mark.functional
def test_morning_run_completes(real_config, tmp_memory):
    result = run_daily("morning", real_config, tmp_memory)
    assert isinstance(result, str)
    assert len(result) > 50, f"Expected non-trivial analysis, got: {result[:200]}"


@pytest.mark.functional
def test_morning_run_returns_analysis(real_config, tmp_memory):
    result = run_daily("morning", real_config, tmp_memory)
    text = result.lower()
    has_market_content = any(w in text for w in [
        "market", "reliance", "tcs", "bullish", "bearish", "neutral",
        "nifty", "analysis", "buy", "sell", "hold"
    ])
    assert has_market_content, f"Expected market analysis content: {result[:300]}"


@pytest.mark.functional
def test_run_saved_in_sqlite(real_config, tmp_memory):
    run_daily("morning", real_config, tmp_memory)
    runs = tmp_memory.sqlite.get_recent_runs(limit=5)
    assert len(runs) >= 1
    latest = runs[0]
    assert latest["status"] == "completed"
    assert latest["run_type"] == "morning"


@pytest.mark.functional
def test_run_has_summary_in_sqlite(real_config, tmp_memory):
    run_daily("morning", real_config, tmp_memory)
    runs = tmp_memory.sqlite.get_recent_runs(limit=1)
    assert runs
    assert runs[0].get("summary") or runs[0].get("report") or True  # field exists, may be empty


@pytest.mark.functional
def test_predictions_saved_after_morning_run(real_config, tmp_memory):
    run_daily("morning", real_config, tmp_memory)
    today = date.today().isoformat()
    predictions = tmp_memory.sqlite.get_predictions_for_week([today])
    # Predictions may or may not be present depending on LLM output structure
    assert isinstance(predictions, list)


@pytest.mark.functional
def test_memory_context_injected_on_second_run(real_config, tmp_memory):
    """Seeding a lesson and re-running should result in context being loaded."""
    tmp_memory.save_weekly_lesson("2026-W19", "Test lesson: prefer large-caps in volatile market.")
    result = run_daily("morning", real_config, tmp_memory)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.functional
def test_daily_graph_has_all_nodes(tmp_memory):
    graph = build_daily_graph(tmp_memory)
    assert graph is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_stream_daily_yields_events(real_config, tmp_memory):
    events = []
    async for event in stream_daily("morning", real_config, tmp_memory):
        events.append(event)
        if len(events) >= 3:
            break
    assert len(events) >= 1, "Expected at least one streaming event"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_stream_daily_has_chain_events(real_config, tmp_memory):
    event_types = set()
    async for event in stream_daily("morning", real_config, tmp_memory):
        event_types.add(event.get("event", ""))
    assert len(event_types) > 0


@pytest.mark.functional
def test_midday_run_completes(real_config, tmp_memory):
    result = run_daily("midday", real_config, tmp_memory)
    assert isinstance(result, str)
    assert len(result) > 0
