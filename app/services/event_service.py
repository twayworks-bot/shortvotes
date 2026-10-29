import hashlib
import random
import string
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.event import Event, MenuItem
from app.schemas.event_schema import EventCreate, MenuItemCreate

def hash_pin(pin: str) -> str:
    """PIN 코드를 SHA-256으로 해싱"""
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """입력된 PIN과 저장된 해시 비교"""
    return hash_pin(plain_pin) == hashed_pin

def generate_random_slug(length: int = 6) -> str:
    """충돌 없는 6자리 무작위 영숫자 슬러그 생성"""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

class EventService:
    @staticmethod
    def create_event(db: Session, event_data: EventCreate) -> Event:
        # 슬러그 결정: 입력되지 않았거나 공백이면 무작위 생성
        slug = (event_data.slug or "").strip().lower()
        if not slug:
            while True:
                candidate = generate_random_slug(6)
                if not db.query(Event).filter(Event.slug == candidate).first():
                    slug = candidate
                    break
        else:
            # 특수문자 및 공백 처리 (URL 안전 문자만 허용)
            slug = "".join(c for c in slug if c.isalnum() or c in "-_")
            if not slug:
                slug = generate_random_slug(6)
            # 중복 검사
            existing = db.query(Event).filter(Event.slug == slug).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미 사용 중인 URL 엔드포인트 이름(슬러그)입니다: '{slug}'"
                )

        new_event = Event(
            slug=slug,
            title=event_data.title.strip(),
            description=(event_data.description or "").strip(),
            pin_hash=hash_pin(event_data.pin.strip()),
            status="OPEN",
            enable_options=bool(event_data.enable_options)
        )
        db.add(new_event)
        db.flush()

        # 메뉴 항목 등록
        for idx, item in enumerate(event_data.menu_items):
            menu_item = MenuItem(
                event_id=new_event.id,
                name=item.name.strip(),
                category=(item.category or "기본").strip(),
                price=item.price or 0,
                display_order=item.display_order if item.display_order is not None else idx
            )
            db.add(menu_item)

        db.commit()
        db.refresh(new_event)
        return new_event

    @staticmethod
    def get_event_by_slug(db: Session, slug: str) -> Optional[Event]:
        return db.query(Event).filter(Event.slug == slug.strip().lower()).first()

    @staticmethod
    def verify_event_pin(db: Session, slug: str, pin: str) -> bool:
        event = EventService.get_event_by_slug(db, slug)
        if not event:
            return False
        return verify_pin(pin.strip(), event.pin_hash)

    @staticmethod
    def update_event_status(db: Session, slug: str, pin: str, new_status: str) -> Event:
        event = EventService.get_event_by_slug(db, slug)
        if not event:
            raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
        if not verify_pin(pin.strip(), event.pin_hash):
            raise HTTPException(status_code=403, detail="관리자 핀코드가 일치하지 않습니다.")

        if new_status.upper() not in ["OPEN", "CLOSED"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 이벤트 상태입니다.")

        event.status = new_status.upper()
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def update_event_options(db: Session, slug: str, pin: str, enable_options: bool) -> Event:
        event = EventService.get_event_by_slug(db, slug)
        if not event:
            raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
        if not verify_pin(pin.strip(), event.pin_hash):
            raise HTTPException(status_code=403, detail="관리자 핀코드가 일치하지 않습니다.")

        event.enable_options = bool(enable_options)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def update_event_menus(db: Session, slug: str, pin: str, items: List[MenuItemCreate]) -> Event:
        event = EventService.get_event_by_slug(db, slug)
        if not event:
            raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
        if not verify_pin(pin.strip(), event.pin_hash):
            raise HTTPException(status_code=403, detail="관리자 핀코드가 일치하지 않습니다.")

        # 기존 메뉴 삭제 후 신규 메뉴 등록
        db.query(MenuItem).filter(MenuItem.event_id == event.id).delete()
        for idx, item in enumerate(items):
            new_item = MenuItem(
                event_id=event.id,
                name=item.name.strip(),
                category=(item.category or "기본").strip(),
                price=item.price or 0,
                display_order=item.display_order if item.display_order is not None else idx
            )
            db.add(new_item)

        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_all_events(db: Session) -> List[dict]:
        """모든 이벤트를 최신순으로 조회하며 통계(메뉴수, 투표수, 참여자수)를 함께 산출"""
        events = db.query(Event).order_by(Event.created_at.desc()).all()
        result = []
        for evt in events:
            menu_count = len(evt.menu_items) if evt.menu_items else 0
            total_votes = len(evt.votes) if evt.votes else 0
            participant_count = sum(1 for u in evt.users if u.is_active) if evt.users else 0
            result.append({
                "id": evt.id,
                "slug": evt.slug,
                "title": evt.title,
                "description": evt.description or "",
                "status": evt.status,
                "enable_options": bool(getattr(evt, "enable_options", False)),
                "max_users": evt.max_users,
                "created_at": evt.created_at,
                "menu_count": menu_count,
                "total_votes": total_votes,
                "participant_count": participant_count
            })
        return result
