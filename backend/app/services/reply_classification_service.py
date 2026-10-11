"""Service for classifying prospect replies."""

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from app.schemas.closer import ReplyClassification
from app.agents.closer.prompts import CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)

class ReplyClassificationService:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def classify(self, context_str: str) -> Optional[ReplyClassification]:
        """Classify the latest reply based on context."""
        if not context_str:
            return None
            
        structured_llm = self.llm.with_structured_output(ReplyClassification)
        
        try:
            logger.info("Classifying reply intent...")
            prompt_val = CLASSIFICATION_PROMPT.format(context=context_str)
            result: ReplyClassification = await structured_llm.ainvoke(prompt_val)
            return result
        except Exception as e:
            logger.error(f"Failed to classify reply: {e}")
            return None
