import asyncio
import os
from datetime import date

import pytest
import yaml
from dotenv import load_dotenv

load_dotenv(override=True)


def _check_gemini_key() -> str | None:
    """Return an error message if the Gemini key is missing, else None.
    Does NOT make a live API call — that would waste quota and cause rate-limit skips."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        return "GEMINI_API_KEY not set"
    # Sync so langchain-google-genai ≥4.x picks up the right key
    os.environ["GOOGLE_API_KEY"] = key
    return None


_gemini_skip_reason: str | None = None
_gemini_checked = False


@pytest.fixture(scope="session", autouse=False)
def gemini_available():
    """Session fixture: skip the test if Gemini API key is unavailable/expired."""
    global _gemini_skip_reason, _gemini_checked
    if not _gemini_checked:
        _gemini_skip_reason = _check_gemini_key()
        _gemini_checked = True
    if _gemini_skip_reason:
        pytest.skip(f"Gemini API unavailable: {_gemini_skip_reason[:120]}")


_gemini_probe_result: str | None = "unchecked"  # "ok" | "skip:<reason>" | "unchecked"


@pytest.fixture(scope="session", autouse=False)
def gemini_quota_ok(gemini_available):
    """Session fixture: probe the Gemini API with a 10s timeout.

    A single lightweight call is enough to confirm quota is currently available.
    This avoids 60+ seconds of tenacity retries per test when quota is exhausted.
    Unlike the base `gemini_available` fixture, this actually hits the API.
    """
    global _gemini_probe_result
    if _gemini_probe_result == "ok":
        return
    if _gemini_probe_result != "unchecked":
        pytest.skip(_gemini_probe_result.removeprefix("skip:"))

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    async def _probe(model: str) -> str:
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.0)
        try:
            await asyncio.wait_for(
                llm.ainvoke([HumanMessage(content="ok")]),
                timeout=15.0,
            )
            return "ok"
        except asyncio.TimeoutError:
            return "timeout"
        except Exception as e:
            return str(e)[:200]

    config_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    skip_keywords = ("quota", "rate limit", "resource exhausted", "429", "resource_exhausted", "permission_denied", "403")

    for model in config_models:
        result = asyncio.run(_probe(model))
        if result == "ok":
            _gemini_probe_result = "ok"
            return
        if result == "timeout" or any(k in result.lower() for k in skip_keywords):
            _gemini_probe_result = f"skip:Gemini quota/access unavailable ({model}): {result[:100]}"
            pytest.skip(_gemini_probe_result.removeprefix("skip:"))

    _gemini_probe_result = "skip:No working Gemini model found"
    pytest.skip("No working Gemini model found")


@pytest.fixture(scope="session")
def real_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def gemini_config(real_config) -> dict:
    return real_config["gemini"]


@pytest.fixture
def tmp_memory(tmp_path):
    from src.memory.memory_manager import MemoryManager
    cfg = {
        "memory": {
            "chroma_dir": str(tmp_path / "chroma"),
            "sqlite_path": str(tmp_path / "test.db"),
            "top_k_memories": 5,
        }
    }
    return MemoryManager(cfg)


@pytest.fixture
def tmp_sqlite(tmp_path):
    from src.memory.sqlite_store import SQLiteStore
    return SQLiteStore(str(tmp_path / "test.db"))


@pytest.fixture
def tmp_chroma(tmp_path):
    from src.memory.chroma_store import ChromaStore
    return ChromaStore(str(tmp_path / "chroma"))


@pytest.fixture
def morning_state(real_config) -> dict:
    return {
        "run_id": "test-run-001",
        "run_type": "morning",
        "watchlist": ["RELIANCE", "TCS"],
        "config": real_config["gemini"],
        "retrieved_memories": [],
        "feedback_context": "",
        "global_context": "",
        "market_regime": "Trending Up",
        "news_analysis": "",
        "technical_analysis": "",
        "portfolio_analysis": "",
        "options_analysis": "",
        "final_analysis": "",
        "predictions": {},
        "messages": [],
    }


@pytest.fixture
def midday_state(real_config) -> dict:
    return {
        "run_id": "test-run-002",
        "run_type": "midday",
        "watchlist": ["RELIANCE", "TCS"],
        "config": real_config["gemini"],
        "retrieved_memories": [],
        "feedback_context": "",
        "global_context": "",
        "market_regime": "Ranging",
        "news_analysis": "",
        "technical_analysis": "",
        "portfolio_analysis": "",
        "options_analysis": "",
        "final_analysis": "",
        "predictions": {},
        "messages": [],
    }


@pytest.fixture
def today() -> str:
    return date.today().isoformat()


@pytest.fixture
def fastapi_app(real_config):
    """FastAPI test app with isolated temp memory."""
    import tempfile
    import yaml
    from src.server import app as app_module

    with tempfile.TemporaryDirectory() as tmp:
        cfg = real_config.copy()
        cfg["memory"] = {
            "chroma_dir": f"{tmp}/chroma",
            "sqlite_path": f"{tmp}/test.db",
            "top_k_memories": 5,
        }
        from src.memory.memory_manager import MemoryManager
        app_module._config = cfg
        app_module._memory = MemoryManager(cfg)
        from src.server.app import create_app
        yield create_app.__wrapped__(cfg) if hasattr(create_app, "__wrapped__") else create_app("config.yaml")
