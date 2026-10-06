"""DeduplicationService — removes duplicate companies from discovery results.

Primary deduplication key: **normalized domain**.
Secondary (fallback): normalized company name.

Domain normalization rules
--------------------------
1. Strip protocol:  https://www.abc-realty.com/ → abc-realty.com
2. Strip www prefix: www.abc-realty.com → abc-realty.com
3. Strip trailing slash.
4. Lower-case.

If two companies share the same normalized domain they are considered
the same entity — the first one encountered wins (preserving order).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from app.schemas.hunter import DiscoveredCompany

logger = logging.getLogger(__name__)

# Regex to strip trailing path/query from a URL-like string
_DOMAIN_CLEANUP = re.compile(r"[/?#].*$")


def normalize_domain(raw: str | None) -> str | None:
    """Return a canonical lower-case domain from a raw URL or domain string.

    Returns None if the input is empty or cannot be parsed.
    """
    if not raw:
        return None

    raw = raw.strip().lower()

    # If it looks like a full URL, parse it properly
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        domain = parsed.netloc
    else:
        domain = raw

    # Strip www.
    if domain.startswith("www."):
        domain = domain[4:]

    # Strip trailing path remnants (e.g. "abc.com/about")
    domain = _DOMAIN_CLEANUP.sub("", domain)

    return domain or None


def normalize_name(name: str) -> str:
    """Normalize a company name for secondary deduplication.

    Removes common legal suffixes (LLC, Inc, Ltd, etc.) and lowercases.
    """
    name = name.lower().strip()
    # Remove common legal suffixes
    name = re.sub(
        r"\b(llc|inc|ltd|co|corp|corporation|limited|lp|llp|plc|gmbh)\b\.?",
        "",
        name,
    )
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


class DeduplicationService:
    """Deduplicate a list of DiscoveredCompany objects."""

    def deduplicate_companies(
        self, companies: list[DiscoveredCompany]
    ) -> list[DiscoveredCompany]:
        """Return only unique companies, preserving order.

        Companies are considered identical if their normalized domains match.
        If a company has no domain, we fall back to normalized name matching.
        """
        seen_domains: set[str] = set()
        seen_names: set[str] = set()
        unique: list[DiscoveredCompany] = []

        for company in companies:
            norm_domain = normalize_domain(company.domain)

            # Primary key: domain
            if norm_domain:
                if norm_domain in seen_domains:
                    logger.debug(
                        "Dedup: dropping '%s' (domain '%s' already seen).",
                        company.name,
                        norm_domain,
                    )
                    continue
                seen_domains.add(norm_domain)
            else:
                # Fallback key: name
                norm_name = normalize_name(company.name)
                if norm_name in seen_names:
                    logger.debug(
                        "Dedup: dropping '%s' (name already seen).", company.name
                    )
                    continue
                seen_names.add(norm_name)

            unique.append(company)

        logger.info(
            "Dedup: %d → %d companies.", len(companies), len(unique)
        )
        return unique
