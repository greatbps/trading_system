#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수동으로 7종목을 지정하여 분석 테스트
"""

import asyncio
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()

# 테스트용 7종목 (대형주 위주)
TEST_STOCKS = [
    {'code': '005930', 'name': '삼성전자'},
    {'code': '000660', 'name': 'SK하이닉스'},
    {'code': '035420', 'name': 'NAVER'},
    {'code': '051910', 'name': 'LG화학'},
    {'code': '006400', 'name': '삼성SDI'},
    {'code': '035720', 'name': '카카오'},
    {'code': '028260', 'name': '삼성물산'},
]

async def main():
    """수동 7종목 분석"""
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold yellow]📊 수동 7종목 분석 테스트[/bold yellow]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")

    # 종목 리스트 출력
    table = Table(title="[bold]분석 대상 7종목[/bold]")
    table.add_column("No", style="cyan", justify="center")
    table.add_column("종목코드", style="magenta")
    table.add_column("종목명", style="green")

    for idx, stock in enumerate(TEST_STOCKS, 1):
        table.add_row(str(idx), stock['code'], stock['name'])

    console.print(table)

    console.print("\n[dim]💡 이 종목들로 momentum 전략 분석을 시작하시겠습니까?[/dim]")
    console.print("[dim]   실행 명령: main.py 실행 후 수동 분석 메뉴 선택[/dim]\n")

if __name__ == "__main__":
    asyncio.run(main())
