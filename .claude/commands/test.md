---
description: Run the MarketCruise test suite — pick a layer or run everything
---

Run pytest for MarketCruise. Choose the right layer based on the user's intent:

- **unit** (`uv run pytest tests/unit/ -v`) — no I/O, < 5 seconds. Run this for any logic change in `memory/`, `agents/base.py`, `graphs/feedback_graph.py` accuracy math, or orchestrator JSON extraction.
- **integration** (`uv run pytest tests/integration/ -v --timeout=60`) — hits real APIs (yfinance, NewsAPI, NSE, Kite, Gemini). Run this when changing anything under `src/tools/` or `src/agents/base.py`.
- **functional** (`uv run pytest tests/functional/ -v --timeout=300`) — full agent and graph runs, plus FastAPI HTTP endpoints. Run after agent or graph changes.
- **e2e** (`uv run pytest tests/e2e/ -v --timeout=300`) — POST → SSE → completion. Slow; run only when verifying the full request lifecycle.
- **all** (`uv run pytest -v --timeout=300`) — everything; takes ~5–10 minutes.

If the user just says "run tests" without specifying a layer, ask which layer (or default to `unit + integration` for speed).

Skips are expected and not failures:
- Gemini tests skip when `GEMINI_API_KEY` is missing
- Individual Gemini tests skip on 429 / `RESOURCE_EXHAUSTED`
- Kite tests skip when `KITE_ACCESS_TOKEN` is unset

Report results back as `<passed>/<total> passed, <skipped> skipped` and mention any real failures explicitly.

Argument hint: layer name (`unit`, `integration`, `functional`, `e2e`, or `all`).
