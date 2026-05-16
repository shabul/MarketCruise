import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class HypothesisCreate(BaseModel):
    ticker: str
    thesis: str
    evidence: str = ""
    entry_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    expiry: str | None = None


class HypothesisUpdate(BaseModel):
    outcome: str | None = None
    status: str | None = None
    evidence: str | None = None
    closed_at: str | None = None
    thesis: str | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    expiry: str | None = None


@router.get("/history")
async def get_history():
    from ..app import get_memory
    memory = get_memory()
    runs = memory.sqlite.get_recent_runs(limit=30)
    return runs


@router.get("/accuracy")
async def get_accuracy():
    from ..app import get_memory
    memory = get_memory()
    from datetime import timedelta
    dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]
    predictions = memory.sqlite.get_predictions_for_week(dates)
    actuals = {
        (a["ticker"], a["date"]): a
        for a in memory.sqlite.get_actuals_for_week(dates)
    }

    by_ticker: dict = {}
    for p in predictions:
        ticker = p["ticker"]
        actual = actuals.get((ticker, p["date"]))
        if not actual:
            continue
        pct = actual.get("pct_change", 0) or 0
        direction = p.get("direction", "").upper()
        hit = (direction == "BUY" and pct > 0.5) or \
              (direction == "SELL" and pct < -0.5) or \
              (direction == "HOLD" and abs(pct) <= 1.0)
        by_ticker.setdefault(ticker, {"correct": 0, "total": 0, "history": []})
        by_ticker[ticker]["total"] += 1
        by_ticker[ticker]["history"].append({"date": p["date"], "direction": direction, "hit": hit, "actual_pct": pct})
        if hit:
            by_ticker[ticker]["correct"] += 1

    return {
        "total_predictions": len(predictions),
        "by_ticker": by_ticker,
    }


@router.get("/usage")
async def get_usage():
    from ..app import get_memory
    memory = get_memory()
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
    return {
        "today": memory.sqlite.get_usage_summary(today_prefix),
        "month": memory.sqlite.get_usage_summary(month_prefix),
    }


@router.get("/portfolio")
async def get_portfolio():
    from ...tools.portfolio_tools import fetch_holdings, fetch_positions, calculate_portfolio_pnl
    holdings = fetch_holdings.invoke({})
    positions = fetch_positions.invoke({})
    pnl = calculate_portfolio_pnl.invoke({})
    return {"holdings": holdings, "positions": positions, "pnl": pnl}


@router.get("/config")
async def get_config():
    from ..app import get_config
    cfg = get_config()
    return {"watchlist": cfg.get("watchlist", [])}


@router.get("/predictions/today")
async def get_predictions_today():
    from ..app import get_memory
    memory = get_memory()
    today = date.today().isoformat()
    return memory.sqlite.get_predictions_for_date(today)


@router.get("/hypotheses")
async def list_hypotheses(status: str | None = Query(default=None)):
    from ..app import get_memory
    return get_memory().sqlite.get_hypotheses(status=status)


@router.post("/hypotheses")
async def create_hypothesis(body: HypothesisCreate):
    from ..app import get_memory
    id_ = str(uuid.uuid4())[:8]
    get_memory().sqlite.save_hypothesis(
        id_, date.today().isoformat(), **body.model_dump()
    )
    return {"id": id_}


@router.patch("/hypotheses/{hyp_id}")
async def update_hypothesis(hyp_id: str, body: HypothesisUpdate):
    from ..app import get_memory
    ok = get_memory().sqlite.update_hypothesis(hyp_id, **body.model_dump(exclude_none=True))
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@router.delete("/hypotheses/{hyp_id}")
async def delete_hypothesis(hyp_id: str):
    from ..app import get_memory
    ok = get_memory().sqlite.delete_hypothesis(hyp_id)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@router.get("/feedback")
async def get_feedback():
    from ..app import get_memory
    memory = get_memory()
    runs = memory.sqlite.get_recent_runs(limit=50)
    weekly = [r for r in runs if r.get("run_type") == "weekly"]
    if not weekly:
        return {"report": "", "date": None, "lessons": []}
    latest = weekly[0]
    return {
        "report": latest.get("report_text", ""),
        "date": latest.get("started_at"),
        "lessons": [],
    }


@router.get("/market/premarket")
async def get_premarket():
    import yfinance as yf
    SYMBOLS = [
        ("Nifty 50",  "^NSEI"),
        ("Bank Nifty", "^NIFTYBANK"),
        ("India VIX", "^INDIAVIX"),
        ("USD/INR",   "USDINR=X"),
        ("Crude Oil", "CL=F"),
        ("S&P 500",   "ES=F"),
        ("Nasdaq",    "NQ=F"),
        ("Nikkei",    "^N225"),
    ]
    result = []
    for label, sym in SYMBOLS:
        try:
            info = yf.Ticker(sym).fast_info
            price = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
            prev  = getattr(info, "previous_close", None) or getattr(info, "regular_market_previous_close", None)
            if price and prev:
                pct = ((price - prev) / prev) * 100
                result.append({
                    "label": label, "symbol": sym,
                    "value": round(price, 2), "pct_change": round(pct, 2),
                    "positive": pct >= 0,
                })
            else:
                result.append({"label": label, "symbol": sym, "value": None, "pct_change": None, "positive": True})
        except Exception:
            result.append({"label": label, "symbol": sym, "value": None, "pct_change": None, "positive": True})
    return result
