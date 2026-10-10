from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import EventService
from app.services.user_service import UserService
from app.schemas.user_schema import (
    UserIdentifyRequest, UserRegisterRequest, IdentifyResult, UserResponse
)

router = APIRouter(prefix="/api/events/{slug}/users", tags=["Users"])

@router.post("/identify", response_model=IdentifyResult)
def identify_user(slug: str, payload: UserIdentifyRequest, db: Session = Depends(get_db)):
    """
    브라우저의 unique_key 또는 사용자 이름으로 현재 사용자 식별.
    - unique_key 유효: status="VALID"
    - unique_key 30일 만료: status="EXPIRED"
    - unique_key 없음 + 서버에 동일 이름 존재: status="NAME_EXISTS" (충돌)
    - unique_key 없음 + 신규 이름: status="VALID" (신규 키 발급 완료)
    """
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    result = UserService.identify_or_register(
        db=db,
        event=event,
        unique_key=payload.unique_key,
        user_name=payload.user_name
    )
    return result

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(slug: str, payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    신규 사용자 등록 또는 기존 사용자 리셋 후 등록.
    - force_reset=True일 경우 기존 동일 이름 사용자의 세션을 만료시키고 신규 키를 발급합니다.
    """
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    user = UserService.register_user(
        db=db,
        event=event,
        user_name=payload.user_name,
        force_reset=payload.force_reset or False
    )
    return user
