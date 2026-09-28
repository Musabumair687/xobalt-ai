from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base

class IntentSignal(Base):
    __tablename__ = "intent_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)

    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'funding_round', 'hiring'
    score_impact: Mapped[float] = mapped_column(Float, default=10.0)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)