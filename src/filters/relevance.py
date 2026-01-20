"""Relevance filter for RSS articles based on keyword matching."""

import logging
import re
from typing import Optional

from ..config import RSS_FILTER_KEYWORDS, RSS_KEYWORD_THRESHOLD
from ..models.items import DigestItem

logger = logging.getLogger(__name__)


class RelevanceFilter:
    """Filter articles based on keyword relevance."""

    def __init__(
        self,
        keywords: list[str] = RSS_FILTER_KEYWORDS,
        threshold: int = RSS_KEYWORD_THRESHOLD,
    ):
        self.keywords = [kw.lower() for kw in keywords]
        self.threshold = threshold
        # Compile regex patterns for word boundary matching
        self.patterns = [
            re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            for kw in keywords
        ]

    def calculate_relevance(self, item: DigestItem) -> tuple[float, list[str]]:
        """Calculate relevance score and matched keywords for an item."""
        # Combine title and excerpt for matching
        text_parts = []
        if item.title:
            text_parts.append(item.title)
        if item.excerpt:
            text_parts.append(item.excerpt)
        if item.abstract:
            text_parts.append(item.abstract)

        text = " ".join(text_parts).lower()

        matched = []
        for keyword, pattern in zip(self.keywords, self.patterns):
            if pattern.search(text):
                matched.append(keyword)

        # Score is number of unique keyword matches
        score = len(matched)
        return score, matched

    def filter_relevant(self, items: list[DigestItem]) -> list[DigestItem]:
        """Filter items to only return those meeting relevance threshold."""
        relevant_items = []

        for item in items:
            score, matched = self.calculate_relevance(item)
            if score >= self.threshold:
                item.relevance_score = score
                item.matched_keywords = matched
                relevant_items.append(item)

        logger.info(
            f"Filtered {len(items)} items to {len(relevant_items)} relevant items "
            f"(threshold: {self.threshold})"
        )
        return relevant_items

    def score_and_sort(self, items: list[DigestItem]) -> list[DigestItem]:
        """Score all items and sort by relevance."""
        for item in items:
            score, matched = self.calculate_relevance(item)
            item.relevance_score = score
            item.matched_keywords = matched

        # Sort by relevance score (descending), then by date (descending)
        return sorted(
            items,
            key=lambda x: (x.relevance_score, x.date_published or x.date_fetched),
            reverse=True,
        )
