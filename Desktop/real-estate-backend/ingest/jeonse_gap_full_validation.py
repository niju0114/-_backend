"""전세매매 갭분석 — 문서 04번 검증 항목 4-1~4-5를 실제 API 데이터로 전부 실행하고
4개 산출물(CSV)을 생성하는 스크립트.

※ 주의: 이 스크립트는 "오늘 안에 답을 내기 위한 임시 버전"입니다.
정식 파이프라인(9/2 단지·평형 마스터 생성, ±1㎡ 클러스터링)을 아직 안 거쳤기 때문에,
여기서는 "아파트명 + 반올림한 전용면적"만으로 아이템을 임시로 묶습니다.
정식 마스터 데이터가 생기면 이 스크립트는 폐기하고 DB 기반 쿼리로 교체해야 합니다.

실행: python ingest/jeonse_gap_full_validation.py
결과: ingest/validation_output/ 폴더에 CSV 4개 생성
콘솔에 4-1~4-5 판정 결과가 출력되므로, 이 부분을 캡쳐해서 증빙으로 쓰면 됩니다.
"""
import sys
import os
import csv
import statistics
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.molit_api import (
    fetch_sale_trades_all,
    fetch_rent_trades_all,
    is_pure_jeonse,
    is_canceled_deal,
)

# ============ 설정 (팀과 협의된 값으로 교체) ============
TARGET_SGG = "11680"  # 서울 강남구. 팀이 확정한 지역코드로 교체
TARGET_YMD_LIST = [
    "202409", "202410", "202411", "202412",
    "202501", "202502", "202503", "202504",
    "202505", "202506", "202507", "202508",
]  # 최근 12개월. 데이터가 늦게 갱신되는 최신월은 빠질 수 있으니 실행 후 개수 확인

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def to_int(v):
    if v is None:
        return None
    try:
        return int(str(v).replace(",", "").strip())
    except ValueError:
        return None


def to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def make_key(apt_nm: str, area: float) -> str:
    """임시 아이템 키: 아파트명 + 반올림 면적. 정식 마스터 생성 전까지만 쓰는 임시 방식."""
    return f"{apt_nm}_{round(area)}"


def collect_all_data():
    """12개월치 매매+전월세 데이터를 전부 수집."""
    print(f"=== 데이터 수집 시작: {TARGET_SGG}, {len(TARGET_YMD_LIST)}개월 ===")
    all_sales, all_rents = [], []
    for ymd in TARGET_YMD_LIST:
        sales = fetch_sale_trades_all(TARGET_SGG, ymd)
        rents = fetch_rent_trades_all(TARGET_SGG, ymd)
        all_sales.extend(sales)
        all_rents.extend(rents)
        print(f"  {ymd}: 매매 {len(sales)}건, 전월세 {len(rents)}건")
    print(f"=== 수집 완료: 매매 총 {len(all_sales)}건, 전월세 총 {len(all_rents)}건 ===\n")
    return all_sales, all_rents


