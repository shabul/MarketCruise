import json
import re
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base import make_llm, get_fallback_llm, get_usage_store, is_quota_error, extract_text_content, log_response_usage
from ..state.schema import MarketState

_SYSTEM = """You are the Chief Market Analyst for an Indian retail investor's personal trading assistant.

You receive analysis from four specialist agents:
- NewsAnalyst: news sentiment and market-moving events
- TechnicalAnalyst: price patterns, MA levels, momentum signals
- PortfolioRisk: holdings, P&L, position-level calls
- OptionsFlow: NSE options chain PCR, OI buildup, support/resistance strikes

Your job:
1. Synthesize all four analyses into one coherent final view
2. Resolve any conflicts between news, technicals, and options positioning
3. Produce a structured final report with:
   - Market mood (1-2 sentences)
   - Top 3 opportunities with direction, confidence, and entry rationale
   - Risk flags (up to 3)
   - Per-stock quick signals table
   - For midday/evening: specific position calls
4. Extract structured predictions as JSON at the end in this exact format:
   ```json
   {"stocks": [
     {
       "ticker": "TCS",
       "direction": "BUY",
       "confidence": "High",
       "reasoning": "...",
       "entry_price": 3520.00,
       "stop_loss": 3275.00,
       "target": 4000.00,
       "timeframe": "1 week"
     }
   ]}
   ```
   Rules for price levels:
   - entry_price: realistic current market price (use technical analysis data)
   - stop_loss: 5-8% below entry for BUY, 5-8% above entry for SELL
   - target: 10-15% above entry for BUY, 10-15% below entry for SELL
   - timeframe: one of "1-3 days" | "1 week" | "2-4 weeks"

5. Calibrate confidence based on market regime:
   - High Volatility regime: downgrade all confidences by one level
   - Trending Up: BUY signals aligned with trend get a slight confidence boost
   - Trending Down: SELL signals aligned with trend get a slight confidence boost

Be decisive. The investor needs actionable calls, not hedged non-answers."""


async def run_orchestrator(state: MarketState) -> dict:
    config = state["config"]
    run_type = state["run_type"]
    watchlist = state["watchlist"]
    market_regime = state.get("market_regime", "Unknown")
    global_context = state.get("global_context", "")

    news = state.get("news_analysis", "Not available.")
    technical = state.get("technical_analysis", "Not available.")
    portfolio = state.get("portfolio_analysis", "Not available.")
    options = state.get("options_analysis", "Not available.")
    memories = "\n".join(state.get("retrieved_memories", []))
    feedback = state.get("feedback_context", "")

    prompt = f"Run type: {run_type}\nMarket Regime: {market_regime}\nWatchlist: {', '.join(watchlist)}\n"

    if global_context:
        prompt += f"\n=== PRE-MARKET GLOBAL CONTEXT ===\n{global_context}\n"

    prompt += f"""
=== NEWS ANALYST ===
{news}

=== TECHNICAL ANALYST ===
{technical}

=== PORTFOLIO RISK ===
{portfolio}

=== OPTIONS FLOW ===
{options}
"""
    if memories:
        prompt += f"\n=== RELEVANT PAST CONTEXT ===\n{memories}\n"
    if feedback:
        prompt += f"\n=== LAST WEEK'S FEEDBACK ===\n{feedback}\n"

    accuracy_ctx = _build_accuracy_context(watchlist)
    if accuracy_ctx:
        prompt += f"\n=== HISTORICAL ACCURACY (last 30 days) ===\n{accuracy_ctx}\n"

    prompt += "\nSynthesize the above and produce the final report with structured predictions JSON."

    llm = make_llm(config)

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)], config={"configurable": {"system": _SYSTEM}})
    except Exception as e:
        if is_quota_error(e):
            llm = get_fallback_llm(config)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
        else:
            raise

    log_response_usage(response, f"{run_type}_analysis", "orchestrator", llm.model)
    final_analysis = extract_text_content(response.content)
    predictions = _extract_predictions(final_analysis)

    devil_section = await _run_devils_advocate(llm, final_analysis, predictions)
    if devil_section:
        final_analysis = final_analysis + "\n\n" + devil_section

    return {
        "final_analysis": final_analysis,
        "predictions": predictions,
        "messages": [HumanMessage(content=prompt), response],
    }


def _extract_predictions(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {"stocks": []}


def _build_accuracy_context(watchlist: list[str]) -> str:
    try:
        store = get_usage_store()
        if store is None:
            return ""
        rows = store.get_ticker_accuracy_summary(watchlist)
        if not rows:
            return ""
        lines = ["Ticker | Correct | Total | Accuracy"]
        for r in rows:
            acc = round(r["correct"] / r["total"] * 100) if r["total"] else 0
            lines.append(f"{r['ticker']} | {r['correct']} | {r['total']} | {acc}%")
        return "\n".join(lines)
    except Exception:
        return ""


async def _run_devils_advocate(llm, final_analysis: str, predictions: dict) -> str:
    stocks = predictions.get("stocks", [])
    actionable = [s for s in stocks if s.get("direction") in ("BUY", "SELL")]
    if not actionable:
        return ""

    pred_summary = "\n".join(
        f"- {s['ticker']}: {s['direction']} ({s.get('confidence', '?')} confidence) — {s.get('reasoning', '')}"
        for s in actionable
    )

    devil_prompt = (
        f"You are a contrarian risk analyst. The main analyst has made these predictions:\n\n"
        f"{pred_summary}\n\n"
        f"Context from full analysis (excerpt):\n{final_analysis[:1500]}\n\n"
        f"For each BUY or SELL prediction, provide 2-3 specific reasons it could be WRONG.\n"
        f"Then give an overall conviction rating for the full set:\n"
        f"- Actionable: high-quality signals, limited contradictions\n"
        f"- Tentative: mixed signals, proceed with caution\n"
        f"- Avoid: contradictory or low-conviction predictions\n\n"
        f"Format:\n## Devil's Advocate Review\n**Overall Conviction: [Actionable/Tentative/Avoid]**\n\n[per-stock challenges]"
    )

    try:
        da_response = await llm.ainvoke([HumanMessage(content=devil_prompt)])
        return extract_text_content(da_response.content)
    except Exception:
        return ""
