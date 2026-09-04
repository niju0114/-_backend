"""FastAPI 앱 진입점.
실행: uvicorn app.main:app --reload
확인: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import search, items, macro, complexes

app = FastAPI(title="부동산 실거래 대시보드 API")

# 프론트엔드(Next.js 등)에서 호출 가능하도록 CORS 허용
# 배포 시에는 allow_origins를 실제 프론트 도메인으로 좁히는 것을 권장
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api/v1")
app.include_router(complexes.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")
app.include_router(macro.router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "부동산 실거래 대시보드 API 서버 정상 동작 중"}
