#!/usr/bin/env python3
"""
MarketCruise — Personal AI stock market assistant for Indian markets.

Usage:
  python main.py --server                  Start the web dashboard (localhost:8001)
  python main.py --run morning             Run morning analysis (terminal mode)
  python main.py --run midday              Run midday check
  python main.py --run evening             Run evening review
  python main.py --run weekly              Run weekly feedback loop
  python main.py --set-kite-token <token>  Save Zerodha Kite access token to .env
"""
import argparse
import os
import sys

from dotenv import load_dotenv, set_key
import yaml

load_dotenv()


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def cmd_server(config: dict) -> None:
    import uvicorn
    from src.server.app import create_app
    app = create_app("config.yaml")
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = config.get("server", {}).get("port", 8001)
    print(f"MarketCruise dashboard running at http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def cmd_run(run_type: str, config: dict) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from src.memory.memory_manager import MemoryManager
    from src.graphs.daily_graph import run_daily
    from src.graphs.feedback_graph import run_weekly_feedback

    console = Console()
    memory = MemoryManager(config)

    with console.status(f"[bold green]Running {run_type} analysis...", spinner="dots"):
        if run_type == "weekly":
            result = run_weekly_feedback(config, memory)
        else:
            result = run_daily(run_type, config, memory)

    console.print(Panel(Markdown(result), title=f"[bold green]MarketCruise — {run_type.upper()}",
                        border_style="green", expand=False))


def cmd_set_kite_token(token: str) -> None:
    env_file = ".env"
    if not os.path.exists(env_file):
        open(env_file, "w").close()
    set_key(env_file, "KITE_ACCESS_TOKEN", token)
    print(f"Kite access token saved to {env_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MarketCruise — AI stock market assistant")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--server", action="store_true", help="Start web dashboard server")
    group.add_argument("--run", choices=["morning", "midday", "evening", "weekly"],
                       help="Execute a specific run type")
    group.add_argument("--set-kite-token", metavar="TOKEN", help="Save Zerodha Kite access token")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY") and not args.set_kite_token:
        print("Error: GEMINI_API_KEY not set. Copy .env.template to .env and fill in your keys.")
        sys.exit(1)

    config = load_config()

    if args.server:
        cmd_server(config)
    elif args.run:
        cmd_run(args.run, config)
    elif args.set_kite_token:
        cmd_set_kite_token(args.set_kite_token)


if __name__ == "__main__":
    main()
