"""SQLAlchemy ORM으로 테이블 5개를 자동 생성.
Supabase SQL Editor에 수동으로 SQL을 붙여넣을 필요 없이, 이 스크립트만 실행하면 된다.

실행 전: .env에 DATABASE_URL을 채워야 함
(Supabase 대시보드 -> Project Settings -> Database -> Connection string(URI))

실행: python ingest/create_tables.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.config import DATABASE_URL
from app.db_models import Base


def create_tables():
    if not DATABASE_URL:
        print("⚠️ .env에 DATABASE_URL이 비어있습니다.")
        print("Supabase 대시보드 -> Project Settings -> Database -> Connection string(URI)에서 확인하세요.")
        return

    print("DB 연결 시도 중...")
    engine = create_engine(DATABASE_URL)

    print("테이블 생성 중 (이미 있는 테이블은 건너뜀)...")
    Base.metadata.create_all(engine)

    print("=== 완료 ===")
    print("생성된(또는 이미 존재하는) 테이블: raw_trades_sale, raw_trades_rent, complex_master, size_master, item_metrics_cache")
    print("Supabase 대시보드의 Table Editor에서 확인해보세요.")


if __name__ == "__main__":
    create_tables()
