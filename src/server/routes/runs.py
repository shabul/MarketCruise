import asyncio
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse


class RunRequest(BaseModel):
    watchlist: list[str] | str | None = None
    model: str | None = None
    notes: str | None = None

router = APIRouter()

# In-memory store for active/recent runs
_runs: dict[str, dict] = {}


def _make_sse_event(event_type: str, data: dict) -> dict:
    return {"event": event_type, "data": json.dumps(data)}


def _translate_langgraph_event(lg_event: dict) -> dict | None:
    """Translate a LangGraph astream_events event into our SSE format."""
    kind = lg_event.get("event", "")
    name = lg_event.get("name", "")
    data = lg_event.get("data", {})

    _TRACKED = ("news_analyst", "technical_analyst", "portfolio_risk", "options_analyst", "synthesize", "load_context")

    if kind == "on_chain_start" and name in _TRACKED:
        return _make_sse_event("agent_start", {"agent": name})

    if kind == "on_chain_end" and name in _TRACKED:
        output = data.get("output", {})
        result_key = {
            "news_analyst": "news_analysis",
            "technical_analyst": "technical_analysis",
            "portfolio_risk": "portfolio_analysis",
            "options_analyst": "options_analysis",
            "synthesize": "final_analysis",
        }.get(name)
        full_text = output.get(result_key, "") if result_key else ""
        summary = full_text[:300]
        payload = {"agent": name, "summary": summary}
        if name == "synthesize":
            payload["report"] = full_text
        return _make_sse_event("agent_end", payload)

    if kind == "on_tool_start":
        return _make_sse_event("tool_start", {
            "tool": name,
            "input": str(data.get("input", ""))[:500],
        })

    if kind == "on_tool_end":
        return _make_sse_event("tool_end", {
            "tool": name,
            "output": str(data.get("output", ""))[:800],
        })

    if kind == "on_chat_model_stream":
        chunk = data.get("chunk")
        token = ""
        if chunk and hasattr(chunk, "content"):
            token = chunk.content
        if token:
            return _make_sse_event("llm_stream", {"token": token})

    return None


def _run_error_payload(exc: Exception) -> dict:
    message = str(exc).strip() or exc.__class__.__name__
    lower = message.lower()
    retry_after = None
    if "retry in " in lower:
        tail = lower.split("retry in ", 1)[1]
        retry_after = tail.split("s", 1)[0].strip()
    return {
        "message": message,
        "retry_after_seconds": retry_after,
        "kind": "quota" if any(word in lower for word in ("quota", "resource_exhausted", "429", "rate limit")) else "runtime",
    }


@router.post("/run/{run_type}")
async def trigger_run(run_type: str, body: RunRequest = Body(default_factory=RunRequest)):
    """Trigger a market analysis run. The run executes in background; stream via /stream/{run_id}."""
    if run_type not in ("morning", "midday", "evening", "weekly"):
        return JSONResponse({"error": f"Unknown run type: {run_type}"}, status_code=400)

    # Clean and parse watchlist
    watchlist = []
    if isinstance(body.watchlist, str):
        watchlist = [s.strip().upper() for s in body.watchlist.split(",") if s.strip()]
    elif isinstance(body.watchlist, list):
        watchlist = [s.strip().upper() for s in body.watchlist if s.strip()]
    
    run_id = str(uuid.uuid4())[:8]
    _runs[run_id] = {
        "id": run_id,
        "type": run_type,
        "status": "pending",
        "started_at": datetime.now().isoformat(),
        "events": [],
        "report": "",
    }

    asyncio.create_task(_execute_run(
        run_id, run_type,
        watchlist_override=watchlist or None,
        model_override=body.model,
    ))
    return {"run_id": run_id, "status": "started"}


async def _execute_run(
    run_id: str, run_type: str,
    watchlist_override: list[str] | None = None,
    model_override: str | None = None,
) -> None:
    from ..app import get_config, get_memory
    from ...utils.logging import set_run_event_sink, reset_run_event_sink
    config = get_config()
    memory = get_memory()

    _runs[run_id]["status"] = "running"
    sink_token = set_run_event_sink(
        lambda event_type, payload: _runs[run_id]["events"].append(_make_sse_event(event_type, payload))
    )

    try:
        if run_type == "weekly":
            from ...graphs.feedback_graph import run_weekly_feedback
            memory.sqlite.start_run(run_id, "weekly")
            report = run_weekly_feedback(config, memory)
            memory.sqlite.finish_run(run_id, report)
            _runs[run_id].update({"status": "completed", "report": report})
        else:
            from ...graphs.daily_graph import stream_daily
            final_report = ""
            async for lg_event in stream_daily(
                run_type, config, memory,
                watchlist_override=watchlist_override,
                model_override=model_override,
                initial_run_id=run_id,
            ):
                sse = _translate_langgraph_event(lg_event)
                if sse:
                    _runs[run_id]["events"].append(sse)
                    if sse["event"] == "agent_end":
                        data = json.loads(sse["data"])
                        if data.get("agent") == "synthesize":
                            final_report = data.get("report", "") or data.get("summary", "")
            _runs[run_id]["status"] = "completed"
            _runs[run_id]["report"] = final_report
    except Exception as e:
        error_payload = _run_error_payload(e)
        _runs[run_id]["status"] = "error"
        _runs[run_id]["error"] = error_payload["message"]
        _runs[run_id]["report"] = error_payload["message"]
        _runs[run_id]["events"].append(
            _make_sse_event("error", error_payload)
        )
    finally:
        reset_run_event_sink(sink_token)


@router.get("/stream/{run_id}")
async def stream_run(run_id: str):
    """SSE endpoint: streams events for an active or recently completed run."""
    if run_id not in _runs:
        return JSONResponse({"error": "Run not found"}, status_code=404)

    async def event_generator():
        sent = 0
        while True:
            run = _runs.get(run_id, {})
            events = run.get("events", [])

            while sent < len(events):
                ev = events[sent]
                yield {"event": ev["event"], "data": ev["data"]}
                sent += 1

            if run.get("status") in ("completed", "error"):
                yield {"event": "run_complete", "data": json.dumps({
                    "status": run["status"],
                    "report": run.get("report", ""),
                    "error": run.get("error", ""),
                })}
                break

            await asyncio.sleep(0.2)

    return EventSourceResponse(event_generator())


@router.get("/runs")
async def list_runs():
    return list(reversed(list(_runs.values())))
