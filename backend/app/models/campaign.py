import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

class Campaign(Base):
    """Represents a campaign."""
    
    __tablename__ = "campaigns"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='draft')
    target_industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_company_size_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_company_size_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_locations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=30)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="campaigns")
    created_by: Mapped[Optional["User"]] = relationship("User", back_populates="created_campaigns")
    campaign_leads: Mapped[List["CampaignLead"]] = relationship("CampaignLead", back_populates="campaign")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="campaign")