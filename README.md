# Contemplative Science Digest

A static website that aggregates new publications in contemplative science, updated daily via GitHub Actions and hosted on GitHub Pages.

## Features

- **Multi-source aggregation**: Fetches papers from Semantic Scholar, PubMed, and magazine articles from RSS feeds
- **Researcher tracking**: Monitors publications from key researchers in contemplative science
- **Co-author discovery**: Automatically discovers frequent collaborators of tracked researchers
- **Keyword filtering**: Filters RSS articles by relevance to contemplative science topics
- **Deduplication**: Tracks seen items to only show new content
- **Static site generation**: Generates a clean, responsive HTML site
- **Free hosting**: Uses GitHub Pages with GitHub Actions automation

## Tracked Sources

### Research Papers
- **Semantic Scholar**: Papers from tracked authors, keyword searches, and specific journals
- **PubMed**: MeSH term and keyword searches for meditation/mindfulness research

### Magazine Articles
- Aeon
- Nautilus
- The New Yorker
- The Atlantic
- Scientific American

## Setup

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/contemplative-science-digest.git
   cd contemplative-science-digest
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the digest:
   ```bash
   python -m src.main
   ```

4. View the generated site in `docs/index.html`

### GitHub Pages Deployment

1. Push the repository to GitHub

2. Enable GitHub Pages:
   - Go to Settings > Pages
   - Source: Deploy from a branch
   - Branch: `main` / `docs`

3. The GitHub Action will run daily at 7am EST and update the site automatically

## Configuration

Edit `src/config.py` to customize:

- **TIER1_RESEARCHERS**: List of researchers to track
- **TRACKED_VENUES**: Academic journals to monitor
- **ALL_KEYWORDS**: Keywords for paper searches
- **RSS_FEEDS**: Magazine RSS feed URLs
- **RSS_FILTER_KEYWORDS**: Keywords for filtering magazine articles
- **RSS_KEYWORD_THRESHOLD**: Minimum keyword matches for article inclusion

## Project Structure

```
contemplative-science-digest/
├── .github/workflows/
│   └── daily-digest.yml      # GitHub Actions workflow
├── src/
│   ├── main.py               # Entry point
│   ├── config.py             # Configuration
│   ├── sources/
│   │   ├── semantic_scholar.py
│   │   ├── pubmed.py
│   │   └── rss_feeds.py
│   ├── filters/
│   │   ├── relevance.py
│   │   └── deduplication.py
│   ├── site_generator/
│   │   └── builder.py
│   └── models/
│       └── items.py
├── templates/                 # Jinja2 templates
├── static/css/               # CSS styles
├── data/                     # Persistent data
├── docs/                     # Generated site (GitHub Pages)
└── requirements.txt
```

## Command Line Options

```bash
python -m src.main [OPTIONS]

Options:
  --skip-author-lookup    Skip looking up new author IDs
  --skip-coauthors        Skip discovering co-authors
  --skip-semantic-scholar Skip Semantic Scholar queries
  --skip-pubmed           Skip PubMed queries
  --skip-rss              Skip RSS feed fetching
  -v, --verbose           Enable verbose logging
```

## License

MIT License
