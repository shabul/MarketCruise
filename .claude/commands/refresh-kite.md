---
description: Refresh the daily-expiring Zerodha Kite access token
---

Zerodha Kite access tokens expire daily around 6 AM IST. Three ways to refresh:

## Option 1 — Browser (recommended)

1. Make sure the server is running: `python main.py --server`
2. Open `http://localhost:8001` and click the **Zerodha** button (top right)
3. Complete OAuth on `kite.zerodha.com`
4. The callback handler at `/kite/callback` exchanges `request_token` → `access_token` via `kite.generate_session()` and saves it to `.env` automatically

## Option 2 — CLI (if you already have a token)

```bash
python main.py --set-kite-token <token>
```

This updates `KITE_ACCESS_TOKEN` in `.env` and re-initializes the Kite client.

## Option 3 — Verify current token works

```bash
curl -s http://localhost:8001/api/portfolio | jq
```

If you see `unavailable` or `cached`, the token is stale — refresh via Option 1 or 2.

## How to know it expired

- `/api/portfolio` returns `"holdings": "Holdings unavailable: TokenException"`
- Functional tests in `tests/integration/test_tools_portfolio.py::test_fetch_holdings_with_kite_token` skip or fail
- The dashboard shows `[cached]` markers on the portfolio panel

Token expiry is a Zerodha-side policy, not a bug. Plan to refresh once a day before the morning run.
