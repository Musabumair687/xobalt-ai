"""Gmail API integration for sending emails."""

import logging
from typing import Optional
from app.integrations.email.base import EmailProvider

logger = logging.getLogger(__name__)

class GmailProvider(EmailProvider):
    """
    Gmail implementation for EmailProvider.
    
    Note: In Phase 7 this acts as a stub that mimics calling the Gmail API
    so we can test the Enforcer's control logic without actually sending spam.
    In Phase 12 (Production) this will connect to googleapiclient.
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        
    async def send_email(self, to_email: str, subject: str, body: str, from_email: Optional[str] = None) -> str:
        """Mimics sending an email via Gmail API."""
        import uuid
        
        if not to_email:
            raise ValueError("Recipient email is required.")
            
        logger.info(f"[GMAIL] Sending email to {to_email} | Subject: {subject}")
        # Mimic external ID generation
        return f"gmail-msg-{uuid.uuid4().hex[:10]}"
