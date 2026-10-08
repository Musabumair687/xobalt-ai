import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class WebsitePage(Base):
    """Represents a single page fetched from a company website."""
    __tablename__ = 'website_pages'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    website_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('websites.id', ondelete='CASCADE'), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
    )  # home, about, services, contact, projects, other
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='pending')
    crawled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    website: Mapped['Website'] = relationship('Website', back_populates='pages')
