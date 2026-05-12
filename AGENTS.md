# MarketCruise Agent Guide

This repository is a working Python implementation of a personal Indian market assistant. Treat the code as the source of truth over the public `README.md`, which is stale.

## Read First

1. `CLAUDE.md`
2. `.claude/README.md`
3. `.codex/README.md`
4. `src/graphs/daily_graph.py`
5. `src/server/routes/runs.py`
6. `src/memory/memory_manager.py`

## What The App Actually Does

- `main.py --server` starts FastAPI, initializes config and memory, and serves the static dashboard.
- `POST /run/{type}` starts a background run and exposes LangGraph progress over SSE.
- Daily runs are sequential: `load_context -> news_analyst -> technical_analyst -> portfolio_risk -> synthesize -> save`.
- Weekly runs compute accuracy from SQLite data, ask Gemini for lessons learned, and save that lesson into Chroma.

## Source Of Truth Conventions

- Use `load_dotenv(override=True)` anywhere new code reads `.env`.
- Use `_api_key()` from `src/agents/base.py` for Gemini access so `GOOGLE_API_KEY` stays synced.
- Tool functions in `src/tools/` must return strings and should degrade gracefully instead of raising.
- Memory writes that matter to later retrieval must dual-write to SQLite and ChromaDB.
- Relative imports inside `src/server/routes/` that target `src.tools` need `from ...tools...`.

## Important Implementation Notes

- The root `README.md` says the repo is metadata-only; that is no longer true.
- The design docs describe a supervisor-style graph, but the current code uses deterministic sequential routing through `next_agent`.
- Evening actuals are extracted by regex from the technical analysis text, so format changes there can silently affect feedback accuracy.
- SSE event payloads are buffered in process memory only. Restarting the server drops in-flight stream history.

## Main Files

- `main.py`: CLI entrypoint.
- `src/server/app.py`: app factory and singletons.
- `src/server/routes/runs.py`: run trigger plus SSE translation.
- `src/graphs/daily_graph.py`: daily runtime graph.
- `src/graphs/feedback_graph.py`: weekly feedback runtime.
- `src/agents/*.py`: agent implementations.
- `src/tools/*.py`: market, news, NSE, and portfolio tool layer.
- `src/memory/*.py`: SQLite plus Chroma persistence.

## Useful Commands

```bash
python main.py --server
python main.py --run morning
python main.py --run weekly
uv run pytest tests/unit/ -v
uv run pytest tests/functional/ -v --timeout=300
```

## Current Branch

- Default working branch for this repo: `feature/init`
