"""Tests for the deterministic scoring service."""

import pytest
from app.services.scoring_service import ScoringService, classify_score
from app.models.company import Company
from app.models.person import Person
from app.models.company_intelligence import CompanyIntelligence
from app.models.intent_signal import IntentSignal

def test_classify_score():
    assert classify_score(90) == "HIGH_PRIORITY"
    assert classify_score(85) == "HIGH_PRIORITY"
    assert classify_score(75) == "QUALIFIED"
    assert classify_score(70) == "QUALIFIED"
    assert classify_score(50) == "NURTURE"
    assert classify_score(40) == "NURTURE"
    assert classify_score(39) == "REJECT"
    assert classify_score(0) == "REJECT"

def test_calculate_industry_score():
    service = ScoringService()
    
    # Target industry
    c_target = Company(industry="Real Estate")
    res = service.calculate_industry_score(c_target)
    assert res.score == 25
    
    # Non-target industry
    c_other = Company(industry="Healthcare")
    res = service.calculate_industry_score(c_other)
    assert res.score == 12 # 25 // 2
    
    # Missing industry
    res = service.calculate_industry_score(Company())
    assert res.score == 0

def test_calculate_size_score():
    service = ScoringService()
    
    c_good = Company(employee_count=45)
    res = service.calculate_size_score(c_good)
    assert res.score == 15
    
    c_huge = Company(employee_count=5000)
    res = service.calculate_size_score(c_huge)
    assert res.score == 0

def test_calculate_decision_maker_score():
    service = ScoringService()
    
    p_ceo = Person(title="CEO")
    res = service.calculate_decision_maker_score(p_ceo)
    assert res.score == 15
    
    p_manager = Person(title="Marketing Manager")
    res = service.calculate_decision_maker_score(p_manager)
    assert res.score == 7 # 15 // 2

def test_calculate_website_score():
    service = ScoringService()
    
    intel = CompanyIntelligence(
        services=["Property Mgmt"],
        unique_selling_points=["24/7 Support"],
        target_market=["Investors"]
    )
    res = service.calculate_website_score(intel)
    assert res.score == 15
    
    intel_empty = CompanyIntelligence()
    res = service.calculate_website_score(intel_empty)
    assert res.score == 0

def test_calculate_intent_score():
    service = ScoringService()
    
    signals = [
        IntentSignal(signal_type="HIRING"),
        IntentSignal(signal_type="NEW_LOCATION")
    ]
    res = service.calculate_intent_score(signals)
    assert res.score == 20
    
    res_empty = service.calculate_intent_score([])
    assert res_empty.score == 0
    
def test_full_scoring():
    service = ScoringService()
    c = Company(industry="Real Estate", employee_count=45, state="Texas")
    p = Person(title="CEO")
    intel = CompanyIntelligence(services=["Mgmt"])
    signals = [IntentSignal(signal_type="HIRING")]
    
    breakdown = service.score_lead(c, p, intel, signals)
    assert breakdown.industry_match.score == 25
    assert breakdown.company_size.score == 15
    assert breakdown.location.score == 10
    assert breakdown.decision_maker.score == 15
    assert breakdown.website.score == 5
    assert breakdown.intent.score == 10
    assert breakdown.total_score() == 80
