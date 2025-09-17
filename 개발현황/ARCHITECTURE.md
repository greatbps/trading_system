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
===============================================
08.23 Complete File Architecture
 🤖 AI Trading System v4.0 - Complete File Architecture
  ================================================================================

  📁 D:/trading_system/
  │
  ├── 🚀 MAIN ENTRY POINTS
  │   ├── main.py                         # 메인 애플리케이션 진입점
  │   ├── config.py                       # 시스템 전체 설정
  │   ├── run_system.py                   # 시스템 실행 스크립트
  │   └── auto_trading_daemon.py          # 데몬 모드 실행
  │
  ├── 📁 core/                           # 🏗️ CORE SYSTEM LAYER
  │   ├── trading_system.py              # 🤖 메인 시스템 컨트롤러
  │   │   └── 시스템 초기화, 컴포넌트 관리, 메뉴 시스템
  │   │
  │   ├── db_auto_trading_handler.py     # 🎯 DB 통합 자동매매 핸들러
  │   │   └── 영구 저장, 복원, 실시간 모니터링
  │   │
  │   ├── auto_mode_controller.py        # 🎛️ NEW: 자동 모드 제어기
  │   │   └── 시장 일정 기반 자동 활성화/비활성화
  │   │
  │   ├── menu_handlers.py               # 📋 사용자 인터페이스 핸들러
  │   │   └── 대화형 메뉴, 명령 처리
  │   │
  │   ├── analysis_handlers.py           # 📊 분석 작업 핸들러
  │   │   └── 종합 분석, 전략별 분석
  │   │
  │   ├── auto_trading_handler.py        # 💼 기존 자동매매 핸들러
  │   │   └── 레거시 매매 시스템 (fallback)
  │   │
  │   └── scheduler.py                   # ⏰ 스케줄링 시스템
  │       └── 정기 작업, 시간 기반 실행
  │
  ├── 📁 utils/                          # 🛠️ UTILITY LAYER
  │   ├── market_schedule_manager.py     # 📅 NEW: 시장 일정 관리자
  │   │   └── KIS API 연동, 휴장일/장시간 추적
  │   │
  │   ├── logger.py                      # 📝 로깅 시스템
  │   ├── stock_search.py                # 🔍 종목 검색 엔진
  │   ├── pattern_detector.py            # 📈 패턴 감지기
  │   ├── safe_console.py                # 💬 안전한 콘솔 출력
  │   ├── data_utils.py                  # 📊 데이터 유틸리티
  │   ├── performance_optimizer.py       # ⚡ 성능 최적화
  │   ├── system_monitor.py              # 📡 시스템 모니터링
  │   ├── http_client.py                 # 🌐 HTTP 클라이언트
  │   ├── error_handler.py               # ⚠️ 에러 처리
  │   └── encoding_fix.py                # 🔧 인코딩 수정
  │
  ├── 📁 trading/                        # 💰 TRADING EXECUTION LAYER
  │   ├── db_auto_trader.py              # 🤖 DB 통합 자동매매 시스템
  │   │   └── 실시간 모니터링, DB 연동, 신호 생성
  │   │
  │   ├── executor.py                    # ⚡ 매매 실행 엔진
  │   │   └── 주문 실행, 포지션 관리
  │   │
  │   ├── auto_trader.py                 # 🎯 기존 자동매매 시스템
  │   │   └── 레거시 매매 로직 (메모리 기반)
  │   │
  │   ├── position_manager.py            # 📊 포지션 관리자
  │   │   └── 포지션 추적, 리스크 계산
  │   │
  │   ├── risk_manager.py                # 🛡️ 리스크 관리자
  │   │   └── 손절매, 익절매, 포지션 사이징
  │   │
  │   └── smart_rebalancer.py            # ⚖️ 스마트 리밸런싱
  │       └── 포트폴리오 최적화
  │
  ├── 📁 data_collectors/                # 📊 DATA COLLECTION LAYER
  │   ├── kis_collector.py               # 🔌 KIS API 데이터 수집기
  │   │   └── 실시간 시세, 뉴스, 재무 데이터
  │   │
  │   ├── chart_data_collector.py        # 📈 차트 데이터 수집기
  │   │   └── 분봉/일봉 데이터, 기술적 지표
  │   │
  │   ├── news_collector.py              # 📰 뉴스 수집기
  │   │   └── 뉴스 수집, 필터링, 감성 분석
  │   │
  │   ├── kis_database_integration.py    # 🗄️ KIS-DB 통합
  │   │   └── API 데이터의 DB 저장
  │   │
  │   ├── base_collector.py              # 🏗️ 수집기 베이스 클래스
  │   ├── kis_models.py                  # 📋 KIS 데이터 모델
  │   ├── exceptions.py                  # ⚠️ 예외 정의
  │   └── kis_example_usage.py           # 📖 사용 예제
  │
  ├── 📁 analyzers/                      # 🧠 ANALYSIS ENGINE LAYER
  │   ├── analysis_engine.py             # 🎯 종합 분석 엔진
  │   │   └── 기술적, 기본적, 뉴스, 패턴 통합 분석
  │   │
  │   ├── ai_controller.py               # 🤖 AI 시스템 컨트롤러
  │   │   └── AI 모델 관리, 예측 조율
  │   │
  │   ├── technical_analyzer.py          # 📊 기술적 분석기
  │   │   └── 가격, 거래량, 추세 분석
  │   │
  │   ├── fundamental_analyzer.py        # 📈 기본적 분석기
  │   │   └── 재무제표, 밸류에이션 분석
  │   │
  │   ├── sentiment_analyzer.py          # 💭 감성 분석기
  │   │   └── 뉴스, 소셜미디어 감성 분석
  │   │
  │   ├── market_regime_detector.py      # 🌊 시장 체제 감지기
  │   │   └── 강세/약세/횡보 구분
  │   │
  │   ├── ai_predictor.py                # 🔮 AI 예측 시스템
  │   │   └── 머신러닝 기반 가격 예측
  │   │
  │   ├── chart_pattern_analyzer.py      # 📉 차트 패턴 분석기
  │   │   └── 캔들패턴, 차트패턴 인식
  │   │
  │   ├── supply_demand_analyzer.py      # ⚖️ 수급 분석기
  │   │   └── 기관, 외국인 매매 분석
  │   │
  │   ├── volume_analyzer.py             # 📊 거래량 분석기
  │   │   └── 거래량 패턴, 이상징후 탐지
  │   │
  │   ├── multi_strategy_analyzer.py     # 🎯 다중 전략 분석기
  │   ├── strategy_optimizer.py          # ⚡ 전략 최적화기
  │   ├── ai_risk_manager.py             # 🛡️ AI 리스크 관리
  │   ├── technical_indicators.py        # 📊 기술적 지표 계산
  │   ├── gemini_analyzer.py             # 🤖 Gemini AI 분석
  │   ├── gpt_analyzer.py                # 🤖 GPT 분석
  │   ├── multi_llm_analyzer.py          # 🤖 다중 LLM 분석
  │   └── advanced_ai_features.py        # 🚀 고급 AI 기능
  │
  ├── 📁 strategies/                     # 📊 TRADING STRATEGY LAYER
  │   ├── strategy_manager.py            # 🎯 전략 관리자
  │   │   └── 전략 선택, 가중치, 통합 실행
  │   │
  │   ├── momentum_strategy.py           # 📈 모멘텀 전략
  │   │   └── 추세 추종, 모멘텀 신호
  │   │
  │   ├── breakout_strategy.py           # 🚀 돌파 전략
  │   │   └── 저항/지지선 돌파 탐지
  │   │
  │   ├── eod_strategy.py                # 🌅 장마감 전략
  │   │   └── 장마감 전 패턴 활용
  │   │
  │   ├── scalping_3m_strategy.py        # ⚡ 3분봉 스캘핑
  │   │   └── 단기 매매, 고빈도 거래
  │   │
  │   ├── supertrend_ema_rsi_strategy.py # 📊 SuperTrend+EMA+RSI
  │   │   └── 다중 지표 조합 전략
  │   │
  │   ├── vwap_strategy.py               # 📊 VWAP 전략
  │   │   └── 거래량 가중 평균가 활용
  │   │
  │   ├── rsi_strategy.py                # 📉 RSI 전략
  │   │   └── 과매수/과매도 역추세
  │   │
  │   ├── ai_momentum_strategy.py        # 🤖 AI 모멘텀 전략
  │   │   └── AI 예측 + 모멘텀 조합
  │   │
  │   ├── enhanced_multi_timeframe_strategy.py # ⏰ 다중 시간대 전략
  │   ├── adaptive_position_sizing.py    # 📊 적응형 포지션 사이징
  │   ├── multi_timeframe_analyzer.py    # 📊 다중 시간대 분석
  │   └── base_strategy.py               # 🏗️ 전략 베이스 클래스
  │
  ├── 📁 database/                       # 🗄️ DATABASE LAYER
  │   ├── models.py                      # 📋 데이터베이스 모델
  │   │   └── MonitoringStock, Stock, TradingRecord 등
  │   │
  │   ├── database_manager.py            # 🔧 데이터베이스 관리자
  │   │   └── 연결 관리, 세션 풀링
  │   │
  │   ├── db_operations.py               # 🛠️ DB 작업 유틸리티
  │   │   └── CRUD 작업, 쿼리 헬퍼
  │   │
  │   ├── init_db.py                     # 🏗️ 데이터베이스 초기화
  │   ├── reset_db.py                    # 🔄 데이터베이스 리셋
  │   ├── create_news_tables.py          # 📰 뉴스 테이블 생성
  │   ├── fix_active_stocks.py           # 🔧 활성 종목 수정
  │   ├── monitoring_models.py           # 📊 모니터링 모델
  │   └── example_usage.py               # 📖 사용 예제
  │
  ├── 📁 ai/                            # 🤖 AI/ML LAYER
  │   ├── ensemble_predictor.py          # 🎯 앙상블 예측기
  │   │   └── 다중 모델 조합 예측
  │   │
  │   ├── lstm_predictor.py              # 🧠 LSTM 예측기
  │   │   └── 시계열 딥러닝 예측
  │   │
  │   ├── gru_predictor.py               # 🧠 GRU 예측기
  │   │   └── 경량 순환 신경망 예측
  │   │
  │   ├── transformer_predictor.py       # 🤖 Transformer 예측기
  │   │   └── 어텐션 메커니즘 기반 예측
  │   │
  │   └── online_learning_system.py      # 📚 온라인 학습 시스템
  │       └── 실시간 모델 업데이트
  │
  ├── 📁 notifications/                 # 📢 NOTIFICATION LAYER
  │   ├── notification_manager.py        # 📨 알림 관리자
  │   │   └── 다중 채널 알림 통합 관리
  │   │
  │   ├── telegram_notifier.py           # 📱 텔레그램 알리미
  │   │   └── 텔레그램 봇 연동
  │   │
  │   └── trading_signal_notifier.py     # 📊 매매 신호 알리미
  │       └── 매매 신호 실시간 알림
  │
  ├── 📁 monitoring/                     # 📡 MONITORING LAYER
  │   ├── db_monitoring_scheduler.py     # 🕐 DB 모니터링 스케줄러
  │   │   └── 감시 제거 시스템, 정기 점검
  │   │
  │   ├── monitoring_scheduler.py        # ⏰ 모니터링 스케줄러
  │   │   └── 실시간 모니터링 작업 관리
  │   │
  │   ├── performance_monitor.py         # 📊 성능 모니터
  │   │   └── 시스템 성능 추적
  │   │
  │   └── performance_dashboard.py       # 📈 성능 대시보드
  │       └── 실시간 성능 시각화
  │
  ├── 📁 backtesting/                    # 🔬 BACKTESTING LAYER
  │   ├── backtesting_engine.py          # 🧪 백테스팅 엔진
  │   │   └── 과거 데이터 기반 전략 검증
  │   │
  │   ├── strategy_validator.py          # ✅ 전략 검증기
  │   │   └── 전략 유효성 검사
  │   │
  │   ├── historical_analyzer.py         # 📜 과거 데이터 분석기
  │   │   └── 과거 패턴, 성과 분석
  │   │
  │   ├── performance_visualizer.py      # 📊 성과 시각화
  │   │   └── 백테스팅 결과 그래프
  │   │
  │   ├── signal_based_backtester.py     # 📡 신호 기반 백테스터
  │   └── strategy_optimizer.py          # ⚡ 전략 최적화기
  │
  ├── 📁 async_processing/               # ⚡ ASYNC PROCESSING LAYER
  │   ├── async_engine.py                # 🚀 비동기 엔진
  │   │   └── 비동기 작업 관리
  │   │
  │   ├── task_scheduler.py              # 📋 태스크 스케줄러
  │   │   └── 비동기 태스크 스케줄링
  │   │
  │   └── async_utils.py                 # 🛠️ 비동기 유틸리티
  │       └── 비동기 헬퍼 함수
  │
  ├── 📁 error_handling/                 # ⚠️ ERROR HANDLING LAYER
  │   └── error_recovery_system.py       # 🔧 에러 복구 시스템
  │       └── 자동 에러 복구, 재시도 로직
  │
  ├── 📁 optimization/                   # ⚡ OPTIMIZATION LAYER
  │   └── system_optimizer.py            # 🚀 시스템 최적화
  │       └── 성능 튜닝, 메모리 최적화
  │
  ├── 📁 config/                         # ⚙️ CONFIGURATION LAYER
  │   └── enhanced_trading_config.py     # 🎯 NEW: 고급 매매 설정
  │       └── 모드별 설정, 리스크 관리, 진입/청산 조건
  │
  ├── 📁 scripts/                        # 📜 UTILITY SCRIPTS
  │   ├── init_database.py               # 🏗️ 데이터베이스 초기 설정
  │   └── update_monitoring_stock_names.py # 🔄 종목명 업데이트
  │
  ├── 📁 tests/                          # 🧪 TESTING LAYER
  │   └── __init__.py                    # 테스트 패키지
  │
  └── 🔧 TEST & UTILITY SCRIPTS
      ├── test_*.py                      # 각종 테스트 스크립트
      ├── check_*.py                     # 상태 확인 스크립트
      ├── simple_*.py                    # 간단한 분석 스크립트
      └── temp_*.py                      # 임시 테스트 스크립트

  ================================================================================
  🎯 KEY ARCHITECTURAL PATTERNS
  ================================================================================

  🏗️ LAYERED ARCHITECTURE
     ├── Presentation Layer (core/menu_handlers.py)
     ├── Business Logic Layer (core/trading_system.py)
     ├── Service Layer (analyzers/, strategies/)
     ├── Data Access Layer (database/, data_collectors/)
     └── Infrastructure Layer (utils/, notifications/)

  🔄 EVENT-DRIVEN ARCHITECTURE
     ├── Market Events → AutoModeController
     ├── Trading Signals → TradingExecutor
     ├── System Events → NotificationManager
     └── Error Events → ErrorRecoverySystem

  🎛️ PLUGIN ARCHITECTURE
     ├── Strategy Plugins (strategies/)
     ├── Analyzer Plugins (analyzers/)
     ├── Collector Plugins (data_collectors/)
     └── AI Model Plugins (ai/)

  📊 DATA FLOW PIPELINE
     Market Data → Collectors → Analyzers → Strategies → Executor → Database

  🤖 AI/ML INTEGRATION
     ├── Multi-Model Ensemble
     ├── Online Learning
     ├── Real-time Prediction
     └── Performance Feedback Loop

  🛡️ FAULT TOLERANCE
     ├── Circuit Breakers
     ├── Retry Mechanisms
     ├── Graceful Degradation
     └── Automatic Recovery
