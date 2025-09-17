# SQLAlchemy Models for AI Trading System

## 📋 개요

AI 주식 트레이딩 시스템을 위한 완전한 SQLAlchemy 데이터베이스 모델 구현입니다.

## 🏗️ 아키텍처

### 데이터베이스 스키마
```
Stock (종목 기본정보) 
├── FilteredStock (1차 필터링) 
│   └── AnalysisResult (2차 분석)
│       └── Trade (매매 내역)
├── Portfolio (포트폴리오)
├── MarketData (시장 데이터)
├── AccountInfo (계좌 정보)
├── SystemLog (시스템 로그)
└── TradingSession (거래 세션)
```

### 9개 핵심 모델
1. **Stock**: 종목 기본 정보 및 재무 지표
2. **FilteredStock**: HTS 조건검색 1차 필터링 결과
3. **AnalysisResult**: AI 정량적 분석 2차 필터링 결과
4. **Trade**: 실제 매매 거래 내역
5. **Portfolio**: 현재 포트폴리오 보유 현황
6. **AccountInfo**: 계좌 잔고 및 자산 정보
7. **MarketData**: OHLCV 차트 데이터
8. **SystemLog**: 시스템 운영 로그
9. **TradingSession**: 거래 세션 및 성과 관리

## ✨ 주요 특징

### 완전한 타입 안전성
- **Enum 클래스**: 모든 상태값에 대한 타입 안전성
- **Type Hints**: 모든 메서드와 속성에 완전한 타입 힌트
- **Validation**: SQLAlchemy validators로 데이터 무결성 보장

### 한국 주식시장 최적화
- **정수형 가격**: 한국 원화 소수점 없음 반영
- **6자리 종목코드**: 한국 주식 종목코드 형식 검증
- **시장구분**: KOSPI, KOSDAQ, KONEX 지원
- **수급분석**: 기관/외국인/개인 순매수 데이터

### 비즈니스 로직 내장
- **포트폴리오 관리**: 평균단가, 실현/미실현 손익 자동 계산
- **거래 검증**: 수량, 가격 유효성 자동 검사
- **관계 관리**: 외래키와 cascade 옵션으로 데이터 일관성

### 성능 최적화
- **인덱스**: 자주 사용되는 컬럼에 자동 인덱스 생성
- **제약조건**: 데이터베이스 레벨 검증으로 성능 향상
- **배치 작업**: 대량 데이터 처리 지원

## 🚀 사용법

### 기본 설정
```python
from database.models import *
from config import DatabaseConfig

# 엔진 생성 및 테이블 생성
engine = create_database_engine(DatabaseConfig.DB_URL)
create_all_tables(engine)

# 세션 팩토리 생성
SessionFactory = get_session_factory(engine)
session = SessionFactory()
```

### 실제 워크플로우 예시
```python
# 1. 종목 등록
stock = Stock(
    symbol='005930',
    name='삼성전자', 
    market=Market.KOSPI,
    current_price=75000
)
stock.save(session)

# 2. 1차 필터링 (HTS 조건검색)
filtered = FilteredStock(
    stock_id=stock.id,
    strategy_name='momentum',
    filtered_date=datetime.now(),
    current_price=75000
)
filtered.save(session)

# 3. 2차 분석 (AI 정량분석)
analysis = AnalysisResult(
    filtered_stock_id=filtered.id,
    stock_id=stock.id,
    total_score=85.5,
    final_grade=AnalysisGrade.BUY,
    is_selected=True
)
analysis.save(session)

# 4. 매매 실행
trade = Trade(
    stock_id=stock.id,
    trade_type=TradeType.BUY,
    order_quantity=100,
    executed_price=74900,
    order_status=OrderStatus.FILLED
)
trade.save(session)

# 5. 포트폴리오 업데이트
portfolio = Portfolio(
    stock_id=stock.id,
    quantity=100,
    avg_price=74900,
    total_cost=7490000
)
portfolio.update_current_values(75000)
portfolio.save(session)
```

## 📊 데이터 검증

### 자동 검증 기능
- **종목코드**: 6자리 숫자 형식 검증
- **가격 데이터**: 양수 값 검증
- **분석 점수**: 0-100 범위 검증
- **수량 데이터**: 음수 방지
- **관계 무결성**: 외래키 제약조건

### 비즈니스 룰 검증
- **포트폴리오**: 수량 음수 불가
- **거래**: 체결수량 ≤ 주문수량
- **계좌**: 잔고 음수 불가
- **세션**: 수익거래 ≤ 총거래

## 🔧 유틸리티 메서드

### Stock 모델
```python
Stock.get_by_symbol(session, '005930')      # 종목코드로 조회
Stock.get_active_stocks(session, Market.KOSPI)  # 활성 종목 조회
stock.get_latest_price(session)             # 최신 가격 조회
```

### Portfolio 모델
```python
portfolio.add_position(100, 75000)          # 포지션 추가
portfolio.reduce_position(50, 77000)        # 포지션 감소
portfolio.update_current_values(76000)      # 평가 정보 업데이트
```

### Trade 모델
```python
trade.get_total_amount()                     # 거래금액 (수수료 포함)
trade.is_completed()                         # 체결 완료 여부
Trade.get_recent_trades(session, days=30)   # 최근 거래 조회
```

## 📁 파일 구조

```
database/
├── models.py           # 메인 모델 정의
├── test_models.py      # 모델 테스트 스크립트
├── example_usage.py    # 실제 사용법 시연
├── MODEL_USAGE.md      # 상세 사용법 가이드
└── README.md           # 이 파일
```

## ✅ 테스트

### 기본 테스트 실행
```bash
python database/test_models.py
```

### 워크플로우 시뮬레이션
```bash
python database/example_usage.py
```

## 🔒 보안 및 성능

### 보안 기능
- SQL 인젝션 방지 (SQLAlchemy ORM)
- 데이터 타입 검증
- 외래키 제약조건
- 트랜잭션 롤백 지원

### 성능 최적화
- 필수 컬럼 인덱싱
- N+1 쿼리 방지 (joinedload)
- 배치 작업 지원
- 연결 풀링

## 🚀 Production 배포

### PostgreSQL 설정
```python
# config.py
DATABASE_URL = "postgresql://user:password@localhost:5432/trading_system"

# 엔진 생성
engine = create_database_engine(DATABASE_URL)
create_all_tables(engine)
```

### 초기 데이터 설정
```python
from database.models import insert_initial_data

session = SessionFactory()
insert_initial_data(session)
session.close()
```

## 📝 추가 정보

- **문서**: `MODEL_USAGE.md` 참조
- **예시**: `example_usage.py` 참조  
- **테스트**: `test_models.py` 참조

이 모델 시스템은 실제 운영 환경에서 바로 사용할 수 있도록 설계되었으며, 한국 주식시장의 특성을 완벽하게 반영합니다.