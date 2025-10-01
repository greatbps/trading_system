#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integrated_dashboard.py

통합 실시간 모니터링 대시보드 - 모든 시스템 상태를 한눈에
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import time
import signal
import sys

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich.columns import Columns
    from rich.rule import Rule
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from utils.logger import get_logger
from core.dynamic_settings_manager import DynamicSettingsManager
from utils.enhanced_market_schedule_manager import EnhancedMarketScheduleManager

@dataclass
class DashboardMetrics:
    """대시보드 통합 지표"""
    # 포트폴리오
    total_balance: float = 0.0
    cash_balance: float = 0.0
    stock_value: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    active_positions: int = 0

    # 거래
    trades_today: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0

    # 시장
    market_status: str = "UNKNOWN"
    trading_permission: str = "NO_ACTIVITY"
    next_market_change: str = ""

    # 시스템
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    api_calls: int = 0
    api_errors: int = 0
    uptime: str = "00:00:00"

    # AI/전략
    ai_accuracy: float = 0.0
    active_strategies: int = 0
    strategy_performance: Dict[str, float] = field(default_factory=dict)

    # 리스크
    risk_level: str = "MEDIUM"
    position_size_ratio: float = 0.1
    max_positions: int = 5
    stop_loss_pct: float = 3.0

