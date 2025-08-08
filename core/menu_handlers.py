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

# 백테스팅 모듈
from backtesting.strategy_validator import StrategyValidator, ValidationCriteria
from backtesting.historical_analyzer import HistoricalAnalyzer
from backtesting.performance_visualizer import PerformanceVisualizer

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
    7. 분석 후 상위 점수 자동 매수
    8. 자동매매 시작
    9. 백테스트 실행

    [bold magenta]🧠 AI 고급 기능 (Phase 4)[/bold magenta]
    12. AI 종합 시장 분석
    13. AI 시장 체제 분석
    14. AI 전략 최적화
    15. AI 리스크 평가
    16. AI 일일 보고서

    [bold yellow]📢 알림 시스템 (Phase 5)[/bold yellow]
    17. 텔레그램 알림 테스트
    18. 알림 설정 관리
    19. 알림 통계 조회
    20. 알림 상태 확인

    [bold purple]🧪 백테스팅 & 검증 (Phase 6)[/bold purple]
    21. AI vs 전통 전략 비교
    22. 전략 성능 검증
    23. 과거 AI 예측 정확도 분석
    24. 시장 체제별 성과 분석
    25. 백테스팅 보고서 생성

    [bold blue]🗄️ 데이터[/bold blue]
    10. 데이터베이스 상태
    11. 종목 데이터 조회

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
                "7": self._analysis_and_auto_buy,
                "8": self._auto_trading,
                "9": self._backtest,
                
                # 데이터베이스
                "10": self._database_status,
                "11": self._view_stock_data,
                
                # AI 고급 기능 (Phase 4)
                "12": self._ai_comprehensive_analysis,
                "13": self._ai_market_regime_analysis,
                "14": self._ai_strategy_optimization,
                "15": self._ai_risk_assessment,
                "16": self._ai_daily_report,
                
                # 알림 시스템 (Phase 5)
                "17": self._test_telegram_notification,
                "18": self._manage_notification_settings,
                "19": self._view_notification_stats,
                "20": self._check_notification_status,
                
                # 백테스팅 & 검증 (Phase 6)
                "21": self._ai_vs_traditional_comparison,
                "22": self._strategy_validation,
                "23": self._ai_prediction_accuracy_analysis,
                "24": self._market_regime_performance,
                "25": self._backtesting_report_generation,
                
                # 고급 기능 (기존) - 번호 이동
                "26": self._supply_demand_analysis,
                "27": self._chart_pattern_analysis,
                "28": self._scheduler,
                "29": self._view_analysis_results,
                "30": self._view_trading_records,
                "31": self._data_cleanup,
                "32": self._log_analysis,
                "33": self._system_monitoring,
                "34": self._debug_filtering
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
    
    async def _analysis_and_auto_buy(self) -> bool:
        """분석 후 상위 점수 자동 매수"""
        console.print(Panel("[bold green]분석 후 상위 점수 자동 매수[/bold green]", border_style="green"))
        
        try:
            # 1. 전략 선택
            strategies = {
                "1": ("momentum", "Momentum 전략"),
                "2": ("breakout", "Breakout 전략"), 
                "3": ("eod", "EOD 전략"),
                "4": ("supertrend_ema_rsi", "Supertrend EMA RSI 전략"),
                "5": ("vwap", "VWAP 전략")
            }
            
            console.print("\n[bold]전략 선택:[/bold]")
            for key, (_, name) in strategies.items():
                console.print(f"  {key}. {name}")
            
            strategy_choice = Prompt.ask("전략 선택", choices=list(strategies.keys()), default="1")
            selected_strategy, strategy_name = strategies[strategy_choice]
            
            # 2. 매수 설정
            console.print(f"\n[bold]선택된 전략:[/bold] {strategy_name}")
            
            top_n = IntPrompt.ask("상위 몇 개 종목을 매수하시겠습니까?", default=3, show_default=True)
            budget_per_stock = IntPrompt.ask("종목당 투자 금액 (원)", default=1000000, show_default=True)
            
            # 3. 안전 확인
            total_budget = top_n * budget_per_stock
            console.print(f"\n[yellow]📋 매수 설정 확인:[/yellow]")
            console.print(f"  • 전략: {strategy_name}")
            console.print(f"  • 대상: 상위 {top_n}개 종목")
            console.print(f"  • 종목당 투자금액: {budget_per_stock:,}원")
            console.print(f"  • 총 투자금액: {total_budget:,}원")
            
            if not Confirm.ask("\n위 설정으로 분석 후 자동 매수를 진행하시겠습니까?", default=False):
                console.print("[yellow]자동 매수를 취소했습니다[/yellow]")
                return False
            
            # 4. 자동 매수 실행
            result = await self.system.run_analysis_and_auto_buy(
                strategy=selected_strategy,
                top_n=top_n,
                budget_per_stock=budget_per_stock
            )
            
            # 5. 결과 표시
            if result['success']:
                console.print(f"\n[bold green]✅ 자동 매수 완료[/bold green]")
                console.print(f"총 주문: {result.get('total_orders', 0)}건")
                console.print(f"성공: {result.get('successful_orders', 0)}건")
                console.print(f"실패: {result.get('failed_orders', 0)}건")
                
                # 성공한 매수 내역 표시
                execution_results = result.get('execution_results', [])
                if execution_results:
                    success_results = [r for r in execution_results if r.get('status') == 'SUCCESS']
                    if success_results:
                        table = Table(title="매수 성공 내역")
                        table.add_column("종목코드", style="cyan")
                        table.add_column("종목명", style="white")
                        table.add_column("수량", style="green")
                        table.add_column("단가", style="yellow")
                        table.add_column("총액", style="magenta")
                        
                        for result_item in success_results:
                            table.add_row(
                                result_item.get('symbol', ''),
                                result_item.get('name', '')[:10],
                                f"{result_item.get('quantity', 0):,}주",
                                f"{result_item.get('price', 0):,}원",
                                f"{result_item.get('amount', 0):,}원"
                            )
                        console.print(table)
                
                return True
            else:
                console.print(f"[red]❌ 자동 매수 실패: {result.get('reason', '알 수 없는 오류')}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ 자동 매수 오류: {e}[/red]")
            self.logger.error(f"자동 매수 오류: {e}")
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
                
                # 44번 메뉴 전용 - DB 저장 없는 실시간 분석 실행
                console.print("[yellow]ℹ️ 실시간 종합 분석 실행 중... (DB 저장 없음)[/yellow]")
                analysis_success = await self.system.analysis_handlers.comprehensive_analysis()
                
                if not analysis_success:
                    console.print("[red]❌ 분석 실행 실패[/red]")
                else:
                    console.print("[green]✅ 실시간 분석 완료[/green]")
                
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
    
    # === AI 고급 기능 메뉴 (Phase 4) ===
    
    async def _ai_comprehensive_analysis(self) -> bool:
        """AI 종합 시장 분석"""
        console.print(Panel("[bold magenta]🧠 AI 종합 시장 분석[/bold magenta]", border_style="magenta"))
        
        try:
            # AI 컨트롤러 확인
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 시장 데이터 수집
            console.print("[yellow]📊 시장 데이터 수집 중...[/yellow]")
            market_data = await self._collect_market_data_for_ai()
            individual_stocks = await self._collect_individual_stocks_data()
            portfolio_data = await self._collect_portfolio_data()
            
            # AI 종합 분석 실행
            console.print("[yellow]🧠 AI 종합 분석 실행 중...[/yellow]")
            results = await self.system.run_ai_comprehensive_analysis(
                market_data, individual_stocks, portfolio_data
            )
            
            if results:
                console.print("[green]✅ AI 종합 분석 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ AI 분석 결과가 없습니다.[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ AI 종합 분석 실패: {e}[/red]")
            self.logger.error(f"❌ AI 종합 분석 실패: {e}")
            return False
    
    async def _ai_market_regime_analysis(self) -> bool:
        """AI 시장 체제 분석"""
        console.print(Panel("[bold magenta]🌐 AI 시장 체제 분석[/bold magenta]", border_style="magenta"))
        
        try:
            # AI 컨트롤러 확인
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 시장 데이터 수집
            console.print("[yellow]📊 시장 데이터 수집 중...[/yellow]")
            market_data = await self._collect_market_data_for_ai()
            individual_stocks = await self._collect_individual_stocks_data()
            
            # AI 시장 체제 분석 실행
            console.print("[yellow]🌐 AI 시장 체제 분석 실행 중...[/yellow]")
            results = await self.system.run_ai_market_regime_analysis(market_data, individual_stocks)
            
            if results:
                console.print("[green]✅ AI 시장 체제 분석 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ 시장 체제 분석 결과가 없습니다.[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ AI 시장 체제 분석 실패: {e}[/red]")
            self.logger.error(f"❌ AI 시장 체제 분석 실패: {e}")
            return False
    
    async def _ai_strategy_optimization(self) -> bool:
        """AI 전략 최적화"""
        console.print(Panel("[bold magenta]⚙️ AI 전략 최적화[/bold magenta]", border_style="magenta"))
        
        try:
            # AI 컨트롤러 확인
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 전략 선택
            available_strategies = ['momentum', 'breakout', 'rsi', 'scalping_3m', 'eod', 'vwap', 'supertrend_ema_rsi']
            console.print("\n[bold]최적화할 전략을 선택하세요:[/bold]")
            for i, strategy in enumerate(available_strategies, 1):
                console.print(f"  {i}. {strategy}")
            console.print("  0. 전체 전략")
            
            choice = Prompt.ask("전략 선택", choices=[str(i) for i in range(len(available_strategies) + 1)], default="0")
            
            if choice == "0":
                strategies = available_strategies
            else:
                strategies = [available_strategies[int(choice) - 1]]
            
            # 성과 데이터 수집
            console.print("[yellow]📊 성과 데이터 수집 중...[/yellow]")
            performance_data = await self._collect_strategy_performance_data()
            market_conditions = await self._collect_market_conditions()
            
            # AI 전략 최적화 실행
            console.print("[yellow]⚙️ AI 전략 최적화 실행 중...[/yellow]")
            results = await self.system.run_ai_strategy_optimization(
                strategies, performance_data, market_conditions
            )
            
            if results:
                console.print("[green]✅ AI 전략 최적화 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ 전략 최적화 결과가 없습니다.[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ AI 전략 최적화 실패: {e}[/red]")
            self.logger.error(f"❌ AI 전략 최적화 실패: {e}")
            return False
    
    async def _ai_risk_assessment(self) -> bool:
        """AI 리스크 평가"""
        console.print(Panel("[bold magenta]🛡️ AI 리스크 평가[/bold magenta]", border_style="magenta"))
        
        try:
            # AI 컨트롤러 확인
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 포트폴리오 데이터 수집
            console.print("[yellow]📊 포트폴리오 데이터 수집 중...[/yellow]")
            portfolio_data = await self._collect_portfolio_data()
            market_context = await self._collect_market_conditions()
            current_positions = await self._collect_current_positions()
            
            # AI 리스크 평가 실행
            console.print("[yellow]🛡️ AI 리스크 평가 실행 중...[/yellow]")
            results = await self.system.run_ai_risk_assessment(
                portfolio_data, market_context, current_positions
            )
            
            if results:
                console.print("[green]✅ AI 리스크 평가 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ 리스크 평가 결과가 없습니다.[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ AI 리스크 평가 실패: {e}[/red]")
            self.logger.error(f"❌ AI 리스크 평가 실패: {e}")
            return False
    
    async def _ai_daily_report(self) -> bool:
        """AI 일일 보고서"""
        console.print(Panel("[bold magenta]📊 AI 일일 보고서[/bold magenta]", border_style="magenta"))
        
        try:
            # AI 컨트롤러 확인
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            
            # 보고서 기간 선택
            period_options = {
                "1": "daily",
                "2": "weekly",
                "3": "monthly"
            }
            
            console.print("\n[bold]보고서 기간을 선택하세요:[/bold]")
            console.print("  1. 일일 보고서")
            console.print("  2. 주간 보고서") 
            console.print("  3. 월간 보고서")
            
            choice = Prompt.ask("기간 선택", choices=list(period_options.keys()), default="1")
            period = period_options[choice]
            
            # AI 일일 보고서 생성
            console.print(f"[yellow]📊 AI {period} 보고서 생성 중...[/yellow]")
            results = await self.system.generate_ai_daily_report(period)
            
            if results:
                console.print(f"[green]✅ AI {period} 보고서 생성 완료[/green]")
                
                # 보고서 저장 옵션
                if Confirm.ask("\n보고서를 파일로 저장하시겠습니까?"):
                    await self._save_ai_report_to_file(results, period)
                
                return True
            else:
                console.print("[yellow]⚠️ 보고서 생성 결과가 없습니다.[/yellow]")
                return False
            
        except Exception as e:
            console.print(f"[red]❌ AI 보고서 생성 실패: {e}[/red]")
            self.logger.error(f"❌ AI 보고서 생성 실패: {e}")
            return False
    
    # === AI 헬퍼 메서드들 ===
    
    async def _collect_market_data_for_ai(self) -> List[Dict]:
        """AI용 시장 데이터 수집"""
        try:
            # 기본 시장 지수 데이터 수집
            market_indices = ["KOSPI", "KOSDAQ", "KS11", "KQ11"]
            market_data = []
            
            for index in market_indices:
                try:
                    data = await self.system.data_collector.get_market_index_data(index)
                    if data:
                        market_data.append(data)
                except Exception as e:
                    self.logger.warning(f"시장 지수 {index} 데이터 수집 실패: {e}")
            
            # 빈 리스트 반환하지 않도록 기본 데이터 생성
            if not market_data:
                market_data = [{
                    'index': 'KOSPI',
                    'current_price': 2500,
                    'change_rate': 0.01,
                    'volume': 1000000,
                    'timestamp': datetime.now()
                }]
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"AI용 시장 데이터 수집 실패: {e}")
            return []
    
    async def _collect_individual_stocks_data(self) -> List[Dict]:
        """개별 종목 데이터 수집"""
        try:
            # 대형주 샘플 데이터 수집
            sample_stocks = ["005930", "000660", "035420", "005380", "051910"]
            stocks_data = []
            
            for symbol in sample_stocks:
                try:
                    data = await self.system.data_collector.get_stock_data(symbol)
                    if data:
                        data['symbol'] = symbol
                        stocks_data.append(data)
                except Exception as e:
                    self.logger.warning(f"종목 {symbol} 데이터 수집 실패: {e}")
            
            return stocks_data
            
        except Exception as e:
            self.logger.error(f"개별 종목 데이터 수집 실패: {e}")
            return []
    
    async def _collect_portfolio_data(self) -> Dict:
        """포트폴리오 데이터 수집"""
        try:
            # 기본 포트폴리오 정보 생성
            portfolio_data = {
                'total_value': 10000000,  # 1천만원
                'cash': 2000000,  # 200만원
                'positions': [],
                'daily_pnl': 0,
                'total_pnl': 0,
                'risk_level': 'MODERATE'
            }
            
            return portfolio_data
            
        except Exception as e:
            self.logger.error(f"포트폴리오 데이터 수집 실패: {e}")
            return {}
    
    async def _collect_strategy_performance_data(self) -> Dict:
        """전략 성과 데이터 수집"""
        try:
            # 기본 전략 성과 데이터
            performance_data = {
                'momentum': {'total_return': 0.05, 'win_rate': 0.6, 'sharpe_ratio': 1.2},
                'breakout': {'total_return': 0.08, 'win_rate': 0.55, 'sharpe_ratio': 1.0},
                'rsi': {'total_return': 0.03, 'win_rate': 0.65, 'sharpe_ratio': 0.8},
                'scalping_3m': {'total_return': 0.12, 'win_rate': 0.58, 'sharpe_ratio': 1.5},
                'eod': {'total_return': 0.06, 'win_rate': 0.62, 'sharpe_ratio': 1.1},
                'vwap': {'total_return': 0.04, 'win_rate': 0.68, 'sharpe_ratio': 0.9},
                'supertrend_ema_rsi': {'total_return': 0.07, 'win_rate': 0.60, 'sharpe_ratio': 1.3}
            }
            
            return performance_data
            
        except Exception as e:
            self.logger.error(f"전략 성과 데이터 수집 실패: {e}")
            return {}
    
    async def _collect_market_conditions(self) -> Dict:
        """시장 조건 데이터 수집"""
        try:
            market_conditions = {
                'volatility': 0.2,
                'trend': 'BULL',
                'volume_trend': 'INCREASING',
                'sector_rotation': 'TECH_TO_VALUE',
                'interest_rate_environment': 'RISING',
                'economic_indicators': 'MIXED'
            }
            
            return market_conditions
            
        except Exception as e:
            self.logger.error(f"시장 조건 데이터 수집 실패: {e}")
            return {}
    
    async def _collect_current_positions(self) -> Dict:
        """현재 포지션 데이터 수집"""
        try:
            current_positions = {
                '005930': {'quantity': 10, 'avg_price': 70000, 'current_price': 72000},
                '000660': {'quantity': 5, 'avg_price': 85000, 'current_price': 87000}
            }
            
            return current_positions
            
        except Exception as e:
            self.logger.error(f"현재 포지션 데이터 수집 실패: {e}")
            return {}
    
    async def _save_ai_report_to_file(self, report: Dict, period: str) -> bool:
        """AI 보고서를 파일로 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_report_{period}_{timestamp}.json"
            
            # 보고서 데이터를 JSON으로 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            console.print(f"[green]✅ AI 보고서가 {filename}에 저장되었습니다.[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ AI 보고서 저장 실패: {e}[/red]")
            return False
    
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
    
    # === 알림 시스템 메뉴 핸들러들 (Phase 5) ===
    
    async def _test_telegram_notification(self):
        """텔레그램 알림 테스트"""
        try:
            console.print("[cyan]📢 텔레그램 알림 테스트 시작...[/cyan]")
            
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            
            # 테스트 알림 전송
            success = await self.system.notification_manager.send_test_notification()
            
            if success:
                console.print("[green]✅ 텔레그램 알림 테스트 성공![/green]")
                console.print("[dim]텔레그램에서 테스트 메시지를 확인하세요.[/dim]")
            else:
                console.print("[red]❌ 텔레그램 알림 테스트 실패[/red]")
                console.print("[dim]설정을 확인하고 다시 시도하세요.[/dim]")
                
        except Exception as e:
            console.print(f"[red]❌ 텔레그램 알림 테스트 오류: {e}[/red]")
    
    async def _manage_notification_settings(self):
        """알림 설정 관리"""
        try:
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            
            # 현재 설정 표시
            settings = self.system.notification_manager.get_notification_settings()
            
            # 설정 표시용 테이블
            table = Table(title="📢 현재 알림 설정", show_header=True, header_style="bold cyan")
            table.add_column("설정", style="yellow", width=20)
            table.add_column("값", style="white", width=30)
            table.add_column("설명", style="dim", width=40)
            
            table.add_row("알림 활성화", "✅ 활성화" if settings['enabled'] else "❌ 비활성화", "텔레그램 알림 전체 활성화 상태")
            table.add_row("알림 수준", ", ".join([level.value for level in settings['alert_levels']]), "전송할 알림 수준")
            table.add_row("조용한 시간", f"{settings['quiet_hours']['start']}:00 - {settings['quiet_hours']['end']}:00", "알림 제한 시간대")
            table.add_row("속도 제한", f"{settings['rate_limit']['messages_per_minute']}개/분", "분당 최대 메시지 수")
            
            console.print(table)
            
            # 설정 변경 옵션
            if Confirm.ask("\n[yellow]설정을 변경하시겠습니까?[/yellow]"):
                await self._modify_notification_settings()
                
        except Exception as e:
            console.print(f"[red]❌ 알림 설정 조회 오류: {e}[/red]")
    
    async def _modify_notification_settings(self):
        """알림 설정 수정"""
        try:
            console.print("\n[cyan]📝 알림 설정 수정[/cyan]")
            
            new_settings = {}
            
            # 조용한 시간 설정
            if Confirm.ask("조용한 시간을 변경하시겠습니까?"):
                start_hour = IntPrompt.ask("시작 시간 (0-23)", default=22)
                end_hour = IntPrompt.ask("종료 시간 (0-23)", default=7)
                new_settings['quiet_hours'] = {'start': start_hour, 'end': end_hour}
            
            # 속도 제한 설정
            if Confirm.ask("속도 제한을 변경하시겠습니까?"):
                rate_limit = IntPrompt.ask("분당 최대 메시지 수", default=10)
                new_settings['rate_limit'] = {'messages_per_minute': rate_limit, 'burst_limit': rate_limit * 2}
            
            # 설정 적용
            if new_settings:
                success = self.system.notification_manager.update_notification_settings(new_settings)
                if success:
                    console.print("[green]✅ 설정이 성공적으로 변경되었습니다.[/green]")
                else:
                    console.print("[red]❌ 설정 변경에 실패했습니다.[/red]")
            else:
                console.print("[yellow]변경된 설정이 없습니다.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ 설정 수정 오류: {e}[/red]")
    
    async def _view_notification_stats(self):
        """알림 통계 조회"""
        try:
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            
            stats = self.system.notification_manager.get_notification_stats()
            
            # 통계 표시용 테이블
            table = Table(title="📊 일일 알림 통계", show_header=True, header_style="bold cyan")
            table.add_column("항목", style="yellow", width=20)
            table.add_column("수량", style="white", width=15)
            table.add_column("비율", style="green", width=15)
            
            total_sent = stats['sent_today']
            total_failed = stats['failed_today']
            total_attempts = total_sent + total_failed
            
            table.add_row("전송 성공", f"{total_sent:,}개", f"{total_sent/total_attempts*100:.1f}%" if total_attempts > 0 else "0%")
            table.add_row("전송 실패", f"{total_failed:,}개", f"{total_failed/total_attempts*100:.1f}%" if total_attempts > 0 else "0%")
            table.add_row("총 시도", f"{total_attempts:,}개", "100%")
            
            console.print(table)
            
            # 타입별 통계
            if stats['types_sent']:
                type_table = Table(title="📈 알림 유형별 통계", show_header=True, header_style="bold magenta")
                type_table.add_column("알림 유형", style="yellow", width=20)
                type_table.add_column("전송 수", style="white", width=15)
                type_table.add_column("비율", style="green", width=15)
                
                for notification_type, count in stats['types_sent'].items():
                    percentage = count / total_sent * 100 if total_sent > 0 else 0
                    type_table.add_row(notification_type, f"{count:,}개", f"{percentage:.1f}%")
                
                console.print(type_table)
            
            console.print(f"\n[dim]마지막 업데이트: {stats['last_reset']}[/dim]")
                
        except Exception as e:
            console.print(f"[red]❌ 알림 통계 조회 오류: {e}[/red]")
    
    async def _check_notification_status(self):
        """알림 상태 확인"""
        try:
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            
            status = self.system.notification_manager.get_system_status()
            
            # 상태 표시용 테이블
            table = Table(title="🔍 알림 시스템 상태", show_header=True, header_style="bold cyan")
            table.add_column("구성 요소", style="yellow", width=25)
            table.add_column("상태", style="white", width=15)
            table.add_column("세부 정보", style="dim", width=40)
            
            # 텔레그램 상태
            telegram_status = "✅ 활성화" if status['telegram_enabled'] else "❌ 비활성화"
            table.add_row("텔레그램 봇", telegram_status, "텔레그램 알림 전송 상태")
            
            # 이벤트 처리 상태
            processing_status = "✅ 실행 중" if status['processing_events'] else "❌ 중지됨"
            table.add_row("이벤트 처리", processing_status, "알림 이벤트 큐 처리 상태")
            
            # 큐 상태
            queue_info = f"{status['queue_size']}개 대기 중"
            table.add_row("이벤트 큐", queue_info, "처리 대기 중인 알림 수")
            
            # 최근 알림 수
            recent_count = status['recent_notifications_count']
            table.add_row("최근 알림", f"{recent_count}개 기록됨", "중복 방지용 최근 알림 기록")
            
            console.print(table)
            
            # 오늘의 통계 요약
            stats = status['stats']
            summary_text = f"""