def check_4_1(all_rents: list[dict]) -> dict:
    """4-1: 순수 전세 비율."""
    pure = [r for r in all_rents if is_pure_jeonse(r)]
    ratio = len(pure) / len(all_rents) if all_rents else 0
    print(f"[4-1] 순수 전세 비율: {len(pure)}/{len(all_rents)} = {ratio*100:.1f}%")

    # 산출물 1: 순수 전세 필터 결과
    path = os.path.join(OUTPUT_DIR, "1_순수전세_필터_결과.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["아파트명", "전용면적", "보증금", "월세금액", "순수전세여부"])
        for r in all_rents:
            writer.writerow([
                r.get("aptNm"), r.get("excluUseAr"), r.get("deposit"),
                r.get("monthlyRent"), "Y" if is_pure_jeonse(r) else "N",
            ])
    print(f"  → 산출물 저장: {path}")
    return {"total": len(all_rents), "pure_count": len(pure), "ratio": ratio, "pure_list": pure}


def check_4_2(all_sales: list[dict], pure_jeonse: list[dict]) -> dict:
    """4-2 [최우선]: 매매∩전세 동시 확보율. 후보 중 상위 10개를 아이템으로 선정."""
    valid_sales = [s for s in all_sales if not is_canceled_deal(s)]

    sale_groups = defaultdict(list)
    for s in valid_sales:
        area = to_float(s.get("excluUseAr"))
        if area is None:
            continue
        sale_groups[make_key(s.get("aptNm", ""), area)].append(s)

    jeonse_groups = defaultdict(list)
    for r in pure_jeonse:
        area = to_float(r.get("excluUseAr"))
        if area is None:
            continue
        jeonse_groups[make_key(r.get("aptNm", ""), area)].append(r)

    # 매매와 전세 둘 다 있는 키만 후보로, 거래건수 합이 많은 순으로 상위 10개 선정
    common_keys = set(sale_groups.keys()) & set(jeonse_groups.keys())
    ranked = sorted(
        common_keys,
        key=lambda k: len(sale_groups[k]) + len(jeonse_groups[k]),
        reverse=True,
    )
    target_items = ranked[:10]

    print(f"[4-2] 매매∩전세 교집합 키 총 {len(common_keys)}개 중 상위 10개를 아이템으로 선정")

    detail = []
    passed = 0
    for key in target_items:
        sale_count = len(sale_groups[key])
        jeonse_count = len(jeonse_groups[key])
        ok = sale_count >= 3 and jeonse_count >= 3
        passed += ok
        detail.append({
            "key": key, "sale_count": sale_count, "jeonse_count": jeonse_count,
            "pass": "Y" if ok else "N",
        })

    rate = passed / len(target_items) if target_items else 0
    print(f"[4-2] 아이템 10개 중 매매3건+전세3건 모두 확보: {passed}/{len(target_items)} = {rate*100:.1f}%")
    print(f"[4-2] 통과 기준(60% 이상): {'✅ 통과' if rate >= 0.6 else '❌ 실패 → Plan B로 전환 필요'}")

    # 산출물 2: 매매&전세 교집합표
    path = os.path.join(OUTPUT_DIR, "2_매매전세_교집합표.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["아이템(아파트_면적)", "매매건수(12개월)", "순수전세건수(12개월)", "3건이상 통과"])
        for d in detail:
            writer.writerow([d["key"], d["sale_count"], d["jeonse_count"], d["pass"]])
    print(f"  → 산출물 저장: {path}")

    return {
        "rate": rate, "pass_60pct": rate >= 0.6, "target_items": target_items,
        "sale_groups": sale_groups, "jeonse_groups": jeonse_groups, "detail": detail,
    }


def check_4_3(all_rents: list[dict], target_items: list[str]) -> dict:
    """4-3: 갱신 계약의 영향."""
    rent_by_key = defaultdict(list)
    for r in all_rents:
        area = to_float(r.get("excluUseAr"))
        if area is None or not is_pure_jeonse(r):
            continue
        rent_by_key[make_key(r.get("aptNm", ""), area)].append(r)

    rows = []
    must_exclude_any = False
    for key in target_items:
        items = rent_by_key.get(key, [])
        new_c = [to_int(x.get("deposit")) for x in items if x.get("contractType") == "신규" and to_int(x.get("deposit")) is not None]
        renewal_c = [to_int(x.get("deposit")) for x in items if x.get("contractType") == "갱신" and to_int(x.get("deposit")) is not None]
        if not new_c or not renewal_c:
            rows.append({"key": key, "comparable": "N", "new_avg": None, "renewal_avg": None, "diff_pct": None})
            continue
        new_avg = statistics.mean(new_c)
        renewal_avg = statistics.mean(renewal_c)
        diff_pct = (new_avg - renewal_avg) / new_avg * 100 if new_avg else 0
        must_exclude = diff_pct >= 10
        must_exclude_any = must_exclude_any or must_exclude
        rows.append({
            "key": key, "comparable": "Y", "new_avg": round(new_avg),
            "renewal_avg": round(renewal_avg), "diff_pct": round(diff_pct, 1),
            "must_exclude": "Y" if must_exclude else "N",
        })

    print(f"[4-3] 갱신/신규 비교 가능한 아이템: {sum(1 for r in rows if r['comparable']=='Y')}/{len(target_items)}")
    print(f"[4-3] 갱신 제외가 필요한(10%p 이상 차이) 아이템 존재 여부: {'있음 → 4-2 재계산 필요' if must_exclude_any else '없음'}")

    # 산출물 3: 갱신영향 리포트
    path = os.path.join(OUTPUT_DIR, "3_갱신영향_리포트.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["아이템", "비교가능", "신규평균보증금", "갱신평균보증금", "차이(%)", "제외필요"])
        for r in rows:
            writer.writerow([r["key"], r["comparable"], r.get("new_avg"), r.get("renewal_avg"),
                              r.get("diff_pct"), r.get("must_exclude", "-")])
    print(f"  → 산출물 저장: {path}")

    return {"rows": rows, "must_exclude_any": must_exclude_any}


def check_4_4(sale_groups: dict, jeonse_groups: dict, target_items: list[str]) -> dict:
    """4-4: 매매와 전세의 시점 정렬."""
    def latest_date(items, y_key="dealYear", m_key="dealMonth"):
        dates = [(to_int(i.get(y_key)), to_int(i.get(m_key))) for i in items]
        dates = [d for d in dates if d[0] and d[1]]
        return max(dates) if dates else None

    aligned_count = 0
    rows = []
    for key in target_items:
        sale_latest = latest_date(sale_groups.get(key, []))
        jeonse_latest = latest_date(jeonse_groups.get(key, []))
        if not sale_latest or not jeonse_latest:
            rows.append({"key": key, "gap_months": None, "aligned": "N"})
            continue
        gap = abs((sale_latest[0] * 12 + sale_latest[1]) - (jeonse_latest[0] * 12 + jeonse_latest[1]))
        aligned = gap <= 6
        aligned_count += aligned
        rows.append({"key": key, "gap_months": gap, "aligned": "Y" if aligned else "N"})

    rate = aligned_count / len(target_items) if target_items else 0
    print(f"[4-4] 매매-전세 최근 거래일 6개월 이내 정렬: {aligned_count}/{len(target_items)} = {rate*100:.1f}%")
    print(f"[4-4] 통과 기준(70% 이상): {'✅ 통과' if rate >= 0.7 else '⚠️ 미달 — 화면에 기준시점 표기 규칙 필요'}")
    return {"rate": rate, "rows": rows}


def remove_outliers_iqr(values: list[float]) -> tuple[list[float], int]:
    """IQR(사분위 범위) 1.5배 규칙으로 이상치를 제거.
    표본이 4개 미만이면 IQR 계산이 무의미하므로 그대로 반환.
    반환값: (이상치 제거된 리스트, 제거된 건수)
    """
    if len(values) < 4:
        return values, 0
    sorted_v = sorted(values)
    q1 = statistics.median(sorted_v[: len(sorted_v) // 2])
    q3 = statistics.median(sorted_v[(len(sorted_v) + 1) // 2:])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtered = [v for v in values if lower <= v <= upper]
    return filtered, len(values) - len(filtered)


def check_dealing_type_composition(all_sales: list[dict]) -> dict:
    """거래유형(직거래/중개거래) 구성비 확인 — 지금까지 확인한 적 없던 항목."""
    valid = [s for s in all_sales if not is_canceled_deal(s)]
    direct = [s for s in valid if s.get("dealingGbn") == "직거래"]
    ratio = len(direct) / len(valid) if valid else 0
    print(f"[추가 검증] 직거래 비율: {len(direct)}/{len(valid)} = {ratio*100:.1f}%")
    if ratio >= 0.1:
        print("  ⚠️ 직거래 비중이 10% 이상 — 시세 왜곡 가능성 있음, 제외 여부 팀 논의 필요")
    return {"direct_count": len(direct), "total": len(valid), "ratio": ratio}


def check_4_5(sale_groups: dict, jeonse_groups: dict, target_items: list[str]) -> dict:
    """4-5: 전세가율의 변별력.
    평균과 중앙값을 둘 다 계산하고, 이상치(IQR) 제거 전후를 비교해서
    어느 대표값이 더 안정적인지 함께 검증한다.
    """
    rows = []
    ratios_mean = []
    ratios_median = []
    for key in target_items:
        raw_sales = [to_int(s.get("dealAmount")) for s in sale_groups.get(key, []) if to_int(s.get("dealAmount"))]
        raw_jeonses = [to_int(r.get("deposit")) for r in jeonse_groups.get(key, []) if to_int(r.get("deposit"))]
        if not raw_sales or not raw_jeonses:
            rows.append({"key": key, "sale_mean": None, "sale_median": None, "jeonse_mean": None,
                         "jeonse_median": None, "ratio_mean": None, "ratio_median": None,
                         "sale_outliers_removed": 0, "jeonse_outliers_removed": 0})
            continue

        sales_f, sale_out = remove_outliers_iqr(raw_sales)
        jeonses_f, jeonse_out = remove_outliers_iqr(raw_jeonses)

        sale_mean = statistics.mean(sales_f)
        sale_median = statistics.median(sales_f)
        jeonse_mean = statistics.mean(jeonses_f)
        jeonse_median = statistics.median(jeonses_f)

        ratio_mean = jeonse_mean / sale_mean * 100
        ratio_median = jeonse_median / sale_median * 100
        ratios_mean.append(ratio_mean)
        ratios_median.append(ratio_median)

        rows.append({
            "key": key, "sale_mean": round(sale_mean), "sale_median": round(sale_median),
            "jeonse_mean": round(jeonse_mean), "jeonse_median": round(jeonse_median),
            "ratio_mean": round(ratio_mean, 1), "ratio_median": round(ratio_median, 1),
            "sale_outliers_removed": sale_out, "jeonse_outliers_removed": jeonse_out,
        })

    spread_mean = (max(ratios_mean) - min(ratios_mean)) if len(ratios_mean) >= 2 else 0
    spread_median = (max(ratios_median) - min(ratios_median)) if len(ratios_median) >= 2 else 0

    print(f"[4-5] 평균 기준 전세가율: {[round(r,1) for r in ratios_mean]}")
    print(f"[4-5] 중앙값 기준 전세가율: {[round(r,1) for r in ratios_median]}")
    print(f"[4-5] 평균 기준 변별력(최대-최소): {spread_mean:.1f}%p / 중앙값 기준: {spread_median:.1f}%p")

    max_diff = max(abs(m - med) for m, med in zip(ratios_mean, ratios_median)) if ratios_mean else 0
    print(f"[4-5] 평균과 중앙값의 최대 차이: {max_diff:.1f}%p", end=" ")
    if max_diff >= 3:
        print("→ ⚠️ 차이가 커서 이상치 영향 의심됨. 중앙값 사용을 권장")
    else:
        print("→ 평균/중앙값 차이 작음, 둘 중 어느 쪽을 써도 큰 차이 없음")

    total_outliers = sum(r.get("sale_outliers_removed", 0) + r.get("jeonse_outliers_removed", 0) for r in rows)
    print(f"[4-5] IQR 기준 제거된 이상치 총 건수: {total_outliers}건")

    pass_15pp = spread_median >= 15  # 중앙값 기준으로 최종 판정
    print(f"[4-5] 통과 기준(중앙값 기준 15%p 이상): {'✅ 통과' if pass_15pp else '❌ 실패'}")

    # 산출물 4: 전세가율 분포 (평균/중앙값 둘 다 기록)
    path = os.path.join(OUTPUT_DIR, "4_전세가율_분포.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "아이템", "매매평균(만원)", "매매중앙값(만원)", "전세평균(만원)", "전세중앙값(만원)",
            "전세가율_평균기준(%)", "전세가율_중앙값기준(%)", "매매이상치제거건수", "전세이상치제거건수",
        ])
        for r in rows:
            writer.writerow([
                r["key"], r.get("sale_mean"), r.get("sale_median"), r.get("jeonse_mean"), r.get("jeonse_median"),
                r.get("ratio_mean"), r.get("ratio_median"), r.get("sale_outliers_removed"), r.get("jeonse_outliers_removed"),
            ])
    print(f"  → 산출물 저장: {path}")

    return {"spread": spread_median, "pass_15pp": pass_15pp, "rows": rows,
            "spread_mean": spread_mean, "max_mean_median_diff": max_diff}


def final_judgement(r42: dict, r45: dict, renewal_flag: bool) -> str:
    print("\n" + "=" * 50)
    print("최종 판정")
    print("=" * 50)
    if not r42["pass_60pct"]:
        print("→ 4-2 실패(60% 미만): 단지 단위로 상향 (Plan B-1)")
        return "PLAN_B_단지단위"
    if renewal_flag:
        print("→ 4-3에서 갱신 제외 필요 발견: 4-2를 갱신 제외 후 재계산 권장")
    if not r45["pass_15pp"]:
        print("→ 4-5 실패(15%p 미만): 변별력 부족, 단지 단위로 상향 (Plan B-1)")
        return "PLAN_B_단지단위"
    print("→ 4-2, 4-5 모두 통과: 아이템 단위 유지 가능")
    return "아이템_단위_유지"


if __name__ == "__main__":
    all_sales, all_rents = collect_all_data()

    check_dealing_type_composition(all_sales)  # 오늘 처음 추가된 검증 항목

    r41 = check_4_1(all_rents)
    r42 = check_4_2(all_sales, r41["pure_list"])
    r43 = check_4_3(all_rents, r42["target_items"])
    r44 = check_4_4(r42["sale_groups"], r42["jeonse_groups"], r42["target_items"])
    r45 = check_4_5(r42["sale_groups"], r42["jeonse_groups"], r42["target_items"])

    result = final_judgement(r42, r45, r43["must_exclude_any"])
    print(f"\n최종 결론: {result}")
    print(f"\n산출물 4개는 {OUTPUT_DIR} 폴더에 저장되었습니다.")
