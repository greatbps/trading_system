# Claude 작업 지시서: `MockTradingSystem` 오류 해결

## 1. 문제 상황

프로그램 실행 시, `'MockTradingSystem' object has no attribute 'data_collector'` 오류가 발생하며 실시간 현황판이 동작하지 않습니다.

## 2. 근본 원인

`strategy_auto_executor.py` 파일이 자체적으로 테스트용 가짜 객체인 `MockTradingSystem`을 생성하여 사용하고 있습니다. 이 가짜 객체에는 실제 데이터 수집기(`data_collector`)가 없어, 데이터 조회 시 오류가 발생합니다.

## 3. 해결 목표

가짜 객체를 생성하는 대신, 프로그램 시작 시 생성된 **실제 `TradingSystem` 객체**를 `StrategyAutoExecutor`까지 전달하여 사용하도록 코드 구조를 수정(리팩토링)합니다.

## 4. 작업 절차

### 단계 1: `core/trading_system.py` 수정

`DatabaseAutoTrader` 객체를 생성하는 부분에, `TradingSystem`의 인스턴스(`self`)를 `trading_system`이라는 인자로 전달해줍니다.

- **파일:** `core/trading_system.py`
- **대상:** `self.db_auto_trader` 초기화 부분
- **수정 전:**
```python
                    self.db_auto_trader = DatabaseAutoTrader(
                        self.config,
                        self.data_collector,
                        self.trading_executor,
                        market_manager,  # 올바른 MarketScheduleManager 전달
                        self.analysis_engine,
                        self.db_manager
                    )
```
- **수정 후:**
```python
                    self.db_auto_trader = DatabaseAutoTrader(
                        self.config,
                        self.data_collector,
                        self.trading_executor,
                        market_manager,  # 올바른 MarketScheduleManager 전달
                        self.analysis_engine,
                        self.db_manager,
                        trading_system=self  # 이 라인 추가
                    )
```

### 단계 2: `trading/db_auto_trader.py` 수정

`DatabaseAutoTrader`가 `trading_system` 인자를 받아서, 자신이 생성하는 `StrategyAutoExecutor`에게 다시 전달하도록 수정합니다.

- **파일:** `trading/db_auto_trader.py`
- **수정 1: `__init__` 메서드 시그니처 변경**
    - **수정 전:** `def __init__(self, config, kis_collector, executor: TradingExecutor, market_manager, analysis_engine=None, db_manager=None):`
    - **수정 후:** `def __init__(self, config, kis_collector, executor: TradingExecutor, market_manager, analysis_engine=None, db_manager=None, trading_system=None):`
- **수정 2: `__init__` 메서드 내부에 `trading_system` 저장 코드 추가**
    - `self.logger = get_logger("DatabaseAutoTrader")` 라인 바로 다음에 `self.trading_system = trading_system` 코드를 추가합니다.
- **수정 3: `initialize_strategy_auto_executor` 메서드 수정**
    - `StrategyAutoExecutor`를 생성할 때 `self.trading_system`을 전달합니다.
    - **수정 전:** `self.strategy_auto_executor = StrategyAutoExecutor(self.config, self.db_manager)`
    - **수정 후:** `self.strategy_auto_executor = StrategyAutoExecutor(self.config, self.db_manager, self.trading_system)`

### 단계 3: `strategy_auto_executor.py` 수정

`StrategyAutoExecutor`가 실제 `trading_system` 객체를 받아 사용하고, 문제가 되었던 `MockTradingSystem` 코드를 완전히 제거합니다.

- **파일:** `strategy_auto_executor.py`
- **수정 1: `__init__` 메서드 시그니처 변경**
    - **수정 전:** `def __init__(self, config: Config, db_manager: DatabaseManager):`
    - **수정 후:** `def __init__(self, config: Config, db_manager: DatabaseManager, trading_system):`
- **수정 2: `__init__` 메서드 내부에 `system` 저장 코드 추가**
    - `self.logger = logging.getLogger('StrategyAutoExecutor')` 라인 바로 다음에 `self.system = trading_system` 코드를 추가합니다.
- **수정 3: `initialize_system` 메서드 전체 교체**
    - `MockTradingSystem`을 생성하던 기존 로직을 모두 삭제하고, 전달받은 실제 `system` 객체를 사용하도록 아래 코드로 완전히 교체합니다.

    ```python
    async def initialize_system(self):
        """시스템 초기화"""
        try:
            if self.system is None:
                self.logger.error("TradingSystem 객체가 전달되지 않았습니다.")
                return False
            
            self.analysis_handlers = AnalysisHandlers(self.system)
            self.logger.info("전략 자동 실행 시스템 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"시스템 초기화 실패: {e}")
            return False
    ```

이 3단계의 리팩토링을 통해, 시스템의 모든 부분이 일관되게 실제 데이터 수집기를 바라보게 되어 오류가 해결될 것입니다.