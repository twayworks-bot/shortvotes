import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Vote(Base):
    __tablename__ = "votes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(String(36), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    voted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 1인 1선택 제약조건
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_user_vote"),
    )

    # Relationships
    event = relationship("Event", back_populates="votes")
    user = relationship("User", back_populates="votes")
    menu_item = relationship("MenuItem", back_populates="votes")
