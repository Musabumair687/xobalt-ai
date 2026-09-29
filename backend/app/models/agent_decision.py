import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base

class AgentDecision(Base):
    """
    AgentDecision model recording decisions made by an AI agent.
    """
    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    
    decision_type: Mapped[Optional[str]] = mapped_column(String(100))
    decision: Mapped[Optional[str]] = mapped_column(String(255))
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    agent_run: Mapped["AgentRun"] = relationship(back_populates="decisions")
    lead: Mapped[Optional["Lead"]] = relationship(back_populates="agent_decisions")