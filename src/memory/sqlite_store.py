import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
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
            self._migrate_predictions_table(conn)
            self._migrate_hypotheses_table(conn)

    def _migrate_hypotheses_table(self, conn) -> None:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(hypotheses)").fetchall()}
        for col_name, sql in [
            ("entry_price", "ALTER TABLE hypotheses ADD COLUMN entry_price REAL"),
            ("stop_loss",   "ALTER TABLE hypotheses ADD COLUMN stop_loss REAL"),
            ("target",      "ALTER TABLE hypotheses ADD COLUMN target REAL"),
            ("expiry",      "ALTER TABLE hypotheses ADD COLUMN expiry TEXT"),
            ("status",      "ALTER TABLE hypotheses ADD COLUMN status TEXT DEFAULT 'open'"),
        ]:
            if col_name not in existing:
                conn.execute(sql)

    def _migrate_predictions_table(self, conn) -> None:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()}
        for col_name, sql in [
            ("entry_price", "ALTER TABLE predictions ADD COLUMN entry_price REAL"),
            ("stop_loss",   "ALTER TABLE predictions ADD COLUMN stop_loss REAL"),
            ("target",      "ALTER TABLE predictions ADD COLUMN target REAL"),
            ("timeframe",   "ALTER TABLE predictions ADD COLUMN timeframe TEXT"),
        ]:
            if col_name not in existing:
                conn.execute(sql)

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
                    "INSERT INTO predictions "
                    "(id,run_id,date,ticker,direction,confidence,reasoning,"
                    "entry_price,stop_loss,target,timeframe,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), run_id, date,
                        p.get("ticker"), p.get("direction"),
                        p.get("confidence"), p.get("reasoning"),
                        p.get("entry_price"), p.get("stop_loss"),
                        p.get("target"), p.get("timeframe"),
                        _now(),
                    ),
                )

    def get_ticker_accuracy_summary(self, tickers: list[str], lookback_days: int = 30) -> list[dict]:
        """Return hit/total counts per ticker for the last N days, joining predictions with actuals."""
        if not tickers:
            return []
        cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
        placeholders = ",".join("?" * len(tickers))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT p.ticker,
                       COUNT(*) as total,
                       SUM(CASE
                         WHEN (p.direction='BUY'  AND a.pct_change > 0.5)  THEN 1
                         WHEN (p.direction='SELL' AND a.pct_change < -0.5) THEN 1
                         WHEN (p.direction='HOLD' AND ABS(a.pct_change) <= 1.0) THEN 1
                         ELSE 0
                       END) as correct
                FROM predictions p
                JOIN actuals a ON p.ticker = a.ticker AND p.date = a.date
                WHERE p.ticker IN ({placeholders})
                  AND p.date >= ?
                GROUP BY p.ticker
                """,
                (*tickers, cutoff),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_predictions_for_week(self, week_dates: list[str]) -> list[dict]:
        placeholders = ",".join("?" * len(week_dates))
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM predictions WHERE date IN ({placeholders}) ORDER BY date",
                week_dates,
            ).fetchall()
        return [dict(r) for r in rows]

    def get_predictions_for_date(self, date: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions WHERE date=? ORDER BY created_at",
                (date,),
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Hypotheses ---
    def save_hypothesis(
        self, id: str, date: str, ticker: str, thesis: str, evidence: str = "",
        entry_price: float | None = None, stop_loss: float | None = None,
        target: float | None = None, expiry: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hypotheses "
                "(id,date,ticker,thesis,evidence,entry_price,stop_loss,target,expiry,status) "
                "VALUES (?,?,?,?,?,?,?,?,?,'open')",
                (id, date, ticker, thesis, evidence, entry_price, stop_loss, target, expiry),
            )

    def get_hypotheses(self, status: str | None = None, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM hypotheses WHERE status=? ORDER BY date DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM hypotheses ORDER BY date DESC LIMIT ?", (limit,)
                ).fetchall()
        return [dict(r) for r in rows]

    def update_hypothesis(self, id: str, **kwargs) -> bool:
        allowed = {"outcome", "status", "evidence", "closed_at", "entry_price", "stop_loss", "target", "expiry", "thesis"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        set_clause = ", ".join(f"{k}=?" for k in fields)
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE hypotheses SET {set_clause} WHERE id=?",
                (*fields.values(), id),
            )
        return cur.rowcount > 0

    def delete_hypothesis(self, id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM hypotheses WHERE id=?", (id,))
        return cur.rowcount > 0

    # --- Actuals ---
    def save_actuals(self, date: str | list[dict], actuals: list[dict] | None = None) -> None:
        # Backward-compatible form: save_actuals(actuals)
        if actuals is None:
            actuals = date
            date = _now()[:10]
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
