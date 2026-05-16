import pytest

from src.graphs.daily_graph import stream_daily


@pytest.mark.functional
@pytest.mark.asyncio
async def test_stream_daily_preserves_supplied_run_id(tmp_memory, monkeypatch):
    import src.graphs.daily_graph as daily_graph

    monkeypatch.setattr(daily_graph, "_compute_market_regime", lambda: "Ranging")
    monkeypatch.setattr(daily_graph, "fetch_global_premarket", lambda: "Flat global cues")
    monkeypatch.setattr(daily_graph, "run_news_analyst", lambda state: {"news_analysis": "News ok"})
    monkeypatch.setattr(daily_graph, "run_technical_analyst", lambda state: {"technical_analysis": "TCS C=₹100.0 (+1.0%)"})
    monkeypatch.setattr(daily_graph, "run_portfolio_risk", lambda state: {"portfolio_analysis": "Portfolio ok"})
    monkeypatch.setattr(daily_graph, "run_options_analyst", lambda state: {"options_analysis": "Options ok"})
    monkeypatch.setattr(
        daily_graph,
        "run_orchestrator",
        lambda state: {
            "final_analysis": "Synthesis complete",
            "predictions": {"stocks": [{"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "Test"}]},
            "messages": [],
        },
    )

    async for _ in stream_daily(
        "morning",
        {"watchlist": ["TCS"], "gemini": {}},
        tmp_memory,
        initial_run_id="run-http-123",
    ):
        pass

    runs = tmp_memory.sqlite.get_recent_runs(limit=1)
    assert runs[0]["run_id"] == "run-http-123"
