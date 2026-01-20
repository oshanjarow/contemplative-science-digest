"""Data models for the Contemplative Science Digest."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from enum import Enum


class ItemType(Enum):
    PAPER = "paper"
    ARTICLE = "article"


class SourceType(Enum):
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"
    RSS = "rss"


@dataclass
class Author:
    """Represents a paper/article author."""
    name: str
    author_id: Optional[str] = None  # Semantic Scholar ID
    affiliation: Optional[str] = None


@dataclass
class DigestItem:
    """Base class for all digest items (papers and articles)."""
    title: str
    url: str
    item_type: ItemType
    source_type: SourceType
    date_published: Optional[datetime] = None
    date_fetched: datetime = field(default_factory=datetime.utcnow)

    # Unique identifiers for deduplication
    doi: Optional[str] = None

    # Content
    authors: list[Author] = field(default_factory=list)
    abstract: Optional[str] = None

    # Paper-specific
    journal: Optional[str] = None
    year: Optional[int] = None

    # Article-specific (RSS)
    source_name: Optional[str] = None  # e.g., "Aeon", "Nautilus"
    excerpt: Optional[str] = None

    # Relevance metadata
    relevance_score: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)

    def get_unique_id(self) -> str:
        """Generate a unique ID for deduplication."""
        if self.doi:
            return f"doi:{self.doi}"
        # Fall back to URL-based ID
        return f"url:{self.url}"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['item_type'] = self.item_type.value
        data['source_type'] = self.source_type.value
        if self.date_published:
            data['date_published'] = self.date_published.isoformat()
        data['date_fetched'] = self.date_fetched.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'DigestItem':
        """Create from dictionary."""
        data['item_type'] = ItemType(data['item_type'])
        data['source_type'] = SourceType(data['source_type'])
        if data.get('date_published'):
            data['date_published'] = datetime.fromisoformat(data['date_published'])
        if data.get('date_fetched'):
            data['date_fetched'] = datetime.fromisoformat(data['date_fetched'])
        data['authors'] = [Author(**a) for a in data.get('authors', [])]
        return cls(**data)


@dataclass
class TrackedAuthor:
    """Represents a tracked researcher."""
    name: str
    semantic_scholar_id: str
    tier: int = 1  # 1 = directly tracked, 2 = co-author
    institution: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TrackedAuthor':
        return cls(**data)
