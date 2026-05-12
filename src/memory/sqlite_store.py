import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    run_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT DEFAULT 'running',
                    report_text TEXT
                );

                CREATE TABLE IF NOT EXISTS predictions (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    direction TEXT,
                    confidence TEXT,
                    reasoning TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS actuals (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    open REAL,
                    close REAL,
                    pct_change REAL,
                    recorded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS hypotheses (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    thesis TEXT,
                    evidence TEXT,
                    outcome TEXT,
                    closed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS usage_log (
                    id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    model TEXT,
                    task TEXT,
                    agent TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0
                );
            """)

    # --- Runs ---
    def start_run(self, run_id: str, run_type: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, run_type, started_at) VALUES (?,?,?)",
                (run_id, run_type, _now()),
            )

    def finish_run(self, run_id: str, report_text: str = "", status: str = "completed") -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE runs SET finished_at=?, status=?, report_text=? WHERE run_id=?",
                (_now(), status, report_text, run_id),
            )

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Predictions ---
    def save_predictions(self, run_id: str, date: str, predictions: list[dict]) -> None:
        with self._conn() as conn:
            for p in predictions:
                conn.execute(
                    "INSERT INTO predictions (id,run_id,date,ticker,direction,confidence,reasoning,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), run_id, date,
                        p.get("ticker"), p.get("direction"),
                        p.get("confidence"), p.get("reasoning"), _now(),
                    ),
                )

    def get_predictions_for_week(self, week_dates: list[str]) -> list[dict]:
        placeholders = ",".join("?" * len(week_dates))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM predictions WHERE date IN ({placeholders}) ORDER BY date",
                week_dates,
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Actuals ---
    def save_actuals(self, date: str, actuals: list[dict]) -> None:
        with self._conn() as conn:
            for a in actuals:
                conn.execute(
                    "INSERT OR REPLACE INTO actuals (id,date,ticker,open,close,pct_change,recorded_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), date,
                        a["ticker"], a.get("open"), a.get("close"),
                        a.get("pct_change"), _now(),
                    ),
                )

    def get_actuals_for_week(self, week_dates: list[str]) -> list[dict]:
        placeholders = ",".join("?" * len(week_dates))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM actuals WHERE date IN ({placeholders})",
                week_dates,
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Usage log ---
    def log_usage(
        self, model: str, task: str, agent: str,
        input_tokens: int, output_tokens: int, cost_usd: float
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO usage_log (id,ts,model,task,agent,input_tokens,output_tokens,cost_usd) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), _now(), model, task, agent, input_tokens, output_tokens, cost_usd),
            )

    def get_usage_summary(self, date_prefix: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT model, agent, SUM(input_tokens) as input_tokens, "
                "SUM(output_tokens) as output_tokens, SUM(cost_usd) as cost_usd, COUNT(*) as calls "
                "FROM usage_log WHERE ts LIKE ? GROUP BY model, agent",
                (f"{date_prefix}%",),
            ).fetchall()
        return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
