# Testing

All tests are **real-API** by design — no mocks for Gemini, yfinance, NewsAPI, NSE, or Kite. We accept some flakiness (NSE in particular) and write each test to tolerate graceful error strings.

## Layers

| Layer | Where | Speed | What |
|-------|-------|-------|------|
| Unit | `tests/unit/` | < 5 s | No I/O — pure logic (accuracy math, JSON extraction, SQLite/Chroma CRUD on temp dirs) |
| Integration | `tests/integration/` | ~30 s | Real external APIs (Gemini, yfinance, NewsAPI, NSE, Kite) |
| Functional | `tests/functional/` | up to 5 min | Full agent runs, daily graph, feedback graph, FastAPI HTTP endpoints |
| E2E | `tests/e2e/` | up to 5 min | `POST /run/morning` → SSE stream → persistence verification |

## Run commands

```bash
# Fast — unit only
uv run pytest tests/unit/ -v

# Real APIs but no Gemini cost
uv run pytest tests/integration/test_tools_market.py tests/integration/test_tools_news.py tests/integration/test_tools_nse.py tests/integration/test_tools_portfolio.py -v

# Everything Gemini
uv run pytest tests/integration/test_gemini_llm.py tests/functional/ tests/e2e/ -v --timeout=300

# Full suite
uv run pytest -v --timeout=300
```

## Skipping behaviour

Tests skip (rather than fail) when:
- `GEMINI_API_KEY` is missing → all Gemini-dependent tests skip via the session-scoped `gemini_available` fixture in `tests/conftest.py`
- Gemini returns 429 / `RESOURCE_EXHAUSTED` mid-test → individual Gemini tests catch this and call `pytest.skip()`
- `KITE_ACCESS_TOKEN` is missing → portfolio tests requiring a live token skip
- NSE public API returns an error string → tests accept either real data or the error string (NSE is genuinely flaky)

This way a developer without all the API keys can still run a meaningful subset, and quota exhaustion never produces red failures.

## Fixtures (`tests/conftest.py`)

| Fixture | Scope | What |
|---------|-------|------|
| `real_config` | session | Loads `config.yaml` |
| `gemini_config` | session | Just `real_config["gemini"]` |
| `tmp_memory` | function | `MemoryManager` with temp Chroma + SQLite dirs |
| `tmp_sqlite` / `tmp_chroma` | function | Just the individual stores |
| `morning_state` / `midday_state` | function | Pre-built `MarketState` dicts for agent tests |
| `gemini_available` | session | Skips the test if `GEMINI_API_KEY` is unset |

## httpx ASGI testing

`httpx` ≥ 0.28 removed the `app=` shorthand. Use the explicit transport:

```python
async with httpx.AsyncClient(
    transport=httpx.ASGITransport(app=fastapi_app),
    base_url="http://test",
) as client:
    resp = await client.post("/run/morning")
```

The functional test module's `fastapi` fixture builds a fresh `FastAPI()` with the same routers — it doesn't call `create_app()`, which mounts `StaticFiles` at `/` and would swallow test routes.

## Known issues

- **Gemini rate limits**: even on Tier 1 (billing enabled), there's a per-project per-minute cap. The integration tests include a 4-second pause between calls and skip on 429. Heavy parallel test runs may still trip the limit.
- **NSE flakiness**: `nseindia.com` rejects ~5% of requests with cookie/header errors. Tools return a fallback string instead of raising; tests assert "data OR error string."
- **Yahoo Finance**: occasionally returns empty frames for valid tickers. The `fetch_*_snapshot` tools return an "unavailable" string in that case.
