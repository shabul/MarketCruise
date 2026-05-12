from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from .base import make_llm, get_fallback_llm, is_quota_error, extract_text_content, log_response_usage
from ..tools.market_tools import (
    fetch_price_snapshot,
    fetch_intraday_snapshot,
    fetch_eod_snapshot,
    fetch_index_snapshot,
)
from ..tools.nse_tools import fetch_market_breadth
from ..state.schema import MarketState

_SYSTEM = """You are a Technical Analyst specializing in Indian equity markets (NSE/BSE).

Your job:
1. Fetch price data for the watchlist stocks appropriate to the run type
2. Identify key technical signals: MA crossovers, proximity to 52w high/low, momentum, volume anomalies
3. Rate each stock: Strong Buy / Buy / Neutral / Sell / Strong Sell based on technicals only
4. Check index health (Nifty50, Sensex) and market breadth
5. Note support/resistance levels where relevant

Be specific with numbers. Reference the 20/50/200 MA levels explicitly.
Context about similar past technical setups will be provided — use it."""

_TOOLS = [fetch_price_snapshot, fetch_intraday_snapshot, fetch_eod_snapshot,
          fetch_index_snapshot, fetch_market_breadth]


def run_technical_analyst(state: MarketState) -> dict:
    config = state["config"]
    watchlist = state["watchlist"]
    run_type = state["run_type"]
    memories = "\n".join(state.get("retrieved_memories", []))
    feedback = state.get("feedback_context", "")

    data_instruction = {
        "morning": "Fetch prior-day close prices + index snapshot + market breadth.",
        "midday": "Fetch intraday snapshot + index snapshot + market breadth.",
        "evening": "Fetch EOD data + index snapshot.",
    }.get(run_type, "Fetch price snapshot.")

    prompt = (
        f"Run type: {run_type}\n"
        f"Watchlist: {', '.join(watchlist)}\n"
        f"{data_instruction}\n\n"
    )
    if memories:
        prompt += f"Relevant past technical context:\n{memories}\n\n"
    if feedback:
        prompt += f"Last week's technical feedback:\n{feedback}\n\n"
    prompt += "Provide your technical analysis with specific signals for each stock."

    llm = make_llm(config)
    agent = create_react_agent(llm, _TOOLS, prompt=_SYSTEM)

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as e:
        if is_quota_error(e):
            llm_fb = get_fallback_llm(config)
            agent = create_react_agent(llm_fb, _TOOLS, prompt=_SYSTEM)
            result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        else:
            raise

    final_message = result["messages"][-1]
    log_response_usage(final_message, f"{run_type}_analysis", "technical_analyst", llm.model)
    analysis = extract_text_content(final_message.content)
    return {
        "technical_analysis": analysis,
        "next_agent": "portfolio_risk",
        "messages": result["messages"],
    }
