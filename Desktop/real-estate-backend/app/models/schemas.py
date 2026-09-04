"""API 응답 형태를 정의하는 Pydantic 모델.
프론트엔드와 응답 구조를 명확히 공유하기 위해 사용합니다.
"""
from pydantic import BaseModel


class ComplexSearchResult(BaseModel):
    complex_id: int
    apt_nm: str
    umd_nm: str
    build_year: int | None = None


class SizeInfo(BaseModel):
    size_id: int
    representative_area: float
    pyeong: int
    recent_price: int | None = None
    trade_count_3y: int


class ItemDetail(BaseModel):
    size_id: int
    apt_nm: str
    recent_avg_price: int | None = None
    recent_min_price: int | None = None
    recent_max_price: int | None = None
    price_per_pyeong: int | None = None
    trade_count_3y: int
    last_trade_date: str | None = None
    sample_insufficient: bool = False


class JeonseGapItem(BaseModel):
    size_id: int
    apt_nm: str
    sale_avg: int | None = None
    jeonse_avg: int | None = None
    jeonse_ratio: float | None = None
    gap_amount: int | None = None
    sample_insufficient: bool = False
