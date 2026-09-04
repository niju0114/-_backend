"""아이템(단지+평형) 분석 함수 모음.
raw_trades_sale/raw_trades_rent에서 데이터를 뽑아 계산하는 로직을 한 곳에 모았다.

주의: item_metrics_cache 배치가 아직 없어서, 지금은 요청 시점에 즉석 계산한다.
데이터가 많아지면 이 계산 결과를 item_metrics_cache에 미리 저장해두는 배치로
전환해야 한다 (다음 단계 작업).
"""
import statistics
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db_models import RawTradeSale, RawTradeRent, ComplexMaster, SizeMaster


def exclude_incomplete_recent(trades: list[RawTradeSale], months: int = 2) -> list[RawTradeSale]:
    """국토부 신고기한(30일) 때문에 최근 N개월 데이터는 신고가 덜 채워진 상태일 수 있다.
    실거래 추이·가격분포처럼 '정확한 시세'가 중요한 계산에서는 이 구간을 제외한다.
    (거래량 유동성은 '지금 활발한지'를 보는 지표라 여기 적용 안 함 — 팀 규칙표 기준)
    """
    today = date.today()
    cutoff = today.year * 12 + today.month - months
    return [t for t in trades if t.deal_year and t.deal_month and (t.deal_year * 12 + t.deal_month) <= cutoff]


def compute_price_per_pyeong(trades: list[RawTradeSale], pyeong: int | None) -> int | None:
    """평단가 = 전체 기간 실거래가 중앙값 ÷ 평수.
    B-03(아이템 기본지표)과 B-09(생활권 랭킹)가 같은 방식을 쓰도록 통일한 함수.
    """
    prices = [t.deal_amount for t in trades if t.deal_amount]
    if not prices or not pyeong:
        return None
    return round(statistics.median(prices) / pyeong)


def compute_recent_median_price(trades: list[RawTradeSale], n: int = 10) -> int | None:
    """최근 N건(기본 10건)의 중앙값. B-03/B-04에서 공통으로 쓰는 'recent_median_price' 정의.
    ⚠️ 시트의 '데이터 산출 기준' 표는 이 값을 평균이라 하고,
       '변수명 통일' 표는 중앙값이라 함 — 서로 다름. 여기서는 후자(중앙값)를 따르되
       표본 수(최근 10건)만 전자 기준을 가져왔음. 팀 확인 필요.
    """
    valid = [t for t in trades if t.deal_amount and t.deal_year and t.deal_month]
    if not valid:
        return None
    valid.sort(key=lambda t: (t.deal_year, t.deal_month, t.deal_day or 0), reverse=True)
    recent = valid[:n]
    return round(statistics.median([t.deal_amount for t in recent]))


def _get_size_and_complex(db: Session, size_id: int):
    size = db.get(SizeMaster, size_id)
    if not size:
        return None, None
    complex_ = db.get(ComplexMaster, size.complex_id)
    return size, complex_


def get_trades_for_size(db: Session, size_id: int, exclude_canceled: bool = True):
    """이 평형(size_id)에 해당하는 매매 거래 목록.
    같은 단지 + 대표면적 ±1㎡ 이내로 매칭 (평형 그룹핑 때와 같은 기준).
    """
    size, complex_ = _get_size_and_complex(db, size_id)
    if not size or not complex_:
        return []

    lo, hi = float(size.representative_area) - 1.0, float(size.representative_area) + 1.0
    query = select(RawTradeSale).where(
        RawTradeSale.sgg_cd == complex_.sgg_cd,
        RawTradeSale.umd_nm == complex_.umd_nm,
        RawTradeSale.jibun == complex_.jibun,
        RawTradeSale.apt_nm == complex_.apt_nm,
        RawTradeSale.exclu_use_ar >= lo,
        RawTradeSale.exclu_use_ar <= hi,
    )
    if exclude_canceled:
        query = query.where(RawTradeSale.cdeal_type.is_(None))
    return db.execute(query).scalars().all()


def get_rents_for_size(db: Session, size_id: int, pure_jeonse_only: bool = True):
    """이 평형(size_id)에 해당하는 전월세 거래 목록."""
    size, complex_ = _get_size_and_complex(db, size_id)
    if not size or not complex_:
        return []

    lo, hi = float(size.representative_area) - 1.0, float(size.representative_area) + 1.0
    query = select(RawTradeRent).where(
        RawTradeRent.sgg_cd == complex_.sgg_cd,
        RawTradeRent.umd_nm == complex_.umd_nm,
        RawTradeRent.jibun == complex_.jibun,
        RawTradeRent.apt_nm == complex_.apt_nm,
        RawTradeRent.exclu_use_ar >= lo,
        RawTradeRent.exclu_use_ar <= hi,
    )
    rows = db.execute(query).scalars().all()
    if pure_jeonse_only:
        rows = [r for r in rows if r.monthly_rent == 0]
    return rows


