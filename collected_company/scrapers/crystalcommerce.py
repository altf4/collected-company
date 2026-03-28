"""CrystalCommerce platform scraper for game stores."""

from typing import List
from datetime import datetime

from .base import BaseScraper, ScraperException
from ..models.schemas import StoreResult


class CrystalCommerceScraper(BaseScraper):
    """
    Scraper for stores using the CrystalCommerce e-commerce platform.

    CrystalCommerce stores have an advanced search page with structured
    product listings using li.product elements with variant rows.
    """

    SCRAPER_NAME = "crystalcommerce"

    async def search(self, card_name: str) -> List[StoreResult]:
        """Search CrystalCommerce store for card."""

        search_url = f"{self.store.url}/advanced_search"
        # category_ids_with_descendants[]=5643 filters to MTG singles
        mtg_category = self.config.get("mtg_category_id", "5643")
        params = {
            "utf8": "\u2713",
            "search[fuzzy_search]": card_name,
            "search[in_stock]": "0",
            "buylist_mode": "0",
            "search[category_ids_with_descendants][]": ["", mtg_category],
            "search[sort]": "name",
            "search[direction]": "ascend",
            "commit": "Search",
        }

        try:
            html = await self._fetch(search_url, params)
        except Exception as e:
            raise ScraperException(f"Failed to fetch CrystalCommerce results: {e}")

        soup = self._parse_html(html)
        results = []

        for item in soup.select("li.product"):
            try:
                # Check if in stock — skip out-of-stock products
                in_stock_row = item.select_one(".variant-row.in-stock")
                if not in_stock_row:
                    continue

                # Set name from category span
                category_elem = item.select_one("span.category")
                set_name = category_elem.get_text(strip=True) if category_elem else None

                # Product link
                link_elem = item.select_one('a[itemprop="url"]')
                product_url = None
                if link_elem and link_elem.get("href"):
                    href = link_elem["href"]
                    if href.startswith("http"):
                        product_url = href
                    else:
                        product_url = f"{self.store.url.rstrip('/')}{href}"

                # Extract data from the add-to-cart form (most reliable source)
                form = in_stock_row.select_one("form.add-to-cart-form")
                if form:
                    price = self._parse_price(form.get("data-price", ""))
                    variant_desc = form.get("data-variant", "")
                else:
                    # Fallback to price element
                    price_elem = in_stock_row.select_one(".regular.price")
                    price = self._parse_price(
                        price_elem.get_text(strip=True)
                    ) if price_elem else None
                    desc_elem = in_stock_row.select_one(".variant-description")
                    variant_desc = desc_elem.get_text(strip=True) if desc_elem else ""

                # Parse condition and location from variant description
                # Format: "Ungraded: Gilbert, English" or "Light Play: Tucson, English"
                condition = self._parse_cc_condition(variant_desc)
                location = self._parse_cc_location(variant_desc)

                # Parse stock quantity
                qty_elem = in_stock_row.select_one(".variant-qty")
                stock = self._parse_stock(
                    qty_elem.get_text(strip=True)
                ) if qty_elem else -1

                # Detect foil from product name
                name_elem = item.select_one("h4.name")
                name_text = name_elem.get_text(strip=True) if name_elem else ""
                foil = "foil" in name_text.lower()

                results.append(StoreResult(
                    store_id=self.store.id,
                    store_name=self.store.name,
                    store_url=self.store.url,
                    price=price,
                    stock_quantity=stock,
                    condition=condition,
                    foil=foil,
                    set_name=set_name,
                    location=location,
                    product_url=product_url,
                    scraped_at=datetime.utcnow(),
                ))

            except Exception as e:
                self.log.warning("failed to parse product", error=str(e))
                continue

        self.log.info(
            "crystalcommerce scraping complete",
            card_name=card_name,
            results=len(results),
        )
        return results

    def _parse_cc_condition(self, variant_desc: str) -> str:
        """Parse condition from CrystalCommerce variant description.

        Formats seen: "Ungraded: Gilbert, English", "Light Play: Tucson, English",
        "Near Mint: Tucson, English"
        """
        if not variant_desc:
            return "NM"

        # The condition is the part before the colon
        condition_part = variant_desc.split(":")[0].strip()

        cc_mappings = {
            "UNGRADED": "NM",
            "NEAR MINT": "NM",
            "LIGHT PLAY": "LP",
            "LIGHTLY PLAYED": "LP",
            "MODERATE PLAY": "MP",
            "MODERATELY PLAYED": "MP",
            "HEAVY PLAY": "HP",
            "HEAVILY PLAYED": "HP",
            "DAMAGED": "DMG",
        }

        upper = condition_part.upper()
        for key, val in cc_mappings.items():
            if key in upper:
                return val

        return "NM"

    def _parse_cc_location(self, variant_desc: str) -> str:
        """Parse location from CrystalCommerce variant description.

        Format: "Ungraded: Gilbert, English" -> "Gilbert"
        """
        if not variant_desc or ":" not in variant_desc:
            return None

        after_colon = variant_desc.split(":", 1)[1].strip()
        # Location is the part before the comma (language comes after)
        if "," in after_colon:
            return after_colon.split(",")[0].strip()
        return after_colon.strip() or None
