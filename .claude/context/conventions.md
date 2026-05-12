# Code conventions

Not stylistic preferences — these are the patterns the rest of the codebase relies on. Breaking them creates silent bugs.

## Imports inside `src/`

Relative imports based on file depth:

| File location | Reaching `src.tools.*` |
|--------------|------------------------|
| `src/agents/*.py` | `from ..tools.x import y` |
| `src/graphs/*.py` | `from ..tools.x import y` |
| `src/server/routes/*.py` | `from ...tools.x import y` |
| `src/server/app.py` | `from ..tools.x import y` |

Count `..` carefully — the `..tools` → `...tools` bug in `src/server/routes/api.py` shipped silently until a test caught it.

## Environment variable loading

Always:
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

Without `override=True`, a stale exported key in the shell silently shadows the `.env` value. The whole codebase assumes `.env` is authoritative.

## Gemini key handling

Don't hardcode `os.environ["GEMINI_API_KEY"]`. Use the helper in `src/agents/base.py`:

```python
from src.agents.base import _api_key
llm = ChatGoogleGenerativeAI(model="...", google_api_key=_api_key(), ...)
```

This reads `GEMINI_API_KEY` and mirrors it to `GOOGLE_API_KEY` (which `langchain-google-genai` ≥ 4.x prefers). Skipping this works but spams a warning on every LLM call.

## Tool return contract

All `@tool`-decorated functions in `src/tools/` MUST return a string and MUST NOT raise. On error, return a graceful string like `"Holdings unavailable: <reason>"`. Agents catch errors from raising tools, but the dashboard SSE stream and tests assume strings.

Verified by `test_all_*_tools_never_raise` in each integration test file.

## Agent return shape

Each `run_<agent>(state)` function returns a `dict` with:

```python
{
    "<output_field>": "...",         # news_analysis / technical_analysis / portfolio_analysis / final_analysis
    "next_agent": "<next_node_name>", # routes the StateGraph
    "messages": [...],                # appended via add_messages reducer
}
```

`next_agent` values map through `route_agent()` in `daily_graph.py`. Adding a new agent requires registering it in BOTH the node list AND the routing dict.

## Memory dual-write

`memory_manager.save_run_predictions()` and `save_actuals()` write to both SQLite AND ChromaDB. If you add a new write path:
- SQLite → for structured queries (accuracy, history)
- ChromaDB → for semantic retrieval (next run's context)

Skipping either breaks downstream features.

## Timestamps

All persisted timestamps are UTC ISO 8601 strings:
```python
datetime.now(timezone.utc).isoformat()
```

Queries against `usage_log.ts` or `runs.started_at` use UTC prefixes too. Don't mix in local time — IST is UTC+5:30, which crosses the day boundary at 5:30 AM IST.

## Test markers

Each test file under `tests/integration/`, `tests/functional/`, or `tests/e2e/` should use the matching marker:

```python
@pytest.mark.integration   # tests/integration/
@pytest.mark.functional    # tests/functional/
@pytest.mark.e2e           # tests/e2e/
```

Unit tests need no marker. Markers are defined in `pyproject.toml` under `[tool.pytest.ini_options].markers`.

## Gemini-dependent tests

If a test calls Gemini directly or indirectly (through agents), add at the top of the file:

```python
pytestmark = pytest.mark.usefixtures("gemini_available")
```

And wrap each `.invoke()` in:

```python
try:
    response = llm.invoke([...])
except Exception as e:
    if _is_rate_limited(e):
        pytest.skip(f"Rate limited: {e}")
    raise
```

This keeps rate-limit failures out of the red-test column.
