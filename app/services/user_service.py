from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.event import Event
from app.models.user import User
from app.models.vote import Vote
from app.config import settings
from app.schemas.user_schema import IdentifyResult, UserResponse

class UserService:
    @staticmethod
    def identify_or_register(
        db: Session,
        event: Event,
        unique_key: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> IdentifyResult:
        """
        사용자 고유키 검증 또는 식별 시도
        """
        now = datetime.utcnow()
        expiry_delta = timedelta(days=settings.USER_EXPIRY_DAYS)

        # 1. 브라우저에 unique_key가 있는 경우
        if unique_key:
            user = db.query(User).filter(
                User.id == unique_key.strip(),
                User.event_id == event.id
            ).first()

            if not user or not user.is_active:
                return IdentifyResult(
                    status="NOT_FOUND",
                    message="등록된 사용자 정보를 찾을 수 없습니다. 이름을 입력하여 새로 등록하세요."
                )

            # 30일 유효기간 만료 검사
            if (now - user.created_at) > expiry_delta:
                user.is_active = False
                db.commit()
                return IdentifyResult(
                    status="EXPIRED",
                    message="30일 유효기간이 만료되었습니다. 새 고유키를 발급받아야 합니다."
                )

            # 세션 활동시간 갱신
            user.last_seen_at = now
            db.commit()
            db.refresh(user)

            return IdentifyResult(
                status="VALID",
                message="인증 성공",
                user=UserResponse.model_validate(user),
                unique_key=user.id
            )

        # 2. 브라우저에 unique_key가 없고 user_name만 제공된 경우
        if not user_name or not user_name.strip():
            return IdentifyResult(
                status="NEED_NAME",
                message="사용자 이름을 입력해 주세요."
            )

        cleaned_name = user_name.strip()

        # 기존 서버에 동일 이름이 이미 등록되어 있는지 확인
        existing_user = db.query(User).filter(
            User.event_id == event.id,
            User.user_name == cleaned_name,
            User.is_active == True
        ).first()

        if existing_user:
            # 유효기간 확인 (만약 만료되었으면 자동 비활성화)
            if (now - existing_user.created_at) > expiry_delta:
                existing_user.is_active = False
                db.commit()
            else:
                # 활성화된 사용자가 이미 서버에 있으므로 충돌 발생 -> 새 이름 or 리셋 요청
                return IdentifyResult(
                    status="NAME_EXISTS",
                    message=f"'{cleaned_name}' 이름이 이미 등록되어 있습니다. 이름을 변경하거나 기존 사용자를 리셋하여 등록하시겠습니까?",
                    user=UserResponse.model_validate(existing_user)
                )

        # 참여 인원 100명 제한 검사
        active_count = db.query(User).filter(
            User.event_id == event.id,
            User.is_active == True
        ).count()

        if active_count >= settings.MAX_USERS_PER_EVENT:
            return IdentifyResult(
                status="LIMIT_EXCEEDED",
                message=f"해당 이벤트의 최대 참여 인원({settings.MAX_USERS_PER_EVENT}명)을 초과하였습니다."
            )

        # 신규 사용자 등록
        new_user = User(
            event_id=event.id,
            user_name=cleaned_name,
            created_at=now,
            last_seen_at=now,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return IdentifyResult(
            status="VALID",
            message="신규 사용자 등록 성공",
            user=UserResponse.model_validate(new_user),
            unique_key=new_user.id
        )

    @staticmethod
    def register_user(
        db: Session,
        event: Event,
        user_name: str,
        force_reset: bool = False
    ) -> User:
        """
        사용자 신규 등록 또는 강제 리셋 후 등록
        """
        now = datetime.utcnow()
        cleaned_name = user_name.strip()
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="사용자 이름을 입력해야 합니다.")

        # 동일 이름 활성 사용자 검색
        existing_user = db.query(User).filter(
            User.event_id == event.id,
            User.user_name == cleaned_name,
            User.is_active == True
        ).first()

        if existing_user:
            if not force_reset:
                raise HTTPException(
                    status_code=409,
                    detail=f"'{cleaned_name}' 이름이 이미 존재합니다. force_reset=True로 기존 유저를 리셋하거나 다른 이름을 입력하세요."
                )
            # 기존 사용자 비활성화 및 기존 투표 내역 삭제
            existing_user.is_active = False
            db.query(Vote).filter(
                Vote.event_id == event.id,
                Vote.user_id == existing_user.id
            ).delete()
            db.commit()

        # 인원수 검사
        active_count = db.query(User).filter(
            User.event_id == event.id,
            User.is_active == True
        ).count()

        if active_count >= settings.MAX_USERS_PER_EVENT:
            raise HTTPException(
                status_code=400,
                detail=f"이벤트 최대 참여 인원({settings.MAX_USERS_PER_EVENT}명)을 초과했습니다."
            )

        new_user = User(
            event_id=event.id,
            user_name=cleaned_name,
            created_at=now,
            last_seen_at=now,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
