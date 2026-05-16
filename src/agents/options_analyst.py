from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from .base import make_llm, get_fallback_llm, is_quota_error, extract_text_content, log_response_usage
from ..tools.options_tools import fetch_options_chain, fetch_index_options
from ..state.schema import MarketState

_SYSTEM = """You are an Options Flow Analyst for Indian equity markets (NSE).

Your job:
1. Fetch options chain data for the watchlist stocks and for Nifty/BankNifty index
2. Interpret the Put/Call Ratio (PCR):
   - PCR > 1.2: significant put buying = bearish hedging by institutions
   - PCR < 0.7: heavy call buying = bullish sentiment
   - PCR 0.7–1.2: neutral positioning
3. Identify top OI strikes = key support (high PE OI) and resistance (high CE OI) levels
4. Flag any unusual OI concentration suggesting large institutional positioning
5. Provide a concise options-flow conclusion: is smart money positioned bullish, bearish, or neutral?

Market regime is provided — calibrate your read accordingly.
Be specific: cite strike prices, PCR values, and OI figures."""

_TOOLS = [fetch_options_chain, fetch_index_options]


async def run_options_analyst(state: MarketState) -> dict:
    if state.get("run_type") == "evening":
        return {
            "options_analysis": "Options analysis skipped for evening run (market closed).",
            "messages": [],
        }

    config = state["config"]
    watchlist = state["watchlist"]
    run_type = state["run_type"]
    market_regime = state.get("market_regime", "Unknown")
    memories = "\n".join(state.get("retrieved_memories", []))

    prompt = (
        f"Run type: {run_type}\n"
        f"Market Regime: {market_regime}\n"
        f"Watchlist: {', '.join(watchlist)}\n\n"
        f"Fetch options chain for NIFTY index and key watchlist stocks.\n"
        f"Identify PCR, max pain proximity, and major OI support/resistance levels.\n\n"
    )
    if memories:
        prompt += f"Relevant past context:\n{memories}\n\n"
    prompt += "Provide your options flow assessment."

    llm = make_llm(config)
    agent = create_react_agent(llm, _TOOLS, prompt=_SYSTEM)

    try:
        result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as e:
        if is_quota_error(e):
            llm_fb = get_fallback_llm(config)
            agent = create_react_agent(llm_fb, _TOOLS, prompt=_SYSTEM)
            result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        else:
            raise

    final_message = result["messages"][-1]
    log_response_usage(final_message, f"{run_type}_analysis", "options_analyst", llm.model)
    analysis = extract_text_content(final_message.content)
    return {
        "options_analysis": analysis,
        "messages": result["messages"],
    }
