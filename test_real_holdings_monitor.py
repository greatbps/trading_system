#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 계좌 보유 종목 모니터링 화면 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.append(str(Path(__file__).parent))

from data_collectors.kis_collector import KISCollector
from config import Config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

console = Console()

class RealHoldingsMonitor:
    """실제 계좌 보유 종목 모니터링"""

    def __init__(self):
        self.config = Config()
        self.kis_collector = None
        self.last_update = None

    async def initialize(self):
        """초기화"""
        try:
            self.kis_collector = KISCollector(self.config)
            await self.kis_collector.initialize()
            console.print("[green]✅ KIS 컬렉터 초기화 완료[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 초기화 실패: {e}[/red]")
            return False

    async def get_real_holdings(self):
        """실제 계좌 보유 종목 조회"""
        try:
            holdings = await self.kis_collector.get_holdings()
            balance = await self.kis_collector.get_account_balance()
            self.last_update = datetime.now()

            return {
                'holdings': holdings,
                'balance': balance,
                'update_time': self.last_update
            }
        except Exception as e:
            console.print(f"[red]❌ 보유 종목 조회 실패: {e}[/red]")
            return None

    def create_holdings_table(self, data):
        """보유 종목 테이블 생성"""
        if not data or not data['holdings']:
            return Panel("[yellow]보유 종목이 없습니다[/yellow]", title="💰 실제 계좌 보유 종목")

        holdings = data['holdings']
        balance = data['balance']
        update_time = data['update_time']

        # 보유 종목 테이블
        table = Table(title=f"💰 실제 계좌 보유 종목 (마지막 업데이트: {update_time.strftime('%H:%M:%S')})")
        table.add_column("종목코드", style="cyan", no_wrap=True, width=8)
        table.add_column("종목명", style="white", width=15)
        table.add_column("보유수량", style="green", justify="right", width=10)
        table.add_column("평단가", style="blue", justify="right", width=12)
        table.add_column("현재가", style="white", justify="right", width=12)
        table.add_column("평가금액", style="green", justify="right", width=12)
        table.add_column("손익률", style="magenta", justify="right", width=10)

        total_evaluation = 0

        for symbol, info in holdings.items():
            name = info['name'][:12] + "..." if len(info['name']) > 12 else info['name']
            quantity = info['quantity']
            avg_price = info['avg_price']
            current_price = info['current_price']
            evaluation = info['evaluation']
            profit_rate = info['profit_rate']

            total_evaluation += evaluation

            # 수익률에 따른 색상
            profit_color = "green" if profit_rate >= 0 else "red"
            profit_symbol = "+" if profit_rate >= 0 else ""

            table.add_row(
                symbol,
                name,
                f"{quantity:,}",
                f"{avg_price:,.0f}원",
                f"{current_price:,}원",
                f"{evaluation:,}원",
                f"[{profit_color}]{profit_symbol}{profit_rate:.2f}%[/{profit_color}]"
            )

        # 계좌 요약 정보
        summary_text = f"""
[bold]📊 계좌 요약[/bold]
• 보유 종목 수: {len(holdings)}개
• 총 평가금액: {total_evaluation:,}원
• 사용가능 현금: {balance.get('available_cash', 0):,}원
• 총 자산: {balance.get('total_evaluation', 0) + balance.get('available_cash', 0):,}원
        """

        layout = Layout()
        layout.split(
            Layout(Panel(table), name="holdings"),
            Layout(Panel(summary_text, title="📈 계좌 현황"), name="summary", size=8)
        )

        return layout

    async def run_monitor(self, refresh_seconds=30):
        """실시간 모니터링 실행"""
        console.print(Panel("[bold green]🔄 실제 계좌 보유 종목 실시간 모니터링[/bold green]", border_style="green"))
        console.print(f"[yellow]📊 {refresh_seconds}초마다 자동 갱신됩니다. Ctrl+C로 종료하세요.[/yellow]")

        try:
            with Live(refresh_per_second=1) as live:
                while True:
                    try:
                        # 실제 보유 종목 조회
                        data = await self.get_real_holdings()

                        if data:
                            # 테이블 업데이트
                            live.update(self.create_holdings_table(data))
                        else:
                            live.update(Panel("[red]❌ 데이터 조회 실패[/red]", title="오류"))

                        # 다음 업데이트까지 대기
                        await asyncio.sleep(refresh_seconds)

                    except KeyboardInterrupt:
                        console.print("\n[yellow]📴 모니터링을 중단합니다.[/yellow]")
                        break
                    except Exception as e:
                        live.update(Panel(f"[red]❌ 오류 발생: {e}[/red]", title="오류"))
                        await asyncio.sleep(5)  # 오류 시 5초 대기

        except KeyboardInterrupt:
            console.print("[yellow]📴 모니터링이 종료되었습니다.[/yellow]")

async def main():
    """메인 실행 함수"""
    monitor = RealHoldingsMonitor()

    if await monitor.initialize():
        # 첫 번째 조회로 테스트
        console.print("[cyan]📊 실제 계좌 보유 종목 조회 테스트...[/cyan]")
        data = await monitor.get_real_holdings()

        if data:
            console.print(monitor.create_holdings_table(data))
            console.print()

            # 실시간 모니터링 옵션 제공
            if console.input("[bold cyan]실시간 모니터링을 시작하시겠습니까? (y/n): [/bold cyan]").lower() == 'y':
                refresh_seconds = 30
                try:
                    refresh_input = console.input(f"[cyan]갱신 주기를 입력하세요 (기본값 {refresh_seconds}초): [/cyan]")
                    if refresh_input.strip():
                        refresh_seconds = int(refresh_input)
                except ValueError:
                    console.print(f"[yellow]⚠️ 잘못된 입력, 기본값 {refresh_seconds}초 사용[/yellow]")

                await monitor.run_monitor(refresh_seconds)
        else:
            console.print("[red]❌ 보유 종목 조회에 실패했습니다.[/red]")
    else:
        console.print("[red]❌ 모니터링 시스템 초기화에 실패했습니다.[/red]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]📴 프로그램이 종료되었습니다.[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 프로그램 실행 중 오류: {e}[/red]")