"""Service for extracting structured intelligence using LLMs."""

import logging
from langchain_core.language_models.chat_models import BaseChatModel
from app.schemas.website_intelligence import FetchedPage, ExtractedIntelligence, IntelligenceWithEvidence
from app.agents.website_intelligence.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

class IntelligenceService:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def extract(self, pages: list[FetchedPage]) -> IntelligenceWithEvidence:
        """Combine clean text from pages and extract structured intelligence."""
        if not pages:
            raise ValueError("No pages to analyze.")

        # Combine text clearly marking sources
        combined_text_parts = []
        for p in pages:
            combined_text_parts.append(f"--- SOURCE URL: {p.url} ({p.page_type.value}) ---\n{p.clean_text}")
        
        combined_text = "\n\n".join(combined_text_parts)
        
        # Max token safety (rough truncation)
        max_chars = 100_000 
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars]

        # Use structured output
        structured_llm = self.llm.with_structured_output(ExtractedIntelligence)
        
        try:
            logger.info(f"Extracting intelligence from {len(pages)} pages using LLM...")
            
            # Note: We must format the prompt into a string first
            prompt_str = EXTRACTION_PROMPT.format(text=combined_text)
            
            result: ExtractedIntelligence = await structured_llm.ainvoke(prompt_str)
            
            # Simple evidence tracker: We can't perfectly map AI thoughts without a more
            # complex pipeline, so for Phase 4 we map URLs.
            urls = [p.url for p in pages]
            evidence = {
                "services": urls,
                "target_market": urls,
                "locations": urls,
                "unique_selling_points": urls,
                "projects": urls,
                "contact_info": urls,
                "technology": urls,
            }
            
            return IntelligenceWithEvidence(
                intelligence=result,
                evidence=evidence,
                confidence=0.85, # Hardcoded for Phase 4, dynamic later
                pages_analyzed=len(pages),
                model_used=getattr(self.llm, "model_name", "unknown")
            )
            
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            raise
