"""Base interface for contact verification providers.

Verification answers: 'Is this email address valid / deliverable?'
Any provider (ZeroBounce, NeverBounce, Hunter verify, etc.) must implement
VerificationProvider.
"""
from abc import ABC, abstractmethod

from app.schemas.hunter import VerificationResult


class VerificationProvider(ABC):
    """Abstract base class for email/contact verification providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider identifier."""
        ...

    @abstractmethod
    async def verify_email(self, email: str) -> VerificationResult:
        """Check whether *email* is valid and deliverable.

        Args:
            email: The raw email address string to verify.

        Returns:
            VerificationResult with status and confidence score.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if the provider is configured and reachable."""
        ...
