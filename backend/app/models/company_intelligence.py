import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class CompanyIntelligence(Base):
    """Structured business intelligence extracted from a company website.

    Each row stores the LLM-extracted intelligence for one company.
    Evidence (source URLs / text snippets) is preserved so downstream
    phases can trace every claim back to the actual website content.
    """
    __tablename__ = 'company_intelligence'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, unique=True
    )
    website_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey('websites.id', ondelete='SET NULL'), nullable=True
    )

    # Structured intelligence fields (all stored as JSON lists)
    services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    target_market: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    locations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    unique_selling_points: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    projects: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    contact_info: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    technology: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Evidence: maps each field to source URLs / text snippets
    evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Quality metadata
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pages_analyzed: Mapped[Optional[int]] = mapped_column(default=0)
    raw_llm_response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    extracted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company: Mapped['Company'] = relationship('Company', backref='intelligence')
    website: Mapped[Optional['Website']] = relationship(
        'Website', back_populates='intelligence'
    )
