"""Functional tests — FastAPI HTTP endpoints via HTTPX async test client."""
import asyncio
import json
import tempfile

import pytest
import httpx

from src.server.app import create_app


@pytest.fixture(scope="module")
def app(real_config):
    """Create a fresh FastAPI app with isolated temp memory for this module."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {**real_config, "memory": {
            "chroma_dir": f"{tmp}/chroma",
            "sqlite_path": f"{tmp}/test.db",
            "top_k_memories": 5,
        }}
        import src.server.app as app_module
        from src.memory.memory_manager import MemoryManager
        app_module._config = cfg
        app_module._memory = MemoryManager(cfg)
        yield app_module._memory  # keep memory alive; app already created via module state


@pytest.fixture(scope="module")
def fastapi(real_config):
    """Return the FastAPI application instance with isolated memory."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {**real_config, "memory": {
            "chroma_dir": f"{tmp}/chroma",
            "sqlite_path": f"{tmp}/test.db",
            "top_k_memories": 5,
        }}
        import src.server.app as app_module
        from src.memory.memory_manager import MemoryManager
        app_module._config = cfg
        app_module._memory = MemoryManager(cfg)
        application = app_module.create_app.__wrapped__(cfg) if hasattr(app_module.create_app, "__wrapped__") else None
        if application is None:
            from fastapi import FastAPI
            from src.server.routes.runs import router as runs_router
            from src.server.routes.api import router as api_router
            from src.server.routes.kite_auth import router as kite_router
            application = FastAPI(title="MarketCruise-Test")
            application.include_router(runs_router)
            application.include_router(api_router, prefix="/api")
            application.include_router(kite_router)
        yield application


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.functional
@pytest.mark.asyncio
async def test_post_run_morning_returns_run_id(fastapi):
    async with _client(fastapi) as client:
        resp = await client.post("/run/morning")
    assert resp.status_code == 200
    body = resp.json()
    assert "run_id" in body
    assert body.get("status") == "started"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_post_invalid_run_type_returns_400(fastapi):
    async with _client(fastapi) as client:
        resp = await client.post("/run/invalid_type")
    assert resp.status_code == 400


