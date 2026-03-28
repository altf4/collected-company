"""Pydantic schemas for API requests/responses."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, HttpUrl


class StoreResult(BaseModel):
    """Result from a single store scraper."""

    store_id: int
    store_name: str
    store_url: str
    price: Optional[Decimal] = None
    stock_quantity: int = -1
    condition: str = "NM"
    foil: bool = False
    set_name: Optional[str] = None
    location: Optional[str] = None
    product_url: Optional[str] = None
    product_image_url: Optional[str] = None
    scraped_at: datetime
    error: Optional[str] = None

    @classmethod
    def error_result(cls, store, error_message: str) -> "StoreResult":
        """Create an error result for a failed scrape."""
        return cls(
            store_id=store.id,
            store_name=store.name,
            store_url=store.url,
            price=None,
            stock_quantity=0,
            condition="",
            foil=False,
            product_url=None,
            scraped_at=datetime.utcnow(),
            error=error_message,
        )

    class Config:
        from_attributes = True


class CardMetadata(BaseModel):
    """Card metadata from Scryfall."""

    card_name: str
    card_image_url: Optional[str] = None
    scryfall_url: Optional[str] = None
    scryfall_id: Optional[str] = None


class CardSearchResponse(BaseModel):
    """Response for non-streaming search endpoint."""

    card_name: str
    card_image_url: Optional[str] = None
    scryfall_url: Optional[str] = None
    results: list[StoreResult]
    search_duration_ms: int
    cache_hit_rate: float = 0.0
    from_cache: bool = False


class StoreSchema(BaseModel):
    """Store schema for API responses."""

    id: int
    name: str
    url: str
    scraper_type: str
    is_active: bool

    class Config:
        from_attributes = True


class HealthStatus(BaseModel):
    """Health check response."""

    status: str
    database: str
    scrapers_available: int
    active_stores: int
