# 프로젝트 파일 구조 분석 - 사용하지 않는 파일 목록

분석 일시: 2025-10-08
분석 방법: main.py -> core/trading_system.py -> 전체 import chain 추적

---

## 📋 요약

### 전체 통계
- 루트 레벨 Python 파일: 98개
- 루트 레벨 디렉토리: 45개
- 분석 대상: 전체 프로젝트 구조

### 핵심 진입점
1. **main.py** - 메인 진입점
2. **background_monitoring_service.py** - 백그라운드 서비스
3. **config.py** - 설정 파일

---

## ✅ 반드시 유지해야 하는 파일들 (KEEP)

### 1. 핵심 시스템 파일
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/main.py | **KEEP** | 프로그램 메인 진입점 |
| /home/greatbps/projects/trading_system/config.py | **KEEP** | 시스템 설정 파일 |
| /home/greatbps/projects/trading_system/background_monitoring_service.py | **KEEP** | 백그라운드 모니터링 서비스 (main.py에서 직접 import) |
| /home/greatbps/projects/trading_system/time_based_strategy_mapper.py | **KEEP** | 시간대별 전략 매핑 (main.py에서 직접 import) |

### 2. Core 모듈 (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/core/trading_system.py | **KEEP** | 메인 트레이딩 시스템 클래스 |
| /home/greatbps/projects/trading_system/core/menu_handlers.py | **KEEP** | 메뉴 핸들러 (trading_system에서 사용) |
| /home/greatbps/projects/trading_system/core/analysis_handlers.py | **KEEP** | 분석 핸들러 (trading_system에서 사용) |
| /home/greatbps/projects/trading_system/core/auto_trading_handler.py | **KEEP** | 자동매매 핸들러 |
| /home/greatbps/projects/trading_system/core/db_auto_trading_handler.py | **KEEP** | DB 기반 자동매매 핸들러 |
| /home/greatbps/projects/trading_system/core/scheduler.py | **KEEP** | 스케줄러 |
| /home/greatbps/projects/trading_system/core/portfolio_manager.py | **KEEP** | 포트폴리오 관리 |
| /home/greatbps/projects/trading_system/core/stop_loss_manager.py | **KEEP** | 손절 관리 |
| /home/greatbps/projects/trading_system/core/trading_flow_manager.py | **KEEP** | 트레이딩 플로우 관리 |
| /home/greatbps/projects/trading_system/core/dynamic_settings_manager.py | **KEEP** | 동적 설정 관리 (trading_system에서 import) |
| /home/greatbps/projects/trading_system/core/auto_trading_orchestrator.py | **KEEP** | 자동매매 오케스트레이터 |
| /home/greatbps/projects/trading_system/core/auto_stop_loss_system.py | **KEEP** | 자동 손절 시스템 |
| /home/greatbps/projects/trading_system/core/auto_balance_monitor.py | **KEEP** | 자동 잔고 모니터 |
| /home/greatbps/projects/trading_system/core/auto_mode_controller.py | **KEEP** | 자동 모드 컨트롤러 |

### 3. Data Collectors (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/data_collectors/kis_collector.py | **KEEP** | KIS API 데이터 수집 (핵심) |
| /home/greatbps/projects/trading_system/data_collectors/news_collector.py | **KEEP** | 뉴스 데이터 수집 (analysis_engine에서 사용) |
| /home/greatbps/projects/trading_system/data_collectors/chart_data_collector.py | **KEEP** | 차트 데이터 수집 |
| /home/greatbps/projects/trading_system/data_collectors/kis_models.py | **KEEP** | KIS 데이터 모델 |
| /home/greatbps/projects/trading_system/data_collectors/base_collector.py | **KEEP** | 베이스 수집기 클래스 |
| /home/greatbps/projects/trading_system/data_collectors/exceptions.py | **KEEP** | 예외 정의 |
| /home/greatbps/projects/trading_system/data_collectors/bulk_realtime_collector.py | **KEEP** | 대량 실시간 데이터 수집 |
| /home/greatbps/projects/trading_system/data_collectors/kis_database_integration.py | **KEEP** | KIS DB 통합 |
| /home/greatbps/projects/trading_system/data_collectors/memory_optimized_storage.py | **KEEP** | 메모리 최적화 저장소 |
| /home/greatbps/projects/trading_system/data_collectors/news_search_wrapper.py | **KEEP** | 뉴스 검색 래퍼 |

