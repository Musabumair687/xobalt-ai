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
from app.integrations.provider_errors import safe_provider_error

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
                
        offer = campaign.settings.get("offer") if (campaign and campaign.settings) else None
        if not offer or "workflow" in offer.lower():
            ind = company.industry if company else "your sector"
            offer = f"Exploring potential synergies, strategic collaboration, and growth opportunities in {ind}."
        
        cta = (campaign.settings.get("cta") if (campaign and campaign.settings) else None) or "Would you be open to a brief 10-minute introductory conversation this week?"
        parts.append(f"INQUIRY OBJECTIVE:\n{offer}\nTARGET CTA:\n{cta}")
        
        return "\n\n".join(parts)

    async def generate_message(self, context_str: str) -> Optional[GeneratedMessage]:
        """Call the LLM to generate the personalized components."""
        if not context_str.strip():
            logger.error("Empty context string provided to PersonalizationService")
            return None

        prompt_val = PERSONALIZATION_PROMPT.format(context=context_str)

        # 1. Try structured output via Gemini
        try:
            structured_llm = self.llm.with_structured_output(GeneratedMessage)
            result = await structured_llm.ainvoke(prompt_val)
            if result and result.subject:
                return result
        except Exception as exc:
            logger.warning(
                "Structured message generation failed (%s); trying JSON fallback.",
                type(exc).__name__,
            )

        # 2. Resilient fallback with direct prompt
        try:
            import json
            import re
            json_prompt = (
                f"{prompt_val}\n\n"
                "Return ONLY a JSON object with keys: 'subject', 'opening', 'value_proposition', 'cta'. "
                "Do not wrap in markdown or anything else."
            )
            raw_res = await self.llm.ainvoke(json_prompt)
            raw_text = raw_res.content if hasattr(raw_res, "content") else str(raw_res)

            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return GeneratedMessage(
                    subject=data.get("subject", "Quick introduction & collaboration"),
                    opening=data.get("opening", "I noticed your team's impressive market presence and wanted to reach out."),
                    value_proposition=data.get("value_proposition", "We are connecting with key industry operators to discuss growth partnerships."),
                    cta=data.get("cta", "Would you have a few minutes for a brief introductory call this week?"),
                )
        except Exception as exc:
            logger.error(
                "Message generation failed (%s).",
                type(exc).__name__,
            )
            raise safe_provider_error("llm", exc) from exc

        raise RuntimeError("LLM returned no valid structured or JSON message.")
