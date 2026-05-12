import uuid
from datetime import date
from typing import Literal

from langgraph.graph import StateGraph, END

from ..state.schema import MarketState
from ..agents.news_analyst import run_news_analyst
from ..agents.technical_analyst import run_technical_analyst
from ..agents.portfolio_risk import run_portfolio_risk
from ..agents.orchestrator import run_orchestrator
from ..memory.memory_manager import MemoryManager


def build_daily_graph(memory: MemoryManager):
    """Build and compile the daily analysis LangGraph."""

    def load_context(state: MarketState) -> dict:
        memories, feedback = memory.load_run_context(
            run_type=state["run_type"],
            watchlist=state["watchlist"],
        )
        run_id = str(uuid.uuid4())[:8]
        memory.sqlite.start_run(run_id, state["run_type"])
        return {
            "run_id": run_id,
            "retrieved_memories": memories,
            "feedback_context": feedback,
            "next_agent": "news_analyst",
        }

    def save_and_finish(state: MarketState) -> dict:
        if state.get("predictions"):
            memory.save_run_predictions(state["run_id"], state["predictions"])

        # For evening runs, also save actuals from technical analysis
        if state["run_type"] == "evening":
            _save_actuals_from_state(state, memory)

        memory.sqlite.finish_run(state["run_id"], state.get("final_analysis", ""))
        return {}

    def route_agent(state: MarketState) -> Literal["news_analyst", "technical_analyst", "portfolio_risk", "synthesize", "save"]:
        return {
            "news_analyst": "news_analyst",
            "technical_analyst": "technical_analyst",
            "portfolio_risk": "portfolio_risk",
            "synthesize": "synthesize",
            "done": "save",
        }.get(state.get("next_agent", "news_analyst"), "news_analyst")

    graph = StateGraph(MarketState)

    graph.add_node("load_context", load_context)
    graph.add_node("news_analyst", run_news_analyst)
    graph.add_node("technical_analyst", run_technical_analyst)
    graph.add_node("portfolio_risk", run_portfolio_risk)
    graph.add_node("synthesize", run_orchestrator)
    graph.add_node("save", save_and_finish)

    graph.set_entry_point("load_context")
    graph.add_conditional_edges("load_context", route_agent)
    graph.add_conditional_edges("news_analyst", route_agent)
    graph.add_conditional_edges("technical_analyst", route_agent)
    graph.add_conditional_edges("portfolio_risk", route_agent)
    graph.add_conditional_edges("synthesize", route_agent)
    graph.add_edge("save", END)

    return graph.compile()


def _save_actuals_from_state(state: MarketState, memory: MemoryManager) -> None:
    """Parse technical analysis text to extract actual prices and store them."""
    tech_text = state.get("technical_analysis", "")
    watchlist = state.get("watchlist", [])
    actuals = []
    for ticker in watchlist:
        import re
        m = re.search(rf"{ticker}.*?C=₹([\d.]+).*?\(([+-][\d.]+)%\)", tech_text)
        if m:
            actuals.append({
                "ticker": ticker,
                "close": float(m.group(1)),
                "pct_change": float(m.group(2)),
            })
    if actuals:
        memory.save_actuals(actuals)


def run_daily(run_type: str, config: dict, memory: MemoryManager) -> str:
    """Execute a daily run and return the final analysis text."""
    graph = build_daily_graph(memory)
    initial_state: MarketState = {
        "run_id": "",
        "run_type": run_type,
        "watchlist": config.get("watchlist", []),
        "config": config.get("gemini", {}),
        "retrieved_memories": [],
        "feedback_context": "",
        "next_agent": "news_analyst",
        "news_analysis": "",
        "technical_analysis": "",
        "portfolio_analysis": "",
        "final_analysis": "",
        "predictions": {},
        "messages": [],
    }
    result = graph.invoke(initial_state)
    return result.get("final_analysis", "Analysis unavailable.")


async def stream_daily(run_type: str, config: dict, memory: MemoryManager):
    """Async generator that streams LangGraph events for SSE delivery."""
    graph = build_daily_graph(memory)
    initial_state: MarketState = {
        "run_id": "",
        "run_type": run_type,
        "watchlist": config.get("watchlist", []),
        "config": config.get("gemini", {}),
        "retrieved_memories": [],
        "feedback_context": "",
        "next_agent": "news_analyst",
        "news_analysis": "",
        "technical_analysis": "",
        "portfolio_analysis": "",
        "final_analysis": "",
        "predictions": {},
        "messages": [],
    }
    async for event in graph.astream_events(initial_state, version="v2"):
        yield event
