"""Card search routes."""

import json
import time
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from ...core.database import get_db
from ...models.store import Store
from ...models.schemas import CardSearchResponse, CardMetadata
from ...services.scraper_service import scraper_service
from ...services.scryfall_service import scryfall_service

router = APIRouter(prefix="/api/cards", tags=["cards"])
logger = structlog.get_logger()


@router.get("/search/stream")
async def search_cards_stream(
    q: str = Query(..., description="Card name to search for"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream search results as they arrive from each store using Server-Sent Events.

    This endpoint initiates scraping of all active stores concurrently and streams
    results back to the client as each store completes.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        try:
            # Get active stores
            result = await db.execute(select(Store).where(Store.is_active == True))
            stores = list(result.scalars().all())

            if not stores:
                yield f"event: error\ndata: {json.dumps({'error': 'No active stores configured'})}\n\n"
                return

            # Get card metadata from Scryfall
            card_metadata = await scryfall_service.search_card(q)
            if not card_metadata:
                card_metadata = CardMetadata(card_name=q)

            # Send metadata event
            metadata = {
                "card_name": card_metadata.card_name,
                "card_image_url": card_metadata.card_image_url,
                "scryfall_url": card_metadata.scryfall_url,
                "total_stores": len(stores),
            }
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

            # Stream results as they arrive
            stores_completed = 0
            async for event_type, store, data in scraper_service.scrape_all_stores_stream(
                q, stores
            ):
                if event_type == "results":
                    # Stream each result
                    for result in data:
                        result_dict = {
                            "store_id": result.store_id,
                            "store_name": result.store_name,
                            "store_url": result.store_url,
                            "price": float(result.price) if result.price else None,
                            "stock_quantity": result.stock_quantity,
                            "condition": result.condition,
                            "foil": result.foil,
                            "set_name": result.set_name,
                            "location": result.location,
                            "product_url": result.product_url,
                            "scraped_at": result.scraped_at.isoformat(),
                        }
                        yield f"event: result\ndata: {json.dumps(result_dict)}\n\n"

                elif event_type == "error":
                    # Stream error
                    error_dict = {
                        "store_id": store.id,
                        "store_name": store.name,
                        "error": data,
                    }
                    yield f"event: error\ndata: {json.dumps(error_dict)}\n\n"

                stores_completed += 1

                # Send progress update
                progress = {"completed": stores_completed, "total": len(stores)}
                yield f"event: progress\ndata: {json.dumps(progress)}\n\n"

            # Send completion event
            yield f"event: complete\ndata: {json.dumps({'status': 'done'})}\n\n"

        except Exception as e:
            logger.error("streaming error", error=str(e))
            error_dict = {"error": f"Streaming failed: {str(e)}"}
            yield f"event: error\ndata: {json.dumps(error_dict)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@router.get("/search", response_model=CardSearchResponse)
async def search_cards_batch(
    q: str = Query(..., description="Card name to search for"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for a card across all stores (non-streaming fallback).

    This endpoint waits for all stores to complete before returning results.
    Use this for cache-only requests or clients without SSE support.
    """
    start_time = time.time()

    # Get active stores
    result = await db.execute(select(Store).where(Store.is_active == True))
    stores = list(result.scalars().all())

    if not stores:
        return CardSearchResponse(
            card_name=q,
            results=[],
            search_duration_ms=0,
            from_cache=False,
        )

    # Get card metadata
    card_metadata = await scryfall_service.search_card(q)
    if not card_metadata:
        card_metadata = CardMetadata(card_name=q)

    # Scrape all stores
    results = await scraper_service.scrape_all_stores_batch(q, stores)

    duration_ms = int((time.time() - start_time) * 1000)

    return CardSearchResponse(
        card_name=card_metadata.card_name,
        card_image_url=card_metadata.card_image_url,
        scryfall_url=card_metadata.scryfall_url,
        results=results,
        search_duration_ms=duration_ms,
        from_cache=False,
    )


@router.get("/autocomplete")
async def autocomplete_cards(
    q: str = Query(..., min_length=2, description="Partial card name"),
):
    """Get autocomplete suggestions from Scryfall."""
    suggestions = await scryfall_service.autocomplete(q)
    return {"suggestions": suggestions}
