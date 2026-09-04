"""아이템(단지+평형) 관련 엔드포인트. 팀 API 명세(B-03~B-09) 기준.

구현 완료: B-03(기본지표), B-04(호가괴리율), B-05(추이), B-06(유동성),
           B-07(층별분포), B-09(생활권랭킹)
API 연결됨(로직 검증 완료): B-08(전세매매갭)
미구현: B-10(거시뷰) — macro.py 참고
"""
import statistics
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics import (
    get_trades_for_size,
    get_rents_for_size,
    compute_trend,
    compute_liquidity,
    compute_price_distribution,
    compute_ranking,
    compute_recent_median_price,
    compute_price_per_pyeong,
    exclude_incomplete_recent,
    _get_size_and_complex,
)

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/{size_id}")
def get_item_basic(size_id: int, db: Session = Depends(get_db)):
    """B-03: 평형 기본 지표.
    ⚠️ item_metrics_cache 배치가 아직 없어서 즉석 계산함(다음 단계에서 캐시로 전환 예정).
    ⚠️ recent_avg_price라는 이름은 쓰지 않음(팀 규칙) — recent_median_price만 사용.
    """
    size, complex_ = _get_size_and_complex(db, size_id)
    if not size or not complex_:
        return {"error": "not_found", "size_id": size_id}

    trades = get_trades_for_size(db, size_id)
    prices = [t.deal_amount for t in trades if t.deal_amount]

    last_trade = None
    if trades:
        dated = [t for t in trades if t.deal_year and t.deal_month]
        if dated:
            dated.sort(key=lambda t: (t.deal_year, t.deal_month, t.deal_day or 0), reverse=True)
            last = dated[0]
            last_trade = f"{last.deal_year}-{last.deal_month:02d}"

    price_per_pyeong = compute_price_per_pyeong(trades, size.pyeong)

    return {
        "size_id": size_id,
        "complex_name": complex_.apt_nm,
        "address": f"{complex_.umd_nm} {complex_.jibun}" if complex_.jibun else complex_.umd_nm,
        "build_year": complex_.build_year,
        "area": float(size.representative_area) if size.representative_area else None,
        "pyeong": size.pyeong,
        "recent_median_price": compute_recent_median_price(trades),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "price_per_pyeong": price_per_pyeong,
        "last_trade_date": last_trade,
        "trade_count_3y": len(trades),
        "sample_insufficient": len(trades) < 3,
    }


@router.post("/{size_id}/price-check")
def price_check(size_id: int, list_price: int = Body(..., embed=True), db: Session = Depends(get_db)):
    """B-04: 호가-실거래가 괴리율.
    ⚠️ recent_median_price 산출 기준에 시트 내 두 표가 서로 다름(평균 vs 중앙값) —
       여기서는 '최근 10건의 중앙값'으로 절충함. 팀 확인 필요.
    """
    trades = get_trades_for_size(db, size_id)
    recent_median_price = compute_recent_median_price(trades)

    if recent_median_price is None:
        return {
            "size_id": size_id, "list_price": list_price,
            "recent_median_price": None, "gap_amount": None, "gap_pct": None,
            "sample_insufficient": True,
        }

    gap_amount = list_price - recent_median_price
    gap_pct = round(gap_amount / recent_median_price * 100, 2)

    return {
        "size_id": size_id,
        "list_price": list_price,
        "recent_median_price": recent_median_price,
        "gap_amount": gap_amount,
        "gap_pct": gap_pct,
    }


