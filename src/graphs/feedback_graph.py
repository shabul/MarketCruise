import json
from datetime import date, timedelta

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from ..state.schema import FeedbackState
from ..agents.base import make_llm, get_fallback_llm, is_quota_error, configure_usage_store, log_response_usage
from ..memory.memory_manager import MemoryManager


def _get_week_dates(week_offset: int = 0) -> list[str]:
    today = date.today()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
    return [(monday + timedelta(days=i)).isoformat() for i in range(5)]


def _week_label(week_offset: int = 1) -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
    return monday.strftime("%Y-W%V")


def build_feedback_graph(memory: MemoryManager, config: dict):

    def load_data(state: FeedbackState) -> dict:
        week_dates = _get_week_dates(week_offset=1)
        predictions = memory.sqlite.get_predictions_for_week(week_dates)
        actuals = memory.sqlite.get_actuals_for_week(week_dates)
        return {
            "prediction_records": predictions,
            "actual_records": actuals,
            "week_label": _week_label(1),
        }

    def compute_accuracy(state: FeedbackState) -> dict:
        preds = state["prediction_records"]
        actuals = {a["ticker"]: a for a in state["actual_records"]}

        total, correct = 0, 0
        by_ticker: dict = {}
        missed: list[str] = []

        for p in preds:
            ticker = p["ticker"]
            actual = actuals.get(ticker)
            if not actual:
                missed.append(ticker)
                continue
            total += 1
            pct = actual.get("pct_change", 0) or 0
            direction = p.get("direction", "").upper()
            hit = (direction == "BUY" and pct > 0.5) or \
                  (direction == "SELL" and pct < -0.5) or \
                  (direction == "HOLD" and abs(pct) <= 1.0)
            if hit:
                correct += 1
            by_ticker.setdefault(ticker, {"correct": 0, "total": 0})
            by_ticker[ticker]["total"] += 1
            if hit:
                by_ticker[ticker]["correct"] += 1

        accuracy = round(correct / total, 3) if total else 0
        stats = {
            "week": state["week_label"],
            "total_predictions": total,
            "correct": correct,
            "accuracy": accuracy,
            "by_ticker": by_ticker,
            "missing_actuals": missed,
        }
        return {"accuracy_stats": stats}

    def generate_feedback(state: FeedbackState) -> dict:
        stats = state["accuracy_stats"]
        preds_text = json.dumps(state["prediction_records"][:20], indent=2)
        actuals_text = json.dumps(state["actual_records"][:20], indent=2)
        stats_text = json.dumps(stats, indent=2)

        prompt = f"""Weekly prediction review for {state['week_label']}.

Accuracy stats:
{stats_text}

Sample predictions:
{preds_text}

Actual outcomes:
{actuals_text}

Write a structured feedback report covering:
1. Overall accuracy assessment and calibration (is "High confidence" actually accurate?)
2. Which stocks were consistently predicted well vs poorly — and why
3. What news or technical patterns were reliably predictive vs noisy
4. Specific adjustments to make in next week's analysis
5. A short "lessons learned" summary (3-5 bullets) to inject into future agent context

End with a JSON block:
```json
{{"week": "{state['week_label']}", "accuracy": {stats['accuracy']}, "key_lessons": ["lesson1", "lesson2"], "weak_stocks": [], "strong_stocks": []}}
```"""

        llm = make_llm(config.get("gemini", {}), use_heavy=True)
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
        except Exception as e:
            if is_quota_error(e):
                llm = get_fallback_llm(config.get("gemini", {}))
                response = llm.invoke([HumanMessage(content=prompt)])
            else:
                raise

        log_response_usage(response, "weekly_feedback", "feedback_graph", llm.model)

        return {
            "synthesized_feedback": response.content,
            "messages": [HumanMessage(content=prompt), response],
        }

    def save_feedback(state: FeedbackState) -> dict:
        week = state["week_label"]
        feedback_text = state["synthesized_feedback"]
        memory.save_weekly_lesson(week, feedback_text)
        return {}

    graph = StateGraph(FeedbackState)
    graph.add_node("load_data", load_data)
    graph.add_node("compute_accuracy", compute_accuracy)
    graph.add_node("generate_feedback", generate_feedback)
    graph.add_node("save_feedback", save_feedback)

    graph.set_entry_point("load_data")
    graph.add_edge("load_data", "compute_accuracy")
    graph.add_edge("compute_accuracy", "generate_feedback")
    graph.add_edge("generate_feedback", "save_feedback")
    graph.add_edge("save_feedback", END)

    return graph.compile()


def run_weekly_feedback(config: dict, memory: MemoryManager) -> str:
    configure_usage_store(memory.sqlite)
    graph = build_feedback_graph(memory, config)
    result = graph.invoke({
        "week_label": "",
        "prediction_records": [],
        "actual_records": [],
        "accuracy_stats": {},
        "news_feedback": "",
        "technical_feedback": "",
        "portfolio_feedback": "",
        "synthesized_feedback": "",
        "messages": [],
    })
    return result.get("synthesized_feedback", "Weekly feedback unavailable.")
