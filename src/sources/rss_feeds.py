"""RSS feed parser for magazine articles."""

import logging
from datetime import datetime
from typing import Optional
from email.utils import parsedate_to_datetime

import feedparser
import requests

from ..config import RSS_FEEDS
from ..models.items import DigestItem, Author, ItemType, SourceType

logger = logging.getLogger(__name__)


class RSSFeedParser:
    """Parser for RSS feeds from various sources."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.feeds = RSS_FEEDS

    def fetch_all_feeds(self) -> list[DigestItem]:
        """Fetch articles from all configured RSS feeds."""
        all_items = []

        for source_name, feed_url in self.feeds.items():
            try:
                items = self._fetch_feed(source_name, feed_url)
                all_items.extend(items)
                logger.info(f"Fetched {len(items)} items from {source_name}")
            except Exception as e:
                logger.error(f"Failed to fetch {source_name}: {e}")

        logger.info(f"Total RSS items fetched: {len(all_items)}")
        return all_items

    def _fetch_feed(self, source_name: str, feed_url: str) -> list[DigestItem]:
        """Fetch and parse a single RSS feed."""
        try:
            # Use requests for better timeout handling
            response = requests.get(feed_url, timeout=self.timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {feed_url}: {e}")
            return []

        items = []
        for entry in feed.entries:
            item = self._entry_to_item(entry, source_name)
            if item:
                items.append(item)

        return items

    def _entry_to_item(self, entry, source_name: str) -> Optional[DigestItem]:
        """Convert a feed entry to a DigestItem."""
        # Get title
        title = entry.get("title")
        if not title:
            return None

        # Get URL
        url = entry.get("link")
        if not url:
            return None

        # Get description/excerpt
        excerpt = None
        if entry.get("summary"):
            excerpt = self._clean_html(entry.summary)
        elif entry.get("description"):
            excerpt = self._clean_html(entry.description)

        # Truncate excerpt if too long
        if excerpt and len(excerpt) > 500:
            excerpt = excerpt[:497] + "..."

        # Get author
        authors = []
        author_name = entry.get("author")
        if author_name:
            authors.append(Author(name=author_name))
        elif entry.get("authors"):
            for author in entry.authors:
                if isinstance(author, dict) and author.get("name"):
                    authors.append(Author(name=author["name"]))

        # Parse publication date
        date_published = None
        if entry.get("published_parsed"):
            try:
                date_published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        elif entry.get("published"):
            try:
                date_published = parsedate_to_datetime(entry.published)
            except (TypeError, ValueError):
                pass
        elif entry.get("updated_parsed"):
            try:
                date_published = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        return DigestItem(
            title=title,
            url=url,
            item_type=ItemType.ARTICLE,
            source_type=SourceType.RSS,
            date_published=date_published,
            authors=authors,
            source_name=source_name,
            excerpt=excerpt,
        )

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        import re

        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        # Decode HTML entities
        import html
        clean = html.unescape(clean)
        return clean
