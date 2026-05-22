"""Rich-formatted terminal logging for the MarketCruise agent pipeline.

Usage (in each agent):
    from ..utils.logging import log, ToolCallLogger

    log.agent_start("NewsAnalyst")
    result = await agent.ainvoke(
        {"messages": [...]},
        config={"callbacks": [ToolCallLogger("NewsAnalyst")]},
    )
    log.agent_done("NewsAnalyst", result["messages"])
"""

import json
from contextvars import ContextVar
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

_console = Console(highlight=False)
_run_event_sink: ContextVar[Any | None] = ContextVar("marketcruise_run_event_sink", default=None)

# ── Agent colour map ──────────────────────────────────────────────────────────
_AGENT_COLOURS = {
    "Context":     "bright_white",
    "NewsAnalyst": "cyan",
    "TechnicalAnalyst": "yellow",
    "PortfolioRisk": "green",
    "OptionsAnalyst": "magenta",
    "Orchestrator": "bold bright_blue",
}


def _colour(agent: str) -> str:
    return _AGENT_COLOURS.get(agent, "white")


# ── Public logger ─────────────────────────────────────────────────────────────

class _MarketLogger:
    """Singleton logger.  Call log.<method>() anywhere in the codebase."""

    # ── Pipeline header ───────────────────────────────────────────────────────

    def run_start(self, run_type: str, watchlist: list[str]) -> None:
        _console.print()
        _console.print(Rule(
            f"[bold]MarketCruise  ·  {run_type.upper()} RUN[/bold]"
            f"  [dim]{', '.join(watchlist)}[/dim]",
            style="bold blue",
        ))

    # ── Context loading ───────────────────────────────────────────────────────

    def context_start(self) -> None:
        _console.print()
        _console.print(Rule("[bright_white]▶ LOAD CONTEXT[/bright_white]", style="bright_white"))

    def context_status(
        self,
        run_id: str,
        regime: str,
        memories: list[str],
        has_feedback: bool,
        has_global: bool,
    ) -> None:
        _console.print(f"  [dim]run_id :[/dim]   {run_id}")
        regime_colour = (
            "green" if "up" in regime.lower()
            else "red" if "down" in regime.lower()
            else "yellow"
        )
        _console.print(f"  [dim]regime :[/dim]   [{regime_colour}]{regime}[/{regime_colour}]")
        _console.print(f"  [dim]memories:[/dim]  {len(memories)} retrieved")
        if has_feedback:
            _console.print("  [dim]feedback:[/dim]  ✓ last-week lesson loaded")
        if has_global:
            _console.print("  [dim]global  :[/dim]  ✓ pre-market context loaded")

    # ── Agent lifecycle ───────────────────────────────────────────────────────

    def agent_start(self, agent: str) -> None:
        c = _colour(agent)
        _console.print()
        _console.print(Rule(f"[{c}]▶ {agent.upper()}[/{c}]", style=c))

    def agent_done(self, agent: str, messages: list) -> None:
        from langchain_core.messages import ToolMessage
        tool_count = sum(1 for m in messages if isinstance(m, ToolMessage))
        # last AI message char count
        text_chars = 0
        for m in reversed(messages):
            content = getattr(m, "content", "")
            if isinstance(content, str) and content:
                text_chars = len(content)
                break
        c = _colour(agent)
        _console.print(
            f"  [{c}]✓ {agent}[/{c}]"
            f"  [dim]{tool_count} tool call(s) · {text_chars} chars[/dim]"
        )

    # ── Options skipped ───────────────────────────────────────────────────────

    def options_skipped(self) -> None:
        _console.print()
        _console.print(Rule("[magenta]▶ OPTIONS ANALYST[/magenta]", style="magenta"))
        _console.print("  [dim]⏭  skipped — market closed (evening run)[/dim]")

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def orchestrator_start(self) -> None:
        _console.print()
        _console.print(Rule("[bold bright_blue]▶ ORCHESTRATOR — SYNTHESISING[/bold bright_blue]", style="bold bright_blue"))

    def predictions_extracted(self, predictions: dict) -> None:
        stocks = predictions.get("stocks", [])
        if not stocks:
            _console.print("  [dim]No structured predictions extracted.[/dim]")
            return

        table = Table(
            "Ticker", "Direction", "Confidence", "Entry ₹", "SL ₹", "Target ₹", "Timeframe",
            title="📊 Predictions",
            title_style="bold bright_blue",
            border_style="dim",
            show_lines=False,
            min_width=60,
        )
        for s in stocks:
            direction = s.get("direction", "?")
            d_style = (
                "bold green" if direction == "BUY"
                else "bold red" if direction == "SELL"
                else "yellow"
            )
            conf = s.get("confidence", "?")
            conf_style = (
                "green" if conf == "High"
                else "yellow" if conf == "Medium"
                else "red"
            )
            def fmt(val: Any) -> str:
                return f"{val:,.2f}" if isinstance(val, (int, float)) else str(val or "—")
            table.add_row(
                s.get("ticker", "?"),
                Text(direction, style=d_style),
                Text(conf, style=conf_style),
                fmt(s.get("entry_price")),
                fmt(s.get("stop_loss")),
                fmt(s.get("target")),
                s.get("timeframe", "?"),
            )
        _console.print()
        _console.print(table)

    def final_analysis_preview(self, text: str) -> None:
        _console.print()
        preview = text[:600].strip()
        if len(text) > 600:
            preview += f"\n[dim]… ({len(text) - 600} more chars)[/dim]"
        _console.print(Panel(
            preview,
            title="[bold bright_blue]Final Analysis[/bold bright_blue]",
            border_style="bright_blue",
            padding=(0, 1),
        ))

    # ── Save / finish ─────────────────────────────────────────────────────────

    def run_saved(self, run_id: str, has_predictions: bool) -> None:
        _console.print()
        saved_str = "predictions + run record" if has_predictions else "run record"
        _console.print(f"  [dim]💾 saved {saved_str} for run_id={run_id}[/dim]")
        _console.print(Rule(style="dim"))


