"""HTML-to-clean-text parser.

Converts raw HTML into clean, readable text suitable for LLM consumption.
Strips scripts, styles, navigation noise, tracking pixels, and other
non-content elements. Preserves headings and paragraph structure.

Uses beautifulsoup4 for robust HTML parsing.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup, Tag
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False
    logger.warning("beautifulsoup4 not installed — HTML parsing will be limited.")

# Tags whose entire subtree we remove (they never contain useful content)
_REMOVE_TAGS = {
    "script", "style", "noscript", "iframe", "svg", "canvas",
    "head", "header", "footer", "nav", "aside",
    "form", "button", "input", "select", "textarea",
}

# Max text length we pass to the LLM (roughly 12k tokens)
_MAX_TEXT_LENGTH = 50_000


def parse_html(html: str) -> str:
    """Convert raw HTML to clean, readable text.

    Args:
        html: Raw HTML string from a website fetch.

    Returns:
        Clean text with headings preserved as markdown-style markers.
    """
    if not html:
        return ""

    if _BS4_AVAILABLE:
        return _parse_with_bs4(html)
    return _parse_fallback(html)


def _parse_with_bs4(html: str) -> str:
    """Parse HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted tags entirely
    for tag_name in _REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove hidden elements
    for tag in soup.find_all(attrs={"style": re.compile(r"display\s*:\s*none", re.I)}):
        tag.decompose()
    for tag in soup.find_all(attrs={"hidden": True}):
        tag.decompose()

    lines: list[str] = []

    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "span", "div", "a"]):
        text = element.get_text(separator=" ", strip=True)
        if not text or len(text) < 3:
            continue

        tag_name = element.name if isinstance(element, Tag) else ""
        if tag_name.startswith("h"):
            level = tag_name[1] if len(tag_name) > 1 else "2"
            lines.append(f"\n{'#' * int(level)} {text}")
        elif tag_name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    result = "\n".join(lines)
    # Collapse excessive whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result[:_MAX_TEXT_LENGTH].strip()


def _parse_fallback(html: str) -> str:
    """Regex-based fallback when bs4 is not installed."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\s+", " ", text)
    return text[:_MAX_TEXT_LENGTH].strip()


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all internal href links from HTML.

    Returns absolute URLs belonging to the same domain.
    """
    if not _BS4_AVAILABLE or not html:
        return []

    from urllib.parse import urljoin, urlparse

    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc.lower()
    links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href")
        
        # Skip purely internal fragment links like "#section" or empty links
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
            
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        # Same domain only, skip if we end up with just the base domain from weird urls
        if parsed.netloc.lower() == base_domain and parsed.scheme in ("http", "https"):
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Don't add if it's just the exact root URL and nothing else (we already start there)
            if clean == base_url.rstrip("/"):
                continue
                
            if clean not in links:
                links.append(clean)

    return links
