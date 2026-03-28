"""Price cache model."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from ..core.database import Base


class PriceCache(Base):
    """Price cache model for storing scraped results."""

    __tablename__ = "price_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id"), nullable=False, index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=-1)
    condition: Mapped[str] = mapped_column(String(10), default="NM")
    foil: Mapped[bool] = mapped_column(Boolean, default=False)
    product_url: Mapped[str] = mapped_column(String(500), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_card_store_scraped", "card_id", "store_id", "scraped_at"),
    )

    def __repr__(self) -> str:
        return f"<PriceCache(card_id={self.card_id}, store_id={self.store_id}, price={self.price})>"
