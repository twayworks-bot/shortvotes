from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import EventService
from app.services.vote_service import VoteService
from app.schemas.vote_schema import (
    VoteSubmitRequest, VoteOptionUpdateRequest, VoteCancelRequest, EventResultsResponse
)

router = APIRouter(prefix="/api/events/{slug}", tags=["Votes"])

@router.post("/vote")
def submit_vote(slug: str, payload: VoteSubmitRequest, db: Session = Depends(get_db)):
    """
    메뉴 투표 등록/변경.
    - 동일 메뉴를 다시 클릭하면 투표가 취소(토글)됩니다.
    - 다른 메뉴를 클릭하면 기존 투표가 해당 메뉴로 변경됩니다.
    - option_text가 함께 전달되면 추가 옵션도 함께 저장됩니다.
    """
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    result = VoteService.submit_vote(
        db=db,
        event=event,
        unique_key=payload.unique_key,
        menu_item_id=payload.menu_item_id,
        option_text=payload.option_text
    )
    return result

@router.post("/vote/option")
@router.patch("/vote/option")
def update_vote_option(slug: str, payload: VoteOptionUpdateRequest, db: Session = Depends(get_db)):
    """참여자 선호 메뉴 추가 옵션(hot/cold, 오트밀, 샷추가 등) 기록 및 저장"""
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    result = VoteService.update_vote_option(
        db=db,
        event=event,
        unique_key=payload.unique_key,
        option_text=payload.option_text
    )
    return result

@router.delete("/vote")
def cancel_vote(slug: str, payload: VoteCancelRequest, db: Session = Depends(get_db)):
    """내 투표 취소"""
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    result = VoteService.cancel_vote(
        db=db,
        event=event,
        unique_key=payload.unique_key
    )
    return result

@router.get("/results", response_model=EventResultsResponse)
def get_results(
    slug: str,
    unique_key: Optional[str] = Query(None, description="내 투표 여부 확인을 위한 고유키"),
    db: Session = Depends(get_db)
):
    """실시간 투표 결과 집계 조회"""
    event = EventService.get_event_by_slug(db, slug)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")

    results = VoteService.get_event_results(db, event, my_unique_key=unique_key)
    return results
