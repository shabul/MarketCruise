Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 MarketCruise — Plan (v3: Multi-Agent + ChromaDB Memory + Live Web Dashboard)

 Context

 Build a personal AI-powered Indian market assistant with a production-grade agentic architecture:
 - 4-agent supervisor system (Orchestrator + NewsAnalyst + TechnicalAnalyst + PortfolioRisk) via LangGraph
 - ChromaDB vector memory that accumulates stock intelligence over weeks — agents retrieve semantically relevant past events before making predictions
 - Always-on FastAPI web server with a Bootstrap + SSE real-time dashboard that shows exactly which agent is running, what tools it called, inputs/outputs, and final analysis as it streams
 - Weekly self-improvement loop: agents review their own prediction accuracy, update ChromaDB with lessons learned, inject feedback into next week's runs

 ---
 Project Structure

 MarketCruise/
 ├── config.yaml
 ├── .env.template
 ├── requirements.txt
 ├── main.py                        # --server | --run [morning|midday|evening|weekly]
 ├── src/
 │   ├── server/
 │   │   ├── app.py                 # FastAPI app: mounts routes + static
 │   │   ├── routes/
 │   │   │   ├── runs.py            # POST /run/{type}, GET /stream/{run_id} (SSE)
 │   │   │   └── api.py             # GET /api/history, /api/accuracy, /api/usage, /api/portfolio
 │   │   └── static/
 │   │       ├── index.html         # Bootstrap 5 dashboard
 │   │       └── js/
 │   │           ├── stream.js      # SSE → live execution view
 │   │           └── charts.js      # Chart.js: accuracy + P&L charts
 │   ├── graphs/
 │   │   ├── daily_graph.py         # LangGraph: Supervisor + 3 sub-agents
 │   │   └── feedback_graph.py      # LangGraph: weekly prediction review
 │   ├── agents/
 │   │   ├── orchestrator.py        # Supervisor: routes tasks, synthesizes final output
 │   │   ├── news_analyst.py        # Fetches + interprets news sentiment
 │   │   ├── technical_analyst.py   # Price patterns, MAs, technicals
 │   │   └── portfolio_risk.py      # Holdings, P&L, position-level calls
 │   ├── tools/
 │   │   ├── market_tools.py        # fetch_price_snapshot, fetch_intraday, fetch_eod, fetch_indices
 │   │   ├── news_tools.py          # fetch_stock_news, fetch_sector_news, fetch_macro_news
 │   │   ├── portfolio_tools.py     # fetch_holdings, fetch_positions, fetch_trades, calc_pnl
 │   │   └── nse_tools.py           # fetch_fii_dii, fetch_events, fetch_market_breadth
 │   ├── memory/
 │   │   ├── chroma_store.py        # ChromaDB collections + embed/retrieve helpers
 │   │   ├── sqlite_store.py        # SQLite: predictions, actuals, hypotheses, usage
 │   │   └── memory_manager.py      # Unified load/save interface used by nodes
 │   └── state/
 │       └── schema.py              # MarketState TypedDict
 ├── data/
 │   ├── chroma/                    # ChromaDB persisted vector store
 │   └── market_cruise.db           # SQLite database
 ├── logs/
 └── cron_setup.sh

 ---
 LangGraph Multi-Agent Architecture

 State Schema

 class MarketState(TypedDict):
     run_id: str
     run_type: str                          # morning | midday | evening | weekly
     watchlist: list[str]
     config: dict
     retrieved_memories: list[str]          # ChromaDB semantic search results
     feedback_context: str                  # latest weekly feedback summary
     next_agent: str                        # supervisor routing decision
     news_analysis: str                     # NewsAnalyst output
     technical_analysis: str                # TechnicalAnalyst output
     portfolio_analysis: str                # PortfolioRisk output
     final_analysis: str                    # Orchestrator synthesis
     predictions: dict                      # structured predictions to persist
     messages: Annotated[list, add_messages]

 Daily Analysis Graph (daily_graph.py)

 [start] → [load_context]
               ↓
          [load_memories]        ← ChromaDB: retrieve relevant past events
               ↓
          [orchestrator] ←──────────────────────────┐
               ↓ (routes to)                         │
     ┌─────────┼──────────┐                          │
     ▼         ▼          ▼                          │
 [news]  [technical]  [portfolio]  ─── each returns result ──►
               ↓ (all done)
          [orchestrator]           ← synthesizes final analysis
               ↓
          [save_predictions]       ← SQLite + ChromaDB
               ↓
          [format_report]          ← rich terminal + SSE events to browser

 The orchestrator uses LangGraph's supervisor pattern with conditional routing:
 - Calls all three sub-agents in sequence (or parallel for morning run)
 - Each sub-agent only gets tools relevant to its domain
 - Orchestrator synthesizes and makes final calls

 Weekly Feedback Graph (feedback_graph.py)

 [load_week_hypotheses]    ← SQLite: last 5 days predictions + actuals
        ↓
 [compute_accuracy]        ← per-stock, per-signal-type hit rate
        ↓
 [feedback_agents]         ← each specialist reviews their own accuracy
        ↓
 [orchestrator_synthesis]  ← synthesized lessons + next-week adjustments
        ↓
 [update_chroma_memory]    ← embed lessons into ChromaDB
        ↓
 [save_feedback_json]      ← loaded by next morning's load_context node

 ---
 Memory Architecture (ChromaDB + SQLite)

 ChromaDB Collections

 ┌───────────────────┬──────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────┐
 │    Collection     │                        What's stored                         │                            Used by                             │
 ├───────────────────┼──────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
 │ stock_events      │ Past predictions + actuals + news events with outcomes       │ All agents — "what happened last time INFY was near 52w high?" │
 ├───────────────────┼──────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
 │ market_regimes    │ Named macro contexts ("FII selling phase", "rate cut rally") │ Orchestrator — pattern matching to current setup               │
 ├───────────────────┼──────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
 │ lessons_learned   │ Weekly feedback summaries embedded for retrieval             │ Morning load_context node                                      │
 ├───────────────────┼──────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
 │ hypothesis_ledger │ Every hypothesis with evidence + resolution                  │ Feedback graph                                                 │
 └───────────────────┴──────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────┘

 SQLite Tables

 - predictions(run_id, date, ticker, direction, confidence, reasoning, created_at)
 - actuals(date, ticker, open, close, pct_change, recorded_at)
 - hypotheses(id, date, ticker, thesis, evidence, outcome, closed_at)
 - usage_log(ts, model, task, input_tokens, output_tokens, cost_usd)
 - runs(run_id, run_type, started_at, finished_at, status, report_text)

 Memory Load at Run Start

 Every run begins with:
 1. Query ChromaDB: "Indian market {run_type} {today's date} {watchlist}"
 → retrieves top-5 semantically similar past events
 2. Load latest lessons_learned entry from ChromaDB
 3. Inject both as system context into every agent's prompt:
 "Based on similar past setups: [memories]. Last week's feedback: [feedback]"

 ---
 Real-Time Web Dashboard

 Server: python main.py --server → runs on localhost:8001
 Cron triggers: curl -X POST http://localhost:8001/run/morning (not direct Python calls)
 This ensures the browser gets live streaming even if it connects mid-run.

 UI Layout (Bootstrap 5)

 ┌─────────────────────────────────────────────────────────────┐
 │  MarketCruise   [● LIVE]              [Run Now ▾]  09:15 IST│
 ├─────────────┬───────────────────────────────────────────────┤
 │ Navigation  │  EXECUTION FLOW              May 13, Morning  │
 │             │  ┌──────────┐  ┌────────┐  ┌─────────────┐   │
 │ ● Today     │  │Orchestrat│→ │  News  │  │  Technical  │   │
 │ ○ History   │  │  or  ✓  │  │Analyst │  │  Analyst    │   │
 │ ○ Portfolio │  │          │  │ ⟳ ...  │  │  (pending)  │   │
 │ ○ Accuracy  │  └──────────┘  └────────┘  └─────────────┘   │
 │ ○ API Usage │                                               │
 │             │  TOOL CALLS                                   │
 │             │  ▼ fetch_stock_news("RELIANCE", hours=24)     │
 │             │    Input: {"ticker":"RELIANCE","hours":24}    │
 │             │    Output: 5 articles [expand ▾]             │
 │             │  ▼ fetch_price_snapshot(["TCS","INFY",...])  │
 │             │    ...streaming...                            │
 │             │                                               │
 │             │  FINAL ANALYSIS (streaming)                  │
 │             │  Market Mood: Cautiously bullish...           │
 │             │  Top Picks: TCS ↑ RELIANCE ↑ HDFC →         │
 └─────────────┴───────────────────────────────────────────────┘

 SSE Event Types (streamed from LangGraph .astream_events())

 ┌──────────────────────────┬─────────────────────────────────────┐
 │          Event           │           Frontend action           │
 ├──────────────────────────┼─────────────────────────────────────┤
 │ agent_start {name}       │ Light up agent node                 │
 ├──────────────────────────┼─────────────────────────────────────┤
 │ tool_start {name, input} │ Add tool call card                  │
 ├──────────────────────────┼─────────────────────────────────────┤
 │ tool_end {output}        │ Fill tool output + collapse         │
 ├──────────────────────────┼─────────────────────────────────────┤
 │ llm_stream {token}       │ Append token to streaming text area │
 ├──────────────────────────┼─────────────────────────────────────┤
 │ agent_end {name}         │ Mark agent node ✓                   │
 ├──────────────────────────┼─────────────────────────────────────┤
 │ run_complete             │ Show "Done" badge, save report      │
 └──────────────────────────┴─────────────────────────────────────┘

 ---
 Agents in Detail

 OrchestratorAgent

 - Receives full state (memories, feedback, run type)
 - Dispatches to sub-agents via LangGraph conditional edges
 - Synthesizes: reads all three analyses → writes final_analysis + predictions
 - Maintains hypothesis ledger entries

 NewsAnalystAgent

 Tools: fetch_stock_news, fetch_sector_news, fetch_macro_news
 Specialty: Sentiment scoring, news credibility weighting, cross-stock news impact
 Memory query: "Past news events that moved {ticker} significantly"

 TechnicalAnalystAgent

 Tools: fetch_price_snapshot, fetch_intraday_snapshot, fetch_eod_snapshot, fetch_index_snapshot, fetch_market_breadth
 Specialty: MA crossovers, RSI-like momentum, 52w proximity signals, volume analysis
 Memory query: "Previous times {ticker} was at similar technical levels"

 PortfolioRiskAgent

 Tools: fetch_holdings, fetch_positions, fetch_todays_trades, calc_pnl, fetch_fii_dii
 Specialty: Position sizing, concentration risk, hold/exit calls, portfolio P&L
 Memory query: "Previous position calls for held stocks"

 ---
 Key Libraries

 langgraph>=0.2.0
 langchain-google-genai>=2.0.0
 langchain-core>=0.3.0
 langchain-chroma>=0.1.4          # ChromaDB integration
 chromadb>=0.5.0
 google-generativeai>=0.8.0       # direct usage tracking
 fastapi>=0.115.0
 uvicorn>=0.30.0
 sse-starlette>=2.0.0             # Server-Sent Events
 yfinance>=0.2.40
 kiteconnect>=5.0.1
 feedparser>=6.0.11
 rich>=13.7.0
 pandas>=2.2.0
 pyyaml>=6.0.1

     ---
     Cron Setup (macOS IST)

     # Cron calls the server API — browser gets live streaming
     0 7  * * 1   curl -s -X POST http://localhost:8001/run/weekly
     0 8  * * 1-5 curl -s -X POST http://localhost:8001/run/morning
     0 14 * * 1-5 curl -s -X POST http://localhost:8001/run/midday
     0 22 * * 1-5 curl -s -X POST http://localhost:8001/run/evening

     Server starts at login via macOS LaunchAgent or python main.py --server &.

     ---
     Gemini Model Strategy

     DEFAULT_MODEL  = "gemini-2.0-flash"   # 3 sub-agents + orchestrator
     FALLBACK_MODEL = "gemini-1.5-flash"   # quota/rate fallback
     HEAVY_MODEL    = "gemini-1.5-pro"     # weekly feedback synthesis (opt-in)

     Custom wrapper catches ResourceExhausted/429, retries on fallback, logs to SQLite usage_log.
     Dashboard /api/usage shows daily/weekly costs by model and agent.

     ---
     Verification Plan

     1. python main.py --server → server starts, browser opens dashboard
     2. Click "Run Morning" in UI → SSE events stream, agents light up in real time
     3. python main.py --run morning (CLI fallback) → terminal output works too
     4. After evening run: SQLite predictions + actuals tables have entries
     5. python main.py --run weekly (Monday) → feedback JSON written, ChromaDB updated
     6. Second morning run: retrieved memories section shows last week's lessons in agent prompt
     7. Pull Zerodha API key, set KITE_ACCESS_TOKEN, rerun → holdings appear in Portfolio panel
     8. Disconnect Zerodha token → portfolio tools fall back to cache, run continues
     9. Exhaust Gemini quota (or mock 429) → wrapper falls back to 1.5-flash, logs the switch