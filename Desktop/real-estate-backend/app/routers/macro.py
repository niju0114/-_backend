"""거시 데이터(매매가격지수 + 매매수급동향지수) 엔드포인트.
한국부동산원 R-ONE API 연동 후 완성. app/services/reb_api.py 참고.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/indices")
def get_macro_indices(region: str = "서울"):
    """가격지수(라인차트용) + 수급지수(뱃지용) 함께 반환.
    예: {"price_index": [...], "supply_demand": {"value": 103.7, "status": "매수세 우위", "trend": "상승"}}
    """
    # TODO: R-ONE API 통계표 코드 확정 후 구현
    raise NotImplementedError("R-ONE API 통계표 코드 확인 후 구현 예정")
