from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes.runs import router as runs_router
from .routes.api import router as api_router
from .routes.kite_auth import router as kite_router
from ..memory.memory_manager import MemoryManager

load_dotenv(override=True)

_config: dict = {}
_memory: MemoryManager | None = None


def get_config() -> dict:
    return _config


def get_memory() -> MemoryManager:
    assert _memory is not None, "Memory not initialized"
    return _memory


def create_app(config_path: str = "config.yaml") -> FastAPI:
    global _config, _memory

    with open(config_path) as f:
        _config = yaml.safe_load(f)

    _memory = MemoryManager(_config)

    app = FastAPI(title="MarketCruise", version="1.0.0")

    app.include_router(runs_router, prefix="", tags=["runs"])
    app.include_router(api_router, prefix="/api", tags=["api"])
    app.include_router(kite_router, prefix="", tags=["kite"])

    static_dir = Path(__file__).parent / "static"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
