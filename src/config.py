"""Configuration for the Contemplative Science Digest."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
DOCS_DIR = PROJECT_ROOT / "docs"

# Data files
SEEN_ITEMS_FILE = DATA_DIR / "seen_items.json"
AUTHOR_IDS_FILE = DATA_DIR / "author_ids.json"

# Semantic Scholar API
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_FIELDS = "title,authors,year,venue,abstract,externalIds,url,publicationDate"

# PubMed API
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_SEARCH_DAYS = 30  # Look back 30 days for papers

# Tier 1: Directly tracked researchers (name -> Semantic Scholar ID)
# IDs need to be looked up on first run
TIER1_RESEARCHERS = [
    "Ruben Laukkonen",
    "Shamil Chandaria",
    "Matthew Sacchet",
    "Mark Miller",
    "Jonas Mago",
    "Aviva Berkovich-Ohana",
    "Georg Northoff",
    "Richard Davidson",
    "Judson Brewer",
    "Willoughby Britton",
    "Evan Thompson",
    "Thomas Metzinger",
    "Heleen Slagter",
    "John Dunne",
    "David Vago",
]

# Minimum papers together to add as Tier 2 co-author
COAUTHOR_MIN_PAPERS = 3

# Tracked journals/venues
TRACKED_VENUES = [
    "Mindfulness",
    "Frontiers in Psychology",
    "Consciousness and Cognition",
    "NeuroImage",
    "Journal of Cognitive Enhancement",
    "PLOS ONE",
    "Frontiers in Human Neuroscience",
    "Scientific Reports",
    "Neuroscience of Consciousness",
    "Psychophysiology",
]

# Tracked institutions for affiliation search
TRACKED_INSTITUTIONS = [
    "Center for Healthy Minds",
    "Mind and Life Institute",
    "Contemplative Sciences Center",
    "Harvard Meditation Research Program",
]

# Keywords for search queries
PRIMARY_KEYWORDS = [
    "meditation",
    "mindfulness",
    "contemplative",
    "consciousness research",
    "awareness training",
    "nondual awareness",
    "non-dual awareness",
]

TECHNIQUE_KEYWORDS = [
    "MBSR",
    "MBCT",
    "vipassana",
    "shamatha",
    "loving-kindness meditation",
    "metta meditation",
    "focused attention meditation",
    "open monitoring",
    "body scan meditation",
    "breath awareness",
]

STATE_KEYWORDS = [
    "jhana",
    "samadhi",
    "meditative absorption",
    "cessation experience",
    "nirodha",
    "mystical experience",
    "ego dissolution",
    "flow state contemplative",
]

NEURAL_KEYWORDS = [
    "default mode network meditation",
    "interoception contemplative",
    "metacognition meditation",
    "neurophenomenology",
]

# All keywords combined for search
ALL_KEYWORDS = PRIMARY_KEYWORDS + TECHNIQUE_KEYWORDS + STATE_KEYWORDS + NEURAL_KEYWORDS

# PubMed MeSH terms
PUBMED_MESH_TERMS = [
    '"Meditation"[Mesh]',
    '"Mindfulness"[Mesh]',
]

# RSS feeds for magazine articles
RSS_FEEDS = {
    "Aeon": "https://aeon.co/feed.rss",
    "Nautilus": "https://nautil.us/feed",
    "The New Yorker": "https://www.newyorker.com/feed/everything",
    "The Atlantic": "https://www.theatlantic.com/feed/all/",
    "Scientific American": "https://rss.sciam.com/ScientificAmerican-Global",
}

# Keywords for filtering RSS articles (case-insensitive)
RSS_FILTER_KEYWORDS = [
    "meditation",
    "mindfulness",
    "contemplative",
    "consciousness",
    "awareness",
    "buddhist",
    "buddhism",
    "zen",
    "yoga",
    "introspection",
    "attention",
    "self-awareness",
    "neuroscience mind",
    "brain consciousness",
    "psychedelics",
    "mystical",
    "spiritual",
]

# Minimum keyword matches for RSS article to be included
RSS_KEYWORD_THRESHOLD = 1

# Rate limiting
SEMANTIC_SCHOLAR_RATE_LIMIT = 100  # requests per 5 minutes
PUBMED_RATE_LIMIT = 3  # requests per second without API key

# Site generation
SITE_TITLE = "Contemplative Science Digest"
SITE_DESCRIPTION = "Daily aggregation of new publications in contemplative science"
ITEMS_PER_PAGE = 50
ARCHIVE_DAYS = 90  # Keep archive for 90 days
