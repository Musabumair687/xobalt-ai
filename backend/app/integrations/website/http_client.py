"""HTTP-based website fetcher.

Uses httpx (already in requirements.txt) for async HTTP requests.
Handles timeouts, redirects, status codes, and user-agent headers.
"""
from __future__ import annotations

import logging

import httpx

from app.integrations.website.base import WebsiteFetcher

logger = logging.getLogger(__name__)

# Reasonable defaults
_DEFAULT_TIMEOUT = 15.0  # seconds
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; XobaltBot/1.0; +https://xobalt.ai)"
)
_MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB — skip giant pages


class HttpFetcher(WebsiteFetcher):
    """Fetch website pages over plain HTTP using httpx."""

    def __init__(
        self,
        timeout: float = _DEFAULT_TIMEOUT,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent

    @property
    def name(self) -> str:
        return "http_fetcher"

    async def is_available(self) -> bool:
        return True  # always available (no API key needed)

    async def fetch(self, url: str) -> tuple[int, str]:
        """GET *url* and return (status_code, html_body).

        Follows redirects (up to 5). Skips responses larger than 5 MB.
        Returns (status_code, '') for non-text responses.
        """
        headers = {"User-Agent": self._user_agent}
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = await client.get(url, headers=headers)

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                logger.debug("Skipping non-text response for %s (%s)", url, content_type)
                return response.status_code, ""

            content_length = int(response.headers.get("content-length", 0))
            if content_length > _MAX_CONTENT_LENGTH:
                logger.warning("Skipping oversized page %s (%d bytes)", url, content_length)
                return response.status_code, ""

            return response.status_code, response.text
