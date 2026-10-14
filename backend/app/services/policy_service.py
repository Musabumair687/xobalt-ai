"""Policy Engine to deterministically allow or block outbound actions."""

import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.message import Message
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.organization import Organization
from app.schemas.enforcer import PolicyResult

class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def evaluate(self, message: Message, lead: Lead, campaign: Campaign) -> PolicyResult:
        """Evaluate if the message is allowed to be sent based on all business rules."""
        reasons = []
        org_res = await self.db.execute(
            select(Organization).where(
                Organization.id == message.organization_id,
            )
        )
        organization = org_res.scalars().first()
        guardrails = ((organization.settings or {}).get("guardrails", {}) if organization else {})
        require_approval = guardrails.get("require_human_approval", True)
        min_lead_score = guardrails.get("min_lead_score", 70)
        daily_send_limit = guardrails.get("daily_send_limit", 50)
        
        # 1. Approval
        if require_approval and message.status != "approved":
            reasons.append(f"Message status is '{message.status}', must be 'approved'.")
        if message.direction != "outbound" or message.channel != "email":
            reasons.append("Only outbound email messages may be sent.")
        if lead.score is None or lead.score < min_lead_score:
            reasons.append(f"Lead score must be at least {min_lead_score}.")
            
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
                Message.organization_id == message.organization_id,
                Message.status == "sent",
                Message.sent_at >= today
            )
        )
        sent_today = res_count.scalar() or 0
        if sent_today >= campaign.daily_limit:
            reasons.append(f"Campaign has reached its daily limit of {campaign.daily_limit} messages.")
        org_daily_res = await self.db.execute(
            select(func.count(Message.id)).where(
                Message.organization_id == message.organization_id,
                Message.status == "sent",
                Message.sent_at >= today,
            )
        )
        org_sent_today = org_daily_res.scalar() or 0
        if org_sent_today >= daily_send_limit:
            reasons.append(
                f"Organization has reached its daily send limit of {daily_send_limit} messages."
            )
            
        # 6. Duplicate checking
        # Did we already send this exact message to this lead?
        # A message is duplicate if there's already a 'sent' message for this campaign & lead
        res_dup = await self.db.execute(
            select(Message).where(
                Message.campaign_id == campaign.id,
                Message.organization_id == message.organization_id,
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
