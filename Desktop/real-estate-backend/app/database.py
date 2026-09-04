"""SQLAlchemy ORM 세션 관리.

Supabase는 "호스팅된 PostgreSQL"일 뿐이고, 실제 데이터 적재·조회는
전부 이 파일의 SQLAlchemy 세션을 통해 이뤄진다 (REST API 클라이언트 미사용).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import DATABASE_URL

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError(
                ".env에 DATABASE_URL을 먼저 채워넣으세요. "
                "Supabase 대시보드 -> Project Settings -> Database -> Connection string(URI)에서 확인."
            )
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_session() -> Session:
    """스크립트(배치)에서 직접 쓸 때: with get_session() as s: ... 형태로 사용."""
    return get_session_factory()()


def get_db():
    """FastAPI 라우터에서 Depends(get_db)로 주입받아 쓰는 제너레이터."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
