"""item_metrics_cache 채우는 배치 스크립트.
size_master의 모든 평형에 대해 대표 지표를 미리 계산해서 저장한다.

전제조건: raw_trades_sale, raw_trades_rent, complex_master, size_master가 이미 준비됨.
실행: python ingest/compute_metrics.py
"""
import sys
import os
import statistics

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database import get_session
from app.db_models import SizeMaster, ItemMetricsCache
from app.services.analytics import (
    get_trades_for_size,
    get_rents_for_size,
    compute_recent_median_price,
    compute_price_per_pyeong,
)


def compute_all_metrics():
    with get_session() as session:
        sizes = session.execute(select(SizeMaster)).scalars().all()
        print(f"대상 평형 수: {len(sizes)}개")

        rows = []
        for i, size in enumerate(sizes, 1):
            trades = get_trades_for_size(session, size.id)
            prices = [t.deal_amount for t in trades if t.deal_amount]

            last_trade_date = None
            if trades:
                dated = [t for t in trades if t.deal_year and t.deal_month]
                if dated:
                    dated.sort(key=lambda t: (t.deal_year, t.deal_month, t.deal_day or 0), reverse=True)
                    last = dated[0]
                    last_trade_date = f"{last.deal_year}-{last.deal_month:02d}"

            # 전세가율(중앙값 기준) — 순수 전세만 사용
            rents = get_rents_for_size(session, size.id, pure_jeonse_only=True)
            jeonse_prices = [r.deposit for r in rents if r.deposit]
            jeonse_ratio = None
            if prices and jeonse_prices:
                sale_median = statistics.median(prices)
                jeonse_median = statistics.median(jeonse_prices)
                if sale_median:
                    jeonse_ratio = round(jeonse_median / sale_median * 100, 2)

            rows.append({
                "size_id": size.id,
                "recent_median_price": compute_recent_median_price(trades),
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "price_per_pyeong": compute_price_per_pyeong(trades, size.pyeong),
                "trade_count_3y": len(trades),
                "last_trade_date": last_trade_date,
                "jeonse_ratio": jeonse_ratio,
            })

            if i % 200 == 0:
                print(f"  진행: {i}/{len(sizes)}")

        print("item_metrics_cache에 upsert 중...")
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            stmt = pg_insert(ItemMetricsCache).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["size_id"],
                set_={
                    "recent_median_price": stmt.excluded.recent_median_price,
                    "min_price": stmt.excluded.min_price,
                    "max_price": stmt.excluded.max_price,
                    "price_per_pyeong": stmt.excluded.price_per_pyeong,
                    "trade_count_3y": stmt.excluded.trade_count_3y,
                    "last_trade_date": stmt.excluded.last_trade_date,
                    "jeonse_ratio": stmt.excluded.jeonse_ratio,
                },
            )
            session.execute(stmt)
            session.commit()
            print(f"  {i + len(batch)}/{len(rows)}건 처리 완료")

    print("=== item_metrics_cache 채우기 완료 ===")


if __name__ == "__main__":
    compute_all_metrics()
