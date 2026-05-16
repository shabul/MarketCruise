import uuid
from datetime import date

from langgraph.graph import StateGraph, END

from ..state.schema import MarketState
from ..agents.news_analyst import run_news_analyst
from ..agents.technical_analyst import run_technical_analyst
from ..agents.portfolio_risk import run_portfolio_risk
from ..agents.options_analyst import run_options_analyst
from ..agents.orchestrator import run_orchestrator
from ..agents.base import configure_usage_store
from ..memory.memory_manager import MemoryManager
from ..tools.market_tools import fetch_global_premarket, _compute_market_regime


def build_daily_graph(memory: MemoryManager):
    """Build and compile the daily analysis LangGraph with parallel agent fan-out."""

    def load_context(state: MarketState) -> dict:
        memories, feedback = memory.load_run_context(
            run_type=state["run_type"],
            watchlist=state["watchlist"],
        )
        run_id = state.get("run_id") or str(uuid.uuid4())[:8]
        memory.sqlite.start_run(run_id, state["run_type"])

        market_regime = _compute_market_regime()
        global_context = fetch_global_premarket() if state["run_type"] == "morning" else ""

        return {
            "run_id": run_id,
            "retrieved_memories": memories,
            "feedback_context": feedback,
            "market_regime": market_regime,
            "global_context": global_context,
        }

    def save_and_finish(state: MarketState) -> dict:
        if state.get("predictions"):
            memory.save_run_predictions(state["run_id"], state["predictions"])

        if state["run_type"] == "evening":
            _save_actuals_from_state(state, memory)

        memory.sqlite.finish_run(state["run_id"], state.get("final_analysis", ""))
        return {}

    graph = StateGraph(MarketState)

    graph.add_node("load_context", load_context)
    graph.add_node("news_analyst", run_news_analyst)
    graph.add_node("technical_analyst", run_technical_analyst)
    graph.add_node("portfolio_risk", run_portfolio_risk)
    graph.add_node("options_analyst", run_options_analyst)
    graph.add_node("synthesize", run_orchestrator)
    graph.add_node("save", save_and_finish)

    graph.set_entry_point("load_context")

    # Fan-out: all 4 analysts run in parallel after load_context
    graph.add_edge("load_context", "news_analyst")
    graph.add_edge("load_context", "technical_analyst")
    graph.add_edge("load_context", "portfolio_risk")
    graph.add_edge("load_context", "options_analyst")

    # Fan-in: LangGraph waits for all 4 before running synthesize
    graph.add_edge("news_analyst", "synthesize")
    graph.add_edge("technical_analyst", "synthesize")
    graph.add_edge("portfolio_risk", "synthesize")
    graph.add_edge("options_analyst", "synthesize")

    graph.add_edge("synthesize", "save")
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


def run_daily(run_type: str, config: dict, memory: MemoryManager, *, initial_run_id: str = "") -> str:
    """Execute a daily run and return the final analysis text."""
    configure_usage_store(memory.sqlite)
    graph = build_daily_graph(memory)
    initial_state: MarketState = {
        "run_id": initial_run_id,
        "run_type": run_type,
        "watchlist": config.get("watchlist", []),
        "config": config.get("gemini", {}),
        "retrieved_memories": [],
        "feedback_context": "",
        "global_context": "",
        "market_regime": "",
        "news_analysis": "",
        "technical_analysis": "",
        "portfolio_analysis": "",
        "options_analysis": "",
        "final_analysis": "",
        "predictions": {},
        "messages": [],
    }
    result = graph.invoke(initial_state)
    return result.get("final_analysis", "Analysis unavailable.")


async def stream_daily(
    run_type: str, config: dict, memory: MemoryManager,
    *, watchlist_override: list[str] | None = None, model_override: str | None = None,
    initial_run_id: str = "",
):
    """Async generator that streams LangGraph events for SSE delivery."""
    configure_usage_store(memory.sqlite)
    cfg = dict(config)
    if watchlist_override:
        cfg["watchlist"] = watchlist_override
    if model_override:
        cfg.setdefault("gemini", {})["default_model"] = model_override
    graph = build_daily_graph(memory)
    initial_state: MarketState = {
        "run_id": initial_run_id,
        "run_type": run_type,
        "watchlist": cfg.get("watchlist", []),
        "config": cfg.get("gemini", {}),
        "retrieved_memories": [],
        "feedback_context": "",
        "global_context": "",
        "market_regime": "",
        "news_analysis": "",
        "technical_analysis": "",
        "portfolio_analysis": "",
        "options_analysis": "",
        "final_analysis": "",
        "predictions": {},
        "messages": [],
    }
    async for event in graph.astream_events(initial_state, version="v2"):
        yield event
