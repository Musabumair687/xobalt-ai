"""Worker for simulating Inbox checks and triggering the Closer."""

import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.conversation_service import ConversationService
from app.services.conversation_context_service import ConversationContextService
from app.services.reply_classification_service import ReplyClassificationService
from app.services.response_service import ResponseService
from app.workflows.closer_workflow import build_closer_graph
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

class InboxWorker:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def process_new_reply(
        self,
        sender_email: str,
        subject: str,
        content: str,
        organization_id: uuid.UUID,
    ):
        """Simulates receiving a webhook from Gmail."""
        conv_service = ConversationService(self.db)
        
        try:
            msg = await conv_service.process_incoming_email(
                sender_email,
                subject,
                content,
                organization_id,
            )
            logger.info(f"Saved message {msg.id}. Triggering Closer workflow.")
            
            # Init LLM services
            llm = ChatGroq(model="llama3-8b-8192", temperature=0)
            
            context_svc = ConversationContextService()
            class_svc = ReplyClassificationService(llm)
            resp_svc = ResponseService(llm)
            
            graph = build_closer_graph(self.db, context_svc, class_svc, resp_svc)
            
            initial_state = {"conversation_message_id": msg.id, "errors": []}
            final_state = await graph.ainvoke(initial_state)
            
            logger.info(f"Closer workflow completed. Action: {final_state.get('action_taken')}")
            return final_state
            
        except ValueError as e:
            logger.error(f"Cannot process email: {e}")
            return {"errors": [str(e)]}
