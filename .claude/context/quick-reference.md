# Quick reference

Compact lookup for code locations, function signatures, and common operations.

## File map

| Concern | File |
|---------|------|
| LLM factory + cost + quota detection | `src/agents/base.py` |
| News agent | `src/agents/news_analyst.py` |
| Technical agent | `src/agents/technical_analyst.py` |
| Portfolio agent | `src/agents/portfolio_risk.py` |
| Synthesis (no tools) | `src/agents/orchestrator.py` |
| Daily LangGraph | `src/graphs/daily_graph.py` |
| Weekly feedback graph | `src/graphs/feedback_graph.py` |
| State TypedDicts | `src/state/schema.py` |
| SQLite store | `src/memory/sqlite_store.py` |
| Chroma store | `src/memory/chroma_store.py` |
| Memory facade | `src/memory/memory_manager.py` |
| FastAPI factory | `src/server/app.py` |
| `/run/*` + `/stream/*` | `src/server/routes/runs.py` |
| `/api/*` | `src/server/routes/api.py` |
| `/kite/login` + `/kite/callback` | `src/server/routes/kite_auth.py` |
| Market data tools | `src/tools/market_tools.py` |
| News tools | `src/tools/news_tools.py` |
| NSE FII/DII/breadth tools | `src/tools/nse_tools.py` |
| Kite portfolio tools | `src/tools/portfolio_tools.py` |
| CLI entry | `main.py` |

## Tool invocation signatures

All return `str`. None raise — failure returns an error string.

```python
fetch_price_snapshot.invoke({"tickers": ["RELIANCE", "TCS"]})
fetch_intraday_snapshot.invoke({"tickers": ["RELIANCE"]})
fetch_eod_snapshot.invoke({"tickers": ["TCS"]})
fetch_index_snapshot.invoke({})

fetch_stock_news.invoke({"ticker": "TCS", "hours": 24, "max_articles": 5})
fetch_sector_news.invoke({"sector": "IT", "hours": 48})
fetch_macro_news.invoke({"hours": 24})

fetch_fii_dii.invoke({})
fetch_market_breadth.invoke({})
fetch_corporate_events.invoke({"tickers": ["RELIANCE", "TCS"]})

fetch_holdings.invoke({})
fetch_positions.invoke({})
fetch_todays_trades.invoke({})
calculate_portfolio_pnl.invoke({})
```

## State schema (`MarketState`)

```python
{
    "run_id": str,                    # 8-char uuid prefix
    "run_type": "morning" | "midday" | "evening" | "weekly",
    "watchlist": list[str],           # NSE tickers without .NS suffix
    "config": dict,                   # gemini sub-config
    "retrieved_memories": list[str],  # from ChromaDB stock_events
    "feedback_context": str,          # latest weekly lesson
    "next_agent": str,                # routing key for daily_graph.route_agent
    "news_analysis": str,
    "technical_analysis": str,
    "portfolio_analysis": str,
    "final_analysis": str,
    "predictions": dict,              # {"stocks": [{"ticker":, "direction": "BUY|SELL|HOLD", "confidence":, "rationale":}]}
    "messages": list[BaseMessage],    # langchain message log
}
```

## SQLite schema (5 tables)

| Table | Key columns |
|-------|-------------|
| `runs` | `run_id`, `run_type`, `started_at`, `completed_at`, `status`, `summary` |
| `predictions` | `run_id`, `date`, `ticker`, `direction`, `confidence`, `rationale` |
| `actuals` | `date`, `ticker`, `close`, `pct_change`, `volume` (insert-or-replace on `(date, ticker)`) |
| `hypotheses` | `id`, `text`, `status`, `created_at`, `updated_at` |
| `usage_log` | `ts`, `model`, `input_tokens`, `output_tokens`, `cost_usd` |

## ChromaDB collections

| Collection | Document content |
|------------|------------------|
| `stock_events` | Per-ticker prediction or actual entries (semantic retrieval) |
| `market_regimes` | Periodic snapshots of broad-market state |
| `lessons_learned` | Weekly feedback reports (IDs are week labels like `2026-W19`) |
| `hypothesis_ledger` | Open / closed hypotheses with outcomes |

## HTTP endpoints

```
POST   /run/{morning|midday|evening|weekly}   → {run_id, status}
GET    /stream/{run_id}                       → SSE (agent_start, agent_end, tool_start, tool_end, llm_stream, run_complete)
GET    /runs                                  → [{id, type, status, started_at, ...}]
GET    /api/history                           → last 30 runs
GET    /api/accuracy                          → {total_predictions, by_ticker}
GET    /api/usage                             → {today: {...}, month: {...}}
GET    /api/portfolio                         → {holdings, positions, pnl}
GET    /kite/login                            → HTML meta-refresh → Zerodha OAuth
GET    /kite/callback?request_token=...       → exchanges + saves to .env, returns success/error HTML
POST   /kite/postback                         → placeholder
```

## Gemini model reference (verified 2026-05-13)

| Use | Model | Pricing (input/output $/1M) |
|-----|-------|------------------------------|
| Default | `gemini-2.0-flash` | 0.10 / 0.40 |
| Fallback (on 429) | `gemini-2.5-flash` | 0.15 / 0.60 |
| Heavy (weekly feedback) | `gemini-2.5-pro` | 1.25 / 10.00 |

If models 404, list current names with `client.models.list()` — see `.claude/commands/check-gemini.md`.

## Useful one-liners

```bash
# Recent runs from SQLite
uv run python -c "
import sqlite3
c = sqlite3.connect('data/market_cruise.db')
for r in c.execute('SELECT run_id, run_type, status, started_at FROM runs ORDER BY started_at DESC LIMIT 10'): print(r)
"

# Today's Gemini spend
curl -s http://localhost:8001/api/usage | jq '.today.total_cost'

# Latest lesson
uv run python -c "
from src.memory.chroma_store import ChromaStore
print(ChromaStore('data/chroma').retrieve_latest_lesson())
"

# Reset memory (DESTRUCTIVE — confirms first via prompt only with the user)
rm -rf data/chroma data/market_cruise.db
```
