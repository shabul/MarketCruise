from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from .base import make_llm, get_fallback_llm, is_quota_error, extract_text_content, log_response_usage
from ..tools.news_tools import fetch_stock_news, fetch_sector_news, fetch_macro_news
from ..state.schema import MarketState

_SYSTEM = """You are a News Analyst specializing in Indian equity markets (NSE/BSE).

Your job:
1. Fetch relevant news for the stocks you're given and for the broad market
2. Score sentiment for each stock: Bullish / Neutral / Bearish
3. Identify the 2-3 most market-moving news items
4. Note any cross-stock or sector-wide themes visible in the news
5. Flag any news that could cause sudden price moves

Be concise. Use bullet points. Always cite the news source.
Context about similar past situations will be provided — use it."""

_TOOLS = [fetch_stock_news, fetch_sector_news, fetch_macro_news]


def run_news_analyst(state: MarketState) -> dict:
    config = state["config"]
    watchlist = state["watchlist"]
    run_type = state["run_type"]
    memories = "\n".join(state.get("retrieved_memories", []))
    feedback = state.get("feedback_context", "")

    hours = {"morning": 24, "midday": 8, "evening": 24}.get(run_type, 24)

    prompt = (
        f"Run type: {run_type}\n"
        f"Watchlist: {', '.join(watchlist)}\n"
        f"Fetch news for the last {hours} hours.\n\n"
    )
    if memories:
        prompt += f"Relevant past context:\n{memories}\n\n"
    if feedback:
        prompt += f"Last week's feedback on news analysis:\n{feedback}\n\n"
    prompt += "Analyze the news and provide your structured assessment."

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
    log_response_usage(final_message, f"{run_type}_analysis", "news_analyst", llm.model)
    analysis = extract_text_content(final_message.content)
    return {
        "news_analysis": analysis,
        "next_agent": "technical_analyst",
        "messages": result["messages"],
    }