class IntegratedDashboard:
    """통합 실시간 모니터링 대시보드"""

    def __init__(self, config=None, data_dir: str = "data"):
        """대시보드 초기화"""
        self.logger = get_logger("IntegratedDashboard")
        self.console = Console() if RICH_AVAILABLE else None

        self.config = config
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # 핵심 컴포넌트
        self.settings_manager = DynamicSettingsManager(config, str(self.data_dir))
        self.market_manager = EnhancedMarketScheduleManager(config, str(self.data_dir))

        # 대시보드 데이터
        self.current_metrics = DashboardMetrics()
        self.metrics_history: List[DashboardMetrics] = []

        # 모니터링 설정
        self.update_interval = 3  # 3초
        self.monitoring_active = False
        self.monitoring_task = None

        # 시작 시간
        self.start_time = datetime.now()

        # 상태 캐시
        self.last_update = None
        self.update_counter = 0

    async def initialize(self):
        """대시보드 초기화"""
        try:
            self.logger.info("🚀 통합 대시보드 초기화 중...")

            # 핵심 컴포넌트 초기화
            await self.settings_manager._load_settings()
            await self.market_manager.initialize()

            # 초기 메트릭 로드
            await self._update_all_metrics()

            if self.console:
                self.console.print(Panel.fit(
                    "🚀 AI Trading System - 통합 모니터링 대시보드\n"
                    "모든 시스템 상태를 실시간으로 모니터링합니다.",
                    style="bold blue"
                ))

            self.logger.info("✅ 통합 대시보드 초기화 완료")

        except Exception as e:
            self.logger.error(f"❌ 대시보드 초기화 실패: {e}")
            raise

    async def start_monitoring(self):
        """통합 모니터링 시작"""
        try:
            if self.monitoring_active:
                self.logger.warning("⚠️ 이미 모니터링이 진행 중입니다")
                return

            self.monitoring_active = True
            self.logger.info("📡 통합 모니터링 시작")

            if not RICH_AVAILABLE:
                await self._simple_monitoring()
                return

            # Rich Live 대시보드
            layout = self._create_main_layout()

            with Live(layout, refresh_per_second=1, screen=True) as live:
                while self.monitoring_active:
                    try:
                        # 모든 메트릭 업데이트
                        await self._update_all_metrics()

                        # 레이아웃 업데이트
                        self._update_main_layout(layout)

                        # 카운터 증가
                        self.update_counter += 1

                        # 잠시 대기
                        await asyncio.sleep(self.update_interval)

                    except KeyboardInterrupt:
                        self.logger.info("👋 사용자가 모니터링을 중단했습니다")
                        break
                    except Exception as e:
                        self.logger.error(f"❌ 대시보드 업데이트 오류: {e}")
                        await asyncio.sleep(self.update_interval)

        except Exception as e:
            self.logger.error(f"❌ 통합 모니터링 실행 실패: {e}")
        finally:
            self.monitoring_active = False

    def _create_main_layout(self) -> Layout:
        """메인 레이아웃 생성"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="center", ratio=1),
            Layout(name="right", ratio=1)
        )

        layout["left"].split_column(
            Layout(name="portfolio", ratio=1),
            Layout(name="trading", ratio=1)
        )

        layout["center"].split_column(
            Layout(name="market", ratio=1),
            Layout(name="strategies", ratio=1)
        )

        layout["right"].split_column(
            Layout(name="system", ratio=1),
            Layout(name="risk", ratio=1)
        )

        return layout

    def _update_main_layout(self, layout: Layout):
        """메인 레이아웃 업데이트"""
        try:
            # 헤더
            layout["header"].update(self._create_header_panel())

            # 포트폴리오
            layout["portfolio"].update(self._create_portfolio_panel())

            # 거래 현황
            layout["trading"].update(self._create_trading_panel())

            # 시장 상태
            layout["market"].update(self._create_market_panel())

            # 전략 현황
            layout["strategies"].update(self._create_strategies_panel())

            # 시스템 상태
            layout["system"].update(self._create_system_panel())

            # 리스크 관리
            layout["risk"].update(self._create_risk_panel())

            # 푸터
            layout["footer"].update(self._create_footer_panel())

        except Exception as e:
            self.logger.error(f"❌ 레이아웃 업데이트 실패: {e}")

    def _create_header_panel(self) -> Panel:
        """헤더 패널 생성"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            uptime = self._get_uptime()

            # 시장 상태에 따른 색상
            market_color = "green" if self.current_metrics.market_status == "OPEN" else "red"
            market_text = f"[{market_color}]{self.current_metrics.market_status}[/{market_color}]"

            # 수익률에 따른 색상
            pnl_color = "green" if self.current_metrics.daily_pnl >= 0 else "red"
            pnl_text = f"[{pnl_color}]{self.current_metrics.daily_pnl_pct:+.2f}%[/{pnl_color}]"

            header_content = Text()
            header_content.append("🤖 AI Trading System - 통합 모니터링 대시보드\n", style="bold cyan")
            header_content.append(f"📅 {current_time} | ⏰ 가동시간: {uptime} | ", style="dim")
            header_content.append(f"🏪 시장: {market_text} | ", style="")
            header_content.append(f"💰 일일수익: {pnl_text} | ", style="")
            header_content.append(f"🔄 업데이트: #{self.update_counter}", style="dim")

            return Panel(
                Align.center(header_content),
                style="blue"
            )

        except Exception as e:
            return Panel(f"헤더 오류: {e}", style="red")

    def _create_portfolio_panel(self) -> Panel:
        """포트폴리오 패널 생성"""
        try:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("항목", style="cyan", width=10)
            table.add_column("값", style="bold", width=12)
            table.add_column("비율", style="dim", width=8)

            # 총 자산
            table.add_row(
                "💰 총자산",
                f"₩{self.current_metrics.total_balance:,.0f}",
                ""
            )

            # 현금
            cash_ratio = self.current_metrics.cash_balance / self.current_metrics.total_balance * 100 if self.current_metrics.total_balance > 0 else 0
            table.add_row(
                "💵 현금",
                f"₩{self.current_metrics.cash_balance:,.0f}",
                f"({cash_ratio:.1f}%)"
            )

            # 주식
            stock_ratio = self.current_metrics.stock_value / self.current_metrics.total_balance * 100 if self.current_metrics.total_balance > 0 else 0
            table.add_row(
                "📈 주식",
                f"₩{self.current_metrics.stock_value:,.0f}",
                f"({stock_ratio:.1f}%)"
            )

            # 일일 손익
            pnl_color = "green" if self.current_metrics.daily_pnl >= 0 else "red"
            table.add_row(
                "📊 일일손익",
                f"[{pnl_color}]₩{self.current_metrics.daily_pnl:,.0f}[/{pnl_color}]",
                f"[{pnl_color}]{self.current_metrics.daily_pnl_pct:+.2f}%[/{pnl_color}]"
            )

            # 총 손익
            total_pnl_color = "green" if self.current_metrics.total_pnl >= 0 else "red"
            table.add_row(
                "💯 총손익",
                f"[{total_pnl_color}]₩{self.current_metrics.total_pnl:,.0f}[/{total_pnl_color}]",
                f"[{total_pnl_color}]{self.current_metrics.total_pnl_pct:+.2f}%[/{total_pnl_color}]"
            )

            # 보유 종목
            table.add_row(
                "🏢 보유종목",
                f"{self.current_metrics.active_positions}개",
                ""
            )

            return Panel(table, title="💼 포트폴리오", border_style="green")

        except Exception as e:
            return Panel(f"포트폴리오 오류: {e}", title="💼 포트폴리오", border_style="red")

    def _create_trading_panel(self) -> Panel:
        """거래 현황 패널 생성"""
        try:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("항목", style="cyan", width=10)
            table.add_column("값", style="bold", width=12)
            table.add_column("상태", style="", width=8)

            # 오늘 거래
            table.add_row("📋 총거래", f"{self.current_metrics.trades_today}건", "")

            # 성공 거래
            success_color = "green" if self.current_metrics.successful_trades > 0 else "dim"
            table.add_row(
                "✅ 성공",
                f"{self.current_metrics.successful_trades}건",
                f"[{success_color}]●[/{success_color}]"
            )

            # 실패 거래
            fail_color = "red" if self.current_metrics.failed_trades > 0 else "dim"
            table.add_row(
                "❌ 실패",
                f"{self.current_metrics.failed_trades}건",
                f"[{fail_color}]●[/{fail_color}]"
            )

            # 승률
            win_rate_color = "green" if self.current_metrics.win_rate >= 60 else "yellow" if self.current_metrics.win_rate >= 40 else "red"
            table.add_row(
                "🎯 승률",
                f"[{win_rate_color}]{self.current_metrics.win_rate:.1f}%[/{win_rate_color}]",
                ""
            )

            # 평균 수익
            table.add_row(
                "📈 평균수익",
                f"₩{self.current_metrics.avg_profit:,.0f}",
                "[green]●[/]"
            )

            # 평균 손실
            table.add_row(
                "📉 평균손실",
                f"₩{self.current_metrics.avg_loss:,.0f}",
                "[red]●[/]"
            )

            return Panel(table, title="💹 거래현황", border_style="yellow")

        except Exception as e:
            return Panel(f"거래현황 오류: {e}", title="💹 거래현황", border_style="red")

    def _create_market_panel(self) -> Panel:
        """시장 상태 패널 생성"""
        try:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("항목", style="cyan", width=10)
            table.add_column("상태", style="bold", width=15)

            # 시장 상태
            status_color = "green" if self.current_metrics.market_status == "OPEN" else "red"
            table.add_row(
                "🏪 시장",
                f"[{status_color}]{self.current_metrics.market_status}[/{status_color}]"
            )

            # 거래 권한
            perm_color = "green" if "FULL" in self.current_metrics.trading_permission else "yellow"
            perm_short = self.current_metrics.trading_permission.replace("_", " ")
            table.add_row(
                "🔑 권한",
                f"[{perm_color}]{perm_short}[/{perm_color}]"
            )

            # 다음 변경
            table.add_row(
                "⏰ 다음변경",
                self.current_metrics.next_market_change[:20] if self.current_metrics.next_market_change else "정보없음"
            )

            # API 상태
            api_color = "green" if self.current_metrics.api_errors == 0 else "red"
            table.add_row(
                "🔌 API호출",
                f"{self.current_metrics.api_calls}건"
            )

            table.add_row(
                "⚠️ API오류",
                f"[{api_color}]{self.current_metrics.api_errors}건[/{api_color}]"
            )

            return Panel(table, title="🏛️ 시장상태", border_style="blue")

        except Exception as e:
            return Panel(f"시장상태 오류: {e}", title="🏛️ 시장상태", border_style="red")

    def _create_strategies_panel(self) -> Panel:
        """전략 현황 패널 생성"""
        try:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("항목", style="cyan", width=10)
            table.add_column("값", style="bold", width=15)

            # 활성 전략
            table.add_row("🧠 활성전략", f"{self.current_metrics.active_strategies}개")

            # AI 정확도
            ai_color = "green" if self.current_metrics.ai_accuracy >= 70 else "yellow" if self.current_metrics.ai_accuracy >= 50 else "red"
            table.add_row(
                "🤖 AI정확도",
                f"[{ai_color}]{self.current_metrics.ai_accuracy:.1f}%[/{ai_color}]"
            )

            # 전략별 성과 (상위 3개)
            if self.current_metrics.strategy_performance:
                sorted_strategies = sorted(
                    self.current_metrics.strategy_performance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )

                table.add_row("", "")  # 구분선
                table.add_row("📊 전략성과", "")

                for i, (strategy, performance) in enumerate(sorted_strategies[:3]):
                    perf_color = "green" if performance >= 0 else "red"
                    strategy_short = strategy[:8] + "..." if len(strategy) > 8 else strategy
                    table.add_row(
                        f"#{i+1} {strategy_short}",
                        f"[{perf_color}]{performance:+.1f}%[/{perf_color}]"
                    )

            return Panel(table, title="🚀 AI전략", border_style="magenta")

        except Exception as e:
            return Panel(f"전략현황 오류: {e}", title="🚀 AI전략", border_style="red")

    def _create_system_panel(self) -> Panel:
        """시스템 상태 패널 생성"""
        try:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("항목", style="cyan", width=10)
            table.add_column("값", style="bold", width=10)
            table.add_column("상태", width=5)

            # CPU 사용률
            cpu_color = "red" if self.current_metrics.cpu_usage > 80 else "yellow" if self.current_metrics.cpu_usage > 60 else "green"
            table.add_row(
                "🖥️ CPU",
                f"{self.current_metrics.cpu_usage:.1f}%",
                f"[{cpu_color}]●[/{cpu_color}]"
            )

            # 메모리 사용률
            mem_color = "red" if self.current_metrics.memory_usage > 80 else "yellow" if self.current_metrics.memory_usage > 60 else "green"
            table.add_row(
                "💾 메모리",
                f"{self.current_metrics.memory_usage:.1f}%",
                f"[{mem_color}]●[/{mem_color}]"
            )

            # 가동시간
            table.add_row(
                "⏰ 가동시간",
                self.current_metrics.uptime,
                "[blue]●[/]"
            )

            # 현재 시간
            current_time = datetime.now().strftime("%H:%M:%S")
            table.add_row(
                "🕒 현재시간",
                current_time,
                "[white]●[/]"
            )

            return Panel(table, title="⚙️ 시스템", border_style="cyan")

        except Exception as e:
            return Panel(f"시스템 오류: {e}", title="⚙️ 시스템", border_style="red")

    def _create_risk_panel(self) -> Panel:
        """리스크 관리 패널 생성"""
        try:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("항목", style="cyan", width=10)
            table.add_column("값", style="bold", width=15)

            # 리스크 레벨
            risk_color = "red" if self.current_metrics.risk_level == "HIGH" else "yellow" if self.current_metrics.risk_level == "MEDIUM" else "green"
            table.add_row(
                "⚠️ 리스크",
                f"[{risk_color}]{self.current_metrics.risk_level}[/{risk_color}]"
            )

            # 포지션 크기
            table.add_row(
                "📊 포지션크기",
                f"{self.current_metrics.position_size_ratio:.1%}"
            )

            # 최대 포지션
            table.add_row(
                "🔢 최대포지션",
                f"{self.current_metrics.max_positions}개"
            )

            # 손절 비율
            table.add_row(
                "🛑 손절비율",
                f"{self.current_metrics.stop_loss_pct:.1f}%"
            )

            # 현재 활용률
            if self.current_metrics.max_positions > 0:
                utilization = (self.current_metrics.active_positions / self.current_metrics.max_positions) * 100
                util_color = "red" if utilization > 90 else "yellow" if utilization > 70 else "green"
                table.add_row(
                    "📈 활용률",
                    f"[{util_color}]{utilization:.1f}%[/{util_color}]"
                )

            return Panel(table, title="🛡️ 리스크관리", border_style="orange")

        except Exception as e:
            return Panel(f"리스크관리 오류: {e}", title="🛡️ 리스크관리", border_style="red")

    def _create_footer_panel(self) -> Panel:
        """푸터 패널 생성"""
        try:
            # 간단한 성과 차트 (ASCII)
            chart_text = "최근 성과 추이: "

            if len(self.metrics_history) >= 10:
                recent_pnl = [m.daily_pnl_pct for m in self.metrics_history[-10:]]
                for pnl in recent_pnl:
                    if pnl > 1:
                        chart_text += "📈"
                    elif pnl < -1:
                        chart_text += "📉"
                    else:
                        chart_text += "➡️"
            else:
                chart_text += "데이터 수집 중..."

            footer_content = Text()
            footer_content.append(chart_text + " | ", style="")
            footer_content.append("💡 Ctrl+C로 종료 | ", style="dim")
            footer_content.append("🔄 자동 업데이트 3초", style="dim")

            return Panel(
                Align.center(footer_content),
                style="dim"
            )

        except Exception as e:
            return Panel(f"푸터 오류: {e}", style="red")

    async def _update_all_metrics(self):
        """모든 메트릭 업데이트"""
        try:
            # 포트폴리오 메트릭
            await self._update_portfolio_metrics()

            # 거래 메트릭
            await self._update_trading_metrics()

            # 시장 메트릭
            await self._update_market_metrics()

            # 시스템 메트릭
            await self._update_system_metrics()

            # AI/전략 메트릭
            await self._update_strategy_metrics()

            # 리스크 메트릭
            await self._update_risk_metrics()

            # 히스토리에 추가
            self.metrics_history.append(DashboardMetrics(**self.current_metrics.__dict__))

            # 히스토리 크기 제한 (최근 100개)
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]

            self.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"❌ 메트릭 업데이트 실패: {e}")

    async def _update_portfolio_metrics(self):
        """포트폴리오 메트릭 업데이트"""
        try:
            # 실제 구현에서는 거래 핸들러에서 데이터 가져오기
            # 데모용 시뮬레이션 데이터
            base_balance = 15_000_000
            fluctuation = 100000 * ((time.time() % 200) - 100) / 100  # -100K ~ +100K

            self.current_metrics.total_balance = base_balance + fluctuation
            self.current_metrics.cash_balance = 3_000_000
            self.current_metrics.stock_value = 12_000_000 + fluctuation
            self.current_metrics.daily_pnl = fluctuation
            self.current_metrics.daily_pnl_pct = (fluctuation / base_balance) * 100
            self.current_metrics.total_pnl = 500_000 + fluctuation
            self.current_metrics.total_pnl_pct = ((500_000 + fluctuation) / base_balance) * 100
            self.current_metrics.active_positions = 5

        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 메트릭 업데이트 실패: {e}")

    async def _update_trading_metrics(self):
        """거래 메트릭 업데이트"""
        try:
            import random

            self.current_metrics.trades_today = random.randint(8, 20)
            self.current_metrics.successful_trades = random.randint(5, 15)
            self.current_metrics.failed_trades = self.current_metrics.trades_today - self.current_metrics.successful_trades

            if self.current_metrics.trades_today > 0:
                self.current_metrics.win_rate = (self.current_metrics.successful_trades / self.current_metrics.trades_today) * 100

            self.current_metrics.avg_profit = random.uniform(80000, 200000)
            self.current_metrics.avg_loss = random.uniform(40000, 100000)

        except Exception as e:
            self.logger.error(f"❌ 거래 메트릭 업데이트 실패: {e}")

    async def _update_market_metrics(self):
        """시장 메트릭 업데이트"""
        try:
            # 시장 관리자에서 정보 가져오기
            market_info = await self.market_manager.get_market_info()

            self.current_metrics.market_status = market_info.get("market_status", "UNKNOWN")
            self.current_metrics.trading_permission = market_info.get("permission_level", "NO_ACTIVITY")
            self.current_metrics.next_market_change = market_info.get("next_status_change", "")

            # API 호출 시뮬레이션
            self.current_metrics.api_calls += 1

        except Exception as e:
            self.logger.error(f"❌ 시장 메트릭 업데이트 실패: {e}")

    async def _update_system_metrics(self):
        """시스템 메트릭 업데이트"""
        try:
            try:
                import psutil
                self.current_metrics.cpu_usage = psutil.cpu_percent()
                self.current_metrics.memory_usage = psutil.virtual_memory().percent
            except ImportError:
                import random
                self.current_metrics.cpu_usage = random.uniform(15, 35)
                self.current_metrics.memory_usage = random.uniform(45, 65)

            self.current_metrics.uptime = self._get_uptime()

        except Exception as e:
            self.logger.error(f"❌ 시스템 메트릭 업데이트 실패: {e}")

    async def _update_strategy_metrics(self):
        """전략 메트릭 업데이트"""
        try:
            import random

            self.current_metrics.active_strategies = random.randint(3, 7)
            self.current_metrics.ai_accuracy = random.uniform(60, 85)

            # 전략별 성과 시뮬레이션
            strategies = ["모멘텀", "평균회귀", "브레이크아웃", "AI강화", "SuperTrend"]
            self.current_metrics.strategy_performance = {
                strategy: random.uniform(-5, 15) for strategy in strategies
            }

        except Exception as e:
            self.logger.error(f"❌ 전략 메트릭 업데이트 실패: {e}")

    async def _update_risk_metrics(self):
        """리스크 메트릭 업데이트"""
        try:
            # 설정 관리자에서 현재 설정 가져오기
            current_settings = self.settings_manager.current_settings

            self.current_metrics.risk_level = current_settings.risk_level.upper()
            self.current_metrics.position_size_ratio = current_settings.position_size_ratio
            self.current_metrics.max_positions = current_settings.max_positions
            self.current_metrics.stop_loss_pct = current_settings.stop_loss_pct

        except Exception as e:
            self.logger.error(f"❌ 리스크 메트릭 업데이트 실패: {e}")

    def _get_uptime(self) -> str:
        """가동시간 계산"""
        uptime = datetime.now() - self.start_time
        total_seconds = int(uptime.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    async def _simple_monitoring(self):
        """간단한 모니터링 (Rich 없이)"""
        try:
            while self.monitoring_active:
                print(f"\n{'='*60}")
                print(f"AI Trading System - 통합 모니터링")
                print(f"업데이트: {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")

                await self._update_all_metrics()

                print(f"💰 총자산: ₩{self.current_metrics.total_balance:,.0f}")
                print(f"📊 일일손익: ₩{self.current_metrics.daily_pnl:,.0f} ({self.current_metrics.daily_pnl_pct:+.2f}%)")
                print(f"🏪 시장상태: {self.current_metrics.market_status}")
                print(f"💹 거래: {self.current_metrics.trades_today}건 (승률: {self.current_metrics.win_rate:.1f}%)")
                print(f"🖥️ CPU: {self.current_metrics.cpu_usage:.1f}% | 💾 메모리: {self.current_metrics.memory_usage:.1f}%")

                await asyncio.sleep(self.update_interval)

        except KeyboardInterrupt:
            print("\n모니터링이 중단되었습니다.")

    async def stop_monitoring(self):
        """모니터링 중지"""
        try:
            self.monitoring_active = False

            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("📊 통합 모니터링 중지")

        except Exception as e:
            self.logger.error(f"❌ 모니터링 중지 실패: {e}")

    async def export_metrics(self, output_dir: str = "reports") -> str:
        """메트릭 데이터 내보내기"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = output_path / f"integrated_metrics_{timestamp}.json"

            # 데이터 준비
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "monitoring_session": {
                    "start_time": self.start_time.isoformat(),
                    "duration_minutes": (datetime.now() - self.start_time).total_seconds() / 60,
                    "total_updates": self.update_counter
                },
                "current_metrics": self.current_metrics.__dict__,
                "metrics_history": [
                    {
                        "timestamp": self.start_time + timedelta(seconds=i*self.update_interval),
                        **metrics.__dict__
                    }
                    for i, metrics in enumerate(self.metrics_history)
                ]
            }

            # 파일 저장
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"📄 메트릭 데이터 내보내기 완료: {export_file}")
            return str(export_file)

        except Exception as e:
            self.logger.error(f"❌ 메트릭 내보내기 실패: {e}")
            return ""

# 시그널 핸들러
def signal_handler(signum, frame):
    """시그널 핸들러"""
    print("\n👋 통합 모니터링을 종료합니다...")
    sys.exit(0)

# 메인 실행 함수
async def main():
    """메인 함수"""
    try:
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 통합 대시보드 초기화
        dashboard = IntegratedDashboard()
        await dashboard.initialize()

        # 모니터링 시작
        await dashboard.start_monitoring()

    except KeyboardInterrupt:
        print("\n👋 사용자가 중단했습니다.")
    except Exception as e:
        print(f"❌ 통합 대시보드 실행 중 오류: {e}")
    finally:
        try:
            await dashboard.stop_monitoring()
        except:
            pass

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 이벤트 루프 실행
    asyncio.run(main())