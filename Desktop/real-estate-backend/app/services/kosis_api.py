"""KOSIS(국가통계포털) API 호출 모듈.

용도: 거시데이터 카드 하단의 "분기별 매매수급동향" 표기용
(상단 그래프의 주단위 매매가격지수는 R-ONE에서 가져옴 — app/services/reb_api.py 참고)

주의: 이 파일은 스켈레톤입니다. KOSIS Open API의 정확한 요청 URL, 파라미터명
(orgId, tblId, itmId 등)은 KOSIS 개발가이드 문서를 보고 채워넣어야 합니다.
"""
import requests
from app.config import KOSIS_API_KEY

# TODO: KOSIS 개발가이드에서 정확한 base URL 확인 후 수정
KOSIS_BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"


def fetch_supply_demand_quarterly(period: str) -> dict:
    """분기별 매매수급동향 조회.
    TODO: orgId(기관코드), tblId(통계표ID), itmId(항목ID) 등
    실제 파라미터는 KOSIS 통계표 검색에서 "매매수급동향" 찾아 확인 필요.
    """
    params = {
        "method": "getList",
        "apiKey": KOSIS_API_KEY,
        "orgId": "TODO_기관코드",
        "tblId": "TODO_통계표ID",
        "prdSe": "Q",  # 분기(Quarter) 단위
        "startPrdDe": period,
        "format": "json",
    }
    res = requests.get(KOSIS_BASE_URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


if __name__ == "__main__":
    print("이 스크립트는 KOSIS 통계표ID 확인 후 실행하세요.")
    print("확인할 것: orgId, tblId, itmId, 응답 JSON 구조, period 형식(YYYYQ1 등)")
