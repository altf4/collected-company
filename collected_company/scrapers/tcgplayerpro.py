"""TCGPlayer Pro storefront scraper."""

from typing import List
from datetime import datetime
from decimal import Decimal

from .base import BaseScraper, ScraperException
from ..models.schemas import StoreResult


class TCGPlayerProScraper(BaseScraper):
    """
    Scraper for stores using TCGPlayer Pro storefronts.

    Uses the storefront's proxied API:
      1. POST /api/catalog/search - search products
      2. GET /api/inventory/skus?productIds=... - get per-SKU pricing/stock

    Config:
      {"storefront_url": "https://playordraw.tcgplayerpro.com", "location": "Avondale"}
    """

    SCRAPER_NAME = "tcgplayerpro"

    def _get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(self, card_name: str) -> List[StoreResult]:
        """Search TCGPlayer Pro storefront for card."""

        storefront_url = self.config.get("storefront_url", "")
        if not storefront_url:
            raise ScraperException(
                "TCGPlayer Pro scraper requires 'storefront_url' in scraper_config"
            )

        location = self.config.get("location")
        await self._init_client()

        # Step 1: Search for products
        search_url = f"{storefront_url.rstrip('/')}/api/catalog/search"
        payload = {
            "query": card_name,
            "context": {"productLineName": "Magic: The Gathering"},
            "filters": {"productTypeName": ["Cards"]},
            "from": 0,
            "size": 25,
            "sort": None,
        }

        try:
            self.log.debug("searching tcgplayer pro", url=search_url)
            response = await self.client.post(search_url, json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise ScraperException(f"TCGPlayer Pro search failed: {e}")

        products = data.get("products", {}).get("items", [])
        if not products:
            return []

        # Filter to exact card name matches
        # Product names can be "Lightning Bolt", "Lightning Bolt (Showcase)", etc.
        # The base card name is extracted by stripping parentheticals
        import re
        matching_products = []
        for p in products:
            name = p.get("name", "")
            base_name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
            # Also handle prefix names like "Hadoken - Lightning Bolt"
            if base_name.lower() == card_name.lower():
                matching_products.append(p)

        if not matching_products:
            return []

        # Step 2: Get SKU data for matching products
        product_ids = ",".join(str(p["id"]) for p in matching_products)
        skus_url = f"{storefront_url.rstrip('/')}/api/inventory/skus"

        try:
            response = await self.client.get(
                skus_url, params={"productIds": product_ids}
            )
            response.raise_for_status()
            skus_data = response.json()
        except Exception as e:
            raise ScraperException(f"TCGPlayer Pro SKU fetch failed: {e}")

        # Build product lookup for set names
        product_map = {p["id"]: p for p in matching_products}

        results = []
        for product_skus in skus_data:
            product_id = product_skus.get("productId")
            product = product_map.get(product_id, {})
            set_name = product.get("setName")
            # URL pattern: /catalog/:productLineUrlName/:setUrlName/:productUrlName/:productId
            product_line_url = product.get("productLineUrlName", "")
            set_url = product.get("setUrlName", "")
            product_url_name = product.get("productUrlName", "")
            product_url = (
                f"{storefront_url.rstrip('/')}/catalog/{product_line_url}/{set_url}/{product_url_name}/{product_id}"
                if product_line_url and set_url and product_url_name
                else None
            )
            product_image_url = (
                f"https://tcgplayer-cdn.tcgplayer.com/product/{product_id}_200w.jpg"
                if product_id else None
            )

            for sku in product_skus.get("skus", []):
                quantity = sku.get("quantity", 0)
                if quantity <= 0:
                    continue

                condition = self._normalize_condition(
                    sku.get("conditionName", "")
                )
                foil = sku.get("isFoil", False)

                price = None
                if sku.get("price") is not None:
                    try:
                        price = Decimal(str(sku["price"]))
                    except Exception:
                        pass

                results.append(StoreResult(
                    store_id=self.store.id,
                    store_name=self.store.name,
                    store_url=storefront_url,
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
            "tcgplayer pro scraping complete",
            card_name=card_name,
            products=len(matching_products),
            results=len(results),
        )
        return results
