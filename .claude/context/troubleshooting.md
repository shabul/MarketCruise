# Troubleshooting (real issues encountered)

Every entry here is a problem that has actually broken this codebase and the resolution that worked. Add new entries as you encounter them — the goal is to never debug the same thing twice.

## Gemini

### `400 INVALID_ARGUMENT — API key expired`

**Cause:** Either the key is genuinely expired, or your shell exported an old `GEMINI_API_KEY` that's shadowing the fresh value in `.env`.

**Fix:** Already handled via `load_dotenv(override=True)` in `tests/conftest.py` and `src/server/app.py`. If you see this in a NEW script you wrote, use `load_dotenv(override=True)` there too.

### `404 NOT_FOUND — models/gemini-1.5-flash is not found`

**Cause:** The model name in `config.yaml` was deprecated by Google. The `v1beta` API no longer serves `gemini-1.5-*`.

**Fix:** Update `config.yaml` to a current model name. List live models with:
```bash
uv run python -c "
import os, google.genai as genai
from dotenv import load_dotenv; load_dotenv(override=True)
for m in genai.Client(api_key=os.environ['GEMINI_API_KEY']).models.list(): print(m.name)
"
```

Current valid names as of 2026-05: `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash-lite` (new users blocked), `gemini-flash-latest`, `gemini-pro-latest`.

### `429 RESOURCE_EXHAUSTED` (even on Tier 1)

**Cause:** Per-project, per-model RPM cap. Tier 1 doesn't remove this — it raises it. The free-tier 15 RPM cap is easy to hit during test runs.

**Fix:** Tests in `tests/integration/test_gemini_llm.py` catch this and `pytest.skip()` instead of failing. For app code, `is_quota_error()` in `src/agents/base.py` triggers a fallback to `get_fallback_llm()`. If both LLMs 429, the run fails — that's a Google quota issue, not a code bug.

Check actual quota at [console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas](https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas) for the project that owns the key.

### Warning: `Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.`

**Cause:** `langchain-google-genai` ≥ 4.x prefers `GOOGLE_API_KEY`. `_api_key()` in `src/agents/base.py` intentionally sets both to keep them in sync.

**Fix:** Suppress only if you must — the warning is harmless. Don't `del os.environ['GOOGLE_API_KEY']` — it'll re-appear on the next LLM creation.

## FastAPI / httpx tests

### `TypeError: AsyncClient.__init__() got an unexpected keyword argument 'app'`

**Cause:** httpx 0.28+ removed the `app=` shorthand.

**Fix:** Use the transport form:
```python
async with httpx.AsyncClient(
    transport=httpx.ASGITransport(app=fastapi_app),
    base_url="http://test",
) as client:
    ...
```

### Test routes return 404 / static files swallow requests

**Cause:** `create_app()` mounts `StaticFiles` at `/`, which catches unmatched routes.

**Fix:** In tests, build a fresh `FastAPI()` and include just the routers you need — don't call `create_app()`. See `tests/functional/test_server_api.py::fastapi` fixture.

### `/api/portfolio` returns 500 with `ModuleNotFoundError: No module named 'src.server.tools'`

**Cause:** Bad relative import. Routes live in `src/server/routes/`, so `..tools` resolves to `src.server.tools` (which doesn't exist), not `src.tools`.

**Fix:** Use `from ...tools.portfolio_tools import ...` (three dots).

## Memory layer

### SQLite usage summary returns empty for "today"

**Cause:** Timestamp prefix matching with `LIKE '2026-05-13%'` fails if the timestamps are stored in UTC but the prefix is local-date. IST is UTC+5:30, so May 13 IST could be May 12 UTC.

**Fix:** Already applied — all `_now()` calls in `src/memory/sqlite_store.py` use `datetime.now(timezone.utc).isoformat()`, and `src/server/routes/api.py` queries with `datetime.now(timezone.utc).strftime("%Y-%m-%d")`. Be consistent.

### ChromaDB lessons not loading after weekly run

**Cause:** Lesson IDs in `chroma_store.py` are `week_label` strings (e.g., `"2026-W19"`). If you save twice with the same label, the second call replaces the first silently.

**Fix:** Either treat that as intentional (latest lesson wins) or include a timestamp suffix in the ID.

## Tools

### NSE API returns 401 / cookie errors

**Cause:** `nseindia.com` aggressively rejects scrapers. The cookie they set on the first request is required for subsequent calls.

**Fix:** Already applied — `_session` global in `src/tools/nse_tools.py` hits `nseindia.com` once to grab cookies before any data call. If you see persistent 401s, the cookie format may have changed; check `_init_nse_session()`.

### yfinance returns empty frame for a valid ticker

**Cause:** Yahoo Finance occasionally serves stale or empty data, particularly outside market hours.

**Fix:** Tools return an "unavailable" string instead of raising. Tests accept either real data or this fallback string. Don't add retries in the tool — the caller (agent) decides.
