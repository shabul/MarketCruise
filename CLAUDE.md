# MarketCruise — Claude Instructions

Personal AI-powered Indian market (NSE/BSE) assistant. LangGraph multi-agent system with ChromaDB memory, weekly self-feedback loop, and a FastAPI + SSE dashboard.

## Project layout

```
src/
├── agents/          # base.py + news_analyst, technical_analyst, portfolio_risk, orchestrator
├── graphs/          # daily_graph (morning/midday/evening), feedback_graph (weekly)
├── memory/          # sqlite_store, chroma_store, memory_manager (dual-write)
├── server/
│   ├── app.py       # FastAPI factory, holds _config + _memory singletons
│   ├── routes/      # runs.py (SSE), api.py (history/accuracy/usage/portfolio), kite_auth.py
│   └── static/      # Bootstrap 5 dashboard + stream.js
├── state/schema.py  # MarketState, FeedbackState TypedDicts
└── tools/           # @tool-decorated: market_tools, news_tools, nse_tools, portfolio_tools
tests/{unit,integration,functional,e2e}/
```

## Critical conventions

**Env loading — always `load_dotenv(override=True)`.** A stale `GEMINI_API_KEY` in the shell will silently shadow the `.env` value otherwise. Already applied in `tests/conftest.py` and `src/server/app.py`.

**API key sync — `langchain-google-genai` ≥ 4.x prefers `GOOGLE_API_KEY`.** Use `_api_key()` in `src/agents/base.py` — it reads `GEMINI_API_KEY` and writes it to `GOOGLE_API_KEY` so both env vars stay aligned (suppresses the noisy "Both … are set" warning).

**Model names — the old `gemini-1.5-*` family is deprecated.** Current `config.yaml`:
- `default_model: gemini-2.0-flash`
- `fallback_model: gemini-2.5-flash`
- `heavy_model: gemini-2.5-pro`

When adding a new model, check availability with `client.models.list()` from the `google.genai` SDK before wiring it in. Don't trust training-data model names — verify against the live API.

**Relative imports across `src/server/`.** Routes are 3 levels deep, so `src.tools.*` is reached via `from ...tools.x import y`, NOT `..tools`. The earlier `..tools` bug broke `/api/portfolio` silently — see fix in `src/server/routes/api.py`.

**Memory manager dual-writes.** `save_run_predictions` / `save_actuals` write to BOTH SQLite (structured) and ChromaDB (semantic). Don't add a writer that only hits one — accuracy queries and feedback retrieval both depend on this.

**Quota errors are caught upstream.** `is_quota_error()` in `src/agents/base.py` matches `quota`, `rate limit`, `resource exhausted`, `429`, `resource_exhausted`. Agents catch quota errors and retry with the fallback LLM. Don't add new error-handling layers around agent code — the pattern is centralized.

## Test conventions

**Run the right layer:**
- `uv run pytest tests/unit/` — no I/O, < 5s
- `uv run pytest tests/integration/` — real APIs (yfinance, NewsAPI, NSE, Kite, Gemini)
- `uv run pytest tests/functional/` — full agent / graph / FastAPI runs
- `uv run pytest tests/e2e/` — POST → SSE → completion

**Gemini tests use the `gemini_available` fixture** (session-scoped, in `conftest.py`). It only verifies the key is non-empty — it does NOT make a probe API call (that wasted quota). Individual Gemini tests wrap `.invoke()` in `try/except` and call `pytest.skip()` on rate-limit errors so quota exhaustion never causes test failures.

**httpx 0.28+ removed the `app=` shorthand.** Use `httpx.ASGITransport(app=...)`:
```python
async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fastapi), base_url="http://test") as client:
```

**Functional tests bypass `create_app()`** and build a fresh `FastAPI()` with the same routers (see `tests/functional/test_server_api.py::fastapi`). This avoids the `StaticFiles` mount swallowing test routes and lets each module use isolated temp memory.

## Common commands

```bash
# Server
python main.py --server                    # FastAPI on :8001
python main.py --run morning               # ad-hoc CLI run
python main.py --set-kite-token <token>    # update Zerodha access token

# Tests
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v --timeout=60
uv run pytest -v --timeout=300             # everything
```

## Things to avoid

- Don't call `load_dotenv()` without `override=True` — see above
- Don't probe Gemini in fixtures — wastes quota, causes false skips
- Don't hardcode `os.environ["GEMINI_API_KEY"]` — use `_api_key()` so `GOOGLE_API_KEY` stays in sync
- Don't add a new agent without registering it in `src/graphs/daily_graph.py`'s `route_agent()` dispatch
- Don't use `gemini-1.5-flash` / `gemini-1.5-pro` — both 404 on the current API
