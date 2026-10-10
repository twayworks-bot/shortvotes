from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category: Optional[str] = "기본"
    price: Optional[int] = 0
    display_order: Optional[int] = 0

class MenuItemResponse(BaseModel):
    id: str
    event_id: str
    name: str
    category: Optional[str] = "기본"
    price: Optional[int] = 0
    display_order: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = ""
    slug: Optional[str] = None
    pin: str = Field(..., min_length=4, max_length=16)
    menu_items: List[MenuItemCreate] = []

class EventResponse(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str] = ""
    status: str
    max_users: int
    created_at: datetime
    menu_items: List[MenuItemResponse] = []

    class Config:
        from_attributes = True

class PinVerifyRequest(BaseModel):
    pin: str

class EventStatusUpdate(BaseModel):
    pin: str
    status: str  # OPEN, CLOSED

class EventListItemResponse(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str] = ""
    status: str
    max_users: int
    created_at: datetime
    menu_count: int = 0
    total_votes: int = 0
    participant_count: int = 0

    class Config:
        from_attributes = True

