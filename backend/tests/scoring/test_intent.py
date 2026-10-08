"""Tests for Intent Extraction."""

import pytest
from unittest.mock import AsyncMock
from app.services.intent_service import IntentService
from app.models.company_intelligence import CompanyIntelligence

@pytest.mark.asyncio
async def test_detect_intent_empty():
    mock_llm = AsyncMock()
    service = IntentService(mock_llm)
    
    intel = CompanyIntelligence()
    signals = await service.detect_intent(intel)
    assert len(signals) == 0
    mock_llm.with_structured_output.assert_not_called()

@pytest.mark.asyncio
async def test_detect_intent_filters_low_confidence():
    from app.services.intent_service import IntentExtractionResult, ExtractedIntentSignal
    
    mock_result = IntentExtractionResult(
        signals=[
            ExtractedIntentSignal(signal_type="HIRING", description="x", evidence="x", confidence=0.9),
            ExtractedIntentSignal(signal_type="NEW_LOCATION", description="y", evidence="y", confidence=0.2)
        ]
    )
    
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke = AsyncMock(return_value=mock_result)
    
    mock_llm = AsyncMock()
    mock_llm.with_structured_output = lambda x: mock_structured_llm
    
    service = IntentService(mock_llm)
    intel = CompanyIntelligence(services=["Real Estate Mgmt"])
    
    signals = await service.detect_intent(intel)
    
    # Should only return the high confidence one
    assert len(signals) == 1
    assert signals[0]["signal_type"] == "HIRING"
