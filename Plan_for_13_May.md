MarketCruise — Analysis Quality Improvements

 Context

 The test suite is complete (97 tests, all passing). The question now is: how do we improve the quality of the analysis the system produces? The current pipeline is news_analyst → technical_analyst →
 portfolio_risk → orchestrator running sequentially on a simple MarketState. This plan brainstorms concrete, ranked improvements.

 ---
 Current Architecture Weaknesses

 ┌────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────┐
 │                      Weakness                      │                                       Impact                                       │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Sequential pipeline — 3 agents wait for each other │ High latency (3–5 min runs), no benefit from parallel data fetching                │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ No options/derivatives data                        │ Options OI/PCR/IV is the single richest leading indicator for NSE stocks and index │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Orchestrator has no tools — pure synthesis pass    │ Can't ask "wait, what's the current Nifty?" when resolving conflicts               │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Predictions are flat (direction + confidence only) │ No entry price, stop-loss, or target — unusable for execution                      │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ No market regime detection                         │ BUY signal in a confirmed downtrend needs different framing than in an uptrend     │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ No pre-market global context                       │ Morning run doesn't know what SGX Nifty / US futures are doing at 8:30 AM IST      │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Sector rotation is buried in news agent            │ FII/DII sector flows and FMCG vs IT rotation are huge signals, lost in a paragraph │
 ├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
 │ Memory retrieval is uniform                        │ All stocks get same ChromaDB query; a stock with 30 past events drowns one with 3  │
 └────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────┘

 ---
 Proposed Improvements (ranked by impact / effort)

 Tier 1 — Highest Impact, Achievable Now

 1. Parallel Agent Execution (graph restructure)

 What: Run news_analyst, technical_analyst, and portfolio_risk in parallel using LangGraph's Send API or a Fan-out → Fan-in graph pattern. The orchestrator waits for all three.

 Why: Currently each agent takes ~30–60s. Sequential = 3× latency. Parallel = latency of the slowest. Morning run drops from ~4 min to ~1 min.

 How:
 load_context → [news_analyst, technical_analyst, portfolio_risk] (parallel) → orchestrator → save
 In LangGraph: use graph.add_edge("load_context", "news_analyst") + same for technical + portfolio, then orchestrator node receives when all three complete.

 Files: src/graphs/daily_graph.py — restructure the conditional edges. No agent code changes.

 ---
 2. Richer Prediction Format

 What: Extend the orchestrator's JSON output and the predictions SQLite schema to include:
 {
   "ticker": "TCS",
   "direction": "BUY",
   "confidence": "High",
   "entry_price": 3450,
   "stop_loss": 3380,
   "target": 3550,
   "timeframe": "1-3 days",
   "reasoning": "..."
 }

 Why: Direction + confidence alone can't be acted on. Entry/stop/target makes accuracy measurement richer too — not just "was it right?" but "was the risk/reward ratio correct?"

 Files:
 - src/agents/orchestrator.py — update _SYSTEM prompt to output new fields
 - src/memory/sqlite_store.py — add columns to predictions table
 - src/state/schema.py — no change needed (predictions is dict)

 ---
 3. Options Flow Agent (new agent)

 What: New options_analyst agent with tools to fetch NSE options chain data:
 - PCR (Put-Call Ratio) by strike — bearish < 0.7, bullish > 1.3
 - Max pain level — where IV is highest, strong magnetic level
 - OI buildup — which strikes are accumulating calls/puts
 - IV percentile — is options market pricing high or low vol?

 Why: For NSE stocks and Nifty, options OI is the most reliable short-term signal — institutions telegraph their positioning. A news sentiment that contradicts options positioning should lower confidence.

 New files:
 - src/tools/options_tools.py — scrape NSE options chain (public endpoint: https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY)
 - src/agents/options_analyst.py
 - Register in daily_graph.py
 - Add options_analysis: str to MarketState

 Note: NSE API requires browser-like headers + session cookie. Wrap in graceful fallback — this tool is flaky.

 ---
 4. Pre-Market Global Context Tool

 What: Morning run gets a global context block before any agent runs:
 - SGX Nifty futures (proxy for Nifty open)
 - US futures (S&P 500, Nasdaq)
 - Dollar Index (DXY) — strong dollar = FII outflow pressure
 - Crude oil — big input cost signal for Indian markets
 - Asian markets open (Nikkei, Hang Seng)

 Why: A Nifty 0.5% pre-market gap-up changes the entire framing of a morning analysis.

 How: Add fetch_global_premarket() tool using yfinance (^GSPC, ES=F, NQ=F, DX-Y.NYB, CL=F). Inject result into load_context as a new global_context: str state field.

 Files: src/tools/market_tools.py, src/state/schema.py, src/graphs/daily_graph.py

 ---
 Tier 2 — High Value, Moderate Effort

 5. Market Regime Detection

 What: At load_context, classify current market regime before agents run:
 - Trending Up: Nifty > 50MA, breadth > 60%, FII net buyer last 5 days
 - Trending Down: Nifty < 200MA, breadth < 40%, FII net seller
 - Ranging: Nifty within 1% of 20MA, breadth 45–55%
 - High Volatility: India VIX > 20

 Inject regime into all agents' context so they can weight signals appropriately.

 Why: A "Bearish" signal in a confirmed uptrend deserves less weight than the same signal in a downtrend. Regime makes the orchestrator's conflict resolution smarter.

 Files: src/graphs/daily_graph.py (in load_context node), src/state/schema.py (add market_regime: str)

 ---
 6. Devil's Advocate / Challenge Pass

 What: After orchestrator produces the final analysis and predictions, add a second LLM call (same model, different prompt) that:
 - Reviews each BUY/SELL prediction
 - Lists 2–3 reasons it could be wrong
 - Rates overall conviction: Actionable / Tentative / Avoid

 Why: Orchestrator is instructed to be "decisive" — it overclaims. A challenge pass injects calibration without changing the main analysis flow.

 How: Extra step in run_orchestrator() — second llm.invoke() call, result appended to final_analysis. Or a separate challenge graph node after synthesize.

 Files: src/agents/orchestrator.py (or new src/agents/challenger.py)

 ---
 7. Sector Rotation Agent

 What: Dedicated agent that analyzes:
 - NSE sector index performance (IT, Bank, FMCG, Pharma, Metal, Auto) — via yfinance sector ETFs or NSE sector indices
 - FII sector allocation shifts (from SEBI monthly data or derived from FII/DII daily)
 - Relative strength: which sectors are outperforming Nifty?

 Injects sector_analysis: str into orchestrator, who can then say "TCS BUY — IT sector seeing rotation in"

 Files:
 - src/tools/nse_tools.py — add sector index fetcher
 - src/agents/sector_analyst.py (new)
 - Register in graph

 ---
 Tier 3 — Lower Priority / Longer Horizon

 8. Earnings Calendar Guard

 When orchestrator issues a BUY/SELL prediction, check fetch_corporate_events result. If earnings are within 3 days, automatically lower confidence and add "PRE-EARNINGS" flag. Prevents confident directional
 calls right before binary events.

 9. Per-Stock Memory Depth Control

 Current ChromaDB query returns N results regardless of how many events exist per ticker. For a stock with 60 past predictions, retrieve only the most recent 5 and the 5 most semantically similar. For a new
 stock with 2 events, retrieve both. Adjust query strategy in memory_manager.load_run_context().

 10. Accuracy-Weighted Confidence

 Use historical accuracy from SQLite (accuracy endpoint data) to recalibrate the orchestrator's confidence labels. If the system has been 40% accurate on "High confidence BUY" calls for RELIANCE, downgrade to
  "Medium". Feed accuracy per-ticker into the orchestrator prompt.

 ---
 Recommended Implementation Order

 1. Parallel execution (graph change only, zero agent changes, biggest latency win)
 2. Richer prediction format (small prompt + schema change, immediately improves usefulness)
 3. Pre-market global context tool (new tool, injected at load_context — low risk)
 4. Options flow agent (new agent + tool, highest signal value but NSE API is flaky)
 5. Devil's advocate pass (one extra LLM call, improves calibration)
 6. Market regime detection (adds regime to context for all agents)

 ---
 Files to Touch Per Item

 ┌───────────────────────┬──────────────────────────────────────┬────────────────────────────────────────────┐
 │      Improvement      │              New Files               │               Modified Files               │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Parallel execution    │ —                                    │ daily_graph.py                             │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Richer predictions    │ —                                    │ orchestrator.py, sqlite_store.py           │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Global premarket tool │ —                                    │ market_tools.py, schema.py, daily_graph.py │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Options agent         │ options_tools.py, options_analyst.py │ daily_graph.py, schema.py                  │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Devil's advocate      │ optional challenger.py               │ orchestrator.py or daily_graph.py          │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Market regime         │ —                                    │ daily_graph.py, schema.py                  │
 ├───────────────────────┼──────────────────────────────────────┼────────────────────────────────────────────┤
 │ Sector agent          │ sector_analyst.py                    │ nse_tools.py, daily_graph.py, schema.py    │
 └───────────────────────┴──────────────────────────────────────┴────────────────────────────────────────────┘

 ---
 Questions to Decide Before Implementation

 1. Parallel execution: LangGraph supports fan-out via multiple add_edge calls from one node. Want to verify this with the current LangGraph version before committing — need to check if the StateGraph
 add_messages reducer handles concurrent writes.
 2. Options tools: NSE public options API requires session cookies. Accept the flakiness (return graceful error string) or add a Playwright-based scraper?
 3. Richer predictions: Do you want entry_price / stop_loss / target in the existing predictions table or a separate trade_calls table with its own accuracy tracking?
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

