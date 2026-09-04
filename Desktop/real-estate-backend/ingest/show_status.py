"""시연용 — 지금까지 쌓인 데이터 현황을 한눈에 보여주는 스크립트.
실행: python ingest/show_status.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.database import get_session
from app.db_models import RawTradeSale, RawTradeRent, ComplexMaster, SizeMaster, ItemMetricsCache


def show_status():
    with get_session() as session:
        sale_count = session.execute(select(func.count()).select_from(RawTradeSale)).scalar()
        rent_count = session.execute(select(func.count()).select_from(RawTradeRent)).scalar()
        complex_count = session.execute(select(func.count()).select_from(ComplexMaster)).scalar()
        size_count = session.execute(select(func.count()).select_from(SizeMaster)).scalar()
        metrics_count = session.execute(select(func.count()).select_from(ItemMetricsCache)).scalar()

        print("=== 현재 데이터 현황 ===")
        print(f"매매 원본 거래 (raw_trades_sale): {sale_count}건")
        print(f"전월세 원본 거래 (raw_trades_rent): {rent_count}건")
        print(f"단지 마스터 (complex_master): {complex_count}개")
        print(f"평형 마스터 (size_master): {size_count}개")
        print(f"지표 캐시 (item_metrics_cache): {metrics_count}건  ← 아직 채우는 스크립트 없음(다음 작업)")

        print("\n=== 단지 마스터 샘플 5건 ===")
        samples = session.execute(select(ComplexMaster).limit(5)).scalars().all()
        for s in samples:
            print(f"  {s.apt_nm} ({s.umd_nm}, {s.build_year}년)")

        print("\n=== 테스트용 size_id 샘플 5건 (아래 번호로 curl 테스트하세요) ===")
        size_samples = session.execute(select(SizeMaster).limit(5)).scalars().all()
        for sz in size_samples:
            print(f"  size_id={sz.id}  (complex_id={sz.complex_id}, 전용면적={sz.representative_area}㎡, {sz.pyeong}평)")


if __name__ == "__main__":
    show_status()
