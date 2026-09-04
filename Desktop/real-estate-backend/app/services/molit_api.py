"""국토교통부 실거래가 API 호출 모듈.
매매 상세자료 + 전월세 자료 둘 다 이 파일에서 처리합니다.
"""
import requests
import xmltodict
from app.config import MOLIT_API_KEY

SALE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


def _parse_items(xml_text: str) -> list[dict]:
    """공통 XML 파싱 로직. item이 1개면 dict, 여러 개면 list로 오는 것을 보정."""
    data = xmltodict.parse(xml_text)
    body = data.get("response", {}).get("body", {})
    items = body.get("items")
    if not items:
        return []
    item = items.get("item")
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


def _parse_total_count(xml_text: str) -> int:
    """응답의 totalCount를 확인해서 페이지 몇 개가 더 필요한지 계산할 때 사용."""
    data = xmltodict.parse(xml_text)
    body = data.get("response", {}).get("body", {})
    try:
        return int(body.get("totalCount", 0))
    except (TypeError, ValueError):
        return 0


def fetch_sale_trades(sgg_cd: str, deal_ymd: str, page_no: int = 1, num_of_rows: int = 1000) -> tuple[list[dict], int]:
    """매매 실거래 조회 (1페이지). 반환값: (아이템 리스트, totalCount)"""
    params = {
        "serviceKey": MOLIT_API_KEY,
        "LAWD_CD": sgg_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
    }
    res = requests.get(SALE_URL, params=params, timeout=10)
    res.raise_for_status()
    return _parse_items(res.text), _parse_total_count(res.text)


def fetch_rent_trades(sgg_cd: str, deal_ymd: str, page_no: int = 1, num_of_rows: int = 1000) -> tuple[list[dict], int]:
    """전월세 실거래 조회 (1페이지). 반환값: (아이템 리스트, totalCount)"""
    params = {
        "serviceKey": MOLIT_API_KEY,
        "LAWD_CD": sgg_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": page_no,
        "numOfRows": num_of_rows,
    }
    res = requests.get(RENT_URL, params=params, timeout=10)
    res.raise_for_status()
    return _parse_items(res.text), _parse_total_count(res.text)


def fetch_sale_trades_all(sgg_cd: str, deal_ymd: str) -> list[dict]:
    """매매 실거래 전체 수집 (totalCount만큼 페이지를 다 돌아서 잘리지 않게)."""
    first_page, total = fetch_sale_trades(sgg_cd, deal_ymd, page_no=1, num_of_rows=1000)
    if total <= len(first_page):
        return first_page
    all_items = list(first_page)
    page = 2
    while len(all_items) < total:
        more, _ = fetch_sale_trades(sgg_cd, deal_ymd, page_no=page, num_of_rows=1000)
        if not more:
            break
        all_items.extend(more)
        page += 1
    return all_items


def fetch_rent_trades_all(sgg_cd: str, deal_ymd: str) -> list[dict]:
    """전월세 실거래 전체 수집 (totalCount만큼 페이지를 다 돌아서 잘리지 않게)."""
    first_page, total = fetch_rent_trades(sgg_cd, deal_ymd, page_no=1, num_of_rows=1000)
    if total <= len(first_page):
        return first_page
    all_items = list(first_page)
    page = 2
    while len(all_items) < total:
        more, _ = fetch_rent_trades(sgg_cd, deal_ymd, page_no=page, num_of_rows=1000)
        if not more:
            break
        all_items.extend(more)
        page += 1
    return all_items


def is_pure_jeonse(rent_item: dict) -> bool:
    """월세금액이 0인 건만 순수 전세로 판정."""
    monthly = str(rent_item.get("monthlyRent", "0")).replace(",", "").strip()
    return monthly == "0" or monthly == ""


def is_canceled_deal(sale_item: dict) -> bool:
    """계약 해제된 거래인지 확인. 통계 계산 시 반드시 제외해야 함."""
    return bool(sale_item.get("cdealType"))


if __name__ == "__main__":
    # 오늘(8/28) 검증용 실행 스크립트
    # 사용법: python -m app.services.molit_api
    test_sgg = "11680"  # 서울 강남구 (원하는 지역코드로 교체)
    test_ymd = "202508"  # 테스트할 계약년월 (원하는 월로 교체)

    print(f"=== 매매 실거래 테스트: {test_sgg} / {test_ymd} ===")
    sales = fetch_sale_trades_all(test_sgg, test_ymd)
    print(f"총 {len(sales)}건 조회됨 (페이지네이션 처리로 전체 수집)")
    for s in sales[:3]:
        print({
            "아파트": s.get("aptNm"),
            "거래금액(만원)": s.get("dealAmount"),
            "전용면적": s.get("excluUseAr"),
            "층": s.get("floor"),
            "해제여부": s.get("cdealType"),
        })

    print(f"\n=== 전월세 실거래 테스트: {test_sgg} / {test_ymd} ===")
    rents = fetch_rent_trades_all(test_sgg, test_ymd)
    print(f"총 {len(rents)}건 조회됨 (페이지네이션 처리로 전체 수집)")
    pure_jeonse = [r for r in rents if is_pure_jeonse(r)]
    print(f"이 중 순수 전세: {len(pure_jeonse)}건")
    for r in rents[:3]:
        print({
            "아파트": r.get("aptNm"),
            "보증금(deposit)": r.get("deposit"),
            "월세금액(monthlyRent)": r.get("monthlyRent"),
            "전용면적": r.get("excluUseAr"),
        })
    print("\n[검증할 것] 매매 dealAmount와 전세 deposit의 자릿수를 비교해서 단위(만원/원)가 같은지 눈으로 확인하세요.")
