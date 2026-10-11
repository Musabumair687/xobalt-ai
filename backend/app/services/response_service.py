"""Service for generating responses."""

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from app.agents.closer.prompts import RESPONSE_PROMPT

logger = logging.getLogger(__name__)

class ResponseService:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def generate_response(self, context_str: str, intent: str) -> Optional[str]:
        """Generate a contextual response for Questions or Pricing."""
        if not context_str:
            return None
            
        chain = RESPONSE_PROMPT | self.llm | StrOutputParser()
        
        try:
            logger.info(f"Generating response for intent {intent}...")
            result = await chain.ainvoke({"context": context_str, "intent": intent})
            return result
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return None
