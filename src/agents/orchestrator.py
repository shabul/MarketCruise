import json
import re
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base import make_llm, get_fallback_llm, is_quota_error
from ..state.schema import MarketState

_SYSTEM = """You are the Chief Market Analyst for an Indian retail investor's personal trading assistant.

You receive analysis from three specialist agents:
- NewsAnalyst: news sentiment and market-moving events
- TechnicalAnalyst: price patterns, MA levels, momentum signals
- PortfolioRisk: holdings, P&L, position-level calls

Your job:
1. Synthesize all three analyses into one coherent final view
2. Resolve any conflicts between news and technicals
3. Produce a structured final report with:
   - Market mood (1-2 sentences)
   - Top 3 opportunities with direction, confidence, and entry rationale
   - Risk flags (up to 3)
   - Per-stock quick signals table
   - For midday/evening: specific position calls
4. Extract structured predictions as JSON at the end in this exact format:
   ```json
   {"stocks": [{"ticker":"TCS","direction":"BUY","confidence":"High","reasoning":"..."}]}
   ```

Be decisive. The investor needs actionable calls, not hedged non-answers."""


def run_orchestrator(state: MarketState) -> dict:
    config = state["config"]
    run_type = state["run_type"]
    watchlist = state["watchlist"]

    news = state.get("news_analysis", "Not available.")
    technical = state.get("technical_analysis", "Not available.")
    portfolio = state.get("portfolio_analysis", "Not available.")
    memories = "\n".join(state.get("retrieved_memories", []))
    feedback = state.get("feedback_context", "")

    prompt = f"""Run type: {run_type}
Watchlist: {', '.join(watchlist)}

=== NEWS ANALYST ===
{news}

=== TECHNICAL ANALYST ===
{technical}

=== PORTFOLIO RISK ===
{portfolio}
"""
    if memories:
        prompt += f"\n=== RELEVANT PAST CONTEXT ===\n{memories}\n"
    if feedback:
        prompt += f"\n=== LAST WEEK'S FEEDBACK ===\n{feedback}\n"

    prompt += "\nSynthesize the above and produce the final report with structured predictions JSON."

    llm = make_llm(config)

    try:
        response = llm.invoke([HumanMessage(content=prompt)], config={"configurable": {"system": _SYSTEM}})
    except Exception as e:
        if is_quota_error(e):
            llm = get_fallback_llm(config)
            response = llm.invoke([HumanMessage(content=prompt)])
        else:
            raise

    final_analysis = response.content
    predictions = _extract_predictions(final_analysis)

    return {
        "final_analysis": final_analysis,
        "predictions": predictions,
        "next_agent": "done",
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