=============================================
✅ 현재 구조 보완 포인트

중복/레거시 관리

core/auto_trading_handler.py vs trading/db_auto_trader.py vs trading/auto_trader.py → 기능이 중첩되는 부분을 리팩토링해서 단일 표준 실행 엔진으로 합치는 게 좋습니다. 레거시는 별도 legacy/ 폴더로 격리 추천.

Config 관리 체계

현재 config.py와 config/enhanced_trading_config.py가 혼재 → 환경별 설정 분리(dev/prod/backtest) + YAML/JSON 로드 지원 추가 필요.

에러 처리 일관성

utils/error_handler.py와 error_handling/error_recovery_system.py → 역할이 나뉘어 있으니, 에러 로깅/처리/복구를 단일 에러 관리 모듈로 통합하는 게 유지보수에 좋습니다.

AI 모델 관리

analyzers/ai_controller.py, ai/ensemble_predictor.py 등이 분산 → Model Registry를 두고 모델 버전/성능/로드 관리 체계화 필요 (MLflow, custom registry).

🚀 고도화를 위한 개선 포인트

Core/Service 분리 강화

core/trading_system.py가 현재 초기화 + 메뉴 + 컨트롤러까지 담당 → 서비스 레이어(service/)를 두고 orchestration을 위임하면 확장성 ↑.

