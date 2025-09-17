# 🗄️ Database Schema Design

## 📋 테이블 설계 명세

### 1. stocks (종목 기본정보)
```sql
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,           -- 종목코드 (005930)
    name VARCHAR(100) NOT NULL,                   -- 종목명 (삼성전자)
    market VARCHAR(10) NOT NULL,                  -- 시장구분 (KOSPI/KOSDAQ)
    sector VARCHAR(50),                           -- 업종
    market_cap BIGINT,                           -- 시가총액
    shares_outstanding BIGINT,                   -- 발행주식수
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_stocks_market ON stocks(market);
```

### 2. filtered_stocks (1차 필터링 결과)
```sql
CREATE TABLE filtered_stocks (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    strategy_name VARCHAR(50) NOT NULL,           -- HTS 조건검색식 이름
    filtered_date DATE NOT NULL,                  -- 필터링 날짜
    hts_condition_name VARCHAR(100),              -- HTS 조건명
    current_price INTEGER,                        -- 현재가
    price_change INTEGER,                         -- 전일대비
    price_change_rate DECIMAL(5,2),              -- 등락률
    volume BIGINT,                               -- 거래량
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(stock_id, strategy_name, filtered_date)
);

CREATE INDEX idx_filtered_stocks_date ON filtered_stocks(filtered_date);
CREATE INDEX idx_filtered_stocks_strategy ON filtered_stocks(strategy_name);
```

### 3. analysis_results (2차 분석 결과)
```sql
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    filtered_stock_id INTEGER REFERENCES filtered_stocks(id),
    
    -- 종합 점수
    total_score DECIMAL(5,2) NOT NULL,           -- 최종 점수 (0-100)
    score_threshold DECIMAL(5,2) DEFAULT 60.0,   -- 통과 기준점
    
    -- 세부 점수
    news_score DECIMAL(5,2) DEFAULT 0,           -- 뉴스 점수 (-50 ~ +50)
    technical_score DECIMAL(5,2) DEFAULT 0,      -- 기술적 분석 점수 (0-50)  
    supply_demand_score DECIMAL(5,2) DEFAULT 0,  -- 수급 점수 (0-50)
    
    -- 기술적 분석 상세
    rsi_14 DECIMAL(5,2),                         -- RSI(14)
    macd_signal VARCHAR(10),                     -- MACD 신호 (BUY/SELL/HOLD)
    supertrend_signal VARCHAR(10),               -- Supertrend 신호
    ema_5 INTEGER,                               -- 5일 지수이동평균
    ema_20 INTEGER,                              -- 20일 지수이동평균
    bollinger_position VARCHAR(10),              -- 볼린저밴드 위치 (UPPER/MIDDLE/LOWER)
    
    -- 뉴스 분석 상세
    positive_news_count INTEGER DEFAULT 0,       -- 긍정 뉴스 개수
    negative_news_count INTEGER DEFAULT 0,       -- 부정 뉴스 개수
    news_keywords TEXT,                          -- 주요 키워드 (JSON)
    
    -- 수급 분석 상세  
    institution_net BIGINT DEFAULT 0,            -- 기관 순매수
    foreign_net BIGINT DEFAULT 0,               -- 외국인 순매수
    individual_net BIGINT DEFAULT 0,            -- 개인 순매수
    
    -- 메타데이터
    analysis_date TIMESTAMP NOT NULL,
    is_selected BOOLEAN DEFAULT FALSE,           -- 최종 선정 여부
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analysis_results_score ON analysis_results(total_score);
CREATE INDEX idx_analysis_results_selected ON analysis_results(is_selected);
CREATE INDEX idx_analysis_results_date ON analysis_results(analysis_date);
```

### 4. trades (매매 내역)
```sql  
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    analysis_result_id INTEGER REFERENCES analysis_results(id),
    
    -- 주문 정보
    order_id VARCHAR(50),                        -- KIS 주문번호
    symbol VARCHAR(10) NOT NULL,                 -- 종목코드
    trade_type VARCHAR(10) NOT NULL,             -- BUY/SELL
    order_type VARCHAR(10) NOT NULL,             -- MARKET/LIMIT
    
    -- 가격/수량 정보
    order_price INTEGER,                         -- 주문가격
    order_quantity INTEGER NOT NULL,             -- 주문수량
    executed_price INTEGER,                      -- 체결가격
    executed_quantity INTEGER DEFAULT 0,         -- 체결수량
    
    -- 상태 정보
    order_status VARCHAR(20) NOT NULL,           -- PENDING/FILLED/CANCELLED/PARTIAL
    
    -- 수수료 및 세금
    commission INTEGER DEFAULT 0,                -- 수수료
    tax INTEGER DEFAULT 0,                      -- 세금
    
    -- 타이밍 정보
    order_time TIMESTAMP NOT NULL,              -- 주문시간
    execution_time TIMESTAMP,                   -- 체결시간
    
    -- 전략 정보
    strategy_name VARCHAR(50),                  -- 사용된 전략
    trigger_reason TEXT,                        -- 매매 사유
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_order_time ON trades(order_time);
CREATE INDEX idx_trades_status ON trades(order_status);
```

