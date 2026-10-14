"""Service for processing approved messages for an individual campaign."""

import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.campaign import Campaign
from app.models.message import Message
from app.models.lead import Lead
from app.workflows.enforcer_workflow import build_enforcer_graph
from app.services.policy_service import PolicyService
from app.services.outreach_service import OutreachService
from app.services.message_event_service import MessageEventService
from app.services.followup_service import FollowupService
from app.integrations.email import get_email_provider

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def process_campaign_outreach(
        self,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
        message_ids: list[uuid.UUID] | None = None,
    ) -> dict[str, int]:
        """
        Worker task that finds all 'approved' messages for a campaign 
        and runs them through the Enforcer.
        """
        logger.info(f"Starting outreach worker for campaign {campaign_id}")
        
        # Find all pending messages for this campaign
        approved_stmt = (
            select(Message)
            .join(Lead, Lead.id == Message.lead_id)
            .where(
                Message.campaign_id == campaign_id,
                Message.organization_id == organization_id,
                Lead.organization_id == organization_id,
                Message.direction == "outbound",
                Message.channel == "email",
                Message.status == "approved"
            )
        )
        if message_ids is not None:
            approved_stmt = approved_stmt.where(Message.id.in_(message_ids))
        res = await self.db.execute(approved_stmt)
        messages = res.scalars().all()

        selected_ids = (
            message_ids
            if message_ids is not None
            else [message.id for message in messages]
        )
        if not messages:
            logger.info("No approved messages to send.")
            return await self._count_selected_messages(
                campaign_id,
                organization_id,
                selected_ids,
                blocked=0,
            )
            
        logger.info(f"Found {len(messages)} approved messages to process.")
        
        # Setup services
        policy_svc = PolicyService(self.db)
        email_provider = get_email_provider()
        outreach_svc = OutreachService(self.db, email_provider)
        event_svc = MessageEventService(self.db)
        followup_svc = FollowupService(self.db)
        
        graph = build_enforcer_graph(self.db, policy_svc, outreach_svc, event_svc, followup_svc)
        
        blocked = 0
        for msg in messages:
            logger.info("Executing Enforcer for message %s", msg.id)
            final_state = await graph.ainvoke({"message_id": msg.id, "errors": []})
            if final_state.get("status") == "blocked":
                blocked += 1

        counts = await self._count_selected_messages(
            campaign_id,
            organization_id,
            selected_ids,
            blocked=blocked,
        )
        logger.info("Outreach processing complete: %s", counts)
        return counts

    async def get_approved_message_ids(
        self,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(Message.id)
            .join(Lead, Lead.id == Message.lead_id)
            .where(
                Message.campaign_id == campaign_id,
                Message.organization_id == organization_id,
                Lead.organization_id == organization_id,
                Message.direction == "outbound",
                Message.channel == "email",
                Message.status == "approved",
            )
        )
        return list(result.scalars().all())

    async def _count_selected_messages(
        self,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
        message_ids: list[uuid.UUID],
        *,
        blocked: int,
    ) -> dict[str, int]:
        counts = {
            "selected": len(message_ids),
            "sent": 0,
            "blocked": blocked,
            "failed": 0,
            "skipped": 0,
        }
        if not message_ids:
            return counts
        result = await self.db.execute(
            select(Message.status).where(
                Message.id.in_(message_ids),
                Message.campaign_id == campaign_id,
                Message.organization_id == organization_id,
            )
        )
        for message_status in result.scalars().all():
            if message_status in ("sent", "failed", "sending"):
                counts["sent" if message_status == "sent" else (
                    "failed" if message_status == "failed" else "skipped"
                )] += 1
        return counts
