# Claude 작업 지시서: 실시간 매매 신호 현황판 구현

## 1. 개발 목표 및 사용자 요구사항

### 왜 이 기능이 필요한가? (As-is)

현재 시스템은 감시 대상 종목을 선정하고 모니터링은 하고 있지만, 어떤 이유로 실제 매수/매도 주문까지 이어지지 않는지 알 수 없는 **"깜깜이" 상태**입니다. 매수 조건이 너무 엄격한 것으로 추정되지만, 여러 개의 매수 조건 중 어느 것이 충족되고 어느 것이 충족되지 않는지 실시간으로 확인할 방법이 없습니다.

### 무엇을 보고 싶은가? (To-be)

사용자는 자동매매 메뉴의 **'모니터링 현황' 화면**에서 다음과 같은 정보가 **실시간으로 갱신**되는 것을 보고 싶어 합니다.

1.  **대상**: 현재 감시 중이거나 보유 중인 모든 종목
2.  **핵심 정보**: 각 종목의 현재가, 수익률 등 기본 정보
3.  **실시간 신호**: 아래 5가지 매매 신호의 충족 여부(True/False)와 충족된 신호의 개수
    -   `RSI` 신호
    -   `Volume` (거래량) 신호
    -   `MACD` 신호
    -   `Candle` (캔들 패턴) 신호
    -   `Golden Cross` (골든 크로스) 신호
4.  **동작 방식**: 화면에 진입하면, 별도 입력 없이 **5초마다 자동으로 화면 전체가 갱신**되어야 합니다.

### 기대 효과

이 기능이 구현되면, 사용자는 어떤 종목이 매수/매도 직전인지, 혹은 왜 매매가 이루어지지 않는지를 직관적으로 파악할 수 있습니다. 이를 통해 향후 매매 조건 로직을 수정하거나 최적화하는 데 중요한 판단 근거로 삼을 수 있습니다.

---

## 2. 기술적 현황 및 문제점

- **문제점**: 이전 개발자(Gemini)가 UI 표시 로직을 엉뚱한 파일(`core/menu_handlers.py`)에 작성했습니다. 실제 자동매매 메뉴의 UI는 **`core/db_auto_trading_handler.py`** 파일이 담당하고 있으므로, 해당 파일의 코드가 수정되어야 합니다.
- **데이터 흐름**: 데이터 처리 부분은 올바르게 수정되었습니다. `trading/db_auto_trader.py`는 현재 신호 분석 결과를 계산하고 임시 저장(캐시)하고 있으며, `get_monitoring_status()` 함수를 통해 이 데이터를 외부로 제공할 준비가 되어 있습니다.

## 3. 작업 절차

### 3.1. [필수] UI 로직 수정 (`core/db_auto_trading_handler.py`)

이 파일의 `_view_monitoring_status_safe` 함수가 실제 현황판을 호출하는 시작점입니다. 이 함수가 호출하는 `_view_monitoring_status` 함수를 아래의 새 코드로 **완전히 교체**해야 합니다. 또한, 테이블 생성을 돕는 `_add_stock_to_table` 헬퍼 함수도 같은 클래스 내에 추가해야 합니다.

**교체 대상 함수:** `_view_monitoring_status`

**새로운 코드:**

