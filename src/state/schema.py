from typing import Annotated, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MarketState(TypedDict):
    run_id: str
    run_type: str                        # morning | midday | evening | weekly
    watchlist: list[str]
    config: dict

    # Memory context loaded at run start
    retrieved_memories: list[str]        # ChromaDB semantic search results
    feedback_context: str                # latest weekly feedback summary

    # Market context loaded at run start
    global_context: str       # pre-market global futures/FX/Asian markets (morning only)
    market_regime: str        # Trending Up | Trending Down | Ranging | High Volatility

    # Sub-agent outputs
    news_analysis: str
    technical_analysis: str
    portfolio_analysis: str
    options_analysis: str     # options flow agent output

    # Orchestrator synthesis
    final_analysis: str
    predictions: dict                    # structured predictions to persist

    # LangGraph message history for all agents
    messages: Annotated[list[BaseMessage], add_messages]


class FeedbackState(TypedDict):
    week_label: str                      # e.g. "2026-W19"
    prediction_records: list[dict]
    actual_records: list[dict]
    accuracy_stats: dict
    news_feedback: str
    technical_feedback: str
    portfolio_feedback: str
    synthesized_feedback: str
    messages: Annotated[list[BaseMessage], add_messages]
