# API reference

FastAPI server on `http://127.0.0.1:8001` by default.

## Run endpoints

### `POST /run/{run_type}`

Triggers an analysis run in the background. `run_type` is one of `morning`, `midday`, `evening`, `weekly`.

```bash
curl -X POST http://localhost:8001/run/morning
```

Response:
```json
{"run_id": "a1b2c3d4", "status": "started"}
```

The actual graph executes asynchronously — stream events via `/stream/{run_id}`.

### `GET /stream/{run_id}`

Server-Sent Events stream for a specific run. Each event is one of:

| Event | Data shape |
|-------|-----------|
| `agent_start` | `{"agent": "news_analyst"}` |
| `agent_end` | `{"agent": "news_analyst", "summary": "..."}` |
| `tool_start` | `{"tool": "fetch_stock_news", "input": "..."}` |
| `tool_end` | `{"tool": "fetch_stock_news", "output": "..."}` |
| `llm_stream` | `{"token": "..."}` |
| `run_complete` | `{"status": "completed", "report": "..."}` |
| `error` | `{"message": "..."}` |

Returns 404 if the run_id is unknown.

### `GET /runs`

Lists all known runs (most recent first), including their current status and event count.

## Data endpoints (`/api/*`)

### `GET /api/history`

Last 30 runs from SQLite (`runs` table). Newest first.

### `GET /api/accuracy`

Per-ticker hit rate over the last 30 days:
```json
{
  "total_predictions": 142,
  "by_ticker": {
    "RELIANCE": {"correct": 18, "total": 22, "history": [...]},
    ...
  }
}
```

Hit rules: `BUY` correct when actual pct > 0.5, `SELL` correct when pct < -0.5, `HOLD` correct when |pct| ≤ 1.0.

### `GET /api/usage`

Gemini API spend, summed by model:
```json
{
  "today":  {"total_cost": 0.0042, "by_model": {"gemini-2.0-flash": {...}}},
  "month":  {"total_cost": 0.1180, ...}
}
```

### `GET /api/portfolio`

Live snapshot from Zerodha Kite (or cached fallback if Kite is unavailable):
```json
{"holdings": "...", "positions": "...", "pnl": "..."}
```

## Kite auth

### `GET /kite/login`

Returns an HTML page that meta-redirects to Zerodha's OAuth login. Visit it in a browser.

### `GET /kite/callback?request_token=...&status=success`

Zerodha's redirect target. Exchanges the `request_token` for a session via `kite.generate_session()`, saves the resulting `access_token` to `.env`, and renders a success / error HTML page.

### `POST /kite/postback`

Placeholder for order-execution webhooks. Not wired up yet.

## Static dashboard

`GET /` and any other unmatched path is served from `src/server/static/`:
- `index.html` — Bootstrap 5 dark dashboard
- `js/stream.js` — `EventSource` consumer that updates DOM in real time

The dashboard subscribes to `/stream/{run_id}` after triggering a run and lights up each agent box as `agent_start` events arrive.