@router.get("/{size_id}/trend")
def get_trend(size_id: int, months: int = Query(60, description="조회 기간(개월), 기본 60개월"), db: Session = Depends(get_db)):
    """B-05: 실거래 추이.
    거래유형: 매매만 / 대표값: 중앙값 / 제외: 최근 2개월(신고지연) + 계약해제건
    """
    trades = get_trades_for_size(db, size_id)  # get_trades_for_size가 이미 계약해제 건 제외함
    trades = exclude_incomplete_recent(trades, months=2)

    if months < 60:
        from datetime import date
        today = date.today()
        cutoff = today.year * 12 + today.month - months
        trades = [t for t in trades if t.deal_year and t.deal_month and (t.deal_year * 12 + t.deal_month) >= cutoff]

    if not trades:
        return {"size_id": size_id, "monthly_median_prices": [], "trend_direction": "표본 부족"}

    computed = compute_trend(trades)
    return {
        "size_id": size_id,
        "monthly_median_prices": computed["monthly_prices"],
        "trend_direction": computed["trend_direction"],
    }


@router.get("/{size_id}/liquidity")
def get_liquidity(
    size_id: int,
    period: int = Query(12, description="6, 12, 24, 36 중 선택"),
    db: Session = Depends(get_db),
):
    """B-06: 거래량 유동성. 모호한 ratio는 반환하지 않음(팀 규칙)."""
    sale_trades = get_trades_for_size(db, size_id)
    rents = get_rents_for_size(db, size_id, pure_jeonse_only=True)  # 순수 전세만
    result = compute_liquidity(sale_trades, rents, period)
    return {
        "size_id": size_id,
        "period_months": result["period_months"],
        "sale_count": result["sale_count"],
        "jeonse_count": result["jeonse_count"],
    }


@router.get("/{size_id}/price-distribution")
def get_price_distribution(size_id: int, db: Session = Depends(get_db)):
    """B-07: 층별 가격분포. 최근 2개월 제외, 저층 건물 예외 처리 포함."""
    trades = get_trades_for_size(db, size_id)
    trades = exclude_incomplete_recent(trades, months=2)
    result = compute_price_distribution(trades)
    result["size_id"] = size_id
    return result


@router.get("/jeonse-gap")
def get_jeonse_gap(ids: str, db: Session = Depends(get_db)):
    """B-08: 전세·매매 갭. ids는 콤마 구분 size_id 목록.
    ⚠️ 검증 스크립트(jeonse_gap_full_validation.py)에서 썼던 IQR 이상치 제거는
       아직 이 API엔 반영 안 됨(단순화 버전) — 필요시 다음 단계에서 추가.
    """
    size_ids = [int(x) for x in ids.split(",")]
    items = []
    for size_id in size_ids:
        sale_trades = get_trades_for_size(db, size_id)
        rents = get_rents_for_size(db, size_id, pure_jeonse_only=True)

        sale_prices = [t.deal_amount for t in sale_trades if t.deal_amount]
        jeonse_prices = [r.deposit for r in rents if r.deposit]

        if len(sale_prices) < 3 or len(jeonse_prices) < 3:
            items.append({
                "size_id": size_id, "sale_median": None, "jeonse_median": None,
                "gap_amount": None, "gap_ratio": None, "sample_insufficient": True,
            })
            continue

        sale_median = round(statistics.median(sale_prices))
        jeonse_median = round(statistics.median(jeonse_prices))
        gap_amount = sale_median - jeonse_median
        gap_ratio = round(jeonse_median / sale_median * 100, 1)

        items.append({
            "size_id": size_id,
            "sale_median": sale_median,
            "jeonse_median": jeonse_median,
            "gap_amount": gap_amount,
            "gap_ratio": gap_ratio,
            "sample_insufficient": False,
        })

    return {"items": items}


@router.get("/{size_id}/ranking")
def get_ranking(size_id: int, area_scope: str = Query("sgg", description="생활권 기준: sgg(구)만 지원 중"), db: Session = Depends(get_db)):
    """B-09: 생활권 랭킹.
    ⚠️ '생활권'을 동/구/반경 중 무엇으로 할지 팀 결정 전까지, 임시로 '같은 구' 기준만 지원.
    """
    result = compute_ranking(db, size_id)
    result["size_id"] = size_id
    result["area_scope"] = "sgg(구)"
    result["criteria_note"] = "임시 기준: 같은 구 + 평형 ±5㎡. 동/구/반경 중 팀 확정 필요"
    return result
