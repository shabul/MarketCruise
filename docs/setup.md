# Setup

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Zerodha account (only needed if you want live portfolio data)

## Install

```bash
git clone https://github.com/shabul/MarketCruise.git
cd MarketCruise
uv sync                       # installs runtime + dev dependencies
cp .env.template .env         # then fill in keys (see below)
```

## Environment variables (`.env`)

| Key | Required? | Where to get it |
|-----|-----------|-----------------|
| `GEMINI_API_KEY` | yes | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `NEWS_API_KEY` | no (RSS fallback) | [newsapi.org](https://newsapi.org) |
| `KITE_API_KEY` | for portfolio | [developers.kite.trade](https://developers.kite.trade) |
| `KITE_API_SECRET` | for portfolio | Kite developer console |
| `KITE_ACCESS_TOKEN` | for portfolio | Auto-filled via `/kite/login` OAuth |
| `LANGCHAIN_TRACING_V2` | optional | `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | optional | [smith.langchain.com](https://smith.langchain.com) |

**Important:** `load_dotenv(override=True)` is used so the `.env` file always wins over any `GEMINI_API_KEY` already exported in your shell. If you have a stale key in your shell session, simply update `.env` — no need to `unset`.

## Zerodha Kite setup

1. Create an app at [developers.kite.trade](https://developers.kite.trade)
2. Set **Redirect URL** to `http://127.0.0.1:8001/kite/callback`
3. **Postback URL** can be left blank or pointed at `http://127.0.0.1:8001/kite/postback` (placeholder; not used yet)
4. Copy the `API Key` and `API Secret` into `.env`
5. Start the server: `python main.py --server`
6. Visit `http://localhost:8001` and click **Zerodha** in the top right
7. Complete the OAuth dance — your `KITE_ACCESS_TOKEN` is auto-saved to `.env`

Access tokens expire **daily at ~6 AM IST**. Re-run step 6 each morning, or run:

```bash
python main.py --set-kite-token <token>
```

## Cron schedule (optional)

```bash
bash cron_setup.sh
```

Installs four entries:

| Time (IST) | Day | Endpoint |
|-----------|-----|----------|
| Monday 7:00 AM | Mon | `POST /run/weekly` |
| 8:00 AM | Mon–Fri | `POST /run/morning` |
| 2:00 PM | Mon–Fri | `POST /run/midday` |
| 10:00 PM | Mon–Fri | `POST /run/evening` |

These hit the local server via curl, so the server must already be running (e.g., as a `launchd` agent or just `python main.py --server` in a tmux pane).

## Configuration (`config.yaml`)

```yaml
watchlist:                            # 10–25 NSE tickers
  - RELIANCE
  - TCS
  - INFY
  # ...

gemini:
  default_model: "gemini-2.0-flash"
  fallback_model: "gemini-2.5-flash"
  heavy_model: "gemini-2.5-pro"
  max_retries: 2

memory:
  chroma_dir: "data/chroma"
  sqlite_path: "data/market_cruise.db"
  top_k_memories: 5

server:
  host: "127.0.0.1"
  port: 8001
```

Edit the `watchlist` to match the stocks you actually care about.
