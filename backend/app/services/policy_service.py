"""Policy Engine to deterministically allow or block outbound actions."""

import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.message import Message
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.schemas.enforcer import PolicyResult

class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def evaluate(self, message: Message, lead: Lead, campaign: Campaign) -> PolicyResult:
        """Evaluate if the message is allowed to be sent based on all business rules."""
        reasons = []
        
        # 1. Approval
        if message.status != "approved":
            reasons.append(f"Message status is '{message.status}', must be 'approved'.")
            
        # 2. Contact validity
        if not lead.person:
            reasons.append("Lead does not have a valid person record.")
        else:
            email = next((c.value for c in lead.person.contacts if c.type == "email"), None)
            if not email:
                reasons.append("Lead does not have a valid email address.")
            
        # 3. Opt-out (We don't have an opt_out flag in Lead Phase 2, but we can mimic it)
        # Assuming lead.person has a conceptual opt_out in metadata or we check events later.
        # For now, let's assume it's valid unless metadata explicitly says so.
        if lead.person and lead.person.metadata_ and lead.person.metadata_.get("opted_out"):
            reasons.append("Lead has opted out of communications.")
            
        # 4. Campaign status
        if campaign.status not in ["active", "running"]:
            # If the user is just testing, we might allow it, but strictly it should be active.
            # We'll just add a warning or block. Let's block if paused/stopped.
            if campaign.status in ["paused", "stopped", "completed"]:
                reasons.append(f"Campaign is currently {campaign.status}.")
                
        # 5. Daily Limits (Campaign limit)
        # Count messages sent today for this campaign
        today = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        res_count = await self.db.execute(
            select(func.count(Message.id)).where(
                Message.campaign_id == campaign.id,
                Message.status == "sent",
                Message.sent_at >= today
            )
        )
        sent_today = res_count.scalar() or 0
        if sent_today >= campaign.daily_limit:
            reasons.append(f"Campaign has reached its daily limit of {campaign.daily_limit} messages.")
            
        # 6. Duplicate checking
        # Did we already send this exact message to this lead?
        # A message is duplicate if there's already a 'sent' message for this campaign & lead
        res_dup = await self.db.execute(
            select(Message).where(
                Message.campaign_id == campaign.id,
                Message.lead_id == lead.id,
                Message.status == "sent"
            )
        )
        if res_dup.scalars().first():
            reasons.append("A message was already sent to this lead in this campaign.")
            
        return PolicyResult(
            allowed=len(reasons) == 0,
            reasons=reasons
        )
