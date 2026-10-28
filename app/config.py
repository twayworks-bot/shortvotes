import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    # Gemini AI Settings (.env 또는 시스템 환경변수 참조)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_API_MAX_TOKENS: int = 1240000

    # Web & Server Settings (DEFAULT_PREFIX 지원)
    DEFAULT_PREFIX: Optional[str] = None
    PREFIX: str = "shortvotes"
    PORT: int = 5000
    HOST: str = "0.0.0.0"

    # Database & Persistent Volume Path
    DATA_DIR: Optional[str] = None
    DATABASE_URL: Optional[str] = None

    # Business Rules
    USER_EXPIRY_DAYS: int = 30
    MAX_USERS_PER_EVENT: int = 100

    # 시스템 환경변수를 최우선으로, 없으면 .env 파일 참조 (파일 부재 시 무시)
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def reload_gemini_settings() -> Settings:
    """
    .env 파일 및 OS 시스템 환경변수에서 Gemini 설정(GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_API_MAX_TOKENS)을
    안전하게 재로드합니다. (빈 문자열 환경변수로 인해 .env 설정이 유실되는 현상 방지)
    """
    file_env = {}
    if ENV_FILE_PATH.exists():
        try:
            file_env = dotenv_values(ENV_FILE_PATH, encoding="utf-8") or {}
        except Exception as e:
            logger.warning(f"Failed to read .env file at {ENV_FILE_PATH}: {e}")

    os_api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    file_api_key = (file_env.get("GEMINI_API_KEY") or "").strip()
    if os_api_key:
        settings.GEMINI_API_KEY = os_api_key
    elif file_api_key:
        settings.GEMINI_API_KEY = file_api_key

    os_model = (os.getenv("GEMINI_MODEL_NAME") or "").strip()
    file_model = (file_env.get("GEMINI_MODEL_NAME") or "").strip()
    # .env에 명시된 모델명이 있고 OS 환경변수가 미지정이거나 기본값인 경우 .env 우선 반영
    if file_model and (not os_model or os_model == "gemini-2.5-flash"):
        settings.GEMINI_MODEL_NAME = file_model
    elif os_model:
        settings.GEMINI_MODEL_NAME = os_model
    elif not settings.GEMINI_MODEL_NAME:
        settings.GEMINI_MODEL_NAME = "gemini-2.5-flash"

    os_tokens = (os.getenv("GEMINI_API_MAX_TOKENS") or "").strip()
    file_tokens = (file_env.get("GEMINI_API_MAX_TOKENS") or "").strip()
    raw_tokens = os_tokens if (os_tokens and os_tokens != "1240000") else (file_tokens or os_tokens)
    if raw_tokens:
        try:
            settings.GEMINI_API_MAX_TOKENS = int(raw_tokens)
        except ValueError:
            pass

    return settings

# 1. 초기 Gemini 환경변수 보정 실행
reload_gemini_settings()

# 2. DEFAULT_PREFIX 환경변수 반영 (예: "/shortvotes" -> "shortvotes")
env_prefix = os.getenv("DEFAULT_PREFIX", settings.DEFAULT_PREFIX)
if env_prefix is not None:
    cleaned = env_prefix.strip()
    if cleaned in ["", "/"]:
        settings.PREFIX = ""
    else:
        settings.PREFIX = cleaned.strip("/")

# 3. DATA_DIR 및 SQLite Persistent Volume 경로 설정
if not settings.DATA_DIR:
    settings.DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))

data_path = Path(settings.DATA_DIR)
os.makedirs(data_path, exist_ok=True)

if not settings.DATABASE_URL:
    db_file_path = data_path / "shortvotes.db"
    # Windows 경로 역슬래시를 sqlite URI에 맞게 슬래시로 변환
    normalized_path = str(db_file_path.resolve()).replace("\\", "/")
    settings.DATABASE_URL = f"sqlite:///{normalized_path}"
