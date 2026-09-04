"""단지별 평형 목록 조회 (B-02)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.db_models import SizeMaster
from app.services.analytics import get_trades_for_size, compute_recent_median_price

router = APIRouter(prefix="/complexes", tags=["complexes"])


@router.get("/{complex_id}/sizes")
def get_sizes(complex_id: int, db: Session = Depends(get_db)):
    """이 단지에 실제로 존재하는 평형 목록.
    B-02 명세: size_id, representative_area, pyeong, recent_median_price, trade_count_3y
    recent_median_price는 compute_recent_median_price(최근 10건 중앙값)로 통일
    — B-03/B-04와 같은 함수를 써서 값이 서로 다르게 나오는 문제를 방지.
    """
    sizes = db.execute(
        select(SizeMaster).where(SizeMaster.complex_id == complex_id)
    ).scalars().all()

    result = []
    for size in sizes:
        trades = get_trades_for_size(db, size.id)
        result.append({
            "size_id": size.id,
            "representative_area": float(size.representative_area) if size.representative_area else None,
            "pyeong": size.pyeong,
            "recent_median_price": compute_recent_median_price(trades),
            "trade_count_3y": len(trades),
        })

    result.sort(key=lambda x: x["representative_area"] or 0)
    return result
