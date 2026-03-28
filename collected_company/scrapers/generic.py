"""Generic config-driven scraper for simple sites."""

from typing import List
from datetime import datetime

from .base import BaseScraper, ScraperException
from ..models.schemas import StoreResult


class GenericScraper(BaseScraper):
    """
    Config-driven scraper for simple sites.
    Uses CSS selectors from store.scraper_config.
    """

    SCRAPER_NAME = "generic"

    async def search(self, card_name: str) -> List[StoreResult]:
        """Search using configured selectors."""

        # Validate config
        required_keys = ["search_url", "selectors"]
        for key in required_keys:
            if key not in self.config:
                raise ScraperException(
                    f"Missing required config key: {key}. "
                    f"Generic scraper requires: {required_keys}"
                )

        selectors = self.config["selectors"]
        required_selectors = ["product_card", "price"]
        for selector in required_selectors:
            if selector not in selectors:
                raise ScraperException(
                    f"Missing required selector: {selector}. "
                    f"Required selectors: {required_selectors}"
                )

        # Build search URL
        search_url = self.config["search_url"]
        search_param = self.config.get("search_param", "q")

        # Fetch results
        try:
            html = await self._fetch(search_url, {search_param: card_name})
        except Exception as e:
            raise ScraperException(f"Failed to fetch search results: {e}")

        soup = self._parse_html(html)

        results = []

        # Parse product cards
        product_cards = soup.select(selectors["product_card"])

        if not product_cards:
            self.log.info("no products found", card_name=card_name)
            return []

        for item in product_cards:
            try:
                # Extract price (required)
                price_elem = item.select_one(selectors["price"])
                if not price_elem:
                    self.log.warning("no price element found, skipping item")
                    continue

                price = self._parse_price(price_elem.text)

                # Extract stock (optional)
                stock = -1
                if "stock" in selectors:
                    stock_elem = item.select_one(selectors["stock"])
                    if stock_elem:
                        stock = self._parse_stock(stock_elem.text)

                # Extract condition (optional)
                condition = "NM"
                if "condition" in selectors:
                    cond_elem = item.select_one(selectors["condition"])
                    if cond_elem:
                        condition = self._normalize_condition(cond_elem.text)

                # Extract product link (optional)
                product_url = None
                if "link" in selectors:
                    link_elem = item.select_one(selectors["link"])
                    if link_elem and link_elem.get("href"):
                        product_url = link_elem["href"]
                        # Make absolute URL if relative
                        if product_url and not product_url.startswith("http"):
                            product_url = self.store.url.rstrip("/") + "/" + product_url.lstrip("/")

                # Detect foil in text
                item_text = item.get_text().lower()
                foil = "foil" in item_text

                result = StoreResult(
                    store_id=self.store.id,
                    store_name=self.store.name,
                    store_url=self.store.url,
                    price=price,
                    stock_quantity=stock,
                    condition=condition,
                    foil=foil,
                    product_url=product_url,
                    scraped_at=datetime.utcnow(),
                )
                results.append(result)

            except Exception as e:
                self.log.warning("failed to parse product card", error=str(e))
                continue

        self.log.info("scraping complete", card_name=card_name, results=len(results))
        return results
