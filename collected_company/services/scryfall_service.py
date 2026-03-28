"""Scryfall API integration."""

import httpx
from typing import Optional
import structlog

from ..core.config import settings
from ..models.schemas import CardMetadata

logger = structlog.get_logger()


class ScryfallService:
    """Service for interacting with Scryfall API."""

    def __init__(self):
        self.base_url = settings.scryfall_api_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def search_card(self, card_name: str) -> Optional[CardMetadata]:
        """
        Search for a card by name using Scryfall API.

        Args:
            card_name: The card name to search for

        Returns:
            CardMetadata or None if not found
        """
        try:
            # Use Scryfall's named endpoint for exact matches
            url = f"{self.base_url}/cards/named"
            params = {"fuzzy": card_name}

            logger.info("searching scryfall", card_name=card_name)
            response = await self.client.get(url, params=params)

            if response.status_code == 404:
                logger.warning("card not found on scryfall", card_name=card_name)
                return None

            response.raise_for_status()
            data = response.json()

            # Extract metadata
            card_metadata = CardMetadata(
                card_name=data.get("name", card_name),
                card_image_url=data.get("image_uris", {}).get("normal"),
                scryfall_url=data.get("scryfall_uri"),
                scryfall_id=data.get("id"),
            )

            logger.info("found card on scryfall", card_name=card_metadata.card_name)
            return card_metadata

        except httpx.HTTPError as e:
            logger.error("scryfall api error", error=str(e))
            # Return basic metadata even if Scryfall fails
            return CardMetadata(card_name=card_name)
        except Exception as e:
            logger.error("unexpected error searching scryfall", error=str(e))
            return CardMetadata(card_name=card_name)

    async def autocomplete(self, partial_name: str) -> list[str]:
        """
        Get autocomplete suggestions for a partial card name.

        Args:
            partial_name: Partial card name to autocomplete

        Returns:
            List of suggested card names
        """
        try:
            url = f"{self.base_url}/cards/autocomplete"
            params = {"q": partial_name}

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("data", [])

        except Exception as e:
            logger.error("scryfall autocomplete error", error=str(e))
            return []

    async def cleanup(self):
        """Clean up resources."""
        await self.client.aclose()


# Global service instance
scryfall_service = ScryfallService()
