"""Functional tests — FastAPI HTTP endpoints via HTTPX async test client."""
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
