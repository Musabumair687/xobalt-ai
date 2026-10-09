"""Tests for Personalization Service."""

import pytest
from app.services.personalization_service import PersonalizationService
from app.models.company import Company
from app.models.person import Person
from app.models.campaign import Campaign
from app.models.intent_signal import IntentSignal

def test_build_context_string():
    service = PersonalizationService(None)
    
    company = Company(name="ABC Realty", industry="Real Estate", city="Miami", state="FL")
    person = Person(first_name="John", last_name="Smith", title="CEO")
    signals = [
        IntentSignal(signal_type="NEW_LOCATION", description="Expanded to Miami", confidence=0.9)
    ]
    campaign = Campaign(settings={"offer": "Test offer", "cta": "Test CTA"})
    
    ctx = service.build_context_string(company, person, None, signals, campaign)
    
    assert "John Smith" in ctx
    assert "ABC Realty" in ctx
    assert "Miami" in ctx
    assert "NEW_LOCATION" in ctx
    assert "Test offer" in ctx
    assert "Test CTA" in ctx