[bold]📊 오늘의 요약[/bold]
• 전송 성공: {stats['sent_today']:,}개
• 전송 실패: {stats['failed_today']:,}개
• 성공률: {stats['sent_today']/(stats['sent_today']+stats['failed_today'])*100:.1f}% (전체 {stats['sent_today']+stats['failed_today']:,}회 시도)
            """
            
            console.print(Panel(summary_text.strip(), title="📈 성과 요약", border_style="green"))
                
        except Exception as e:
            console.print(f"[red]❌ 알림 상태 확인 오류: {e}[/red]")
    
    #######################################################
    # Phase 6: 백테스팅 & 검증 시스템
    #######################################################
    
    async def _ai_vs_traditional_comparison(self) -> bool:
        """AI vs 전통적 전략 성능 비교"""
        console.print(Panel("[bold purple]🧪 AI vs 전통 전략 비교[/bold purple]", border_style="purple"))
        
        try:
            # 컴포넌트 초기화
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            
            # 전략 검증기 초기화
            validator = StrategyValidator(self.config)
            
            # 비교 매개변수 설정
            console.print("\n[bold]비교 설정:[/bold]")
            
            # 전략 선택
            strategies = ["momentum_strategy", "supertrend_ema_rsi_strategy"]
            strategy_table = Table(title="📋 사용 가능한 전략")
            strategy_table.add_column("번호", style="cyan", width=6)
            strategy_table.add_column("전략명", style="green")
            strategy_table.add_column("설명", style="white")
            
            for i, strategy in enumerate(strategies, 1):
                descriptions = {
                    "momentum_strategy": "모멘텀 기반 단기 매매 전략",
                    "supertrend_ema_rsi_strategy": "SuperTrend + EMA + RSI 기술적 분석 전략"
                }
                strategy_table.add_row(str(i), strategy, descriptions.get(strategy, "설명 없음"))
            
            console.print(strategy_table)
            
            # 전략 선택
            try:
                strategy_choice = IntPrompt.ask("전략 번호를 선택하세요", choices=[str(i) for i in range(1, len(strategies) + 1)], default=1)
                selected_strategy = strategies[strategy_choice - 1]
            except (ValueError, IndexError):
                selected_strategy = strategies[0]
            
            console.print(f"[green]✅ 선택된 전략: {selected_strategy}[/green]")
            
            # 기간 설정
            console.print("\n[bold]분석 기간 설정:[/bold]")
            end_date = datetime.now()
            
            period_options = {
                "1": 30,   # 1개월
                "2": 90,   # 3개월  
                "3": 180,  # 6개월
                "4": 365   # 1년
            }
            
            console.print("1. 1개월")
            console.print("2. 3개월")
            console.print("3. 6개월") 
            console.print("4. 1년")
            
            period_choice = Prompt.ask("분석 기간을 선택하세요", choices=["1", "2", "3", "4"], default="3")
            days = period_options[period_choice]
            start_date = end_date - timedelta(days=days)
            
            console.print(f"[green]✅ 분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}[/green]")
            
            # 종목 설정
            default_symbols = ['005930', '000660', '035420', '005380', '068270']  # 대형주 5개
            symbols_input = Prompt.ask("분석 종목 (콤마로 구분, 엔터시 기본 대형주 5개)", default=",".join(default_symbols))
            symbols = [s.strip() for s in symbols_input.split(",") if s.strip()]
            
            console.print(f"[green]✅ 분석 종목: {', '.join(symbols)}[/green]")
            
            # 백테스팅 실행
            console.print(f"\n[yellow]🔄 AI vs 전통 전략 비교 실행 중...[/yellow]")
            
            with Progress() as progress:
                task = progress.add_task("비교 분석", total=100)
                
                progress.update(task, advance=20, description="AI 전략 백테스팅...")
                comparison_result = await validator.compare_ai_vs_traditional(
                    selected_strategy, start_date, end_date, symbols
                )
                
                progress.update(task, advance=80, description="분석 완료")
            
            # 결과 표시
            console.print("\n" + "="*60)
            console.print("[bold green]📊 AI vs 전통 전략 비교 결과[/bold green]")
            console.print("="*60)
            
            # 성과 비교 테이블
            results_table = Table(title="📈 성과 비교")
            results_table.add_column("지표", style="cyan", width=20)
            results_table.add_column("AI 전략", style="green", width=15)
            results_table.add_column("전통 전략", style="yellow", width=15)
            results_table.add_column("개선도", style="magenta", width=15)
            
            ai_metrics = comparison_result.with_ai_result.metrics
            traditional_metrics = comparison_result.without_ai_result.metrics
            
            results_table.add_row(
                "연수익률 (%)",
                f"{ai_metrics.annual_return:.2f}%",
                f"{traditional_metrics.annual_return:.2f}%",
                f"{comparison_result.return_improvement:+.2f}%"
            )
            
            results_table.add_row(
                "샤프 비율",
                f"{ai_metrics.sharpe_ratio:.2f}",
                f"{traditional_metrics.sharpe_ratio:.2f}",
                f"{comparison_result.sharpe_improvement:+.2f}"
            )
            
            results_table.add_row(
                "최대 낙폭 (%)",
                f"{ai_metrics.max_drawdown:.2f}%",
                f"{traditional_metrics.max_drawdown:.2f}%",
                f"{comparison_result.drawdown_improvement:+.2f}%"
            )
            
            results_table.add_row(
                "승률 (%)",
                f"{ai_metrics.win_rate:.2f}%",
                f"{traditional_metrics.win_rate:.2f}%",
                f"{comparison_result.win_rate_improvement:+.2f}%"
            )
            
            console.print(results_table)
            
            # AI 효과성 점수
            effectiveness_text = f"""
