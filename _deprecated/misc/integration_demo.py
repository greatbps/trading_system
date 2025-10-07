#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integration_demo.py

동적 설정 조정 및 향상된 시각화 시스템 통합 데모
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Core components
from core.dynamic_settings_manager import DynamicSettingsManager, TradingSettings
from backtesting.enhanced_visualizer import EnhancedVisualizer
from backtesting.backtesting_engine import BacktestingEngine, BacktestResult, PerformanceMetrics
from utils.logger import get_logger

class TradingSystemIntegration:
    """동적 설정 및 향상된 시각화 통합 시스템"""

    def __init__(self, config=None):
        """통합 시스템 초기화"""
        self.logger = get_logger("TradingSystemIntegration")
        self.config = config
        self.console = Console() if RICH_AVAILABLE else None

        # 핵심 컴포넌트 초기화
        self.settings_manager = DynamicSettingsManager(config)
        self.visualizer = EnhancedVisualizer(config)
        self.backtest_engine = BacktestingEngine(config)

        # 데모용 데이터
        self.demo_balance_history = []
        self.demo_backtest_results = []

    async def run_integration_demo(self):
        """통합 시스템 데모 실행"""
        try:
            if self.console:
                self.console.print(Panel.fit(
                    "🚀 AI Trading System - 통합 데모\n"
                    "💰 동적 설정 조정 + 📊 향상된 시각화",
                    style="bold blue"
                ))

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:

                # 1. 초기 설정 표시
                task1 = progress.add_task("초기 설정 로드 중...", total=1)
                await self._demo_initial_settings()
                progress.advance(task1)

                # 2. 잔고 변화 시뮬레이션
                task2 = progress.add_task("잔고 변화 시뮬레이션 중...", total=1)
                await self._demo_balance_changes()
                progress.advance(task2)

                # 3. 백테스팅 실행
                task3 = progress.add_task("백테스팅 실행 중...", total=1)
                await self._demo_backtesting()
                progress.advance(task3)

                # 4. 시각화 생성
                task4 = progress.add_task("향상된 시각화 생성 중...", total=1)
                await self._demo_visualization()
                progress.advance(task4)

                # 5. 실시간 모니터링
                task5 = progress.add_task("실시간 모니터링 시작...", total=1)
                await self._demo_real_time_monitoring()
                progress.advance(task5)

            if self.console:
                self.console.print("[green]✅ 통합 데모 완료![/green]")

        except Exception as e:
            self.logger.error(f"❌ 통합 데모 실행 실패: {e}")
            if self.console:
                self.console.print(f"[red]❌ 데모 실행 실패: {e}[/red]")

    async def _demo_initial_settings(self):
        """초기 설정 데모"""
        try:
            self.logger.info("📋 초기 설정 로드 중...")

            # 현재 설정 가져오기
            current_settings = await self.settings_manager.get_current_settings()

            if self.console:
                # 설정 테이블 생성
                settings_table = Table(title="현재 거래 설정")
                settings_table.add_column("설정 항목", style="cyan")
                settings_table.add_column("값", style="magenta")
                settings_table.add_column("설명", style="dim")

                settings_table.add_row(
                    "포지션 크기 비율",
                    f"{current_settings.position_size_ratio:.1%}",
                    "총 자본 대비 단일 포지션 크기"
                )
                settings_table.add_row(
                    "최대 포지션 수",
                    str(current_settings.max_positions),
                    "동시 보유 가능한 최대 종목 수"
                )
                settings_table.add_row(
                    "손절 비율",
                    f"{current_settings.stop_loss_pct:.1f}%",
                    "손실 제한 비율"
                )
                settings_table.add_row(
                    "익절 비율",
                    f"{current_settings.take_profit_pct:.1f}%",
                    "이익 실현 비율"
                )
                settings_table.add_row(
                    "리스크 레벨",
                    current_settings.risk_level,
                    "전체적인 위험 수준"
                )

                self.console.print(settings_table)

            await asyncio.sleep(2)

        except Exception as e:
            self.logger.error(f"❌ 초기 설정 데모 실패: {e}")

    async def _demo_balance_changes(self):
        """잔고 변화 및 동적 설정 조정 데모"""
        try:
            self.logger.info("💰 잔고 변화 시뮬레이션 시작...")

            # 시뮬레이션 시나리오
            scenarios = [
                {"balance": 5_000_000, "description": "초기 자본 (500만원)"},
                {"balance": 7_500_000, "description": "수익 발생 (750만원)"},
                {"balance": 12_000_000, "description": "큰 수익 (1200만원)"},
                {"balance": 8_000_000, "description": "일부 손실 (800만원)"},
                {"balance": 15_000_000, "description": "회복 및 성장 (1500만원)"}
            ]

            for i, scenario in enumerate(scenarios):
                total_balance = scenario["balance"]
                cash_balance = total_balance * 0.3  # 30% 현금
                stock_value = total_balance * 0.7   # 70% 주식

                # 설정 업데이트
                new_settings, adjustment_info = await self.settings_manager.update_balance_and_adjust_settings(
                    current_balance=total_balance,
                    cash_balance=cash_balance,
                    stock_value=stock_value
                )

                # 결과 출력
                if self.console:
                    self.console.print(f"\n[bold cyan]시나리오 {i+1}: {scenario['description']}[/bold cyan]")

                    # 잔고 정보
                    balance_table = Table(title="잔고 현황")
                    balance_table.add_column("구분", style="cyan")
                    balance_table.add_column("금액", style="magenta")

                    balance_table.add_row("총 자산", f"₩{total_balance:,.0f}")
                    balance_table.add_row("현금", f"₩{cash_balance:,.0f}")
                    balance_table.add_row("주식", f"₩{stock_value:,.0f}")

                    self.console.print(balance_table)

                    # 설정 변경사항
                    if adjustment_info.get("adjustments_made"):
                        changes_table = Table(title="설정 변경사항")
                        changes_table.add_column("설정", style="cyan")
                        changes_table.add_column("이전 값", style="dim")
                        changes_table.add_column("새 값", style="magenta")
                        changes_table.add_column("변화", style="green")

                        for change in adjustment_info["adjustments_made"]:
                            change_icon = "⬆️" if change["change_type"] == "increase" else "⬇️" if change["change_type"] == "decrease" else "🔄"

                            changes_table.add_row(
                                change["setting"],
                                f"{change['old_value']}{change['unit']}",
                                f"{change['new_value']}{change['unit']}",
                                change_icon
                            )

                        self.console.print(changes_table)
                    else:
                        self.console.print("[dim]설정 변경사항 없음[/dim]")

                await asyncio.sleep(3)

        except Exception as e:
            self.logger.error(f"❌ 잔고 변화 데모 실패: {e}")

    async def _demo_backtesting(self):
        """백테스팅 데모"""
        try:
            self.logger.info("📈 백테스팅 실행 중...")

            # 데모용 백테스팅 결과 생성
            demo_strategies = ["모멘텀 전략", "평균회귀 전략", "브레이크아웃 전략"]

            for strategy_name in demo_strategies:
                # 가상의 성과 데이터 생성
                result = await self._create_demo_backtest_result(strategy_name)
                self.demo_backtest_results.append(result)

            if self.console:
                # 백테스팅 결과 요약
                results_table = Table(title="백테스팅 결과 요약")
                results_table.add_column("전략", style="cyan")
                results_table.add_column("총 수익률", style="magenta")
                results_table.add_column("연간 수익률", style="magenta")
                results_table.add_column("최대 낙폭", style="red")
                results_table.add_column("샤프 비율", style="green")

                for result in self.demo_backtest_results:
                    results_table.add_row(
                        result.strategy_name,
                        f"{result.total_return_pct:.2f}%",
                        f"{result.metrics.annual_return:.2f}%",
                        f"{result.metrics.max_drawdown:.2f}%",
                        f"{result.metrics.sharpe_ratio:.2f}"
                    )

                self.console.print(results_table)

        except Exception as e:
            self.logger.error(f"❌ 백테스팅 데모 실패: {e}")

    async def _demo_visualization(self):
        """향상된 시각화 데모"""
        try:
            self.logger.info("📊 향상된 시각화 생성 중...")

            if not self.demo_backtest_results:
                await self._demo_backtesting()

            # 인터랙티브 대시보드 생성
            dashboard_path = await self.visualizer.create_interactive_dashboard(
                self.demo_backtest_results,
                live_mode=True
            )

            if self.console:
                self.console.print(f"[green]✅ 인터랙티브 대시보드 생성: {dashboard_path}[/green]")

            # 전략 비교 히트맵 (데모용 비교 결과 생성)
            # comparison_results = await self._create_demo_comparison_results()
            # heatmap_path = await self.visualizer.create_strategy_comparison_heatmap(comparison_results)

            # if heatmap_path and self.console:
            #     self.console.print(f"[green]✅ 전략 비교 히트맵 생성: {heatmap_path}[/green]")

        except Exception as e:
            self.logger.error(f"❌ 시각화 데모 실패: {e}")

    async def _demo_real_time_monitoring(self):
        """실시간 모니터링 데모"""
        try:
            self.logger.info("📡 실시간 모니터링 시작...")

            if not self.console:
                return

            # 실시간 모니터링 레이아웃
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main", ratio=1)
            )

            layout["main"].split_row(
                Layout(name="left"),
                Layout(name="right")
            )

            # 5초간 실시간 모니터링 시뮬레이션
            for i in range(5):
                # 헤더
                layout["header"].update(
                    Panel(
                        f"🤖 AI Trading System - 실시간 모니터링\n"
                        f"업데이트: {datetime.now().strftime('%H:%M:%S')} | 주기: {i+1}/5",
                        style="bold blue"
                    )
                )

                # 포트폴리오 현황
                portfolio_table = Table(title="포트폴리오 현황")
                portfolio_table.add_column("항목", style="cyan")
                portfolio_table.add_column("값", style="magenta")

                current_balance = 15_000_000 + i * 100_000  # 점진적 증가
                portfolio_table.add_row("총 자산", f"₩{current_balance:,.0f}")
                portfolio_table.add_row("일일 수익", f"+{2.5 + i * 0.1:.1f}%")
                portfolio_table.add_row("활성 전략", "3개")

                layout["left"].update(portfolio_table)

                # 현재 설정
                settings = await self.settings_manager.get_current_settings()
                settings_table = Table(title="현재 설정")
                settings_table.add_column("설정", style="cyan")
                settings_table.add_column("값", style="magenta")

                settings_table.add_row("리스크 레벨", settings.risk_level)
                settings_table.add_row("포지션 크기", f"{settings.position_size_ratio:.1%}")
                settings_table.add_row("최대 포지션", f"{settings.max_positions}개")

                layout["right"].update(settings_table)

                # 화면 출력
                self.console.print(layout)
                await asyncio.sleep(1)
                self.console.clear()

        except Exception as e:
            self.logger.error(f"❌ 실시간 모니터링 데모 실패: {e}")

    async def _create_demo_backtest_result(self, strategy_name: str) -> BacktestResult:
        """데모용 백테스팅 결과 생성"""
        import random

        # 가상의 수익률 곡선 생성
        initial_capital = 10_000_000
        days = 60
        equity_curve = []

        current_value = initial_capital
        for day in range(days):
            date = datetime.now() - timedelta(days=days-day)
            daily_return = random.uniform(-0.03, 0.05)  # -3% ~ +5%
            current_value *= (1 + daily_return)

            equity_curve.append({
                "date": date,
                "portfolio_value": current_value
            })

        # 성과 지표 계산
        total_return_pct = (current_value - initial_capital) / initial_capital * 100
        annual_return = total_return_pct * (365 / days)
        volatility = random.uniform(15, 25)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        max_drawdown = random.uniform(5, 15)

        metrics = PerformanceMetrics(
            total_return=total_return_pct,
            annual_return=annual_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=random.uniform(55, 75),
            profit_factor=random.uniform(1.2, 2.0),
            total_trades=random.randint(20, 50)
        )

        return BacktestResult(
            strategy_name=strategy_name,
            initial_capital=initial_capital,
            final_capital=current_value,
            total_return_pct=total_return_pct,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=[]  # 간소화
        )

# 메인 실행 함수
async def main():
    """메인 함수"""
    try:
        # 통합 시스템 초기화
        integration = TradingSystemIntegration()

        # 데모 실행
        await integration.run_integration_demo()

    except KeyboardInterrupt:
        print("\n👋 사용자가 중단했습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 이벤트 루프 실행
    asyncio.run(main())