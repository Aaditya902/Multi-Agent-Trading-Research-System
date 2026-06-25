"""
Google News RSS fetcher for Indian financial news.
No paid API required — uses public RSS feeds.
"""

from __future__ import annotations
import re
import time
import feedparser
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from logging_config import logger


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; StockResearchBot/1.0; +https://github.com)"
    )
}

_RSS_TEMPLATES = [
    "https://news.google.com/rss/search?q={query}+stock+NSE&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q={query}+shares+India&hl=en-IN&gl=IN&ceid=IN:en",
    "https://feeds.feedburner.com/ndtvprofit-latest-business-news",
]

_BUSINESS_RSS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def fetch_google_news(company_name: str, ticker: str, max_articles: int = 15) -> list[dict]:
    """
    Fetch recent news articles for a stock via Google News RSS.
    Returns a list of dicts with keys: title, summary, link, published.
    """
    articles: list[dict] = []
    queries = [company_name, ticker.replace(".NS", "").replace(".BO", "")]

    for query in queries:
        url = _RSS_TEMPLATES[0].format(query=query.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_articles]:
                title = _clean_text(entry.get("title", ""))
                summary = _clean_text(entry.get("summary", "") or entry.get("description", ""))
                if not title:
                    continue
                articles.append({
                    "title": title,
                    "summary": summary[:500],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "Google News"),
                })
            if articles:
                break  # Got enough, skip second query
        except Exception as e:
            logger.warning(f"RSS fetch failed for query '{query}': {e}")
        time.sleep(0.5)

    logger.info(f"Fetched {len(articles)} news articles for {company_name}/{ticker}")
    return articles[:max_articles]


def fetch_market_news(max_articles: int = 20) -> list[dict]:
    """Fetch general Indian market news from Business Standard / ET / Moneycontrol RSS."""
    articles: list[dict] = []
    for rss_url in _BUSINESS_RSS:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                title = _clean_text(entry.get("title", ""))
                summary = _clean_text(entry.get("summary", "") or entry.get("description", ""))
                if title:
                    articles.append({
                        "title": title,
                        "summary": summary[:500],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": entry.get("source", {}).get("title", rss_url),
                    })
        except Exception as e:
            logger.warning(f"Market RSS fetch failed ({rss_url}): {e}")

    logger.info(f"Fetched {len(articles)} market news articles")
    return articles[:max_articles]


def extract_headlines(articles: list[dict]) -> list[str]:
    """Return just the headline strings from an article list."""
    return [a["title"] for a in articles if a.get("title")]


def _clean_text(text: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    cleaned = soup.get_text(separator=" ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned