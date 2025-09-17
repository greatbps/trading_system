#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/core/auto_trading_handler.py

자동매매 핸들러 - 메인 시스템과 자동매매 모듈 연결
"""

import asyncio
from datetime import datetime
from utils.monitoring_display_updater import get_monitoring_updater
from utils.stock_name_resolver import get_stock_name_resolver
from utils.strategy_mapper import strategy_mapper
from utils.status_definitions import status_definitions
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from utils.logger import get_logger
from trading.auto_trader import AutoTrader
from trading.executor import TradingExecutor
from database.models import OrderType
from monitoring.monitoring_scheduler import MonitoringRemovalScheduler
from utils.stock_search import StockSearchEngine
from strategies.ai_strategy_selector import AIStrategySelector


class AutoTradingHandler:
    """자동매매 핸들러"""
    
    def __init__(self, config, kis_collector, db_manager=None, analysis_engine=None):
        self.config = config
        self.kis_collector = kis_collector
        self.db_manager = db_manager
        self.analysis_engine = analysis_engine
        self.logger = get_logger("AutoTradingHandler")
        self.console = Console()
        
        # 자동매매 시스템 초기화
        self.executor = TradingExecutor(config, kis_collector, db_manager)
        self.auto_trader = AutoTrader(config, kis_collector, self.executor, analysis_engine, db_manager) # Pass db_manager here
        
        # 감시 제거 스케줄러 (매매와 별개)
        self.removal_scheduler = MonitoringRemovalScheduler(config, kis_collector)
        
        # 종목 검색 엔진 (UX 개선)
        self.stock_search = StockSearchEngine(kis_collector)
        
        # AI 전략 선택기
        self.ai_strategy_selector = AIStrategySelector(config)
        
        # 현재 선택된 전략
        self.current_strategy_info = None
        
        # 모니터링 태스크들
        self.monitoring_task = None
        self.removal_scheduler_task = None
        
        self.logger.info("🤖 AI-강화 AutoTradingHandler 초기화 완료")

    async def initialize_systems(self):
        """
        (Compatibility stub) Initializes systems.
        In the base handler, this does nothing. The full implementation
        is in the DatabaseAutoTradingHandler.
        """
        self.logger.info("⚙️ AutoTradingHandler has no advanced systems to initialize.")
        await asyncio.sleep(0) # To make it an awaitable coroutine
    
    async def handle_auto_trading_menu(self) -> None:
        """자동매매 메뉴 처리"""
        while True:
            try:
                self._display_auto_trading_menu()
                choice = input("\n🤖 선택하세요 (0-11): ").strip()
                
                if choice == '1':
                    await self._start_monitoring()
                elif choice == '2':
                    await self._stop_monitoring()
                elif choice == '3':
                    await self._add_buy_recommendation()
                elif choice == '4':
                    await self._remove_monitoring()
                elif choice == '5':
                    await self._view_monitoring_status()
                elif choice == '6':
                    await self._configure_trading_settings()
                elif choice == '7':
                    await self._manual_trade()
                elif choice == '8':
                    await self._start_removal_scheduler()
                elif choice == '9':
                    await self._stop_removal_scheduler()
                elif choice == '10':
                    await self._view_removal_scheduler_status()
                elif choice == '11':
                    await self._manage_monitoring_stocks()
                elif choice == '0':
                    break
                else:
                    self.console.print("❌ 잘못된 선택입니다. 다시 선택해주세요.")
                    
            except KeyboardInterrupt:
                self.console.print("\n\n🛑 자동매매 메뉴를 종료합니다...")
                break
            except Exception as e:
                self.logger.error(f"❌ 자동매매 메뉴 처리 오류: {e}")
                self.console.print(f"❌ 오류가 발생했습니다: {e}")
    
    def _display_auto_trading_menu(self):
        """자동매매 메뉴 표시"""
        status = "🟢 실행중" if self.auto_trader.is_monitoring else "🔴 중지"
        trading_mode = "🟢 활성화" if self.executor.is_trading_enabled() else "🔴 비활성화"
        monitoring_count = len(self.auto_trader.monitoring_stocks)
        
        # 감시 제거 스케줄러 상태
        removal_status = "🟢 실행중" if self.removal_scheduler.is_running else "🔴 중지"
        
        self.console.print(Panel("[bold blue]🤖 자동매매 & 감시 관리 시스템[/bold blue]", border_style="blue"))
        self.console.print(f"📊 매매 모니터링: {'[green]🟢 실행중[/green]' if self.auto_trader.is_monitoring else '[red]🔴 중지[/red]'}")
        self.console.print(f"💰 매매 모드: {'[green]🟢 활성화[/green]' if self.executor.is_trading_enabled() else '[red]🔴 비활성화[/red]'}")
        self.console.print(f"📋 모니터링 종목: [yellow]{len(self.auto_trader.monitoring_stocks)}[/yellow]개")
        self.console.print(f"🕐 감시 제거 스케줄러: {'[green]🟢 실행중[/green]' if self.removal_scheduler.is_running else '[red]🔴 중지[/red]'} (30분 간격)")
        self.console.print("="*80)
        self.console.print("📈 [bold green]매매 모니터링 (실시간)[/bold green]")
        self.console.print("1. 📍 자동매매 모니터링 시작")
        self.console.print("2. 🛑 자동매매 모니터링 중지")
        self.console.print("3. ➕ Buy 추천 종목 추가")
        self.console.print("4. ➖ 모니터링 종목 제거")
        self.console.print("5. 📊 모니터링 상태 조회")
        self.console.print("6. ⚙️  매매 설정 변경")
        self.console.print("7. 타겟 수동 매매 실행")
        self.console.print("")
        self.console.print("🕐 [bold yellow]감시 제거 스케줄러 (30분 간격)[/bold yellow]")
        self.console.print("8. 🚀 감시 제거 스케줄러 시작")
        self.console.print("9. 🛑 감시 제거 스케줄러 중지")
        self.console.print("10. 📊 감시 제거 스케줄러 상태")
        self.console.print("11. 📋 감시 종목 관리 (추가/제거)")
        self.console.print("")
        self.console.print("0. 🔙 메인 메뉴로 돌아가기")
        self.console.print("="*80)
    
    async def _start_monitoring(self):
        """자동매매 모니터링 시작"""
        try:
            if self.auto_trader.is_monitoring:
                self.console.print("⚠️ 이미 모니터링이 실행 중입니다.")
                return
            
            self.console.print("🚀 자동매매 모니터링을 시작합니다...")
            self.console.print("💡 중지하려면 '2. 모니터링 중지'를 선택하세요.")
            
            # 백그라운드에서 모니터링 시작
            self.monitoring_task = asyncio.create_task(self.auto_trader.start_monitoring())
            
            # 잠깐 기다린 후 상태 확인
            await asyncio.sleep(1)
            if self.auto_trader.is_monitoring:
                self.console.print("✅ 자동매매 모니터링이 시작되었습니다.")
            else:
                self.console.print("❌ 모니터링 시작에 실패했습니다.")
                
        except Exception as e:
            self.logger.error(f"❌ 모니터링 시작 실패: {e}")
            self.console.print(f"❌ 모니터링 시작 실패: {e}")
    
    async def _stop_monitoring(self):
        """자동매매 모니터링 중지"""
        try:
            if not self.auto_trader.is_monitoring:
                self.console.print("⚠️ 현재 모니터링이 실행되지 않고 있습니다.")
                return
            
            self.console.print("🛑 자동매매 모니터링을 중지합니다...")
            
            await self.auto_trader.stop_monitoring()
            
            # 모니터링 태스크 취소
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            self.console.print("✅ 자동매매 모니터링이 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 중지 실패: {e}")
            self.console.print(f"❌ 모니터링 중지 실패: {e}")
    
    async def _add_buy_recommendation(self):
        """Buy 추천 종목 추가 (개선된 UX)"""
        try:
            self.console.print("\n📋 Buy 추천 종목 추가")
            self.console.print("-" * 50)
            self.console.print("💡 종목 코드(6자리) 또는 종목명을 입력하세요")
            self.console.print("   예: 005930, 삼성전자, 네이버, SK하이닉스")
            
            # 종목 검색 입력
            query = input("🔍 종목 코드 또는 종목명: ").strip()
            if not query:
                self.console.print("❌ 검색어를 입력해주세요.")
                return
            
            self.console.print("🔍 종목 검색 중...")
            stock_result = await self.stock_search.interactive_stock_selection(query)
            
            if not stock_result:
                self.console.print("❌ 종목을 찾을 수 없거나 선택이 취소되었습니다.")
                return
            
            symbol, name = stock_result
            
            # 전략명 입력
            strategy = input("타겟 전략명 (예: momentum, breakout): ").strip()
            if not strategy:
                strategy = "manual"
            
            # 목표가 입력 (선택사항)
            target_input = input("💰 목표가 (선택사항, Enter로 스킵): ").strip()
            target_price = None
            if target_input:
                try:
                    target_price = int(target_input)
                except ValueError:
                    self.console.print("⚠️ 목표가는 숫자로 입력해주세요. 기본값으로 진행합니다.")
            
            # 종목 추가
            success = await self.auto_trader.add_buy_recommendation(
                symbol=symbol,
                name=name,
                strategy_name=strategy,
                target_price=target_price
            )
            
            if success:
                self.console.print(f"✅ {symbol}({name})을 모니터링 리스트에 추가했습니다.")
                self.console.print(f"   전략: {strategy}")
                if target_price:
                    self.console.print(f"   목표가: {target_price:,}원")
            else:
                self.console.print("❌ 종목 추가에 실패했습니다.")
                
        except Exception as e:
            self.logger.error(f"❌ 종목 추가 실패: {e}")
            self.console.print(f"❌ 종목 추가 실패: {e}")
    
    async def _remove_monitoring(self):
        """모니터링 종목 제거"""
        try:
            if not self.auto_trader.monitoring_stocks:
                self.console.print("⚠️ 모니터링 중인 종목이 없습니다.")
                return
            
            self.console.print("\n[bold]📋 현재 모니터링 중인 종목:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("번호", style="cyan", width=5)
            table.add_column("종목명 (코드)", style="green", min_width=20)
            table.add_column("전략", style="white", min_width=10)
            table.add_column("상태", style="yellow", min_width=8)
            
            for i, (symbol, stock) in enumerate(self.auto_trader.monitoring_stocks.items(), 1):
                status_text = "[green]🟢 활성[/green]" if stock.monitoring_active else "[red]🔴 비활성[/red]"
                display_name = f"{stock.name} ([dim]{symbol}[/dim])"
                table.add_row(str(i), display_name, stock.strategy_name, status_text)
            
            self.console.print(table)
            
            choice = input("제거할 종목 번호를 입력하세요 (취소: Enter): ").strip()
            
            if not choice:
                return
            
            try:
                choice_num = int(choice)
                symbols = list(self.auto_trader.monitoring_stocks.keys())
                
                if 1 <= choice_num <= len(symbols):
                    symbol = symbols[choice_num - 1]
                    success = await self.auto_trader.remove_monitoring(symbol)
                    
                    if success:
                        self.console.print(f"[green]✅ {symbol} 종목을 모니터링에서 제거했습니다.[/green]")
                    else:
                        self.console.print("[red]❌ 종목 제거에 실패했습니다.[/red]")
                else:
                    self.console.print("[red]❌ 잘못된 번호입니다.[/red]")
                    
            except ValueError:
                self.console.print("[red]❌ 숫자를 입력해주세요.[/red]")
                
        except Exception as e:
            self.logger.error(f"❌ 종목 제거 실패: {e}")
            self.console.print(f"[red]❌ 종목 제거 실패: {e}[/red]")
    
    async def _view_monitoring_status(self):
        """모니터링 상태 조회 - Rich 컴포넌트 스타일 (DB 기반)"""
        try:
            # DB에서 직접 모니터링 종목 조회
            from database.models import MonitoringStock, MonitoringStatus, MonitoringType
            from database.database_manager import DatabaseManager
            from config import Config
            
            config = Config()
            db_manager = DatabaseManager(config)
            
            with db_manager.get_session() as session:
                # 매매 모니터링 종목들 - 직접 쿼리 사용
                db_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.monitoring_active == True,
                    MonitoringStock.monitoring_type == MonitoringType.TRADING.value
                ).order_by(MonitoringStock.recommendation_time.asc()).all()
                
                # 세션 내에서 필요한 데이터를 딕셔너리로 변환 (세션 바인딩 문제 해결)
                trading_stocks = []
                for stock in db_stocks:
                    stock_data = {
                        'name': stock.name,
                        'symbol': stock.symbol,
                        'strategy_name': stock.strategy_name,
                        'current_price': stock.current_price,
                        'target_price': stock.target_price,
                        'stop_loss_price': stock.stop_loss_price,
                        'monitoring_active': stock.monitoring_active,
                        'recommendation_time': stock.recommendation_time
                    }
                    trading_stocks.append(stock_data)
                
                self.logger.info(f"📊 모니터링 종목 조회 (auto_trading_handler): {len(trading_stocks)}개 종목 발견")
                
            # 보유 종목 정보 조회 (타임아웃 및 재시도 로직 추가)
            holdings = {}
            try:
                self.logger.info("💰 보유 종목 잔고 조회 중...")
                
                # 타임아웃 방지 - 10초 제한
                holdings_task = asyncio.create_task(self.kis_collector.get_holdings())
                try:
                    holdings = await asyncio.wait_for(holdings_task, timeout=10.0) or {}
                    
                    if holdings:
                        self.logger.info(f"✅ 보유 종목 {len(holdings)}개 조회됨")
                        for symbol, info in list(holdings.items())[:3]:  # 처음 3개만 로그
                            self.logger.info(f"  - {symbol}: {info.get('name', 'N/A')} {info.get('quantity', 0)}주 @ {info.get('avg_price', 0):,}원")
                    else:
                        self.logger.info("ℹ️ 보유 종목이 없거나 조회 실패")
                except asyncio.TimeoutError:
                    self.logger.warning("⚠️ 보유 종목 조회 타임아웃 (10초) - 스킵하고 계속 진행")
                    holdings_task.cancel()  # 태스크 취소
                    holdings = {}
                    
            except Exception as e:
                self.logger.warning(f"⚠️ 보유 종목 조회 실패: {e}")
                holdings = {}
                
            # 기본 상태 정보
            status = await self.auto_trader.get_monitoring_status()
            
            # 메인 헤더 패널
            header_text = Text()
            header_text.append("📊 자동매매 모니터링 상태", style="bold blue")
            header_panel = Panel(header_text, border_style="blue", expand=False)
            self.console.print(header_panel)
            
            # 시스템 상태 정보 패널
            status_text = Text()
            
            # 모니터링 상태
            if status['is_monitoring']:
                status_text.append("🔍 모니터링 상태: ", style="white")
                status_text.append("🟢 실행중", style="bold green")
            else:
                status_text.append("🔍 모니터링 상태: ", style="white")
                status_text.append("🔴 중지", style="bold red")
            status_text.append("\n")
            
            # 매매 모드
            if status['trading_enabled']:
                status_text.append("💰 매매 모드: ", style="white")
                status_text.append("🟢 활성화", style="bold green")
            else:
                status_text.append("💰 매매 모드: ", style="white")
                status_text.append("🔴 비활성화", style="bold red")
            status_text.append("\n")
            
            # 종목 수 정보 (DB 기반)
            total_count = len(trading_stocks)
            active_count = sum(1 for s in trading_stocks if s['monitoring_active'])
            
            status_text.append("📋 전체 종목 수: ", style="white")
            status_text.append(f"{total_count}", style="bold yellow")
            status_text.append("개\n")
            
            status_text.append("📈 활성 종목 수: ", style="white")
            status_text.append(f"{active_count}", style="bold green")
            status_text.append("개")
            
            status_panel = Panel(status_text, title="[bold cyan]시스템 상태[/bold cyan]", 
                               border_style="cyan", expand=False, padding=(1, 2))
            self.console.print(status_panel)
            
            # 모니터링 종목 테이블 (DB 기반)
            if trading_stocks:
                table = Table(show_header=True, header_style="bold magenta", 
                            title="[bold]📋 모니터링 중인 종목 목록[/bold]", 
                            title_style="bold white", border_style="magenta")
                
                table.add_column("종목명", style="cyan", min_width=12, no_wrap=True)
                table.add_column("전략", style="green", min_width=15)
                table.add_column("현재가", style="white", justify="right", min_width=10)
                table.add_column("매수가", style="yellow", justify="right", min_width=10)
                table.add_column("수량", style="bright_yellow", justify="right", min_width=8)
                table.add_column("수익률", justify="right", min_width=10)
                table.add_column("손절가", style="purple", justify="right", min_width=10)
                table.add_column("등록일", style="dim", min_width=12)
                
                for stock in trading_stocks:
                    # 딕셔너리 기반 데이터 사용 (세션 바인딩 문제 해결)
                    display_name = stock['name']  # 종목명만 표시
                    
                    # 매수가, 수량, 수익률 계산
                    buy_price = None
                    quantity = None
                    profit_rate = None
                    
                    # 1. 먼저 실제 보유종목에서 확인 (해당 종목만)
                    if stock['symbol'] in holdings:
                        holding_info = holdings[stock['symbol']]
                        avg_price = holding_info.get('avg_price', 0)
                        qty = holding_info.get('quantity', 0)
                        real_time_price = holding_info.get('current_price', 0)  # HTS에서 가져온 실시간 현재가
                        
                        if avg_price > 0:
                            buy_price = avg_price
                            quantity = qty
                            
                            # 실시간 현재가로 수익률 계산 (HTS 잔고의 실시간 가격 사용)
                            if real_time_price and buy_price:
                                profit_rate = ((real_time_price - buy_price) / buy_price) * 100
                                # 모니터링 테이블의 현재가도 업데이트 (실시간 반영)
                                stock['current_price'] = real_time_price
                    else:
                        # 2. 보유종목에 없으면 모든 값을 None으로 설정
                        buy_price = None
                        quantity = None
                        profit_rate = None
                    
                    # 현재가 포매팅
                    current_price = f"{stock['current_price']:,}원" if stock['current_price'] else '[dim]N/A[/dim]'
                    
                    # 매수가 포매팅 (실제 매수한 경우만 표시)
                    if buy_price and quantity and quantity > 0:
                        buy_price_display = f"{int(buy_price):,}원"
                    else:
                        buy_price_display = ""
                    
                    # 수량 포매팅 (실제 보유한 경우만 표시)
                    if quantity and quantity > 0:
                        quantity_display = f"{quantity:,}주"
                    else:
                        quantity_display = ""
                    
                    # 수익률 포매팅 (실제 보유한 경우만 표시)
                    if profit_rate is not None and quantity and quantity > 0:
                        if profit_rate >= 5.0:
                            profit_rate_display = f"[bold green]▲{profit_rate:.2f}%[/bold green]"
                        elif profit_rate > 0:
                            profit_rate_display = f"[green]▲{profit_rate:.2f}%[/green]"
                        elif profit_rate <= -5.0:
                            profit_rate_display = f"[bold red]▼{abs(profit_rate):.2f}%[/bold red]"
                        else:
                            profit_rate_display = f"[red]▼{abs(profit_rate):.2f}%[/red]"
                    else:
                        profit_rate_display = ""
                    
                    # 손절가: 실제 보유한 경우만 표시
                    if buy_price and buy_price > 0 and quantity and quantity > 0:
                        if stock['stop_loss_price'] and stock['stop_loss_price'] > 0:
                            stop_loss_price = f"{stock['stop_loss_price']:,}원"
                        else:
                            auto_stop_loss = int(buy_price * 0.95)  # -5%
                            stop_loss_price = f"[dim]{auto_stop_loss:,}원[/dim]"
                    else:
                        stop_loss_price = ""
                    
                    # 등록일 포매팅
                    reg_date = stock['recommendation_time'].strftime('%m-%d %H:%M') if stock['recommendation_time'] else 'N/A'

                    table.add_row(
                        display_name,
                        stock['strategy_name'],
                        current_price,
                        buy_price_display,
                        quantity_display,
                        profit_rate_display,
                        stop_loss_price,
                        reg_date
                    )
                
                # 테이블을 패널로 감싸기
                table_panel = Panel(table, border_style="magenta", expand=True)
                self.console.print(table_panel)
                
            else:
                # 빈 상태 메시지 패널
                empty_text = Text()
                empty_text.append("⚠️ 현재 모니터링 중인 종목이 없습니다.", style="bold yellow")
                empty_text.append("\n\n💡 ", style="white")
                empty_text.append("'3. Buy 추천 종목 추가'", style="bold cyan")
                empty_text.append("를 선택하여 종목을 추가해보세요.", style="white")
                
                empty_panel = Panel(empty_text, title="[bold yellow]모니터링 종목[/bold yellow]", 
                                  border_style="yellow", expand=False, padding=(1, 2))
                self.console.print(empty_panel)
            
            # 푸터 패널
            footer_text = Text()
            footer_text.append("🔄 ", style="white")
            footer_text.append("실시간 모니터링", style="bold blue")
            if status['is_monitoring']:
                footer_text.append(" 중", style="bold green")
            else:
                footer_text.append(" 중지됨", style="bold red")
                
            footer_panel = Panel(footer_text, border_style="blue", expand=False)
            self.console.print(footer_panel)
            
        except Exception as e:
            self.logger.error(f"❌ 상태 조회 실패: {e}")
            
            # 에러 패널
            error_text = Text()
            error_text.append("❌ 상태 조회 실패: ", style="bold red")
            error_text.append(str(e), style="red")
            
            error_panel = Panel(error_text, title="[bold red]오류[/bold red]", 
                              border_style="red", expand=False)
            self.console.print(error_panel)
    
    async def _configure_trading_settings(self):
        """매매 설정 변경"""
        try:
            self.console.print("\n⚙️ 매매 설정")
            self.console.print("-" * 50)
            self.console.print(f"현재 설정:")
            self.console.print(f"  📊 최대 포지션 수: {self.auto_trader.max_positions}개")
            self.console.print(f"  💰 포지션 크기: {self.auto_trader.position_size:,}원")
            self.console.print(f"  📉 손절 비율: {self.auto_trader.stop_loss_pct*100:.1f}%")
            self.console.print(f"  📈 익절 비율: {self.auto_trader.take_profit_pct*100:.1f}%")
            self.console.print(f"  💰 매매 모드: {'🟢 활성화' if self.executor.is_trading_enabled() else '🔴 비활성화'}")
            self.console.print("-" * 50)
            
            self.console.print("\n변경할 설정을 선택하세요:")
            self.console.print("1. 매매 모드 토글 (활성화/비활성화)")
            self.console.print("2. 포지션 크기 변경")
            self.console.print("3. 손절/익절 비율 변경")
            self.console.print("4. 돌아가기")
            
            choice = input("선택 (1-4): ").strip()
            
            if choice == '1':
                if self.executor.is_trading_enabled():
                    self.executor.disable_trading()
                    self.console.print("🔴 매매 모드를 비활성화했습니다.")
                else:
                    confirm = input("⚠️ 실제 매매가 실행됩니다. 계속하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        self.executor.enable_trading()
                        self.console.print("🟢 매매 모드를 활성화했습니다.")
                    else:
                        self.console.print("매매 모드 변경을 취소했습니다.")
                        
            elif choice == '2':
                try:
                    new_size = input(f"새로운 포지션 크기 (현재: {self.auto_trader.position_size:,}원): ").strip()
                    if new_size:
                        self.auto_trader.position_size = int(new_size)
                        self.console.print(f"✅ 포지션 크기를 {self.auto_trader.position_size:,}원으로 변경했습니다.")
                except ValueError:
                    self.console.print("❌ 숫자를 입력해주세요.")
                    
            elif choice == '3':
                try:
                    stop_loss = input(f"손절 비율 % (현재: {self.auto_trader.stop_loss_pct*100:.1f}%): ").strip()
                    if stop_loss:
                        self.auto_trader.stop_loss_pct = float(stop_loss) / 100
                        
                    take_profit = input(f"익절 비율 % (현재: {self.auto_trader.take_profit_pct*100:.1f}%): ").strip()
                    if take_profit:
                        self.auto_trader.take_profit_pct = float(take_profit) / 100
                        
                    self.console.print("✅ 손익 비율을 변경했습니다.")
                except ValueError:
                    self.console.print("❌ 숫자를 입력해주세요.")
                    
        except Exception as e:
            self.logger.error(f"❌ 설정 변경 실패: {e}")
            self.console.print(f"[red]❌ 설정 변경 실패: {e}[/red]")
    
    async def _manual_trade(self):
        """수동 매매 실행"""
        try:
            self.console.print("\n타겟 수동 매매 실행")
            self.console.print("-" * 50)
            self.console.print("1. 📈 매수 주문")
            self.console.print("2. 📉 매도 주문")
            self.console.print("3. 📊 계좌 잔고 조회")
            self.console.print("4. 📋 보유 종목 조회")
            self.console.print("5. 돌아가기")
            
            choice = input("선택 (1-5): ").strip()
            
            if choice == '1':
                await self._execute_manual_buy()
            elif choice == '2':
                await self._execute_manual_sell()
            elif choice == '3':
                await self._view_account_balance()
            elif choice == '4':
                await self._view_holdings()
                
        except Exception as e:
            self.logger.error(f"❌ 수동 매매 실패: {e}")
            self.console.print(f"[red]❌ 수동 매매 실패: {e}[/red]")
    
    async def _execute_manual_buy(self):
        """수동 매수 실행"""
        try:
            symbol = input("종목 코드 (6자리): ").strip()
            if not symbol or len(symbol) != 6:
                self.console.print("❌ 올바른 종목 코드를 입력해주세요.")
                return
                
            quantity = int(input("매수 수량: ").strip())
            price = input("매수 가격 (시장가: Enter): ").strip()
            
            price_val = int(price) if price else None
            order_type = OrderType.LIMIT if price_val else OrderType.MARKET
            
            self.console.print(f"📈 매수 주문: {symbol} {quantity}주 @ {price_val or '시장가'}")
            confirm = input("주문을 실행하시겠습니까? (y/N): ").strip().lower()
            
            if confirm == 'y':
                result = await self.executor.execute_buy_order(symbol, quantity, price_val, order_type)
                
                if result['success']:
                    self.console.print(f"✅ 매수 주문 성공!")
                    self.console.print(f"   주문 ID: {result.get('order_id')}")
                    if result.get('simulation'):
                        self.console.print("   (시뮬레이션 모드)")
                else:
                    self.console.print(f"❌ 매수 주문 실패: {result.get('error')}")
            
        except ValueError:
            self.console.print("❌ 숫자를 정확히 입력해주세요.")
        except Exception as e:
            self.console.print(f"❌ 매수 실행 실패: {e}")
    
    async def _execute_manual_sell(self):
        """수동 매도 실행"""
        try:
            symbol = input("종목 코드 (6자리): ").strip()
            if not symbol or len(symbol) != 6:
                self.console.print("❌ 올바른 종목 코드를 입력해주세요.")
                return
                
            quantity = int(input("매도 수량: ").strip())
            price = input("매도 가격 (시장가: Enter): ").strip()
            
            price_val = int(price) if price else None
            order_type = OrderType.LIMIT if price_val else OrderType.MARKET
            
            self.console.print(f"📉 매도 주문: {symbol} {quantity}주 @ {price_val or '시장가'}")
            confirm = input("주문을 실행하시겠습니까? (y/N): ").strip().lower()
            
            if confirm == 'y':
                result = await self.executor.execute_sell_order(symbol, quantity, price_val, order_type)
                
                if result['success']:
                    self.console.print(f"✅ 매도 주문 성공!")
                    self.console.print(f"   주문 ID: {result.get('order_id')}")
                    if result.get('simulation'):
                        self.console.print("   (시뮬레이션 모드)")
                else:
                    self.console.print(f"❌ 매도 주문 실패: {result.get('error')}")
            
        except ValueError:
            self.console.print("❌ 숫자를 정확히 입력해주세요.")
        except Exception as e:
            self.console.print(f"❌ 매도 실행 실패: {e}")
    
    async def _view_account_balance(self):
        """계좌 잔고 조회"""
        try:
            self.console.print("💰 계좌 잔고 조회 중...")
            
            balance = await self.kis_collector.get_account_balance()
            
            self.console.print("\n💰 계좌 잔고 정보")
            self.console.print("-" * 30)
            self.console.print(f"예수금: {balance.get('available_cash', 0):,}원")
            self.console.print(f"총 평가금액: {balance.get('total_evaluation', 0):,}원")
            
        except Exception as e:
            self.console.print(f"❌ 계좌 잔고 조회 실패: {e}")
    
    async def _view_holdings(self):
        """보유 종목 조회"""
        try:
            self.console.print("📋 보유 종목 조회 중...")
            
            # 타임아웃 방지 - 10초 제한
            holdings_task = asyncio.create_task(self.kis_collector.get_holdings())
            try:
                holdings = await asyncio.wait_for(holdings_task, timeout=10.0)
            except asyncio.TimeoutError:
                self.console.print("⚠️ 보유 종목 조회 타임아웃 (10초)")
                holdings_task.cancel()
                return
            
            if holdings:
                self.console.print("\n📋 보유 종목 정보")
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("종목코드", style="cyan", min_width=10)
                table.add_column("수량", style="green", justify="right", min_width=8)
                table.add_column("평균단가", style="yellow", justify="right", min_width=12)
                table.add_column("현재가", style="white", justify="right", min_width=12)
                table.add_column("평가금액", style="blue", justify="right", min_width=12)
                
                for symbol, info in holdings.items():
                    self.console.print(f"{symbol:<8} {info['quantity']:<8} {info['avg_price']:,}원{'':<3} "
                          f"{info['current_price']:,}원{'':<3} {info['evaluation']:,}원")
            else:
                self.console.print("⚠️ 보유 중인 종목이 없습니다.")
                
        except Exception as e:
            self.console.print(f"❌ 보유 종목 조회 실패: {e}")
    
    async def cleanup(self):
        """자동매매 핸들러 정리"""
        try:
            from rich.console import Console
            console = Console()

            # 모니터링 중지
            if self.auto_trader.is_monitoring:
                await self.auto_trader.stop_monitoring()
            
            # 모니터링 태스크 취소
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # 감시 제거 스케줄러 중지
            if self.removal_scheduler.is_running:
                await self.removal_scheduler.stop_scheduler()
            
            # 감시 제거 스케줄러 태스크 취소
            if self.removal_scheduler_task and not self.removal_scheduler_task.done():
                self.removal_scheduler_task.cancel()
                try:
                    await self.removal_scheduler_task
                except asyncio.CancelledError:
                    pass
            
            # 모니터링 상태 저장
            await self.auto_trader.save_monitoring_state("data/auto_trading_state.json")
            
            self.logger.info("🧹 AutoTradingHandler 정리 완료")
            self.console.print("[green]🧹 AutoTradingHandler 정리 완료[/green]")
            
        except Exception as e:
            self.logger.error(f"❌ AutoTradingHandler 정리 실패: {e}")
            self.console.print(f"[red]❌ AutoTradingHandler 정리 실패: {e}[/red]")
    
    # === 감시 제거 스케줄러 메서드들 ===
    
    async def _start_removal_scheduler(self):
        """감시 제거 스케줄러 시작 (30분 간격)"""
        try:
            if self.removal_scheduler.is_running:
                self.console.print("⚠️ 감시 제거 스케줄러가 이미 실행 중입니다.")
                return
            
            self.console.print("🚀 감시 제거 스케줄러를 시작합니다...")
            self.console.print("💡 30분마다 종합 점수를 평가하여 Buy 신호가 사라진 종목을 자동 제거합니다.")
            self.console.print("💡 중지하려면 '9. 감시 제거 스케줄러 중지'를 선택하세요.")
            
            # 백그라운드에서 스케줄러 시작
            self.removal_scheduler_task = asyncio.create_task(self.removal_scheduler.start_scheduler())
            
            # 잠깐 기다린 후 상태 확인
            await asyncio.sleep(1)
            if self.removal_scheduler.is_running:
                self.console.print("✅ 감시 제거 스케줄러가 시작되었습니다.")
                self.console.print(f"   📊 30분마다 {self.removal_scheduler.removal_threshold}점 이하 종목을 자동 제거합니다.")
            else:
                self.console.print("❌ 스케줄러 시작에 실패했습니다.")
                
        except Exception as e:
            self.logger.error(f"❌ 감시 제거 스케줄러 시작 실패: {e}")
            self.console.print(f"❌ 스케줄러 시작 실패: {e}")
    
    async def _stop_removal_scheduler(self):
        """감시 제거 스케줄러 중지"""
        try:
            if not self.removal_scheduler.is_running:
                self.console.print("⚠️ 현재 감시 제거 스케줄러가 실행되지 않고 있습니다.")
                return
            
            self.console.print("🛑 감시 제거 스케줄러를 중지합니다...")
            
            await self.removal_scheduler.stop_scheduler()
            
            # 스케줄러 태스크 취소
            if self.removal_scheduler_task and not self.removal_scheduler_task.done():
                self.removal_scheduler_task.cancel()
                try:
                    await self.removal_scheduler_task
                except asyncio.CancelledError:
                    pass
            
            self.console.print("✅ 감시 제거 스케줄러가 중지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"❌ 감시 제거 스케줄러 중지 실패: {e}")
            self.console.print(f"❌ 스케줄러 중지 실패: {e}")
    
    async def _view_removal_scheduler_status(self):
        """감시 제거 스케줄러 상태 조회"""
        try:
            self.console.print("\n📊 감시 제거 스케줄러 상태")
            self.console.print("=" * 70)
            
            status = self.removal_scheduler.get_monitoring_status()
            
            self.console.print(f"🕐 스케줄러 상태: {'🟢 실행중' if status['scheduler_running'] else '🔴 중지'}")
            self.console.print(f"시간 체크 간격: {status.get('check_interval_minutes', 30)}분")
            self.console.print(f"📊 제거 임계점: {status.get('removal_threshold', 40)}점")
            self.console.print(f"📋 전체 감시 종목: {status.get('total_stocks', 0)}개")
            self.console.print(f"📈 활성 감시 종목: {status.get('active_stocks', 0)}개")
            self.console.print(f"🗑️ 제거된 종목: {status.get('removed_stocks', 0)}개")
            if status.get('avg_score'):
                self.console.print(f"📊 평균 점수: {status['avg_score']:.1f}점")
            
            # 최근 24시간 내 제거된 종목들
            if status.get('recent_removals_24h', 0) > 0:
                self.console.print(f"\n🗑️ 최근 24시간 내 제거된 종목: {status['recent_removals_24h']}개")
                self.console.print("-" * 70)
                self.console.print(f"{'종목코드':<8} {'종목명':<15} {'제거시간':<20} {'최종점수':<8} {'제거사유'}")
                self.console.print("-" * 70)
                
                for removed in status.get('recent_removed_stocks', []):
                    removed_time = removed['removed_at'][:16].replace('T', ' ')  # YYYY-MM-DD HH:MM
                    last_score = f"{removed['last_score']:.1f}점" if removed['last_score'] else "N/A"
                    reason = removed['removal_reason'] or "Unknown"
                    
                    self.console.print(f"{removed['symbol']:<8} {removed['name']:<15} {removed_time:<20} "
                          f"{last_score:<8} {reason}")
            else:
                self.console.print("\n✅ 최근 24시간 내 제거된 종목이 없습니다.")
            
            self.console.print("=" * 70)
            
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 상태 조회 실패: {e}")
            self.console.print(f"❌ 상태 조회 실패: {e}")
    
    async def _manage_monitoring_stocks(self):
        """감시 종목 관리 (DB 기반)"""
        try:
            self.console.print("\n📋 감시 종목 관리 (데이터베이스)")
            self.console.print("=" * 50)
            self.console.print("1. 새 감시 종목 추가")
            self.console.print("2. 감시 종목 수동 제거")
            self.console.print("3. 감시 종목 목록 조회")
            self.console.print("4. 돌아가기")
            
            choice = input("선택 (1-4): ").strip()
            
            if choice == '1':
                await self._add_monitoring_stock_to_db()
            elif choice == '2':
                await self._remove_monitoring_stock_from_db()
            elif choice == '3':
                await self._list_monitoring_stocks_from_db()
                
        except Exception as e:
            self.logger.error(f"❌ 감시 종목 관리 실패: {e}")
            self.console.print(f"❌ 감시 종목 관리 실패: {e}")
    
    async def _add_monitoring_stock_to_db(self):
        """감시 종목을 DB에 추가"""
        try:
            self.console.print("\n📋 감시 종목 추가 (데이터베이스)")
            self.console.print("-" * 50)
            
            # 종목 코드 또는 종목명 입력 (개선된 UX)
            query = input("📈 종목 코드 또는 종목명 입력: ").strip()
            if not query:
                self.console.print("❌ 종목 정보를 입력해주세요.")
                return
            
            # 스마트 종목 검색
            result = await self.stock_search.interactive_stock_selection(query)
            if not result:
                self.console.print("❌ 종목 선택이 취소되었거나 찾을 수 없습니다.")
                return
            
            symbol, name = result
            
            # 전략명 입력
            strategy = input("타겟 전략명 (예: Buy 추천, 기술적분석): ").strip()
            if not strategy:
                strategy = "Buy 추천"
            
            # 포지션 크기 입력
            position_input = input(f"💰 포지션 크기 (기본: 1,000,000원): ").strip()
            position_size = 1000000
            if position_input:
                try:
                    position_size = int(position_input)
                except ValueError:
                    self.console.print("⚠️ 포지션 크기는 숫자로 입력해주세요. 기본값으로 진행합니다.")
            
            # 최소 점수 임계값
            score_input = input(f"📊 최소 점수 임계값 (기본: 40점): ").strip()
            min_score = 40.0
            if score_input:
                try:
                    min_score = float(score_input)
                except ValueError:
                    self.console.print("⚠️ 점수는 숫자로 입력해주세요. 기본값으로 진행합니다.")
            
            # DB에 감시 종목 추가
            success = await self.removal_scheduler.add_stock_to_monitoring(
                symbol=symbol,
                name=name,
                strategy_name=strategy,
                position_size=position_size,
                min_score=min_score
            )
            
            if success:
                self.console.print(f"✅ {symbol}({name})을 감시 목록에 추가했습니다.")
                self.console.print(f"   전략: {strategy}")
                self.console.print(f"   포지션 크기: {position_size:,}원")
                self.console.print(f"   최소 점수: {min_score}점")
                self.console.print("💡 30분마다 자동으로 점수가 평가됩니다.")
            else:
                self.console.print("❌ 감시 종목 추가에 실패했습니다.")
                
        except Exception as e:
            self.logger.error(f"❌ DB 감시 종목 추가 실패: {e}")
            self.console.print(f"❌ 감시 종목 추가 실패: {e}")
    
    async def _remove_monitoring_stock_from_db(self):
        """감시 종목을 DB에서 제거"""
        try:
            self.console.print("\n🗑️ 감시 종목 수동 제거")
            self.console.print("-" * 50)
            
            symbol = input("📈 제거할 종목 코드 (6자리): ").strip()
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                self.console.print("❌ 올바른 종목 코드를 입력해주세요. (6자리 숫자)")
                return
            
            # 제거 사유 입력
            reason = input("📝 제거 사유 (선택사항): ").strip()
            if not reason:
                reason = "수동 제거"
            
            # 확인
            confirm = input(f"⚠️ 정말로 {symbol} 종목을 감시에서 제거하시겠습니까? (y/N): ").strip().lower()
            if confirm != 'y':
                self.console.print("제거를 취소했습니다.")
                return
            
            # DB에서 감시 종목 제거
            success = await self.removal_scheduler.remove_stock_from_monitoring(symbol, f"manual_remove: {reason}")
            
            if success:
                self.console.print(f"✅ {symbol} 종목을 감시에서 제거했습니다.")
                self.console.print(f"   제거 사유: {reason}")
            else:
                self.console.print("❌ 감시 종목 제거에 실패했습니다. (종목이 존재하지 않거나 이미 제거되었을 수 있습니다)")
                
        except Exception as e:
            self.logger.error(f"❌ DB 감시 종목 제거 실패: {e}")
            self.console.print(f"❌ 감시 종목 제거 실패: {e}")
    
    async def _list_monitoring_stocks_from_db(self):
        """DB의 감시 종목 목록 조회"""
        try:
            self.console.print("\n📋 감시 종목 목록 (데이터베이스)")
            self.console.print("=" * 80)
            
            status = self.removal_scheduler.get_monitoring_status()
            
            if status.get('total_stocks', 0) == 0:
                self.console.print("⚠️ 등록된 감시 종목이 없습니다.")
                return
            
            self.console.print(f"전체: {status['total_stocks']}개, 활성: {status['active_stocks']}개, 제거됨: {status['removed_stocks']}개")
            self.console.print("=" * 80)
            
            # 실제 DB에서 감시 종목 목록 조회
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.removal_scheduler.engine)
            session = Session()
            
            try:
                from database.monitoring_models import MonitoringStock
                
                # 활성 감시 종목들
                active_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).order_by(MonitoringStock.recommendation_time.desc()).all()
                
                if active_stocks:
                    self.console.print("🟢 활성 감시 종목:")
                    self.console.print("-" * 80)
                    self.console.print(f"{'종목코드':<8} {'종목명':<12} {'전략':<15} {'추가일시':<16} {'최종점수':<8} {'체크횟수'}")
                    self.console.print("-" * 80)
                    
                    for stock in active_stocks:
                        added_time = stock.added_at.strftime('%m-%d %H:%M') if stock.added_at else "N/A"
                        last_score = f"{stock.last_score:.1f}" if stock.last_score else "N/A"
                        check_count = stock.check_count or 0
                        
                        # 종목명 매핑
                        stock_name_mapping = {
                            "187660": "아바이오메드", "005360": "모나미", "290550": "디케이티",
                            "023160": "현대위아", "226950": "올릭스", "059090": "KCC",
                            "011070": "LG이노텍", "223250": "영창케미칼", "090460": "비에이치",
                            "414780": "펄어비스", "108380": "대봉LS", "413630": "대한과선"
                        }
                        display_name = stock_name_mapping.get(stock.symbol, stock.name or f"종목{stock.symbol}")
                        self.console.print(f"{stock.symbol:<8} {display_name:<12} {stock.strategy_name:<15} "
                              f"{added_time:<16} {last_score:<8} {check_count}")
                else:
                    self.console.print("⚠️ 활성 감시 종목이 없습니다.")
                
                # 최근 제거된 종목들 (최대 5개)
                removed_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.REMOVED
                ).order_by(MonitoringStock.removed_at.desc()).limit(5).all()
                
                if removed_stocks:
                    self.console.print("\n🔴 최근 제거된 종목 (최대 5개):")
                    self.console.print("-" * 80)
                    self.console.print(f"{'종목코드':<8} {'종목명':<12} {'제거일시':<16} {'최종점수':<8} {'제거사유'}")
                    self.console.print("-" * 80)
                    
                    for stock in removed_stocks:
                        removed_time = stock.removed_at.strftime('%m-%d %H:%M') if stock.removed_at else "N/A"
                        last_score = f"{stock.last_score:.1f}" if stock.last_score else "N/A"
                        reason = stock.removal_reason or "Unknown"
                        
                        self.console.print(f"{stock.symbol:<8} {stock.name:<12} {removed_time:<16} "
                              f"{last_score:<8} {reason}")
                
            finally:
                session.close()
            
            self.console.print("=" * 80)
            
        except Exception as e:
            self.logger.error(f"❌ 감시 종목 목록 조회 실패: {e}")
            self.console.print(f"❌ 감시 종목 목록 조회 실패: {e}")
            
        finally:
            # 메뉴로 돌아가기 전 대기
            input("\n📍 Enter 키를 눌러 계속...")
    
    async def cleanup_systems(self):
        """시스템 정리"""
        try:
            self.logger.info("🧹 AutoTradingHandler 시스템 정리 시작")
            
            # 실행 중인 모니터링 태스크 정리
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.logger.info("⏹️ 모니터링 태스크 종료")
            
            # 감시 제거 스케줄러 태스크 정리
            if self.removal_scheduler_task and not self.removal_scheduler_task.done():
                self.removal_scheduler_task.cancel()
                try:
                    await self.removal_scheduler_task
                except asyncio.CancelledError:
                    pass
                self.logger.info("⏹️ 감시 제거 스케줄러 태스크 종료")
            
            # AutoTrader 정리
            if hasattr(self.auto_trader, 'cleanup') and callable(self.auto_trader.cleanup):
                await self.auto_trader.cleanup()
                self.logger.info("⏹️ AutoTrader 정리 완료")
            
            # RemovalScheduler 정리
            if hasattr(self.removal_scheduler, 'cleanup') and callable(self.removal_scheduler.cleanup):
                await self.removal_scheduler.cleanup()
                self.logger.info("⏹️ RemovalScheduler 정리 완료")
            
            self.logger.info("✅ AutoTradingHandler 시스템 정리 완료")
            
        except Exception as e:
            self.logger.error(f"❌ AutoTradingHandler 시스템 정리 중 오류: {e}")
            raise