### 4. Analyzers (핵심 분석기들)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/analyzers/analysis_engine.py | **KEEP** | 종합 분석 엔진 (핵심) |
| /home/greatbps/projects/trading_system/analyzers/ai_predictor.py | **KEEP** | AI 예측기 (실제 사용) |
| /home/greatbps/projects/trading_system/analyzers/ai_risk_manager.py | **KEEP** | AI 리스크 관리 |
| /home/greatbps/projects/trading_system/analyzers/market_regime_detector.py | **KEEP** | 시장 체제 감지 |
| /home/greatbps/projects/trading_system/analyzers/strategy_optimizer.py | **KEEP** | 전략 최적화 |
| /home/greatbps/projects/trading_system/analyzers/institutional_flow_analyzer.py | **KEEP** | 기관 수급 분석 |
| /home/greatbps/projects/trading_system/analyzers/sentiment_analyzer.py | **KEEP** | 감성 분석 |
| /home/greatbps/projects/trading_system/analyzers/theme_sector_analyzer.py | **KEEP** | 테마/섹터 분석 |
| /home/greatbps/projects/trading_system/analyzers/technical_analyzer.py | **KEEP** | 기술적 분석 |
| /home/greatbps/projects/trading_system/analyzers/fundamental_analyzer.py | **KEEP** | 펀더멘털 분석 |
| /home/greatbps/projects/trading_system/analyzers/technical_indicators.py | **KEEP** | 기술적 지표 |
| /home/greatbps/projects/trading_system/analyzers/technical_indicators_enhanced.py | **KEEP** | 향상된 기술적 지표 |
| /home/greatbps/projects/trading_system/analyzers/chart_pattern_analyzer.py | **KEEP** | 차트 패턴 분석 |
| /home/greatbps/projects/trading_system/analyzers/volume_analyzer.py | **KEEP** | 거래량 분석 |
| /home/greatbps/projects/trading_system/analyzers/supply_demand_analyzer.py | **KEEP** | 수급 분석 |
| /home/greatbps/projects/trading_system/analyzers/trading_signals.py | **KEEP** | 트레이딩 시그널 |
| /home/greatbps/projects/trading_system/analyzers/enhanced_consensus_engine.py | **KEEP** | 향상된 합의 엔진 (실제 사용) |
| /home/greatbps/projects/trading_system/analyzers/consensus_engine.py | **KEEP** | 기본 합의 엔진 (enhanced_consensus_engine의 부모 클래스) |
| /home/greatbps/projects/trading_system/analyzers/market_condition_analyzer.py | **KEEP** | 시장 상황 분석 |
| /home/greatbps/projects/trading_system/analyzers/performance_tracker.py | **KEEP** | 성능 추적기 |
| /home/greatbps/projects/trading_system/analyzers/weight_adjuster.py | **KEEP** | 가중치 조정기 |
| /home/greatbps/projects/trading_system/analyzers/ai_controller.py | **KEEP** | AI 컨트롤러 |
| /home/greatbps/projects/trading_system/analyzers/advanced_ai_features.py | **KEEP** | 고급 AI 기능 |
| /home/greatbps/projects/trading_system/analyzers/mtf_analyzer.py | **KEEP** | 다중 시간프레임 분석 |
| /home/greatbps/projects/trading_system/analyzers/multi_strategy_analyzer.py | **KEEP** | 다중 전략 분석 |
| /home/greatbps/projects/trading_system/analyzers/performance_optimizer.py | **KEEP** | 성능 최적화 |
| /home/greatbps/projects/trading_system/analyzers/market_regime_analyzer.py | **KEEP** | 시장 체제 분석 (market_regime_detector와 다름) |

### 5. Strategies (전략들)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/strategies/ai_strategy_selector.py | **KEEP** | AI 전략 선택기 |
| /home/greatbps/projects/trading_system/strategies/momentum_strategy.py | **KEEP** | 모멘텀 전략 (핵심) |
| /home/greatbps/projects/trading_system/strategies/smart_money_strategy.py | **KEEP** | 스마트머니 전략 |
| /home/greatbps/projects/trading_system/strategies/breakout_strategy.py | **KEEP** | 돌파 전략 |
| /home/greatbps/projects/trading_system/strategies/eod_strategy.py | **KEEP** | EOD 전략 |
| /home/greatbps/projects/trading_system/strategies/rsi_strategy.py | **KEEP** | RSI 전략 |
| /home/greatbps/projects/trading_system/strategies/vwap_strategy.py | **KEEP** | VWAP 전략 |
| /home/greatbps/projects/trading_system/strategies/scalping_3m_strategy.py | **KEEP** | 3분봉 스캘핑 전략 |
| /home/greatbps/projects/trading_system/strategies/supertrend_ema_rsi_strategy.py | **KEEP** | 슈퍼트렌드 EMA RSI 전략 |
| /home/greatbps/projects/trading_system/strategies/squeeze_momentum_pro_strategy.py | **KEEP** | 스퀴즈 모멘텀 프로 전략 |
| /home/greatbps/projects/trading_system/strategies/base_strategy.py | **KEEP** | 베이스 전략 클래스 |
| /home/greatbps/projects/trading_system/strategies/strategy_manager.py | **KEEP** | 전략 관리자 |
| /home/greatbps/projects/trading_system/strategies/strategy_definitions.py | **KEEP** | 전략 정의 |
| /home/greatbps/projects/trading_system/strategies/ai_momentum_strategy.py | **KEEP** | AI 모멘텀 전략 |
| /home/greatbps/projects/trading_system/strategies/enhanced_multi_timeframe_strategy.py | **KEEP** | 향상된 다중 시간프레임 전략 |
| /home/greatbps/projects/trading_system/strategies/multi_timeframe_analyzer.py | **KEEP** | 다중 시간프레임 분석기 |
| /home/greatbps/projects/trading_system/strategies/adaptive_position_sizing.py | **KEEP** | 적응형 포지션 사이징 |
| /home/greatbps/projects/trading_system/strategies/advanced_exit_strategy.py | **KEEP** | 고급 청산 전략 |
| /home/greatbps/projects/trading_system/strategies/exit_signal_executor.py | **KEEP** | 청산 시그널 실행기 |
| /home/greatbps/projects/trading_system/strategies/portfolio_cleanup_strategy.py | **KEEP** | 포트폴리오 정리 전략 |

