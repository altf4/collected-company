# Collected Company

> *"Look at the top six cards of your library. Put up to two creature cards with converted mana cost 3 or less from among them onto the battlefield."*

**Collected Company** is a Magic: the Gathering singles price aggregator that gathers the best prices from multiple local game stores into one simple view.

## Problem

Looking for Magic singles across a dozen local stores means visiting each website individually, searching for the same card over and over, and manually comparing prices. This takes 10-15 minutes per card.

## Solution

Search once, see all prices. Collected Company scrapes all your local stores concurrently and shows you everything in one sortable table - in under 5 seconds.

## Key Features

- **Real-Time Streaming**: Results appear as they arrive via Server-Sent Events (SSE)
  - First results in ~500ms instead of waiting 5+ seconds
  - Progressive loading with live progress bar
  - Graceful handling of slow or failed stores
- **Fast**: Concurrent async scraping of all stores
- **Simple**: Search for any Magic card, get instant price comparison
- **Modular**: Adding a new store takes 15 minutes (or just 2 minutes for common platforms)
- **Smart Caching**: 15-30 minute cache to avoid hammering stores
- **Local First**: Designed for local game stores, not big retailers
- **Progressive Enhancement**: Works without JavaScript (falls back to non-streaming mode)

## Architecture Highlights

### Real-Time Streaming Architecture

When you search for a card, the application:

1. **Immediately** returns card metadata (image, name, etc.)
2. **Concurrently** launches scrapers for all 12 stores
3. **Streams** each result to the browser as soon as it arrives
4. **Updates** the results table in real-time with smooth animations
5. **Shows** a progress bar tracking completion (8/12 stores done...)

**Result**: You see the cheapest options within 500ms-1s, while slower stores continue loading in the background.

```
Timeline:
0ms    → User searches for "Lightning Bolt"
50ms   → Card metadata displayed, 12 scrapers launched
500ms  → Store A results arrive and appear ✓
800ms  → Store B, E, F results arrive ✓
1.2s   → Store C, G results arrive ✓
...
5s     → All 12 stores complete or timeout
```

This is powered by **Server-Sent Events (SSE)** with an async queue-based orchestration system.

### Plugin-Based Scrapers

Adding a new store is as simple as possible:

```python
# collected_company/scrapers/custom/my_store.py
from ..base import BaseScraper

class MyStoreScraper(BaseScraper):
    SCRAPER_NAME = "my_store"

    async def search(self, card_name: str) -> List[StoreResult]:
        html = await self._fetch(f"{self.store.url}/search?q={card_name}")
        soup = self._parse_html(html)
        # ... extract and return results
```

**That's it!** The scraper auto-registers and is immediately available.

### Three-Tier Flexibility

1. **Platform Scrapers** (BinderPOS, Crystal Commerce): Just add store config, no code needed
2. **Generic Scraper**: Configure CSS selectors, no code needed
3. **Custom Scrapers**: 30-50 lines of Python for complex sites

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Database**: PostgreSQL (SQLite for dev)
- **Scraping**: httpx (async), BeautifulSoup4, Playwright (if needed)
- **Frontend**: Jinja2 templates + TailwindCSS (MVP), React (future)
- **Deployment**: Docker, Render/Railway/Fly.io

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/collected_company.git
cd collected_company
uv sync

# Configure database
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn collected_company.main:app --reload

# Visit http://localhost:8000
```

## Adding Your First Store

### Option 1: Platform-Based Store (2 minutes)

```sql
INSERT INTO stores (name, url, scraper_type, is_active)
VALUES ('Dragons Lair', 'https://dragonslair.com', 'binderbpos', true);
```

### Option 2: Config-Driven Store (15 minutes)

Inspect the site, create config:

```json
{
  "search_url": "https://mystore.com/search",
  "search_param": "q",
  "selectors": {
    "product_card": ".product-item",
    "price": ".price",
    "stock": ".stock",
    "condition": ".condition",
    "link": "a.product-link"
  }
}
```

Add to database with the config, done!

### Option 3: Custom Scraper (30-60 minutes)

Drop a Python file in `collected_company/scrapers/custom/`, implement the `search()` method, auto-registers!

## Project Structure

```
collected_company/
├── scrapers/              # All store scrapers (auto-discovered)
│   ├── base.py           # Base scraper with helpers
│   ├── binderbpos.py     # Platform scrapers
│   ├── generic.py        # Config-driven scraper
│   └── custom/           # Custom store scrapers
├── models/               # Database models
├── services/             # Business logic
├── api/                  # FastAPI routes
├── templates/            # Jinja2 templates
└── static/               # CSS, JS, images
```

## Documentation

- **[Design Document](DESIGN.md)**: Comprehensive architecture and design decisions
- **[API Documentation](http://localhost:8000/docs)**: Interactive OpenAPI docs (when running)
- **Adding Stores**: See [DESIGN.md Section 6](DESIGN.md#6-adding-a-new-store-step-by-step-guide)

## Development

```bash
# Run tests
uv run pytest

# Test a specific scraper
uv run python -m collected_company.cli test-scraper --store-id 1 --card "Lightning Bolt"

# List all registered scrapers
uv run python -m collected_company.cli list-scrapers

# Format code
uv run black collected_company/
uv run ruff check collected_company/
```

## Contributing

Contributions welcome! Especially:
- New platform scrapers (BinderPOS, Crystal Commerce, etc.)
- Scraper improvements and bug fixes
- UI/UX enhancements
- Documentation

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- [Scryfall](https://scryfall.com) for the amazing MTG card API
- Local game stores for keeping Magic alive
- The Python community for excellent libraries

---

*Built with FastAPI, BeautifulSoup, and a love for Magic: the Gathering*
