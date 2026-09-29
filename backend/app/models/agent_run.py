import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base

class AgentRun(Base):
    """
    AgentRun model tracking AI background tasks.
    """
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    agent_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default='running')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    input_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    leads_processed: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="agent_runs")
    decisions: Mapped[list["AgentDecision"]] = relationship(back_populates="agent_run", cascade="all, delete-orphan")