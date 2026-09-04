"""한국부동산원 R-ONE(부동산통계정보시스템) API 호출 모듈.

주의: 이 파일은 스켈레톤입니다. R-ONE API의 정확한 요청 URL, 파라미터명,
통계표 코드(statblCd)는 팀이 R-ONE 포털에서 인증키를 발급받은 뒤
공식 문서를 보고 채워넣어야 합니다. (오늘 계획의 "부동산통계정보시스템
접근 방식 확인" 단계에서 실제 값 확인 예정)
"""
import requests
from app.config import REB_API_KEY

# TODO: R-ONE 포털에서 정확한 base URL 확인 후 수정
REB_BASE_URL = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"


def fetch_price_index(region_cd: str, period: str) -> dict:
    """아파트 매매가격지수 조회.
    TODO: statblCd(통계표 코드), itmId(항목 코드) 등 실제 파라미터명은
    R-ONE 개발가이드 문서 확인 후 채워야 함.
    """
    params = {
        "KEY": REB_API_KEY,
        "STATBL_ID": "TODO_통계표코드",  # 매매가격지수 통계표 코드로 교체
        "DTACYCLE_CD": "WEEK",  # 주간 자료
        "WRTTIME_IDTFR_ID": period,
        "type": "json",
    }
    res = requests.get(REB_BASE_URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


def fetch_supply_demand_index(region_cd: str, period: str) -> dict:
    """매매수급동향지수 조회. price_index와 같은 API, 통계표 코드만 다름."""
    params = {
        "KEY": REB_API_KEY,
        "STATBL_ID": "TODO_통계표코드",  # 매매수급동향지수 통계표 코드로 교체
        "DTACYCLE_CD": "WEEK",
        "WRTTIME_IDTFR_ID": period,
        "type": "json",
    }
    res = requests.get(REB_BASE_URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


if __name__ == "__main__":
    print("이 스크립트는 R-ONE 인증키 발급 및 통계표 코드 확인 후 실행하세요.")
    print("실행 전 확인할 것: statblCd 값, 응답 필드명, region_cd 형식")
