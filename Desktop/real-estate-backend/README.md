# 부동산 실거래 대시보드 백엔드

국토부 실거래가 API + Supabase(PostgreSQL) + FastAPI 기반 백엔드

## 폴더 구조

```
real-estate-backend/
├── app/                     # FastAPI 애플리케이션
│   ├── main.py              # 앱 진입점
│   ├── config.py            # 환경변수 로드
│   ├── database.py          # Supabase 클라이언트
│   ├── routers/             # 엔드포인트 (기능 단위로 분리)
│   │   ├── search.py        # 단지 검색
│   │   ├── items.py         # 상세조회/비교/갭분석
│   │   └── macro.py         # 거시 데이터(매매가격지수 등)
│   ├── services/            # 외부 API 호출 로직
│   │   ├── molit_api.py     # 국토부 API
│   │   ├── kakao_api.py     # 카카오 주소 정규화
│   │   └── reb_api.py       # 한국부동산원 R-ONE API
│   └── models/
│       └── schemas.py       # Pydantic 응답 모델
├── ingest/                  # 배치 스크립트 (주기 실행용)
│   ├── batch_collect.py     # 국토부 원본 데이터 수집
│   ├── build_master.py      # 단지/평형 마스터 생성
│   └── compute_metrics.py   # 파생 지표 사전계산
├── tests/
├── .env.example             # 환경변수 템플릿 (실제 .env는 커밋 금지)
├── .gitignore
├── requirements.txt
└── README.md
```

## 시작하기

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. .env 파일 생성 (.env.example 참고해서 실제 키 입력)
cp .env.example .env

# 4. 개발 서버 실행
uvicorn app.main:app --reload

# 5. 브라우저에서 확인
# http://localhost:8000/docs  (자동 생성되는 API 문서)
```

## 오늘(8/28) 할 일과의 매핑

| 오늘 작업 | 해당 파일 |
|---|---|
| 국토부 API 호출 테스트 | `app/services/molit_api.py` |
| 카카오 주소 정규화 테스트 | `app/services/kakao_api.py` |
| Supabase 프로젝트 연결 | `app/database.py`, `.env` |

## 다음 단계에서 채울 파일

- `ingest/batch_collect.py`: 9/1~9/2 (전체 데이터 수집)
- `ingest/build_master.py`: 9/2~9/3 (단지/평형 마스터 + K-apt 조인)
- `ingest/compute_metrics.py`: 9/6~9/7 (파생 지표 계산)
- `app/routers/items.py`의 갭분석 엔드포인트: 검증(4-1~4-5) 통과 후 완성
