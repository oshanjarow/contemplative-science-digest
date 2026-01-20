"""Semantic Scholar API client for fetching papers."""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import requests

from ..config import (
    SEMANTIC_SCHOLAR_BASE_URL,
    SEMANTIC_SCHOLAR_FIELDS,
    ALL_KEYWORDS,
    TRACKED_VENUES,
)
from ..models.items import DigestItem, Author, ItemType, SourceType

logger = logging.getLogger(__name__)


class SemanticScholarClient:
    """Client for the Semantic Scholar API."""

    def __init__(self, rate_limit_delay: float = 1.0):
        self.base_url = SEMANTIC_SCHOLAR_BASE_URL
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0

    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make a rate-limited request to the API."""
        self._rate_limit()
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def search_author(self, name: str) -> Optional[str]:
        """Search for an author by name and return their Semantic Scholar ID."""
        params = {"query": name, "fields": "name,authorId,paperCount"}
        data = self._make_request("author/search", params)
        if data and data.get("data"):
            # Return the first match with the most papers
            authors = sorted(data["data"], key=lambda x: x.get("paperCount", 0), reverse=True)
            if authors:
                author = authors[0]
                logger.info(f"Found author {name}: {author['authorId']} ({author.get('paperCount', 0)} papers)")
                return author["authorId"]
        logger.warning(f"Author not found: {name}")
        return None

    def get_author_papers(
        self, author_id: str, limit: int = 100, days_back: int = 365
    ) -> list[DigestItem]:
        """Fetch recent papers by an author."""
        params = {
            "fields": SEMANTIC_SCHOLAR_FIELDS,
            "limit": limit,
        }
        data = self._make_request(f"author/{author_id}/papers", params)
        if not data:
            return []

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        items = []
        for paper in data.get("data", []):
            item = self._paper_to_item(paper)
            if item and item.date_published and item.date_published >= cutoff_date:
                items.append(item)

        logger.info(f"Found {len(items)} recent papers for author {author_id}")
        return items

    def get_author_coauthors(self, author_id: str) -> list[dict]:
        """Get co-authors of an author."""
        # First get the author's papers to find co-authors
        params = {
            "fields": "authors",
            "limit": 500,
        }
        data = self._make_request(f"author/{author_id}/papers", params)
        if not data:
            return []

        coauthor_counts = {}
        for paper in data.get("data", []):
            for author in paper.get("authors", []):
                aid = author.get("authorId")
                if aid and aid != author_id:
                    if aid not in coauthor_counts:
                        coauthor_counts[aid] = {"name": author.get("name"), "count": 0}
                    coauthor_counts[aid]["count"] += 1

        # Return co-authors sorted by collaboration count
        coauthors = [
            {"authorId": aid, "name": info["name"], "paperCount": info["count"]}
            for aid, info in coauthor_counts.items()
        ]
        return sorted(coauthors, key=lambda x: x["paperCount"], reverse=True)

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        venue: Optional[str] = None,
    ) -> list[DigestItem]:
        """Search for papers by query."""
        params = {
            "query": query,
            "fields": SEMANTIC_SCHOLAR_FIELDS,
            "limit": limit,
        }
        if year_from:
            params["year"] = f"{year_from}-"
        if venue:
            params["venue"] = venue

        data = self._make_request("paper/search", params)
        if not data:
            return []

        items = []
        for paper in data.get("data", []):
            item = self._paper_to_item(paper)
            if item:
                items.append(item)

        logger.info(f"Found {len(items)} papers for query: {query}")
        return items

    def search_by_keywords(self, limit_per_keyword: int = 50, year_from: Optional[int] = None) -> list[DigestItem]:
        """Search for papers using configured keywords."""
        all_items = []
        seen_ids = set()

        for keyword in ALL_KEYWORDS:
            items = self.search_papers(keyword, limit=limit_per_keyword, year_from=year_from)
            for item in items:
                uid = item.get_unique_id()
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    item.matched_keywords.append(keyword)
                    all_items.append(item)

        logger.info(f"Total unique papers from keyword search: {len(all_items)}")
        return all_items

    def search_by_venues(self, limit_per_venue: int = 50, year_from: Optional[int] = None) -> list[DigestItem]:
        """Search for papers in tracked venues."""
        all_items = []
        seen_ids = set()

        for venue in TRACKED_VENUES:
            items = self.search_papers("", limit=limit_per_venue, year_from=year_from, venue=venue)
            for item in items:
                uid = item.get_unique_id()
                if uid not in seen_ids:
                    seen_ids.add(uid)
                    all_items.append(item)

        logger.info(f"Total unique papers from venue search: {len(all_items)}")
        return all_items

    def _paper_to_item(self, paper: dict) -> Optional[DigestItem]:
        """Convert a Semantic Scholar paper to a DigestItem."""
        if not paper.get("title"):
            return None

        # Extract DOI
        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI")

        # Parse publication date
        date_published = None
        pub_date_str = paper.get("publicationDate")
        if pub_date_str:
            try:
                date_published = datetime.strptime(pub_date_str, "%Y-%m-%d")
            except ValueError:
                pass

        # Extract authors
        authors = []
        for author in paper.get("authors", []):
            authors.append(
                Author(
                    name=author.get("name", "Unknown"),
                    author_id=author.get("authorId"),
                )
            )

        # Build URL
        paper_id = paper.get("paperId")
        url = paper.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"

        return DigestItem(
            title=paper["title"],
            url=url,
            item_type=ItemType.PAPER,
            source_type=SourceType.SEMANTIC_SCHOLAR,
            date_published=date_published,
            doi=doi,
            authors=authors,
            abstract=paper.get("abstract"),
            journal=paper.get("venue"),
            year=paper.get("year"),
        )
