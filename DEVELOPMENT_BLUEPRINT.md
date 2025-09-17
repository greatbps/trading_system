# 개발 청사진 (Development Blueprint)

## 1. 긴급 청산 시스템 (Urgent Liquidation System)

*   **목표:** 손절가를 하회하는 보유 종목을 신속하고 안전하게 청산한다.
*   **설계 원칙:**
    *   **안전성 우선:** 자동 실행이 아닌, 사용자의 최종 확인(Confirm)을 반드시 거친다.
    *   **명확성:** 청산 대상, 예상 손익, 사유를 명확히 제시한다.
    *   **일회성 실행:** 정규 기능이 아닌, 필요시 실행하는 독립 스크립트로 구현하여 시스템 복잡도를 낮춘다.
*   **구현 계획:**
    1.  **`find_stoploss_breached_stocks.py` 스크립트 작성:**
        *   **기능:** 청산 대상을 '찾아서 보여주기만' 하는 스크립트. (매도 기능 없음)
        *   **프로세스:** KIS API로 보유 종목 조회 -> DB에서 손절가 조회 -> 조건 비교 -> 대상 목록을 테이블로 출력.
    2.  **사용자 확인:** 스크립트 실행 결과를 보고 사용자가 청산 여부 결정.
    3.  **`execute_liquidation.py` 스크립트 작성 (사용자 동의 시):**
        *   **기능:** `find...` 스크립트의 로직을 기반으로, 실제 시장가 매도 주문을 실행하는 스크립트.
        *   **프로세스:** 청산 대상 목록 생성 -> **"정말로 다음 N개 종목을 시장가 매도합니다. 동의하십니까? (y/n)"** 와 같은 최종 확인 절차 추가 -> `executor.sell_stock` 호출.

## 2. 시장 시간 인지 시스템 (Market Hours Awareness System)

*   **목표:** 모든 모니터링과 매매 관련 작업이 정규 장 시간 및 개장일에만 동작하도록 보장한다.
*   **설계 원칙:**
    *   **중앙 관리:** 시간 확인 로직을 `MarketScheduleManager`에서 중앙 관리하여 일관성을 유지한다.
    *   **명시적 확인:** 각 주요 기능(모니터링 루프, 주문 실행 등)의 시작 지점에서 명시적으로 장 시간을 확인하는 '게이트'를 둔다.
    *   **확장성:** 향후 프리마켓, 애프터마켓 등을 고려할 수 있는 구조로 설계한다.
*   **구현 계획:**
    1.  **`utils/market_schedule_manager.py` 기능 분석 및 강화:**
        *   현재 KIS API의 '오늘 휴장일 여부 조회' 기능이 연동되어 있는지 확인.
        *   만약 없다면, 해당 API(`uapi/domestic-stock/v1/quotations/inquire-daily-chartprice`의 응답 헤더 또는 별도 API)를 연동하여 `is_today_market_open()`과 같은 메서드 추가.
    2.  **`trading/db_auto_trader.py` 수정:**
        *   `_monitoring_cycle` 함수의 맨 처음에 `market_manager.is_trading_allowed_now()` 와 같은 확인 로직을 추가하여, 장 시간이 아닐 경우 사이클 전체를 건너뛰고 대기하도록 수정.
    3.  **`core/db_auto_trading_handler.py` 수정:**
        *   사용자가 메뉴를 통해 직접 매매/모니터링을 실행하는 함수(`_manual_trade`, `_start_monitoring` 등)의 시작 부분에도 장 시간 확인 로직을 추가하여 사용자에게 즉시 피드백.
