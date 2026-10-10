from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import EventService
from app.schemas.event_schema import (
    EventCreate, EventResponse, PinVerifyRequest, EventStatusUpdate, MenuItemCreate, MenuItemResponse, EventListItemResponse
)

router = APIRouter(prefix="/api/events", tags=["Events"])

@router.get("", response_model=List[EventListItemResponse])
def list_events(db: Session = Depends(get_db)):
    """등록된 모든 이벤트 목록 및 통계 요약 조회"""
    events = EventService.get_all_events(db)
    return events

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(event_data: EventCreate, db: Session = Depends(get_db)):
    """새로운 단기 이벤트 개설"""
    new_event = EventService.create_event(db, event_data)
    return new_event

@router.get("/{slug}", response_model=EventResponse)
def get_event(slug: str, db: Session = Depends(get_db)):
    """이벤트 정보 및 메뉴 목록 조회"""
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
    return event

@router.post("/{slug}/verify-pin")
def verify_pin(slug: str, payload: PinVerifyRequest, db: Session = Depends(get_db)):
    """관리자 PIN 일치 여부 검증"""
    valid = EventService.verify_event_pin(db, slug, payload.pin)
    if not valid:
        raise HTTPException(status_code=401, detail="관리자 핀코드가 올바르지 않습니다.")
    return {"valid": True, "message": "관리자 인증 성공"}

@router.patch("/{slug}/status", response_model=EventResponse)
def update_status(slug: str, payload: EventStatusUpdate, db: Session = Depends(get_db)):
    """이벤트 상태 변경 (OPEN/CLOSED)"""
    updated_event = EventService.update_event_status(db, slug, payload.pin, payload.status)
    return updated_event

@router.post("/{slug}/menus", response_model=EventResponse)
def update_menus(slug: str, pin: str, items: List[MenuItemCreate], db: Session = Depends(get_db)):
    """이벤트 메뉴 목록 갱신 (관리자 전용)"""
    updated_event = EventService.update_event_menus(db, slug, pin, items)
    return updated_event
