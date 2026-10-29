import asyncio
import os
import sys

# Windows 콘솔 한글/이모지 출력 인코딩 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.services.event_service import EventService
from app.services.user_service import UserService
from app.services.vote_service import VoteService
from app.services.gemini_service import GeminiService
from app.schemas.event_schema import EventCreate, MenuItemCreate

async def run_tests():
    print("========== [1] DB 및 테이블 초기화 ==========")
    init_db()
    db: Session = SessionLocal()

    try:
        print("\n========== [2] 이벤트 생성 테스트 ==========")
        event_data = EventCreate(
            title="금요 커피 선호도 조사",
            description="금요일 점심 회식 후 마실 커피를 골라주세요!",
            slug="friday-coffee-test",
            pin="1234",
            enable_options=True,
            menu_items=[
                MenuItemCreate(name="아이스 아메리카노", category="커피", price=4500, display_order=0),
                MenuItemCreate(name="카페라떼", category="커피", price=5000, display_order=1),
                MenuItemCreate(name="자몽허니블랙티", category="에이드/티", price=5800, display_order=2),
            ]
        )
        # 기존 테스트 데이터 정리
        existing = EventService.get_event_by_slug(db, "friday-coffee-test")
        if existing:
            db.delete(existing)
            db.commit()

        event = EventService.create_event(db, event_data)
        print(f"✅ 이벤트 생성 성공! ID: {event.id}, Slug: {event.slug}, 메뉴 개수: {len(event.menu_items)}")
        assert event.slug == "friday-coffee-test"
        assert len(event.menu_items) == 3

        print("\n========== [3] 무작위 슬러그 자동 생성 테스트 ==========")
        random_event_data = EventCreate(
            title="무작위 슬러그 이벤트",
            pin="9999",
            menu_items=[MenuItemCreate(name="녹차", price=3000)]
        )
        rand_event = EventService.create_event(db, random_event_data)
        print(f"✅ 무작위 슬러그 자동 발급 성공: {rand_event.slug} (길이: {len(rand_event.slug)})")
        assert len(rand_event.slug) == 6

        print("\n========== [4] 사용자 식별 및 충돌 방지 테스트 ==========")
        # 4-1. 신규 사용자 등록
        id_res1 = UserService.identify_or_register(db, event, unique_key=None, user_name="김철수")
        print(f"✅ 신규 사용자 등록: status={id_res1.status}, unique_key={id_res1.unique_key}, 이름={id_res1.user.user_name}")
        assert id_res1.status == "VALID"
        user1_key = id_res1.unique_key

        # 4-2. 발급된 키로 재방문 식별
        id_res2 = UserService.identify_or_register(db, event, unique_key=user1_key)
        print(f"✅ 재방문 자동 식별: status={id_res2.status}, 이름={id_res2.user.user_name}")
        assert id_res2.status == "VALID"

        # 4-3. 키 없는 상태에서 동일 이름 제출 (충돌 발생 테스트)
        id_res3 = UserService.identify_or_register(db, event, unique_key=None, user_name="김철수")
        print(f"✅ 이름 충돌 감지: status={id_res3.status}, 메시지={id_res3.message}")
        assert id_res3.status == "NAME_EXISTS"

        # 4-4. 충돌 후 강제 리셋 등록
        reset_user = UserService.register_user(db, event, user_name="김철수", force_reset=True)
        print(f"✅ 기존 사용자 리셋 후 새 키 발급: ID={reset_user.id}, 이름={reset_user.user_name}")
        assert reset_user.id != user1_key
        user1_key = reset_user.id

        print("\n========== [5] 투표 및 실시간 집계 테스트 ==========")
        menu_items = event.menu_items
        menu1 = menu_items[0]
        menu2 = menu_items[1]

        # 5-1. 메뉴 1에 투표
        v_res1 = VoteService.submit_vote(db, event, user1_key, menu1.id)
        print(f"✅ 메뉴1 투표: {v_res1}")
        assert v_res1["action"] == "VOTED"

        # 5-2. 동일 메뉴 재클릭 (취소 토글)
        v_res2 = VoteService.submit_vote(db, event, user1_key, menu1.id)
        print(f"✅ 동일 메뉴 재클릭 (취소 토글): {v_res2}")
        assert v_res2["action"] == "CANCELLED"

        # 5-3. 메뉴 2에 재투표
        v_res3 = VoteService.submit_vote(db, event, user1_key, menu2.id)
        print(f"✅ 메뉴2 투표: {v_res3}")
        assert v_res3["action"] == "VOTED"

        # 5-4. 다른 사용자(이영희) 생성 후 메뉴2 투표 (옵션 포함: 'hot, 샷추가')
        user2_res = UserService.identify_or_register(db, event, unique_key=None, user_name="이영희")
        VoteService.submit_vote(db, event, user2_res.unique_key, menu2.id, option_text="hot, 샷추가")

        # 5-5. 김철수 옵션선택 저장 ('cold, 오트밀')
        opt_res = VoteService.update_vote_option(db, event, user1_key, "cold, 오트밀")
        print(f"✅ 김철수 옵션 저장: {opt_res}")
        assert opt_res["display_name"] == "김철수(cold, 오트밀)"

        # 5-6. 결과 집계 확인 ("이름(옵션)" 표시 검증)
        results = VoteService.get_event_results(db, event, my_unique_key=user1_key)
        print(f"✅ 결과 집계: 총 투표수={results.total_votes}, 참여자수={results.total_participants}")
        print(f"   내 투표 메뉴 ID: {results.my_vote_menu_id}, 내 옵션: {results.my_vote_option}")
        for item in results.items:
            print(f"   - {item.name}: {item.vote_count}표 ({item.percentage}%) / 투표자: {item.voters}")
        assert results.total_votes == 2
        assert results.my_vote_option == "cold, 오트밀"
        menu2_result = next(i for i in results.items if i.menu_item_id == menu2.id)
        assert "김철수(cold, 오트밀)" in menu2_result.voters
        assert "이영희(hot, 샷추가)" in menu2_result.voters

        print("\n========== [6] Gemini AI 텍스트 메뉴 오타 교정 테스트 ==========")
        test_raw_text = "아에리카노 4500\n카페라때 5000\n자몽허니블랙티이 5800"
        print(f"입력 텍스트:\n{test_raw_text}")
        ai_res = await GeminiService.extract_menu_from_text(test_raw_text)
        print(f"AI 응답 success: {ai_res.success}, 항목 수: {len(ai_res.items)}")
        for it in ai_res.items:
            print(f"   * [{it.category}] {it.name} - {it.price}원")
        assert ai_res.success is True
        assert len(ai_res.items) >= 3

        print("\n🎉 모든 단위 및 비즈니스 로직 테스트가 100% 성공하였습니다!")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
