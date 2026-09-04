"""complex_master(단지 마스터) 생성 스크립트. SQLAlchemy ORM 사용.

전제조건: raw_trades_sale에 데이터가 이미 적재되어 있어야 함 (batch_collect.py 먼저 실행).
K-apt를 쓰지 않으므로, raw_trades_sale에서 (법정동+지번+아파트명) 조합을
유니크하게 뽑는 것만으로 단지 마스터를 만든다.

실행: python ingest/build_complex_master.py
"""
import sys
import os
from collections import defaultdict, Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database import get_session
from app.db_models import RawTradeSale, ComplexMaster


def build_complex_master():
    with get_session() as session:
        print("raw_trades_sale에서 전체 데이터 조회 중...")
        rows = session.execute(
            select(RawTradeSale.sgg_cd, RawTradeSale.umd_nm, RawTradeSale.jibun,
                   RawTradeSale.apt_nm, RawTradeSale.build_year)
        ).all()
        print(f"총 {len(rows)}건 조회됨")

        if not rows:
            print("⚠️ raw_trades_sale이 비어있습니다. ingest/batch_collect.py를 먼저 실행하세요.")
            return

        groups: dict[tuple, list] = defaultdict(list)
        for r in rows:
            key = (r.sgg_cd, r.umd_nm, r.jibun, r.apt_nm)
            if None in key or "" in key:
                continue
            groups[key].append(r.build_year)

        print(f"유니크 단지 수: {len(groups)}개")

        insert_rows = []
        for (sgg_cd, umd_nm, jibun, apt_nm), build_years in groups.items():
            valid_years = [y for y in build_years if y]
            representative_year = Counter(valid_years).most_common(1)[0][0] if valid_years else None
            insert_rows.append({
                "sgg_cd": sgg_cd, "umd_nm": umd_nm, "jibun": jibun, "apt_nm": apt_nm,
                "build_year": representative_year,
            })

        print(f"complex_master에 {len(insert_rows)}건 upsert 시도 (SQLAlchemy ORM)...")

        batch_size = 500
        for i in range(0, len(insert_rows), batch_size):
            batch = insert_rows[i:i + batch_size]
            # PostgreSQL 전용 upsert 구문: 중복 키면 UPDATE, 없으면 INSERT
            stmt = pg_insert(ComplexMaster).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["sgg_cd", "umd_nm", "jibun", "apt_nm"],
                set_={"build_year": stmt.excluded.build_year},
            )
            session.execute(stmt)
            session.commit()
            print(f"  {i + len(batch)}/{len(insert_rows)}건 처리 완료")

        print("=== complex_master 생성 완료 ===")

        sample = session.execute(select(ComplexMaster).limit(5)).scalars().all()
        print("\n샘플 5건:")
        for row in sample:
            print(f"  {row.apt_nm} ({row.umd_nm}, {row.build_year}년)")

        total_count = session.execute(select(func.count()).select_from(ComplexMaster)).scalar()
        print(f"\ncomplex_master 전체 건수: {total_count}건")


if __name__ == "__main__":
    build_complex_master()
