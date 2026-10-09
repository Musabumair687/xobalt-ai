"""Deterministic validation for generated messages."""

from app.schemas.personalization import GeneratedMessage, MessageValidationResult

class MessageValidationService:
    def __init__(self):
        # Could inject DB to check duplicates/opt-outs, but keep simple for now
        pass

    def validate(self, message: GeneratedMessage) -> MessageValidationResult:
        """Run deterministic checks on the generated content."""
        errors = []
        warnings = []
        
        # 1. Required fields
        if not message.subject or not message.subject.strip():
            errors.append("Subject is missing.")
        if not message.opening or not message.opening.strip():
            errors.append("Opening is missing.")
        if not message.value_proposition or not message.value_proposition.strip():
            errors.append("Value proposition is missing.")
        if not message.cta or not message.cta.strip():
            errors.append("CTA is missing.")
            
        # 2. Length constraints
        full_body = f"{message.opening}\n\n{message.value_proposition}\n\n{message.cta}"
        if len(full_body) > 1500:
            errors.append("Generated body exceeds maximum allowed length (1500 chars).")
        if len(full_body) < 50:
            errors.append("Generated body is suspiciously short.")
            
        # 3. Simple regex checks (e.g., placeholder leaks)
        if "[" in full_body and "]" in full_body:
            warnings.append("Message may contain unfilled placeholders (e.g. [Company Name]).")
            
        return MessageValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
