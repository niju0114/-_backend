"""raw_trades_sale, raw_trades_rent, complex_master, size_master, item_metrics_cache를
전부 비우는 스크립트. TRUNCATE ... RESTART IDENTITY를 써서 ID도 1번부터 다시 시작하게 만든다
(이렇게 해야 테스트할 때 size_id=1 같은 예측 가능한 번호를 계속 쓸 수 있다).

실행: python ingest/reset_data.py
실행하면 "정말 삭제하시겠습니까?"를 묻고, RESET이라고 정확히 입력해야 진행됨.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import get_session


def reset_data():
    print("⚠️  아래 테이블의 데이터를 전부 삭제하고 ID를 1번부터 다시 시작합니다:")
    print("   raw_trades_sale, raw_trades_rent, complex_master, size_master, item_metrics_cache")
    answer = input("정말 진행하려면 RESET 이라고 입력하세요: ")
    if answer != "RESET":
        print("취소되었습니다. 아무것도 삭제되지 않았습니다.")
        return

    with get_session() as session:
        # TRUNCATE ... RESTART IDENTITY: 데이터 삭제 + ID 시퀀스도 1로 리셋
        # CASCADE: 외래키로 연결된 테이블도 함께 처리
        session.execute(text(
            "TRUNCATE TABLE item_metrics_cache, size_master, raw_trades_sale, "
            "raw_trades_rent, complex_master RESTART IDENTITY CASCADE"
        ))
        session.commit()

    print("=== 전체 삭제 완료 (ID도 1번부터 리셋됨) ===")
    print("다음 단계: python ingest/batch_collect.py 부터 다시 실행하세요.")


if __name__ == "__main__":
    reset_data()
