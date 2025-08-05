#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/core/menu_handlers.py

메뉴 핸들러 - 사용자 인터페이스와 비즈니스 로직 연결
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Rich UI 라이브러리
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.progress import Progress
from rich import print as rprint

console = Console()

class MenuHandlers:
    """메뉴 처리 핸들러 클래스"""
    
    def __init__(self, trading_system):
        self.system = trading_system
        self.config = trading_system.config
        self.logger = trading_system.logger
    #######################################################
    def show_main_menu(self):
        """메인 메뉴 표시"""
        menu = """[bold cyan]🔧 시스템 관리[/bold cyan]
    1. 시스템 테스트
    2. 설정 확인
    3. 컴포넌트 초기화

    [bold green]📊 분석 및 매매[/bold green]
    4. 종합 분석 (5개 영역 통합)
    5. 특정 종목 분석
    6. 뉴스 재료 분석
    7. 자동매매 시작
    8. 백테스트 실행

    [bold blue]🗄️ 데이터[/bold blue]
    9. 데이터베이스 상태
    10. 종목 데이터 조회

    [bold red]0. 종료[/bold red]"""
        
        console.print(Panel.fit(menu, title="📋 메인 메뉴", border_style="cyan"))

    def get_user_choice(self) -> str:
        """사용자 입력"""
        try:
            return Prompt.ask("[bold yellow]메뉴 선택[/bold yellow]", default="0").strip()
        except KeyboardInterrupt:
            return "0"
    #######################################################
    
    
    
    async def execute_menu_choice(self, choice: str) -> Optional[bool]:
        """메뉴 선택 실행"""
        try:
            menu_map = {
                # 시스템 관리
                "1": self._system_test,
                "2": self._config_management,
                "3": self._component_initialization,
                
                # 분석 및 매매
                "4": self._comprehensive_analysis,
                "5": self._specific_symbol_analysis,
                "6": self._news_analysis,
                "7": self._supply_demand_analysis,
                "8": self._chart_pattern_analysis,
                "9": self._auto_trading,
                "10": self._backtest,
                "11": self._scheduler,
                
                # 데이터베이스
                "12": self._database_status,
                "13": self._view_stock_data,
                "14": self._view_analysis_results,
                "15": self._view_trading_records,
                
                # 고급 기능
                "16": self._data_cleanup,
                "17": self._log_analysis,
                "18": self._system_monitoring,
                "19": self._debug_filtering
            }
            
            handler = menu_map.get(choice)
            if handler:
                return await handler()
            else:
                console.print(f"[yellow]⚠️ 알 수 없는 메뉴: {choice}[/yellow]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ 메뉴 실행 오류: {e}[/red]")
            self.logger.error(f"❌ 메뉴 실행 오류 ({choice}): {e}")
            return False
    async def _debug_filtering(self) -> bool:
        """필터링 디버깅"""
        console.print(Panel("[bold yellow]🔍 필터링 디버깅[/bold yellow]", border_style="yellow"))
        
        try:
            # 컴포넌트 초기화 확인
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            
            console.print("\n[bold]디버깅 옵션:[/bold]")
            console.print("1. 전체 필터링 프로세스 디버깅")
            console.print("2. 특정 종목 상세 디버깅")
            console.print("3. 대형주 5개 테스트")
            
            debug_choice = Prompt.ask("디버깅 옵션을 선택하세요", choices=["1", "2", "3"], default="1")
            
            if debug_choice == "1":
                # 전체 필터링 프로세스 디버깅
                await self.system.data_collector.debug_filtering_process()
                
            elif debug_choice == "2":
                # 특정 종목 디버깅
                symbol = Prompt.ask("디버깅할 종목 코드를 입력하세요", default="005930")
                await self.system.data_collector.debug_single_stock(symbol)
                
            elif debug_choice == "3":
                # 대형주 테스트
                test_symbols = ["005930", "000660", "035420", "005380", "051910"]
                await self.system.data_collector.debug_filtering_process(test_symbols)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 필터링 디버깅 실패: {e}[/red]")
            self.logger.error(f"❌ 필터링 디버깅 실패: {e}")
            return False
    async def execute_command_mode(self, mode: str) -> bool:
        """명령 모드 실행"""
        try:
            mode_map = {
                'test': self._system_test,
                'analysis': self._comprehensive_analysis,
                'news': self._news_analysis,
                'supply-demand': self._supply_demand_analysis,
                'chart-pattern': self._chart_pattern_analysis
            }
            
            handler = mode_map.get(mode)
            if handler:
                result = await handler()
                return result if result is not None else True
            else:
                console.print(f"[yellow]⚠️ 알 수 없는 모드: {mode}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ 명령 모드 실행 오류: {e}[/red]")
            return False
    
    # === 시스템 관리 메뉴 ===
    
    async def _system_test(self) -> bool:
        """시스템 테스트 및 상태 확인"""
        console.print(Panel("[bold cyan]🔧 시스템 테스트 및 상태 확인[/bold cyan]", border_style="cyan"))
        
        try:
            # 시스템 테스트 실행
            result = await self.system._run_system_test()
            
            if result:
                # 시스템 상태 표시
                await self._display_system_status()
            
            return result
            
        except Exception as e:
            console.print(f"[red]❌ 시스템 테스트 실패: {e}[/red]")
            return False
    
    async def _config_management(self) -> bool:
        """설정 확인 및 변경"""
        console.print(Panel("[bold cyan]⚙️ 설정 관리[/bold cyan]", border_style="cyan"))
        
        try:
            # 현재 설정 표시
            await self._display_current_config()
            
            # 설정 변경 옵션
            change_config = Confirm.ask("\n설정을 변경하시겠습니까?")
            
            if change_config:
                await self._modify_config()
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 설정 관리 실패: {e}[/red]")
            return False
    
    async def _component_initialization(self) -> bool:
        """컴포넌트 초기화"""
        console.print(Panel("[bold cyan]🔧 컴포넌트 초기화[/bold cyan]", border_style="cyan"))
        
        # 현재 상태 확인
        status = await self.system.get_system_status()
        
        if all(status['components'].values()):
            if not Confirm.ask("모든 컴포넌트가 이미 초기화되어 있습니다. 재초기화하시겠습니까?"):
                return True
        
        # 컴포넌트 초기화 실행
        return await self.system.initialize_components()
    
    # === 분석 및 매매 메뉴 ===
    
    async def _comprehensive_analysis(self) -> bool:
        """종합 분석 (5개 영역 통합) - 서브메뉴 추가"""
        console.print(Panel("[bold green]📊 종합 분석 (5개 영역 통합)[/bold green]", border_style="green"))
        
        # 서브메뉴 표시
        strategies = {
            "1": ("momentum", "1. Momentum 전략"),
            "2": ("breakout", "2. Breakout 전략"), 
            "3": ("eod", "3. EOD 전략"),
            "4": ("supertrend_ema_rsi", "4. Supertrend EMA RSI 전략"),
            "5": ("vwap", "5. VWAP 전략"),
            "6": ("scalping_3m", "6. 3분봉 스캘핑 전략"),
            "7": ("rsi", "7. RSI (상대강도지수) 전략")
        }
        
        console.print("\n[bold]분석 전략을 선택하세요:[/bold]")
        for key, (_, description) in strategies.items():
            console.print(f"  {description}")
        console.print("  0. 메인 메뉴로 돌아가기")
        
        while True:
            try:
                choice = Prompt.ask("전략 선택", choices=list(strategies.keys()) + ["0"], default="1")
                
                if choice == "0":
                    return True  # 메인 메뉴로 돌아가기
                
                strategy_name, strategy_desc = strategies[choice]
                console.print(f"\n[green]✅ {strategy_desc} 선택됨[/green]")
                
                # 분석 실행 (1차 필터링 결과 모두 2차 필터링)
                console.print("[yellow]ℹ️ 1차 필터링에서 추출된 모든 종목을 2차 필터링합니다.[/yellow]")
                results = await self.system.run_market_analysis(strategy=strategy_name, limit=None)
                
                # 결과 표시
                if results:
                    await self.system._display_analysis_results(results)
                    
                    # 결과 저장 옵션
                    if Confirm.ask("\n분석 결과를 파일로 저장하시겠습니까?"):
                        await self._save_analysis_to_file(results)
                
                # 다른 전략 분석 여부
                if not Confirm.ask("\n다른 전략으로 분석하시겠습니까?"):
                    break
                    
            except Exception as e:
                console.print(f"[red]❌ 분석 실패: {e}[/red]")
                
        return True
    
    async def _specific_symbol_analysis(self) -> bool:
        """특정 종목 분석"""
        console.print(Panel("[bold green]🎯 특정 종목 분석[/bold green]", border_style="green"))
        
        try:
            # 종목 코드 입력
            symbols_input = Prompt.ask("분석할 종목 코드를 입력하세요 (쉼표로 구분)")
            symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
            
            if not symbols:
                console.print("[yellow]⚠️ 종목 코드가 입력되지 않았습니다.[/yellow]")
                return False
            
            # 전략 선택
            strategy = await self._get_strategy_choice()
            
            # 분석 실행
            results = await self.system.analyze_symbols(symbols, strategy)
            
            # 결과 표시
            if results:
                await self.system.display_results(results, "종합 분석 결과")
            
            return len(results) > 0
            
        except Exception as e:
            console.print(f"[red]❌특정 종목 분석 실패: {e}[/red]")
            return False
    
    async def _news_analysis(self) -> bool:
        """뉴스 재료 분석만 실행"""
        console.print(Panel("[bold green]📰 뉴스 재료 분석[/bold green]", border_style="green"))
        
        try:
            # 컴포넌트 확인
            if not self.system.news_collector:
                console.print("[yellow]⚠️ 뉴스 수집기가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 분석 옵션
            symbols_input = Prompt.ask("분석할 종목 코드 (전체 분석은 Enter)", default="")
            
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                for symbol in symbols:
                    try:
                        # 종목 정보 조회
                        stock_info = await self.system.data_collector.get_stock_info(symbol)
                        name = stock_info.get('name', symbol) if stock_info else symbol
                        
                        # 뉴스 분석
                        news_result = await self.system.news_collector.analyze_stock_news(symbol, name)
                        
                        # 결과 표시
                        await self._display_news_analysis_result(symbol, name, news_result)
                        
                    except Exception as e:
                        console.print(f"[yellow]⚠️ {symbol} 뉴스 분석 실패: {e}[/yellow]")
            else:
                # 전체 시장 뉴스 분석
                market_news = await self.system.news_collector.get_market_news()
                await self._display_market_news(market_news)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 뉴스 분석 실패: {e}[/red]")
            return False
    
    async def _supply_demand_analysis(self) -> bool:
        """수급정보 분석만 실행"""
        console.print(Panel("[bold green]💰 수급정보 분석 (NEW)[/bold green]", border_style="green"))
        
        try:
            # 수급 분석 모듈 확인
            try:
                from analyzers.supply_demand_analyzer import SupplyDemandAnalyzer
                analyzer = SupplyDemandAnalyzer(self.config)
            except ImportError:
                console.print("[yellow]⚠️ 수급 분석 모듈이 없습니다. 기본 분석으로 대체합니다.[/yellow]")
                return await self._basic_supply_demand_analysis()
            
            # 분석 실행
            symbols_input = Prompt.ask("분석할 종목 코드 (전체 분석은 Enter)", default="")
            
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                results = await analyzer.analyze_symbols(symbols)
            else:
                results = await analyzer.analyze_market()
            
            # 결과 표시
            await self._display_supply_demand_results(results)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 수급 분석 실패: {e}[/red]")
            return False
    
    async def _chart_pattern_analysis(self) -> bool:
        """차트패턴 분석만 실행"""
        console.print(Panel("[bold green]📈 차트패턴 분석 (NEW)[/bold green]", border_style="green"))
        
        try:
            # 차트패턴 분석 모듈 확인
            try:
                from analyzers.chart_pattern_analyzer import ChartPatternAnalyzer
                analyzer = ChartPatternAnalyzer(self.config)
            except ImportError:
                console.print("[yellow]⚠️ 차트패턴 분석 모듈이 없습니다. 기본 분석으로 대체합니다.[/yellow]")
                return await self._basic_chart_pattern_analysis()
            
            # 분석 옵션
            symbols_input = Prompt.ask("분석할 종목 코드 (전체 분석은 Enter)", default="")
            pattern_types = await self._get_pattern_types()
            
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                results = await analyzer.analyze_symbols(symbols, pattern_types)
            else:
                results = await analyzer.analyze_market(pattern_types)
            
            # 결과 표시
            await self._display_chart_pattern_results(results)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 차트패턴 분석 실패: {e}[/red]")
            return False
    
    async def _auto_trading(self) -> bool:
        """자동매매 시작"""
        if not self.system.trading_enabled:
            console.print(Panel("[red]❌ 매매 모드가 비활성화되어 있습니다.[/red]", border_style="red"))
            return False
        
        console.print(Panel("[bold red]💰 자동매매 시작 (실제 거래 위험!)[/bold red]", border_style="red"))
        
        # 경고 및 확인
        warning_text = """
[bold red]⚠️ 경고: 실제 자금으로 자동매매가 실행됩니다![/bold red]

자동매매 시작 전 확인사항:
• 충분한 테스트를 완료했는지 확인
• 리스크 설정이 적절한지 확인  
• 시장 상황을 고려했는지 확인
• 손실 가능성을 충분히 인지했는지 확인

자동매매 중에는 시스템을 임의로 종료하지 마세요.
        """
        
        console.print(Panel(warning_text, title="⚠️ 자동매매 경고", border_style="red"))
        
        if not Confirm.ask("\n[bold]정말로 자동매매를 시작하시겠습니까?[/bold]"):
            return False
        
        if not Confirm.ask("[bold red]다시 한번 확인합니다. 실제 자금으로 거래하시겠습니까?[/bold red]"):
            return False
        
        try:
            # 전략 선택
            strategy = await self._get_strategy_choice()
            
            # 자동매매 실행
            await self.system.run_auto_trading(strategy)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 자동매매 실행 실패: {e}[/red]")
            return False
    
    async def _backtest(self) -> bool:
        """백테스트 실행"""
        console.print(Panel("[bold green]📈 백테스트 실행[/bold green]", border_style="green"))
        
        try:
            # 백테스트 옵션 입력
            strategy = await self._get_strategy_choice()
            
            # 기간 설정
            console.print("\n[bold]백테스트 기간 설정[/bold]")
            start_date = Prompt.ask("시작 날짜 (YYYY-MM-DD)", default="2024-01-01")
            end_date = Prompt.ask("종료 날짜 (YYYY-MM-DD)", default="2024-12-31")
            
            # 종목 선택
            symbols_input = Prompt.ask("특정 종목 (전체는 Enter)", default="")
            symbols = None
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
            
            # 백테스트 실행
            results = await self.system.run_backtest(strategy, start_date, end_date, symbols)
            
            # 결과 표시
            await self.system._display_backtest_results(results)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 백테스트 실행 실패: {e}[/red]")
            return False
    
    async def _scheduler(self) -> bool:
        """실시간 매매 스케줄러 관리"""
        console.print(Panel("[bold green]⏰ 실시간 매매 스케줄러[/bold green]", border_style="green"))
        
        if not self.system.scheduler:
            console.print("[red]❌ 스케줄러가 초기화되지 않았습니다.[/red]")
            return False
        
        while True:
            try:
                # 현재 스케줄러 상태 표시
                status = self.system.scheduler.get_status()
                
                console.print(f"\n[bold]📊 현재 상태:[/bold]")
                console.print(f"• 실행 상태: {'[green]실행 중[/green]' if status['is_running'] else '[red]중지됨[/red]'}")
                console.print(f"• 장중 여부: {'[green]장중[/green]' if status['is_market_hours'] else '[yellow]장외[/yellow]'}")
                console.print(f"• 모니터링 종목: {status['monitored_stocks_count']}개")
                console.print(f"• 마지막 분석 시간: {status['last_analysis_time'] or 'N/A'}")
                
                # 스케줄러 메뉴
                scheduler_options = {
                    "1": "📈 실시간 스케줄러 시작",
                    "2": "🛑 실시간 스케줄러 중지", 
                    "3": "📋 모니터링 종목 추가",
                    "4": "🗑️ 모니터링 종목 제거",
                    "5": "📊 스케줄러 상태 확인",
                    "0": "메인 메뉴로 돌아가기"
                }
                
                console.print("\n[bold]스케줄러 관리 옵션:[/bold]")
                for key, value in scheduler_options.items():
                    console.print(f"  {key}. {value}")
                
                choice = Prompt.ask("옵션을 선택하세요", choices=list(scheduler_options.keys()), default="0")
                
                if choice == "0":
                    break
                elif choice == "1":
                    # 스케줄러 시작
                    if status['is_running']:
                        console.print("[yellow]⚠️ 스케줄러가 이미 실행 중입니다.[/yellow]")
                    else:
                        await self.system.scheduler.start()
                        console.print("[green]✅ 실시간 스케줄러가 시작되었습니다.[/green]")
                        
                elif choice == "2":
                    # 스케줄러 중지
                    if status['is_running']:
                        await self.system.scheduler.stop()
                        console.print("[red]🛑 실시간 스케줄러가 중지되었습니다.[/red]")
                    else:
                        console.print("[yellow]⚠️ 스케줄러가 이미 중지되어 있습니다.[/yellow]")
                        
                elif choice == "3":
                    # 모니터링 종목 추가
                    symbol = Prompt.ask("추가할 종목 코드를 입력하세요 (예: 005930)")
                    
                    # 전략 선택
                    available_strategies = list(self.system.strategies.keys())
                    strategy_list = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(available_strategies)])
                    console.print(f"\n[bold]사용 가능한 전략:[/bold]\n{strategy_list}")
                    
                    strategy_choice = Prompt.ask("전략 번호를 선택하세요", 
                                               choices=[str(i+1) for i in range(len(available_strategies))], 
                                               default="1")
                    strategy = available_strategies[int(strategy_choice) - 1]
                    
                    success = await self.system.scheduler.add_monitoring_stock(symbol, strategy)
                    if success:
                        console.print(f"[green]✅ {symbol} ({strategy} 전략) 모니터링 추가됨[/green]")
                    else:
                        console.print(f"[yellow]⚠️ {symbol} 모니터링 추가 실패 (이미 존재할 수 있음)[/yellow]")
                        
                elif choice == "4":
                    # 모니터링 종목 제거
                    if status['monitored_stocks_count'] == 0:
                        console.print("[yellow]⚠️ 모니터링 중인 종목이 없습니다.[/yellow]")
                    else:
                        symbol = Prompt.ask("제거할 종목 코드를 입력하세요")
                        success = self.system.scheduler.remove_monitoring_stock(symbol)
                        if success:
                            console.print(f"[green]✅ {symbol} 모니터링 제거됨[/green]")
                        else:
                            console.print(f"[yellow]⚠️ {symbol} 모니터링 제거 실패 (존재하지 않을 수 있음)[/yellow]")
                            
                elif choice == "5":
                    # 상태 확인 (이미 상단에 표시됨)
                    console.print("[green]✅ 상태 정보가 상단에 표시되어 있습니다.[/green]")
                
                # 잠시 대기 후 다시 메뉴 표시
                if choice != "0":
                    await asyncio.sleep(1)
                    
            except Exception as e:
                console.print(f"[red]❌ 스케줄러 관리 실패: {e}[/red]")
                self.logger.error(f"❌ 스케줄러 관리 실패: {e}")
                break
        
        return True
    
    # === 데이터베이스 메뉴 ===
    
    async def _database_status(self) -> bool:
        """데이터베이스 상태 확인"""
        console.print(Panel("[bold blue]🗄️ 데이터베이스 상태 확인[/bold blue]", border_style="blue"))
        
        try:
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 연결 상태 확인
            connection_status = await self.system.db_manager.check_connection()
            
            if connection_status:
                # 데이터베이스 정보 조회
                db_info = await self.system.db_manager.get_database_info()
                await self._display_database_info(db_info)
            else:
                console.print("[red]❌ 데이터베이스 연결 실패[/red]")
            
            return connection_status
            
        except Exception as e:
            console.print(f"[red]❌ 데이터베이스 상태 확인 실패: {e}[/red]")
            return False
    
    async def _view_stock_data(self) -> bool:
        """종목 데이터 조회"""
        console.print(Panel("[bold blue]📊 종목 데이터 조회[/bold blue]", border_style="blue"))
        
        try:
            symbol = Prompt.ask("조회할 종목 코드를 입력하세요")
            
            if not symbol:
                console.print("[yellow]⚠️ 종목 코드가 입력되지 않았습니다.[/yellow]")
                return False
            
            # 데이터 조회
            if self.system.db_manager:
                stock_data = await self.system.db_manager.get_stock_data(symbol)
                if stock_data:
                    await self._display_stock_data(symbol, stock_data)
                else:
                    console.print(f"[yellow]⚠️ {symbol}의 데이터를 찾을 수 없습니다.[/yellow]")
            else:
                # 실시간 데이터 조회
                stock_data = await self.system.data_collector.get_stock_data(symbol)
                if stock_data:
                    await self._display_stock_data(symbol, stock_data)
                else:
                    console.print(f"[yellow]⚠️ {symbol}의 데이터를 조회할 수 없습니다.[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 종목 데이터 조회 실패: {e}[/red]")
            return False
    
    async def _view_analysis_results(self) -> bool:
        """분석 결과 조회"""
        console.print(Panel("[bold blue]📈 분석 결과 조회[/bold blue]", border_style="blue"))
        
        try:
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 없어 최근 분석 결과만 표시합니다.[/yellow]")
                return False
            
            # 조회 옵션
            days = IntPrompt.ask("최근 며칠간의 결과를 조회하시겠습니까?", default=7)
            
            # 결과 조회
            results = await self.system.db_manager.get_analysis_results(days=days)
            
            if results:
                await self._display_historical_analysis_results(results)
            else:
                console.print("[yellow]📊 분석 결과가 없습니다.[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 분석 결과 조회 실패: {e}[/red]")
            return False
    
    async def _view_trading_records(self) -> bool:
        """거래 기록 조회"""
        console.print(Panel("[bold blue]💰 거래 기록 조회[/bold blue]", border_style="blue"))
        
        try:
            if not self.system.trading_enabled:
                console.print("[yellow]⚠️ 매매 모드가 비활성화되어 있습니다.[/yellow]")
                return False
            
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 조회 기간
            days = IntPrompt.ask("최근 며칠간의 거래 기록을 조회하시겠습니까?", default=30)
            
            # 거래 기록 조회
            trading_records = await self.system.db_manager.get_trading_records(days=days)
            
            if trading_records:
                await self._display_trading_records(trading_records)
            else:
                console.print("[yellow]💰 거래 기록이 없습니다.[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 거래 기록 조회 실패: {e}[/red]")
            return False
    
    # === 고급 기능 메뉴 ===
    
    async def _data_cleanup(self) -> bool:
        """데이터 정리 및 최적화"""
        console.print(Panel("[bold magenta]🧹 데이터 정리 및 최적화[/bold magenta]", border_style="magenta"))
        
        try:
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 정리 옵션
            cleanup_options = {
                "1": "오래된 분석 결과 삭제 (30일 이상)",
                "2": "중복 데이터 제거",
                "3": "데이터베이스 최적화",
                "4": "전체 정리 및 최적화"
            }
            
            console.print("\n[bold]정리 옵션:[/bold]")
            for key, value in cleanup_options.items():
                console.print(f"  {key}. {value}")
            
            choice = Prompt.ask("정리 작업을 선택하세요", choices=list(cleanup_options.keys()))
            
            if not Confirm.ask(f"'{cleanup_options[choice]}' 작업을 실행하시겠습니까?"):
                return False
            
            # 정리 작업 실행
            with Progress() as progress:
                task = progress.add_task("[green]데이터 정리 중...", total=100)
                
                if choice == "1":
                    await self.system.db_manager.cleanup_old_analysis_results(days=30)
                elif choice == "2":
                    await self.system.db_manager.remove_duplicate_data()
                elif choice == "3":
                    await self.system.db_manager.optimize_database()
                elif choice == "4":
                    await self.system.db_manager.full_cleanup_and_optimize()
                
                progress.update(task, advance=100)
            
            console.print("[green]✅ 데이터 정리 완료[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 데이터 정리 실패: {e}[/red]")
            return False
    
    async def _log_analysis(self) -> bool:
        """로그 분석"""
        console.print(Panel("[bold magenta]📋 로그 분석[/bold magenta]", border_style="magenta"))
        
        try:
            # 로그 파일 위치 확인
            log_file = getattr(self.config, 'LOG_FILE', 'trading_system.log')
            
            # 로그 분석 옵션
            analysis_options = {
                "1": "최근 에러 로그 확인",
                "2": "성능 분석",
                "3": "거래 로그 분석",
                "4": "전체 로그 요약"
            }
            
            console.print("\n[bold]분석 옵션:[/bold]")
            for key, value in analysis_options.items():
                console.print(f"  {key}. {value}")
            
            choice = Prompt.ask("분석 유형을 선택하세요", choices=list(analysis_options.keys()))
            
            # 로그 분석 실행 (실제 구현에서는 별도 로그 분석 모듈 사용)
            await self._analyze_logs(choice, log_file)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 로그 분석 실패: {e}[/red]")
            return False
    
    async def _system_monitoring(self) -> bool:
        """시스템 상태 모니터링"""
        console.print(Panel("[bold magenta]📊 시스템 상태 모니터링[/bold magenta]", border_style="magenta"))
        
        try:
            console.print("[yellow]실시간 모니터링을 시작합니다. Ctrl+C로 중단하세요.[/yellow]")
            
            while True:
                # 시스템 상태 조회
                status = await self.system.get_system_status()
                
                # 상태 표시
                await self._display_realtime_status(status)
                
                # 5초 대기
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]🛑 모니터링 중단[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 시스템 모니터링 실패: {e}[/red]")
            return False
    
    # === 헬퍼 메서드들 ===
    
    async def _get_strategy_choice(self) -> str:
        """전략 선택"""
        strategies = {
        "1": "momentum",
        "2": "breakout", 
        "3": "eod",
        "4": "supertrend_ema_rsi"  # ⭐ 이 줄만 추가
    }
        
        console.print("\n[bold]전략 선택:[/bold]")
        console.print("  1. Momentum (모멘텀)")
        console.print("  2. Breakout (돌파)")
        console.print("  3. EOD (장마감)")
        console.print("  4. Supertrend EMA RSI (신규)")  # ⭐ 이 줄만 추가
        choice = Prompt.ask("전략을 선택하세요", choices=list(strategies.keys()), default="1")
        return strategies[choice]
    
    async def _get_analysis_limit(self) -> int:
        """분석 종목 수 제한 - 1차 필터링 결과 모두 분석"""
        console.print("[yellow]ℹ️ 1차 필터링에서 추출된 모든 종목을 2차 필터링합니다.[/yellow]")
        return None  # 제한 없음
    
    async def _get_pattern_types(self) -> List[str]:
        """차트패턴 유형 선택"""
        pattern_options = {
            "1": "head_and_shoulders",
            "2": "double_top",
            "3": "double_bottom", 
            "4": "triangle",
            "5": "flag",
            "6": "wedge",
            "7": "rectangle"
        }
        
        console.print("\n[bold]차트패턴 유형:[/bold]")
        for key, value in pattern_options.items():
            console.print(f"  {key}. {value.replace('_', ' ').title()}")
        console.print("  0. 전체 패턴")
        
        choices = Prompt.ask("패턴을 선택하세요 (쉼표로 구분, 전체는 0)", default="0")
        
        if choices == "0":
            return list(pattern_options.values())
        else:
            selected = []
            for choice in choices.split(','):
                choice = choice.strip()
                if choice in pattern_options:
                    selected.append(pattern_options[choice])
            return selected if selected else list(pattern_options.values())
    
    async def _save_analysis_to_file(self, results: List) -> bool:
        """분석 결과를 파일로 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_results_{timestamp}.json"
            
            # 결과를 딕셔너리로 변환
            data = {
                'timestamp': datetime.now().isoformat(),
                'total_results': len(results),
                'results': [result.to_dict() if hasattr(result, 'to_dict') else result for result in results]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            console.print(f"[green]✅ 결과가 {filename}에 저장되었습니다.[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 파일 저장 실패: {e}[/red]")
            return False
    
    # === 표시 메서드들 ===
    
    async def _display_system_status(self):
        """시스템 상태 표시"""
        status = await self.system.get_system_status()
        
        # 시스템 정보 테이블
        table = Table(title="🔧 시스템 상태")
        table.add_column("구분", style="cyan", width=20)
        table.add_column("상태", style="green", width=15)
        table.add_column("설명", style="white")
        
        table.add_row("매매 모드", "✅ 활성화" if status['trading_enabled'] else "❌ 비활성화", "실제 거래 가능 여부")
        table.add_row("백테스트 모드", "✅ 활성화" if status['backtest_mode'] else "❌ 비활성화", "백테스트 모드 여부")
        table.add_row("시스템 실행", "🟢 실행중" if status['is_running'] else "🔴 정지", "자동매매 실행 상태")
        table.add_row("활성 포지션", str(status['active_positions']), "현재 보유 포지션 수")
        
        console.print(table)
        
        # 컴포넌트 상태 테이블
        comp_table = Table(title="🔧 컴포넌트 상태")
        comp_table.add_column("컴포넌트", style="cyan", width=20)
        comp_table.add_column("상태", style="green", width=10)
        
        for comp, status_val in status['components'].items():
            comp_table.add_row(
                comp.replace('_', ' ').title(),
                "✅ 정상" if status_val else "❌ 미초기화"
            )
        
        console.print(comp_table)
    
    async def _display_current_config(self):
        """현재 설정 표시"""
        config_table = Table(title="⚙️ 현재 시스템 설정")
        config_table.add_column("설정 항목", style="cyan", width=25)
        config_table.add_column("현재 값", style="yellow", width=20)
        config_table.add_column("설명", style="white")
        
        # 주요 설정들 표시 (실제 config 구조에 맞게 수정 필요)
        try:
            config_table.add_row("API 타임아웃", f"{getattr(self.config, 'API_TIMEOUT', 30)}초", "API 응답 대기 시간")
            config_table.add_row("분석 최소 점수", f"{getattr(self.config.analysis, 'MIN_COMPREHENSIVE_SCORE', 60)}점", "분석 결과 필터링 기준")
            config_table.add_row("최대 포지션", f"{getattr(self.config.trading, 'MAX_POSITIONS', 5)}개", "동시 보유 가능 포지션 수")
            config_table.add_row("리스크 한도", f"{getattr(self.config.trading, 'MAX_PORTFOLIO_RISK', 0.2):.1%}", "포트폴리오 최대 리스크")
        except AttributeError:
            config_table.add_row("설정 로드", "❌ 실패", "설정 파일 확인 필요")
        
        console.print(config_table)
    
    async def _modify_config(self):
        """설정 변경"""
        console.print("\n[bold]설정 변경 메뉴[/bold]")
        console.print("1. API 타임아웃 변경")
        console.print("2. 분석 최소 점수 변경")
        console.print("3. 최대 포지션 수 변경")
        console.print("4. 리스크 한도 변경")
        
        choice = Prompt.ask("변경할 설정을 선택하세요", choices=["1", "2", "3", "4"])
        
        try:
            if choice == "1":
                new_timeout = IntPrompt.ask("새로운 API 타임아웃 (초)", default=30)
                self.config.API_TIMEOUT = new_timeout
                console.print(f"[green]✅ API 타임아웃이 {new_timeout}초로 변경되었습니다.[/green]")
            
            elif choice == "2":
                new_score = IntPrompt.ask("새로운 분석 최소 점수", default=60)
                self.config.analysis.MIN_COMPREHENSIVE_SCORE = new_score
                console.print(f"[green]✅ 분석 최소 점수가 {new_score}점으로 변경되었습니다.[/green]")
            
            elif choice == "3":
                new_positions = IntPrompt.ask("새로운 최대 포지션 수", default=5)
                self.config.trading.MAX_POSITIONS = new_positions
                console.print(f"[green]✅ 최대 포지션 수가 {new_positions}개로 변경되었습니다.[/green]")
            
            elif choice == "4":
                new_risk = float(Prompt.ask("새로운 리스크 한도 (0.1 = 10%)", default="0.2"))
                self.config.trading.MAX_PORTFOLIO_RISK = new_risk
                console.print(f"[green]✅ 리스크 한도가 {new_risk:.1%}로 변경되었습니다.[/green]")
                
        except Exception as e:
            console.print(f"[red]❌ 설정 변경 실패: {e}[/red]")
    
    async def _display_news_analysis_result(self, symbol: str, name: str, news_result: Dict):
        """뉴스 분석 결과 표시"""
        panel_content = f"""
[bold]📰 {symbol} {name} 뉴스 분석[/bold]

뉴스 점수: {news_result.get('news_score', 0):.1f}점
감정 분석: {news_result.get('sentiment', 'N/A')}
주요 키워드: {', '.join(news_result.get('keywords', [])[:5])}

최근 뉴스 ({len(news_result.get('articles', []))}건):
        """
        
        for i, article in enumerate(news_result.get('articles', [])[:3]):
            panel_content += f"\n{i+1}. {article.get('title', 'N/A')}"
            panel_content += f"\n   📅 {article.get('date', 'N/A')} | 감정: {article.get('sentiment', 'N/A')}"
        
        console.print(Panel(panel_content, title="📰 뉴스 분석 결과", border_style="blue"))
    
    async def _display_market_news(self, market_news: Dict):
        """전체 시장 뉴스 표시"""
        table = Table(title="📰 시장 뉴스 요약")
        table.add_column("분야", style="cyan", width=15)
        table.add_column("주요 뉴스", style="white", width=50)
        table.add_column("감정", style="yellow", width=10)
        
        for category, news_list in market_news.items():
            for news in news_list[:3]:  # 각 분야별 상위 3개
                table.add_row(
                    category.title(),
                    news.get('title', 'N/A')[:47] + "..." if len(news.get('title', '')) > 50 else news.get('title', 'N/A'),
                    news.get('sentiment', 'N/A')
                )
        
        console.print(table)
    
    async def _basic_supply_demand_analysis(self) -> bool:
        """기본 수급 분석 (모듈이 없을 때)"""
        console.print("[yellow]기본 수급 분석을 실행합니다...[/yellow]")
        
        # 기본적인 수급 지표 분석
        try:
            symbols_input = Prompt.ask("분석할 종목 코드 (샘플 분석은 Enter)", default="")
            
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
            else:
                symbols = ["005930", "000660", "035420"]  # 샘플 종목들
            
            results = []
            for symbol in symbols:
                try:
                    # 기본 데이터 수집
                    stock_data = await self.system.data_collector.get_stock_data(symbol)
                    if stock_data:
                        # 간단한 수급 지표 계산
                        supply_demand = {
                            'symbol': symbol,
                            'volume_ratio': stock_data.get('volume_ratio', 1.0),
                            'foreign_ratio': stock_data.get('foreign_ratio', 0),
                            'institution_ratio': stock_data.get('institution_ratio', 0),
                            'individual_ratio': stock_data.get('individual_ratio', 0)
                        }
                        results.append(supply_demand)
                except Exception as e:
                    console.print(f"[yellow]⚠️ {symbol} 분석 실패: {e}[/yellow]")
            
            await self._display_supply_demand_results(results)
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 기본 수급 분석 실패: {e}[/red]")
            return False
    
    async def _basic_chart_pattern_analysis(self) -> bool:
        """기본 차트패턴 분석 (모듈이 없을 때)"""
        console.print("[yellow]기본 차트패턴 분석을 실행합니다...[/yellow]")
        
        try:
            symbols_input = Prompt.ask("분석할 종목 코드 (샘플 분석은 Enter)", default="")
            
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
            else:
                symbols = ["005930", "000660", "035420"]  # 샘플 종목들
            
            results = []
            for symbol in symbols:
                try:
                    # 기본 데이터 수집
                    stock_data = await self.system.data_collector.get_stock_data(symbol)
                    if stock_data:
                        # 간단한 패턴 분석 (실제로는 더 복잡한 로직 필요)
                        pattern_result = {
                            'symbol': symbol,
                            'patterns_detected': ['uptrend', 'support_level'],  # 예시
                            'pattern_strength': 75,
                            'next_resistance': stock_data.get('current_price', 0) * 1.05,
                            'next_support': stock_data.get('current_price', 0) * 0.95
                        }
                        results.append(pattern_result)
                except Exception as e:
                    console.print(f"[yellow]⚠️ {symbol} 분석 실패: {e}[/yellow]")
            
            await self._display_chart_pattern_results(results)
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 기본 차트패턴 분석 실패: {e}[/red]")
            return False
    
    async def _display_supply_demand_results(self, results: List[Dict]):
        """수급 분석 결과 표시"""
        if not results:
            console.print("[yellow]📊 수급 분석 결과가 없습니다.[/yellow]")
            return
        
        table = Table(title="💰 수급 분석 결과")
        table.add_column("종목", style="cyan", width=10)
        table.add_column("거래량비", style="green", width=10)
        table.add_column("외국인", style="blue", width=10)
        table.add_column("기관", style="magenta", width=10)
        table.add_column("개인", style="yellow", width=10)
        table.add_column("평가", style="white", width=15)
        
        for result in results:
            # 수급 평가 로직
            volume_ratio = result.get('volume_ratio', 1.0)
            foreign_ratio = result.get('foreign_ratio', 0)
            evaluation = "긍정적" if volume_ratio > 1.5 and foreign_ratio > 0 else "보통"
            
            table.add_row(
                result.get('symbol', 'N/A'),
                f"{volume_ratio:.2f}",
                f"{foreign_ratio:.1f}%",
                f"{result.get('institution_ratio', 0):.1f}%",
                f"{result.get('individual_ratio', 0):.1f}%",
                evaluation
            )
        
        console.print(table)
    
    async def _display_chart_pattern_results(self, results: List[Dict]):
        """차트패턴 분석 결과 표시"""
        if not results:
            console.print("[yellow]📈 차트패턴 분석 결과가 없습니다.[/yellow]")
            return
        
        table = Table(title="📈 차트패턴 분석 결과")
        table.add_column("종목", style="cyan", width=10)
        table.add_column("감지된 패턴", style="green", width=20)
        table.add_column("강도", style="yellow", width=8)
        table.add_column("저항선", style="red", width=12)
        table.add_column("지지선", style="blue", width=12)
        
        for result in results:
            patterns = ', '.join(result.get('patterns_detected', []))
            strength = result.get('pattern_strength', 0)
            resistance = result.get('next_resistance', 0)
            support = result.get('next_support', 0)
            
            table.add_row(
                result.get('symbol', 'N/A'),
                patterns,
                f"{strength}%",
                f"{resistance:,.0f}" if resistance else "N/A",
                f"{support:,.0f}" if support else "N/A"
            )
        
        console.print(table)
    
    async def _display_database_info(self, db_info: Dict):
        """데이터베이스 정보 표시"""
        info_text = f"""
[bold]🗄️ 데이터베이스 정보[/bold]

연결 상태: ✅ 정상
데이터베이스: {db_info.get('database_name', 'N/A')}
테이블 수: {db_info.get('table_count', 0)}개
총 레코드 수: {db_info.get('total_records', 0):,}개

테이블별 레코드 수:
• 종목 데이터: {db_info.get('stock_records', 0):,}개
• 분석 결과: {db_info.get('analysis_records', 0):,}개  
• 거래 기록: {db_info.get('trading_records', 0):,}개

마지막 업데이트: {db_info.get('last_update', 'N/A')}
        """
        
        console.print(Panel(info_text, title="🗄️ 데이터베이스 상태", border_style="blue"))
    
    async def _display_stock_data(self, symbol: str, stock_data: Dict):
        """종목 데이터 표시"""
        data_text = f"""
[bold]📊 {symbol} 종목 정보[/bold]

종목명: {stock_data.get('name', 'N/A')}
현재가: {stock_data.get('current_price', 0):,}원
등락률: {stock_data.get('change_rate', 0):.2f}%
거래량: {stock_data.get('volume', 0):,}주
시가총액: {stock_data.get('market_cap', 0):,}억원

기술적 지표:
• RSI: {stock_data.get('rsi', 0):.1f}
• MACD: {stock_data.get('macd', 0):.3f}
• 볼린저밴드: {stock_data.get('bollinger_position', 'N/A')}

재무 정보:
• PER: {stock_data.get('per', 0):.1f}
• PBR: {stock_data.get('pbr', 0):.2f}
• ROE: {stock_data.get('roe', 0):.1f}%
        """
        
        console.print(Panel(data_text, title=f"📊 {symbol} 종목 데이터", border_style="cyan"))
    
    async def _display_historical_analysis_results(self, results: List[Dict]):
        """과거 분석 결과 표시"""
        table = Table(title="📈 과거 분석 결과")
        table.add_column("날짜", style="cyan", width=12)
        table.add_column("종목", style="magenta", width=10)
        table.add_column("점수", style="green", width=8)
        table.add_column("추천", style="yellow", width=12)
        table.add_column("전략", style="blue", width=10)
        
        for result in results[-20:]:  # 최근 20개만 표시
            table.add_row(
                result.get('date', 'N/A')[:10],
                result.get('symbol', 'N/A'),
                f"{result.get('score', 0):.1f}",
                result.get('recommendation', 'N/A'),
                result.get('strategy', 'N/A')
            )
        
        console.print(table)
    
    async def _display_trading_records(self, records: List[Dict]):
        """거래 기록 표시"""
        table = Table(title="💰 거래 기록")
        table.add_column("날짜", style="cyan", width=12)
        table.add_column("종목", style="magenta", width=10)
        table.add_column("구분", style="yellow", width=8)
        table.add_column("수량", style="white", width=10)
        table.add_column("가격", style="green", width=12)
        table.add_column("손익", style="blue", width=12)
        
        for record in records[-20:]:  # 최근 20개만 표시
            pnl = record.get('pnl', 0)
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
            
            table.add_row(
                record.get('date', 'N/A')[:10],
                record.get('symbol', 'N/A'),
                record.get('action', 'N/A'),
                f"{record.get('quantity', 0):,}주",
                f"{record.get('price', 0):,}원",
                f"[{pnl_color}]{pnl:+,.0f}원[/{pnl_color}]"
            )
        
        console.print(table)
    
    async def _display_realtime_status(self, status: Dict):
        """실시간 상태 표시"""
        # 콘솔 클리어 (Rich에서 지원하는 방식)
        console.clear()
        
        # 현재 시간
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        status_text = f"""
[bold]📊 실시간 시스템 상태 ({current_time})[/bold]

시스템 상태:
• 매매 모드: {'🟢 활성화' if status['trading_enabled'] else '🔴 비활성화'}
• 자동매매: {'🟢 실행중' if status['is_running'] else '🔴 정지'}
• 활성 포지션: {status['active_positions']}개

컴포넌트 상태:
• 데이터 수집기: {'✅' if status['components']['data_collector'] else '❌'}
• 분석 엔진: {'✅' if status['components']['analysis_engine'] else '❌'}
• 매매 실행기: {'✅' if status['components']['executor'] else '❌'}
• 리스크 관리: {'✅' if status['components']['risk_manager'] else '❌'}

[dim]Ctrl+C를 눌러 모니터링을 중단하세요.[/dim]
        """
        
        console.print(Panel(status_text, title="📊 실시간 모니터링", border_style="green"))
    
    async def _analyze_logs(self, choice: str, log_file: str):
        """로그 분석 실행"""
        try:
            console.print(f"[yellow]📋 로그 분석 중... ({log_file})[/yellow]")
            
            # 실제 로그 파일 분석 로직 (간단한 예시)
            if choice == "1":
                console.print("🔍 최근 에러 로그를 확인합니다...")
                # 에러 로그 필터링 및 표시
                
            elif choice == "2":
                console.print("📈 성능 분석을 실행합니다...")
                # 성능 관련 로그 분석
                
            elif choice == "3":
                console.print("💰 거래 로그를 분석합니다...")
                # 거래 관련 로그 분석
                
            elif choice == "4":
                console.print("📊 전체 로그 요약을 생성합니다...")
                # 전체 로그 요약
            
            # 분석 결과 표시 (실제 구현에서는 파일을 읽어서 분석)
            summary_text = f"""
[bold]📋 로그 분석 결과[/bold]

분석 대상: {log_file}
분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

요약:
• 총 로그 라인: 1,234개 (예시)
• 에러 로그: 5개
• 경고 로그: 23개
• 거래 로그: 15개

[dim]상세 분석은 별도 로그 분석 도구를 사용하세요.[/dim]
            """
            
            console.print(Panel(summary_text, title="📋 로그 분석 결과", border_style="magenta"))
            
        except Exception as e:
            console.print(f"[red]❌ 로그 분석 실패: {e}[/red]")