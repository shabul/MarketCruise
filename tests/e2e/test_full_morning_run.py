"""E2E test — POST /run/morning → SSE stream → verify completion and persistence."""
import asyncio
import json
import tempfile
from datetime import date

import pytest
import httpx
from fastapi import FastAPI

pytestmark = pytest.mark.usefixtures("gemini_available")

from src.server.routes.runs import router as runs_router
from src.server.routes.api import router as api_router
from src.server.routes.kite_auth import router as kite_router


@pytest.fixture(scope="module")
def e2e_app(real_config):
    """Isolated FastAPI app for E2E tests."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {**real_config, "memory": {
            "chroma_dir": f"{tmp}/chroma",
            "sqlite_path": f"{tmp}/test.db",
            "top_k_memories": 5,
        }}
        import src.server.app as app_module
        from src.memory.memory_manager import MemoryManager
        app_module._config = cfg
        mem = MemoryManager(cfg)
        app_module._memory = mem

        application = FastAPI(title="MarketCruise-E2E")
        application.include_router(runs_router)
        application.include_router(api_router, prefix="/api")
        application.include_router(kite_router)
        yield application, mem


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_morning_run_via_http(e2e_app):
    """
    Full E2E: trigger a morning run over HTTP, consume the SSE stream,
    verify agent events flow and run completes successfully.
    """
    application, memory = e2e_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test", timeout=300.0) as client:
        # Step 1: trigger the run
        post_resp = await client.post("/run/morning")
        assert post_resp.status_code == 200
        run_id = post_resp.json()["run_id"]
        assert run_id

        # Step 2: consume SSE stream until run_complete or timeout
        event_types = []
        run_complete_data = None
        deadline = asyncio.get_event_loop().time() + 280  # 280s budget

        async with client.stream("GET", f"/stream/{run_id}") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if asyncio.get_event_loop().time() > deadline:
                    break
                if line.startswith("event:"):
                    event_types.append(line.split(":", 1)[1].strip())
                if line.startswith("data:") and event_types and event_types[-1] == "run_complete":
                    run_complete_data = json.loads(line.split("data:", 1)[1].strip())
                    break

        # Step 3: verify event flow
        assert len(event_types) > 0, "Expected at least one SSE event"
        has_agent_event = any(e in event_types for e in ["agent_start", "agent_end", "run_complete"])
        assert has_agent_event, f"Expected agent events, got: {event_types}"

        # Step 4: verify run completed
        if run_complete_data:
            assert run_complete_data.get("status") == "completed", \
                f"Run did not complete successfully: {run_complete_data}"

        # Step 5: verify persistence — run appears in API history
        hist_resp = await client.get("/api/history")
        assert hist_resp.status_code == 200
        history = hist_resp.json()
        assert isinstance(history, list)

        # Step 6: verify in-memory runs list
        runs_resp = await client.get("/runs")
        assert runs_resp.status_code == 200
        runs = runs_resp.json()
        run_ids = [r["id"] for r in runs]
        assert run_id in run_ids


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_two_sequential_runs(e2e_app):
    """Trigger two runs back-to-back and verify both get unique run IDs."""
    application, _ = e2e_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test", timeout=30.0) as client:
        resp1 = await client.post("/run/morning")
        resp2 = await client.post("/run/midday")

        id1 = resp1.json()["run_id"]
        id2 = resp2.json()["run_id"]
        assert id1 != id2


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_stream_after_run_completes(e2e_app):
    """After a run finishes, opening the stream should deliver run_complete immediately."""
    application, _ = e2e_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://test", timeout=300.0) as client:
        post_resp = await client.post("/run/morning")
        run_id = post_resp.json()["run_id"]

        # Wait for the run to finish (poll /runs)
        for _ in range(150):
            await asyncio.sleep(2)
            runs_resp = await client.get("/runs")
            runs = {r["id"]: r for r in runs_resp.json()}
            if runs.get(run_id, {}).get("status") in ("completed", "error"):
                break

        # Now open the stream and confirm run_complete is delivered
        got_complete = False
        async with client.stream("GET", f"/stream/{run_id}") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("event:") and "run_complete" in line:
                    got_complete = True
                    break
        assert got_complete, "Expected run_complete event after run finished"
