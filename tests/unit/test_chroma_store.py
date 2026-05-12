"""Unit tests for ChromaStore — uses local ChromaDB, no network."""
import pytest


@pytest.mark.unit
def test_add_and_retrieve_stock_event(tmp_chroma):
    tmp_chroma.add_stock_event("TCS", "2026-05-10", "TCS Q4 results beat estimates by 8%")
    results = tmp_chroma.retrieve_relevant("TCS results quarterly", collection="stock_events", n_results=1)
    assert len(results) == 1
    assert "TCS" in results[0]


@pytest.mark.unit
def test_retrieve_from_empty_collection(tmp_chroma):
    results = tmp_chroma.retrieve_relevant("anything", collection="stock_events", n_results=5)
    assert results == []


@pytest.mark.unit
def test_n_results_clamped_to_count(tmp_chroma):
    for i in range(3):
        tmp_chroma.add_stock_event("RELIANCE", f"2026-05-0{i+1}", f"Event {i}")
    results = tmp_chroma.retrieve_relevant("RELIANCE", collection="stock_events", n_results=10)
    assert len(results) <= 3


@pytest.mark.unit
def test_lessons_sorted_descending(tmp_chroma):
    tmp_chroma.add_lesson("2026-W15", "Lesson from week 15: IT sector signals were reliable")
    tmp_chroma.add_lesson("2026-W17", "Lesson from week 17: Banking calls were off")
    tmp_chroma.add_lesson("2026-W16", "Lesson from week 16: FII data was predictive")
    latest = tmp_chroma.retrieve_latest_lesson()
    assert "W17" in latest


@pytest.mark.unit
def test_retrieve_latest_lesson_empty_db(tmp_chroma):
    result = tmp_chroma.retrieve_latest_lesson()
    assert result == ""


@pytest.mark.unit
def test_add_market_regime(tmp_chroma):
    tmp_chroma.add_market_regime("2026-05-01", "FII selling phase — ₹12,000 Cr outflow over 5 sessions")
    results = tmp_chroma.retrieve_relevant("FII selling market", collection="market_regimes", n_results=1)
    assert len(results) == 1
    assert "FII" in results[0]


@pytest.mark.unit
def test_add_and_update_hypothesis(tmp_chroma):
    tmp_chroma.add_hypothesis("hyp-001", "TCS will rise on IT sector momentum", {"ticker": "TCS"})
    tmp_chroma.update_hypothesis("hyp-001", "CORRECT — TCS rose 2.3%")
    results = tmp_chroma.retrieve_relevant("TCS hypothesis outcome", collection="hypothesis_ledger", n_results=1)
    assert len(results) >= 1


@pytest.mark.unit
def test_update_nonexistent_hypothesis_no_crash(tmp_chroma):
    tmp_chroma.update_hypothesis("does-not-exist", "some outcome")


@pytest.mark.unit
def test_multiple_collections_isolated(tmp_chroma):
    tmp_chroma.add_stock_event("INFY", "2026-05-01", "INFY raised guidance")
    events = tmp_chroma.retrieve_relevant("INFY guidance", collection="stock_events", n_results=5)
    regimes = tmp_chroma.retrieve_relevant("INFY guidance", collection="market_regimes", n_results=5)
    assert len(events) >= 1
    assert len(regimes) == 0
