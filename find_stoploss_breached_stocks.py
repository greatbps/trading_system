import asyncio
import pandas as pd
from rich.console import Console
from rich.table import Table
from config import Config
from data_collectors.kis_collector import KISCollector
from data_collectors.chart_data_collector import ChartDataCollector
from analyzers.technical_indicators import RealTechnicalIndicators

async def find_breached_stocks_with_atr():
    """
    ATR을 이용해 동적으로 손절가를 계산하고, 이를 하회한 보유 종목을 찾아 리스트업합니다.
    (매도 기능은 없습니다.)
    """
    console = Console()
    console.print("[yellow]손절가 하회 종목 검색을 시작합니다... (ATR 동적 계산 방식)[/yellow]")

    try:
        # --- 1. 시스템 초기화 ---
        console.print("\n[1/4] 시스템 컴포넌트를 초기화합니다...")
        config = Config()
        kis_collector = KISCollector(config)
        await kis_collector.initialize()
        chart_collector = ChartDataCollector(kis_collector)
        indicator_calculator = RealTechnicalIndicators()
        ATR_MULTIPLIER = 2.0  # ATR 기반 손절을 위한 배수

        # --- 2. 보유 종목 조회 ---
        console.print("\n[2/4] KIS API에서 현재 보유 종목을 조회합니다...")
        holdings = await kis_collector.get_holdings()

        if not holdings:
            console.print("[green]현재 보유 중인 종목이 없습니다.[/green]")
            return

        console.print(f"총 {len(holdings)}개의 보유 종목을 확인했습니다.")

        # --- 3. 종목별 분석 및 손절가 계산 ---
        breached_stocks = []
        console.print("\n[3/4] 각 종목의 ATR을 계산하여 동적 손절가를 설정하고 현재가와 비교합니다...")

        for symbol, holding_info in holdings.items():
            avg_price = holding_info.get('avg_price', 0)
            quantity = holding_info.get('quantity', 0)
            current_price = holding_info.get('current_price', 0)

            if quantity == 0 or avg_price == 0:
                continue

            console.print(f"  - [cyan]{holding_info.get('name')}({symbol})[/cyan] 분석 중...")

            # 15분봉 데이터 조회 (get_minute_chart_data 사용)
            price_data_list = await chart_collector.get_minute_chart_data(symbol=symbol, minutes=15, periods=100)

            if not price_data_list or len(price_data_list) < 20: # ATR 계산을 위한 최소 데이터 확인
                console.print(f"    [yellow]경고: '{holding_info.get('name')}'의 차트 데이터가 부족하여 ATR 계산이 불가합니다. 기본 손절 로직을 적용합니다.[/yellow]")
                stop_loss_price = int(avg_price * 0.95) # 5% 고정 손절
            else:
                # ATR 계산
                # PriceData 객체 리스트를 딕셔너리 리스트로 변환
                price_dicts = [p.to_dict() for p in price_data_list]
                df = pd.DataFrame(price_dicts)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
                df = df.astype(float)
                
                indicators = indicator_calculator.calculate_all_indicators(symbol, df)
                atr = indicators.get('indicators', {}).get('atr')

                if atr is not None and atr > 0:
                    stop_loss_price = int(avg_price - (atr * ATR_MULTIPLIER))
                    console.print(f"    [green]ATR 기반 손절가 계산 완료: {stop_loss_price:,}원 (ATR: {atr:,.1f})[/green]")
                else:
                    console.print(f"    [yellow]경고: ATR 계산 실패. 기본 손절 로직을 적용합니다.[/yellow]")
                    stop_loss_price = int(avg_price * 0.95)

            # 현재가가 계산된 손절가 이하인 경우, 청산 대상 목록에 추가
            if current_price <= stop_loss_price:
                profit_loss = (current_price - avg_price) * quantity
                profit_rate = (profit_loss / (avg_price * quantity)) * 100 if avg_price > 0 and quantity > 0 else 0
                breached_stocks.append({
                    "symbol": symbol,
                    "name": holding_info.get('name'),
                    "quantity": quantity,
                    "current_price": current_price,
                    "stop_loss_price": stop_loss_price,
                    "profit_rate": profit_rate,
                    "profit_loss": profit_loss
                })
                console.print(f"    [red]>> 청산 대상 발견: 현재가 {current_price:,}원 <= 손절가 {stop_loss_price:,}원[/red]")

        # --- 4. 최종 결과 출력 ---
        console.print("\n[4/4] 분석 완료. 결과를 출력합니다.")
        if not breached_stocks:
            console.print("\n[bold green]손절가를 하회한 종목이 없습니다. 모든 포지션이 안전합니다.[/bold green]")
            return

        console.print("\n[bold red]>> 긴급 청산이 필요한 종목 목록 <<[/bold red]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("종목코드", style="cyan")
        table.add_column("종목명")
        table.add_column("보유수량", justify="right")
        table.add_column("현재가", justify="right")
        table.add_column("계산된 손절가(ATR)", justify="right", style="yellow")
        table.add_column("수익률", justify="right")
        table.add_column("평가손익", justify="right")

        total_loss = 0
        for stock in breached_stocks:
            profit_rate_str = f"[red]{stock['profit_rate']:.2f}%[/red]"
            table.add_row(
                stock['symbol'],
                stock['name'],
                str(stock['quantity']),
                f"{stock['current_price']:,}원",
                f"{stock['stop_loss_price']:,}원",
                profit_rate_str,
                f"[red]{stock['profit_loss']:,.0f}원[/red]"
            )
            total_loss += stock['profit_loss']

        console.print(table)
        console.print(f"\n[bold red]>> 총 예상 손실: {total_loss:,.0f}원[/bold red]")
        console.print("[yellow]위 목록은 청산이 필요한 종목들입니다. 다음 단계에서 실제 매도를 진행할 수 있습니다.[/yellow]")

    except Exception as e:
        console.print(f"[bold red]오류 발생: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())
    finally:
        if 'kis_collector' in locals() and kis_collector:
            await kis_collector.close()

if __name__ == "__main__":
    asyncio.run(find_breached_stocks_with_atr())