@pytest.mark.functional
@pytest.mark.asyncio
async def test_get_runs_returns_list(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_get_stream_unknown_id_returns_404(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/stream/nonexistent-id-xyz")
    assert resp.status_code == 404


@pytest.mark.functional
@pytest.mark.asyncio
async def test_get_stream_known_id_content_type(fastapi):
    """Trigger a run, then verify the stream endpoint returns SSE content-type."""
    async with _client(fastapi) as client:
        post_resp = await client.post("/run/morning")
        run_id = post_resp.json()["run_id"]
        async with client.stream("GET", f"/stream/{run_id}") as resp:
            assert resp.status_code == 200
            content_type = resp.headers.get("content-type", "")
            assert "text/event-stream" in content_type


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_history_returns_list(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_accuracy_has_required_keys(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/accuracy")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_predictions" in data
    assert "by_ticker" in data


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_usage_has_today_and_month(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert "today" in data
    assert "month" in data


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_portfolio_has_required_keys(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "holdings" in data
    assert "positions" in data
    assert "pnl" in data


@pytest.mark.functional
@pytest.mark.asyncio
async def test_kite_login_returns_html(fastapi):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        resp = await client.get("/kite/login")
    assert resp.status_code in (200, 302, 307)
    if resp.status_code == 200:
        assert "kite" in resp.text.lower() or "zerodha" in resp.text.lower()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_kite_callback_bad_status_returns_html(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/kite/callback?status=failed&request_token=invalid")
    assert resp.status_code == 200
    assert "<html" in resp.text.lower() or "error" in resp.text.lower()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_post_weekly_run_returns_run_id(fastapi):
    async with _client(fastapi) as client:
        resp = await client.post("/run/weekly")
    assert resp.status_code == 200
    assert "run_id" in resp.json()


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_predictions_today_empty(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/predictions/today")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_hypotheses_empty(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/hypotheses")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_hypotheses_create_and_list(fastapi):
    async with _client(fastapi) as client:
        post_resp = await client.post("/api/hypotheses", json={
            "ticker": "TESTCO", "thesis": "Integration test thesis",
            "evidence": "test signal", "entry_price": 1000.0,
        })
        assert post_resp.status_code == 200
        hyp_id = post_resp.json()["id"]
        assert hyp_id

        list_resp = await client.get("/api/hypotheses")
        ids = [h["id"] for h in list_resp.json()]
        assert hyp_id in ids


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_hypotheses_update(fastapi):
    async with _client(fastapi) as client:
        post_resp = await client.post("/api/hypotheses", json={
            "ticker": "UPDATECO", "thesis": "Will be updated",
        })
        hyp_id = post_resp.json()["id"]

        patch_resp = await client.patch(f"/api/hypotheses/{hyp_id}", json={"status": "won", "outcome": "Target hit"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["ok"] is True

        list_resp = await client.get("/api/hypotheses?status=won")
        found = [h for h in list_resp.json() if h["id"] == hyp_id]
        assert len(found) == 1
        assert found[0]["status"] == "won"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_hypotheses_delete(fastapi):
    async with _client(fastapi) as client:
        post_resp = await client.post("/api/hypotheses", json={"ticker": "DELCO", "thesis": "To be deleted"})
        hyp_id = post_resp.json()["id"]

        del_resp = await client.delete(f"/api/hypotheses/{hyp_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["ok"] is True

        del2 = await client.delete(f"/api/hypotheses/{hyp_id}")
        assert del2.status_code == 404


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_feedback_empty(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/feedback")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report"] == ""
    assert data["date"] is None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_accuracy_uses_ticker_and_date(fastapi):
    import src.server.app as app_module

    memory = app_module.get_memory()
    memory.sqlite.save_predictions("run-1", "2026-05-15", [
        {"ticker": "TCS", "direction": "BUY", "confidence": "High", "reasoning": "Day 1"},
    ])
    memory.sqlite.save_predictions("run-2", "2026-05-16", [
        {"ticker": "TCS", "direction": "SELL", "confidence": "High", "reasoning": "Day 2"},
    ])
    memory.sqlite.save_actuals("2026-05-15", [{"ticker": "TCS", "close": 100.0, "pct_change": 1.2}])
    memory.sqlite.save_actuals("2026-05-16", [{"ticker": "TCS", "close": 98.0, "pct_change": -1.1}])

    async with _client(fastapi) as client:
        resp = await client.get("/api/accuracy")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_predictions"] == 2
    assert data["by_ticker"]["TCS"]["total"] == 2
    assert data["by_ticker"]["TCS"]["correct"] == 2
    history = data["by_ticker"]["TCS"]["history"]
    assert {entry["date"] for entry in history} == {"2026-05-15", "2026-05-16"}


@pytest.mark.functional
@pytest.mark.asyncio
async def test_weekly_run_persists_feedback_report(fastapi, monkeypatch):
    import src.graphs.feedback_graph as feedback_graph

    monkeypatch.setattr(feedback_graph, "run_weekly_feedback", lambda config, memory: "Weekly lessons report")

    async with _client(fastapi) as client:
        post_resp = await client.post("/run/weekly")
        assert post_resp.status_code == 200
        run_id = post_resp.json()["run_id"]

        for _ in range(20):
            runs_resp = await client.get("/runs")
            run = next((r for r in runs_resp.json() if r["id"] == run_id), None)
            if run and run["status"] == "completed":
                break
            await asyncio.sleep(0.05)

        feedback_resp = await client.get("/api/feedback")
        history_resp = await client.get("/api/history")

    assert feedback_resp.status_code == 200
    assert feedback_resp.json()["report"] == "Weekly lessons report"

    history = history_resp.json()
    weekly = next(r for r in history if r["run_id"] == run_id)
    assert weekly["run_type"] == "weekly"
    assert weekly["report_text"] == "Weekly lessons report"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_execute_run_passes_http_run_id_to_daily_graph(fastapi, monkeypatch):
    import src.server.routes.runs as runs_module
    import src.graphs.daily_graph as daily_graph

    captured = {}

    async def fake_stream_daily(run_type, config, memory, **kwargs):
        captured["run_type"] = run_type
        captured["initial_run_id"] = kwargs.get("initial_run_id")
        yield {"event": "on_chain_start", "name": "load_context", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "synthesize",
            "data": {"output": {"final_analysis": "Synthetic report"}},
        }

    monkeypatch.setattr(daily_graph, "stream_daily", fake_stream_daily)

    runs_module._runs["http-run-123"] = {
        "id": "http-run-123",
        "type": "morning",
        "status": "pending",
        "started_at": "2026-05-17T00:00:00",
        "events": [],
        "report": "",
    }

    await runs_module._execute_run("http-run-123", "morning")

    assert captured["run_type"] == "morning"
    assert captured["initial_run_id"] == "http-run-123"
    assert runs_module._runs["http-run-123"]["status"] == "completed"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_config_returns_watchlist(fastapi):
    async with _client(fastapi) as client:
        resp = await client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "watchlist" in data
    assert isinstance(data["watchlist"], list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_run_trigger_accepts_json_body(fastapi):
    async with _client(fastapi) as client:
        resp = await client.post("/run/morning", json={"watchlist": ["TCS"], "model": "gemini-2.0-flash", "notes": "test"})
    assert resp.status_code == 200
    body = resp.json()
    assert "run_id" in body
    assert body["status"] == "started"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_api_premarket_returns_list(fastapi):
    """Premarket endpoint returns list with label keys (yfinance may return null values in test env)."""
    async with _client(fastapi) as client:
        resp = await client.get("/api/market/premarket")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 8
    assert all("label" in item for item in data)
