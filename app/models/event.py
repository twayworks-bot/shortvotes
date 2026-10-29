import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    pin_hash = Column(String(128), nullable=False)  # 4~6자리 PIN 해시
    status = Column(String(16), nullable=False, default="OPEN")  # OPEN, CLOSED
    enable_options = Column(Boolean, nullable=False, default=True)  # 추가 옵션(hot/cold, 오트밀, 샷추가 등) 입력 활성화 여부
    max_users = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    menu_items = relationship("MenuItem", back_populates="event", cascade="all, delete-orphan", order_by="MenuItem.display_order")
    users = relationship("User", back_populates="event", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="event", cascade="all, delete-orphan")

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=True, default="기본")
    price = Column(Integer, nullable=True, default=0)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="menu_items")
    votes = relationship("Vote", back_populates="menu_item", cascade="all, delete-orphan")
