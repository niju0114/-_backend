-- Supabase SQL 편집기에 붙여넣어서 실행하세요.
-- 순서대로 실행 (외래키 참조 관계 때문에 순서 중요)

-- 원본 거래 레코드 (매매)
CREATE TABLE raw_trades_sale (
  id BIGSERIAL PRIMARY KEY,
  sgg_cd VARCHAR(5),
  umd_nm VARCHAR(50),
  jibun VARCHAR(20),
  apt_nm VARCHAR(100),
  build_year INT,
  exclu_use_ar NUMERIC(6,2),
  floor INT,
  deal_amount BIGINT,
  deal_year INT,
  deal_month INT,
  deal_day INT,
  dealing_gbn VARCHAR(20),
  cdeal_type VARCHAR(10),
  cdeal_day VARCHAR(20),
  created_at TIMESTAMP DEFAULT now()
);

-- 원본 거래 레코드 (전월세)
CREATE TABLE raw_trades_rent (
  id BIGSERIAL PRIMARY KEY,
  sgg_cd VARCHAR(5),
  umd_nm VARCHAR(50),
  jibun VARCHAR(20),
  apt_nm VARCHAR(100),
  exclu_use_ar NUMERIC(6,2),
  floor INT,
  deposit BIGINT,
  monthly_rent BIGINT,
  deal_year INT,
  deal_month INT,
  contract_type VARCHAR(10),
  created_at TIMESTAMP DEFAULT now()
);

-- 단지 마스터
CREATE TABLE complex_master (
  id BIGSERIAL PRIMARY KEY,
  sgg_cd VARCHAR(5),
  umd_nm VARCHAR(50),
  jibun VARCHAR(20),
  apt_nm VARCHAR(100),
  build_year INT,
  household_cnt INT,
  UNIQUE(sgg_cd, umd_nm, jibun, apt_nm)
);

-- 평형 마스터
CREATE TABLE size_master (
  id BIGSERIAL PRIMARY KEY,
  complex_id BIGINT REFERENCES complex_master(id),
  representative_area NUMERIC(6,2),
  pyeong INT,
  UNIQUE(complex_id, representative_area)
);

-- 사전계산 지표 캐시
CREATE TABLE item_metrics_cache (
  size_id BIGINT REFERENCES size_master(id) PRIMARY KEY,
  recent_avg_price BIGINT,
  recent_min_price BIGINT,
  recent_max_price BIGINT,
  price_per_pyeong BIGINT,
  trade_count_3y INT,
  last_trade_date DATE,
  jeonse_ratio NUMERIC(5,2),
  updated_at TIMESTAMP DEFAULT now()
);

-- 검색 성능을 위한 인덱스
CREATE INDEX idx_complex_apt_nm ON complex_master(apt_nm);
CREATE INDEX idx_size_complex_id ON size_master(complex_id);
