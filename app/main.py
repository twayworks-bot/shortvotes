from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.api import api_router
from app.web import web_router
from app.web.views import templates

# 가격 천단위 콤마 필터 등록
def format_price(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

templates.env.filters["format_price"] = format_price

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 SQLite 데이터베이스 및 테이블 초기화
    init_db()
    yield

app = FastAPI(
    title="ShortVotes API",
    description="초경량 단기 이벤트 선호조사 및 투표 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# PREFIX 경로 정규화
prefix_path = f"/{settings.PREFIX}" if settings.PREFIX else ""

# 1. 정적 파일 서빙: {prefix_path}/static -> app/static
static_dir = Path(__file__).resolve().parent / "static"
app.mount(f"{prefix_path}/static", StaticFiles(directory=str(static_dir)), name="static")

# 2. 웹 라우터 마운트: {prefix_path}
app.include_router(web_router, prefix=prefix_path)

# 3. API 라우터 마운트: {prefix_path} (하위 라우터들이 자체 /api 접두사 보유)
app.include_router(api_router, prefix=prefix_path)

# 4. 컨테이너 헬스체크 엔드포인트 (/api/status 및 {prefix_path}/api/status)
def healthcheck_handler():
    return JSONResponse(content={
        "status": "ok",
        "service": "shortvotes",
        "prefix": settings.PREFIX,
        "database_url": settings.DATABASE_URL
    })

# 루트 기준 /api/status 및 prefix 기준 {prefix_path}/api/status 둘 다 등록
app.add_api_route("/api/status", healthcheck_handler, methods=["GET"], tags=["Health"])
if prefix_path:
    app.add_api_route(f"{prefix_path}/api/status", healthcheck_handler, methods=["GET"], tags=["Health"])

# 5. 루트 경로 접속 시 {prefix_path}로 자동 리다이렉트 (prefix가 있는 경우)
if prefix_path:
    @app.get("/")
    def root_redirect():
        return RedirectResponse(url=f"{prefix_path}/")