### 6. Trading 모듈 (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/trading/executor.py | **KEEP** | 거래 실행기 (핵심) |
| /home/greatbps/projects/trading_system/trading/db_auto_trader.py | **KEEP** | DB 기반 자동 트레이더 |
| /home/greatbps/projects/trading_system/trading/trade_history_manager.py | **KEEP** | 거래 이력 관리 |
| /home/greatbps/projects/trading_system/trading/auto_trader.py | **KEEP** | 자동 트레이더 |
| /home/greatbps/projects/trading_system/trading/position_manager.py | **KEEP** | 포지션 관리 |
| /home/greatbps/projects/trading_system/trading/profit_calculator.py | **KEEP** | 수익 계산기 |
| /home/greatbps/projects/trading_system/trading/risk_manager.py | **KEEP** | 리스크 관리 |
| /home/greatbps/projects/trading_system/trading/smart_rebalancer.py | **KEEP** | 스마트 리밸런싱 |

### 7. Database 모듈 (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/database/models.py | **KEEP** | 데이터베이스 모델 (핵심) |
| /home/greatbps/projects/trading_system/database/database_manager.py | **KEEP** | DB 관리자 |
| /home/greatbps/projects/trading_system/database/db_operations.py | **KEEP** | DB 연산 |
| /home/greatbps/projects/trading_system/database/monitoring_models.py | **KEEP** | 모니터링 모델 |
| /home/greatbps/projects/trading_system/database/trade_history_models.py | **KEEP** | 거래 이력 모델 |
| /home/greatbps/projects/trading_system/database/init_db.py | **KEEP** | DB 초기화 스크립트 |
| /home/greatbps/projects/trading_system/database/create_news_tables.py | **KEEP** | 뉴스 테이블 생성 |

### 8. Notifications (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/notifications/telegram_notifier.py | **KEEP** | 텔레그램 알림 (핵심) |
| /home/greatbps/projects/trading_system/notifications/notification_manager.py | **KEEP** | 알림 관리자 |
| /home/greatbps/projects/trading_system/notifications/trading_signal_notifier.py | **KEEP** | 트레이딩 시그널 알림 |

### 9. Utils 모듈 (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/utils/logger.py | **KEEP** | 로거 (핵심) |
| /home/greatbps/projects/trading_system/utils/error_recovery.py | **KEEP** | 에러 복구 (main.py에서 직접 import) |
| /home/greatbps/projects/trading_system/utils/market_schedule_manager.py | **KEEP** | 시장 스케줄 관리 |
| /home/greatbps/projects/trading_system/utils/strategy_mapper.py | **KEEP** | 전략 매퍼 |
| /home/greatbps/projects/trading_system/utils/error_handler.py | **KEEP** | 에러 핸들러 (main.py에서 직접 import) |
| /home/greatbps/projects/trading_system/utils/encoding_fix.py | **KEEP** | 인코딩 수정 (main.py에서 직접 import) |
| /home/greatbps/projects/trading_system/utils/display.py | **KEEP** | 디스플레이 유틸 |
| /home/greatbps/projects/trading_system/utils/data_utils.py | **KEEP** | 데이터 유틸 |
| /home/greatbps/projects/trading_system/utils/enhanced_error_handler.py | **KEEP** | 향상된 에러 핸들러 |
| /home/greatbps/projects/trading_system/utils/enhanced_market_schedule_manager.py | **KEEP** | 향상된 시장 스케줄 관리 |
| /home/greatbps/projects/trading_system/utils/fallback_market_schedule.py | **KEEP** | 폴백 시장 스케줄 |
| /home/greatbps/projects/trading_system/utils/http_client.py | **KEEP** | HTTP 클라이언트 |
| /home/greatbps/projects/trading_system/utils/parallel_analyzer.py | **KEEP** | 병렬 분석기 |
| /home/greatbps/projects/trading_system/utils/pattern_detector.py | **KEEP** | 패턴 감지기 |
| /home/greatbps/projects/trading_system/utils/performance_optimizer.py | **KEEP** | 성능 최적화 |
| /home/greatbps/projects/trading_system/utils/rate_limiter.py | **KEEP** | 레이트 리미터 |
| /home/greatbps/projects/trading_system/utils/realtime_display.py | **KEEP** | 실시간 디스플레이 |
| /home/greatbps/projects/trading_system/utils/safe_console.py | **KEEP** | 안전한 콘솔 |
| /home/greatbps/projects/trading_system/utils/status_definitions.py | **KEEP** | 상태 정의 |
| /home/greatbps/projects/trading_system/utils/stock_search.py | **KEEP** | 주식 검색 |
| /home/greatbps/projects/trading_system/utils/sync_token_cache.py | **KEEP** | 토큰 캐시 동기화 |
| /home/greatbps/projects/trading_system/utils/system_monitor.py | **KEEP** | 시스템 모니터 |

