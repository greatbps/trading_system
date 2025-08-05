# SQLAlchemy Models Usage Guide

이 문서는 AI 주식 트레이딩 시스템의 SQLAlchemy 모델 사용법을 설명합니다.

## 📋 목차

1. [모델 개요](#모델-개요)
2. [데이터베이스 설정](#데이터베이스-설정)
3. [모델 사용법](#모델-사용법)
4. [관계 및 쿼리](#관계-및-쿼리)
5. [유틸리티 메서드](#유틸리티-메서드)
6. [데이터 검증](#데이터-검증)
7. [성능 최적화](#성능-최적화)

## 🎯 모델 개요

### 핵심 모델 구조
```
Stock (종목 기본정보)
├── FilteredStock (1차 필터링 결과)
│   └── AnalysisResult (2차 분석 결과)
│       └── Trade (매매 내역)
├── Portfolio (포트폴리오)
├── MarketData (시장 데이터)
├── AccountInfo (계좌 정보)
├── SystemLog (시스템 로그)
└── TradingSession (거래 세션)
```

### 8개 주요 테이블
1. **Stock**: 종목 기본 정보
2. **FilteredStock**: HTS 조건검색 결과
3. **AnalysisResult**: AI 정량적 분석 결과  
4. **Trade**: 실제 매매 실행 내역
5. **Portfolio**: 현재 포트폴리오 현황
6. **AccountInfo**: 계좌 잔고 정보
7. **MarketData**: OHLCV 차트 데이터
8. **SystemLog**: 시스템 로그
9. **TradingSession**: 거래 세션 관리

## 🔧 데이터베이스 설정

### 기본 설정
```python
from database.models import create_database_engine, create_all_tables, get_session_factory
from config import DatabaseConfig

# 1. 엔진 생성
engine = create_database_engine(DatabaseConfig.DB_URL, DatabaseConfig.DB_ECHO)

# 2. 테이블 생성
create_all_tables(engine)

# 3. 세션 팩토리 생성
SessionFactory = get_session_factory(engine)

# 4. 세션 사용
session = SessionFactory()
```

### 초기 데이터 설정
```python
from database.models import insert_initial_data

# 주요 종목 데이터 삽입
insert_initial_data(session)
```

## 📊 모델 사용법

### 1. Stock (종목 정보)
```python
from database.models import Stock, Market

# 새 종목 생성
stock = Stock(
    symbol='005930',
    name='삼성전자',
    market=Market.KOSPI,
    sector='IT',
    current_price=75000,
    market_cap=4500000000000
)
stock.save(session)

# 종목 조회
samsung = Stock.get_by_symbol(session, '005930')
active_stocks = Stock.get_active_stocks(session, Market.KOSPI)
```

### 2. FilteredStock (1차 필터링)
```python
from database.models import FilteredStock

# 필터링 결과 저장
filtered = FilteredStock(
    stock_id=stock.id,
    strategy_name='momentum',
    filtered_date=datetime.now(),
    current_price=75000,
    volume=1000000
)
filtered.save(session)

# 전략별 조회
momentum_stocks = FilteredStock.get_by_strategy_date(
    session, 'momentum', datetime.now()
)
```

### 3. AnalysisResult (2차 분석)  
```python
from database.models import AnalysisResult, AnalysisGrade, RiskLevel

# 분석 결과 저장
analysis = AnalysisResult(
    filtered_stock_id=filtered.id,
    stock_id=stock.id,
    total_score=85.5,
    final_grade=AnalysisGrade.BUY,
    news_score=15.0,
    technical_score=35.5,
    supply_demand_score=35.0,
    rsi_14=65.2,
    risk_level=RiskLevel.MEDIUM,
    is_selected=True
)
analysis.save(session)

# 선정된 종목 조회
selected_stocks = AnalysisResult.get_selected_stocks(session)
high_score_stocks = AnalysisResult.get_by_score_range(session, 80, 100)
```

### 4. Trade (매매 내역)
```python
from database.models import Trade, TradeType, OrderType, OrderStatus

# 거래 생성
trade = Trade(
    stock_id=stock.id,
    trade_type=TradeType.BUY,
    order_type=OrderType.LIMIT,
    order_quantity=100,
    order_price=75000,
    executed_price=74900,
    executed_quantity=100,
    order_time=datetime.now(),
    execution_time=datetime.now(),
    order_status=OrderStatus.FILLED
)
trade.save(session)

# 거래 조회
recent_trades = Trade.get_recent_trades(session, days=30)
pending_orders = Trade.get_by_status(session, OrderStatus.PENDING)

# 거래 금액 계산
total_amount = trade.get_total_amount()  # 수수료 포함
is_complete = trade.is_completed()       # 체결 완료 여부
```

### 5. Portfolio (포트폴리오)
```python
from database.models import Portfolio, PortfolioStatus

# 포트폴리오 생성
portfolio = Portfolio(
    stock_id=stock.id,
    quantity=100,
    avg_price=74900,
    total_cost=7490000
)

# 현재가 업데이트
portfolio.update_current_values(75000)

# 포지션 추가
portfolio.add_position(50, 76000)  # 50주 76,000원에 추가 매수

# 포지션 감소
realized_pnl = portfolio.reduce_position(30, 77000)  # 30주 매도

portfolio.save(session)

# 포트폴리오 조회
open_positions = Portfolio.get_open_positions(session)
samsung_position = Portfolio.get_by_symbol(session, '005930')
```

### 6. MarketData (시장 데이터)
```python
from database.models import MarketData

# 시장 데이터 저장
market_data = MarketData(
    stock_id=stock.id,
    symbol='005930',
    timeframe='1d',
    open_price=74000,
    high_price=76000,
    low_price=73500,
    close_price=75000,
    volume=5000000,
    datetime=datetime.now()
)
market_data.save(session)

# 데이터 조회
latest_data = MarketData.get_latest_data(session, '005930', '1d')
ohlcv_data = MarketData.get_ohlcv_data(
    session, '005930', '1d', start_date, end_date
)
```

### 7. AccountInfo (계좌 정보)
```python
from database.models import AccountInfo

# 계좌 정보 생성
account = AccountInfo(
    account_number='12345678',
    cash_balance=10000000,
    total_assets=17490000,
    stock_value=7490000,
    available_cash=2500000
)

# 잔고 업데이트
account.update_balances(
    cash_balance=9500000,
    stock_value=8000000,
    available_cash=1500000
)

# 매수가능금액 확인
buying_power = account.get_buying_power()

account.save(session)
```

### 8. SystemLog (시스템 로그)
```python
from database.models import SystemLog, LogLevel

# 로그 생성
info_log = SystemLog.log_info(
    session=session,
    module='trading_system',
    function='execute_trade',
    message='Trade executed successfully',
    extra_data={'trade_id': 123, 'amount': 1000000}
)

error_log = SystemLog.log_error(
    session=session,
    module='kis_collector',
    function='get_market_data',
    message='API rate limit exceeded',
    error_details='HTTP 429 Too Many Requests'
)

# 로그 조회
recent_errors = SystemLog.get_recent_logs(session, LogLevel.ERROR, hours=24)
```

### 9. TradingSession (거래 세션)
```python
from database.models import TradingSession, SessionStatus

# 새 세션 생성
session_obj = TradingSession.create_new_session(
    session=session,
    session_id='MOMENTUM_20240804_001',
    strategy='momentum',
    initial_capital=10000000,
    max_positions=5
)

# 성과 업데이트
session_obj.update_performance(
    total_trades=10,
    winning_trades=7,
    total_pnl=500000,
    max_drawdown=-200000
)

# 승률 계산
win_rate = session_obj.get_win_rate()  # 70.0

# 세션 종료
session_obj.end_session()

# 활성 세션 조회
active_session = TradingSession.get_active_session(session)
```

## 🔗 관계 및 쿼리

### 관계 활용
```python
# Stock -> FilteredStock -> AnalysisResult -> Trade 체인
stock = session.query(Stock).filter(Stock.symbol == '005930').first()

# 해당 종목의 모든 필터링 결과
for filtered in stock.filtered_stocks:
    print(f"Strategy: {filtered.strategy_name}")
    
    # 각 필터링 결과의 분석
    if filtered.analysis_result:
        analysis = filtered.analysis_result
        print(f"Score: {analysis.total_score}")
        
        # 분석 기반 거래들
        for trade in analysis.trades:
            print(f"Trade: {trade.trade_type.value} {trade.order_quantity}주")

# 포트폴리오와 종목 정보
for position in Portfolio.get_open_positions(session):
    stock = position.stock
    print(f"{stock.name}: {position.quantity}주 보유")
```

### 복합 쿼리
```python
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, desc

# 조인을 통한 복합 조회
high_score_trades = session.query(Trade).join(AnalysisResult).filter(
    AnalysisResult.total_score >= 80,
    Trade.order_status == OrderStatus.FILLED
).all()

# 이거로드를 통한 N+1 쿼리 방지
stocks_with_data = session.query(Stock).options(
    joinedload(Stock.filtered_stocks).joinedload(FilteredStock.analysis_result),
    joinedload(Stock.portfolio_positions)
).all()

# 집계 쿼리
from sqlalchemy import func

# 종목별 거래 횟수
trade_counts = session.query(
    Stock.symbol,
    Stock.name,
    func.count(Trade.id).label('trade_count')
).join(Trade).group_by(Stock.id).all()
```

## ⚙️ 유틸리티 메서드

### Stock 유틸리티
```python
# 최신 가격 조회 (MarketData에서)
latest_price = stock.get_latest_price(session)

# 활성 종목만 조회
active_kospi = Stock.get_active_stocks(session, Market.KOSPI)
```

### Portfolio 유틸리티
```python
# 포지션 관리
portfolio.add_position(100, 75000)        # 매수
realized_pnl = portfolio.reduce_position(50, 77000)  # 매도

# 평가 정보 업데이트
portfolio.update_current_values(76000)
```

### Trade 유틸리티
```python
# 거래 금액 계산 (수수료 포함)
total_amount = trade.get_total_amount()

# 체결 상태 확인
is_completed = trade.is_completed()
```

## ✅ 데이터 검증

### 자동 검증
```python
# 종목코드 검증 (6자리 숫자)
try:
    stock = Stock(symbol='12345', name='잘못된 종목')  # ValueError 발생
except ValueError as e:
    print(f"검증 오류: {e}")

# 가격 양수 검증
try:
    stock = Stock(symbol='005930', name='삼성전자', current_price=-1000)
except ValueError as e:
    print(f"가격 검증 오류: {e}")

# 분석 점수 범위 검증 (0-100)
try:
    analysis = AnalysisResult(total_score=150)  # ValueError 발생
except ValueError as e:
    print(f"점수 검증 오류: {e}")
```

### 데이터베이스 제약 조건
- 종목코드: 6자리 숫자 필수
- 가격: 양수만 허용
- 수량: 음수 불가
- 분석점수: 0-100 범위
- 외래키 제약조건으로 데이터 무결성 보장

## 🚀 성능 최적화

### 인덱스 최적화
```python
# 자주 사용되는 쿼리용 인덱스들이 자동 생성됨:
# - 종목코드 (symbol)
# - 날짜 필드들 (created_at, filtered_date, order_time 등)
# - 상태 필드들 (is_active, order_status, final_grade 등)
# - 외래키 관계 필드들
```

### 배치 작업
```python
# 대량 데이터 삽입
stocks_data = [
    Stock(symbol='005930', name='삼성전자', market=Market.KOSPI),
    Stock(symbol='000660', name='SK하이닉스', market=Market.KOSPI),
    # ... 더 많은 데이터
]

# 배치 삽입
session.bulk_save_objects(stocks_data)
session.commit()

# 배치 업데이트
session.bulk_update_mappings(Stock, [
    {'id': 1, 'current_price': 75000},
    {'id': 2, 'current_price': 125000},
])
session.commit()
```

### 쿼리 최적화
```python
# N+1 쿼리 방지
stocks = session.query(Stock).options(
    joinedload(Stock.filtered_stocks),
    joinedload(Stock.portfolio_positions)
).all()

# 필요한 컬럼만 조회
stock_prices = session.query(Stock.symbol, Stock.current_price).all()

# 페이지네이션
page_size = 50
offset = page * page_size
stocks = session.query(Stock).offset(offset).limit(page_size).all()
```

## 🔒 트랜잭션 관리

### 안전한 트랜잭션
```python
try:
    # 복합 작업
    stock = Stock(symbol='005930', name='삼성전자', market=Market.KOSPI)
    session.add(stock)
    session.flush()  # ID 할당을 위해
    
    portfolio = Portfolio(
        stock_id=stock.id,
        quantity=100,
        avg_price=75000,
        total_cost=7500000
    )
    session.add(portfolio)
    
    session.commit()  # 모든 변경사항 커밋
    
except Exception as e:
    session.rollback()  # 오류 시 롤백
    raise e
finally:
    session.close()
```

### 컨텍스트 매니저 사용
```python
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# 사용 예시
with get_db_session() as session:
    stock = Stock(symbol='005930', name='삼성전자', market=Market.KOSPI)
    stock.save(session)
```

## 📝 주의사항

1. **한국 원화 처리**: 모든 가격은 정수형(Integer)으로 저장
2. **시간대**: 모든 DateTime은 한국 시간(Asia/Seoul) 기준
3. **외래키 제약**: 관련 데이터 삭제 시 CASCADE 설정 확인
4. **열거형 사용**: 상태값들은 Enum으로 타입 안전성 보장
5. **세션 관리**: 작업 완료 후 반드시 세션 닫기

이 가이드를 통해 AI 주식 트레이딩 시스템의 데이터베이스를 효율적으로 활용하실 수 있습니다.