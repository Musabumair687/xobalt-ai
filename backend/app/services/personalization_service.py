"""Service for generating evidence-based personalized messages using LLMs."""

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from app.models.lead import Lead
from app.models.company import Company
from app.models.person import Person
from app.models.company_intelligence import CompanyIntelligence
from app.models.intent_signal import IntentSignal
from app.models.campaign import Campaign
from app.schemas.personalization import GeneratedMessage
from app.agents.personalization.prompts import PERSONALIZATION_PROMPT

logger = logging.getLogger(__name__)

class PersonalizationService:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def build_context_string(
        self,
        company: Optional[Company],
        person: Optional[Person],
        intelligence: Optional[CompanyIntelligence],
        intent_signals: list[IntentSignal],
        campaign: Campaign
    ) -> str:
        """Construct the evidence block for the LLM."""
        
        parts = []
        
        if person:
            parts.append(f"PERSON:\nName: {person.first_name} {person.last_name}\nRole: {person.title}")
            
        if company:
            parts.append(f"COMPANY FACTS:\nName: {company.name}\nIndustry: {company.industry}\nLocation: {company.city}, {company.state}")
            
        if intelligence:
            intel_parts = []
            if intelligence.services: intel_parts.append(f"Services: {', '.join(intelligence.services)}")
            if intelligence.locations: intel_parts.append(f"Locations: {', '.join(intelligence.locations)}")
            if intelligence.unique_selling_points: intel_parts.append(f"USPs: {', '.join(intelligence.unique_selling_points)}")
            if intel_parts:
                parts.append("WEBSITE EVIDENCE:\n" + "\n".join(intel_parts))
                
        if intent_signals:
            sig_parts = []
            for sig in intent_signals[:2]: # Top 2 signals to avoid overwhelming context
                sig_parts.append(f"- {sig.signal_type}: {sig.description} (Confidence: {sig.confidence})")
            if sig_parts:
                parts.append("INTENT SIGNALS:\n" + "\n".join(sig_parts))
                
        offer = campaign.settings.get("offer", "We help automate business workflows.")
        cta = campaign.settings.get("cta", "Would you be open to a quick chat?")
        parts.append(f"OUR OFFER:\n{offer}\nTARGET CTA:\n{cta}")
        
        return "\n\n".join(parts)

    async def generate_message(self, context_str: str) -> Optional[GeneratedMessage]:
        """Call the LLM to generate the personalized components."""
        if not context_str.strip():
            logger.error("Empty context string provided to PersonalizationService")
            return None
            
        structured_llm = self.llm.with_structured_output(GeneratedMessage)
        
        try:
            logger.info("Generating personalized message via LLM...")
            prompt_val = PERSONALIZATION_PROMPT.format(context=context_str)
            result: GeneratedMessage = await structured_llm.ainvoke(prompt_val)
            return result
        except Exception as e:
            logger.error(f"Failed to generate personalization: {e}")
            return None
