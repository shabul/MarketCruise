# Quick Reference

## Core Entry Points

- `main.py`: CLI for server, daily runs, weekly feedback, and Kite token updates.
- `src/server/app.py`: FastAPI app factory, config singleton, memory singleton.
- `src/server/routes/runs.py`: `POST /run/{type}`, `GET /stream/{run_id}`, `GET /runs`.
- `src/server/routes/api.py`: history, accuracy, usage, portfolio endpoints.

## Actual Runtime Flow

### Daily

1. `load_context`
2. `news_analyst`
3. `technical_analyst`
4. `portfolio_risk`
5. `synthesize`
6. `save`

### Weekly

1. `load_data`
2. `compute_accuracy`
3. `generate_feedback`
4. `save_feedback`

## Main Modules

- `src/agents/base.py`: Gemini model factory, fallback handling, pricing helpers.
- `src/agents/news_analyst.py`: news-only agent.
- `src/agents/technical_analyst.py`: technical and index agent.
- `src/agents/portfolio_risk.py`: holdings, positions, P&L, FII/DII agent.
- `src/agents/orchestrator.py`: synthesis and JSON prediction extraction.
- `src/memory/memory_manager.py`: read/write facade over SQLite and Chroma.
- `src/memory/sqlite_store.py`: structured persistence.
- `src/memory/chroma_store.py`: semantic persistence.

## Key Data Stores

- SQLite tables: `runs`, `predictions`, `actuals`, `hypotheses`, `usage_log`
- Chroma collections: `stock_events`, `market_regimes`, `lessons_learned`, `hypothesis_ledger`

## Tool Groups

- `src/tools/market_tools.py`: yfinance snapshots and indices.
- `src/tools/news_tools.py`: NewsAPI or Google RSS fallback.
- `src/tools/nse_tools.py`: FII/DII, market breadth, corporate events.
- `src/tools/portfolio_tools.py`: Zerodha holdings, positions, trades, portfolio P&L.

## Known Doc Drift

- `README.md` is stale and says implementation is not published.
- High-level plan docs describe a richer supervisor architecture than the code currently implements.
- `.claude` quick reference has some schema details that no longer exactly match SQLite column names.
