"""BinderPOS platform scraper using the BinderPOS product search API."""

import asyncio
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

    Supports both single-domain and multi-domain (multi-location) configs:
      Single:  {"shopify_domain": "store.myshopify.com", "location": "Mesa"}
      Multi:   {"shopify_domains": [
                   {"domain": "store-a.myshopify.com", "location": "Tempe", "url": "https://store-a.com"},
                   {"domain": "store-b.myshopify.com", "location": "Gilbert", "url": "https://store-b.com"}
                ]}
    """

    SCRAPER_NAME = "binderbpos"
    API_URL = "https://app.binderpos.com/external/shopify/products/forStore"

    async def search(self, card_name: str) -> List[StoreResult]:
        """Search BinderPOS store(s) for card via the API."""

        # Build list of domains to query
        domains = self._get_domains()
        if not domains:
            raise ScraperException(
                "BinderPOS scraper requires 'shopify_domain' or 'shopify_domains' "
                "in scraper_config"
            )

        await self._init_client()

        # Query all domains concurrently
        tasks = [
            self._search_domain(card_name, d["domain"], d["location"], d["url"])
            for d in domains
        ]
        domain_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, result in enumerate(domain_results):
            if isinstance(result, Exception):
                self.log.error(
                    "domain search failed",
                    domain=domains[i]["domain"],
                    error=str(result),
                )
                continue
            results.extend(result)

        self.log.info(
            "binderbpos scraping complete",
            card_name=card_name,
            domains=len(domains),
            results=len(results),
        )
        return results

    def _get_domains(self) -> List[dict]:
        """Get list of {domain, location, url} from config."""
        # Multi-domain config
        if "shopify_domains" in self.config:
            return self.config["shopify_domains"]

        # Single-domain config (backwards compatible)
        domain = self.config.get("shopify_domain", "")
        if not domain:
            return []
        return [{
            "domain": domain,
            "location": self.config.get("location"),
            "url": self.store.url,
        }]

    async def _search_domain(
        self, card_name: str, domain: str, location: str, store_url: str
    ) -> List[StoreResult]:
        """Search a single BinderPOS domain."""

        payload = {
            "storeUrl": domain,
            "game": "mtg",
            "title": card_name,
            "instockOnly": True,
            "page": 1,
            "perPage": 25,
        }

        try:
            self.log.debug("querying binderpos api", domain=domain)
            response = await self.client.post(self.API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise ScraperException(f"BinderPOS API request failed for {domain}: {e}")

        results = []
        for product in data.get("products", []):
            # Exact card name match only
            product_card_name = product.get("cardName", "")
            if product_card_name.lower() != card_name.lower():
                continue

            handle = product.get("handle", "")
            product_url = f"{store_url.rstrip('/')}/products/{handle}" if handle else None
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
                    store_url=store_url,
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

        return results
