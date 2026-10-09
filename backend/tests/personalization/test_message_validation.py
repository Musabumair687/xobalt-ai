"""Tests for Message Validation Service."""

from app.schemas.personalization import GeneratedMessage
from app.services.message_validation_service import MessageValidationService

def test_validate_message_valid():
    service = MessageValidationService()
    
    msg = GeneratedMessage(
        subject="Hello",
        opening="This is a good opening.",
        value_proposition="This is a solid value prop that is long enough to pass validation.",
        cta="Let's talk."
    )
    
    res = service.validate(msg)
    assert res.is_valid is True
    assert len(res.errors) == 0

def test_validate_message_missing_fields():
    service = MessageValidationService()
    
    msg = GeneratedMessage(
        subject="",
        opening="This is an opening.",
        value_proposition="",
        cta="Let's talk."
    )
    
    res = service.validate(msg)
    assert res.is_valid is False
    assert "Subject is missing." in res.errors
    assert "Value proposition is missing." in res.errors

def test_validate_message_too_short():
    service = MessageValidationService()
    
    msg = GeneratedMessage(
        subject="Hi",
        opening="a",
        value_proposition="b",
        cta="c"
    )
    
    res = service.validate(msg)
    assert res.is_valid is False
    assert any("suspiciously short" in e for e in res.errors)

def test_validate_message_placeholders():
    service = MessageValidationService()
    
    msg = GeneratedMessage(
        subject="Hello [Name]",
        opening="This is a good opening for [Company].",
        value_proposition="This is a solid value prop that is long enough to pass validation.",
        cta="Let's talk."
    )
    
    res = service.validate(msg)
    # Warnings don't fail validation by default right now, but they are flagged
    assert res.is_valid is True
    assert len(res.warnings) > 0
    assert "unfilled placeholders" in res.warnings[0]
