import json
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


_COLLECTIONS = ["stock_events", "market_regimes", "lessons_learned", "hypothesis_ledger"]


class ChromaStore:
    def __init__(self, chroma_dir: str):
        Path(chroma_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=chroma_dir)
        self._ef = embedding_functions.DefaultEmbeddingFunction()
        self._cols = {
            name: self.client.get_or_create_collection(name, embedding_function=self._ef)
            for name in _COLLECTIONS
        }

    def add_stock_event(
        self,
        ticker: str,
        date: str,
        event_text: str,
        metadata: dict | None = None,
    ) -> None:
        doc = f"[{date}] {ticker}: {event_text}"
        meta = {"ticker": ticker, "date": date, **(metadata or {})}
        self._cols["stock_events"].add(
            documents=[doc],
            metadatas=[meta],
            ids=[str(uuid.uuid4())],
        )

    def add_market_regime(self, date: str, description: str) -> None:
        self._cols["market_regimes"].add(
            documents=[f"[{date}] {description}"],
            metadatas=[{"date": date}],
            ids=[str(uuid.uuid4())],
        )

    def add_lesson(self, week_label: str, lesson_text: str) -> None:
        self._cols["lessons_learned"].add(
            documents=[f"[{week_label}] {lesson_text}"],
            metadatas=[{"week": week_label}],
            ids=[str(uuid.uuid4())],
        )

    def add_hypothesis(self, hypothesis_id: str, text: str, metadata: dict | None = None) -> None:
        self._cols["hypothesis_ledger"].add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[hypothesis_id],
        )

    def update_hypothesis(self, hypothesis_id: str, outcome: str) -> None:
        try:
            existing = self._cols["hypothesis_ledger"].get(ids=[hypothesis_id])
            if existing["documents"]:
                updated = existing["documents"][0] + f" | OUTCOME: {outcome}"
                meta = existing["metadatas"][0]
                meta["outcome"] = outcome
                self._cols["hypothesis_ledger"].update(
                    ids=[hypothesis_id],
                    documents=[updated],
                    metadatas=[meta],
                )
        except Exception:
            pass

    def retrieve_relevant(
        self,
        query: str,
        collection: str = "stock_events",
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[str]:
        col = self._cols.get(collection)
        if col is None or col.count() == 0:
            return []
        try:
            kwargs: dict = {"query_texts": [query], "n_results": min(n_results, col.count())}
            if where:
                kwargs["where"] = where
            results = col.query(**kwargs)
            return results["documents"][0] if results["documents"] else []
        except Exception:
            return []

    def retrieve_latest_lesson(self) -> str:
        col = self._cols["lessons_learned"]
        if col.count() == 0:
            return ""
        try:
            results = col.get(include=["documents", "metadatas"])
            if not results["documents"]:
                return ""
            # sort by week label descending
            paired = sorted(
                zip(results["metadatas"], results["documents"]),
                key=lambda x: x[0].get("week", ""),
                reverse=True,
            )
            return paired[0][1] if paired else ""
        except Exception:
            return ""