### 10. Backtesting (필수)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/backtesting/historical_analyzer.py | **KEEP** | 히스토리컬 분석 |
| /home/greatbps/projects/trading_system/backtesting/backtesting_engine.py | **KEEP** | 백테스팅 엔진 (main.py에서 참조) |
| /home/greatbps/projects/trading_system/backtesting/ai_backtester.py | **KEEP** | AI 백테스터 |
| /home/greatbps/projects/trading_system/backtesting/enhanced_visualizer.py | **KEEP** | 향상된 시각화 |
| /home/greatbps/projects/trading_system/backtesting/performance_visualizer.py | **KEEP** | 성능 시각화 |
| /home/greatbps/projects/trading_system/backtesting/signal_based_backtester.py | **KEEP** | 시그널 기반 백테스터 |
| /home/greatbps/projects/trading_system/backtesting/strategy_optimizer.py | **KEEP** | 전략 최적화 |
| /home/greatbps/projects/trading_system/backtesting/strategy_validator.py | **KEEP** | 전략 검증 |
| /home/greatbps/projects/trading_system/backtesting/auto_backtest_trigger.py | **KEEP** | 자동 백테스트 트리거 |
| /home/greatbps/projects/trading_system/backtesting/holding_sell_optimizer.py | **KEEP** | 보유 매도 최적화 |
| /home/greatbps/projects/trading_system/backtesting/watch_buy_optimizer.py | **KEEP** | 관심 매수 최적화 |

### 11. 지원 모듈 (실제 사용)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/monitoring/performance_monitor.py | **KEEP** | 성능 모니터 (trading_system에서 import) |
| /home/greatbps/projects/trading_system/monitoring/performance_dashboard.py | **KEEP** | 성능 대시보드 |
| /home/greatbps/projects/trading_system/monitoring/db_monitoring_scheduler.py | **KEEP** | DB 모니터링 스케줄러 |
| /home/greatbps/projects/trading_system/monitoring/monitoring_scheduler.py | **KEEP** | 모니터링 스케줄러 |
| /home/greatbps/projects/trading_system/monitoring/notification_system.py | **KEEP** | 알림 시스템 |
| /home/greatbps/projects/trading_system/monitoring/phase1_performance_monitor.py | **KEEP** | Phase1 성능 모니터 |
| /home/greatbps/projects/trading_system/monitoring/realtime_monitoring_handler.py | **KEEP** | 실시간 모니터링 핸들러 |
| /home/greatbps/projects/trading_system/monitoring/integrated_dashboard.py | **KEEP** | 통합 대시보드 |
| /home/greatbps/projects/trading_system/async_processing/async_engine.py | **KEEP** | 비동기 엔진 (trading_system에서 import) |
| /home/greatbps/projects/trading_system/async_processing/task_scheduler.py | **KEEP** | 태스크 스케줄러 |
| /home/greatbps/projects/trading_system/async_processing/async_utils.py | **KEEP** | 비동기 유틸 |
| /home/greatbps/projects/trading_system/error_handling/error_recovery_system.py | **KEEP** | 에러 복구 시스템 (trading_system에서 import) |
| /home/greatbps/projects/trading_system/signal_processing/consensus_engine.py | **KEEP** | 시그널 처리 합의 엔진 |
| /home/greatbps/projects/trading_system/signal_processing/liquidity_gate.py | **KEEP** | 유동성 게이트 |
| /home/greatbps/projects/trading_system/signal_processing/mtf_analyzer.py | **KEEP** | MTF 분석기 |
| /home/greatbps/projects/trading_system/signal_processing/news_gate.py | **KEEP** | 뉴스 게이트 |
| /home/greatbps/projects/trading_system/signal_processing/regime_gate.py | **KEEP** | 체제 게이트 |
| /home/greatbps/projects/trading_system/recommendations/squeeze_momentum_engine.py | **KEEP** | 스퀴즈 모멘텀 엔진 |
| /home/greatbps/projects/trading_system/recommendations/stock_recommendation_system.py | **KEEP** | 주식 추천 시스템 |
| /home/greatbps/projects/trading_system/api_optimization/timeout_optimizer.py | **KEEP** | 타임아웃 최적화 |
| /home/greatbps/projects/trading_system/integration/performance_integration.py | **KEEP** | 성능 통합 |
| /home/greatbps/projects/trading_system/risk_management/position_sizing.py | **KEEP** | 포지션 사이징 |
| /home/greatbps/projects/trading_system/optimization/exit_strategy_optimizer.py | **KEEP** | 청산 전략 최적화 |
| /home/greatbps/projects/trading_system/optimization/system_optimizer.py | **KEEP** | 시스템 최적화 |
| /home/greatbps/projects/trading_system/api/web_dashboard_api.py | **KEEP** | 웹 대시보드 API |
| /home/greatbps/projects/trading_system/configs/position_scoring_config.py | **KEEP** | 포지션 스코어링 설정 |
| /home/greatbps/projects/trading_system/configs/squeeze_momentum_config.py | **KEEP** | 스퀴즈 모멘텀 설정 |

