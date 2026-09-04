"""item_metrics_cache 테이블을 새 컬럼 구조(recent_median_price 등)로 재생성.
지금 테이블이 비어있는(0건) 상태라서 안전하게 지우고 새로 만든다.

실행: python ingest/rebuild_metrics_table.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import get_session, get_engine
from app.db_models import Base, ItemMetricsCache


def rebuild():
    with get_session() as session:
        session.execute(text("DROP TABLE IF EXISTS item_metrics_cache"))
        session.commit()
    print("기존 item_metrics_cache 삭제 완료")

    ItemMetricsCache.__table__.create(bind=get_engine())
    print("새 구조로 item_metrics_cache 재생성 완료 (recent_median_price 등)")


if __name__ == "__main__":
    rebuild()
