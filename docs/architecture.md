# Architecture

## Agents

Four specialized LangGraph agents in `src/agents/`, all built on `ChatGoogleGenerativeAI`:

| Agent | Tools | Output field |
|-------|-------|--------------|
| `news_analyst` | `fetch_stock_news`, `fetch_sector_news`, `fetch_macro_news` | `news_analysis` |
| `technical_analyst` | `fetch_price_snapshot`, `fetch_intraday_snapshot`, `fetch_eod_snapshot`, `fetch_index_snapshot`, `fetch_market_breadth` | `technical_analysis` |
| `portfolio_risk` | `fetch_holdings`, `fetch_positions`, `fetch_todays_trades`, `calculate_portfolio_pnl`, `fetch_fii_dii` | `portfolio_analysis` |
| `orchestrator` | (none — synthesizes the above) | `final_analysis` + `predictions` |

The first three use `create_react_agent` from LangGraph. The orchestrator calls the LLM directly and extracts a structured `predictions` dict via regex on a ```json``` code block.

## Daily graph (`src/graphs/daily_graph.py`)

```
load_context → news_analyst → technical_analyst → portfolio_risk → synthesize → save → END
```

Each node returns a partial `MarketState` update; routing reads `state["next_agent"]`. `load_context` calls `MemoryManager.load_run_context(...)` to pull retrieved memories and last week's feedback into the state.

`stream_daily()` exposes `graph.astream_events(version="v2")` so the FastAPI SSE route can translate events into `agent_start` / `agent_end` / `tool_start` / `tool_end` / `llm_stream` for the dashboard.

## Memory (`src/memory/`)

- **`sqlite_store.py`** — 5 tables: `runs`, `predictions`, `actuals`, `hypotheses`, `usage_log`. All timestamps are `datetime.now(timezone.utc).isoformat()` (UTC). Aggregation queries use `LIKE '<prefix>%'` on the `ts` column.
- **`chroma_store.py`** — 4 collections via `DefaultEmbeddingFunction` (local, no API):
  - `stock_events` — predictions + actuals (per ticker, per run)
  - `market_regimes` — periodic snapshots of market state
  - `lessons_learned` — weekly feedback reports
  - `hypothesis_ledger` — open/closed hypotheses with outcomes
- **`memory_manager.py`** — unified facade. `load_run_context` retrieves top-k stock_events + latest lesson. `save_run_predictions` / `save_actuals` **dual-write** to SQLite and ChromaDB.

## Feedback loop (`src/graphs/feedback_graph.py`)

Runs once per week (Monday). Pulls last week's `predictions` and `actuals` from SQLite, computes per-ticker accuracy (BUY hit if pct > 0.5%, SELL hit if pct < -0.5%, HOLD hit if |pct| ≤ 1.0%), then calls `gemini-2.5-pro` to write a structured lessons report. The report is stored in ChromaDB `lessons_learned` and is automatically injected into all future agent prompts via `load_run_context`.

## Web layer (`src/server/`)

- **`app.py`** — `create_app(config_path)` factory; sets module-level `_config` and `_memory` singletons (`get_config()`, `get_memory()` accessors)
- **`routes/runs.py`** — `POST /run/{type}` fires an async background task that streams LangGraph events into a per-run buffer; `GET /stream/{run_id}` is an `EventSourceResponse` that drains the buffer
- **`routes/api.py`** — `/api/history`, `/api/accuracy` (30-day window), `/api/usage` (today + month), `/api/portfolio` (live Kite holdings + positions + P&L)
- **`routes/kite_auth.py`** — `/kite/login` redirects to Zerodha OAuth; `/kite/callback` exchanges `request_token` for `access_token` via `kite.generate_session()` and saves to `.env` via `python-dotenv`'s `set_key()`

## State schemas (`src/state/schema.py`)

```python
class MarketState(TypedDict):
    run_id: str; run_type: str; watchlist: list[str]; config: dict
    retrieved_memories: list[str]; feedback_context: str; next_agent: str
    news_analysis: str; technical_analysis: str; portfolio_analysis: str
    final_analysis: str; predictions: dict
    messages: Annotated[list[BaseMessage], add_messages]

class FeedbackState(TypedDict):
    week_label: str; prediction_records: list[dict]; actual_records: list[dict]
    accuracy_stats: dict; synthesized_feedback: str
    messages: Annotated[list[BaseMessage], add_messages]
```

## Sequence of a morning run

1. Cron fires `curl -X POST http://localhost:8001/run/morning` at 8 AM IST
2. `trigger_run` creates a `run_id`, fires `_execute_run` as `asyncio.create_task`
3. `stream_daily` yields LangGraph events; route translates each into an SSE event and appends to `_runs[run_id]["events"]`
4. Any open browser tab streaming `/stream/{run_id}` receives events in real time (sees agents lighting up, tool inputs/outputs, LLM tokens)
5. On `END`, `save_and_finish` writes predictions to memory and marks the run completed in SQLite
