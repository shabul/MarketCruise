from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from .base import make_llm, get_fallback_llm, is_quota_error
from ..tools.portfolio_tools import (
    fetch_holdings,
    fetch_positions,
    fetch_todays_trades,
    calculate_portfolio_pnl,
)
from ..tools.nse_tools import fetch_fii_dii
from ..state.schema import MarketState

_SYSTEM = """You are a Portfolio Risk Analyst for an Indian retail investor trading NSE stocks.

Your job:
1. Fetch current holdings and open positions
2. Calculate P&L and assess portfolio health
3. On midday/evening runs: make explicit HOLD / EXIT / PARTIAL EXIT calls for each held position with reasoning
4. Flag concentration risk (any stock > 20% of portfolio)
5. Summarize FII/DII activity and its likely impact on your holdings
6. On evening runs: pull today's completed trades and assess if they were well-timed

Always be direct. Give specific ₹ amounts and % figures. Risk calls must have clear reasoning."""

_TOOLS = [fetch_holdings, fetch_positions, fetch_todays_trades, calculate_portfolio_pnl, fetch_fii_dii]


def run_portfolio_risk(state: MarketState) -> dict:
    config = state["config"]
    run_type = state["run_type"]
    memories = "\n".join(state.get("retrieved_memories", []))
    feedback = state.get("feedback_context", "")

    instructions = {
        "morning": "Fetch holdings and FII/DII data. Summarize portfolio status entering the day.",
        "midday": "Fetch holdings, open positions, FII/DII. Make HOLD/EXIT calls for each position.",
        "evening": "Fetch holdings, today's trades, FII/DII. Calculate P&L. Review trade timing.",
    }.get(run_type, "Fetch holdings and calculate P&L.")

    prompt = f"Run type: {run_type}\n{instructions}\n\n"
    if memories:
        prompt += f"Relevant past portfolio context:\n{memories}\n\n"
    if feedback:
        prompt += f"Last week's portfolio feedback:\n{feedback}\n\n"
    prompt += "Provide your portfolio risk assessment."

    llm = make_llm(config)
    agent = create_react_agent(llm, _TOOLS, state_modifier=_SYSTEM)

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    except Exception as e:
        if is_quota_error(e):
            llm_fb = get_fallback_llm(config)
            agent = create_react_agent(llm_fb, _TOOLS, state_modifier=_SYSTEM)
            result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        else:
            raise

    analysis = result["messages"][-1].content
    return {
        "portfolio_analysis": analysis,
        "next_agent": "synthesize",
        "messages": result["messages"],
    }
