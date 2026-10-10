from fastapi import APIRouter
from app.api.routes_ai import router as ai_router
from app.api.routes_event import router as event_router
from app.api.routes_user import router as user_router
from app.api.routes_vote import router as vote_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(event_router)
api_router.include_router(user_router)
api_router.include_router(vote_router)

__all__ = ["api_router"]
