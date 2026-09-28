from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'email', 'phone'
    value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    person: Mapped["Person"] = relationship("Person", back_populates="contacts")