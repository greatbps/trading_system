
import asyncio
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from config import Config
from data_collectors.kis_collector import KISCollector
from trading.executor import TradingExecutor

def calculate_fallback_stop_loss(avg_price: float) -> int:
    """기본 손절가 계산 (고정 5%)"""
    if avg_price > 0:
        return int(avg_price * 0.95)
    return 0

async def execute_liquidation():
    """
    손절가를 하회한 보유 종목을 찾아 즉시 시장가 매도합니다.
    """
    console = Console()
    console.print("[bold red]>> 긴급 청산 절차를 시작합니다. <<[/bold red]")

    breached_stocks = []
    kis_collector = None
    try:
        # --- 1. 시스템 초기화 및 청산 대상 검색 ---
        console.print("\n[1/3] 청산 대상을 검색합니다...")
        config = Config()
        kis_collector = KISCollector(config)
        await kis_collector.initialize()
        
        holdings = await kis_collector.get_holdings()
        if not holdings:
            console.print("[green]청산할 보유 종목이 없습니다.[/green]")
            return

        for symbol, holding_info in holdings.items():
            current_price = holding_info.get('current_price', 0)
            avg_price = holding_info.get('avg_price', 0)
            quantity = holding_info.get('quantity', 0)

            if quantity == 0 or avg_price == 0:
                continue

            # 이 스크립트는 ATR 계산이 실패했으므로, 검증된 기본 손절 로직만 사용합니다.
            stop_loss_price = calculate_fallback_stop_loss(avg_price)

            if current_price <= stop_loss_price:
                breached_stocks.append({
                    "symbol": symbol,
                    "name": holding_info.get('name'),
                    "quantity": quantity
                })
        
        if not breached_stocks:
            console.print("\n[green]손절가를 하회한 종목이 없습니다. 모든 포지션이 안전합니다.[/green]")
            return

        # --- 2. 사용자 최종 확인 ---
        console.print("\n[2/3] 청산 대상 목록을 확인하고 최종 승인을 요청합니다...")
        console.print("\n[bold red]!! 경고 !! 아래 종목에 대한 시장가 매도 주문이 실행됩니다.[/bold red]")
        table = Table(title="긴급 청산 대상")
        table.add_column("종목코드", style="cyan")
        table.add_column("종목명")
        table.add_column("매도수량", justify="right")
        for stock in breached_stocks:
            table.add_row(stock['symbol'], stock['name'], str(stock['quantity']))
        console.print(table)

        if not Confirm.ask("\n이 작업은 되돌릴 수 없습니다. 정말로 위 종목들의 매도를 진행하시겠습니까?", default=False):
            console.print("[yellow]사용자가 작업을 취소했습니다.[/yellow]")
            return

        # --- 3. 매도 실행 ---
        console.print("\n[3/3] 사용자 승인 확인. 매도 주문을 실행합니다...")
        executor = TradingExecutor(config, kis_collector)

        success_count = 0
        fail_count = 0
        for stock in breached_stocks:
            console.print(f"  - [cyan]{stock['name']}({stock['symbol']})[/cyan] {stock['quantity']}주 시장가 매도 시도...")
            try:
                result = await executor.sell_stock(
                    symbol=stock['symbol'],
                    quantity=stock['quantity'],
                    order_type='MARKET' # 시장가로 즉시 체결
                )
                if result and result.get('success'):
                    console.print(f"    [green]>> 매도 주문 성공 (주문번호: {result.get('order_id')})[/green]")
                    success_count += 1
                else:
                    console.print(f"    [red]>> 매도 주문 실패: {result.get('message', '알 수 없는 오류')}[/red]")
                    fail_count += 1
            except Exception as e:
                console.print(f"    [red]>> 매도 중 심각한 오류 발생: {e}[/red]")
                fail_count += 1
            await asyncio.sleep(0.5) # 주문 간 간격

        console.print("\n[bold]>> 긴급 청산 절차 완료 <<[/bold]")
        console.print(f"- 성공: {success_count}건")
        console.print(f"- 실패: {fail_count}건")

    except Exception as e:
        console.print(f"[bold red]오류 발생: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
    finally:
        if kis_collector:
            await kis_collector.close()

if __name__ == "__main__":
    asyncio.run(execute_liquidation())
