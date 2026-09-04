"""size_master(평형 마스터) 생성 스크립트. SQLAlchemy ORM 사용.

전제조건: complex_master가 먼저 만들어져 있어야 함.
각 단지에서 실제 거래된 전용면적들을 ±1㎡ 이내로 묶어서 "평형"으로 그룹핑한다.

실행: python ingest/build_size_master.py
"""
import sys
import os
import statistics
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database import get_session
from app.db_models import RawTradeSale, ComplexMaster, SizeMaster


def cluster_areas(areas: list[float]) -> list[dict]:
    if not areas:
        return []
    sorted_areas = sorted(areas)
    clusters = []
    current = [sorted_areas[0]]
    for a in sorted_areas[1:]:
        if a - current[-1] <= 1.0:
            current.append(a)
        else:
            clusters.append(current)
            current = [a]
    clusters.append(current)
    return [
        {"representative_area": round(statistics.median(c), 2), "count": len(c)}
        for c in clusters
    ]


def build_size_master():
    with get_session() as session:
        print("complex_master 조회 중...")
        complexes = session.execute(
            select(ComplexMaster.id, ComplexMaster.sgg_cd, ComplexMaster.umd_nm,
                   ComplexMaster.jibun, ComplexMaster.apt_nm)
        ).all()
        print(f"단지 수: {len(complexes)}개")

        if not complexes:
            print("⚠️ complex_master가 비어있습니다. build_complex_master.py를 먼저 실행하세요.")
            return

        print("raw_trades_sale 조회 중...")
        sales = session.execute(
            select(RawTradeSale.sgg_cd, RawTradeSale.umd_nm, RawTradeSale.jibun,
                   RawTradeSale.apt_nm, RawTradeSale.exclu_use_ar)
        ).all()
        print(f"매매 거래 건수: {len(sales)}건")

        complex_key_to_id = {
            (c.sgg_cd, c.umd_nm, c.jibun, c.apt_nm): c.id for c in complexes
        }

        areas_by_complex: dict[int, list[float]] = defaultdict(list)
        unmatched = 0
        for s in sales:
            key = (s.sgg_cd, s.umd_nm, s.jibun, s.apt_nm)
            complex_id = complex_key_to_id.get(key)
            if complex_id is None or s.exclu_use_ar is None:
                unmatched += 1
                continue
            areas_by_complex[complex_id].append(float(s.exclu_use_ar))

        if unmatched:
            print(f"⚠️ complex_master와 매칭 안 된 거래: {unmatched}건 (무시하고 진행)")

        print(f"평형 그룹핑 대상 단지 수: {len(areas_by_complex)}개")

        insert_rows = []
        group_count_distribution = []
        for complex_id, areas in areas_by_complex.items():
            clusters = cluster_areas(areas)
            group_count_distribution.append(len(clusters))
            for c in clusters:
                representative_area = c["representative_area"]
                pyeong = round(representative_area * 0.3025)
                insert_rows.append({
                    "complex_id": complex_id,
                    "representative_area": representative_area,
                    "pyeong": pyeong,
                })

        print(f"size_master에 {len(insert_rows)}건 upsert 시도 (SQLAlchemy ORM)...")
        batch_size = 500
        for i in range(0, len(insert_rows), batch_size):
            batch = insert_rows[i:i + batch_size]
            stmt = pg_insert(SizeMaster).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["complex_id", "representative_area"],
                set_={"pyeong": stmt.excluded.pyeong},
            )
            session.execute(stmt)
            session.commit()
            print(f"  {i + len(batch)}/{len(insert_rows)}건 처리 완료")

        print("=== size_master 생성 완료 ===")

        if group_count_distribution:
            avg_groups = statistics.mean(group_count_distribution)
            max_groups = max(group_count_distribution)
            print(f"\n단지당 평균 평형 그룹 수: {avg_groups:.1f}개 (최대: {max_groups}개)")
            if avg_groups > 6:
                print("⚠️ 평형 그룹이 너무 촘촘합니다. ±1㎡ 기준을 넓히는 걸 고려하세요.")
            elif avg_groups < 2:
                print("⚠️ 평형 그룹이 너무 거칩니다. ±1㎡ 기준을 좁히는 걸 고려하세요.")
            else:
                print("정상 범위(3~5개)에 가깝습니다.")

        total_count = session.execute(select(func.count()).select_from(SizeMaster)).scalar()
        print(f"\nsize_master 전체 건수: {total_count}건")


if __name__ == "__main__":
    build_size_master()
