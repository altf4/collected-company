"""Base scraper class with helper methods."""

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
import structlog

from ..models.schemas import StoreResult
from ..models.store import Store

logger = structlog.get_logger()


class ScraperException(Exception):
    """Exception raised when scraping fails."""

    pass


class BaseScraper(ABC):
    """Base scraper that all store scrapers inherit from."""

    # Override these in subclasses
    SCRAPER_NAME: str = "base"
    TIMEOUT: int = 15  # Per-request timeout in seconds

    def __init__(self, store: Store):
        self.store = store
        self.config = store.scraper_config or {}
        self.client: Optional[httpx.AsyncClient] = None
        self.log = logger.bind(scraper=self.SCRAPER_NAME, store=store.name)

    async def _init_client(self):
        """Initialize HTTP client lazily."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.TIMEOUT, headers=self._get_headers()
            )

    @abstractmethod
    async def search(self, card_name: str) -> List[StoreResult]:
        """
        Search for a card on this store's website.

        Args:
            card_name: The normalized card name to search for

        Returns:
            List of StoreResult objects (can be empty if no matches)

        Raises:
            ScraperException: If scraping fails
        """
        pass

    # Helper methods available to all scrapers

    async def _fetch(self, url: str, params: Optional[dict] = None) -> str:
        """
        Fetch HTML with retry logic and error handling.

        Args:
            url: URL to fetch
            params: Optional query parameters

        Returns:
            HTML content as string

        Raises:
            ScraperException: If fetching fails after retries
        """
        await self._init_client()

        for attempt in range(2):  # Max 2 attempts
            try:
                self.log.debug("fetching url", url=url, attempt=attempt + 1)
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                return response.text
            except httpx.TimeoutException:
                if attempt == 1:
                    raise ScraperException(f"Timeout fetching {url}")
                await asyncio.sleep(1)
            except httpx.HTTPError as e:
                self.log.error("http error", url=url, error=str(e))
                raise ScraperException(f"HTTP error: {e}")

    def _parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML into BeautifulSoup object.

        Args:
            html: HTML content as string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, "lxml")

    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """
        Normalize price strings to Decimal.
        Handles: "$1.99", "1,99 €", "USD 1.99", etc.

        Args:
            price_str: Price string to parse

        Returns:
            Decimal price or None if parsing fails
        """
        if not price_str:
            return None

        # Remove common currency symbols and text
        cleaned = re.sub(r"[^\d.,]", "", price_str)

        if not cleaned:
            return None

        # Handle European format (1,99 -> 1.99)
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        # Handle format with both (1,234.56)
        elif "," in cleaned and "." in cleaned:
            # Remove thousands separator
            cleaned = cleaned.replace(",", "")

        try:
            return Decimal(cleaned)
        except Exception as e:
            self.log.warning("failed to parse price", price_str=price_str, error=str(e))
            return None

    def _parse_stock(self, stock_str: str) -> int:
        """
        Parse stock quantity.

        Args:
            stock_str: Stock string to parse

        Returns:
            -1 if unknown, 0 if out of stock, N if in stock
        """
        if not stock_str:
            return -1

        stock_lower = stock_str.lower()

        # Check for out of stock indicators
        if any(x in stock_lower for x in ["out", "sold", "unavailable", "none"]):
            return 0

        # Try to extract number
        numbers = re.findall(r"\d+", stock_str)
        if numbers:
            return int(numbers[0])

        return -1

    def _normalize_condition(self, condition_str: str) -> str:
        """
        Normalize condition to standard abbreviations.

        Args:
            condition_str: Condition string to normalize

        Returns:
            Standard condition abbreviation (NM, LP, MP, HP, DMG)
        """
        if not condition_str:
            return "NM"

        c = condition_str.upper()

        # Map various formats to standard
        mappings = {
            "NEAR MINT": "NM",
            "MINT": "NM",
            "LIGHTLY PLAYED": "LP",
            "LIGHT PLAY": "LP",
            "SLIGHTLY PLAYED": "LP",
            "MODERATELY PLAYED": "MP",
            "MODERATE PLAY": "MP",
            "HEAVILY PLAYED": "HP",
            "HEAVY PLAY": "HP",
            "DAMAGED": "DMG",
            "POOR": "DMG",
        }

        for key, val in mappings.items():
            if key in c:
                return val

        # Return first 2-3 chars if already abbreviated
        if len(c) <= 3:
            return c
        return "NM"

    def _get_headers(self) -> dict:
        """
        Get HTTP headers for requests.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "User-Agent": "CollectedCompany/1.0 (MTG Price Aggregator; +https://github.com/collected-company)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def cleanup(self):
        """Clean up resources (called after scraping)."""
        if self.client:
            await self.client.aclose()
            self.client = None

    def __del__(self):
        """Ensure cleanup on deletion."""
        if self.client and not self.client.is_closed:
            # Note: This won't work in async context, but provides a fallback
            try:
                asyncio.get_event_loop().create_task(self.cleanup())
            except:
                pass