log = _MarketLogger()


def set_run_event_sink(sink):
    return _run_event_sink.set(sink)


def reset_run_event_sink(token) -> None:
    _run_event_sink.reset(token)


# ── LangChain callback — captures tool calls in real-time ─────────────────────

class ToolCallLogger(BaseCallbackHandler):
    """Passed as a callback to agent.ainvoke() so every tool call is logged live."""

    def __init__(self, agent_name: str) -> None:
        super().__init__()
        self._agent = agent_name
        self._colour = _colour(agent_name)
        self._tool_stack: list[str] = []
        self._tool_runs: dict[str, str] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name") or serialized.get("id", ["?"])[-1]
        # Pretty-print JSON args if possible
        try:
            args = json.loads(input_str)
            args_str = "  ".join(f"{k}={v!r}" for k, v in args.items())
        except Exception:
            args_str = str(input_str)[:120]
        _console.print(
            f"  [{self._colour}]🔧 {name}[/{self._colour}]"
            f"([dim]{args_str}[/dim])"
        )
        run_id = str(kwargs.get("run_id") or "")
        if run_id:
            self._tool_runs[run_id] = name
        else:
            self._tool_stack.append(name)
        sink = _run_event_sink.get()
        if sink:
            try:
                sink("tool_start", {
                    "agent": self._agent,
                    "tool": name,
                    "input": input_str[:500],
                })
            except Exception:
                pass

    def on_tool_end(
        self,
        output: Any,
        **kwargs: Any,
    ) -> None:
        text = str(output).replace("\n", " ").strip()
        preview = text[:160] + ("…" if len(text) > 160 else "")
        _console.print(f"  [dim]   ↩ {preview}[/dim]")
        run_id = str(kwargs.get("run_id") or "")
        if run_id and run_id in self._tool_runs:
            name = self._tool_runs.pop(run_id)
        else:
            name = self._tool_stack.pop() if self._tool_stack else ""
        sink = _run_event_sink.get()
        if sink:
            try:
                sink("tool_end", {
                    "agent": self._agent,
                    "tool": name,
                    "output": str(output)[:800],
                })
            except Exception:
                pass
