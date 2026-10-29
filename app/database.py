from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# SQLite 연결 설정 (단일 스레드 제약 완화 및 타임아웃 15초)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    echo=False
)

# SQLite WAL(Write-Ahead Logging) 모드 활성화로 동시성 및 쓰기 락 방지
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from sqlalchemy import text
    from app.models import event, user, vote
    Base.metadata.create_all(bind=engine)

    # 기존 SQLite 데이터베이스 파일에 신규 컬럼 자동 마이그레이션 보장
    with engine.begin() as conn:
        event_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(events)")).fetchall()]
        if "enable_options" not in event_cols:
            conn.execute(text("ALTER TABLE events ADD COLUMN enable_options BOOLEAN NOT NULL DEFAULT 1"))

        user_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()]
        if "option_text" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN option_text VARCHAR(128) DEFAULT ''"))

        vote_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(votes)")).fetchall()]
        if "option_text" not in vote_cols:
            conn.execute(text("ALTER TABLE votes ADD COLUMN option_text VARCHAR(128) DEFAULT ''"))
