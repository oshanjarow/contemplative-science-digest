"""PubMed E-utilities API client for fetching papers."""

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import requests

from ..config import (
    PUBMED_BASE_URL,
    PUBMED_MESH_TERMS,
    PUBMED_SEARCH_DAYS,
    ALL_KEYWORDS,
)
from ..models.items import DigestItem, Author, ItemType, SourceType

logger = logging.getLogger(__name__)


class PubMedClient:
    """Client for the PubMed E-utilities API."""

    def __init__(self, rate_limit_delay: float = 0.34):
        """Initialize the client.

        Default rate limit is 3 requests per second (0.34s delay).
        """
        self.base_url = PUBMED_BASE_URL
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0

    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: dict) -> Optional[str]:
        """Make a rate-limited request to the API."""
        self._rate_limit()
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def search(self, query: str, max_results: int = 100, days_back: Optional[int] = None) -> list[str]:
        """Search PubMed and return PMIDs."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "pub_date",
        }

        if days_back:
            # Use relative date filter
            params["datetype"] = "pdat"
            params["reldate"] = days_back

        data = self._make_request("esearch.fcgi", params)
        if not data:
            return []

        try:
            import json
            result = json.loads(data)
            pmids = result.get("esearchresult", {}).get("idlist", [])
            logger.info(f"Found {len(pmids)} PMIDs for query: {query}")
            return pmids
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse search results: {e}")
            return []

    def fetch_details(self, pmids: list[str]) -> list[DigestItem]:
        """Fetch detailed information for PMIDs."""
        if not pmids:
            return []

        # Fetch in batches of 200
        items = []
        for i in range(0, len(pmids), 200):
            batch = pmids[i:i + 200]
            items.extend(self._fetch_batch(batch))

        return items

    def _fetch_batch(self, pmids: list[str]) -> list[DigestItem]:
        """Fetch a batch of articles."""
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }

        data = self._make_request("efetch.fcgi", params)
        if not data:
            return []

        return self._parse_xml(data)

    def _parse_xml(self, xml_data: str) -> list[DigestItem]:
        """Parse PubMed XML response."""
        items = []
        try:
            root = ET.fromstring(xml_data)
            for article in root.findall(".//PubmedArticle"):
                item = self._article_to_item(article)
                if item:
                    items.append(item)
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")

        return items

    def _article_to_item(self, article: ET.Element) -> Optional[DigestItem]:
        """Convert a PubMed article XML element to a DigestItem."""
        medline = article.find(".//MedlineCitation")
        if medline is None:
            return None

        # Get PMID
        pmid_elem = medline.find(".//PMID")
        if pmid_elem is None:
            return None
        pmid = pmid_elem.text

        # Get article data
        article_elem = medline.find(".//Article")
        if article_elem is None:
            return None

        # Title
        title_elem = article_elem.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else None
        if not title:
            return None

        # Abstract
        abstract_parts = []
        abstract_elem = article_elem.find(".//Abstract")
        if abstract_elem is not None:
            for text in abstract_elem.findall(".//AbstractText"):
                if text.text:
                    label = text.get("Label", "")
                    if label:
                        abstract_parts.append(f"{label}: {text.text}")
                    else:
                        abstract_parts.append(text.text)
        abstract = " ".join(abstract_parts) if abstract_parts else None

        # Authors
        authors = []
        author_list = article_elem.find(".//AuthorList")
        if author_list is not None:
            for author in author_list.findall(".//Author"):
                last_name = author.find("LastName")
                first_name = author.find("ForeName")
                if last_name is not None:
                    name_parts = []
                    if first_name is not None and first_name.text:
                        name_parts.append(first_name.text)
                    name_parts.append(last_name.text)
                    authors.append(Author(name=" ".join(name_parts)))

        # Journal
        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else None

        # Publication date
        date_published = None
        pub_date = article_elem.find(".//Journal/JournalIssue/PubDate")
        if pub_date is not None:
            year = pub_date.find("Year")
            month = pub_date.find("Month")
            day = pub_date.find("Day")

            if year is not None:
                try:
                    year_val = int(year.text)
                    month_val = 1
                    day_val = 1

                    if month is not None:
                        month_text = month.text
                        # Handle month names
                        month_map = {
                            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
                            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
                            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                        }
                        if month_text.isdigit():
                            month_val = int(month_text)
                        else:
                            month_val = month_map.get(month_text[:3], 1)

                    if day is not None and day.text.isdigit():
                        day_val = int(day.text)

                    date_published = datetime(year_val, month_val, day_val)
                except (ValueError, AttributeError):
                    pass

        # DOI
        doi = None
        article_ids = article.find(".//PubmedData/ArticleIdList")
        if article_ids is not None:
            for aid in article_ids.findall("ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text
                    break

        # Year
        year = None
        if date_published:
            year = date_published.year

        return DigestItem(
            title=title,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            item_type=ItemType.PAPER,
            source_type=SourceType.PUBMED,
            date_published=date_published,
            doi=doi,
            authors=authors,
            abstract=abstract,
            journal=journal,
            year=year,
        )

    def search_mesh_terms(self, days_back: int = PUBMED_SEARCH_DAYS) -> list[DigestItem]:
        """Search using configured MeSH terms."""
        all_pmids = set()

        for mesh_term in PUBMED_MESH_TERMS:
            pmids = self.search(mesh_term, max_results=200, days_back=days_back)
            all_pmids.update(pmids)

        logger.info(f"Total unique PMIDs from MeSH search: {len(all_pmids)}")
        return self.fetch_details(list(all_pmids))

    def search_keywords(self, days_back: int = PUBMED_SEARCH_DAYS) -> list[DigestItem]:
        """Search using configured keywords."""
        all_pmids = set()

        for keyword in ALL_KEYWORDS:
            # Add [Title/Abstract] qualifier for more precise matching
            query = f"{keyword}[Title/Abstract]"
            pmids = self.search(query, max_results=100, days_back=days_back)
            all_pmids.update(pmids)

        logger.info(f"Total unique PMIDs from keyword search: {len(all_pmids)}")
        return self.fetch_details(list(all_pmids))
