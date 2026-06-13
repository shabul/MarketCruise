<div align="center">

# 📈 MarketCruise

### Personal AI stock analyst for Indian markets — 5 agents, live Zerodha data, self-improving memory

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B35?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Gemini_2.0_Flash-Primary_LLM-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Live_Dashboard-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Memory-FF4B4B?style=for-the-badge&logo=databricks&logoColor=white)](https://www.trychroma.com)
[![Zerodha](https://img.shields.io/badge/Zerodha_Kite-Live_Portfolio-387ED1?style=for-the-badge)](https://kite.trade)
[![NSE](https://img.shields.io/badge/NSE-Options_%2B_FII%2FDII-1A237E?style=for-the-badge)](https://nseindia.com)

<br/>

> **5 AI agents. 3 runs a day. 1 WhatsApp message every morning.**
>
> MarketCruise watches your Nifty watchlist, reads options flow and FII/DII data,
> checks your Zerodha portfolio, cross-examines its own predictions with a Devil's Advocate,
> and gets smarter every week — all automatically.

<br/>

![runs](https://img.shields.io/badge/Runs-Morning_%7C_Midday_%7C_Evening_%7C_Weekly-brightgreen?style=flat-square)
![models](https://img.shields.io/badge/Models-Gemini_2.0_Flash_%2F_2.5_Pro-4285F4?style=flat-square&logo=google)
![memory](https://img.shields.io/badge/Memory-ChromaDB_%2B_SQLite-FF4B4B?style=flat-square)
![market](https://img.shields.io/badge/Market-NSE_%2F_BSE_%2F_Indian_Indices-1A237E?style=flat-square)
![alerts](https://img.shields.io/badge/Alerts-WhatsApp_via_Pocket_Brain-25D366?style=flat-square&logo=whatsapp)

</div>

---

## How it works

```
                         ┌─────────────────────────────────────────┐
                         │     MarketCruise — LangGraph Pipeline    │
                         └─────────────────────────────────────────┘

  Every morning (08:00), midday (14:00), evening (22:00) IST — cron fires:
  curl -X POST http://localhost:8001/run/morning

                         ┌──────────────────────┐
                         │     load_context      │
                         │  • ChromaDB recall    │
                         │  • Weekly feedback    │
                         │  • Market regime      │
                         │  • Global premarket   │
                         │    (S&P, Nasdaq,      │
                         │    Nikkei, Crude)     │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │         news_analyst            │
                    │  Tools: stock news, sector      │
                    │  news, macro news               │
                    │  → Sentiment per stock          │
                    │  → Top 3 market-moving items    │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │       technical_analyst         │
                    │  Tools: price snapshot,         │
                    │  intraday, EOD, index,          │
                    │  market breadth                 │
                    │  → MA levels, momentum          │
                    │  → Support / resistance         │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │        portfolio_risk           │
                    │  Tools: Zerodha holdings,       │
                    │  positions, trades, P&L,        │
                    │  FII/DII data                   │
                    │  → HOLD / EXIT / PARTIAL calls  │
                    │  → Concentration risk flags     │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │        options_analyst          │
                    │  Tools: NSE options chain,      │
                    │  index options (Nifty/BankNifty)│
                    │  → PCR interpretation           │
                    │  → Max pain, OI support/resist  │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │     orchestrator (synthesize)   │
                    │  • Reads all 4 analyses         │
                    │  • Resolves conflicts           │
                    │  • Writes final markdown report │
                    │  • Extracts BUY/SELL/HOLD calls │
                    │  • Devil's Advocate review ──►  │
                    │    "3 reasons this BUY is wrong"│
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │             save                │
                    │  • SQLite: predictions, runs    │
                    │  • ChromaDB: stock events       │
                    │  • SSE: streams to browser      │
                    └────────────────────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │       Pocket Brain (phone)      │
                    │  Polls via Tailscale → formats  │
                    │  WhatsApp alert → sends it      │
                    └────────────────────────────────┘
```

---

## The 5 Agents

### 🗞️ News Analyst
Fetches and interprets market news using three tools:

| Tool | What it fetches |
|------|----------------|
| `fetch_stock_news` | Per-ticker news for the last 8–24 hours (RSS + web) |
| `fetch_sector_news` | IT, Banking, Auto, Energy sector themes |
| `fetch_macro_news` | RBI, inflation, global macro events |

**Output:** Sentiment score per stock (Bullish / Neutral / Bearish), top 3 market-moving stories, cross-stock sector themes, sudden-move flags.

---

### 📉 Technical Analyst
Reads price data and identifies actionable technical signals:

| Tool | Used in |
|------|---------|
| `fetch_price_snapshot` | All runs — previous close, 52w high/low, MAs |
| `fetch_intraday_snapshot` | Midday runs — live prices, intraday momentum |
| `fetch_eod_snapshot` | Evening runs — day's OHLCV |
| `fetch_index_snapshot` | All runs — Nifty50, Sensex, Nasdaq, S&P500 |
| `fetch_market_breadth` | All runs — advance/decline ratio, A/D line |

**Output:** Rating per stock (Strong Buy → Strong Sell), 20/50/200 MA levels, support/resistance, volume anomalies.

---

### 💼 Portfolio Risk Analyst
Connects to your live Zerodha account and makes explicit position calls:

| Tool | What it does |
|------|--------------|
| `fetch_holdings` | Live holdings from Kite API (falls back to cache) |
| `fetch_positions` | Open intraday positions |
| `fetch_todays_trades` | Completed orders for post-trade review |
| `calculate_portfolio_pnl` | Total value, cost basis, unrealized P&L % |
| `fetch_fii_dii` | FII / DII net buy/sell from NSE — impact on holdings |

**Morning:** Portfolio status entering the day + FII/DII read.
**Midday:** HOLD / EXIT / PARTIAL EXIT call for each open position.
**Evening:** Trade timing review + day's P&L.

---

### 🎯 Options Flow Analyst
Reads NSE options chain to find where institutional money is positioned:

| Signal | Interpretation |
|--------|----------------|
| PCR > 1.2 | Heavy put buying — institutions hedging downside |
| PCR < 0.7 | Heavy call buying — bullish institutional sentiment |
| PCR 0.7–1.2 | Neutral positioning |
| Top CE OI strikes | Key resistance levels |
| Top PE OI strikes | Key support levels |

Fetches Nifty, Bank Nifty, and key watchlist stock options chains. Skipped on evening runs (market closed).

---

### 🧠 Orchestrator — Chief Analyst
Synthesizes all four reports into one final analysis:

1. **Resolves conflicts** — News says bullish but technicals say overbought? Orchestrator adjudicates.
2. **Market regime weighting** — In high-volatility regimes, all confidence scores are downgraded one level.
3. **Writes the report** with structured sections: Market Mood · Top Opportunities · Risk Flags · Quick Signals · Positioning Notes
4. **Extracts BUY/SELL/HOLD calls** — structured JSON with entry price, stop loss, target, timeframe.
5. **Devil's Advocate review** — A contrarian sub-prompt challenges every BUY or SELL prediction with 3 specific reasons it could be wrong, then rates the full set: **Actionable / Tentative / Avoid**.

```
## Devil's Advocate Review
**Overall Conviction: Actionable**

TCS BUY — Counter-arguments:
1. IT sector FII selling persists for 3rd consecutive week
2. USDINR above 84 compresses export margins
3. 200 DMA resistance not yet cleared on weekly chart
```

---

## Memory Architecture

MarketCruise accumulates intelligence over weeks. Every run reads from memory before analyzing and writes back after.

### ChromaDB — Vector Store (semantic recall)

| Collection | Stores | Used by |
|------------|--------|---------|
| `stock_events` | Past predictions + outcomes + news events per ticker | All agents — "last time INFY was at this level..." |
| `market_regimes` | Named macro contexts: "FII selling phase", "rate cut rally" | Orchestrator — pattern match to current setup |
| `lessons_learned` | Weekly feedback summaries embedded as vectors | Morning load_context node |
| `hypothesis_ledger` | Every hypothesis + evidence + resolution | Weekly feedback graph |

### SQLite — Structured Store

| Table | Stores |
|-------|--------|
| `predictions` | run_id, ticker, direction, confidence, reasoning, entry/stop/target |
| `actuals` | Daily EOD prices — used to score past predictions |
| `hypotheses` | Long-term thesis tracking with open/close lifecycle |
| `usage_log` | Token counts + cost per model per agent per run |
| `runs` | Run metadata + full report text |

### Weekly Self-Improvement Loop

Every Monday 07:00 IST, the feedback graph runs:

```
load_week_hypotheses → compute_accuracy → feedback_agents → orchestrator_synthesis
        → update_chroma_memory → save_feedback_json
```

Each agent reviews its own prediction accuracy from the past week. Lessons are embedded into ChromaDB and injected into every subsequent morning run as system context.

---

## Live Dashboard

```
python main.py --server   →   http://localhost:8001
```

Real-time SSE streaming — the browser lights up as each agent runs:

```
┌──────────────────────────────────────────────────────────────────┐
│  MarketCruise  [● LIVE]                    [Run Now ▾]  09:15 IST│
├─────────────┬────────────────────────────────────────────────────┤
│ Navigation  │  AGENT PIPELINE            14 Jun · Morning Run    │
│             │  ✓ load_context    ✓ news_analyst                  │
│ ● Today     │  ⟳ technical_analyst   ○ portfolio   ○ options     │
│ ○ History   │                                                     │
│ ○ Portfolio │  TOOL CALLS                                        │
│ ○ Accuracy  │  ▼ fetch_stock_news("TCS", hours=24)              │
│ ○ API Usage │    → 4 articles, sentiment: Bullish               │
│             │  ▼ fetch_price_snapshot(["TCS","INFY"...])        │
│             │    → streaming...                                  │
│             │                                                     │
│             │  FINAL ANALYSIS (streaming)                        │
│             │  ## Market Mood                                    │
│             │  Cautiously bullish. IT sector leading...          │
└─────────────┴────────────────────────────────────────────────────┘
```

**SSE event types streamed from LangGraph:**
`agent_start` → `tool_start` → `tool_end` → `llm_stream` → `agent_end` → `run_complete`

**API endpoints:**

| Endpoint | What |
|----------|------|
| `POST /run/{morning\|midday\|evening\|weekly}` | Trigger a run |
| `GET /stream/{run_id}` | SSE stream of a live run |
| `GET /api/history` | Recent runs with report text |
| `GET /api/predictions/today` | Today's BUY/SELL/HOLD calls |
| `GET /api/accuracy` | 30-day accuracy by ticker |
| `GET /api/portfolio` | Live Zerodha holdings + P&L |
| `GET /api/market/premarket` | Nifty, BankNifty, VIX, USD/INR, Crude, S&P500 |
| `GET /api/hypotheses` | Open/closed hypothesis ledger |
| `GET /kite/login` | Start Zerodha OAuth flow |

---

## Gemini Model Strategy

| Model | Used for | Why |
|-------|----------|-----|
| `gemini-2.0-flash` | All 4 sub-agents (daily) | Fast, cheap, handles tool use well |
| `gemini-2.5-flash` | Automatic fallback on quota/429 | Same speed, different quota pool |
| `gemini-2.5-pro` | Weekly feedback synthesis | Deeper reasoning for accuracy review |

All model calls are logged to SQLite `usage_log` with token counts and USD cost. View them live at `/api/usage`.

---

## Zerodha Kite Integration

Connect once, stays connected:

```bash
# Step 1 — Open login in browser (from the dashboard)
GET http://localhost:8001/kite/login

# Step 2 — Zerodha redirects back with request_token
# MarketCruise auto-exchanges it for access_token and saves to .env

# Step 3 — Or set token directly
python main.py --set-kite-token YOUR_ACCESS_TOKEN
```

The portfolio tools fall back to a JSON cache if the Kite token expires — runs continue uninterrupted.

---

## Cron Schedule

```bash
bash cron_setup.sh   # installs all 4 entries
```

| Time (IST) | Days | Run |
|------------|------|-----|
| Mon 07:00 | Weekly | Self-improvement feedback loop |
| Mon–Fri 08:00 | Daily | Morning briefing |
| Mon–Fri 14:00 | Daily | Midday position check |
| Mon–Fri 22:00 | Daily | Evening review + P&L |

Cron calls the FastAPI server via HTTP — the browser gets live SSE streaming even if it connects mid-run.

---

## Watchlist

Default in `config.yaml` (edit freely):

```
RELIANCE · TCS · INFY · HDFCBANK · ICICIBANK
WIPRO · AXISBANK · SBIN · BAJFINANCE · MARUTI
```

Indices tracked: Nifty 50, Sensex, S&P 500, Nasdaq (global premarket context for morning runs).

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/shabul/MarketCruise.git
cd MarketCruise
pip install uv && uv sync

# 2. Configure
cp .env.template .env
# Fill in: GEMINI_API_KEY, KITE_API_KEY, KITE_API_SECRET

# 3. Start the server
python main.py --server
# → http://localhost:8001

# 4. Connect Zerodha (one-time)
open http://localhost:8001/kite/login

# 5. Set up cron (Mac)
bash cron_setup.sh

# 6. Or run manually
python main.py --run morning
python main.py --run weekly
```

---

## Project Structure

```
MarketCruise/
│
├── 📄 config.yaml              # Watchlist, schedules, Gemini models, news settings
├── 🚀 main.py                  # Entry point: --server | --run | --set-kite-token
├── 📜 cron_setup.sh            # Installs macOS crontab entries
│
├── 🤖 src/agents/
│   ├── orchestrator.py         # Chief Analyst — synthesizes + Devil's Advocate
│   ├── news_analyst.py         # News sentiment + macro events
│   ├── technical_analyst.py    # Price patterns + MA signals
│   ├── portfolio_risk.py       # Zerodha P&L + HOLD/EXIT calls
│   └── options_analyst.py      # NSE options chain + PCR + OI
│
├── 🔗 src/graphs/
│   ├── daily_graph.py          # LangGraph: load → news → tech → portfolio → options → synthesize → save
│   └── feedback_graph.py       # Weekly: accuracy → lessons → ChromaDB update
│
├── 🛠️  src/tools/
│   ├── market_tools.py         # Price snapshots, indices, global premarket, market regime
│   ├── news_tools.py           # RSS + web news for stocks, sectors, macro
│   ├── nse_tools.py            # FII/DII, market breadth, events calendar
│   ├── options_tools.py        # NSE options chain (PCR, OI, max pain)
│   └── portfolio_tools.py      # Zerodha Kite — holdings, positions, trades, P&L
│
├── 🧠 src/memory/
│   ├── chroma_store.py         # ChromaDB: stock_events, regimes, lessons, hypotheses
│   ├── sqlite_store.py         # SQLite: predictions, actuals, usage, runs
│   └── memory_manager.py       # Unified load/save interface for all agents
│
├── 🌐 src/server/
│   ├── app.py                  # FastAPI app
│   └── routes/
│       ├── runs.py             # POST /run/* + GET /stream/* (SSE)
│       ├── api.py              # GET /api/history, accuracy, portfolio, premarket
│       └── kite_auth.py        # Zerodha OAuth flow
│
└── 🧪 tests/
    ├── unit/                   # No external I/O
    ├── integration/            # Hits real APIs
    ├── functional/             # Full graph runs
    └── e2e/                    # HTTP end-to-end
```

---

## Related

[![Pocket Brain](https://img.shields.io/badge/GitHub-pocket--brain-181717?style=for-the-badge&logo=github)](https://github.com/shabul/pocket-brain)

**[Pocket Brain](https://github.com/shabul/pocket-brain)** — An old Samsung Galaxy running a 24/7 hub that polls MarketCruise every hour via Tailscale, caches the analysis, shows your Zerodha portfolio, and automatically sends you a WhatsApp message every morning and evening with today's calls.

---

<div align="center">

**Built with [Claude Fable 5](https://claude.ai) — Max Effort mode via Claude Code**

*Multi-agent architecture, ChromaDB memory design, Devil's Advocate review system,
Zerodha integration, and the weekly self-improvement loop — all designed
and iterated through an agentic coding session with Fable 5 Max effort.*

<br/>

[![Star this repo](https://img.shields.io/github/stars/shabul/MarketCruise?style=social)](https://github.com/shabul/MarketCruise)

</div>
