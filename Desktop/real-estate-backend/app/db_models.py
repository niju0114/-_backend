"""SQLAlchemy ORM 모델. ingest/schema.sql과 동일한 구조를 파이썬 클래스로 정의.

이 파일의 모델로 테이블을 만들면(ingest/create_tables.py 실행),
Supabase SQL Editor에 수동으로 SQL을 붙여넣을 필요가 없다.
"""
from sqlalchemy import Column, BigInteger, Integer, String, Numeric, Date, TIMESTAMP, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RawTradeSale(Base):
    __tablename__ = "raw_trades_sale"
    __table_args__ = (
        UniqueConstraint(
            "sgg_cd", "umd_nm", "jibun", "apt_nm", "exclu_use_ar",
            "floor", "deal_amount", "deal_year", "deal_month", "deal_day",
            name="uq_raw_trade_sale_natural_key",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sgg_cd = Column(String(5))
    umd_nm = Column(String(50))
    jibun = Column(String(20))
    apt_nm = Column(String(100))
    build_year = Column(Integer)
    exclu_use_ar = Column(Numeric(6, 2))
    floor = Column(Integer)
    deal_amount = Column(BigInteger)
    deal_year = Column(Integer)
    deal_month = Column(Integer)
    deal_day = Column(Integer)
    dealing_gbn = Column(String(20))
    cdeal_type = Column(String(10))
    cdeal_day = Column(String(20))
    created_at = Column(TIMESTAMP, server_default=func.now())


class RawTradeRent(Base):
    __tablename__ = "raw_trades_rent"
    __table_args__ = (
        UniqueConstraint(
            "sgg_cd", "umd_nm", "jibun", "apt_nm", "exclu_use_ar",
            "floor", "deposit", "monthly_rent", "deal_year", "deal_month",
            name="uq_raw_trade_rent_natural_key",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sgg_cd = Column(String(5))
    umd_nm = Column(String(50))
    jibun = Column(String(20))
    apt_nm = Column(String(100))
    exclu_use_ar = Column(Numeric(6, 2))
    floor = Column(Integer)
    deposit = Column(BigInteger)
    monthly_rent = Column(BigInteger)
    deal_year = Column(Integer)
    deal_month = Column(Integer)
    contract_type = Column(String(10))
    created_at = Column(TIMESTAMP, server_default=func.now())


class ComplexMaster(Base):
    __tablename__ = "complex_master"
    __table_args__ = (UniqueConstraint("sgg_cd", "umd_nm", "jibun", "apt_nm"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sgg_cd = Column(String(5))
    umd_nm = Column(String(50))
    jibun = Column(String(20))
    apt_nm = Column(String(100))
    build_year = Column(Integer)
    household_cnt = Column(Integer)  # K-apt 없이는 비워둠


class SizeMaster(Base):
    __tablename__ = "size_master"
    __table_args__ = (UniqueConstraint("complex_id", "representative_area"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complex_id = Column(BigInteger, ForeignKey("complex_master.id"))
    representative_area = Column(Numeric(6, 2))
    pyeong = Column(Integer)


class ItemMetricsCache(Base):
    __tablename__ = "item_metrics_cache"

    size_id = Column(BigInteger, ForeignKey("size_master.id"), primary_key=True)
    recent_median_price = Column(BigInteger)  # 팀 정책: 평균이 아니라 중앙값 (구 이름: recent_avg_price)
    min_price = Column(BigInteger)
    max_price = Column(BigInteger)
    price_per_pyeong = Column(BigInteger)
    trade_count_3y = Column(Integer)
    last_trade_date = Column(String(7))  # "YYYY-MM" 형태로 통일 (다른 엔드포인트와 형식 맞춤)
    jeonse_ratio = Column(Numeric(5, 2))
    updated_at = Column(TIMESTAMP, server_default=func.now())
