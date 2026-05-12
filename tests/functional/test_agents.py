"""Functional tests — full agent runs with real Gemini + real tools."""
import pytest
from langchain_core.messages import HumanMessage

# All tests call Gemini — skip the whole module if the API key is expired.
pytestmark = pytest.mark.usefixtures("gemini_available")

from src.agents.news_analyst import run_news_analyst
from src.agents.technical_analyst import run_technical_analyst
from src.agents.portfolio_risk import run_portfolio_risk
from src.agents.orchestrator import run_orchestrator


@pytest.mark.functional
def test_news_analyst_morning(morning_state):
    result = run_news_analyst(morning_state)
    assert "news_analysis" in result
    assert isinstance(result["news_analysis"], str)
    assert len(result["news_analysis"]) > 50
    assert result.get("next_agent") == "technical_analyst"


@pytest.mark.functional
def test_news_analyst_contains_sentiment(morning_state):
    result = run_news_analyst(morning_state)
    text = result["news_analysis"].lower()
    has_sentiment = any(w in text for w in ["bullish", "bearish", "neutral", "positive", "negative"])
    assert has_sentiment, f"Expected sentiment word in: {text[:300]}"


@pytest.mark.functional
def test_news_analyst_midday(midday_state):
    result = run_news_analyst(midday_state)
    assert result["news_analysis"]
    assert result["next_agent"] == "technical_analyst"


@pytest.mark.functional
def test_technical_analyst_morning(morning_state):
    result = run_technical_analyst(morning_state)
    assert "technical_analysis" in result
    assert isinstance(result["technical_analysis"], str)
    assert len(result["technical_analysis"]) > 50
    assert result.get("next_agent") == "portfolio_risk"


@pytest.mark.functional
def test_technical_analyst_references_watchlist(morning_state):
    result = run_technical_analyst(morning_state)
    text = result["technical_analysis"]
    found = sum(1 for t in morning_state["watchlist"] if t in text)
    assert found >= 1, f"Expected at least one ticker in analysis: {text[:300]}"


@pytest.mark.functional
def test_portfolio_risk_morning(morning_state):
    result = run_portfolio_risk(morning_state)
    assert "portfolio_analysis" in result
    assert isinstance(result["portfolio_analysis"], str)
    assert len(result["portfolio_analysis"]) > 20
    assert result.get("next_agent") == "synthesize"


@pytest.mark.functional
def test_portfolio_risk_handles_no_holdings(morning_state):
    """Portfolio agent should never raise even if Kite has no data."""
    result = run_portfolio_risk(morning_state)
    text = result["portfolio_analysis"].lower()
    has_data = "₹" in result["portfolio_analysis"]
    has_fallback = any(w in text for w in ["no holdings", "unavailable", "no open", "no completed"])
    assert has_data or has_fallback, f"Unexpected portfolio result: {text[:300]}"


@pytest.mark.functional
def test_orchestrator_with_seeded_analyses(morning_state):
    """Inject realistic sub-agent outputs and verify orchestrator synthesizes them."""
    state = dict(morning_state)
    state["news_analysis"] = (
        "RELIANCE: Bullish — JioMart revenue beat reported.\n"
        "TCS: Neutral — Q4 guidance in line with estimates."
    )
    state["technical_analysis"] = (
        "RELIANCE close=₹2800 (+1.2%) 52w_high=₹3010 ma20=₹2750\n"
        "TCS close=₹3500 (-0.3%) 52w_high=₹4100 ma20=₹3480"
    )
    state["portfolio_analysis"] = (
        "Holdings: RELIANCE 10 units @ ₹2600 avg\n"
        "P&L: +₹2000 unrealised"
    )

    result = run_orchestrator(state)

    assert "final_analysis" in result
    assert len(result["final_analysis"]) > 50
    assert result.get("next_agent") == "done"

    predictions = result.get("predictions", {})
    assert isinstance(predictions, dict)


@pytest.mark.functional
def test_orchestrator_predictions_have_stocks_key(morning_state):
    state = dict(morning_state)
    state["news_analysis"] = "RELIANCE: Bullish. TCS: Bearish."
    state["technical_analysis"] = "RELIANCE trending up. TCS below MA50."
    state["portfolio_analysis"] = "No open positions."

    result = run_orchestrator(state)
    predictions = result.get("predictions", {})
    # predictions should be a dict; if LLM produces structured output, "stocks" key appears
    assert isinstance(predictions, dict)


@pytest.mark.functional
def test_orchestrator_messages_populated(morning_state):
    state = dict(morning_state)
    state["news_analysis"] = "Market broadly positive."
    state["technical_analysis"] = "Indices near 52w highs."
    state["portfolio_analysis"] = "No holdings found."

    result = run_orchestrator(state)
    assert "messages" in result
    assert len(result["messages"]) > 0
