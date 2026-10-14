"""Service for managing Conversations and Inbox ingestion."""

import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.models.contact import Contact
from app.models.lead import Lead

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def process_incoming_email(
        self,
        sender_email: str,
        subject: str,
        content: str,
        organization_id: uuid.UUID,
    ) -> ConversationMessage:
        """
        Process an incoming email. Finds the associated lead/conversation and stores the message.
        """
        logger.info(f"Processing incoming email from {sender_email}")
        
        # Find contact
        res_contact = await self.db.execute(
            select(Contact)
            .join(Lead, Lead.person_id == Contact.person_id)
            .where(
                Contact.type == "email",
                Contact.value == sender_email,
                Lead.organization_id == organization_id,
            )
        )
        contact = res_contact.scalars().first()
        
        if not contact:
            raise ValueError(f"No known contact found for email {sender_email}")
            
        # Find lead
        res_lead = await self.db.execute(
            select(Lead).where(
                Lead.person_id == contact.person_id,
                Lead.organization_id == organization_id,
            )
        )
        lead = res_lead.scalars().first()
        
        if not lead:
            raise ValueError(f"No lead found for contact {sender_email}")
            
        # Find or create conversation
        res_conv = await self.db.execute(
            select(Conversation).where(
                Conversation.lead_id == lead.id,
                Conversation.organization_id == organization_id,
                Conversation.channel == "email",
            )
        )
        conv = res_conv.scalars().first()
        
        if not conv:
            conv = Conversation(
                organization_id=organization_id,
                lead_id=lead.id,
                subject=subject,
                channel="email"
            )
            self.db.add(conv)
            await self.db.flush()
            
        # Store message
        seq = conv.message_count + 1
        msg = ConversationMessage(
            conversation_id=conv.id,
            direction="INBOUND",
            content=content,
            sender=sender_email,
            sequence_number=seq
        )
        self.db.add(msg)
        
        conv.message_count = seq
        conv.status = "WAITING_FOR_XOBALT"
        
        await self.db.commit()
        await self.db.refresh(msg)
        return msg
