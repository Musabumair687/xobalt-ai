"""Base interface for Email Providers."""

from abc import ABC, abstractmethod
from typing import Optional

class EmailProvider(ABC):
    """Abstract base class for email sending providers."""
    
    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str, from_email: Optional[str] = None) -> str:
        """
        Sends an email.
        
        Args:
            to_email: The recipient's email address.
            subject: The subject of the email.
            body: The body of the email (plain text or HTML depending on implementation).
            from_email: Optional sender address, if provider allows multiple.
            
        Returns:
            The external provider's message ID as a string.
            
        Raises:
            Exception if sending fails permanently or temporarily.
        """
        pass
