"""Main entry point for the Contemplative Science Digest."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import (
    DATA_DIR,
    AUTHOR_IDS_FILE,
    TIER1_RESEARCHERS,
    COAUTHOR_MIN_PAPERS,
)
from .sources.semantic_scholar import SemanticScholarClient
from .sources.pubmed import PubMedClient
from .sources.rss_feeds import RSSFeedParser
from .filters.deduplication import DeduplicationFilter
from .filters.relevance import RelevanceFilter
from .site_generator.builder import SiteBuilder
from .models.items import DigestItem, ItemType, TrackedAuthor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_author_ids() -> dict[str, TrackedAuthor]:
    """Load tracked author IDs from file."""
    if AUTHOR_IDS_FILE.exists():
        try:
            with open(AUTHOR_IDS_FILE, "r") as f:
                data = json.load(f)
                return {
                    name: TrackedAuthor.from_dict(info)
                    for name, info in data.get("authors", {}).items()
                }
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load author IDs: {e}")
    return {}


def save_author_ids(authors: dict[str, TrackedAuthor]):
    """Save tracked author IDs to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "updated_at": datetime.utcnow().isoformat(),
        "authors": {name: author.to_dict() for name, author in authors.items()},
    }
    with open(AUTHOR_IDS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved {len(authors)} author IDs")


def lookup_author_ids(ss_client: SemanticScholarClient) -> dict[str, TrackedAuthor]:
    """Look up Semantic Scholar IDs for Tier 1 researchers."""
    authors = load_author_ids()

    for name in TIER1_RESEARCHERS:
        if name not in authors:
            logger.info(f"Looking up author ID for {name}...")
            author_id = ss_client.search_author(name)
            if author_id:
                authors[name] = TrackedAuthor(
                    name=name,
                    semantic_scholar_id=author_id,
                    tier=1,
                )
            else:
                logger.warning(f"Could not find author ID for {name}")

    save_author_ids(authors)
    return authors


def discover_coauthors(
    ss_client: SemanticScholarClient,
    authors: dict[str, TrackedAuthor],
    min_papers: int = COAUTHOR_MIN_PAPERS,
) -> dict[str, TrackedAuthor]:
    """Discover co-authors of Tier 1 researchers and add as Tier 2."""
    tier1_ids = {a.semantic_scholar_id for a in authors.values() if a.tier == 1}

    for name, author in list(authors.items()):
        if author.tier != 1:
            continue

        logger.info(f"Discovering co-authors of {name}...")
        coauthors = ss_client.get_author_coauthors(author.semantic_scholar_id)

        for coauthor in coauthors:
            if coauthor["paperCount"] >= min_papers:
                coauthor_id = coauthor["authorId"]
                coauthor_name = coauthor["name"]

                # Skip if already in our list
                if coauthor_id in tier1_ids:
                    continue
                if any(a.semantic_scholar_id == coauthor_id for a in authors.values()):
                    continue

                authors[coauthor_name] = TrackedAuthor(
                    name=coauthor_name,
                    semantic_scholar_id=coauthor_id,
                    tier=2,
                )
                logger.info(
                    f"Added Tier 2 co-author: {coauthor_name} "
                    f"({coauthor['paperCount']} papers with {name})"
                )

    save_author_ids(authors)
    return authors


def fetch_papers_from_authors(
    ss_client: SemanticScholarClient,
    authors: dict[str, TrackedAuthor],
    days_back: int = 365,
) -> list[DigestItem]:
    """Fetch papers from tracked authors."""
    all_papers = []
    seen_ids = set()

    for name, author in authors.items():
        papers = ss_client.get_author_papers(
            author.semantic_scholar_id,
            days_back=days_back,
        )
        for paper in papers:
            uid = paper.get_unique_id()
            if uid not in seen_ids:
                seen_ids.add(uid)
                all_papers.append(paper)

    logger.info(f"Fetched {len(all_papers)} unique papers from tracked authors")
    return all_papers


def run_digest(
    skip_author_lookup: bool = False,
    skip_coauthors: bool = False,
    skip_semantic_scholar: bool = False,
    skip_pubmed: bool = False,
    skip_rss: bool = False,
    days_back: int = 7,
):
    """Run the full digest pipeline."""
    logger.info(f"Starting Contemplative Science Digest (looking back {days_back} days)...")

    # Initialize clients
    ss_client = SemanticScholarClient()
    pubmed_client = PubMedClient()
    rss_parser = RSSFeedParser()
    dedup_filter = DeduplicationFilter()
    relevance_filter = RelevanceFilter()
    site_builder = SiteBuilder()

    all_papers: list[DigestItem] = []
    all_articles: list[DigestItem] = []

    # Step 1: Look up author IDs if needed
    if not skip_author_lookup and not skip_semantic_scholar:
        authors = lookup_author_ids(ss_client)

        # Step 2: Discover co-authors if this is a fresh run
        if not skip_coauthors:
            authors = discover_coauthors(ss_client, authors)
    else:
        authors = load_author_ids()

    # Step 3: Fetch papers from Semantic Scholar
    if not skip_semantic_scholar:
        # Papers from tracked authors
        logger.info("Fetching papers from tracked authors...")
        author_papers = fetch_papers_from_authors(ss_client, authors, days_back=days_back)
        all_papers.extend(author_papers)

        # Papers from keyword searches
        logger.info("Searching papers by keywords...")
        current_year = datetime.utcnow().year
        keyword_papers = ss_client.search_by_keywords(
            limit_per_keyword=30,
            year_from=current_year - 1,
        )
        all_papers.extend(keyword_papers)

        # Papers from tracked venues
        logger.info("Searching papers by venues...")
        venue_papers = ss_client.search_by_venues(
            limit_per_venue=30,
            year_from=current_year - 1,
        )
        all_papers.extend(venue_papers)

    # Step 4: Fetch papers from PubMed
    if not skip_pubmed:
        logger.info("Fetching papers from PubMed...")

        # MeSH term search
        mesh_papers = pubmed_client.search_mesh_terms(days_back=days_back)
        all_papers.extend(mesh_papers)

        # Keyword search
        keyword_papers = pubmed_client.search_keywords(days_back=days_back)
        all_papers.extend(keyword_papers)

    # Step 5: Fetch articles from RSS feeds
    if not skip_rss:
        logger.info("Fetching articles from RSS feeds...")
        rss_articles = rss_parser.fetch_all_feeds()

        # Filter RSS articles by relevance
        relevant_articles = relevance_filter.filter_relevant(rss_articles)
        all_articles.extend(relevant_articles)

    # Step 6: Deduplicate
    logger.info("Deduplicating items...")

    # First deduplicate within the fetched items
    all_papers = dedup_filter.deduplicate_within_list(all_papers)
    all_articles = dedup_filter.deduplicate_within_list(all_articles)

    # Then filter out items we've seen in previous runs
    new_papers = dedup_filter.filter_new(all_papers)
    new_articles = dedup_filter.filter_new(all_articles)

    # Step 7: Clean up old seen items
    dedup_filter.cleanup_old()
    dedup_filter.save()

    # Step 8: Build the site
    logger.info("Building site...")
    site_builder.build(new_papers, new_articles)
    site_builder.save_items_json(new_papers, new_articles)

    # Summary
    logger.info("=" * 50)
    logger.info("Digest complete!")
    logger.info(f"  New papers: {len(new_papers)}")
    logger.info(f"  New articles: {len(new_articles)}")
    logger.info(f"  Total tracked authors: {len(authors)}")
    logger.info("=" * 50)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Contemplative Science Digest - Aggregates new publications"
    )
    parser.add_argument(
        "--skip-author-lookup",
        action="store_true",
        help="Skip looking up new author IDs",
    )
    parser.add_argument(
        "--skip-coauthors",
        action="store_true",
        help="Skip discovering co-authors",
    )
    parser.add_argument(
        "--skip-semantic-scholar",
        action="store_true",
        help="Skip Semantic Scholar queries",
    )
    parser.add_argument(
        "--skip-pubmed",
        action="store_true",
        help="Skip PubMed queries",
    )
    parser.add_argument(
        "--skip-rss",
        action="store_true",
        help="Skip RSS feed fetching",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for papers (default: 7)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    run_digest(
        skip_author_lookup=args.skip_author_lookup,
        skip_coauthors=args.skip_coauthors,
        skip_semantic_scholar=args.skip_semantic_scholar,
        skip_pubmed=args.skip_pubmed,
        skip_rss=args.skip_rss,
        days_back=args.days,
    )


if __name__ == "__main__":
    main()
