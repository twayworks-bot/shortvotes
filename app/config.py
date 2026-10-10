import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Gemini AI Settings (.env)
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

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# 1. DEFAULT_PREFIX 환경변수 반영 (예: "/shortvotes" -> "shortvotes")
if settings.DEFAULT_PREFIX is not None:
    cleaned = settings.DEFAULT_PREFIX.strip()
    if cleaned in ["", "/"]:
        settings.PREFIX = ""
    else:
        settings.PREFIX = cleaned.strip("/")

# 2. DATA_DIR 및 SQLite Persistent Volume 경로 설정
if not settings.DATA_DIR:
    settings.DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))

data_path = Path(settings.DATA_DIR)
os.makedirs(data_path, exist_ok=True)

if not settings.DATABASE_URL:
    db_file_path = data_path / "shortvotes.db"
    # Windows 경로 역슬래시를 sqlite URI에 맞게 슬래시로 변환
    normalized_path = str(db_file_path.resolve()).replace("\\", "/")
    settings.DATABASE_URL = f"sqlite:///{normalized_path}"
