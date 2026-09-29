import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base

class BillingRecord(Base):
    """
    BillingRecord model tracking subscription details for an organization.
    """
    __tablename__ = "billing_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    plan: Mapped[str] = mapped_column(String(100), default='free')
    status: Mapped[str] = mapped_column(String(50), default='active')
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255))
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    seats_allowed: Mapped[int] = mapped_column(Integer, default=1)
    seats_used: Mapped[int] = mapped_column(Integer, default=1)
    monthly_email_limit: Mapped[int] = mapped_column(Integer, default=100)
    monthly_lead_limit: Mapped[int] = mapped_column(Integer, default=50)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, name='metadata')

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="billing_record")
