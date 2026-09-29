import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base

class Message(Base):
    """
    Message model representing communications sent/received.
    """
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"))
    
    channel: Mapped[str] = mapped_column(String(50))
    direction: Mapped[str] = mapped_column(String(20))
    sender_email: Mapped[Optional[str]] = mapped_column(String(320))
    recipient_email: Mapped[Optional[str]] = mapped_column(String(320))
    subject: Mapped[Optional[str]] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default='draft')
    
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[Optional[str]] = mapped_column(String(500))
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, name='metadata')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="messages")
    lead: Mapped[Optional["Lead"]] = relationship(back_populates="messages")
    campaign: Mapped[Optional["Campaign"]] = relationship(back_populates="messages")
    events: Mapped[list["MessageEvent"]] = relationship(back_populates="message", cascade="all, delete-orphan")