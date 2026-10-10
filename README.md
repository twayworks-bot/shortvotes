# 🗳️ ShortVotes - 초경량 무인증 단기 이벤트 선호조사 시스템

> **ShortVotes**는 회식, 동아리 모임, 팀 워크숍 등 며칠 내 신속하게 투표를 완료해야 하는 임시성 단기 이벤트를 위해 제작된 **초경량 무인증 웹 투표 및 선호조사 솔루션**입니다.  
> 복잡한 회원가입이나 소셜 로그인 없이 **사용자 이름**과 브라우저 **Local Storage 고유키(Unique Key)**를 기반으로 100명 내외 규모의 참여자를 안전하고 간편하게 식별합니다.

---

## 📌 목차
1. [프로젝트 목적](#-프로젝트-목적)
2. [핵심 기능 설명](#-핵심-기능-설명)
3. [사용 방법 (User Guide)](#-사용-방법-user-guide)
4. [시스템 구현 내용 및 아키텍처](#-시스템-구현-내용-및-아키텍처)
5. [환경 변수 설정 (.env)](#-환경-변수-설정-env)
6. [로컬 실행 방법](#-로컬-실행-방법)
7. [Docker 컨테이너 배포 방법](#-docker-컨테이너-배포-방법)
8. [프로젝트 디렉터리 구조](#-프로젝트-디렉터리-구조)

---

## 🎯 프로젝트 목적

- **Zero-Friction 참여 경험**: 비밀번호, 본인인증, 이메일 가입 절차 없이 이름 입력 한 번으로 즉시 투표 참여.
- **Gemini AI 기반 초고속 메뉴 등록**: 카페 메뉴판 사진(영수증/간판)을 올리거나 텍스트를 붙여넣으면 Gemini 2.5 Flash가 오탈자를 자동 교정하여 10초 만에 투표 항목 생성.
- **안전한 단기 세션 관리**: 브라우저 Local Storage에 Unique Key(UUID)를 저장하여 재방문 시 동일인 자동 판별 및 30일(1개월) 자동 만료 정책 적용.
- **가벼운 운영 비용**: 별도의 대형 DB 서버 없이 SQLite(WAL 모드) 및 단일 Docker 컨테이너로 즉시 구동.

---

## ✨ 핵심 기능 설명

### 1. 🤖 Gemini 2.5 Flash 기반 메뉴 자동 추출 및 오타 교정
- **이미지 OCR 모드**: 메뉴판 사진(JPEG, PNG, WEBP)을 업로드하면 Gemini 멀티모달 API가 메뉴명, 가격, 카테고리를 자동 파싱하고 오탈자를 교정합니다.
  - *흐름*: `이미지 업로드 > 메뉴 텍스트 추출 > 오타 교정 > 미리보기 테이블 편집 > 최종 등록`
- **텍스트 입력 모드**: 사용자가 비정형 텍스트(예: `아에리카노 4500`, `카페라때 5000`)를 대충 입력해도 대한민국 표준 명칭(`아메리카노`, `카페라떼`)으로 자동 교정합니다.
  - *흐름*: `텍스트 입력 > 오타 교정 및 정형화 > 미리보기 테이블 편집 > 최종 등록`
- **관리자 검토 테이블**: AI가 파싱한 결과를 확인하고, 실시간으로 행 추가/수정/삭제 가능.

### 2. 🔑 무인증 식별 및 로컬 스토리지 관리
- **동일인 자동 판별**: 브라우저의 `localStorage`에 고유 키(`UUID v4`)를 보관하여 재접속 시 로그인 없이 바로 내 투표 상태를 복원합니다.
- **이름 충돌 방지 (Conflict Resolution)**: 새 기기나 시크릿 모드에서 이미 등록된 이름을 입력했을 때, 다음 두 가지 선택지를 모달로 제공합니다:
  - ✏️ **[다른 이름으로 변경]**: 기존 사용자 데이터를 보존하고 새 닉네임으로 등록.
  - 🔄 **[기존 사용자 리셋 후 내가 이어받기]**: 이전 세션을 만료시키고 현재 기기로 소유권을 이어받아 투표 초기화/재참여.
- **30일 자동 만료**: 보안 및 데이터 위생을 위해 접속 후 30일이 지난 Unique Key는 무효화되어 신규 발급을 유도합니다.
- **100명 인원 제한**: 단기 이벤트의 안정성을 위해 이벤트당 최대 100명 내외로 참여 인원을 관리합니다.

### 3. 📊 원클릭 투표 및 실시간 결과 집계
- **원클릭 투표 인터랙션**: 메뉴 카드 클릭 시 내 투표가 즉각 반영되며, 같은 메뉴를 다시 누르면 취소(토글), 다른 메뉴를 누르면 변경됩니다.
- **실시간 선호도 차트**: 메뉴별 득표수, 득표율 프로그레스 바, 선택한 사람들의 이름 명단을 시각적으로 노출합니다.
- **내 선택 강조**: 내가 투표한 항목에는 `내 선택` 뱃지와 시각적 하이라이트가 적용됩니다.

### 4. 🛡️ 핀코드(PIN) 기반 관리자 모드
- **투표 상태 제어**: 4자리 이상 핀코드로 인증 후 언제든지 투표를 **마감(CLOSE)**하거나 **재개(OPEN)**할 수 있습니다.
- **주문 취합 도구**:
  - 📋 **주문서 텍스트 복사**: 카페 카운터나 메신저에 전달할 수 있는 요약 텍스트(`아메리카노: 5잔 (홍길동, ...)`) 원클릭 복사.
  - 📑 **CSV 다운로드**: 엑셀 호환 UTF-8 BOM 인코딩의 결과 데이터 다운로드.

### 5. 🗂️ 전체 이벤트 카드 목록 및 관리 뷰
- 메인 시작 페이지의 **[전체 이벤트 보기 및 관리]** 버튼을 통해 개설된 모든 이벤트를 카드 그리드로 탐색.
- 실시간 이벤트 검색(제목, 슬러그), 참여 통계(메뉴수, 투표수, 참여자수), 바로가기 버튼 제공.

---

## 📖 사용 방법 (User Guide)

### 👑 관리자 (이벤트 주최자)
1. 메인 홈(`http://localhost:5000/shortvotes/`)에서 **[새 투표 이벤트 만들기]** 클릭.
2. 이벤트 제목, 원하는 URL 슬러그(미입력 시 6자리 랜덤 생성), 관리자 PIN(4자리 이상) 입력.
3. **메뉴 등록**:
   - 메뉴판 사진을 드래그앤드롭하여 **[AI로 메뉴 추출 및 오타 교정]** 클릭, 또는
   - 메뉴 텍스트를 붙여넣고 **[AI 오타 교정 및 목록 변환]** 클릭.
4. 미리보기 테이블에서 메뉴와 가격을 확인/수정 후 **[이벤트 개설 및 링크 생성 완료]** 클릭.
5. 생성된 전용 링크(예: `http://localhost:5000/shortvotes/friday-coffee`)를 단체 채팅방에 공유!
6. 투표가 끝나면 `/admin` 페이지에서 핀코드를 입력하고 **투표 마감** 후 **주문서 복사** 또는 **CSV 다운로드**.

### 🙋 일반 사용자 (투표 참여자)
1. 공유받은 이벤트 URL 링크에 접속.
2. 이름 입력 창이 뜨면 본인 이름(예: `홍길동`) 입력 후 시작.
   - *동일 이름이 이미 존재하는 경우 [이름 변경] 또는 [리셋 후 이어받기] 선택.*
3. 마음에 드는 메뉴 카드를 클릭하면 투표 완료! (동일 카드 재클릭 시 취소).
4. **[투표 결과 현황]** 탭에서 다른 동료들이 무엇을 골랐는지 실시간 확인.

---

## 🏗️ 시스템 구현 내용 및 아키텍처

- **백엔드**: Python 3.10+ / FastAPI / Uvicorn (포트 `5000`, Base URL Prefix `/shortvotes`)
- **데이터베이스**: SQLite3 (동시성 향상을 위한 **WAL 모드** 및 복합 인덱스 적용)
- **AI 멀티모달 파이프라인**: Google Gemini 2.5 Flash (`google-generativeai`)
- **프론트엔드**: Jinja2 SSR + TailwindCSS CDN + Vanilla JS (빌드 도구 없는 초경량 반응형 SPA 경험)
- **클라이언트 식별**: 브라우저 `localStorage` 기반 식별자(`shortvotes_user_{slug}`)

---

## ⚙️ 환경 변수 설정 (.env)

프로젝트 루트의 `.env` 파일에 다음 환경값을 지정합니다:

```ini
# Gemini API 환경 설정 (필수)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL_NAME=gemini-2.5-flash
GEMINI_API_MAX_TOKENS=1240000

# 웹 서비스 기본 설정 (선택 사항)
DEFAULT_PREFIX=/shortvotes
PORT=5000
HOST=0.0.0.0

# 데이터베이스 저장 경로 (Docker 볼륨 연동용)
DATA_DIR=./data
```

---

## 💻 로컬 실행 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
python run.py
```
> 서버가 실행되면 기본적으로 `http://localhost:5000/shortvotes/`로 접속할 수 있으며,  
> 루트 주소(`http://localhost:5000/`)로 접속하더라도 자동으로 Prefix 주소로 리다이렉트됩니다.

### 3. 자동화 테스트 실행
```bash
# 백엔드 단위 및 비즈니스 로직, Gemini 실시간 오타 교정 테스트
python test_backend.py

# HTTP 엔드포인트 및 Docker 헬스체크 검증
python test_http.py
```

---

## 🐳 Docker 컨테이너 배포 방법

이 프로젝트는 프로덕션 컨테이너 환경에서 **Persistent Volume**과 **동적 Base URL Prefix**, **자동 헬스체크**를 지원하도록 설계되었습니다.

### 1. Dockerfile 빌드
```bash
docker build -t shortvotes:latest .
```

### 2. Docker 컨테이너 실행 (볼륨 마운트 및 환경변수 주입)
SQLite 데이터베이스를 호스트에 영구 보존하기 위해 `/data` 경로를 볼륨으로 마운트합니다:

```bash
docker run -d \
  --name shortvotes-app \
  -p 5000:5000 \
  -v shortvotes_data:/data \
  -e DEFAULT_PREFIX=/shortvotes \
  -e GEMINI_API_KEY="AIzaSy..." \
  shortvotes:latest
```

### 3. Docker Compose 사용 시 (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  shortvotes:
    build: .
    container_name: shortvotes-service
    ports:
      - "5000:5000"
    volumes:
      - shortvotes_db_data:/data
    environment:
      - DEFAULT_PREFIX=/shortvotes
      - GEMINI_API_KEY=AIzaSy...
      - GEMINI_MODEL_NAME=gemini-2.5-flash
    restart: unless-stopped

volumes:
  shortvotes_db_data:
```

### 4. 헬스체크 동작 원리
컨테이너에 설정된 `DEFAULT_PREFIX` 환경변수에 맞추어 30초마다 자동으로 상태를 점검합니다:
```bash
# 헬스체크 명령
python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"

# 상태 확인
docker ps
# STATUS 열에 "(healthy)" 표시 확인
```

---

## 📁 프로젝트 디렉터리 구조

```
shortVotes/
├── Dockerfile                 # Docker 컨테이너 빌드 명세서
├── .dockerignore              # Docker 빌드 제외 설정
├── .env                       # Gemini API 키 및 환경변수
├── README.md                  # 프로젝트 종합 가이드 문서 (본 문서)
├── GOAL.md                    # 프로젝트 전체 목표 및 구현 요약
├── requirements.txt           # Python 패키지 의존성 목록
├── main.py                    # Docker/Uvicorn 엔트리포인트 (main:app)
├── run.py                     # 로컬 실행 스크립트 (Port 5000)
├── test_backend.py            # 백엔드 단위/AI 테스트 스크립트
├── test_http.py               # HTTP 엔드포인트 및 헬스체크 테스트 스크립트
├── notes/                     # 설계 문서 및 개발 히스토리 누적 보관소
│   ├── requirement.md         # 상세 요구사항 정의서 (누적)
│   ├── SPECIFICATION.md       # 시스템 상세 사양서
│   ├── history.md             # 변경 히스토리 및 개발 요약
│   └── plan_202610101517.md   # MVP 정의 및 개발 로드맵
├── app/
│   ├── config.py              # 환경변수 로더 (DEFAULT_PREFIX, DATA_DIR 등)
│   ├── database.py            # SQLite WAL 연결 및 세션 관리
│   ├── main.py                # FastAPI 앱, 라우터 마운트, 헬스체크
│   ├── models/                # ORM 모델 (Event, MenuItem, User, Vote)
│   ├── schemas/               # Pydantic DTO 스키마
│   ├── services/              # 비즈니스 로직 (Gemini, Event, User, Vote)
│   ├── api/                   # REST API 엔드포인트 (AI, Event, User, Vote)
│   ├── web/                   # SSR 웹 뷰 라우터
│   ├── templates/             # Jinja2 HTML 템플릿
│   │   ├── base.html          # 공통 레이아웃 (헤더, 토스트)
│   │   ├── index.html         # 메인 시작 페이지
│   │   ├── event_list.html    # 전체 이벤트 카드 목록 및 관리 페이지
│   │   ├── event_new.html     # 이벤트 생성 및 AI 메뉴 등록 화면
│   │   ├── event_view.html    # 투표 참여 및 실시간 현황 화면
│   │   └── event_admin.html   # 관리자 대시보드 (마감, CSV)
│   └── static/                # 정적 에셋 (JS, CSS)
└── data/                      # SQLite DB 파일 저장 디렉터리
    └── shortvotes.db
```

---

## 📜 라이선스
본 프로젝트는 사내 행사 및 팀 모임을 위해 자유롭게 사용 및 수정할 수 있습니다.
