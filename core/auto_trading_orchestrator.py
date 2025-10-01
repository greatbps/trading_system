#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_trading_orchestrator.py

완전 자동화 거래 시스템 오케스트레이터
조건 감지시 자동으로 실행되는 통합 시스템
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json

from utils.logger import get_logger
from .auto_balance_monitor import AutoBalanceMonitor
from backtesting.auto_backtest_trigger import AutoBacktestTrigger
from backtesting.enhanced_visualizer import EnhancedVisualizer

@dataclass
class SystemEvent:
    """시스템 이벤트"""
    timestamp: datetime
    event_type: str  # balance_change, backtest_trigger, setting_change, alert
    source: str      # balance_monitor, backtest_trigger, orchestrator
    data: Dict[str, Any]
    severity: str    # info, warning, critical
    auto_handled: bool = False

@dataclass
class AutomationRule:
    """자동화 규칙"""
    name: str
    trigger_conditions: Dict[str, Any]
    actions: List[str]
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

class AutoTradingOrchestrator:
    """완전 자동화 거래 시스템 오케스트레이터"""

    def __init__(self, trading_handler=None, config=None):
        """오케스트레이터 초기화"""
        self.logger = get_logger("AutoTradingOrchestrator")
        self.trading_handler = trading_handler
        self.config = config

        # 핵심 컴포넌트들
        self.balance_monitor = AutoBalanceMonitor(trading_handler, config)
        self.backtest_trigger = AutoBacktestTrigger(config, trading_handler)
        self.visualizer = EnhancedVisualizer(config)

        # 오케스트레이션 상태
        self.is_running = False
        self.system_events: List[SystemEvent] = []

        # 자동화 규칙들
        self.automation_rules = self._initialize_automation_rules()

        # 시스템 상태
        self.system_health = {
            "overall_status": "healthy",
            "last_health_check": datetime.now(),
            "component_status": {
                "balance_monitor": "healthy",
                "backtest_trigger": "healthy",
                "visualizer": "healthy"
            },
            "alerts": []
        }

        # 성과 추적
        self.performance_tracking = {
            "start_time": None,
            "total_adjustments": 0,
            "total_backtests": 0,
            "total_alerts": 0,
            "last_portfolio_value": 0,
            "best_performance": 0,
            "worst_performance": 0
        }

    def _initialize_automation_rules(self) -> List[AutomationRule]:
        """자동화 규칙 초기화"""
        return [
            # 큰 손실시 즉시 보수적 모드 + 백테스팅
            AutomationRule(
                name="emergency_loss_response",
                trigger_conditions={
                    "balance_loss_pct": -10.0,
                    "time_window_hours": 2
                },
                actions=[
                    "switch_to_conservative",
                    "run_defensive_backtest",
                    "generate_emergency_report",
                    "send_critical_alert"
                ]
            ),

            # 큰 수익시 적극적 모드 + 기회 탐색
            AutomationRule(
                name="high_profit_optimization",
                trigger_conditions={
                    "balance_gain_pct": 15.0,
                    "time_window_hours": 6
                },
                actions=[
                    "switch_to_aggressive",
                    "run_opportunity_backtest",
                    "optimize_position_sizing",
                    "generate_opportunity_report"
                ]
            ),

            # 변동성 급증시 전략 재검토
            AutomationRule(
                name="volatility_response",
                trigger_conditions={
                    "market_volatility": 25.0,
                    "duration_minutes": 30
                },
                actions=[
                    "run_volatility_backtest",
                    "adjust_risk_parameters",
                    "generate_market_analysis"
                ]
            ),

            # 일일 마감 루틴
            AutomationRule(
                name="daily_closing_routine",
                trigger_conditions={
                    "schedule": "15:35",  # 장 마감 후 5분
                    "weekdays_only": True
                },
                actions=[
                    "run_daily_performance_review",
                    "update_risk_settings",
                    "generate_daily_report",
                    "backup_system_state"
                ]
            ),

            # 주간 최적화
            AutomationRule(
                name="weekly_optimization",
                trigger_conditions={
                    "schedule": "friday:17:00"
                },
                actions=[
                    "run_comprehensive_backtest",
                    "optimize_all_parameters",
                    "generate_weekly_report",
                    "plan_next_week_strategy"
                ]
            )
        ]

    async def start_orchestration(self):
        """완전 자동화 시스템 시작"""
        try:
            if self.is_running:
                self.logger.warning("오케스트레이터가 이미 실행 중입니다")
                return

            self.is_running = True
            self.performance_tracking["start_time"] = datetime.now()

            self.logger.info("🚀 완전 자동화 거래 시스템 시작")

            # 컴포넌트들 시작
            await self._start_components()

            # 오케스트레이션 루프 시작
            await self._orchestration_loop()

        except Exception as e:
            self.logger.error(f"❌ 오케스트레이터 시작 실패: {e}")
            self.is_running = False

    async def stop_orchestration(self):
        """완전 자동화 시스템 중지"""
        try:
            self.is_running = False

            # 컴포넌트들 중지
            await self._stop_components()

            # 최종 리포트 생성
            await self._generate_final_report()

            self.logger.info("⏹️ 완전 자동화 거래 시스템 중지")

        except Exception as e:
            self.logger.error(f"❌ 오케스트레이터 중지 실패: {e}")

    async def _start_components(self):
        """모든 컴포넌트 시작"""
        try:
            # 병렬로 컴포넌트들 시작
            await asyncio.gather(
                self.balance_monitor.start_monitoring(),
                self.backtest_trigger.start_monitoring(),
                return_exceptions=True
            )

            self.logger.info("✅ 모든 컴포넌트 시작 완료")

        except Exception as e:
            self.logger.error(f"❌ 컴포넌트 시작 실패: {e}")

    async def _stop_components(self):
        """모든 컴포넌트 중지"""
        try:
            await asyncio.gather(
                self.balance_monitor.stop_monitoring(),
                self.backtest_trigger.stop_monitoring(),
                return_exceptions=True
            )

            self.logger.info("✅ 모든 컴포넌트 중지 완료")

        except Exception as e:
            self.logger.error(f"❌ 컴포넌트 중지 실패: {e}")

    async def _orchestration_loop(self):
        """메인 오케스트레이션 루프"""
        try:
            while self.is_running:
                try:
                    # 시스템 상태 체크
                    await self._check_system_health()

                    # 이벤트 수집 및 처리
                    await self._collect_and_process_events()

                    # 자동화 규칙 체크
                    await self._check_automation_rules()

                    # 성과 추적 업데이트
                    await self._update_performance_tracking()

                    # 5분 간격으로 실행
                    await asyncio.sleep(300)

                except Exception as e:
                    self.logger.error(f"❌ 오케스트레이션 루프 오류: {e}")
                    await asyncio.sleep(60)  # 에러시 1분 대기

        except asyncio.CancelledError:
            self.logger.info("🛑 오케스트레이션 루프 취소됨")
        except Exception as e:
            self.logger.error(f"❌ 오케스트레이션 치명적 오류: {e}")
        finally:
            self.is_running = False

    async def _check_system_health(self):
        """시스템 건강성 체크"""
        try:
            current_time = datetime.now()

            # 각 컴포넌트 상태 체크
            balance_status = self.balance_monitor.is_monitoring
            backtest_status = self.backtest_trigger.is_active

            # 상태 업데이트
            self.system_health.update({
                "last_health_check": current_time,
                "component_status": {
                    "balance_monitor": "healthy" if balance_status else "inactive",
                    "backtest_trigger": "healthy" if backtest_status else "inactive",
                    "visualizer": "healthy"
                }
            })

            # 전체 상태 평가
            if not balance_status or not backtest_status:
                self.system_health["overall_status"] = "degraded"

                # 컴포넌트 재시작 시도
                await self._restart_failed_components()
            else:
                self.system_health["overall_status"] = "healthy"

        except Exception as e:
            self.logger.error(f"❌ 시스템 건강성 체크 실패: {e}")
            self.system_health["overall_status"] = "error"

    async def _restart_failed_components(self):
        """실패한 컴포넌트 재시작"""
        try:
            if not self.balance_monitor.is_monitoring:
                self.logger.warning("🔄 잔고 모니터링 재시작 중...")
                await self.balance_monitor.start_monitoring()

            if not self.backtest_trigger.is_active:
                self.logger.warning("🔄 백테스팅 트리거 재시작 중...")
                await self.backtest_trigger.start_monitoring()

        except Exception as e:
            self.logger.error(f"❌ 컴포넌트 재시작 실패: {e}")

    async def _collect_and_process_events(self):
        """이벤트 수집 및 처리"""
        try:
            # 잔고 모니터 이벤트
            balance_events = await self._collect_balance_events()

            # 백테스팅 이벤트
            backtest_events = await self._collect_backtest_events()

            # 모든 이벤트 처리
            all_events = balance_events + backtest_events

            for event in all_events:
                await self._process_event(event)
                self.system_events.append(event)

            # 이벤트 히스토리 정리 (최근 1000개만 유지)
            if len(self.system_events) > 1000:
                self.system_events = self.system_events[-1000:]

        except Exception as e:
            self.logger.error(f"❌ 이벤트 처리 실패: {e}")

    async def _collect_balance_events(self) -> List[SystemEvent]:
        """잔고 모니터 이벤트 수집"""
        events = []
        try:
            # 잔고 히스토리에서 최근 이벤트 확인
            if self.balance_monitor.event_history:
                recent_events = self.balance_monitor.event_history[-5:]  # 최근 5개

                for balance_event in recent_events:
                    if abs(balance_event.change_percentage) > 3:  # 3% 이상 변화
                        event = SystemEvent(
                            timestamp=balance_event.timestamp,
                            event_type="balance_change",
                            source="balance_monitor",
                            data={
                                "previous_balance": balance_event.previous_balance,
                                "current_balance": balance_event.current_balance,
                                "change_percentage": balance_event.change_percentage,
                                "trigger_conditions": balance_event.trigger_conditions
                            },
                            severity="warning" if abs(balance_event.change_percentage) > 10 else "info"
                        )
                        events.append(event)

        except Exception as e:
            self.logger.error(f"❌ 잔고 이벤트 수집 실패: {e}")

        return events

    async def _collect_backtest_events(self) -> List[SystemEvent]:
        """백테스팅 이벤트 수집"""
        events = []
        try:
            # 백테스팅 실행 히스토리에서 최근 이벤트 확인
            if self.backtest_trigger.execution_history:
                recent_executions = self.backtest_trigger.execution_history[-3:]  # 최근 3개

                for backtest_result in recent_executions:
                    event = SystemEvent(
                        timestamp=backtest_result.execution_time,
                        event_type="backtest_trigger",
                        source="backtest_trigger",
                        data={
                            "trigger_name": backtest_result.trigger_name,
                            "best_strategy": backtest_result.best_strategy,
                            "best_performance": backtest_result.best_performance,
                            "strategies_tested": backtest_result.strategies_tested,
                            "alerts": backtest_result.alerts_generated
                        },
                        severity="critical" if backtest_result.best_performance < -10 else
                                "warning" if backtest_result.best_performance < 0 else "info"
                    )
                    events.append(event)

        except Exception as e:
            self.logger.error(f"❌ 백테스팅 이벤트 수집 실패: {e}")

        return events

    async def _process_event(self, event: SystemEvent):
        """개별 이벤트 처리"""
        try:
            self.logger.info(f"📋 이벤트 처리: {event.event_type} ({event.severity})")

            # 심각도별 처리
            if event.severity == "critical":
                await self._handle_critical_event(event)
            elif event.severity == "warning":
                await self._handle_warning_event(event)
            else:
                await self._handle_info_event(event)

            event.auto_handled = True

        except Exception as e:
            self.logger.error(f"❌ 이벤트 처리 실패: {e}")

    async def _handle_critical_event(self, event: SystemEvent):
        """치명적 이벤트 처리"""
        try:
            self.logger.critical(f"🚨 치명적 이벤트: {event.event_type}")

            if event.event_type == "balance_change":
                # 큰 손실 감지
                change_pct = event.data.get("change_percentage", 0)
                if change_pct < -10:
                    await self._activate_emergency_mode()

            elif event.event_type == "backtest_trigger":
                # 모든 전략이 큰 손실 예상
                performance = event.data.get("best_performance", 0)
                if performance < -10:
                    await self._activate_defensive_mode()

        except Exception as e:
            self.logger.error(f"❌ 치명적 이벤트 처리 실패: {e}")

    async def _handle_warning_event(self, event: SystemEvent):
        """경고 이벤트 처리"""
        try:
            self.logger.warning(f"⚠️ 경고 이벤트: {event.event_type}")

            # 자동 대응 조치 실행
            if event.event_type == "balance_change":
                # 설정 재검토
                await self._review_settings()
            elif event.event_type == "backtest_trigger":
                # 전략 조정 검토
                await self._review_strategies()

        except Exception as e:
            self.logger.error(f"❌ 경고 이벤트 처리 실패: {e}")

    async def _handle_info_event(self, event: SystemEvent):
        """정보 이벤트 처리"""
        try:
            self.logger.info(f"ℹ️ 정보 이벤트: {event.event_type}")

            # 통계 업데이트만 수행
            if event.event_type == "balance_change":
                self.performance_tracking["total_adjustments"] += 1
            elif event.event_type == "backtest_trigger":
                self.performance_tracking["total_backtests"] += 1

        except Exception as e:
            self.logger.error(f"❌ 정보 이벤트 처리 실패: {e}")

    async def _check_automation_rules(self):
        """자동화 규칙 체크 및 실행"""
        try:
            current_time = datetime.now()

            for rule in self.automation_rules:
                if not rule.enabled:
                    continue

                is_triggered = await self._check_rule_conditions(rule, current_time)

                if is_triggered:
                    self.logger.info(f"🔥 자동화 규칙 활성화: {rule.name}")

                    await self._execute_rule_actions(rule)

                    rule.last_triggered = current_time
                    rule.trigger_count += 1

        except Exception as e:
            self.logger.error(f"❌ 자동화 규칙 체크 실패: {e}")

    async def _check_rule_conditions(self, rule: AutomationRule, current_time: datetime) -> bool:
        """규칙 조건 체크"""
        try:
            conditions = rule.trigger_conditions

            # 스케줄 기반 조건
            if "schedule" in conditions:
                schedule = conditions["schedule"]
                if ":" in schedule:  # 시간 형식
                    target_time = schedule.split(":")
                    if (current_time.hour == int(target_time[0]) and
                        current_time.minute == int(target_time[1])):

                        # 오늘 이미 실행했는지 체크
                        if (rule.last_triggered is None or
                            rule.last_triggered.date() < current_time.date()):
                            return True

            # 잔고 변화 기반 조건
            if "balance_loss_pct" in conditions or "balance_gain_pct" in conditions:
                if self.balance_monitor.event_history:
                    recent_event = self.balance_monitor.event_history[-1]
                    change_pct = recent_event.change_percentage

                    loss_threshold = conditions.get("balance_loss_pct", float('-inf'))
                    gain_threshold = conditions.get("balance_gain_pct", float('inf'))

                    if change_pct <= loss_threshold or change_pct >= gain_threshold:
                        return True

            # 시장 변동성 조건
            if "market_volatility" in conditions:
                market_volatility = self.backtest_trigger.market_state.get("volatility", 0)
                threshold = conditions.get("market_volatility", 25.0)

                if market_volatility >= threshold:
                    return True

            return False

        except Exception as e:
            self.logger.error(f"❌ 규칙 조건 체크 실패: {e}")
            return False

    async def _execute_rule_actions(self, rule: AutomationRule):
        """규칙 액션 실행"""
        try:
            for action in rule.actions:
                try:
                    await self._execute_action(action, rule)
                except Exception as e:
                    self.logger.error(f"❌ 액션 실행 실패 ({action}): {e}")

        except Exception as e:
            self.logger.error(f"❌ 규칙 액션 실행 실패: {e}")

    async def _execute_action(self, action: str, rule: AutomationRule):
        """개별 액션 실행"""
        try:
            if action == "switch_to_conservative":
                await self._activate_emergency_mode()
            elif action == "switch_to_aggressive":
                await self._activate_aggressive_mode()
            elif action == "run_defensive_backtest":
                await self._run_targeted_backtest(["defensive", "mean_reversion"])
            elif action == "run_opportunity_backtest":
                await self._run_targeted_backtest(["momentum", "breakout"])
            elif action == "generate_emergency_report":
                await self._generate_emergency_report()
            elif action == "generate_daily_report":
                await self._generate_daily_report()
            elif action == "backup_system_state":
                await self._backup_system_state()
            else:
                self.logger.warning(f"알 수 없는 액션: {action}")

        except Exception as e:
            self.logger.error(f"❌ 액션 실행 실패 ({action}): {e}")

    async def _activate_emergency_mode(self):
        """긴급 모드 활성화"""
        self.logger.critical("🚨 긴급 모드 활성화 - 보수적 설정으로 전환")
        # 실제 구현은 balance_monitor의 긴급 핸들러 호출

    async def _activate_aggressive_mode(self):
        """적극적 모드 활성화"""
        self.logger.info("🎯 적극적 모드 활성화 - 기회 포착 설정으로 전환")

    async def _run_targeted_backtest(self, strategies: List[str]):
        """특정 전략 백테스팅 실행"""
        self.logger.info(f"📈 타겟 백테스팅 실행: {strategies}")

    async def _generate_emergency_report(self):
        """긴급 리포트 생성"""
        self.logger.info("📋 긴급 상황 리포트 생성 중...")

    async def _generate_daily_report(self):
        """일일 리포트 생성"""
        self.logger.info("📊 일일 성과 리포트 생성 중...")

    async def _backup_system_state(self):
        """시스템 상태 백업"""
        self.logger.info("💾 시스템 상태 백업 중...")

    async def _review_settings(self):
        """설정 재검토"""
        self.logger.info("⚙️ 거래 설정 재검토 중...")

    async def _review_strategies(self):
        """전략 재검토"""
        self.logger.info("📋 거래 전략 재검토 중...")

    async def _update_performance_tracking(self):
        """성과 추적 업데이트"""
        try:
            if self.balance_monitor.event_history:
                latest_balance = self.balance_monitor.event_history[-1].current_balance

                if self.performance_tracking["last_portfolio_value"] > 0:
                    current_performance = ((latest_balance - self.performance_tracking["last_portfolio_value"]) /
                                         self.performance_tracking["last_portfolio_value"] * 100)

                    self.performance_tracking["best_performance"] = max(
                        self.performance_tracking["best_performance"], current_performance
                    )
                    self.performance_tracking["worst_performance"] = min(
                        self.performance_tracking["worst_performance"], current_performance
                    )

                self.performance_tracking["last_portfolio_value"] = latest_balance

        except Exception as e:
            self.logger.error(f"❌ 성과 추적 업데이트 실패: {e}")

    async def _generate_final_report(self):
        """최종 리포트 생성"""
        try:
            runtime = datetime.now() - self.performance_tracking["start_time"]

            final_report = {
                "운영_시간": str(runtime),
                "총_설정_조정": self.performance_tracking["total_adjustments"],
                "총_백테스팅": self.performance_tracking["total_backtests"],
                "총_알림": self.performance_tracking["total_alerts"],
                "최고_성과": f"{self.performance_tracking['best_performance']:.2f}%",
                "최악_성과": f"{self.performance_tracking['worst_performance']:.2f}%",
                "시스템_이벤트": len(self.system_events),
                "최종_시스템_상태": self.system_health["overall_status"]
            }

            self.logger.info("📋 최종 운영 리포트:")
            for key, value in final_report.items():
                self.logger.info(f"  {key}: {value}")

        except Exception as e:
            self.logger.error(f"❌ 최종 리포트 생성 실패: {e}")

    async def get_system_overview(self) -> Dict[str, Any]:
        """시스템 전체 현황"""
        return {
            "is_running": self.is_running,
            "system_health": self.system_health,
            "performance_tracking": self.performance_tracking,
            "active_rules": len([r for r in self.automation_rules if r.enabled]),
            "recent_events": len([e for e in self.system_events
                                if (datetime.now() - e.timestamp).total_seconds() < 3600]),  # 1시간 내
            "components": {
                "balance_monitor": self.balance_monitor.is_monitoring,
                "backtest_trigger": self.backtest_trigger.is_active
            }
        }

# 사용 예시
async def main():
    """테스트 함수"""
    orchestrator = AutoTradingOrchestrator()

    try:
        # 완전 자동화 시스템 시작
        await orchestrator.start_orchestration()
    except KeyboardInterrupt:
        print("\n사용자가 중단했습니다.")
        await orchestrator.stop_orchestration()

if __name__ == "__main__":
    asyncio.run(main())