### 5. portfolio (포트폴리오 현황)
```sql
CREATE TABLE portfolio (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    
    -- 보유 정보
    quantity INTEGER NOT NULL DEFAULT 0,         -- 보유수량
    avg_price INTEGER NOT NULL,                  -- 평균단가
    total_cost BIGINT NOT NULL,                 -- 총 매수금액
    
    -- 현재가 정보 (실시간 업데이트)
    current_price INTEGER,                       -- 현재가
    market_value BIGINT,                        -- 평가금액
    unrealized_pnl BIGINT,                      -- 평가손익
    unrealized_pnl_rate DECIMAL(5,2),           -- 평가손익률
    
    -- 실현손익 정보
    realized_pnl BIGINT DEFAULT 0,              -- 실현손익
    
    -- 메타데이터
    first_buy_date TIMESTAMP,                   -- 최초매수일
    last_update TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_portfolio_symbol ON portfolio(symbol);
```

### 6. account_info (계좌 정보)
```sql
CREATE TABLE account_info (
    id SERIAL PRIMARY KEY,
    account_number VARCHAR(20) NOT NULL,
    
    -- 잔고 정보
    cash_balance BIGINT NOT NULL,               -- 예수금
    total_assets BIGINT NOT NULL,               -- 총 자산
    stock_value BIGINT NOT NULL,                -- 주식 평가금액
    
    -- 주문 가능 정보
    available_cash BIGINT NOT NULL,             -- 주문가능현금
    loan_amount BIGINT DEFAULT 0,               -- 대출금액
    
    -- 손익 정보 
    daily_pnl BIGINT DEFAULT 0,                 -- 일일손익
    total_pnl BIGINT DEFAULT 0,                 -- 누적손익
    
    -- 업데이트 시간
    update_time TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 7. market_data (시장 데이터 - 차트용)
```sql
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,             -- 1m, 3m, 5m, 15m, 1h, 1d
    
    -- OHLCV 데이터
    open_price INTEGER NOT NULL,
    high_price INTEGER NOT NULL, 
    low_price INTEGER NOT NULL,
    close_price INTEGER NOT NULL,
    volume BIGINT NOT NULL,
    
    -- 거래대금
    trade_amount BIGINT,
    
    -- 시간 정보
    datetime TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(symbol, timeframe, datetime)
);

CREATE INDEX idx_market_data_symbol_time ON market_data(symbol, timeframe, datetime);
```

### 8. system_logs (시스템 로그)
```sql
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(10) NOT NULL,             -- INFO/WARNING/ERROR
    module_name VARCHAR(50),                    -- 모듈명
    function_name VARCHAR(50),                  -- 함수명
    message TEXT NOT NULL,                      -- 로그 메시지
    error_details TEXT,                         -- 오류 상세
    execution_time DECIMAL(10,6),               -- 실행시간(초)
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_system_logs_level ON system_logs(log_level);
CREATE INDEX idx_system_logs_time ON system_logs(created_at);
```

## 🔄 비즈니스 로직 흐름

### 1. 일일 워크플로우
```
1. HTS 조건검색 → filtered_stocks 테이블 저장
2. 2차 분석 실행 → analysis_results 테이블 저장  
3. 최종 선정종목 → is_selected = TRUE
4. 실시간 모니터링 → market_data 수집
5. 매매 신호 감지 → trades 테이블 저장
6. 포트폴리오 업데이트 → portfolio 테이블 갱신
```

### 2. 성능 최적화
```sql
-- 파티셔닝 (대용량 데이터 대비)
CREATE TABLE market_data_202501 PARTITION OF market_data 
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 인덱스 최적화
CREATE INDEX CONCURRENTLY idx_trades_symbol_date ON trades(symbol, DATE(order_time));
```

### 3. 데이터 정리 정책
```sql
-- 오래된 시장 데이터 정리 (1개월 이상)
DELETE FROM market_data 
WHERE datetime < NOW() - INTERVAL '1 month' 
AND timeframe IN ('1m', '3m');

-- 시스템 로그 정리 (1주일 이상)  
DELETE FROM system_logs 
WHERE created_at < NOW() - INTERVAL '1 week';
```

## 📊 초기 데이터 설정

### 주요 지수 및 ETF
```sql
INSERT INTO stocks (symbol, name, market, sector) VALUES
('005930', '삼성전자', 'KOSPI', 'IT'),
('000660', 'SK하이닉스', 'KOSPI', 'IT'),
('035420', 'NAVER', 'KOSPI', 'IT'),
('005490', 'POSCO홀딩스', 'KOSPI', '철강'),
('068270', '셀트리온', 'KOSPI', '바이오');
```

이제 서브 에이전트에게 이 스키마를 기반으로 SQLAlchemy 모델 클래스 구현을 위임하겠습니다!