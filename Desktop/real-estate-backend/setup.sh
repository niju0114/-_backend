#!/bin/bash
# 한 번에 실행하는 초기 설정 스크립트
# 사용법: bash setup.sh

set -e  # 중간에 하나라도 실패하면 즉시 멈춤

echo "1/5 가상환경 생성 (Python 3.12)..."
if [ ! -d ".venv" ]; then
  uv venv --python 3.12
else
  echo "  이미 .venv가 있어서 건너뜁니다."
fi

echo "2/5 가상환경 활성화..."
source .venv/bin/activate

echo "3/5 패키지 설치..."
uv pip install -r requirements.txt

echo "4/5 .env 파일 생성..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  # 국토부 키는 이미 알고 있으니 자동으로 채워둡니다.
  sed -i.bak 's|MOLIT_API_KEY=|MOLIT_API_KEY=uKQuy77kMUVZi%2FRy0S2OC13joNE0dCt2IF9J4z1P%2BR%2BxXGdmNZBKNGy0aJvfZJptcw4cq%2BWybcGE9DDIkPLF9Q%3D%3D|' .env
  rm -f .env.bak
  echo "  .env 생성 완료. 국토부 키는 자동으로 채워졌습니다."
else
  echo "  이미 .env가 있어서 건너뜁니다."
fi

echo "5/5 완료!"
echo ""
echo "=================================================="
echo "딱 하나만 직접 하셔야 합니다:"
echo "  .env 파일을 열어서 아래 두 줄을 채워주세요 (Supabase 값은 제가 모릅니다)"
echo "  SUPABASE_URL=..."
echo "  SUPABASE_KEY=..."
echo ""
echo "다 채우셨으면 이 명령어로 데이터 수집을 시작하세요:"
echo "  source .venv/bin/activate && python ingest/batch_collect.py"
echo "=================================================="
