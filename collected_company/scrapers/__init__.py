"""Scraper auto-discovery and registry."""

import importlib
import pkgutil
from typing import Dict, Type, List
import structlog

from .base import BaseScraper

logger = structlog.get_logger()


class ScraperRegistry:
    """Auto-discover and register all scrapers."""

    def __init__(self):
        self._scrapers: Dict[str, Type[BaseScraper]] = {}
        self._discover_scrapers()

    def _discover_scrapers(self):
        """Automatically find all scraper classes."""
        import collected_company.scrapers as scrapers_module

        # Iterate through all modules in scrapers/
        for importer, modname, ispkg in pkgutil.walk_packages(
            scrapers_module.__path__, prefix="collected_company.scrapers."
        ):
            # Skip __pycache__ and non-scraper modules
            if "__pycache__" in modname or modname.endswith("base"):
                continue

            try:
                module = importlib.import_module(modname)

                # Find all BaseScraper subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseScraper)
                        and attr is not BaseScraper
                    ):
                        # Register by SCRAPER_NAME
                        name = getattr(attr, "SCRAPER_NAME", None)
                        if name and name != "base":
                            self._scrapers[name] = attr
                            logger.info(
                                "registered scraper",
                                name=name,
                                class_name=attr.__name__,
                            )
            except Exception as e:
                logger.error(
                    "failed to import scraper module", module=modname, error=str(e)
                )

    def get(self, scraper_type: str) -> Type[BaseScraper]:
        """
        Get scraper class by type.

        Args:
            scraper_type: The scraper type identifier

        Returns:
            Scraper class

        Raises:
            ValueError: If scraper type is unknown
        """
        if scraper_type not in self._scrapers:
            raise ValueError(
                f"Unknown scraper type: {scraper_type}. "
                f"Available: {', '.join(self.list_available())}"
            )
        return self._scrapers[scraper_type]

    def list_available(self) -> List[str]:
        """
        List all available scraper types.

        Returns:
            List of scraper type identifiers
        """
        return sorted(list(self._scrapers.keys()))

    def count(self) -> int:
        """
        Get count of registered scrapers.

        Returns:
            Number of registered scrapers
        """
        return len(self._scrapers)


# Global registry instance
registry = ScraperRegistry()


def get_scraper(store) -> BaseScraper:
    """
    Factory function to create scraper instance for a store.

    Args:
        store: Store model instance

    Returns:
        Initialized scraper instance

    Raises:
        ValueError: If store's scraper_type is unknown
    """
    scraper_class = registry.get(store.scraper_type)
    return scraper_class(store)


__all__ = ["BaseScraper", "ScraperRegistry", "registry", "get_scraper"]
