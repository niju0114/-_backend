"""전체 대상 지역 x 기간에 대해 국토부 API를 반복 호출해서
raw_trades_sale, raw_trades_rent 테이블에 적재하는 배치 스크립트.

SQLAlchemy ORM으로 적재한다 (supabase-py REST 클라이언트 미사용).

실행 전 확인할 것:
1. .env에 MOLIT_API_KEY, DATABASE_URL이 채워져 있는지
2. ingest/create_tables.py를 먼저 실행해서 테이블이 만들어져 있는지
3. 아래 TARGET_SGG_CODES를 팀이 확정한 지역 코드로 바꿨는지

실행 방법: python ingest/batch_collect.py
"""
import sys
import os
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.molit_api import fetch_sale_trades_all, fetch_rent_trades_all
from app.database import get_session
from app.db_models import RawTradeSale, RawTradeRent
from sqlalchemy.dialects.postgresql import insert as pg_insert

TARGET_SGG_CODES = ["11680"]  # 예: 서울 강남구

# 주의: 5년치를 수집해도 아래 필드들은 시작 시점이 더 짧아서 과거 구간엔 값이 비어있는 게 정상.
# - 계약해제(cdealType): 2020.02~
# - 거래유형(dealingGbn): 2021.11~
# - 등기일자(rgstDate, 이 테이블엔 미포함): 2023.01~


def recent_months(n: int) -> list[str]:
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(f"{y}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


TARGET_DEAL_YMD_LIST = recent_months(60)  # 최근 5년(60개월) 자동 생성 — 최대 수집 범위


def collect_sale_data():
    total = 0
    with get_session() as session:
        for sgg in TARGET_SGG_CODES:
            for ymd in TARGET_DEAL_YMD_LIST:
                items = fetch_sale_trades_all(sgg, ymd)
                rows = [
                    {
                        "sgg_cd": sgg,
                        "umd_nm": item.get("umdNm"),
                        "jibun": item.get("jibun"),
                        "apt_nm": item.get("aptNm"),
                        "build_year": _to_int(item.get("buildYear")),
                        "exclu_use_ar": _to_float(item.get("excluUseAr")),
                        "floor": _to_int(item.get("floor")),
                        "deal_amount": _to_int(item.get("dealAmount")),
                        "deal_year": _to_int(item.get("dealYear")),
                        "deal_month": _to_int(item.get("dealMonth")),
                        "deal_day": _to_int(item.get("dealDay")),
                        "dealing_gbn": item.get("dealingGbn"),
                        "cdeal_type": item.get("cdealType"),
                        "cdeal_day": item.get("cdealDay"),
                    }
                    for item in items
                ]
                if rows:
                    # 중복(같은 거래가 이미 있으면) 무시하고 넘어감 — 여러 번 실행해도 안전
                    stmt = pg_insert(RawTradeSale).values(rows)
                    stmt = stmt.on_conflict_do_nothing(constraint="uq_raw_trade_sale_natural_key")
                    session.execute(stmt)
                    session.commit()
                    total += len(rows)
                print(f"[매매] {sgg}/{ymd}: {len(rows)}건 적재")
    print(f"매매 데이터 총 {total}건 적재 완료")


def collect_rent_data():
    total = 0
    with get_session() as session:
        for sgg in TARGET_SGG_CODES:
            for ymd in TARGET_DEAL_YMD_LIST:
                items = fetch_rent_trades_all(sgg, ymd)
                rows = [
                    {
                        "sgg_cd": sgg,
                        "umd_nm": item.get("umdNm"),
                        "jibun": item.get("jibun"),
                        "apt_nm": item.get("aptNm"),
                        "exclu_use_ar": _to_float(item.get("excluUseAr")),
                        "floor": _to_int(item.get("floor")),
                        "deposit": _to_int(item.get("deposit")),
                        "monthly_rent": _to_int(item.get("monthlyRent")),
                        "deal_year": _to_int(item.get("dealYear")),
                        "deal_month": _to_int(item.get("dealMonth")),
                        "contract_type": item.get("contractType"),
                    }
                    for item in items
                ]
                if rows:
                    stmt = pg_insert(RawTradeRent).values(rows)
                    stmt = stmt.on_conflict_do_nothing(constraint="uq_raw_trade_rent_natural_key")
                    session.execute(stmt)
                    session.commit()
                    total += len(rows)
                print(f"[전월세] {sgg}/{ymd}: {len(rows)}건 적재")
    print(f"전월세 데이터 총 {total}건 적재 완료")


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


if __name__ == "__main__":
    print(f"대상 지역: {TARGET_SGG_CODES}")
    print(f"대상 기간: {TARGET_DEAL_YMD_LIST[0]} ~ {TARGET_DEAL_YMD_LIST[-1]} (총 {len(TARGET_DEAL_YMD_LIST)}개월, 최대 5년 수집)")
    print("※ SQLAlchemy ORM으로 적재합니다 (Supabase REST API 미사용).")
    print("=== 배치 수집 시작 ===")
    collect_sale_data()
    collect_rent_data()
    print("=== 배치 수집 완료 ===")
    print("\n다음 단계: python ingest/build_complex_master.py 를 실행하세요.")
