
import asyncio
from rich.console import Console
from config import Config
from data_collectors.kis_collector import KISCollector
from database.database_manager import DatabaseManager
from trading.db_auto_trader import DatabaseAutoTrader
from trading.executor import TradingExecutor

async def import_holdings_to_system():
    """
    현재 HTS 보유 종목을 시스템의 모니터링 DB로 가져옵니다.
    이 과정에서 손절가가 자동으로 계산되고 저장됩니다.
    """
    console = Console()
    console.print("[yellow]보유 종목 시스템 등록을 시작합니다...[/yellow]")

    try:
        config = Config()
        db_manager = DatabaseManager(config)
        kis_collector = KISCollector(config)
        await kis_collector.initialize()
        
        # DatabaseAutoTrader 초기화에 필요한 의존성 주입
        executor = TradingExecutor(config, kis_collector, db_manager)
        auto_trader = DatabaseAutoTrader(config, kis_collector, executor, db_manager=db_manager)

        console.print("\n[1/2] HTS 보유 종목을 모니터링 DB로 가져옵니다...")
        result = await auto_trader.import_portfolio_to_monitoring()

        console.print("\n[2/2] 작업 완료. 결과를 출력합니다.")
        if result and result.get('success'):
            console.print(f"[green]총 {result.get('total_processed', 0)}개 보유 종목 처리 완료.[/green]")
            console.print(f"- 신규 추가: {result.get('added_count', 0)}개")
            console.print(f"- 이미 존재하여 건너뜀: {result.get('skipped_count', 0)}개")
            console.print(f"- 실패: {result.get('failed_count', 0)}개")
        else:
            console.print(f"[red]작업 실패: {result.get('message', '알 수 없는 오류')}[/red]")

    except Exception as e:
        console.print(f"[bold red]오류 발생: {e}[/bold red]")
    finally:
        if 'kis_collector' in locals() and kis_collector:
            await kis_collector.close()

if __name__ == "__main__":
    asyncio.run(import_holdings_to_system())