이벤트 버스(Event Bus) 도입

현재 event-driven 구조를 문서상 정의했는데, 구현이 분산됨.
→ 중앙 이벤트 버스(예: event_bus.py)를 두고 signals, orders, errors를 pub/sub 방식으로 연결하면 비동기 확장성 확보.

실시간 모니터링 고도화

monitoring/performance_dashboard.py는 시각화 위주 →
운영 단계에서는 Prometheus + Grafana 같은 외부 모니터링 연동 고려 추천.
(슬리피지, fill ratio, latency, win rate 등 KPI를 PromQL로 바로 조회 가능)

백테스트/실거래 통합

backtesting/ 모듈과 trading/ 모듈이 분리 →
인터페이스를 통일(IExecutor, IDataFeed)하면 전략 코드가 변경 없이 백테스트/실거래 모두 실행 가능.

리스크 관리 고도화

현재는 trading/risk_manager.py + analyzers/ai_risk_manager.py →
체계적으로 합쳐서 3단계 리스크 게이트 구축 추천:

사전 리스크 필터(시장 상태/체결강도)

주문 단위 리스크(사이징, 슬리피지 캡)

포트폴리오 단위 리스크(익스포저, 섹터 편중)

멀티프로세스/분산 처리

async_processing/은 비동기 중심 →
전략/수집/실행을 프로세스 단위로 나누고 메시지 큐(Redis, NATS) 연결 고려 시 확장성 극대화.

테스트 체계 고도화

tests/가 빈약 → 최소한

단위 테스트(pytest)

시뮬레이션 리플레이 테스트

전략 성능 회귀 테스트
구축 필요.

🎯 정리

단기 개선: 레거시 통합, config 체계화, 에러 처리 통합

중기 개선: 이벤트 버스 도입, 백테스트/실거래 인터페이스 통일, 리스크 관리 고도화

장기 개선: 모니터링 외부화(Prometheus), 분산 처리(MQ), Model Registry 도입