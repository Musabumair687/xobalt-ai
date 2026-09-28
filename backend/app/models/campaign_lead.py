from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base

class CampaignLead(Base):
    __tablename__ = "campaign_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # pending, contacted, converted, bounced
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)