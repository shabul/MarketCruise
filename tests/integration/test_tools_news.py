"""Integration tests for news tools — real NewsAPI + Google RSS calls."""
import os
import pytest
from src.tools.news_tools import fetch_stock_news, fetch_sector_news, fetch_macro_news


@pytest.mark.integration
def test_stock_news_returns_articles():
    result = fetch_stock_news.invoke({"ticker": "RELIANCE", "hours": 48, "max_articles": 5})
    assert isinstance(result, str)
    assert len(result) > 10
    # Either real articles or no-news message
    has_articles = "[" in result
    no_news = "No recent news" in result
    assert has_articles or no_news


@pytest.mark.integration
def test_stock_news_format():
    result = fetch_stock_news.invoke({"ticker": "TCS", "hours": 72, "max_articles": 3})
    if "No recent news" not in result:
        lines = [l for l in result.strip().split("\n") if l.strip()]
        for line in lines:
            assert line.startswith("["), f"Article line should start with '[source]': {line}"


@pytest.mark.integration
def test_stock_news_tcs():
    result = fetch_stock_news.invoke({"ticker": "TCS", "hours": 168})  # 7 days
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_sector_news_it():
    result = fetch_sector_news.invoke({"sector": "IT", "hours": 48})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_sector_news_banking():
    result = fetch_sector_news.invoke({"sector": "Banking", "hours": 48})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_macro_news_returns_articles():
    result = fetch_macro_news.invoke({"hours": 48})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_news_fallback_to_rss_when_no_api_key(monkeypatch):
    """Google RSS fallback works even without NewsAPI key."""
    monkeypatch.delenv("NEWS_API_KEY", raising=False)
    result = fetch_stock_news.invoke({"ticker": "RELIANCE", "hours": 72})
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_news_api_key_is_used_when_present():
    """If NEWS_API_KEY is set, it should attempt NewsAPI first."""
    if not os.environ.get("NEWS_API_KEY"):
        pytest.skip("NEWS_API_KEY not set")
    result = fetch_stock_news.invoke({"ticker": "INFY", "hours": 24, "max_articles": 3})
    assert isinstance(result, str)


@pytest.mark.integration
def test_stock_news_handles_obscure_ticker():
    """Ticker with no news should return graceful message, not raise."""
    result = fetch_stock_news.invoke({"ticker": "ZZZZOBSCUREXYZ", "hours": 24})
    assert isinstance(result, str)
    # Should not raise, should return empty message
    assert "No recent news" in result or len(result) > 0
