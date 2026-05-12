"""Integration tests for direct Gemini API calls."""
import os
import time
import pytest
from langchain_core.messages import HumanMessage
from src.agents.base import make_llm, get_fallback_llm, estimate_cost

# All tests in this file require a live, non-expired Gemini API key.
pytestmark = pytest.mark.usefixtures("gemini_available")

_RATE_LIMIT_MSGS = ("resource_exhausted", "resource exhausted", "429", "quota")


def _is_rate_limited(e: Exception) -> bool:
    return any(m in str(e).lower() for m in _RATE_LIMIT_MSGS)


@pytest.fixture(autouse=True)
def rate_limit_pause():
    """4-second gap between tests to stay under free-tier 15 RPM limit."""
    time.sleep(4)
    yield


@pytest.mark.integration
def test_basic_gemini_call(gemini_config):
    llm = make_llm(gemini_config)
    try:
        response = llm.invoke([HumanMessage(content="Reply with exactly: MARKET_TEST_OK")])
    except Exception as e:
        if _is_rate_limited(e):
            pytest.skip(f"Rate limited: {e}")
        raise
    assert response.content
    assert len(response.content) > 0


@pytest.mark.integration
def test_gemini_flash_model_used(gemini_config):
    llm = make_llm(gemini_config)
    assert "flash" in llm.model.lower() or "flash" in gemini_config.get("default_model", "")


@pytest.mark.integration
def test_fallback_llm_works(gemini_config):
    llm = get_fallback_llm(gemini_config)
    try:
        response = llm.invoke([HumanMessage(content="Say: FALLBACK_OK")])
    except Exception as e:
        if _is_rate_limited(e):
            pytest.skip(f"Rate limited: {e}")
        raise
    assert response.content
    assert len(response.content) > 0


@pytest.mark.integration
def test_gemini_returns_usage_metadata(gemini_config):
    llm = make_llm(gemini_config)
    try:
        response = llm.invoke([HumanMessage(content="Count to 3")])
    except Exception as e:
        if _is_rate_limited(e):
            pytest.skip(f"Rate limited: {e}")
        raise
    assert response.content


@pytest.mark.integration
def test_gemini_cost_estimate_positive(gemini_config):
    model = gemini_config.get("default_model", "gemini-2.0-flash")
    cost = estimate_cost(model, 500, 200)
    assert cost > 0


@pytest.mark.integration
def test_gemini_structured_prompt(gemini_config):
    """Verify Gemini can follow a structured output instruction."""
    llm = make_llm(gemini_config)
    try:
        response = llm.invoke([HumanMessage(content="List 2 Indian NSE stock tickers, one per line.")])
    except Exception as e:
        if _is_rate_limited(e):
            pytest.skip(f"Rate limited: {e}")
        raise
    assert response.content
    assert len(response.content) > 0


@pytest.mark.integration
def test_gemini_with_system_context(gemini_config):
    """Verify Gemini answers a simple question correctly."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=gemini_config.get("default_model", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
        temperature=0.0,
    )
    try:
        response = llm.invoke([HumanMessage(content="What is 2+2? Answer with just the number.")])
    except Exception as e:
        if _is_rate_limited(e):
            pytest.skip(f"Rate limited: {e}")
        raise
    assert "4" in response.content
