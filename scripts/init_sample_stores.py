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


if __name__ == "__main__":
    print("Initializing database with stores...\n")
    asyncio.run(create_stores())
    print("\nDone! Start the application with:")
    print("  uvicorn collected_company.main:app --reload")
