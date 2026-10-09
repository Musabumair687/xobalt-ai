"""Service for scheduling follow-ups."""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from app.models.campaign_lead import CampaignLead

logger = logging.getLogger(__name__)

class FollowupService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def schedule_followup(self, message: Message, campaign_lead: CampaignLead) -> bool:
        """
        Determine if a follow-up should be scheduled and queue it conceptually.
        For Phase 7, we update the CampaignLead with next_followup_at.
        """
        if message.status != "sent":
            return False
            
        # Simple sequence logic:
        # If this was initial outreach, schedule day 3.
        # This can be made sophisticated later.
        meta = message.metadata_ or {}
        step = meta.get("step", 1)
        
        if step == 1:
            delay_days = 3
        elif step == 2:
            delay_days = 4 # Day 7 relative to start
        else:
            return False # No more follow-ups
            
        next_date = datetime.now(timezone.utc) + timedelta(days=delay_days)
        
        # We would store this schedule in CampaignLead or a dedicated table
        # Let's use last_activity_at and a conceptual next action
        campaign_lead.last_activity_at = datetime.now(timezone.utc)
        
        lead_meta = campaign_lead.lead.metadata_ or {}
        lead_meta["next_followup_at"] = next_date.isoformat()
        lead_meta["next_step"] = step + 1
        campaign_lead.lead.metadata_ = lead_meta
        
        await self.db.commit()
        logger.info(f"Scheduled follow-up step {step + 1} for lead {campaign_lead.lead_id} at {next_date}")
        return True
