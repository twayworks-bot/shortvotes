from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.event import Event, MenuItem
from app.models.user import User
from app.models.vote import Vote
from app.config import settings
from app.schemas.vote_schema import EventResultsResponse, VoteItemResult

class VoteService:
    @staticmethod
    def submit_vote(
        db: Session,
        event: Event,
        unique_key: str,
        menu_item_id: str
    ) -> Dict:
        """메뉴 투표 등록/변경 (동일 메뉴 재클릭 시 취소 토글)"""
        if event.status == "CLOSED":
            raise HTTPException(status_code=400, detail="이미 마감된 이벤트입니다.")

        # 사용자 검증
        user = db.query(User).filter(
            User.id == unique_key.strip(),
            User.event_id == event.id,
            User.is_active == True
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="유효한 사용자 고유키가 아닙니다.")

        # 30일 만료 검사
        if (datetime.utcnow() - user.created_at) > timedelta(days=settings.USER_EXPIRY_DAYS):
            user.is_active = False
            db.commit()
            raise HTTPException(status_code=401, detail="고유키가 만료되었습니다. 다시 등록하세요.")

        # 메뉴 항목 검증
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == menu_item_id.strip(),
            MenuItem.event_id == event.id
        ).first()

        if not menu_item:
            raise HTTPException(status_code=404, detail="해당 메뉴 항목을 찾을 수 없습니다.")

        # 기존 투표 내역 확인
        existing_vote = db.query(Vote).filter(
            Vote.event_id == event.id,
            Vote.user_id == user.id
        ).first()

        user.last_seen_at = datetime.utcnow()

        if existing_vote:
            if existing_vote.menu_item_id == menu_item.id:
                # 동일 메뉴 클릭 시 취소
                db.delete(existing_vote)
                db.commit()
                return {
                    "action": "CANCELLED",
                    "message": f"'{menu_item.name}' 투표를 취소했습니다.",
                    "menu_item_id": None
                }
            else:
                # 다른 메뉴로 변경
                existing_vote.menu_item_id = menu_item.id
                existing_vote.voted_at = datetime.utcnow()
                db.commit()
                return {
                    "action": "UPDATED",
                    "message": f"'{menu_item.name}'(으)로 투표를 변경했습니다.",
                    "menu_item_id": menu_item.id
                }
        else:
            # 신규 투표 생성
            new_vote = Vote(
                event_id=event.id,
                user_id=user.id,
                menu_item_id=menu_item.id
            )
            db.add(new_vote)
            db.commit()
            return {
                "action": "VOTED",
                "message": f"'{menu_item.name}'에 투표했습니다.",
                "menu_item_id": menu_item.id
            }

    @staticmethod
    def cancel_vote(db: Session, event: Event, unique_key: str) -> Dict:
        """내 투표 취소"""
        user = db.query(User).filter(
            User.id == unique_key.strip(),
            User.event_id == event.id,
            User.is_active == True
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="유효한 사용자 고유키가 아닙니다.")

        db.query(Vote).filter(
            Vote.event_id == event.id,
            Vote.user_id == user.id
        ).delete()
        db.commit()
        return {"action": "CANCELLED", "message": "투표가 취소되었습니다."}

    @staticmethod
    def get_event_results(db: Session, event: Event, my_unique_key: Optional[str] = None) -> EventResultsResponse:
        """실시간 투표 결과 집계"""
        # 전체 유효 투표
        all_votes = db.query(Vote).filter(Vote.event_id == event.id).all()
        total_votes = len(all_votes)

        # 활성 참여자 수
        total_participants = db.query(User).filter(
            User.event_id == event.id,
            User.is_active == True
        ).count()

        # 메뉴별 집계 매핑
        vote_by_menu: Dict[str, List[str]] = {}
        for v in all_votes:
            if v.menu_item_id not in vote_by_menu:
                vote_by_menu[v.menu_item_id] = []
            if v.user:
                vote_by_menu[v.menu_item_id].append(v.user.user_name)

        # 내 투표 찾기
        my_vote_menu_id = None
        if my_unique_key:
            my_vote = db.query(Vote).filter(
                Vote.event_id == event.id,
                Vote.user_id == my_unique_key.strip()
            ).first()
            if my_vote:
                my_vote_menu_id = my_vote.menu_item_id

        # 메뉴 목록에 투표 집계 연결
        items_result: List[VoteItemResult] = []
        for menu in event.menu_items:
            voters = vote_by_menu.get(menu.id, [])
            count = len(voters)
            percentage = round((count / total_votes * 100), 1) if total_votes > 0 else 0.0
            items_result.append(VoteItemResult(
                menu_item_id=menu.id,
                name=menu.name,
                category=menu.category or "기본",
                price=menu.price or 0,
                vote_count=count,
                percentage=percentage,
                voters=voters
            ))

        return EventResultsResponse(
            event_id=event.id,
            slug=event.slug,
            title=event.title,
            status=event.status,
            total_votes=total_votes,
            total_participants=total_participants,
            items=items_result,
            my_vote_menu_id=my_vote_menu_id
        )
