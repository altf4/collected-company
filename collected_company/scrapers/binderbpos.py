"""BinderPOS platform scraper using the BinderPOS product search API."""

import json
from typing import List
from datetime import datetime
from decimal import Decimal

from .base import BaseScraper, ScraperException
from ..models.schemas import StoreResult


class BinderPOSScraper(BaseScraper):
    """
    Scraper for stores using the BinderPOS e-commerce platform.

    Uses the BinderPOS API (app.binderpos.com) to search for MTG singles,
    which returns structured JSON with variant-level pricing and stock data.
    """

    SCRAPER_NAME = "binderbpos"
    API_URL = "https://app.binderpos.com/external/shopify/products/forStore"

    async def search(self, card_name: str) -> List[StoreResult]:
        """Search BinderPOS store for card via the API."""

        # The API requires the Shopify domain (e.g. "ggazcards.myshopify.com").
        # Stores can configure this in scraper_config["shopify_domain"],
        # or we derive it from the store URL's Shopify setup.
        shopify_domain = self.config.get("shopify_domain", "")
        if not shopify_domain:
            raise ScraperException(
                "BinderPOS scraper requires 'shopify_domain' in scraper_config "
                "(e.g. 'ggazcards.myshopify.com')"
            )

        payload = {
            "storeUrl": shopify_domain,
            "game": "mtg",
            "title": card_name,
            "instockOnly": True,
            "page": 1,
            "perPage": 25,
        }

        try:
            await self._init_client()
            self.log.debug("querying binderpos api", payload=payload)
            response = await self.client.post(
                self.API_URL,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise ScraperException(f"BinderPOS API request failed: {e}")

        results = []
        products = data.get("products", [])
        location = self.config.get("location")

        for product in products:
            handle = product.get("handle", "")
            product_url = f"{self.store.url}/products/{handle}" if handle else None
            set_name = product.get("setName")
            product_image_url = product.get("img") or product.get("tcgImage")

            for variant in product.get("variants", []):
                quantity = variant.get("quantity", 0)
                if quantity <= 0:
                    continue

                condition_text = variant.get("title", "") or variant.get("option1", "")
                foil = "foil" in condition_text.lower()
                condition = self._normalize_condition(
                    condition_text.replace("Foil", "").strip()
                )

                price = None
                if variant.get("price") is not None:
                    try:
                        price = Decimal(str(variant["price"]))
                    except Exception:
                        pass

                results.append(StoreResult(
                    store_id=self.store.id,
                    store_name=self.store.name,
                    store_url=self.store.url,
                    price=price,
                    stock_quantity=quantity,
                    condition=condition,
                    foil=foil,
                    set_name=set_name,
                    location=location,
                    product_url=product_url,
                    product_image_url=product_image_url,
                    scraped_at=datetime.utcnow(),
                ))

        self.log.info(
            "binderbpos scraping complete",
            card_name=card_name,
            products=len(products),
            results=len(results),
        )
        return results
