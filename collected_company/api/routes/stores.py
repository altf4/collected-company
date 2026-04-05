"""Store management routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.database import get_db
from ...models.store import Store
from ...models.schemas import StoreSchema

router = APIRouter(prefix="/api/stores", tags=["stores"])


@router.get("", response_model=list[StoreSchema])
async def list_stores(db: AsyncSession = Depends(get_db)):
    """List all configured stores."""
    result = await db.execute(select(Store))
    stores = result.scalars().all()
    return stores


@router.get("/locations")
async def list_store_locations(db: AsyncSession = Depends(get_db)):
    """List all active stores with their locations."""
    result = await db.execute(select(Store).where(Store.is_active == True))
    stores = result.scalars().all()
    out = []
    for store in stores:
        config = store.scraper_config or {}
        locations = config.get("locations", [])
        out.append({
            "id": store.id,
            "name": store.name,
            "locations": locations,
        })
    return out
