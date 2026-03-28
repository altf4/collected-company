"""Scraper service for coordinating store scraping operations."""

import asyncio
from typing import List, AsyncGenerator, Tuple
import structlog

from ..models.store import Store
from ..models.schemas import StoreResult
from ..scrapers import get_scraper

logger = structlog.get_logger()


class ScraperService:
    """Service for coordinating store scraping operations."""

    async def scrape_all_stores_batch(
        self, card_name: str, stores: List[Store]
    ) -> List[StoreResult]:
        """
        Scrape all stores and wait for all results (non-streaming).
        Used for cached results or non-SSE endpoints.

        Args:
            card_name: The card name to search for
            stores: List of Store objects to scrape

        Returns:
            List of all StoreResult objects
        """
        scrapers = [get_scraper(store) for store in stores]

        try:
            tasks = [scraper.search(card_name) for scraper in scrapers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_results = []
            for store, result in zip(stores, results):
                if isinstance(result, Exception):
                    logger.error(
                        "scraper failed", store=store.name, error=str(result)
                    )
                    all_results.append(
                        StoreResult.error_result(store, str(result))
                    )
                else:
                    all_results.extend(result)

            return all_results

        finally:
            # Cleanup all scrapers
            await asyncio.gather(
                *[s.cleanup() for s in scrapers], return_exceptions=True
            )

    async def scrape_all_stores_stream(
        self, card_name: str, stores: List[Store]
    ) -> AsyncGenerator[Tuple[str, Store, List[StoreResult]], None]:
        """
        Scrape all stores concurrently, yielding results as they complete.

        Args:
            card_name: The card name to search for
            stores: List of Store objects to scrape

        Yields:
            Tuple of (event_type, store, data) where:
            - event_type: "results" or "error"
            - store: The Store object
            - data: List[StoreResult] or error string
        """
        # Create queue for inter-task communication
        result_queue = asyncio.Queue()
        scrapers = []

        async def scrape_and_queue(store: Store):
            """Scrape a single store and put result in queue."""
            scraper = get_scraper(store)
            scrapers.append(scraper)

            try:
                logger.info("starting scrape", store=store.name, card=card_name)
                results = await scraper.search(card_name)
                await result_queue.put(("results", store, results))
                logger.info(
                    "scrape complete", store=store.name, results=len(results)
                )
            except Exception as e:
                logger.error("scraper failed", store=store.name, error=str(e))
                await result_queue.put(("error", store, str(e)))

        # Launch all scraping tasks
        tasks = [
            asyncio.create_task(scrape_and_queue(store)) for store in stores
        ]

        # Create a task that signals completion
        async def signal_completion():
            await asyncio.gather(*tasks)
            await result_queue.put(("complete", None, None))

        completion_task = asyncio.create_task(signal_completion())

        # Yield results as they arrive
        stores_completed = 0
        while stores_completed < len(stores):
            event_type, store, data = await result_queue.get()

            if event_type == "complete":
                break

            yield (event_type, store, data)
            stores_completed += 1

        # Cleanup all scrapers
        await asyncio.gather(
            *[s.cleanup() for s in scrapers], return_exceptions=True
        )

        # Ensure completion task finishes
        await completion_task


# Global service instance
scraper_service = ScraperService()