### 12. 공식 테스트 디렉토리 (유지)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/tests/test_market_regime_detector.py | **KEEP** | 공식 테스트 |
| /home/greatbps/projects/trading_system/tests/test_dynamic_weight_system.py | **KEEP** | 공식 테스트 |
| /home/greatbps/projects/trading_system/tests/test_position_sizing.py | **KEEP** | 공식 테스트 |
| /home/greatbps/projects/trading_system/tests/test_squeeze_momentum_integration.py | **KEEP** | 공식 테스트 |

### 13. 스크립트 (유지)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/scripts/deploy_dynamic_weights.py | **KEEP** | 배포 스크립트 |
| /home/greatbps/projects/trading_system/scripts/init_database.py | **KEEP** | DB 초기화 스크립트 |
| /home/greatbps/projects/trading_system/scripts/update_db_schema.py | **KEEP** | DB 스키마 업데이트 |
| /home/greatbps/projects/trading_system/scripts/update_monitoring_stock_names.py | **KEEP** | 모니터링 주식명 업데이트 |
| /home/greatbps/projects/trading_system/scripts/find_stoploss_breached_stocks.py | **KEEP** | 손절가 돌파 종목 찾기 |
| /home/greatbps/projects/trading_system/scripts/execute_liquidation.py | **KEEP** | 청산 실행 |

### 14. 루트 레벨 유틸리티 스크립트 (일부 유지)
| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/init_database.py | **KEEP** | DB 초기화 (사용자가 직접 실행할 수 있는 스크립트) |
| /home/greatbps/projects/trading_system/service_controller.py | **KEEP** | 서비스 컨트롤러 |
| /home/greatbps/projects/trading_system/auto_trading_daemon.py | **KEEP** | 자동매매 데몬 |
| /home/greatbps/projects/trading_system/trading_scheduler.py | **KEEP** | 트레이딩 스케줄러 |

---

## ❌ 사용하지 않는 파일들 (MOVE)

