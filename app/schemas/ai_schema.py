from typing import List, Optional
from pydantic import BaseModel

class ExtractedMenuItem(BaseModel):
    name: str
    price: Optional[int] = 0
    category: Optional[str] = "기본"

class TextMenuParseRequest(BaseModel):
    raw_text: str
    existing_menus: Optional[List[str]] = []

class AIMenuParseResponse(BaseModel):
    success: bool
    items: List[ExtractedMenuItem]
    raw_response: Optional[str] = None
    message: Optional[str] = ""
