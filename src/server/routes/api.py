from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


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
    # Last 30 days of predictions vs actuals
    from datetime import date, timedelta
    dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(30)]
    predictions = memory.sqlite.get_predictions_for_week(dates)
    actuals = {a["ticker"]: a for a in memory.sqlite.get_actuals_for_week(dates)}

    by_ticker: dict = {}
    for p in predictions:
        ticker = p["ticker"]
        actual = actuals.get(ticker)
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
