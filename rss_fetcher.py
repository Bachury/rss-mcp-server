"""RSS feed fetcher and parser module."""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import asyncio

import feedparser
import httpx

FEEDS_CONFIG_PATH = Path(__file__).parent / "feeds_config.json"
REQUEST_TIMEOUT = 60
DEFAULT_LIMIT = 10
MAX_CONCURRENCY = 5
MAX_CONCURRENCY = 5


def load_feeds_config() -> list[dict]:
    """Load RSS feeds configuration from JSON file."""
    with open(FEEDS_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config["feeds"]


def _parse_published_time(entry: dict) -> Optional[str]:
    """Extract and normalize the published time from a feed entry."""
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct:
        try:
            dt = datetime(*time_struct[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return entry.get("published") or entry.get("updated") or ""


def _entry_to_dict(entry: dict, feed_name: str) -> dict:
    """Convert a feedparser entry to a clean dictionary."""
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()
    summary = entry.get("summary", "").strip()
    # Truncate long summaries
    if len(summary) > 500:
        summary = summary[:500] + "..."

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published": _parse_published_time(entry),
        "source": feed_name,
        "id": hashlib.md5(f"{title}{link}".encode()).hexdigest()[:12],
    }


async def fetch_single_feed(
    url: str, name: str = "", limit: int = DEFAULT_LIMIT
) -> dict:
    """Fetch and parse a single RSS feed.

    Args:
        url: RSS feed URL.
        name: Human-readable name for the feed source.
        limit: Maximum number of entries to return.

    Returns:
        Dict with feed metadata and entries list.
    """
    name = name or url
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=REQUEST_TIMEOUT
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "RSS-MCP-Server/1.0"})
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return {"source": name, "url": url, "error": str(e), "entries": []}

    feed = feedparser.parse(resp.text)

    if feed.bozo and not feed.entries:
        return {
            "source": name,
            "url": url,
            "error": f"Feed parse error: {feed.bozo_exception}",
            "entries": [],
        }

    entries = [_entry_to_dict(e, name) for e in feed.entries[:limit]]

    return {
        "source": name,
        "url": url,
        "total_available": len(feed.entries),
        "returned": len(entries),
        "entries": entries,
    }


async def fetch_multiple_feeds(
    urls: Optional[list[str]] = None,
    category: Optional[str] = None,
    limit_per_feed: int = 5,
) -> list[dict]:
    """Fetch multiple RSS feeds, optionally filtered by category.

    Args:
        urls: List of RSS URLs. If None, uses feeds from config.
        category: Filter config feeds by category (e.g. "国内AI垂直").
        limit_per_feed: Max entries per feed.

    Returns:
        List of feed results.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _limited_fetch(url: str, name: str = "", limit: int = 5):
        async with semaphore:
            return await fetch_single_feed(url, name=name, limit=limit)

    if urls:
        tasks = [_limited_fetch(u, limit=limit_per_feed) for u in urls]
        return list(await asyncio.gather(*tasks))

    # Use config feeds
    feeds = load_feeds_config()
    if category:
        feeds = [f for f in feeds if category in f.get("category", "")]

    tasks = [
        _limited_fetch(f["url"], name=f["name"], limit=limit_per_feed)
        for f in feeds
    ]
    return list(await asyncio.gather(*tasks))
