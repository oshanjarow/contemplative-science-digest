"""Deduplication filter to track and filter seen items."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..config import SEEN_ITEMS_FILE, ARCHIVE_DAYS
from ..models.items import DigestItem

logger = logging.getLogger(__name__)


class DeduplicationFilter:
    """Filter to track and deduplicate items across runs."""

    def __init__(self, seen_file: Path = SEEN_ITEMS_FILE):
        self.seen_file = seen_file
        self.seen_items: dict[str, dict] = {}
        self._load()

    def _load(self):
        """Load seen items from file."""
        if self.seen_file.exists():
            try:
                with open(self.seen_file, "r") as f:
                    data = json.load(f)
                    self.seen_items = data.get("items", {})
                    logger.info(f"Loaded {len(self.seen_items)} seen items")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load seen items: {e}")
                self.seen_items = {}

    def save(self):
        """Save seen items to file."""
        self.seen_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.seen_file, "w") as f:
                json.dump({"items": self.seen_items}, f, indent=2)
            logger.info(f"Saved {len(self.seen_items)} seen items")
        except IOError as e:
            logger.error(f"Failed to save seen items: {e}")

    def is_seen(self, item: DigestItem) -> bool:
        """Check if an item has been seen before."""
        uid = item.get_unique_id()
        return uid in self.seen_items

    def mark_seen(self, item: DigestItem):
        """Mark an item as seen."""
        uid = item.get_unique_id()
        self.seen_items[uid] = {
            "title": item.title,
            "first_seen": datetime.utcnow().isoformat(),
        }

    def filter_new(self, items: list[DigestItem]) -> list[DigestItem]:
        """Filter items to only return new (unseen) ones."""
        new_items = []
        for item in items:
            if not self.is_seen(item):
                new_items.append(item)
                self.mark_seen(item)

        logger.info(f"Filtered {len(items)} items to {len(new_items)} new items")
        return new_items

    def cleanup_old(self, days: int = ARCHIVE_DAYS):
        """Remove items older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        original_count = len(self.seen_items)

        to_remove = []
        for uid, data in self.seen_items.items():
            first_seen_str = data.get("first_seen")
            if first_seen_str:
                try:
                    first_seen = datetime.fromisoformat(first_seen_str)
                    if first_seen < cutoff:
                        to_remove.append(uid)
                except ValueError:
                    pass

        for uid in to_remove:
            del self.seen_items[uid]

        removed_count = original_count - len(self.seen_items)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old items")

    def deduplicate_within_list(self, items: list[DigestItem]) -> list[DigestItem]:
        """Remove duplicates within a list of items (by DOI or URL)."""
        seen_ids = set()
        unique_items = []

        for item in items:
            uid = item.get_unique_id()
            if uid not in seen_ids:
                seen_ids.add(uid)
                unique_items.append(item)

        if len(items) != len(unique_items):
            logger.info(f"Removed {len(items) - len(unique_items)} duplicates within list")

        return unique_items
