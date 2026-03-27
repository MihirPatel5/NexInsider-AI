"""
ingestion/news.py — News ingestion pipeline.
Pulls from MoneyControl + Economic Times RSS feeds via feedparser.
Stores items in the news_items table for sentiment processing.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List

import feedparser
from loguru import logger
from sqlalchemy import text

from data.db import get_session

# ─── RSS feed URLs ────────────────────────────────────────────────────────────
FEEDS = [
    {
        "name":  "MoneyControl Markets",
        "url":   "https://www.moneycontrol.com/rss/marketreports.xml",
    },
    {
        "name":  "MoneyControl Business",
        "url":   "https://www.moneycontrol.com/rss/business.xml",
    },
    {
        "name":  "Economic Times Markets",
        "url":   "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    },
    {
        "name":  "Economic Times Companies",
        "url":   "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    },
    {
        "name":  "Business Standard",
        "url":   "https://www.business-standard.com/rss/markets-106.rss",
    },
]


def _parse_date(entry) -> datetime:
    try:
        return parsedate_to_datetime(entry.get("published", "")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(tz=timezone.utc)


async def fetch_and_store_news() -> int:
    """
    Fetch all configured RSS feeds and insert new items into the DB.
    Returns total count of new items stored.
    """
    total_new = 0
    for feed_config in FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            entries = feed.entries[:50]  # cap at 50 per feed per run
        except Exception as exc:
            logger.error(f"[news] Failed to parse {feed_config['name']}: {exc}")
            continue

        for entry in entries:
            published_at = _parse_date(entry)
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            url     = entry.get("link", "").strip()

            if not title or not url:
                continue

            try:
                async with get_session() as session:
                    result = await session.execute(
                        text("""
                            INSERT INTO news_items (published_at, title, summary, source, url)
                            VALUES (:published_at, :title, :summary, :source, :url)
                            ON CONFLICT (url) DO NOTHING
                            RETURNING id
                        """),
                        dict(
                            published_at=published_at,
                            title=title,
                            summary=summary,
                            source=feed_config["name"],
                            url=url,
                        ),
                    )
                    if result.rowcount:
                        total_new += 1
            except Exception as exc:
                logger.debug(f"[news] Skipped duplicate or error: {exc}")

    logger.info(f"[news] Stored {total_new} new articles across {len(FEEDS)} feeds")
    return total_new


async def get_unprocessed_news(limit: int = 100) -> List[dict]:
    """Return news items not yet scored by finBERT."""
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT id, published_at, title, summary, source, url
                FROM news_items
                WHERE processed = FALSE
                ORDER BY published_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()
    return [
        {
            "id": r[0], "published_at": r[1], "title": r[2],
            "summary": r[3], "source": r[4], "url": r[5],
        }
        for r in rows
    ]
