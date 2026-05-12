# MarketCruise Docs

Personal AI-powered Indian stock market (NSE/BSE) assistant. Multi-agent LangGraph system that runs three times a day (morning/midday/evening), reviews itself weekly, and shows live execution on a real-time dashboard.

## What's in here

| Doc | What it covers |
|-----|----------------|
| [architecture.md](architecture.md) | LangGraph agents, ChromaDB memory, feedback loop, data flow |
| [setup.md](setup.md) | Install, environment variables, Zerodha Kite token, cron |
| [api.md](api.md) | FastAPI endpoints — runs, streaming, history, portfolio |
| [testing.md](testing.md) | Test layers, running pytest, real-API guarantees |

## Quick start

```bash
# 1. Clone + install
uv sync
cp .env.template .env       # fill in API keys

# 2. Start server (port 8001 by default)
python main.py --server

# 3. Open http://localhost:8001 — Bootstrap dashboard
# 4. Click "Run Now → Morning" or hit POST /run/morning
```

## Stack

- **AI**: Google Gemini (gemini-2.0-flash default, gemini-2.5-flash fallback, gemini-2.5-pro heavy) via `langchain-google-genai`
- **Orchestration**: LangGraph (StateGraph + conditional routing + `astream_events`)
- **Memory**: ChromaDB (vector, 4 collections) + SQLite (structured)
- **Market data**: yfinance (NSE via `TICKER.NS`), NSE public API, NewsAPI + Google RSS
- **Portfolio**: Zerodha Kite Connect API
- **Web**: FastAPI + Server-Sent Events + Bootstrap 5 dashboard
- **Runtime**: Python 3.11+, uv, pytest