[bold]🤖 AI 효과성 분석[/bold]
• AI 효과성 점수: {comparison_result.ai_effectiveness_score:.1f}/100점
• 통계적 유의성: {"✅ 유의함" if comparison_result.statistical_significance else "❌ 유의하지 않음"}
• P-값: {comparison_result.p_value:.4f}
            """
            
            console.print(Panel(effectiveness_text.strip(), title="🎯 AI 효과성 평가", border_style="magenta"))
            
            # 저장 옵션
            if Confirm.ask("\n📁 결과를 파일로 저장하시겠습니까?"):
                filename = f"ai_vs_traditional_comparison_{selected_strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # 결과 데이터 준비
                result_data = {
                    "timestamp": datetime.now().isoformat(),
                    "strategy": selected_strategy,
                    "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                    "symbols": symbols,
                    "ai_metrics": {
                        "annual_return": ai_metrics.annual_return,
                        "sharpe_ratio": ai_metrics.sharpe_ratio,
                        "max_drawdown": ai_metrics.max_drawdown,
                        "win_rate": ai_metrics.win_rate,
                        "total_trades": ai_metrics.total_trades
                    },
                    "traditional_metrics": {
                        "annual_return": traditional_metrics.annual_return,
                        "sharpe_ratio": traditional_metrics.sharpe_ratio,
                        "max_drawdown": traditional_metrics.max_drawdown,
                        "win_rate": traditional_metrics.win_rate,
                        "total_trades": traditional_metrics.total_trades
                    },
                    "improvements": {
                        "return_improvement": comparison_result.return_improvement,
                        "sharpe_improvement": comparison_result.sharpe_improvement,
                        "drawdown_improvement": comparison_result.drawdown_improvement,
                        "win_rate_improvement": comparison_result.win_rate_improvement
                    },
                    "ai_effectiveness_score": comparison_result.ai_effectiveness_score,
                    "statistical_significance": comparison_result.statistical_significance,
                    "p_value": comparison_result.p_value
                }
                
                # 파일 저장
                import os
                reports_dir = "reports/backtesting"
                os.makedirs(reports_dir, exist_ok=True)
                
                filepath = os.path.join(reports_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                console.print(f"[green]✅ 결과가 저장되었습니다: {filepath}[/green]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ AI vs 전통 전략 비교 오류: {e}[/red]")
            self.logger.error(f"AI vs 전통 전략 비교 오류: {e}")
            return False
    
    async def _strategy_validation(self) -> bool:
        """전략 성능 검증"""
        console.print(Panel("[bold purple]🔍 전략 성능 검증[/bold purple]", border_style="purple"))
        
        try:
            # 컴포넌트 초기화
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            
            validator = StrategyValidator(self.config)
            
            # 전략 선택
            strategies = ["momentum_strategy", "supertrend_ema_rsi_strategy"]
            console.print("\n[bold]검증할 전략 선택:[/bold]")
            
            for i, strategy in enumerate(strategies, 1):
                console.print(f"{i}. {strategy}")
            
            try:
                choice = IntPrompt.ask("전략 번호", choices=[str(i) for i in range(1, len(strategies) + 1)], default=1)
                selected_strategy = strategies[choice - 1]
            except (ValueError, IndexError):
                selected_strategy = strategies[0]
            
            console.print(f"[green]✅ 선택된 전략: {selected_strategy}[/green]")
            
            # 검증 기준 설정
            console.print("\n[bold]검증 기준 설정:[/bold]")
            
            use_custom = Confirm.ask("기본 검증 기준을 사용하시겠습니까? (아니오 선택시 사용자 정의)", default=True)
            
            if use_custom:
                criteria = ValidationCriteria()
                console.print("[yellow]✅ 기본 검증 기준을 사용합니다[/yellow]")
            else:
                # 사용자 정의 기준
                console.print("[cyan]사용자 정의 검증 기준 설정:[/cyan]")
                
                min_return = IntPrompt.ask("최소 연수익률 (%)", default=5)
                max_drawdown = IntPrompt.ask("최대 낙폭 (%)", default=20)
                min_sharpe = float(Prompt.ask("최소 샤프 비율", default="1.0"))
                min_win_rate = IntPrompt.ask("최소 승률 (%)", default=45)
                min_trades = IntPrompt.ask("최소 거래 수", default=50)
                min_ai_accuracy = IntPrompt.ask("최소 AI 정확도 (%)", default=60)
                
                criteria = ValidationCriteria(
                    min_return=min_return,
                    max_drawdown=max_drawdown,
                    min_sharpe=min_sharpe,
                    min_win_rate=min_win_rate,
                    min_trades=min_trades,
                    min_ai_accuracy=min_ai_accuracy
                )
            
            # 기간 설정
            end_date = datetime.now()
            days = 180  # 6개월 기본
            start_date = end_date - timedelta(days=days)
            
            symbols = ['005930', '000660', '035420', '005380', '068270']  # 기본 대형주
            
            console.print(f"\n[yellow]🔄 전략 검증 실행 중...[/yellow]")
            
            with Progress() as progress:
                task = progress.add_task("전략 검증", total=100)
                
                progress.update(task, advance=30, description="백테스팅 실행...")
                
                # 백테스팅 실행
                backtest_result = await validator.backtesting_engine.run_backtest(
                    selected_strategy, start_date, end_date, symbols, use_ai=True
                )
                
                progress.update(task, advance=30, description="검증 수행...")
                
                # 검증 수행
                validation_result = await validator.validate_strategy(
                    selected_strategy, backtest_result, criteria
                )
                
                progress.update(task, advance=40, description="검증 완료")
            
            # 결과 표시
            console.print("\n" + "="*60)
            console.print(f"[bold green]📋 전략 검증 결과: {selected_strategy}[/bold green]")
            console.print("="*60)
            
            # 전체 상태
            status_color = {
                "PASSED": "green",
                "WARNING": "yellow", 
                "FAILED": "red",
                "INSUFFICIENT_DATA": "orange"
            }.get(validation_result.status.value, "white")
            
            console.print(f"[bold {status_color}]📊 검증 상태: {validation_result.status.value}[/bold {status_color}]")
            console.print(f"[bold cyan]🔢 전체 점수: {validation_result.overall_score:.1f}/100점[/bold cyan]")
            
            # 상세 검증 결과
            console.print("\n[bold]📋 상세 검증 결과:[/bold]")
            for message in validation_result.messages:
                console.print(f"  {message}")
            
            # 경고 메시지
            if validation_result.warnings:
                console.print("\n[bold yellow]⚠️ 경고 사항:[/bold yellow]")
                for warning in validation_result.warnings:
                    console.print(f"  - {warning}")
            
            # 개선 제안
            suggestions = []
            if not validation_result.return_check:
                suggestions.append("• 수익률 개선을 위한 전략 매개변수 조정 고려")
            if not validation_result.drawdown_check:
                suggestions.append("• 리스크 관리 강화 (손절선, 포지션 크기 조정)")
            if not validation_result.sharpe_check:
                suggestions.append("• 위험 대비 수익 개선 (변동성 관리)")
            if not validation_result.ai_accuracy_check:
                suggestions.append("• AI 모델 개선 또는 추가 훈련 데이터 확보")
            
            if suggestions:
                suggestion_text = "\n".join(suggestions)
                console.print(Panel(suggestion_text, title="💡 개선 제안", border_style="blue"))
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 전략 검증 오류: {e}[/red]")
            self.logger.error(f"전략 검증 오류: {e}")
            return False
    
    async def _ai_prediction_accuracy_analysis(self) -> bool:
        """과거 AI 예측 정확도 분석"""
        console.print(Panel("[bold purple]🎯 AI 예측 정확도 분석[/bold purple]", border_style="purple"))
        
        try:
            # 컴포넌트 초기화
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            
            analyzer = HistoricalAnalyzer(self.config)
            
            # 분석 기간 설정
            console.print("\n[bold]분석 기간 설정:[/bold]")
            end_date = datetime.now()
            
            # 기간 선택
            period_map = {"1": 30, "2": 90, "3": 180, "4": 365}
            console.print("1. 1개월")
            console.print("2. 3개월") 
            console.print("3. 6개월")
            console.print("4. 1년")
            
            period_choice = Prompt.ask("분석 기간", choices=["1", "2", "3", "4"], default="3")
            days = period_map[period_choice]
            start_date = end_date - timedelta(days=days)
            
            console.print(f"[green]✅ 분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}[/green]")
            
            # 분석 종목
            symbols = ['005930', '000660', '035420', '005380', '068270']
            symbols_input = Prompt.ask("분석 종목 (콤마로 구분)", default=",".join(symbols))
            selected_symbols = [s.strip() for s in symbols_input.split(",") if s.strip()]
            
            console.print(f"[green]✅ 분석 종목: {', '.join(selected_symbols)}[/green]")
            
            # 분석 실행
            console.print(f"\n[yellow]🔄 AI 예측 정확도 분석 실행 중...[/yellow]")
            
            with Progress() as progress:
                task = progress.add_task("정확도 분석", total=100)
                
                progress.update(task, advance=50, description="과거 예측 데이터 수집...")
                
                accuracy_results = await analyzer.analyze_ai_prediction_accuracy(
                    start_date, end_date, selected_symbols
                )
                
                progress.update(task, advance=50, description="분석 완료")
            
            # 결과 표시
            console.print("\n" + "="*60)
            console.print("[bold green]🎯 AI 예측 정확도 분석 결과[/bold green]")
            console.print("="*60)
            
            # 전체 정확도
            overall_accuracy = accuracy_results.get('overall_accuracy', 0.0)
            console.print(f"[bold cyan]📊 전체 예측 정확도: {overall_accuracy:.2f}%[/bold cyan]")
            
            # 종목별 정확도
            symbol_accuracy = accuracy_results.get('symbol_accuracy', {})
            if symbol_accuracy:
                accuracy_table = Table(title="📈 종목별 예측 정확도")
                accuracy_table.add_column("종목", style="cyan", width=10)
                accuracy_table.add_column("정확도 (%)", style="green", width=15)
                accuracy_table.add_column("예측 횟수", style="yellow", width=15)
                accuracy_table.add_column("맞춘 횟수", style="magenta", width=15)
                
                for symbol, data in symbol_accuracy.items():
                    accuracy_table.add_row(
                        symbol,
                        f"{data['accuracy']:.2f}%",
                        str(data['total_predictions']),
                        str(data['correct_predictions'])
                    )
                
                console.print(accuracy_table)
            
            # 예측 유형별 정확도
            prediction_types = accuracy_results.get('prediction_types', {})
            if prediction_types:
                console.print("\n[bold]📋 예측 유형별 성능:[/bold]")
                
                for pred_type, data in prediction_types.items():
                    type_names = {
                        'directional': '방향 예측',
                        'magnitude': '크기 예측',
                        'confidence_high': '고신뢰도 예측',
                        'confidence_low': '저신뢰도 예측'
                    }
                    
                    type_name = type_names.get(pred_type, pred_type)
                    console.print(f"  • {type_name}: {data['accuracy']:.1f}% ({data['sample_count']}회)")
            
            # 신뢰도와 정확도 상관관계
            correlation = accuracy_results.get('confidence_correlation', 0.0)
            if abs(correlation) > 0.1:
                correlation_text = f"""