### 1. 디버그 파일들 (34개)
**이동 대상: _deprecated/debug/**

| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/debug_api_raw_response.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_buy_signals.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_condition_api.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_holdings.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_hts_condition_list.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_hts_conditions.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_kis_connection.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_kis_response.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_monitoring_db.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_monitoring_query.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_portfolio_manager.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_profit_rate.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_rebalancing_issue.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_recommendation_issue.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_signal_scores.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_stock_name_issue.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_strategy_extraction_issue.py | **MOVE** | 디버그용 임시 파일 |
| /home/greatbps/projects/trading_system/debug_token_issue.py | **MOVE** | 디버그용 임시 파일 |

### 2. Check 파일들 (16개)
**이동 대상: _deprecated/check/**

| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/check_account_config.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_actual_holdings.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_auto_trading_status.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_column_types.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_column_values.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_holdings_debug.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_kis_trades.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_monitoring_analysis.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_monitoring_status.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_monitoring_stocks.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_real_monitoring_data.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_stock_types.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_stop_loss.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_strategy_filtering.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_today_trades.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/check_trading_status.py | **MOVE** | 검증용 임시 파일 |

### 3. Test 파일들 (루트 레벨, 23개)
**이동 대상: _deprecated/test/**

| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/test_all_conditions.py | **MOVE** | 루트 레벨 테스트 파일 (tests/ 폴더 외부) |
| /home/greatbps/projects/trading_system/test_atr_calculation.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_atr_simple.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_backtest.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_complete_system.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_condition_search.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_filtered_results.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_final_verification.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_hts_api_raw.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_hts_conditions.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_integration.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_manual_stocks.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_news_improved.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_news_parallel.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_optimization_system.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_parallel_analysis.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_parallel_performance.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_risk_validation.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_stock_data.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_strategy_mapping.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_supertrend_pagination.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/test_trading_integration.py | **MOVE** | 루트 레벨 테스트 파일 |
| /home/greatbps/projects/trading_system/Dtrading_systemtest_integration.py | **MOVE** | 루트 레벨 테스트 파일 |

### 4. Emergency 스크립트들 (6개)
**이동 대상: _deprecated/emergency/**

| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/emergency_exem_sell.py | **MOVE** | 긴급 스크립트 (일회성) |
| /home/greatbps/projects/trading_system/emergency_holdings_check.py | **MOVE** | 긴급 스크립트 (일회성) |
| /home/greatbps/projects/trading_system/emergency_stop_loss.py | **MOVE** | 긴급 스크립트 (일회성) |
| /home/greatbps/projects/trading_system/execute_emergency_stop_loss.py | **MOVE** | 긴급 스크립트 (일회성) |
| /home/greatbps/projects/trading_system/execute_liquidation.py | **MOVE** | 긴급 스크립트 (일회성) |
| /home/greatbps/projects/trading_system/execute_stop_loss_orders.py | **MOVE** | 긴급 스크립트 (일회성) |
| /home/greatbps/projects/trading_system/quick_emergency_stop_loss.py | **MOVE** | 긴급 스크립트 (일회성) |

### 5. 백업/패치 파일들 (7개)
**이동 대상: _deprecated/backup/**

| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/core/analysis_handlers_backup.py | **MOVE** | 백업 파일 |
| /home/greatbps/projects/trading_system/core/menu_handlers_backup.py | **MOVE** | 백업 파일 |
| /home/greatbps/projects/trading_system/core/menu_handlers_fixed.py | **MOVE** | 임시 수정 파일 |
| /home/greatbps/projects/trading_system/core/menu_handlers_patch.py | **MOVE** | 패치 파일 |
| /home/greatbps/projects/trading_system/utils/logger_backup.py | **MOVE** | 백업 파일 |
| /home/greatbps/projects/trading_system/utils/logger_original.py | **MOVE** | 오리지널 백업 파일 |
| /home/greatbps/projects/trading_system/utils/kis_collector_patch.py | **MOVE** | 패치 파일 |

### 6. 기타 임시/분석 파일들 (15개)
**이동 대상: _deprecated/misc/**

| 파일 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/benchmark_bottleneck.py | **MOVE** | 벤치마크용 임시 파일 |
| /home/greatbps/projects/trading_system/compare_hts_results.py | **MOVE** | 비교 분석용 임시 파일 |
| /home/greatbps/projects/trading_system/detailed_trading_analysis_report.py | **MOVE** | 분석 리포트 생성 임시 파일 |
| /home/greatbps/projects/trading_system/direct_monitoring_test.py | **MOVE** | 모니터링 테스트용 임시 파일 |
| /home/greatbps/projects/trading_system/fallback_analysis.py | **MOVE** | 폴백 분석용 임시 파일 |
| /home/greatbps/projects/trading_system/final_verification.py | **MOVE** | 검증용 임시 파일 |
| /home/greatbps/projects/trading_system/fix_condition_search.py | **MOVE** | 수정 스크립트 (이미 적용됨) |
| /home/greatbps/projects/trading_system/force_kis_token_refresh.py | **MOVE** | 토큰 갱신용 임시 파일 |
| /home/greatbps/projects/trading_system/force_monitoring_test.py | **MOVE** | 모니터링 테스트 강제 실행 |
| /home/greatbps/projects/trading_system/integration_demo.py | **MOVE** | 데모용 임시 파일 |
| /home/greatbps/projects/trading_system/kis_auth_test.py | **MOVE** | 인증 테스트용 임시 파일 |
| /home/greatbps/projects/trading_system/kis_token_check.py | **MOVE** | 토큰 체크용 임시 파일 |
| /home/greatbps/projects/trading_system/manual_analysis_test.py | **MOVE** | 수동 분석 테스트 |
| /home/greatbps/projects/trading_system/manual_trading_strategy.py | **MOVE** | 수동 트레이딩 전략 테스트 |
| /home/greatbps/projects/trading_system/manual_update_names.py | **MOVE** | 수동 업데이트 스크립트 |
| /home/greatbps/projects/trading_system/minimal_monitoring_check.py | **MOVE** | 최소 모니터링 체크 |
| /home/greatbps/projects/trading_system/portfolio_cleanup_strategy.py | **MOVE** | 포트폴리오 정리 전략 (strategies/에 있음) |
| /home/greatbps/projects/trading_system/position_cleanup_strategy.py | **MOVE** | 포지션 정리 전략 (중복) |
| /home/greatbps/projects/trading_system/start_auto_system.py | **MOVE** | 자동 시스템 시작 스크립트 (중복) |
| /home/greatbps/projects/trading_system/stop_auto_trading.py | **MOVE** | 자동매매 중지 스크립트 (중복) |
| /home/greatbps/projects/trading_system/strategy_auto_executor.py | **MOVE** | 전략 자동 실행 (중복) |
| /home/greatbps/projects/trading_system/trading_logic_performance_analysis.py | **MOVE** | 성능 분석 임시 파일 |
| /home/greatbps/projects/trading_system/verify_hts_mapping.py | **MOVE** | HTS 매핑 검증 스크립트 |
| /home/greatbps/projects/trading_system/verify_realtime_hts.py | **MOVE** | 실시간 HTS 검증 스크립트 |
| /home/greatbps/projects/trading_system/database/fix_active_stocks.py | **MOVE** | DB 수정 스크립트 (이미 적용됨) |
| /home/greatbps/projects/trading_system/database/reset_db.py | **MOVE** | DB 리셋 스크립트 (위험) |
| /home/greatbps/projects/trading_system/core/fix_menu.py | **MOVE** | 메뉴 수정 스크립트 (이미 적용됨) |
| /home/greatbps/projects/trading_system/get-pip.py | **MOVE** | pip 설치 스크립트 (불필요) |
| /home/greatbps/projects/trading_system/setup_oracle_db.py | **MOVE** | Oracle DB 설정 (사용하지 않음, PostgreSQL 사용) |

### 7. 사용하지 않는 디렉토리 (전체 이동)
**이동 대상: _deprecated/**

| 디렉토리 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/ai/ | **MOVE** | ai 폴더 내 모델들 사용하지 않음 (analyzers/ai_predictor.py만 사용) |
| /home/greatbps/projects/trading_system/old_config_package/ | **MOVE** | 구버전 설정 패키지 (config.py로 대체됨) |
| /home/greatbps/projects/trading_system/precision_analyzer/ | **MOVE** | 정밀 분석기 (import 없음, 사용하지 않음) |
| /home/greatbps/projects/trading_system/services/ | **MOVE** | 비어있는 디렉토리 (__init__.py만 존재) |

### 8. 데이터/문서 디렉토리 (유지하되 정리 권장)
**현재 위치 유지 (데이터/문서)**

| 디렉토리 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/analysis/ | **KEEP** | 분석 결과 저장 디렉토리 |
| /home/greatbps/projects/trading_system/analysis_results/ | **KEEP** | 분석 결과 저장 디렉토리 |
| /home/greatbps/projects/trading_system/ai_models/ | **KEEP** | AI 모델 저장 디렉토리 |
| /home/greatbps/projects/trading_system/data/ | **KEEP** | 데이터 저장 디렉토리 |
| /home/greatbps/projects/trading_system/logs/ | **KEEP** | 로그 디렉토리 |
| /home/greatbps/projects/trading_system/metrics/ | **KEEP** | 메트릭 저장 디렉토리 |
| /home/greatbps/projects/trading_system/performance_reports/ | **KEEP** | 성능 리포트 디렉토리 |
| /home/greatbps/projects/trading_system/reports/ | **KEEP** | 리포트 디렉토리 |

### 9. 문서/참고 디렉토리 (정리 권장)
**이동 대상: docs/ 하위로 재구성**

| 디렉토리 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/docs/ | **KEEP** | 문서 디렉토리 (정리 권장) |
| /home/greatbps/projects/trading_system/optimization_plans/ | **REORGANIZE** | docs/optimization_plans/로 이동 권장 |
| /home/greatbps/projects/trading_system/개발현황/ | **REORGANIZE** | docs/development_status/로 이동 권장 |
| /home/greatbps/projects/trading_system/공식API/ | **REORGANIZE** | docs/official_api/로 이동 권장 |

### 10. 외부 도구/미사용 디렉토리
**이동 대상: _deprecated/**

| 디렉토리 경로 | 이동 여부 | 이유 |
|----------|---------|------|
| /home/greatbps/projects/trading_system/Superclaude/ | **MOVE** | 외부 도구 (프로젝트와 무관) |
| /home/greatbps/projects/trading_system/claudia/ | **MOVE** | 외부 도구 (프로젝트와 무관) |
| /home/greatbps/projects/trading_system/cluefin/ | **MOVE** | 외부 도구 (프로젝트와 무관) |
| /home/greatbps/projects/trading_system/com/ | **MOVE** | 용도 불명 디렉토리 |

---

## 📊 통계 요약

### 이동 대상 파일 통계
- **debug_*.py**: 18개
- **check_*.py**: 16개
- **test_*.py (루트 레벨)**: 23개
- **emergency_*.py**: 7개
- **백업/패치 파일**: 7개
- **기타 임시 파일**: 27개
- **총계**: 약 98개 파일

### 이동 대상 디렉토리 통계
- **사용하지 않는 모듈**: 4개 (ai/, old_config_package/, precision_analyzer/, services/)
- **외부 도구**: 4개 (Superclaude/, claudia/, cluefin/, com/)
- **총계**: 8개 디렉토리

### 유지 파일 통계
- **핵심 시스템**: 4개
- **Core 모듈**: 14개
- **Data Collectors**: 10개
- **Analyzers**: 26개
- **Strategies**: 20개
- **Trading**: 8개
- **Database**: 7개
- **Notifications**: 3개
- **Utils**: 22개
- **Backtesting**: 11개
- **지원 모듈**: 29개
- **공식 테스트**: 4개
- **스크립트**: 10개
- **총계**: 약 168개 파일

---

## 🎯 권장 조치사항

### 1. 단계별 정리 계획

#### Phase 1: 디버그/체크/테스트 파일 이동
```bash
mkdir -p _deprecated/{debug,check,test,emergency,backup,misc}

# Debug 파일 이동
mv debug_*.py _deprecated/debug/

# Check 파일 이동
mv check_*.py _deprecated/check/

# Test 파일 이동 (루트 레벨만)
mv test_*.py _deprecated/test/
mv Dtrading_systemtest_integration.py _deprecated/test/

# Emergency 스크립트 이동
mv emergency_*.py _deprecated/emergency/
mv execute_emergency_stop_loss.py _deprecated/emergency/
mv execute_liquidation.py _deprecated/emergency/
mv execute_stop_loss_orders.py _deprecated/emergency/
mv quick_emergency_stop_loss.py _deprecated/emergency/
```

#### Phase 2: 백업 파일 이동
```bash
# Core 백업 파일
mv core/*_backup.py _deprecated/backup/
mv core/*_fixed.py _deprecated/backup/
mv core/*_patch.py _deprecated/backup/

# Utils 백업 파일
mv utils/*_backup.py _deprecated/backup/
mv utils/*_original.py _deprecated/backup/
mv utils/*_patch.py _deprecated/backup/
```

#### Phase 3: 사용하지 않는 디렉토리 이동
```bash
# 사용하지 않는 모듈
mv ai/ _deprecated/
mv old_config_package/ _deprecated/
mv precision_analyzer/ _deprecated/
mv services/ _deprecated/

# 외부 도구
mv Superclaude/ _deprecated/
mv claudia/ _deprecated/
mv cluefin/ _deprecated/
mv com/ _deprecated/
```

#### Phase 4: 기타 임시 파일 이동
```bash
mv benchmark_bottleneck.py _deprecated/misc/
mv compare_hts_results.py _deprecated/misc/
mv detailed_trading_analysis_report.py _deprecated/misc/
mv direct_monitoring_test.py _deprecated/misc/
mv fallback_analysis.py _deprecated/misc/
mv final_verification.py _deprecated/misc/
mv fix_condition_search.py _deprecated/misc/
mv force_kis_token_refresh.py _deprecated/misc/
mv force_monitoring_test.py _deprecated/misc/
mv integration_demo.py _deprecated/misc/
mv kis_auth_test.py _deprecated/misc/
mv kis_token_check.py _deprecated/misc/
mv manual_*.py _deprecated/misc/
mv minimal_monitoring_check.py _deprecated/misc/
mv portfolio_cleanup_strategy.py _deprecated/misc/
mv position_cleanup_strategy.py _deprecated/misc/
mv start_auto_system.py _deprecated/misc/
mv stop_auto_trading.py _deprecated/misc/
mv strategy_auto_executor.py _deprecated/misc/
mv trading_logic_performance_analysis.py _deprecated/misc/
mv verify_*.py _deprecated/misc/
mv get-pip.py _deprecated/misc/
mv setup_oracle_db.py _deprecated/misc/
mv database/fix_active_stocks.py _deprecated/misc/
mv database/reset_db.py _deprecated/misc/
mv core/fix_menu.py _deprecated/misc/
```

### 2. .gitignore 업데이트
```gitignore
# Deprecated files
_deprecated/

# Debug and test files (root level only)
debug_*.py
check_*.py
test_*.py
emergency_*.py

# Backup files
*_backup.py
*_original.py
*_fixed.py
*_patch.py

# Temporary files
*.save
err.txt.save
```

### 3. 검증 절차
1. 이동 전 백업 생성
2. 각 Phase별로 순차 이동
3. 이동 후 `python main.py` 실행하여 정상 동작 확인
4. 모든 import 오류가 없는지 확인
5. 핵심 기능 테스트 실행

---

## ⚠️ 주의사항

1. **절대 삭제하지 말 것**: 파일을 삭제하지 말고 _deprecated/로 이동만 할 것
2. **백업 필수**: 이동 작업 전 전체 프로젝트 백업 생성
3. **단계별 검증**: 각 Phase 완료 후 시스템 정상 동작 확인
4. **Git 커밋**: 각 Phase별로 커밋하여 롤백 가능하도록 함
5. **tests/ 폴더 유지**: tests/ 디렉토리 내의 공식 테스트는 절대 이동하지 말 것

---

## 📝 결론

이 분석을 통해:
- **98개의 임시/디버그 파일** 발견 및 이동 대상 지정
- **8개의 사용하지 않는 디렉토리** 발견 및 이동 대상 지정
- **168개의 핵심 파일** 식별 및 유지 대상 지정
- 프로젝트 구조를 깔끔하게 정리하여 유지보수성 향상 가능

권장: Phase 1부터 순차적으로 진행하며, 각 단계마다 시스템 정상 동작 확인
