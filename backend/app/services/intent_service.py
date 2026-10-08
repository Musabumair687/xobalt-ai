"""Service for detecting intent using LLMs."""

import logging
from typing import List
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel
from app.models.company_intelligence import CompanyIntelligence
from app.agents.scoring_intent.prompts import INTENT_PROMPT

logger = logging.getLogger(__name__)

# Output schema for the LLM
class ExtractedIntentSignal(BaseModel):
    signal_type: str = Field(description="Must be one of the supported signal types")
    description: str = Field(description="Summary of the signal")
    evidence: str = Field(description="Text proving the signal")
    confidence: float = Field(description="Confidence between 0.0 and 1.0")

class IntentExtractionResult(BaseModel):
    signals: List[ExtractedIntentSignal] = Field(default_factory=list)

class IntentService:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def detect_intent(self, intelligence: CompanyIntelligence) -> List[dict]:
        """Analyze website intelligence for intent signals."""
        if not intelligence:
            return []

        # Build context string from structured intelligence
        context_parts = []
        if intelligence.services:
            context_parts.append(f"Services: {', '.join(intelligence.services)}")
        if intelligence.projects:
            context_parts.append(f"Projects: {', '.join(intelligence.projects)}")
        if intelligence.unique_selling_points:
            context_parts.append(f"USPs: {', '.join(intelligence.unique_selling_points)}")
            
        context = "\n".join(context_parts)
        if not context.strip():
            return []

        structured_llm = self.llm.with_structured_output(IntentExtractionResult)
        
        try:
            logger.info("Extracting intent signals using LLM...")
            prompt_str = INTENT_PROMPT.format(context=context)
            
            result: IntentExtractionResult = await structured_llm.ainvoke(prompt_str)
            
            # Convert to dicts, filter out low confidence
            signals = []
            for sig in result.signals:
                if sig.confidence >= 0.5:
                    signals.append(sig.model_dump())
                    
            return signals
            
        except Exception as e:
            logger.error(f"Intent Extraction failed: {e}")
            # If LLM fails, return empty gracefully so scoring can continue
            return []
