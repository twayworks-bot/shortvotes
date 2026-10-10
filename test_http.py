import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("========== HTTP 엔드포인트 검증 시작 ==========")

    # 1. 루트 리다이렉트 (307 or 302 -> /shortvotes/)
    r = client.get("/", follow_redirects=False)
    print(f"GET / : status={r.status_code}, location={r.headers.get('location')}")
    assert r.status_code in [302, 307]
    assert "/shortvotes" in r.headers.get("location")

    # 2. 홈 페이지
    r = client.get("/shortvotes/")
    print(f"GET /shortvotes/ : status={r.status_code}")
    assert r.status_code == 200
    assert "ShortVotes" in r.text

    # 3. 신규 이벤트 생성 페이지
    r = client.get("/shortvotes/new")
    print(f"GET /shortvotes/new : status={r.status_code}")
    assert r.status_code == 200
    assert "새 투표 이벤트 개설" in r.text

    # 4. 이벤트 상세 페이지
    r = client.get("/shortvotes/friday-coffee-test")
    print(f"GET /shortvotes/friday-coffee-test : status={r.status_code}")
    assert r.status_code == 200
    assert "금요 커피 선호도 조사" in r.text

    # 5. 관리자 페이지
    r = client.get("/shortvotes/friday-coffee-test/admin")
    print(f"GET /shortvotes/friday-coffee-test/admin : status={r.status_code}")
    assert r.status_code == 200
    assert "관리자 핀코드 입력" in r.text

    # 6. 결과 API
    r = client.get("/shortvotes/api/events/friday-coffee-test/results")
    print(f"GET /shortvotes/api/events/friday-coffee-test/results : status={r.status_code}")
    assert r.status_code == 200
    data = r.json()
    print(f"   결과 데이터: total_votes={data['total_votes']}, total_participants={data['total_participants']}")
    assert "items" in data

    # 7. 전체 이벤트 카드 목록 페이지 검증
    r = client.get("/shortvotes/events")
    print(f"GET /shortvotes/events : status={r.status_code}")
    assert r.status_code == 200
    assert "전체 이벤트 목록 및 관리" in r.text

    # 8. 전체 이벤트 목록 API 검증
    r = client.get("/shortvotes/api/events")
    print(f"GET /shortvotes/api/events : status={r.status_code}")
    assert r.status_code == 200
    events_data = r.json()
    print(f"   등록된 이벤트 수: {len(events_data)}개")
    assert isinstance(events_data, list)
    assert len(events_data) > 0

    # 9. Docker 헬스체크 엔드포인트 검증 (/api/status 및 /shortvotes/api/status)
    r1 = client.get("/api/status")
    print(f"GET /api/status : status={r1.status_code}, data={r1.json()}")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"

    r2 = client.get("/shortvotes/api/status")
    print(f"GET /shortvotes/api/status : status={r2.status_code}, data={r2.json()}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"

    print("\n🎉 모든 HTTP 엔드포인트, 템플릿 렌더링, Docker 헬스체크 검증이 100% 성공하였습니다!")

if __name__ == "__main__":
    test_endpoints()
