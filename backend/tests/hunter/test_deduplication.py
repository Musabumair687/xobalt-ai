"""Tests for DeduplicationService."""

import pytest
from app.services.deduplication_service import (
    DeduplicationService,
    normalize_domain,
)
from app.schemas.hunter import DiscoveredCompany


# ---------------------------------------------------------------------------
# normalize_domain unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://www.abc-realty.com/", "abc-realty.com"),
        ("http://abc-realty.com", "abc-realty.com"),
        ("www.abc-realty.com", "abc-realty.com"),
        ("ABC-Realty.COM", "abc-realty.com"),
        ("abc-realty.com/about", "abc-realty.com"),
        ("https://abc-realty.com?source=google", "abc-realty.com"),
        (None, None),
        ("", None),
    ],
)
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


# ---------------------------------------------------------------------------
# DeduplicationService tests
# ---------------------------------------------------------------------------


def _make(name: str, domain: str | None = None) -> DiscoveredCompany:
    return DiscoveredCompany(name=name, domain=domain)


def test_dedup_removes_same_domain_variants():
    """Companies with the same canonical domain should collapse to one."""
    companies = [
        _make("ABC Realty", "https://www.abc-realty.com/"),
        _make("ABC Realty LLC", "http://abc-realty.com"),
        _make("ABC Realty Inc", "www.abc-realty.com"),
    ]
    svc = DeduplicationService()
    result = svc.deduplicate_companies(companies)
    assert len(result) == 1
    assert result[0].name == "ABC Realty"  # first one wins


def test_dedup_keeps_different_domains():
    companies = [
        _make("ABC Realty", "abc-realty.com"),
        _make("XYZ Properties", "xyzproperties.com"),
    ]
    result = DeduplicationService().deduplicate_companies(companies)
    assert len(result) == 2


def test_dedup_fallback_to_name():
    """Without a domain, use normalized name as key."""
    companies = [
        _make("ABC Realty LLC"),
        _make("ABC Realty Inc"),   # same normalized name → duplicate
        _make("XYZ Properties"),
    ]
    result = DeduplicationService().deduplicate_companies(companies)
    assert len(result) == 2


def test_dedup_empty_list():
    assert DeduplicationService().deduplicate_companies([]) == []


def test_dedup_single_company():
    companies = [_make("Solo Co", "solo.com")]
    result = DeduplicationService().deduplicate_companies(companies)
    assert len(result) == 1
