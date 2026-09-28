from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base

class SocialProfile(Base):
    __tablename__ = "social_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # 'linkedin', 'twitter'
    url: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    person: Mapped["Person"] = relationship("Person", back_populates="social_profiles")