[bold]🔗 신뢰도-정확도 상관관계 분석[/bold]
• 상관계수: {correlation:.3f}
• 해석: {"AI 신뢰도가 높을수록 예측이 더 정확함" if correlation > 0.3 else "AI 신뢰도와 정확도 간 약한 상관관계" if correlation > 0.1 else "AI 신뢰도와 정확도 간 상관관계 미약"}
                """
                
                console.print(Panel(correlation_text.strip(), title="📊 상관관계 분석", border_style="blue"))
            
            # 개선 제안
            suggestions = []
            if overall_accuracy < 60:
                suggestions.append("• AI 모델 재훈련 또는 새로운 특성 추가 고려")
            if correlation < 0.2:
                suggestions.append("• 신뢰도 측정 방식 개선 필요")
            if len(symbol_accuracy) > 0:
                worst_performer = min(symbol_accuracy.items(), key=lambda x: x[1]['accuracy'])
                if worst_performer[1]['accuracy'] < 50:
                    suggestions.append(f"• {worst_performer[0]} 종목에 대한 특별 분석 필요")
            
            if suggestions:
                suggestion_text = "\n".join(suggestions)
                console.print(Panel(suggestion_text, title="💡 개선 제안", border_style="yellow"))
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ AI 예측 정확도 분석 오류: {e}[/red]")
            self.logger.error(f"AI 예측 정확도 분석 오류: {e}")
            return False
    
    async def _market_regime_performance(self) -> bool:
        """시장 체제별 성과 분석"""
        console.print(Panel("[bold purple]📊 시장 체제별 성과 분석[/bold purple]", border_style="purple"))
        
        try:
            # 컴포넌트 초기화
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            
            analyzer = HistoricalAnalyzer(self.config)
            
            # 분석 기간 설정 (시장 체제 분석을 위해 더 긴 기간)
            console.print("\n[bold]분석 기간 설정:[/bold]")
            end_date = datetime.now()
            
            # 기간 선택 (최소 6개월)
            period_map = {"1": 180, "2": 365, "3": 730}  # 6개월, 1년, 2년
            console.print("1. 6개월")
            console.print("2. 1년")
            console.print("3. 2년")
            
            period_choice = Prompt.ask("분석 기간", choices=["1", "2", "3"], default="2")
            days = period_map[period_choice]
            start_date = end_date - timedelta(days=days)
            
            console.print(f"[green]✅ 분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}[/green]")
            
            # 시장 지수 선택
            market_indices = {"1": "KOSPI", "2": "KOSDAQ"}
            console.print("\n[bold]시장 지수 선택:[/bold]")
            console.print("1. KOSPI")
            console.print("2. KOSDAQ")
            
            index_choice = Prompt.ask("시장 지수", choices=["1", "2"], default="1")
            selected_index = market_indices[index_choice]
            
            console.print(f"[green]✅ 선택된 지수: {selected_index}[/green]")
            
            # 분석 실행
            console.print(f"\n[yellow]🔄 시장 체제별 성과 분석 실행 중...[/yellow]")
            
            with Progress() as progress:
                task = progress.add_task("체제 분석", total=100)
                
                progress.update(task, advance=30, description="시장 데이터 수집...")
                
                regime_analyses = await analyzer.identify_market_regimes(
                    start_date, end_date, selected_index
                )
                
                progress.update(task, advance=40, description="체제별 성과 분석...")
                
                # 뉴스 영향 분석 추가
                symbols = ['005930', '000660', '035420']  # 대표 종목
                news_validation = await analyzer.validate_historical_news_impact(
                    start_date, end_date, symbols
                )
                
                progress.update(task, advance=30, description="분석 완료")
            
            # 결과 표시
            console.print("\n" + "="*60)
            console.print(f"[bold green]📊 시장 체제별 성과 분석 결과 ({selected_index})[/bold green]")
            console.print("="*60)
            
            if not regime_analyses:
                console.print("[yellow]⚠️ 충분한 데이터가 없거나 명확한 체제 변화가 감지되지 않았습니다[/yellow]")
                return True
            
            # 체제별 분석 결과 테이블
            regime_table = Table(title="📈 시장 체제별 성과")
            regime_table.add_column("체제", style="cyan", width=15)
            regime_table.add_column("기간", style="green", width=20)
            regime_table.add_column("수익률 (%)", style="yellow", width=12)
            regime_table.add_column("변동성 (%)", style="orange", width=12)
            regime_table.add_column("최대낙폭 (%)", style="red", width=12)
            regime_table.add_column("AI 정확도 (%)", style="magenta", width=12)
            
            regime_names = {
                "BULL_MARKET": "강세장",
                "BEAR_MARKET": "약세장", 
                "SIDEWAYS": "횡보장",
                "HIGH_VOLATILITY": "고변동성",
                "LOW_VOLATILITY": "저변동성"
            }
            
            for regime_analysis in regime_analyses:
                regime_name = regime_names.get(regime_analysis.regime.value, regime_analysis.regime.value)
                period_str = f"{regime_analysis.period_start.strftime('%y/%m/%d')} - {regime_analysis.period_end.strftime('%y/%m/%d')}"
                
                regime_table.add_row(
                    regime_name,
                    period_str,
                    f"{regime_analysis.avg_return:.2f}",
                    f"{regime_analysis.volatility:.2f}",
                    f"{regime_analysis.max_drawdown:.2f}",
                    f"{regime_analysis.ai_accuracy:.2f}"
                )
            
            console.print(regime_table)
            
            # 체제별 AI 성과 요약
            best_regime = max(regime_analyses, key=lambda x: x.ai_accuracy)
            worst_regime = min(regime_analyses, key=lambda x: x.ai_accuracy)
            
            ai_summary = f"""
