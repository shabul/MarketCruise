---
description: Start the MarketCruise FastAPI server or trigger a run via HTTP
---

Manage the MarketCruise FastAPI server on port 8001.

## Common operations

**Start the server (background):**
```bash
python main.py --server
```
Listens on `http://127.0.0.1:8001`. Static dashboard at `/`.

**Trigger a run from the CLI:**
```bash
curl -X POST http://localhost:8001/run/morning   # also: midday | evening | weekly
```

**Watch a live run (SSE):**
```bash
curl -N http://localhost:8001/stream/<run_id>
```

**Check what's running:**
```bash
curl -s http://localhost:8001/runs | jq
```

**Inspect persisted data:**
```bash
curl -s http://localhost:8001/api/history  | jq
curl -s http://localhost:8001/api/accuracy | jq
curl -s http://localhost:8001/api/usage    | jq
curl -s http://localhost:8001/api/portfolio | jq
```

## Things to remember

- The server holds a module-level `_config` and `_memory` singleton — restarting picks up `config.yaml` changes
- `_runs` dict in `src/server/routes/runs.py` is in-memory only; restarting drops the SSE event buffer for in-flight runs
- Kite tokens expire daily ~6 AM IST — if `/api/portfolio` returns "unavailable", visit `/kite/login` to re-auth
- For development, run with `--reload` is NOT supported by `main.py` directly; restart the process manually
