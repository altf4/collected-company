"""Initialize database with stores."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collected_company.core.database import AsyncSessionLocal, init_db
from collected_company.models.store import Store
from sqlalchemy import select


STORES = [
    {
        "name": "Gamers Guild",
        "url": "https://gamersguildazcards.com",
        "scraper_type": "binderbpos",
        "scraper_config": {
            "shopify_domain": "ggazcards.myshopify.com",
            "location": "All locations",
            "locations": ["All locations"],
        },
        "is_active": True,
    },
    {
        "name": "Amazing Discoveries",
        "url": "https://www.amazingmtg.com",
        "scraper_type": "crystalcommerce",
        "scraper_config": {
            "mtg_category_id": "5643",
            "locations": ["Casa Grande", "Chandler", "Gilbert", "Glendale", "Tucson"],
        },
        "is_active": True,
    },
    {
        "name": "Primetime Games",
        "url": "https://primetimemagic.com",
        "scraper_type": "binderbpos",
        "scraper_config": {
            "shopify_domains": [
                {"domain": "prime-time-cards-tempe.myshopify.com", "location": "Tempe", "url": "https://primetimetempe.com"},
                {"domain": "primetimemagicgilbert.myshopify.com", "location": "Gilbert", "url": "https://primetimegilbert.com"},
                {"domain": "primetimecg.myshopify.com", "location": "Warehouse", "url": "https://primetimemagic.com"},
            ],
            "locations": ["Gilbert", "Tempe", "Warehouse"],
        },
        "is_active": True,
    },
    {
        "name": "Play or Draw",
        "url": "https://playordraw.tcgplayerpro.com",
        "scraper_type": "tcgplayerpro",
        "scraper_config": {
            "storefront_url": "https://playordraw.tcgplayerpro.com",
            "location": "Avondale",
            "locations": ["Avondale"],
        },
        "is_active": True,
    },
    {
        "name": "Authority Games",
        "url": "https://authoritygames.crystalcommerce.com",
        "scraper_type": "crystalcommerce",
        "scraper_config": {
            "mtg_category_id": "8",
            "locations": ["Mesa"],
        },
        "is_active": True,
    },
    {
        "name": "Authoria Games",
        "url": "https://athoriagamestempe.crystalcommerce.com",
        "scraper_type": "crystalcommerce",
        "scraper_config": {
            "mtg_category_id": "8",
            "locations": ["Tempe"],
        },
        "is_active": True,
    },
    {
        "name": "Dream Realm Cards",
        "url": "https://www.dreamrealmcards.com",
        "scraper_type": "crystalcommerce",
        "scraper_config": {
            "mtg_category_id": "8",
            "locations": ["Online"],
        },
        "is_active": True,
    },
]


async def create_stores():
    """Create stores in the database (skips existing ones by name)."""

    await init_db()

    async with AsyncSessionLocal() as session:
        created = 0
        for store_data in STORES:
            # Skip if store already exists
            result = await session.execute(
                select(Store).where(Store.name == store_data["name"])
            )
            if result.scalar_one_or_none():
                print(f"  - {store_data['name']} (already exists, skipping)")
                continue

            store = Store(**store_data)
            session.add(store)
            created += 1
            print(f"  - {store_data['name']} ({store_data['scraper_type']})")

        await session.commit()
        print(f"\nCreated {created} store(s)")

    # Dispose engine so asyncio.run() can exit cleanly
    from collected_company.core.database import engine
    await engine.dispose()


if __name__ == "__main__":
    print("Initializing database with stores...\n")
    asyncio.run(create_stores())
    print("\nDone! Start the application with:")
    print("  uvicorn collected_company.main:app --reload")
