# Conventions

## Environment Loading

- New entrypoints should use `load_dotenv(override=True)`.
- `src/server/app.py` already does this correctly.
- `main.py` still uses plain `load_dotenv()`, so treat that as technical debt, not precedent.

## Gemini Usage

- Use `_api_key()` from `src/agents/base.py` instead of reading `GEMINI_API_KEY` directly.
- Default, fallback, and heavy models come from `config.yaml`.
- Quota handling belongs in agent code via `is_quota_error()` and fallback LLM selection.

## Tool Layer Contract

- `src/tools/*.py` functions are LangChain tools and must return `str`.
- Prefer graceful error strings over exceptions because tests and SSE flows assume string outputs.

## Runtime Graph

- Daily flow is sequential, not parallel and not orchestrator-first:
  `load_context -> news_analyst -> technical_analyst -> portfolio_risk -> synthesize -> save`
- Routing depends on `next_agent`, so any new agent must be added to both the graph node list and `route_agent()`.

## Persistence

- Predictions and actuals should be written to both SQLite and ChromaDB.
- Weekly lessons are stored in ChromaDB and injected into future runs.
- Accuracy endpoints depend on SQLite; memory retrieval depends on Chroma.

## Imports

- Inside `src/server/routes/`, imports that reach `src.tools` require three dots: `from ...tools...`.

## Testing

- Unit tests cover pure logic and local persistence.
- Integration, functional, and e2e tests intentionally hit real external services.
- Gemini and Kite failures may skip tests; skips are expected, not necessarily regressions.