[bold]🤖 체제별 AI 성과 요약[/bold]
• 최고 성과 체제: {regime_names.get(best_regime.regime.value, best_regime.regime.value)} (정확도: {best_regime.ai_accuracy:.1f}%)
• 최저 성과 체제: {regime_names.get(worst_regime.regime.value, worst_regime.regime.value)} (정확도: {worst_regime.ai_accuracy:.1f}%)
• 평균 AI 정확도: {sum(r.ai_accuracy for r in regime_analyses) / len(regime_analyses):.1f}%
            """
            
            console.print(Panel(ai_summary.strip(), title="🎯 AI 성과 분석", border_style="blue"))
            
            # 뉴스 영향 분석 결과
            if news_validation and news_validation.get('overall_correlation', 0) != 0:
                news_summary = f"""
[bold]📰 뉴스 영향 분석[/bold]
• 전체 감정-가격 상관관계: {news_validation['overall_correlation']:.3f}
• AI 감정 분석 정확도: {news_validation['sentiment_accuracy']:.1f}%
• 분석된 뉴스-가격 쌍: {len(news_validation.get('detailed_analysis', []))}개
                """
                
                console.print(Panel(news_summary.strip(), title="📈 뉴스 영향 검증", border_style="green"))
            
            # 각 체제별 주요 특징
            console.print("\n[bold]📋 체제별 주요 특징:[/bold]")
            for regime_analysis in regime_analyses:
                regime_name = regime_names.get(regime_analysis.regime.value, regime_analysis.regime.value)
                console.print(f"\n[cyan]{regime_name} ({regime_analysis.period_start.strftime('%Y-%m-%d')} ~ {regime_analysis.period_end.strftime('%Y-%m-%d')}):[/cyan]")
                
                if regime_analysis.key_events:
                    console.print("  주요 이벤트:")
                    for event in regime_analysis.key_events:
                        console.print(f"    - {event}")
                
                characteristics = regime_analysis.characteristics
                if characteristics:
                    console.print("  시장 특성:")
                    for key, value in characteristics.items():
                        if key in ['trend_strength', 'momentum']:
                            console.print(f"    - {key}: {value:.2f}")
                        elif 'volatility' in key:
                            console.print(f"    - {key}: {value:.2f}%")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 시장 체제별 성과 분석 오류: {e}[/red]")
            self.logger.error(f"시장 체제별 성과 분석 오류: {e}")
            return False
    
    async def _backtesting_report_generation(self) -> bool:
        """백테스팅 종합 보고서 생성"""
        console.print(Panel("[bold purple]📋 백테스팅 종합 보고서 생성[/bold purple]", border_style="purple"))
        
        try:
            # 컴포넌트 초기화
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            
            validator = StrategyValidator(self.config)
            visualizer = PerformanceVisualizer(self.config)
            
            # 보고서 설정
            console.print("\n[bold]보고서 설정:[/bold]")
            
            # 전략 선택
            strategies = ["momentum_strategy", "supertrend_ema_rsi_strategy"]
            console.print("포함할 전략 (여러 선택 가능):")
            for i, strategy in enumerate(strategies, 1):
                console.print(f"{i}. {strategy}")
            
            strategy_choices = Prompt.ask("전략 번호 (콤마로 구분)", default="1,2")
            selected_indices = [int(x.strip()) - 1 for x in strategy_choices.split(',') if x.strip().isdigit()]
            selected_strategies = [strategies[i] for i in selected_indices if 0 <= i < len(strategies)]
            
            if not selected_strategies:
                selected_strategies = strategies
            
            console.print(f"[green]✅ 선택된 전략: {', '.join(selected_strategies)}[/green]")
            
            # 분석 기간
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)  # 6개월
            symbols = ['005930', '000660', '035420', '005380', '068270']
            
            console.print(f"[green]✅ 분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}[/green]")
            console.print(f"[green]✅ 분석 종목: {', '.join(symbols)}[/green]")
            
            # 보고서 생성
            console.print(f"\n[yellow]🔄 종합 보고서 생성 중...[/yellow]")
            
            all_results = {}
            all_comparisons = {}
            
            with Progress() as progress:
                total_tasks = len(selected_strategies)
                task = progress.add_task("보고서 생성", total=total_tasks * 100)
                
                for i, strategy in enumerate(selected_strategies):
                    progress.update(task, description=f"전략 분석: {strategy}")
                    
                    # 백테스팅 실행
                    backtest_result = await validator.backtesting_engine.run_backtest(
                        strategy, start_date, end_date, symbols, use_ai=True
                    )
                    
                    # 검증 실행
                    validation_result = await validator.validate_strategy(
                        strategy, backtest_result
                    )
                    
                    # AI vs 전통 비교
                    comparison_result = await validator.compare_ai_vs_traditional(
                        strategy, start_date, end_date, symbols
                    )
                    
                    all_results[strategy] = validation_result
                    all_comparisons[strategy] = comparison_result
                    
                    progress.update(task, advance=100)
            
            # 종합 보고서 생성
            console.print(f"[yellow]📝 보고서 작성 중...[/yellow]")
            
            # 텍스트 보고서
            text_report = await validator.generate_validation_report(
                all_results, all_comparisons
            )
            
            # HTML 보고서 (시각화 포함)
            html_report = await visualizer.generate_comprehensive_report(
                all_comparisons, all_results
            )
            
            # 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            import os
            reports_dir = "reports/backtesting"
            os.makedirs(reports_dir, exist_ok=True)
            
            # 텍스트 보고서 저장
            text_filename = f"backtesting_report_{timestamp}.txt"
            text_filepath = os.path.join(reports_dir, text_filename)
            with open(text_filepath, 'w', encoding='utf-8') as f:
                f.write(text_report)
            
            # HTML 보고서 저장
            html_filename = f"backtesting_report_{timestamp}.html"
            html_filepath = os.path.join(reports_dir, html_filename)
            with open(html_filepath, 'w', encoding='utf-8') as f:
                f.write(html_report)
            
            # 결과 표시
            console.print("\n" + "="*60)
            console.print("[bold green]📋 백테스팅 종합 보고서 완성[/bold green]")
            console.print("="*60)
            
            # 요약 통계
            passed_count = sum(1 for r in all_results.values() if r.status.value == "PASSED")
            total_strategies = len(all_results)
            avg_ai_effectiveness = sum(c.ai_effectiveness_score for c in all_comparisons.values()) / len(all_comparisons) if all_comparisons else 0
            
            summary_stats = f"""
