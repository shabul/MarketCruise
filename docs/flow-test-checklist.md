# Flow Test Checklist

This checklist focuses on end-to-end correctness, not just "route returns 200".

## 1. Run Trigger and Identity

- What to test: `POST /run/{type}` creates a run and the same `run_id` is preserved through graph execution and SQLite persistence.
- How to test:
  - Trigger `POST /run/morning`
  - Capture the returned `run_id`
  - Wait for completion through `/runs` or `/stream/{run_id}`
  - Confirm the latest `/api/history` row has the same `run_id`

## 2. SSE Event Flow

- What to test: the browser stream sees the full sequence for a run.
- How to test:
  - Open `/stream/{run_id}` immediately after triggering a run
  - Verify `agent_start` / `agent_end` events appear for:
    - `load_context`
    - `news_analyst`
    - `technical_analyst`
    - `portfolio_risk`
    - `options_analyst`
    - `synthesize`
  - Verify a final `run_complete` event is emitted

## 3. Morning Prediction Persistence

- What to test: orchestrator predictions are saved and can be retrieved from the API.
- How to test:
  - Run a morning analysis
  - Check `/api/predictions/today`
  - Confirm predicted tickers, directions, confidence, and optional trade fields are present

## 4. Evening Actual Persistence

- What to test: evening runs save actual market outcomes for watchlist stocks.
- How to test:
  - Trigger an evening run
  - Confirm the technical analysis output includes parseable price-change lines
  - Verify SQLite `actuals` rows were created for the watchlist
  - Confirm `/api/accuracy` reflects the new actuals

## 5. Accuracy Across Multiple Days

- What to test: repeated predictions for the same ticker are matched by both ticker and date.
- How to test:
  - Seed or generate predictions for the same ticker on two dates
  - Seed matching actuals on those same two dates
  - Verify `/api/accuracy` reports two history entries, not one overwritten entry

## 6. Weekly Feedback Persistence

- What to test: weekly feedback is persisted and visible from the API.
- How to test:
  - Seed last week's predictions and actuals
  - Trigger `POST /run/weekly`
  - Verify `/api/feedback` returns the latest report
  - Verify the weekly run appears in `/api/history`

## 7. Override Handling

- What to test: request-body overrides actually reach the graph.
- How to test:
  - Trigger `POST /run/morning` with a custom `watchlist` and `model`
  - Confirm streamed analysis references that watchlist
  - Confirm persisted predictions align with the override

## 8. Failure Handling

- What to test: tool or agent errors propagate cleanly.
- How to test:
  - Force a tool or agent failure
  - Verify the run status becomes `error`
  - Verify the stream emits an `error` event and then `run_complete`

## 9. Portfolio Endpoint Fallbacks

- What to test: `/api/portfolio` remains usable with missing or unavailable Kite data.
- How to test:
  - Call `/api/portfolio` with no valid live token
  - Confirm the response remains structured and does not hang or crash

## 10. Frontend Dashboard Flow

- What to test: the dashboard reflects a run from trigger to completion.
- How to test:
  - Load the UI
  - Trigger a run from the interface
  - Confirm agents light up in order, streamed text appears, and the final report renders
  - Refresh after completion and confirm history/feedback sections still load

## Recommended Commands

```bash
uv run pytest tests/unit/ -q
uv run pytest tests/functional/test_daily_graph_flow.py tests/functional/test_server_api.py -q
uv run pytest tests/functional/test_daily_graph.py -v --timeout=300
uv run pytest tests/e2e/test_full_morning_run.py -v --timeout=300
uv run pytest tests/integration/ -v --timeout=300
```
