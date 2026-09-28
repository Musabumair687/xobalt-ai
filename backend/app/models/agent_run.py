from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="running")  # running, success, failed
    
    input_params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    output_summary: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    error_log: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)