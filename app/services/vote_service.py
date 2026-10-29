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
        menu_item_id: str,
        option_text: Optional[str] = None
    ) -> Dict:
        """메뉴 투표 등록/변경 (동일 메뉴 재클릭 시 취소 토글, 옵션 변경 시 옵션 갱신)"""
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

        enable_opts = bool(getattr(event, "enable_options", False))
        if option_text is not None:
            clean_opt = option_text.strip()[:128]
            if enable_opts:
                user.option_text = clean_opt
        else:
            clean_opt = (user.option_text or "").strip() if enable_opts else ""

        effective_opt = clean_opt if enable_opts else ""

        if existing_vote:
            if existing_vote.menu_item_id == menu_item.id:
                existing_opt = (existing_vote.option_text or "").strip()
                if enable_opts and option_text is not None and effective_opt != existing_opt:
                    existing_vote.option_text = effective_opt
                    existing_vote.voted_at = datetime.utcnow()
                    db.commit()
                    return {
                        "action": "UPDATED",
                        "message": f"'{menu_item.name}' 옵션이 '{effective_opt}'(으)로 변경되었습니다." if effective_opt else f"'{menu_item.name}' 옵션이 해제되었습니다.",
                        "menu_item_id": menu_item.id,
                        "option_text": effective_opt
                    }
                # 동일 메뉴 클릭 시 취소
                db.delete(existing_vote)
                db.commit()
                return {
                    "action": "CANCELLED",
                    "message": f"'{menu_item.name}' 투표를 취소했습니다.",
                    "menu_item_id": None,
                    "option_text": effective_opt
                }
            else:
                # 다른 메뉴로 변경
                existing_vote.menu_item_id = menu_item.id
                existing_vote.option_text = effective_opt
                existing_vote.voted_at = datetime.utcnow()
                db.commit()
                opt_suffix = f" ({effective_opt})" if effective_opt else ""
                return {
                    "action": "UPDATED",
                    "message": f"'{menu_item.name}'{opt_suffix}(으)로 투표를 변경했습니다.",
                    "menu_item_id": menu_item.id,
                    "option_text": effective_opt
                }
        else:
            # 신규 투표 생성
            new_vote = Vote(
                event_id=event.id,
                user_id=user.id,
                menu_item_id=menu_item.id,
                option_text=effective_opt
            )
            db.add(new_vote)
            db.commit()
            opt_suffix = f" ({effective_opt})" if effective_opt else ""
            return {
                "action": "VOTED",
                "message": f"'{menu_item.name}'{opt_suffix}에 투표했습니다.",
                "menu_item_id": menu_item.id,
                "option_text": effective_opt
            }

    @staticmethod
    def update_vote_option(
        db: Session,
        event: Event,
        unique_key: str,
        option_text: str
    ) -> Dict:
        """참여자 추가 옵션(hot/cold, 오트밀, 샷추가 등) 기록 및 저장"""
        if event.status == "CLOSED":
            raise HTTPException(status_code=400, detail="이미 마감된 이벤트입니다.")

        if not getattr(event, "enable_options", False):
            raise HTTPException(status_code=400, detail="이 이벤트는 추가 옵션 기능이 활성화되어 있지 않습니다.")

        user = db.query(User).filter(
            User.id == unique_key.strip(),
            User.event_id == event.id,
            User.is_active == True
        ).first()

        if not user:
            raise HTTPException(status_code=401, detail="유효한 사용자 고유키가 아닙니다.")

        if (datetime.utcnow() - user.created_at) > timedelta(days=settings.USER_EXPIRY_DAYS):
            user.is_active = False
            db.commit()
            raise HTTPException(status_code=401, detail="고유키가 만료되었습니다. 다시 등록하세요.")

        clean_opt = (option_text or "").strip()[:128]
        user.option_text = clean_opt
        user.last_seen_at = datetime.utcnow()

        existing_vote = db.query(Vote).filter(
            Vote.event_id == event.id,
            Vote.user_id == user.id
        ).first()

        if existing_vote:
            existing_vote.option_text = clean_opt

        db.commit()

        display_name = f"{user.user_name}({clean_opt})" if clean_opt else user.user_name
        msg = f"옵션이 저장되었습니다: {display_name}" if clean_opt else "추가 옵션이 초기화되었습니다."

        return {
            "action": "OPTION_UPDATED",
            "option_text": clean_opt,
            "display_name": display_name,
            "has_vote": existing_vote is not None,
            "menu_item_id": existing_vote.menu_item_id if existing_vote else None,
            "message": msg
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

        enable_opts = bool(getattr(event, "enable_options", False))

        # 메뉴별 집계 매핑
        vote_by_menu: Dict[str, List[str]] = {}
        for v in all_votes:
            if v.menu_item_id not in vote_by_menu:
                vote_by_menu[v.menu_item_id] = []
            if v.user:
                opt = (v.option_text if v.option_text is not None else (v.user.option_text or "")).strip()
                if enable_opts and opt:
                    voter_display = f"{v.user.user_name}({opt})"
                else:
                    voter_display = v.user.user_name
                vote_by_menu[v.menu_item_id].append(voter_display)

        # 내 투표 및 내 옵션 찾기
        my_vote_menu_id = None
        my_vote_option = ""
        if my_unique_key:
            clean_key = my_unique_key.strip()
            my_user = db.query(User).filter(
                User.event_id == event.id,
                User.id == clean_key
            ).first()
            if my_user and my_user.option_text:
                my_vote_option = my_user.option_text.strip()

            my_vote = db.query(Vote).filter(
                Vote.event_id == event.id,
                Vote.user_id == clean_key
            ).first()
            if my_vote:
                my_vote_menu_id = my_vote.menu_item_id
                if my_vote.option_text is not None:
                    my_vote_option = my_vote.option_text.strip()

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
            enable_options=enable_opts,
            total_votes=total_votes,
            total_participants=total_participants,
            items=items_result,
            my_vote_menu_id=my_vote_menu_id,
            my_vote_option=my_vote_option if enable_opts else ""
        )
