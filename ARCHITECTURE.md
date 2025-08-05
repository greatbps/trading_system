# 🏗️ AI Trading System Architecture

## 🎯 시스템 개요
실시간 주식 자동매매 시스템 - KIS API 기반 2단계 필터링 및 정밀 매매

## 📋 핵심 컴포넌트

### 1. 데이터 계층 (Data Layer)
```
database/
├── models.py          # SQLAlchemy 모델 정의
├── db_operations.py   # CRUD 연산
└── migrations/        # DB 스키마 변경
```

**주요 테이블:**
- `stocks` - 종목 기본정보
- `filtered_stocks` - 1차 필터링 결과  
- `analysis_results` - 2차 분석 결과
- `trades` - 매매 내역
- `portfolio` - 포트폴리오 현황
- `account_info` - 계좌 정보

### 2. 데이터 수집 계층 (Data Collection Layer)
```
data_collectors/
├── kis_collector.py      # KIS API 통합 (HTS 조건검색 + 시세)
├── news_collector.py     # 뉴스 수집
└── base_collector.py     # 수집기 베이스 클래스
```

### 3. 분석 엔진 계층 (Analysis Engine Layer)
```
analyzers/
├── analysis_engine.py      # 2차 필터링 메인 엔진
├── technical_analyzer.py   # 기술적 분석 (차트, 지표)
├── sentiment_analyzer.py   # 뉴스 감성 분석
└── supply_demand_analyzer.py # 수급 분석
```

### 4. 전략 계층 (Strategy Layer)
```
strategies/
├── base_strategy.py        # 전략 베이스 클래스
├── momentum_strategy.py    # 모멘텀 전략
└── supertrend_ema_rsi_strategy.py # 복합 기술적 전략
```

### 5. 거래 실행 계층 (Trading Execution Layer)
```
trading/
├── executor.py           # 매매 실행기
├── risk_manager.py       # 리스크 관리
└── position_manager.py   # 포지션 관리
```

### 6. 핵심 비즈니스 로직 계층 (Core Business Layer)
```
core/
├── trading_system.py     # 메인 시스템 오케스트레이터
├── scheduler.py          # 시간대별 스케줄러
└── workflow_manager.py   # 워크플로우 관리
```

### 7. 알림 계층 (Notification Layer)
```
notifications/
├── telegram_bot.py       # 텔레그램 알림
├── email_notifier.py     # 이메일 알림
└── notification_manager.py # 알림 통합 관리
```

## 🔄 시스템 워크플로우

### 장전 준비 (Pre-Market)
1. **KIS HTS 조건검색 결과 수신** → `filtered_stocks` 테이블 저장
2. **1차 필터링된 종목 리스트 생성**
3. **2차 분석 준비**: 뉴스, 차트, 수급 데이터 수집

### 장중 실시간 모니터링 (Market Hours)
1. **2차 분석 실행**: 점수화 및 최종 후보군 선정
2. **3분봉 실시간 모니터링**: 매수 조건 감시
3. **매매 신호 발생시**: 정밀 매수 실행
4. **포지션 관리**: 손절/익절 모니터링

### 장후 정리 (Post-Market)
1. **일일 성과 분석**
2. **리포트 생성 및 알림**
3. **다음 거래일 준비**

## 🗄️ 데이터베이스 스키마 설계

### 테이블 관계도
```
stocks (종목기본정보)
  ↓ 1:N
filtered_stocks (1차필터링결과)
  ↓ 1:1  
analysis_results (2차분석결과)
  ↓ 1:N
trades (매매내역)
  ↓ N:1
portfolio (포트폴리오)
```

### 주요 비즈니스 규칙
1. **1차 필터링**: HTS 조건검색 결과를 매일 업데이트
2. **2차 분석**: 점수 임계값 이상만 거래 대상
3. **리스크 관리**: 포지션 사이징, 손절/익절 자동화
4. **실시간 알림**: 모든 중요 이벤트 텔레그램 전송

## 🔧 기술 스택

### Backend
- **Python 3.9+**: 메인 언어
- **PostgreSQL**: 메인 데이터베이스
- **SQLAlchemy**: ORM
- **Asyncio**: 비동기 처리

### External APIs
- **KIS API**: 주식 데이터 및 매매
- **Naver News API**: 뉴스 수집
- **Telegram Bot API**: 알림

### Libraries
- **pandas/numpy**: 데이터 분석
- **TA-Lib**: 기술적 분석
- **requests/aiohttp**: HTTP 통신
- **schedule**: 작업 스케줄링

## 📋 개발 우선순위

### Phase 1: 핵심 인프라 (이번 단계)
1. ✅ 데이터베이스 모델 설계
2. 🔄 PostgreSQL 마이그레이션
3. 🔄 KIS API 수집기 완성
4. 🔄 기본 분석 엔진 구현

### Phase 2: 비즈니스 로직
1. 매매 전략 구현
2. 리스크 관리 시스템
3. 실시간 모니터링

### Phase 3: 고도화
1. 백테스팅 시스템
2. 성능 최적화
3. UI 대시보드

## 🤖 에이전트 협업 계획

### 역할 분담
- **Claude (Manager)**: 아키텍처 설계, 코드 리뷰, 품질 관리
- **Sub-Agent**: 개별 모듈 구현, 테스트 코드 작성

### 작업 흐름
1. 상세 요구사항 작성 → Sub-Agent에게 전달
2. 구현 결과 검토 → 피드백 및 수정 지시
3. 품질 검증 → 최종 승인 및 통합