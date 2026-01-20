"""Static site generator for the digest."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from ..config import (
    TEMPLATES_DIR,
    STATIC_DIR,
    DOCS_DIR,
    SITE_TITLE,
    SITE_DESCRIPTION,
    ITEMS_PER_PAGE,
)
from ..models.items import DigestItem, ItemType

logger = logging.getLogger(__name__)


class SiteBuilder:
    """Builder for generating the static digest site."""

    def __init__(
        self,
        templates_dir: Path = TEMPLATES_DIR,
        static_dir: Path = STATIC_DIR,
        output_dir: Path = DOCS_DIR,
    ):
        self.templates_dir = templates_dir
        self.static_dir = static_dir
        self.output_dir = output_dir
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True,
        )
        # Add custom filters
        self.env.filters["format_date"] = self._format_date
        self.env.filters["format_authors"] = self._format_authors
        self.env.filters["truncate_abstract"] = self._truncate_abstract

    def _format_date(self, dt: Optional[datetime]) -> str:
        """Format a datetime for display."""
        if dt is None:
            return "Unknown date"
        return dt.strftime("%B %d, %Y")

    def _format_authors(self, authors: list) -> str:
        """Format author list for display."""
        if not authors:
            return "Unknown authors"
        names = [a.name if hasattr(a, 'name') else str(a) for a in authors]
        if len(names) == 1:
            return names[0]
        elif len(names) == 2:
            return f"{names[0]} and {names[1]}"
        elif len(names) <= 5:
            return ", ".join(names[:-1]) + f", and {names[-1]}"
        else:
            return ", ".join(names[:3]) + f", et al. ({len(names)} authors)"

    def _truncate_abstract(self, text: Optional[str], length: int = 300) -> str:
        """Truncate abstract to specified length."""
        if not text:
            return ""
        if len(text) <= length:
            return text
        return text[:length].rsplit(" ", 1)[0] + "..."

    def build(
        self,
        papers: list[DigestItem],
        articles: list[DigestItem],
        archive_data: Optional[dict] = None,
    ):
        """Build the complete static site."""
        logger.info("Building static site...")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy static files
        self._copy_static_files()

        # Generate index page
        self._generate_index(papers, articles)

        # Generate archive page
        if archive_data:
            self._generate_archive(archive_data)

        # Generate CNAME if needed (for custom domain)
        # self._generate_cname()

        logger.info(f"Site built successfully in {self.output_dir}")

    def _copy_static_files(self):
        """Copy static CSS/JS files to output directory."""
        static_output = self.output_dir / "static"
        if static_output.exists():
            shutil.rmtree(static_output)
        if self.static_dir.exists():
            shutil.copytree(self.static_dir, static_output)
            logger.info("Copied static files")

    def _generate_index(self, papers: list[DigestItem], articles: list[DigestItem]):
        """Generate the main index page."""
        template = self.env.get_template("index.html")

        # Sort by date (newest first)
        papers = sorted(
            papers,
            key=lambda x: x.date_published or x.date_fetched,
            reverse=True,
        )[:ITEMS_PER_PAGE]

        articles = sorted(
            articles,
            key=lambda x: x.date_published or x.date_fetched,
            reverse=True,
        )[:ITEMS_PER_PAGE]

        # Convert items to dicts for template
        papers_data = [self._item_to_template_dict(p) for p in papers]
        articles_data = [self._item_to_template_dict(a) for a in articles]

        html = template.render(
            site_title=SITE_TITLE,
            site_description=SITE_DESCRIPTION,
            papers=papers_data,
            articles=articles_data,
            generated_at=datetime.utcnow(),
            total_papers=len(papers),
            total_articles=len(articles),
        )

        output_file = self.output_dir / "index.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"Generated {output_file}")

    def _generate_archive(self, archive_data: dict):
        """Generate the archive page."""
        template = self.env.get_template("archive.html")

        html = template.render(
            site_title=SITE_TITLE,
            archive_data=archive_data,
            generated_at=datetime.utcnow(),
        )

        output_file = self.output_dir / "archive.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"Generated {output_file}")

    def _item_to_template_dict(self, item: DigestItem) -> dict:
        """Convert a DigestItem to a dictionary for templates."""
        return {
            "title": item.title,
            "url": item.url,
            "item_type": item.item_type.value,
            "source_type": item.source_type.value,
            "date_published": item.date_published,
            "date_fetched": item.date_fetched,
            "doi": item.doi,
            "authors": item.authors,
            "abstract": item.abstract,
            "journal": item.journal,
            "year": item.year,
            "source_name": item.source_name,
            "excerpt": item.excerpt,
            "relevance_score": item.relevance_score,
            "matched_keywords": item.matched_keywords,
        }

    def save_items_json(self, papers: list[DigestItem], articles: list[DigestItem]):
        """Save items as JSON for potential API use."""
        data = {
            "generated_at": datetime.utcnow().isoformat(),
            "papers": [p.to_dict() for p in papers],
            "articles": [a.to_dict() for a in articles],
        }

        output_file = self.output_dir / "items.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved items JSON to {output_file}")
