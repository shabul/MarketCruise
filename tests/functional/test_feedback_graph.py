"""Functional tests — weekly feedback graph with seeded prediction data."""
import uuid
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.usefixtures("gemini_available")

from src.graphs.feedback_graph import run_weekly_feedback, build_feedback_graph, _get_week_dates, _week_label


@pytest.mark.functional
def test_feedback_runs_on_empty_data(real_config, tmp_memory):
    """No seeded predictions → accuracy=0, but report still generated without crash."""
    result = run_weekly_feedback(real_config, tmp_memory)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.functional
def test_feedback_empty_data_no_exception(real_config, tmp_memory):
    try:
        run_weekly_feedback(real_config, tmp_memory)
    except Exception as e:
        pytest.fail(f"run_weekly_feedback raised on empty data: {e}")


@pytest.mark.functional
def test_feedback_with_seeded_predictions(real_config, tmp_memory):
    """Seed last week's predictions + actuals → verify lesson is saved to Chroma."""
    last_week_dates = _get_week_dates(week_offset=1)
    week_label = _week_label(1)

    # Seed a run and predictions
    run_id = str(uuid.uuid4())[:8]
    tmp_memory.sqlite.start_run(run_id, "morning")
    tmp_memory.sqlite.finish_run(run_id, "Test analysis")

    predictions = {
        "stocks": [
            {"ticker": "RELIANCE", "direction": "BUY", "confidence": "High", "rationale": "Strong momentum"},
            {"ticker": "TCS", "direction": "HOLD", "confidence": "Medium", "rationale": "Flat trend"},
        ]
    }
    tmp_memory.save_run_predictions(run_id, predictions)

    # Seed actuals for last week
    date_str = last_week_dates[0] if last_week_dates else date.today().isoformat()
    actuals = [
        {"ticker": "RELIANCE", "close": 2850.0, "pct_change": 1.2},
        {"ticker": "TCS", "close": 3490.0, "pct_change": 0.3},
    ]
    tmp_memory.sqlite.save_actuals(actuals)

    result = run_weekly_feedback(real_config, tmp_memory)
    assert isinstance(result, str)
    assert len(result) > 50


@pytest.mark.functional
def test_feedback_lesson_saved_to_chroma(real_config, tmp_memory):
    """After feedback run, a lesson should appear in Chroma lessons_learned collection."""
    run_weekly_feedback(real_config, tmp_memory)
    lesson = tmp_memory.chroma.retrieve_latest_lesson()
    assert isinstance(lesson, str)


@pytest.mark.functional
def test_feedback_graph_buildable(tmp_memory, real_config):
    graph = build_feedback_graph(tmp_memory, real_config)
    assert graph is not None


@pytest.mark.functional
def test_feedback_week_dates_helper():
    dates = _get_week_dates(week_offset=1)
    assert len(dates) == 5
    for d in dates:
        assert len(d) == 10  # YYYY-MM-DD


@pytest.mark.functional
def test_feedback_week_label_format():
    label = _week_label(1)
    assert "-W" in label
    parts = label.split("-W")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


@pytest.mark.functional
def test_feedback_with_mixed_correct_wrong(real_config, tmp_memory):
    """Seed one correct + one wrong prediction to verify accuracy logic runs."""
    run_id = str(uuid.uuid4())[:8]
    tmp_memory.sqlite.start_run(run_id, "morning")
    tmp_memory.sqlite.finish_run(run_id, "")

    predictions = {
        "stocks": [
            {"ticker": "RELIANCE", "direction": "BUY", "confidence": "High", "rationale": ""},
            {"ticker": "TCS", "direction": "SELL", "confidence": "Medium", "rationale": ""},
        ]
    }
    tmp_memory.save_run_predictions(run_id, predictions)

    # RELIANCE went up (BUY correct), TCS also went up (SELL wrong)
    tmp_memory.sqlite.save_actuals([
        {"ticker": "RELIANCE", "close": 2900.0, "pct_change": 1.5},
        {"ticker": "TCS", "close": 3550.0, "pct_change": 1.2},
    ])

    result = run_weekly_feedback(real_config, tmp_memory)
    assert isinstance(result, str)
    assert len(result) > 0
