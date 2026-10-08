import uuid
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Website(Base):
    """Represents a company's website tracked by Website Intelligence."""
    __tablename__ = 'websites'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, unique=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='pending')
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    crawl_count: Mapped[int] = mapped_column(default=0)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        'metadata', JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    company: Mapped['Company'] = relationship('Company', backref='website')
    pages: Mapped[List['WebsitePage']] = relationship(
        'WebsitePage', back_populates='website', cascade='all, delete-orphan'
    )
    intelligence: Mapped[Optional['CompanyIntelligence']] = relationship(
        'CompanyIntelligence', back_populates='website', uselist=False,
        cascade='all, delete-orphan'
    )