def compute_trend(trades: list[RawTradeSale]) -> dict:
    """월별 중앙값 시세 + 추세(모멘텀) 계산. 선형회귀 slope를 직접 계산(numpy 없이)."""
    by_month: dict[tuple, list[int]] = {}
    for t in trades:
        if t.deal_year is None or t.deal_month is None or t.deal_amount is None:
            continue
        key = (t.deal_year, t.deal_month)
        by_month.setdefault(key, []).append(t.deal_amount)

    monthly = sorted(by_month.items())
    series = [
        {"year_month": f"{y}-{m:02d}", "median_price": round(statistics.median(prices))}
        for (y, m), prices in monthly
    ]

    if len(series) < 2:
        return {"monthly_prices": series, "momentum_score": None, "trend_direction": "표본 부족"}

    xs = list(range(len(series)))
    ys = [s["median_price"] for s in series]
    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    numerator = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    denominator = sum((xs[i] - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator else 0

    direction = "상승" if slope > 0 else ("하락" if slope < 0 else "보합")
    return {"monthly_prices": series, "momentum_score": round(slope, 1), "trend_direction": direction}


def compute_liquidity(sale_trades: list[RawTradeSale], rents: list[RawTradeRent], period_months: int) -> dict:
    """최근 N개월 기준 매매/전세 거래 건수.
    rents는 호출부(items.py)에서 이미 순수 전세(monthly_rent=0)만 필터링해서 넘겨준다고 가정.
    """
    today = date.today()
    cutoff_ordinal = today.year * 12 + today.month - period_months

    def in_period_sale(t):
        if t.deal_year is None or t.deal_month is None:
            return False
        return t.deal_year * 12 + t.deal_month >= cutoff_ordinal

    def in_period_rent(r):
        if r.deal_year is None or r.deal_month is None:
            return False
        return r.deal_year * 12 + r.deal_month >= cutoff_ordinal

    sale_count = sum(1 for t in sale_trades if in_period_sale(t))
    jeonse_count = sum(1 for r in rents if in_period_rent(r))
    return {"period_months": period_months, "sale_count": sale_count, "jeonse_count": jeonse_count}


def compute_price_distribution(trades: list[RawTradeSale]) -> dict:
    """층별 가격 분포 (B-07 명세: floor_groups + price_points 구조).
    건물 총 층수 데이터가 없어서, 해당 단지 거래 중 관측된 최고층을 근사값(프록시)으로 사용.
    ⚠️ 이 근사는 실제 건물 총 층수와 다를 수 있음 — 팀 논의 필요.
    """
    valid = [t for t in trades if t.floor is not None and t.deal_amount is not None and t.floor > 0]
    if not valid:
        return {"floor_groups": {}, "price_points": [], "note": "표본 없음"}

    max_floor_observed = max(t.floor for t in valid)  # 총 층수 근사값(프록시)

    # 저층 건물 예외: 관측 최고층이 5층 이하면 3단계로 나누는 게 무의미함 (빌라/저층 단지)
    if max_floor_observed <= 5:
        return {
            "floor_groups": {},
            "price_points": [
                {"floor": t.floor, "deal_amount": t.deal_amount,
                 "exclu_use_ar": float(t.exclu_use_ar) if t.exclu_use_ar is not None else None}
                for t in valid
            ],
            "note": f"저층 건물(관측 최고층 {max_floor_observed}층)이라 저/중/고층 분류를 적용하지 않음",
        }

    low_cut = max_floor_observed / 3
    mid_cut = max_floor_observed * 2 / 3

    def group_of(floor):
        if floor <= low_cut:
            return "저층"
        elif floor <= mid_cut:
            return "중층"
        return "고층"

    price_points = [
        {
            "floor": t.floor,
            "deal_amount": t.deal_amount,
            "exclu_use_ar": float(t.exclu_use_ar) if t.exclu_use_ar is not None else None,
            "group": group_of(t.floor),
        }
        for t in valid
    ]

    floor_groups: dict[str, dict] = {}
    for group_name in ["저층", "중층", "고층"]:
        group_prices = [p["deal_amount"] for p in price_points if p["group"] == group_name]
        floor_groups[group_name] = {
            "count": len(group_prices),
            "median_price": round(statistics.median(group_prices)) if group_prices else None,
        }

    return {
        "floor_groups": floor_groups,
        "price_points": price_points,
        "max_floor_observed_proxy": max_floor_observed,
        "note": "총 층수 실데이터가 없어 관측 최고층을 근사값으로 사용함",
    }


def compute_ranking(db: Session, size_id: int) -> dict:
    """같은 구 + 같은 평형(±5㎡) 내 평단가 랭킹."""
    size, complex_ = _get_size_and_complex(db, size_id)
    if not size or not complex_:
        return {"error": "not_found"}

    target_area = float(size.representative_area)
    lo, hi = target_area - 5, target_area + 5

    peer_sizes = db.execute(
        select(SizeMaster, ComplexMaster)
        .join(ComplexMaster, SizeMaster.complex_id == ComplexMaster.id)
        .where(
            ComplexMaster.sgg_cd == complex_.sgg_cd,
            SizeMaster.representative_area >= lo,
            SizeMaster.representative_area <= hi,
        )
    ).all()

    ranked = []
    for peer_size, peer_complex in peer_sizes:
        trades = get_trades_for_size(db, peer_size.id)
        price_per_pyeong = compute_price_per_pyeong(trades, peer_size.pyeong)
        if price_per_pyeong is None:
            continue
        ranked.append({
            "size_id": peer_size.id,
            "apt_nm": peer_complex.apt_nm,
            "price_per_pyeong": price_per_pyeong,
        })

    if not ranked:
        return {"error": "no_data"}

    ranked.sort(key=lambda x: x["price_per_pyeong"], reverse=True)
    total = len(ranked)
    my_rank = next((i + 1 for i, r in enumerate(ranked) if r["size_id"] == size_id), None)
    top = ranked[0]
    my_entry = next((r for r in ranked if r["size_id"] == size_id), None)

    return {
        "my_rank": my_rank,
        "total": total,
        "my_price_per_pyeong": my_entry["price_per_pyeong"] if my_entry else None,
        "top_complex": top["apt_nm"],
        "top_price_per_pyeong": top["price_per_pyeong"],
    }
