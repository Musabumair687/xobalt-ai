"""Service to build context string for Closer."""

from typing import List
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.models.lead import Lead
from app.models.campaign import Campaign

class ConversationContextService:
    def build_context(
        self,
        conversation: Conversation,
        messages: List[ConversationMessage],
        lead: Lead,
        campaign: Campaign
    ) -> str:
        """Construct the context string for the LLM to understand the conversation history."""
        parts = []
        
        if lead.person:
            parts.append(f"CONTACT: {lead.person.first_name} {lead.person.last_name} ({lead.person.title})")
        if lead.company:
            parts.append(f"COMPANY: {lead.company.name} - {lead.company.industry}")
            
        if campaign:
            offer = campaign.settings.get("offer", "We help automate business workflows.")
            parts.append(f"OUR OFFER: {offer}")
        
        parts.append("--- CONVERSATION HISTORY ---")
        
        # Sort messages by sequence number just in case
        sorted_messages = sorted(messages, key=lambda m: m.sequence_number)
        
        # Only include the last 5 messages to avoid blowing up the context window
        recent_messages = sorted_messages[-5:]
        
        for m in recent_messages:
            sender = "XOBALT" if m.direction == "OUTBOUND" else "PROSPECT"
            parts.append(f"[{sender}]: {m.content}")
            
        return "\n".join(parts)
