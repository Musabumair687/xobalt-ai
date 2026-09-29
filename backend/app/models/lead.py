import uuid
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import String, Float, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Lead(Base):
    """Lead model representing a sales prospect lifecycle."""
    __tablename__ = 'leads'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('persons.id', ondelete='SET NULL'), nullable=True)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('companies.id', ondelete='SET NULL'), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='new', index=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qualification_status: Mapped[str] = mapped_column(String(50), default='unqualified')
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="leads")
    person: Mapped[Optional["Person"]] = relationship("Person", back_populates="leads")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="leads")
    events: Mapped[List["LeadEvent"]] = relationship("LeadEvent", back_populates="lead")
    intent_signals: Mapped[List["IntentSignal"]] = relationship("IntentSignal", back_populates="lead")
    sources: Mapped[List["LeadSource"]] = relationship("LeadSource", back_populates="lead")
    campaign_leads: Mapped[List["CampaignLead"]] = relationship("CampaignLead", back_populates="lead")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="lead")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="lead")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="lead")
    agent_decisions: Mapped[List["AgentDecision"]] = relationship("AgentDecision", back_populates="lead")