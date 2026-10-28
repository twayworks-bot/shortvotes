# -------------------------------------------------------------
# ShortVotes Dockerfile
# 초경량 단기 이벤트 선호조사 및 투표 웹 시스템
# -------------------------------------------------------------
FROM python:3.11-slim

# 파이썬 출력 버퍼링 해제 및 pyc 생성 방지
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 1. Database Persistent Volume 환경변수 설정
# SQLite 데이터베이스 파일을 보존하기 위한 디렉터리 경로
ENV DATA_DIR=/data
VOLUME ["/data"]

# 2. 웹앱 Base URL Prefix 환경변수 설정 (기본값: /shortvotes)
ENV DEFAULT_PREFIX=/shortvotes

# 3. Gemini AI 환경변수 설정 (코드에서 ".env" 또는 시스템 환경변수로 참조)
# GEMINI_API_KEY는 기본값을 컨테이너 외부 관리(docker run -e, K8s Secret 등)나 시스템 내부에서 지정
ENV GEMINI_API_KEY="" \
    GEMINI_MODEL_NAME=gemini-2.5-flash \
    GEMINI_API_MAX_TOKENS=1240000

# 4. 작업 디렉터리 설정
WORKDIR /app

# 5. 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 애플리케이션 소스 코드 복사
COPY . .

# 7. 노출 포트 설정 (5000번)
EXPOSE 5000

# 8. 컨테이너 헬스체크 정의 (요청 사양에 맞춘 Prefix 경로 연동)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s \
    CMD python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"

# 9. 컨테이너 시작 CMD (FastAPI Uvicorn 5000번 포트 기동)
# (운영 Gunicorn 워커로 기동 시: CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5000", "--workers", "2", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "main:app"])
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
