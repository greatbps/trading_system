#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start_auto_system.py

완전 자동화 거래 시스템 시작 스크립트
조건 감지시 자동으로 모든 기능이 실행됩니다.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️ Rich 라이브러리가 설치되지 않았습니다. 기본 출력을 사용합니다.")

from core.auto_trading_orchestrator import AutoTradingOrchestrator
from utils.logger import get_logger

class AutoSystemStarter:
    """자동화 시스템 시작 관리자"""

    def __init__(self):
        """시작 관리자 초기화"""
        self.logger = get_logger("AutoSystemStarter")
        self.console = Console() if RICH_AVAILABLE else None
        self.orchestrator = None
        self.is_running = False

        # 종료 신호 처리
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """종료 신호 처리"""
        if self.console:
            self.console.print("\n[yellow]종료 신호를 받았습니다. 안전하게 종료 중...[/yellow]")
        else:
            print("\n종료 신호를 받았습니다. 안전하게 종료 중...")

        self.is_running = False

    async def start_system(self):
        """자동화 시스템 시작"""
        try:
            self._show_welcome_message()

            # 시스템 초기화
            await self._initialize_system()

            # 자동화 시작
            await self._run_automation()

        except Exception as e:
            self.logger.error(f"❌ 시스템 시작 실패: {e}")
            if self.console:
                self.console.print(f"[red]❌ 시스템 시작 실패: {e}[/red]")

    def _show_welcome_message(self):
        """시작 메시지 표시"""
        if self.console:
            welcome_text = """
🤖 AI Trading System - 완전 자동화 모드

자동으로 실행되는 기능들:
• 📊 잔고 변화 감지 시 설정 자동 조정
• 📈 시장 조건 변화 시 백테스팅 자동 실행
• 📋 성과 악화 시 보수적 모드 자동 전환
• 🎯 수익 증가 시 적극적 모드 자동 전환
• 📊 실시간 시각화 자동 생성
• ⏰ 정기적 성과 리뷰 및 최적화

Ctrl+C로 안전하게 종료할 수 있습니다.
            """

            self.console.print(Panel.fit(welcome_text, style="bold blue"))
        else:
            print("🤖 AI Trading System - 완전 자동화 모드 시작")
            print("Ctrl+C로 종료할 수 있습니다.")

    async def _initialize_system(self):
        """시스템 초기화"""
        try:
            if self.console:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console
                ) as progress:
                    task = progress.add_task("시스템 초기화 중...", total=1)

                    # 오케스트레이터 초기화
                    self.orchestrator = AutoTradingOrchestrator()

                    progress.advance(task)
                    progress.update(task, description="초기화 완료!")

                self.console.print("[green]✅ 시스템 초기화 완료[/green]")
            else:
                print("시스템 초기화 중...")
                self.orchestrator = AutoTradingOrchestrator()
                print("✅ 시스템 초기화 완료")

        except Exception as e:
            self.logger.error(f"❌ 시스템 초기화 실패: {e}")
            raise

    async def _run_automation(self):
        """자동화 실행"""
        try:
            self.is_running = True

            if self.console:
                # Rich를 사용한 실시간 대시보드
                await self._run_with_dashboard()
            else:
                # 기본 로깅 모드
                await self._run_basic_mode()

        except Exception as e:
            self.logger.error(f"❌ 자동화 실행 실패: {e}")
            raise

    async def _run_with_dashboard(self):
        """Rich 대시보드와 함께 실행"""
        try:
            # 레이아웃 설정
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main", ratio=1),
                Layout(name="footer", size=5)
            )

            layout["main"].split_row(
                Layout(name="status"),
                Layout(name="events")
            )

            # 오케스트레이터 시작 (백그라운드에서)
            orchestrator_task = asyncio.create_task(
                self.orchestrator.start_orchestration()
            )

            # 대시보드 업데이트 루프
            with Live(layout, refresh_per_second=1, console=self.console) as live:
                while self.is_running and not orchestrator_task.done():
                    try:
                        # 시스템 상태 가져오기
                        system_overview = await self.orchestrator.get_system_overview()

                        # 헤더 업데이트
                        layout["header"].update(
                            Panel(
                                f"🤖 AI Trading System - 자동화 실행 중 | 상태: {system_overview['system_health']['overall_status']}",
                                style="bold blue"
                            )
                        )

                        # 시스템 상태
                        status_table = Table(title="시스템 상태")
                        status_table.add_column("구성요소", style="cyan")
                        status_table.add_column("상태", style="magenta")

                        components = system_overview.get('components', {})
                        status_table.add_row("잔고 모니터링", "🟢 활성" if components.get('balance_monitor') else "🔴 비활성")
                        status_table.add_row("백테스팅 트리거", "🟢 활성" if components.get('backtest_trigger') else "🔴 비활성")

                        performance = system_overview.get('performance_tracking', {})
                        status_table.add_row("총 설정 조정", str(performance.get('total_adjustments', 0)))
                        status_table.add_row("총 백테스팅", str(performance.get('total_backtests', 0)))

                        layout["status"].update(status_table)

                        # 최근 이벤트
                        events_table = Table(title="최근 이벤트")
                        events_table.add_column("시간", style="cyan")
                        events_table.add_column("이벤트", style="magenta")

                        # 실제 이벤트 데이터가 있다면 표시
                        recent_count = system_overview.get('recent_events', 0)
                        events_table.add_row("지난 1시간", f"{recent_count}개 이벤트")
                        events_table.add_row("활성 규칙", f"{system_overview.get('active_rules', 0)}개")

                        layout["events"].update(events_table)

                        # 푸터
                        layout["footer"].update(
                            Panel(
                                "💡 시스템이 자동으로 실행 중입니다. Ctrl+C로 안전하게 종료할 수 있습니다.\n"
                                "📊 잔고 변화, 시장 조건, 성과 임계값을 모니터링하여 자동으로 대응합니다.",
                                style="dim"
                            )
                        )

                        await asyncio.sleep(5)  # 5초마다 업데이트

                    except Exception as e:
                        self.logger.error(f"❌ 대시보드 업데이트 오류: {e}")
                        await asyncio.sleep(5)

            # 오케스트레이터 정리
            if not orchestrator_task.done():
                orchestrator_task.cancel()
                try:
                    await orchestrator_task
                except asyncio.CancelledError:
                    pass

            await self.orchestrator.stop_orchestration()

        except Exception as e:
            self.logger.error(f"❌ 대시보드 실행 실패: {e}")

    async def _run_basic_mode(self):
        """기본 모드로 실행"""
        try:
            print("🚀 자동화 시스템 시작...")

            # 오케스트레이터 시작
            orchestrator_task = asyncio.create_task(
                self.orchestrator.start_orchestration()
            )

            # 상태 출력 루프
            while self.is_running and not orchestrator_task.done():
                try:
                    system_overview = await self.orchestrator.get_system_overview()

                    print(f"\n📊 시스템 상태 ({datetime.now().strftime('%H:%M:%S')})")
                    print(f"  전체 상태: {system_overview['system_health']['overall_status']}")
                    print(f"  잔고 모니터링: {'활성' if system_overview['components']['balance_monitor'] else '비활성'}")
                    print(f"  백테스팅: {'활성' if system_overview['components']['backtest_trigger'] else '비활성'}")

                    performance = system_overview.get('performance_tracking', {})
                    print(f"  설정 조정: {performance.get('total_adjustments', 0)}회")
                    print(f"  백테스팅: {performance.get('total_backtests', 0)}회")

                    await asyncio.sleep(30)  # 30초마다 상태 출력

                except Exception as e:
                    self.logger.error(f"❌ 상태 출력 오류: {e}")
                    await asyncio.sleep(30)

            # 정리
            if not orchestrator_task.done():
                orchestrator_task.cancel()
                try:
                    await orchestrator_task
                except asyncio.CancelledError:
                    pass

            await self.orchestrator.stop_orchestration()

        except Exception as e:
            self.logger.error(f"❌ 기본 모드 실행 실패: {e}")

async def main():
    """메인 함수"""
    try:
        starter = AutoSystemStarter()
        await starter.start_system()

    except KeyboardInterrupt:
        print("\n👋 사용자가 시스템을 종료했습니다.")
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        logging.error(f"시스템 오류: {e}", exc_info=True)

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/auto_system.log'),
            logging.StreamHandler()
        ]
    )

    # 로그 디렉토리 생성
    Path('logs').mkdir(exist_ok=True)

    # 시스템 시작
    asyncio.run(main())