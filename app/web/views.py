from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import EventService
from app.config import settings

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

web_router = APIRouter()

@web_router.get("/")
def index_page(request: Request):
    """메인 랜딩 페이지"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"prefix": settings.PREFIX}
    )

@web_router.get("/new")
def new_event_page(request: Request):
    """새 이벤트 생성 및 메뉴 등록 위저드"""
    return templates.TemplateResponse(
        request=request,
        name="event_new.html",
        context={"prefix": settings.PREFIX}
    )

@web_router.get("/events")
def event_list_page(request: Request, db: Session = Depends(get_db)):
    """전체 이벤트 카드 리스트 및 통합 관리 페이지"""
    events = EventService.get_all_events(db)
    return templates.TemplateResponse(
        request=request,
        name="event_list.html",
        context={
            "events": events,
            "prefix": settings.PREFIX
        }
    )

@web_router.get("/{slug}")
def event_view_page(slug: str, request: Request, db: Session = Depends(get_db)):
    """일반 사용자 투표 및 실시간 현황 화면"""
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="존재하지 않는 이벤트입니다.")

    return templates.TemplateResponse(
        request=request,
        name="event_view.html",
        context={
            "event": event,
            "prefix": settings.PREFIX
        }
    )

@web_router.get("/{slug}/admin")
def event_admin_page(slug: str, request: Request, db: Session = Depends(get_db)):
    """이벤트 관리자 대시보드"""
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="존재하지 않는 이벤트입니다.")

    return templates.TemplateResponse(
        request=request,
        name="event_admin.html",
        context={
            "event": event,
            "prefix": settings.PREFIX
        }
    )
