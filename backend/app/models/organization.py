import uuid
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import String, Boolean, Text, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Organization(Base):
    """Organization model for multi-tenancy."""
    __tablename__ = 'organizations'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    companies: Mapped[List["Company"]] = relationship("Company", back_populates="organization")
    persons: Mapped[List["Person"]] = relationship("Person", back_populates="organization")
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="organization")
    campaigns: Mapped[List["Campaign"]] = relationship("Campaign", back_populates="organization")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="organization")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="organization")
    agent_runs: Mapped[List["AgentRun"]] = relationship("AgentRun", back_populates="organization")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="organization")
    usage_records: Mapped[List["UsageRecord"]] = relationship("UsageRecord", back_populates="organization")
    billing_record: Mapped[Optional["BillingRecord"]] = relationship("BillingRecord", back_populates="organization", uselist=False)