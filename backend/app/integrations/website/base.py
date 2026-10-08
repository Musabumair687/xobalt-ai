"""Base interface for website access providers.

Allows swapping HTTP-based fetching for headless-browser or cached
implementations without changing the workflow or services.
"""
from abc import ABC, abstractmethod


class WebsiteFetcher(ABC):
    """Abstract base class for fetching website content."""

    @abstractmethod
    async def fetch(self, url: str) -> tuple[int, str]:
        """Fetch a URL and return (status_code, html_content).

        Raises:
            httpx.HTTPError or similar on network failures.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if this fetcher is usable."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this fetcher."""
        ...
