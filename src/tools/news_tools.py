import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Annotated

import feedparser
import requests
from langchain_core.tools import tool


_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
_NEWSAPI_URL = "https://newsapi.org/v2/everything"


def _google_rss(query: str, max_articles: int, since_hours: int) -> list[str]:
    url = _GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
    feed = feedparser.parse(url)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    lines = []
    for entry in feed.entries:
        try:
            pub = parsedate_to_datetime(entry.get("published", ""))
            if pub < cutoff:
                continue
        except Exception:
            pass
        source = entry.get("source", {}).get("title", "Google News")
        published = entry.get("published", "")[:16]
        lines.append(f"[{source}] {entry.get('title','')} ({published})")
        if len(lines) >= max_articles:
            break
    return lines


def _newsapi(query: str, max_articles: int, since_hours: int) -> list[str]:
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        return []
    from_dt = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        resp = requests.get(
            _NEWSAPI_URL,
            params={"q": query, "from": from_dt, "sortBy": "publishedAt",
                    "pageSize": max_articles, "apiKey": api_key, "language": "en"},
            timeout=10,
        )
        resp.raise_for_status()
        return [
            f"[{a['source']['name']}] {a['title']} ({a['publishedAt'][:16]})"
            for a in resp.json().get("articles", [])
        ]
    except Exception:
        return []


@tool
def fetch_stock_news(
    ticker: Annotated[str, "NSE ticker symbol"],
    hours: Annotated[int, "Look back this many hours"] = 24,
    max_articles: Annotated[int, "Max articles to return"] = 5,
) -> str:
    """Fetch recent news for a specific NSE-listed stock."""
    query = f"{ticker} NSE stock India"
    lines = _newsapi(query, max_articles, hours) or _google_rss(query, max_articles, hours)
    return "\n".join(lines) if lines else f"No recent news found for {ticker}."


@tool
def fetch_sector_news(
    sector: Annotated[str, "Sector name (e.g. IT, Banking, FMCG)"],
    hours: Annotated[int, "Look back this many hours"] = 24,
) -> str:
    """Fetch recent news for a market sector to understand sector-wide trends."""
    lines = _google_rss(f"{sector} sector India stock market", 8, hours)
    return "\n".join(lines) if lines else f"No recent sector news for {sector}."


@tool
def fetch_macro_news(hours: Annotated[int, "Look back this many hours"] = 24) -> str:
    """Fetch macro-level Indian market news: RBI, Nifty, economy, FII activity."""
    seen: set[str] = set()
    lines: list[str] = []
    for q in ["NSE Nifty India market", "RBI India interest rate", "India economy GDP inflation"]:
        for l in _google_rss(q, 5, hours):
            if l not in seen:
                seen.add(l)
                lines.append(l)
    return "\n".join(lines[:10]) if lines else "No macro news found."
