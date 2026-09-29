import uuid
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Person(Base):
    """Person model representing a contact or prospect."""
    __tablename__ = 'persons'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('companies.id', ondelete='SET NULL'), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="persons")
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="people")
    contacts: Mapped[List["Contact"]] = relationship("Contact", back_populates="person")
    social_profiles: Mapped[List["SocialProfile"]] = relationship("SocialProfile", back_populates="person")
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="person")