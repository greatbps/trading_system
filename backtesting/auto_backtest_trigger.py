#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_backtest_trigger.py

자동 백테스팅 트리거 및 시각화 시스템
조건이 맞으면 자동으로 백테스팅 실행하고 결과 시각화
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from utils.logger import get_logger
from .backtesting_engine import BacktestingEngine, BacktestResult
from .enhanced_visualizer import EnhancedVisualizer
from .strategy_validator import StrategyValidator

@dataclass
class BacktestTrigger:
    """백테스팅 자동 실행 트리거"""
    name: str
    trigger_type: str  # market_change, performance_drop, schedule, signal_count
    condition: Dict[str, Any]
    enabled: bool = True
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    priority: int = 1  # 1=높음, 2=보통, 3=낮음

@dataclass
class BacktestResult:
    """백테스팅 실행 결과"""
    trigger_name: str
    execution_time: datetime
    strategies_tested: List[str]
    best_strategy: str
    best_performance: float
    results_path: str
    visualization_path: str
    alerts_generated: List[str]

class AutoBacktestTrigger:
    """자동 백테스팅 트리거 시스템"""

    def __init__(self, config=None, trading_handler=None):
        """자동 백테스팅 시스템 초기화"""
        self.logger = get_logger("AutoBacktestTrigger")
        self.config = config
        self.trading_handler = trading_handler

        # 백테스팅 엔진 및 시각화
        self.backtest_engine = BacktestingEngine(config)
        self.visualizer = EnhancedVisualizer(config)
        self.validator = StrategyValidator(config)

        # 실행 상태
        self.is_active = False
        self.check_interval = 300  # 5분마다 체크

        # 트리거 조건들
        self.triggers = self._initialize_triggers()

        # 실행 히스토리
        self.execution_history: List[BacktestResult] = []

        # 현재 시장 상태
        self.market_state = {
            "volatility": 0,
            "trend": "neutral",
            "volume": 0,
            "last_updated": datetime.now()
        }

        # 설정 파일
        self.settings_file = Path("data/auto_backtest_settings.json")
        self._load_settings()

    def _initialize_triggers(self) -> List[BacktestTrigger]:
        """자동 트리거 조건 초기화"""
        return [
            # 시장 변동성 급증시
            BacktestTrigger(
                name="high_volatility",
                trigger_type="market_change",
                condition={
                    "volatility_threshold": 25.0,  # 25% 이상
                    "duration_minutes": 30,        # 30분 지속
                    "strategies": ["momentum", "breakout", "scalping"]
                },
                priority=1
            ),

            # 포트폴리오 성과 악화시
            BacktestTrigger(
                name="performance_drop",
                trigger_type="performance_drop",
                condition={
                    "loss_threshold": -5.0,        # -5% 이하
                    "period_hours": 4,             # 4시간 동안
                    "strategies": ["defensive", "mean_reversion"]
                },
                priority=1
            ),

            # 매일 시장 마감 후
            BacktestTrigger(
                name="daily_close",
                trigger_type="schedule",
                condition={
                    "time": "15:30",               # 오후 3시 30분
                    "weekdays_only": True,
                    "strategies": ["all"]
                },
                priority=2
            ),

            # 거래 신호 급증시
            BacktestTrigger(
                name="signal_spike",
                trigger_type="signal_count",
                condition={
                    "signal_threshold": 10,        # 10개 이상
                    "time_window_minutes": 15,     # 15분 내
                    "strategies": ["signal_based"]
                },
                priority=1
            ),

            # 주간 성과 리뷰
            BacktestTrigger(
                name="weekly_review",
                trigger_type="schedule",
                condition={
                    "day": "friday",
                    "time": "16:00",
                    "strategies": ["all"]
                },
                priority=3
            ),

            # 새로운 전략 추가시 검증
            BacktestTrigger(
                name="new_strategy_validation",
                trigger_type="strategy_change",
                condition={
                    "auto_validate": True,
                    "comparison_period_days": 30,
                    "strategies": ["new"]
                },
                priority=1
            )
        ]

    async def start_monitoring(self):
        """자동 모니터링 시작"""
        try:
            if self.is_active:
                self.logger.warning("이미 자동 백테스팅이 실행 중입니다")
                return

            self.is_active = True
            self.logger.info("🔄 자동 백테스팅 모니터링 시작")

            # 모니터링 루프
            await self._monitoring_loop()

        except Exception as e:
            self.logger.error(f"❌ 자동 백테스팅 시작 실패: {e}")
            self.is_active = False

    async def stop_monitoring(self):
        """자동 모니터링 중지"""
        self.is_active = False
        self.logger.info("⏹️ 자동 백테스팅 모니터링 중지")

    async def _monitoring_loop(self):
        """메인 모니터링 루프"""
        try:
            while self.is_active:
                try:
                    # 시장 상태 업데이트
                    await self._update_market_state()

                    # 트리거 조건 체크
                    triggered_items = await self._check_all_triggers()

                    # 실행할 트리거가 있으면 처리
                    if triggered_items:
                        await self._execute_triggered_backtests(triggered_items)

                    # 대기
                    await asyncio.sleep(self.check_interval)

                except Exception as e:
                    self.logger.error(f"❌ 모니터링 루프 오류: {e}")
                    await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            self.logger.info("🛑 백테스팅 모니터링 루프 취소됨")
        except Exception as e:
            self.logger.error(f"❌ 백테스팅 모니터링 치명적 오류: {e}")
        finally:
            self.is_active = False

    async def _update_market_state(self):
        """시장 상태 업데이트"""
        try:
            # TODO: 실제 시장 데이터로 업데이트
            # 현재는 시뮬레이션 데이터 사용

            import random
            current_time = datetime.now()

            # 시뮬레이션: 장중 시간대에 변동성 증가
            if 9 <= current_time.hour <= 15:
                base_volatility = random.uniform(10, 30)
            else:
                base_volatility = random.uniform(5, 15)

            self.market_state.update({
                "volatility": base_volatility,
                "trend": random.choice(["bullish", "bearish", "neutral"]),
                "volume": random.uniform(0.5, 2.0),  # 평균 대비 배수
                "last_updated": current_time
            })

            self.logger.debug(
                f"📈 시장 상태 업데이트: 변동성={self.market_state['volatility']:.1f}%, "
                f"트렌드={self.market_state['trend']}"
            )

        except Exception as e:
            self.logger.error(f"❌ 시장 상태 업데이트 실패: {e}")

    async def _check_all_triggers(self) -> List[BacktestTrigger]:
        """모든 트리거 조건 체크"""
        triggered = []

        for trigger in self.triggers:
            if not trigger.enabled:
                continue

            is_triggered = False

            try:
                if trigger.trigger_type == "market_change":
                    is_triggered = await self._check_market_trigger(trigger)
                elif trigger.trigger_type == "performance_drop":
                    is_triggered = await self._check_performance_trigger(trigger)
                elif trigger.trigger_type == "schedule":
                    is_triggered = await self._check_schedule_trigger(trigger)
                elif trigger.trigger_type == "signal_count":
                    is_triggered = await self._check_signal_trigger(trigger)

                if is_triggered:
                    triggered.append(trigger)
                    self.logger.info(f"🔥 트리거 활성화: {trigger.name}")

            except Exception as e:
                self.logger.error(f"❌ 트리거 체크 실패 ({trigger.name}): {e}")

        return triggered

    async def _check_market_trigger(self, trigger: BacktestTrigger) -> bool:
        """시장 변화 트리거 체크"""
        try:
            condition = trigger.condition
            current_volatility = self.market_state["volatility"]
            threshold = condition.get("volatility_threshold", 25.0)

            # 변동성 임계값 체크
            if current_volatility >= threshold:
                # 지속 시간 체크 (간소화)
                duration_minutes = condition.get("duration_minutes", 30)

                # 마지막 실행에서 충분한 시간이 지났는지 체크
                if (trigger.last_executed is None or
                    (datetime.now() - trigger.last_executed).total_seconds() >= duration_minutes * 60):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"❌ 시장 트리거 체크 실패: {e}")
            return False

    async def _check_performance_trigger(self, trigger: BacktestTrigger) -> bool:
        """성과 악화 트리거 체크"""
        try:
            # TODO: 실제 포트폴리오 성과 데이터 사용
            # 현재는 시뮬레이션

            import random
            current_performance = random.uniform(-10, 5)  # -10% ~ +5%

            condition = trigger.condition
            loss_threshold = condition.get("loss_threshold", -5.0)

            if current_performance <= loss_threshold:
                # 지속 시간 체크
                period_hours = condition.get("period_hours", 4)

                if (trigger.last_executed is None or
                    (datetime.now() - trigger.last_executed).total_seconds() >= period_hours * 3600):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"❌ 성과 트리거 체크 실패: {e}")
            return False

    async def _check_schedule_trigger(self, trigger: BacktestTrigger) -> bool:
        """스케줄 트리거 체크"""
        try:
            condition = trigger.condition
            current_time = datetime.now()

            # 시간 체크
            target_time = condition.get("time", "15:30")
            target_hour, target_minute = map(int, target_time.split(":"))

            time_match = (current_time.hour == target_hour and
                         current_time.minute == target_minute)

            if not time_match:
                return False

            # 요일 체크
            if condition.get("weekdays_only", False):
                if current_time.weekday() >= 5:  # 토, 일
                    return False

            # 특정 요일 체크
            target_day = condition.get("day")
            if target_day:
                weekdays = {
                    "monday": 0, "tuesday": 1, "wednesday": 2,
                    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
                }
                if current_time.weekday() != weekdays.get(target_day, -1):
                    return False

            # 오늘 이미 실행했는지 체크
            if (trigger.last_executed and
                trigger.last_executed.date() == current_time.date()):
                return False

            return True

        except Exception as e:
            self.logger.error(f"❌ 스케줄 트리거 체크 실패: {e}")
            return False

    async def _check_signal_trigger(self, trigger: BacktestTrigger) -> bool:
        """신호 수량 트리거 체크"""
        try:
            # TODO: 실제 거래 신호 데이터 사용
            # 현재는 시뮬레이션

            import random
            current_signals = random.randint(0, 20)

            condition = trigger.condition
            signal_threshold = condition.get("signal_threshold", 10)

            if current_signals >= signal_threshold:
                time_window = condition.get("time_window_minutes", 15)

                if (trigger.last_executed is None or
                    (datetime.now() - trigger.last_executed).total_seconds() >= time_window * 60):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"❌ 신호 트리거 체크 실패: {e}")
            return False

    async def _execute_triggered_backtests(self, triggers: List[BacktestTrigger]):
        """트리거된 백테스팅 실행"""
        try:
            # 우선순위별 정렬
            triggers.sort(key=lambda x: x.priority)

            for trigger in triggers:
                try:
                    self.logger.info(f"🚀 자동 백테스팅 실행: {trigger.name}")

                    # 백테스팅 실행
                    result = await self._run_backtest_for_trigger(trigger)

                    if result:
                        # 실행 기록 업데이트
                        trigger.last_executed = datetime.now()
                        trigger.execution_count += 1

                        self.execution_history.append(result)

                        # 결과 처리
                        await self._process_backtest_result(result, trigger)

                except Exception as e:
                    self.logger.error(f"❌ 백테스팅 실행 실패 ({trigger.name}): {e}")

        except Exception as e:
            self.logger.error(f"❌ 트리거된 백테스팅 실행 실패: {e}")

    async def _run_backtest_for_trigger(self, trigger: BacktestTrigger) -> Optional[BacktestResult]:
        """특정 트리거에 대한 백테스팅 실행"""
        try:
            condition = trigger.condition
            strategies = condition.get("strategies", ["momentum"])

            # "all" 전략인 경우 모든 전략 사용
            if strategies == ["all"]:
                strategies = ["momentum", "breakout", "mean_reversion", "scalping"]

            # 백테스팅 실행 (시뮬레이션)
            results = []
            best_strategy = ""
            best_performance = -float('inf')

            for strategy_name in strategies:
                # TODO: 실제 백테스팅 엔진 사용
                # result = await self.backtest_engine.run_strategy_backtest(strategy_name)

                # 시뮬레이션 결과
                import random
                performance = random.uniform(-10, 20)

                if performance > best_performance:
                    best_performance = performance
                    best_strategy = strategy_name

                results.append({
                    "strategy": strategy_name,
                    "performance": performance
                })

            # 시각화 생성
            visualization_path = await self._create_auto_visualization(trigger, results)

            # 결과 저장
            results_path = await self._save_backtest_results(trigger, results)

            # 알림 생성
            alerts = await self._generate_alerts(trigger, results, best_performance)

            return BacktestResult(
                trigger_name=trigger.name,
                execution_time=datetime.now(),
                strategies_tested=strategies,
                best_strategy=best_strategy,
                best_performance=best_performance,
                results_path=results_path,
                visualization_path=visualization_path,
                alerts_generated=alerts
            )

        except Exception as e:
            self.logger.error(f"❌ 백테스팅 실행 실패: {e}")
            return None

    async def _create_auto_visualization(self, trigger: BacktestTrigger, results: List[Dict]) -> str:
        """자동 시각화 생성"""
        try:
            # 간단한 결과 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            viz_file = Path(f"reports/auto_backtest_{trigger.name}_{timestamp}.json")

            viz_data = {
                "trigger": trigger.name,
                "execution_time": datetime.now().isoformat(),
                "market_state": self.market_state.copy(),
                "results": results,
                "summary": {
                    "total_strategies": len(results),
                    "best_performance": max(r["performance"] for r in results),
                    "avg_performance": sum(r["performance"] for r in results) / len(results)
                }
            }

            # 디렉토리 생성
            viz_file.parent.mkdir(exist_ok=True)

            with open(viz_file, 'w', encoding='utf-8') as f:
                json.dump(viz_data, f, ensure_ascii=False, indent=2)

            return str(viz_file)

        except Exception as e:
            self.logger.error(f"❌ 자동 시각화 생성 실패: {e}")
            return ""

    async def _save_backtest_results(self, trigger: BacktestTrigger, results: List[Dict]) -> str:
        """백테스팅 결과 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = Path(f"data/backtest_results_{trigger.name}_{timestamp}.json")

            results_data = {
                "trigger_name": trigger.name,
                "trigger_type": trigger.trigger_type,
                "execution_time": datetime.now().isoformat(),
                "market_conditions": self.market_state.copy(),
                "strategies_tested": [r["strategy"] for r in results],
                "performance_data": results,
                "trigger_condition": trigger.condition
            }

            # 디렉토리 생성
            results_file.parent.mkdir(exist_ok=True)

            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)

            return str(results_file)

        except Exception as e:
            self.logger.error(f"❌ 백테스팅 결과 저장 실패: {e}")
            return ""

    async def _generate_alerts(self, trigger: BacktestTrigger, results: List[Dict], best_performance: float) -> List[str]:
        """알림 생성"""
        alerts = []

        try:
            # 성과 기반 알림
            if best_performance < -5:
                alerts.append(f"⚠️ 주의: 최고 전략도 {best_performance:.1f}% 손실")
            elif best_performance > 15:
                alerts.append(f"🎯 기회: {best_performance:.1f}% 수익 전략 발견!")

            # 트리거 타입별 알림
            if trigger.trigger_type == "market_change":
                alerts.append(f"📈 시장 변동성 {self.market_state['volatility']:.1f}%로 백테스팅 실행")
            elif trigger.trigger_type == "performance_drop":
                alerts.append(f"📉 성과 악화로 인한 전략 재검토 완료")

            # 전략 추천
            best_strategy = max(results, key=lambda x: x["performance"])
            alerts.append(f"💡 추천 전략: {best_strategy['strategy']} ({best_strategy['performance']:.1f}%)")

        except Exception as e:
            self.logger.error(f"❌ 알림 생성 실패: {e}")

        return alerts

    async def _process_backtest_result(self, result: BacktestResult, trigger: BacktestTrigger):
        """백테스팅 결과 후처리"""
        try:
            # 로그 출력
            self.logger.info(
                f"✅ 자동 백테스팅 완료 ({result.trigger_name}): "
                f"최고 성과 {result.best_performance:.1f}% ({result.best_strategy})"
            )

            # 알림 처리
            for alert in result.alerts_generated:
                self.logger.info(f"🔔 {alert}")

            # 중요한 결과인 경우 추가 처리
            if result.best_performance > 15 or result.best_performance < -10:
                await self._handle_significant_result(result, trigger)

        except Exception as e:
            self.logger.error(f"❌ 백테스팅 결과 후처리 실패: {e}")

    async def _handle_significant_result(self, result: BacktestResult, trigger: BacktestTrigger):
        """중요한 결과에 대한 특별 처리"""
        try:
            if result.best_performance > 15:
                # 고수익 기회 발견
                self.logger.info("🎯 고수익 기회 발견 - 추가 검증 실행")

                # TODO: 추가 검증 백테스팅 실행
                # await self._run_validation_backtest(result.best_strategy)

            elif result.best_performance < -10:
                # 큰 손실 가능성
                self.logger.warning("🚨 위험 신호 - 보수적 전략 검토")

                # TODO: 보수적 전략 자동 실행
                # await self._activate_defensive_mode()

        except Exception as e:
            self.logger.error(f"❌ 중요 결과 처리 실패: {e}")

    def _load_settings(self):
        """설정 로드"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 체크 간격 설정
                self.check_interval = data.get("check_interval", 300)

                # 트리거 설정 로드
                if "triggers" in data:
                    for trigger_data in data["triggers"]:
                        trigger_name = trigger_data.get("name")
                        for trigger in self.triggers:
                            if trigger.name == trigger_name:
                                trigger.enabled = trigger_data.get("enabled", True)
                                trigger.condition.update(trigger_data.get("condition", {}))
                                break

                self.logger.info("✅ 자동 백테스팅 설정을 로드했습니다")

        except Exception as e:
            self.logger.error(f"❌ 설정 로드 실패: {e}")

    async def save_settings(self):
        """설정 저장"""
        try:
            data = {
                "check_interval": self.check_interval,
                "triggers": [
                    {
                        "name": trigger.name,
                        "trigger_type": trigger.trigger_type,
                        "condition": trigger.condition,
                        "enabled": trigger.enabled,
                        "priority": trigger.priority,
                        "execution_count": trigger.execution_count
                    }
                    for trigger in self.triggers
                ],
                "last_updated": datetime.now().isoformat()
            }

            # 디렉토리 생성
            self.settings_file.parent.mkdir(exist_ok=True)

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info("✅ 자동 백테스팅 설정 저장 완료")

        except Exception as e:
            self.logger.error(f"❌ 설정 저장 실패: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        return {
            "is_active": self.is_active,
            "check_interval": self.check_interval,
            "market_state": self.market_state.copy(),
            "triggers": [
                {
                    "name": trigger.name,
                    "enabled": trigger.enabled,
                    "execution_count": trigger.execution_count,
                    "last_executed": trigger.last_executed.isoformat() if trigger.last_executed else None
                }
                for trigger in self.triggers
            ],
            "recent_executions": [
                {
                    "trigger_name": result.trigger_name,
                    "execution_time": result.execution_time.isoformat(),
                    "best_strategy": result.best_strategy,
                    "best_performance": result.best_performance,
                    "alerts_count": len(result.alerts_generated)
                }
                for result in self.execution_history[-5:]  # 최근 5개
            ]
        }

# 사용 예시
async def main():
    """테스트 함수"""
    trigger_system = AutoBacktestTrigger()

    try:
        # 자동 모니터링 시작
        await trigger_system.start_monitoring()
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다.")
        await trigger_system.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())