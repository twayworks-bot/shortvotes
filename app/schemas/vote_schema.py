from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class VoteSubmitRequest(BaseModel):
    unique_key: str
    menu_item_id: str
    option_text: Optional[str] = None

class VoteOptionUpdateRequest(BaseModel):
    unique_key: str
    option_text: str = ""

class VoteCancelRequest(BaseModel):
    unique_key: str

class VoteItemResult(BaseModel):
    menu_item_id: str
    name: str
    category: str
    price: int
    vote_count: int
    percentage: float
    voters: List[str] = []

class EventResultsResponse(BaseModel):
    event_id: str
    slug: str
    title: str
    status: str
    enable_options: bool = False
    total_votes: int
    total_participants: int
    items: List[VoteItemResult]
    my_vote_menu_id: Optional[str] = None
    my_vote_option: Optional[str] = ""
