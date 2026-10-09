"""Service for managing campaigns and background workers conceptually."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.campaign import Campaign
from app.models.message import Message
from app.workflows.enforcer_workflow import build_enforcer_graph
from app.services.policy_service import PolicyService
from app.services.outreach_service import OutreachService
from app.services.message_event_service import MessageEventService
from app.services.followup_service import FollowupService
from app.integrations.email.gmail import GmailProvider

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def process_campaign_outreach(self, campaign_id: str):
        """
        Worker task that finds all 'approved' messages for a campaign 
        and runs them through the Enforcer.
        """
        logger.info(f"Starting outreach worker for campaign {campaign_id}")
        
        # Find all pending messages for this campaign
        res = await self.db.execute(
            select(Message).where(
                Message.campaign_id == campaign_id,
                Message.status == "approved"
            )
        )
        messages = res.scalars().all()
        
        if not messages:
            logger.info("No approved messages to send.")
            return
            
        logger.info(f"Found {len(messages)} approved messages to process.")
        
        # Setup services
        policy_svc = PolicyService(self.db)
        email_provider = GmailProvider() # Stub
        outreach_svc = OutreachService(self.db, email_provider)
        event_svc = MessageEventService(self.db)
        followup_svc = FollowupService(self.db)
        
        graph = build_enforcer_graph(self.db, policy_svc, outreach_svc, event_svc, followup_svc)
        
        for msg in messages:
            logger.info(f"Executing Enforcer for message {msg.id}")
            initial_state = {"message_id": msg.id, "errors": []}
            
            try:
                await graph.ainvoke(initial_state)
            except Exception as e:
                logger.error(f"Error processing message {msg.id}: {e}")
                
        logger.info("Outreach processing complete.")
