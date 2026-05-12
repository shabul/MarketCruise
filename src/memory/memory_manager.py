from datetime import datetime, date

from .chroma_store import ChromaStore
from .sqlite_store import SQLiteStore


class MemoryManager:
    """Unified interface for all memory operations used by graph nodes."""

    def __init__(self, config: dict):
        mem_cfg = config.get("memory", {})
        self.chroma = ChromaStore(mem_cfg.get("chroma_dir", "data/chroma"))
        self.sqlite = SQLiteStore(mem_cfg.get("sqlite_path", "data/market_cruise.db"))
        self.top_k = mem_cfg.get("top_k_memories", 5)

    def load_run_context(self, run_type: str, watchlist: list[str]) -> tuple[list[str], str]:
        """Returns (retrieved_memories, feedback_context) to inject at run start."""
        query = f"Indian market {run_type} {date.today().isoformat()} {' '.join(watchlist[:5])}"

        memories = self.chroma.retrieve_relevant(
            query=query,
            collection="stock_events",
            n_results=self.top_k,
        )
        memories += self.chroma.retrieve_relevant(
            query=query,
            collection="market_regimes",
            n_results=2,
        )

        feedback = self.chroma.retrieve_latest_lesson()
        return memories, feedback

    def save_run_predictions(self, run_id: str, predictions: dict) -> None:
        today = date.today().isoformat()
        pred_list = predictions.get("stocks", [])
        self.sqlite.save_predictions(run_id, today, pred_list)

        # Embed each prediction as a stock event for future retrieval
        for p in pred_list:
            text = (
                f"Predicted {p.get('direction','?')} for {p.get('ticker','?')} "
                f"({p.get('confidence','?')} confidence): {p.get('reasoning','')}"
            )
            self.chroma.add_stock_event(
                ticker=p.get("ticker", "UNKNOWN"),
                date=today,
                event_text=text,
                metadata={"type": "prediction", "run_type": run_id},
            )

    def save_actuals(self, eod_data: list[dict]) -> None:
        today = date.today().isoformat()
        self.sqlite.save_actuals(today, eod_data)
        for a in eod_data:
            text = (
                f"EOD: {a['ticker']} closed at ₹{a.get('close')} "
                f"({a.get('pct_change',0):+.2f}% vs prev close)"
            )
            self.chroma.add_stock_event(
                ticker=a["ticker"],
                date=today,
                event_text=text,
                metadata={"type": "actual"},
            )

    def save_weekly_lesson(self, week_label: str, lesson_text: str) -> None:
        self.chroma.add_lesson(week_label, lesson_text)
