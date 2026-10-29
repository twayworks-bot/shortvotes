import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)  # Unique Key (브라우저 localStorage에 저장)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_name = Column(String(64), nullable=False)
    option_text = Column(String(128), nullable=True, default="")  # 참여자 기본/추가 옵션 기록 (예: hot, 샷추가)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="users")
    votes = relationship("Vote", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_event_active_user", "event_id", "user_name", "is_active"),
    )
