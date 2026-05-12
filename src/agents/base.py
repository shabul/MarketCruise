import os
import time
from typing import Optional

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


_PRICING = {
    "gemini-2.0-flash":      {"input": 0.10,  "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-2.5-flash":      {"input": 0.15,  "output": 0.60},
    "gemini-2.5-pro":        {"input": 1.25,  "output": 10.00},
    # Legacy names kept for backwards compat
    "gemini-1.5-flash":      {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro":        {"input": 1.25,  "output": 5.00},
}

_QUOTA_ERRORS = ("quota", "rate limit", "resource exhausted", "429", "resource_exhausted")


def _api_key() -> str:
    """Return the Gemini API key, keeping GOOGLE_API_KEY in sync so langchain-google-genai ≥4.x doesn't complain."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if key:
        os.environ["GOOGLE_API_KEY"] = key
    return key


def make_llm(config: dict, use_heavy: bool = False) -> ChatGoogleGenerativeAI:
    model = (
        config.get("heavy_model", "gemini-1.5-pro")
        if use_heavy
        else config.get("default_model", "gemini-2.0-flash")
    )
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=_api_key(),
        temperature=0.2,
    )


def make_llm_with_fallback(config: dict, use_heavy: bool = False) -> ChatGoogleGenerativeAI:
    return make_llm(config, use_heavy)


def get_fallback_llm(config: dict) -> ChatGoogleGenerativeAI:
    model = config.get("fallback_model", "gemini-2.5-flash")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=_api_key(),
        temperature=0.2,
    )


def estimate_cost(model: str, input_tok: int, output_tok: int) -> float:
    p = _PRICING.get(model, {"input": 0.0, "output": 0.0})
    return round((input_tok / 1_000_000) * p["input"] + (output_tok / 1_000_000) * p["output"], 6)


def is_quota_error(e: Exception) -> bool:
    return any(q in str(e).lower() for q in _QUOTA_ERRORS)
