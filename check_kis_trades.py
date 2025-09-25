#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API를 통한 실제 거래내역 조회 및 시스템 기록과 비교
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config import Config
from data_collectors.kis_collector import KISCollector
from database.database_manager import DatabaseManager
from utils.logger import get_logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

async def main():
    """KIS API 거래내역 조회 및 비교"""
    console = Console()
    logger = get_logger("check_kis_trades")

    try:
        # 설정 로드
        config = Config()

        # KIS Collector 초기화
        kis_collector = KISCollector(config)
        await kis_collector.initialize()

        # 오늘 날짜
        today = datetime.now().strftime('%Y%m%d')

        console.print(Panel(f"[bold cyan]KIS API 거래내역 조회[/bold cyan]\n날짜: {today}", expand=False))

        # KIS API를 통한 거래내역 조회
        logger.info("KIS API 거래내역 조회 시작...")
        kis_result = await kis_collector.get_daily_trades(today, today)

        if not kis_result.get('success'):
            console.print(f"[red]❌ KIS API 조회 실패: {kis_result.get('error')}[/red]")
            return

        trades = kis_result.get('trades', [])
        console.print(f"[green]✅ KIS API에서 {len(trades)}건의 거래내역 조회 완료[/green]")

        if not trades:
            console.print("[yellow]⚠️  오늘 거래내역이 없습니다.[/yellow]")
            return

        # 거래내역 테이블 출력
        table = Table(title=f"KIS API 거래내역 ({today})")
        table.add_column("시간", style="cyan")
        table.add_column("종목", style="white")
        table.add_column("종목명", style="green")
        table.add_column("구분", style="magenta")
        table.add_column("수량", style="yellow")
        table.add_column("단가", style="white")
        table.add_column("금액", style="blue")
        table.add_column("주문번호", style="dim")

        total_buy_amount = 0
        total_sell_amount = 0

        for trade in trades:
            side_color = "red" if trade['side'] == '매도' else "green"
            table.add_row(
                trade['time'][:6] if trade['time'] else '',  # HHMMSS -> HHMMSS
                trade['symbol'],
                trade['name'][:8] + '...' if len(trade['name']) > 8 else trade['name'],
                f"[{side_color}]{trade['side']}[/{side_color}]",
                f"{trade['quantity']:,}주",
                f"{trade['price']:,}원",
                f"{trade['amount']:,}원",
                trade['order_id'][:8] + '...' if len(trade['order_id']) > 8 else trade['order_id']
            )

            if trade['side'] == '매수':
                total_buy_amount += trade['amount']
            else:
                total_sell_amount += trade['amount']

        console.print(table)

        # 거래 요약
        summary_table = Table(title="거래 요약")
        summary_table.add_column("구분", style="cyan")
        summary_table.add_column("금액", style="yellow")

        summary_table.add_row("총 매수금액", f"{total_buy_amount:,}원")
        summary_table.add_row("총 매도금액", f"{total_sell_amount:,}원")
        summary_table.add_row("순손익", f"{total_sell_amount - total_buy_amount:,}원")

        console.print(summary_table)

        # 013360, 045340 종목 특별 확인
        target_symbols = ['013360', '045340']
        console.print(f"\n[bold cyan]🔍 문제 종목 ({', '.join(target_symbols)}) 거래 확인:[/bold cyan]")

        found_trades = []
        for trade in trades:
            if trade['symbol'] in target_symbols:
                found_trades.append(trade)

        if found_trades:
            target_table = Table(title="문제 종목 거래내역")
            target_table.add_column("시간", style="cyan")
            target_table.add_column("종목", style="white")
            target_table.add_column("종목명", style="green")
            target_table.add_column("구분", style="magenta")
            target_table.add_column("수량", style="yellow")
            target_table.add_column("단가", style="white")
            target_table.add_column("금액", style="blue")

            for trade in found_trades:
                side_color = "red" if trade['side'] == '매도' else "green"
                target_table.add_row(
                    trade['time'][:6] if trade['time'] else '',
                    trade['symbol'],
                    trade['name'],
                    f"[{side_color}]{trade['side']}[/{side_color}]",
                    f"{trade['quantity']:,}주",
                    f"{trade['price']:,}원",
                    f"{trade['amount']:,}원"
                )

            console.print(target_table)
        else:
            console.print("[yellow]⚠️  문제 종목의 거래내역이 KIS API에서 발견되지 않았습니다.[/yellow]")
            console.print("[dim]이는 매도 주문이 실제로 체결되지 않았음을 의미합니다.[/dim]")

        # Raw 데이터 저장 (디버깅용)
        import json
        with open('kis_trades_raw.json', 'w', encoding='utf-8') as f:
            json.dump(kis_result, f, indent=2, ensure_ascii=False)

        console.print(f"\n[dim]원본 데이터가 kis_trades_raw.json에 저장되었습니다.[/dim]")

    except Exception as e:
        console.print(f"[red]❌ 오류 발생: {e}[/red]")
        logger.error(f"거래내역 조회 중 오류: {e}")

    finally:
        if 'kis_collector' in locals():
            await kis_collector.close()

if __name__ == "__main__":
    asyncio.run(main())