```python
    async def _view_monitoring_status(self) -> bool:
        """[실시간] 모니터링 현황 - 보유/감시 종목 및 신호 분석 결과를 실시간으로 표시합니다."""
        if not (hasattr(self, 'auto_trader') and self.auto_trader):
            self.console.print("[red]❌ 자동매매 시스템(auto_trader)을 찾을 수 없습니다.[/red]")
            return False

        try:
            with self.console.status("[bold green]실시간 모니터링 시작... (Ctrl+C로 종료)", spinner="dots") as status:
                while True:
                    status_info = await self.auto_trader.get_monitoring_status()
                    
                    self.console.clear()
                    self.console.print(Panel(f"[bold cyan]📊 실시간 모니터링 현황 ({datetime.now().strftime('%H:%M:%S')})[/bold cyan]", border_style="cyan"))

                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("종목명", style="cyan", width=12)
                    table.add_column("현재가", justify="right", style="green", width=10)
                    table.add_column("수익률", justify="right", width=8)
                    table.add_column("상태", style="yellow", width=8)
                    table.add_column("전략", style="blue", width=12)
                    table.add_column("신호(R/V/M/C/G)", justify="center", width=20)
                    table.add_column("신호수", justify="center", style="bold", width=6)

                    monitored_stocks = status_info.get('monitoring_stocks', {})
                    
                    if not monitored_stocks:
                        self.console.print("[yellow]⚠️ 감시 또는 보유중인 종목이 없습니다.[/yellow]")
                    
                    holding_stocks = {s: d for s, d in monitored_stocks.items() if d.get('buy_price')}
                    watching_stocks = {s: d for s, d in monitored_stocks.items() if not d.get('buy_price')}

                    if holding_stocks:
                        table.add_section()
                        table.add_row("[bold green]🏦 보유 종목[/bold green]")
                        for symbol, stock_data in holding_stocks.items():
                            self._add_stock_to_table(table, symbol, stock_data)

                    if watching_stocks:
                        table.add_section()
                        table.add_row("[bold blue]🎯 감시 종목[/bold blue]")
                        for symbol, stock_data in watching_stocks.items():
                            self._add_stock_to_table(table, symbol, stock_data)

                    self.console.print(table)
                    self.console.print("[dim]R:RSI, V:Volume, M:MACD, C:Candle, G:Golden Cross[/dim]")
                    self.console.print("[dim]업데이트 중... (Ctrl+C로 종료)[/dim]")
                    
                    await asyncio.sleep(5) # 5초마다 갱신

        except asyncio.CancelledError:
            self.console.print("\n[yellow]모니터링이 취소되었습니다.[/yellow]")
            return True
        except KeyboardInterrupt:
            self.console.print("\n[yellow]🛑 실시간 모니터링을 종료합니다.[/yellow]")
            return True
        except Exception as e:
            self.console.print(f"[red]❌ 모니터링 현황 조회 중 오류 발생: {e}[/red]")
            self.logger.error(f"❌ _view_monitoring_status 오류: {e}", exc_info=True)
            return False

    def _add_stock_to_table(self, table: Table, symbol: str, stock_data: Dict):
        """테이블에 종목 정보를 추가하는 헬퍼 함수"""
        profit_rate = stock_data.get('profit_rate', 0.0)
        profit_color = "green" if profit_rate >= 0 else "red"
        profit_str = f"[{profit_color}]{profit_rate:+.2f}%[/{profit_color}]" if stock_data.get('buy_price') else "-"

        status_str = "[bold green]보유[/bold green]" if stock_data.get('buy_price') else "[dim]감시[/dim]"

        signals = stock_data.get('signals', {})
        signal_keys = ['RSI', 'Vol', 'MACD', 'Candle', 'Golden']
        signal_str = "/".join([f"[{'green' if signals.get(k) else 'red'}]{k[0]}[/{'green' if signals.get(k) else 'red'}]" for k in signal_keys])
        
        count = signals.get('count', 0)
        count_color = "green" if count > 0 else "white"
        count_str = f"[{count_color}]{count}[/{count_color}]"

        table.add_row(
            f"{stock_data.get('name', 'N/A')}\n[dim]{symbol}[/dim]",
            f"{stock_data.get('current_price', 0):,}",
            profit_str,
            status_str,
            stock_data.get('strategy', 'N/A'),
            signal_str,
            count_str
        )
```

### 3.2. [참고] 데이터 흐름

- `trading/db_auto_trader.py`의 `_perform_dataframe_analysis` 함수가 매 주기마다 신호 분석 결과를 계산하여 `self.signal_analysis_cache`에 저장합니다.
- `trading/db_auto_trader.py`의 `get_monitoring_status` 함수는 각 종목 정보를 반환할 때, 위 캐시에서 신호 분석 결과를 찾아 `'signals'` 키에 담아 함께 반환합니다.
- `core/db_auto_trading_handler.py`의 `_view_monitoring_status` 함수는 이 `'signals'` 데이터를 사용하여 화면의 '신호' 컬럼을 그리게 됩니다.

이 지시대로 코드를 수정하면, 사용자가 원하는 실시간 모니터링 현황판 기능이 정상적으로 구현될 것입니다.
