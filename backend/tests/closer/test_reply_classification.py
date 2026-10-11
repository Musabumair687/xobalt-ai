"""Tests for Reply Classification Service."""

import pytest
from unittest.mock import AsyncMock
from app.services.reply_classification_service import ReplyClassificationService
from app.schemas.closer import ReplyClassification

class MockLLM:
    def with_structured_output(self, schema):
        return self
        
    async def ainvoke(self, prompt):
        prompt_str = str(prompt).lower()
        if "does it cost" in prompt_str:
            return ReplyClassification(intent="PRICING", confidence=0.9, reason="test")
        elif "integrate with hubspot" in prompt_str:
            return ReplyClassification(intent="QUESTION", confidence=0.9, reason="test")
        elif "remove me" in prompt_str:
            return ReplyClassification(intent="UNSUBSCRIBE", confidence=0.9, reason="test")
        elif "tomorrow" in prompt_str:
            return ReplyClassification(intent="INTERESTED", confidence=0.9, reason="test")
        return ReplyClassification(intent="UNCLEAR", confidence=0.4, reason="test")

@pytest.mark.asyncio
async def test_classify_pricing():
    service = ReplyClassificationService(MockLLM())
    res = await service.classify("How much does it cost?")
    assert res.intent == "PRICING"

@pytest.mark.asyncio
async def test_classify_question():
    service = ReplyClassificationService(MockLLM())
    res = await service.classify("Does it integrate with HubSpot?")
    assert res.intent == "QUESTION"

@pytest.mark.asyncio
async def test_classify_unsubscribe():
    service = ReplyClassificationService(MockLLM())
    res = await service.classify("Remove me from your list")
    assert res.intent == "UNSUBSCRIBE"