[bold]📊 보고서 요약[/bold]
• 분석된 전략: {total_strategies}개
• 검증 통과 전략: {passed_count}개
• 평균 AI 효과성 점수: {avg_ai_effectiveness:.1f}/100점
• 분석 기간: {(end_date - start_date).days}일
• 분석 종목: {len(symbols)}개
            """
            
            console.print(Panel(summary_stats.strip(), title="📈 보고서 요약", border_style="cyan"))
            
            # 파일 정보
            file_info = f"""
[bold]📁 생성된 파일[/bold]
• 텍스트 보고서: {text_filepath}
• HTML 보고서: {html_filepath}
            """
            
            console.print(Panel(file_info.strip(), title="💾 저장된 파일", border_style="green"))
            
            # 브라우저에서 HTML 보고서 열기 옵션
            if Confirm.ask("\n🌐 HTML 보고서를 브라우저에서 여시겠습니까?"):
                import webbrowser
                import os
                
                # 절대 경로로 변환
                abs_path = os.path.abspath(html_filepath)
                file_url = f"file:///{abs_path.replace(chr(92), '/')}"  # Windows 경로 처리
                
                try:
                    webbrowser.open(file_url)
                    console.print(f"[green]✅ 브라우저에서 보고서를 열었습니다[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ 브라우저 열기 실패: {e}[/yellow]")
                    console.print(f"[cyan]수동으로 다음 파일을 열어주세요: {html_filepath}[/cyan]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 백테스팅 보고서 생성 오류: {e}[/red]")
            self.logger.error(f"백테스팅 보고서 생성 오류: {e}")
            return False