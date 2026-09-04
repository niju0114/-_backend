"""단지 검색 엔드포인트 (B-01). 팀 API 명세 기준으로 필드명 통일."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from app.database import get_db
from app.db_models import ComplexMaster

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search_complex(keyword: str, db: Session = Depends(get_db)):
    """단지명 또는 법정동명으로 검색. 예: /search?keyword=래미안 또는 /search?keyword=옥수동
    B-01 명세: keyword 파라미터, complex_id/complex_name/legal_dong_name/address/build_year 반환.
    """
    rows = db.execute(
        select(ComplexMaster).where(
            or_(
                ComplexMaster.apt_nm.ilike(f"%{keyword}%"),
                ComplexMaster.umd_nm.ilike(f"%{keyword}%"),
            )
        ).limit(20)
    ).scalars().all()

    return [
        {
            "complex_id": r.id,
            "complex_name": r.apt_nm,
            "legal_dong_name": r.umd_nm,
            # 팀 스키마에 별도 주소 필드가 없어서 법정동+지번으로 임시 구성 (정식 주소 데이터 아님)
            "address": f"{r.umd_nm} {r.jibun}" if r.jibun else r.umd_nm,
            "build_year": r.build_year,
        }
        for r in rows
    ]
