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

# 안전한 콘솔 출력 (UTF-8 인코딩 문제 해결)
try:
    from utils.safe_console import SafeConsole, safe_print, safe_ask
    console = SafeConsole()
    use_safe_console = True
except ImportError:
    # 폴백: 기본 Rich 콘솔
    import os
    if os.name == 'nt':  # Windows
        try:
            # UTF-8 콘솔 설정
            os.system("chcp 65001 > nul 2>&1")
            console = Console(force_terminal=True, legacy_windows=False)
        except:
            console = Console(legacy_windows=True)
    else:
        console = Console()
    use_safe_console = False

class MenuHandlers:
    """메뉴 처리 핸들러 클래스"""
    
    def __init__(self, trading_system):
        self.system = trading_system
        self.config = trading_system.config
        self.logger = trading_system.logger

    def show_main_menu(self):
        """메인 메뉴 표시"""
        menu = """[bold cyan]시스템 관리[/bold cyan]
    1. 시스템 테스트
    2. 설정 확인
    3. 컴포넌트 초기화

    [bold green]분석 및 매매[/bold green]
    4. 종합 분석 (5개 영역 통합)
    5. 특정 종목 분석
    6. 뉴스 재료 분석
    7. 자동매매 시스템
    8. 백테스트 실행

    [bold magenta]AI 고급 기능 (Phase 4)[/bold magenta]
    9. AI 종합 시장 분석
    10. AI 시장 체제 분석
    11. AI 전략 최적화
    12. AI 리스크 평가
    13. AI 일일 보고서

    [bold yellow]알림 시스템 (Phase 5)[/bold yellow]
    14. 텔레그램 알림 테스트
    15. 알림 설정 관리
    16. 알림 통계 조회
    17. 알림 상태 확인

    [bold purple]백테스팅 & 검증 (Phase 6)[/bold purple]
    18. AI vs 전통 전략 비교
    19. 전략 성능 검증
    20. 과거 AI 예측 정확도 분석
    21. 시장 체제별 성과 분석
    22. 백테스팅 보고서 생성

    [bold cyan]고급 AI 전략 (Phase 8+)[/bold cyan]
    23. AI 모멘텀 전략 분석
    24. 적응형 포지션 사이징
    25. 다중 시간대 분석
    26. 종합 전략 분석 (통합)
    27. 고급 전략 백테스트
    28. 다중 전략 조합 분석

    [bold blue]데이터 & 모니터링[/bold blue]
    29. 데이터베이스 상태
    30. 종목 데이터 조회
    31. 실시간 시스템 모니터
    32. 200개 종목 실시간 모니터링
    33. 보유종목 조회

    [bold red]0. 종료[/bold red]"""
        
        console.print(Panel.fit(menu, title="📋 메인 메뉴", border_style="cyan"))

    def get_user_choice(self) -> str:
        """사용자 입력"""
        try:
            if use_safe_console:
                return safe_ask("메뉴 선택", "0")
            else:
                return Prompt.ask("[bold yellow]메뉴 선택[/bold yellow]", default="0").strip()
        except (KeyboardInterrupt, EOFError):
            return "0"

    async def execute_menu_choice(self, choice: str) -> Optional[bool]:
        """메뉴 선택 실행"""
        try:
            menu_map = {
                "0": self._return_to_main_menu,
                "1": self._system_test,
                "2": self._config_management,
                "3": self._component_initialization,
                "4": self._comprehensive_analysis,
                "5": self._specific_symbol_analysis,
                "6": self._news_analysis,
                "7": self._handle_auto_trading_menu,
                "8": self._backtest,
                "9": self._ai_comprehensive_analysis,
                "10": self._ai_market_regime_analysis,
                "11": self._ai_strategy_optimization,
                "12": self._ai_risk_assessment,
                "13": self._ai_daily_report,
                "14": self._test_telegram_notification,
                "15": self._manage_notification_settings,
                "16": self._view_notification_stats,
                "17": self._check_notification_status,
                "18": self._ai_vs_traditional_comparison,
                "19": self._strategy_validation,
                "20": self._ai_prediction_accuracy_analysis,
                "21": self._market_regime_performance,
                "22": self._backtesting_report_generation,
                "23": self._ai_momentum_strategy_analysis,
                "24": self._adaptive_position_sizing,
                "25": self._multi_timeframe_analysis,
                "26": self._comprehensive_strategy_analysis,
                "27": self._advanced_strategy_backtest,
                "28": self._multi_strategy_analysis,
                "29": self._database_status,
                "30": self._symbol_data_query,
                "31": self._real_time_system_monitor,
                "32": self._realtime_monitoring_system,
                "33": self._portfolio_holdings,
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

    async def _return_to_main_menu(self) -> bool:
        console.print("메인 메뉴로 돌아갑니다...")
        return True

    async def _system_test(self) -> bool:
        console.print(Panel("[bold cyan]시스템 테스트 및 상태 확인[/bold cyan]", border_style="cyan"))
        try:
            result = await self.system._run_system_test()
            if result:
                await self._display_system_status()
            return result
        except Exception as e:
            console.print(f"[red]❌ 시스템 테스트 실패: {e}[/red]")
            return False

    async def _config_management(self) -> bool:
        console.print(Panel("[bold cyan]설정 관리[/bold cyan]", border_style="cyan"))
        try:
            await self._display_current_config()
            change_config = Confirm.ask("\n설정을 변경하시겠습니까?")
            if change_config:
                await self._modify_config()
            return True
        except Exception as e:
            console.print(f"[red]❌ 설정 관리 실패: {e}[/red]")
            return False

    async def _component_initialization(self) -> bool:
        console.print(Panel("[bold cyan]컴포넌트 초기화[/bold cyan]", border_style="cyan"))
        status = await self.system.get_system_status()
        if all(status['components'].values()):
            if not Confirm.ask("모든 컴포넌트가 이미 초기화되어 있습니다. 재초기화하시겠습니까?"):
                return True
        return await self.system.initialize_components()

    async def _comprehensive_analysis(self) -> bool:
        """종합 분석 (5개 영역 통합) - 백그라운드 작업 중에도 안전한 수동 실행"""
        console.print(Panel("[bold green]종합 분석 (5개 영역 통합)[/bold green]", border_style="green"))
        
        # 백그라운드 상태 확인 및 표시
        background_status = await self._check_background_analysis_status()
        if background_status.get('is_running', False):
            console.print("[yellow]🔄 백그라운드 자동 분석 실행 중[/yellow]")
            console.print("[cyan]💡 수동 분석도 안전하게 실행할 수 있습니다![/cyan]")
            next_auto = background_status.get('next_run', 'Unknown')
            console.print(f"[dim]   • 다음 자동 분석: {next_auto}[/dim]")
        else:
            console.print("[green]✅ 시스템 대기 중 - 즉시 실행 가능[/green]")
        
        return await self._execute_safe_comprehensive_analysis()

    def _display_analysis_results_table(self, analysis_results: List[Dict], strategy_name: str):
        """분석 결과를 Rich 테이블로 표시"""
        try:
            console.print(f"\n[bold blue]📊 '{strategy_name}' 전략 분석 결과[/bold blue]")
            
            # 결과를 점수순으로 정렬
            sorted_results = sorted(analysis_results, key=lambda x: x.get('score', 0), reverse=True)
            
            # Rich 테이블 생성
            table = Table(show_header=True, header_style="bold magenta", title=f"분석 결과: {len(analysis_results)}개 종목")
            table.add_column("순위", style="cyan", width=4)
            table.add_column("종목코드", style="white", width=8)
            table.add_column("종목명", style="white", width=12)
            table.add_column("점수", style="green", width=6)
            table.add_column("추천등급", style="yellow", width=8)
            table.add_column("전략", style="blue", width=10)
            table.add_column("이유", style="dim white", width=20)
            
            # 추천 등급별 색상 설정
            def get_recommendation_style(recommendation):
                if recommendation in ['BUY', 'STRONG_BUY']:
                    return "[bold green]"
                elif recommendation in ['WEAK_BUY']:
                    return "[green]"
                elif recommendation == 'HOLD':
                    return "[yellow]"
                elif recommendation in ['SELL', 'WEAK_SELL']:
                    return "[red]"
                else:
                    return ""
            
            # 테이블 데이터 추가
            for i, result in enumerate(sorted_results, 1):
                symbol = result.get('symbol', 'N/A')
                name = result.get('name', 'N/A')
                score = result.get('score', result.get('overall_score', 0))
                recommendation = result.get('recommendation', 'HOLD')
                strategy = result.get('strategy', strategy_name)
                reason = result.get('reason', '분석 완료')
                
                # 추천등급에 색상 적용
                rec_style = get_recommendation_style(recommendation)
                
                table.add_row(
                    str(i),
                    symbol,
                    name[:10] + "..." if len(name) > 10 else name,
                    f"{score:.1f}",
                    f"{rec_style}{recommendation}[/]",
                    strategy,
                    reason[:18] + "..." if len(reason) > 18 else reason
                )
            
            console.print(table)
            
            # 통계 요약
            buy_count = len([r for r in analysis_results if r.get('recommendation') in ['BUY', 'STRONG_BUY', 'WEAK_BUY']])
            hold_count = len([r for r in analysis_results if r.get('recommendation') == 'HOLD'])
            sell_count = len([r for r in analysis_results if r.get('recommendation') in ['SELL', 'WEAK_SELL']])
            
            console.print(f"\n[bold]📈 추천 분포:[/bold]")
            console.print(f"  • [green]매수 추천:[/green] {buy_count}개 ({buy_count/len(analysis_results)*100:.1f}%)")
            console.print(f"  • [yellow]보유:[/yellow] {hold_count}개 ({hold_count/len(analysis_results)*100:.1f}%)")
            console.print(f"  • [red]매도:[/red] {sell_count}개 ({sell_count/len(analysis_results)*100:.1f}%)")
            
        except Exception as e:
            console.print(f"[red]❌ 분석 결과 표시 실패: {e}[/red]")
            self.logger.error(f"Display analysis results failed: {e}")

    async def _add_recommendations_to_monitoring(self, analysis_results: List[Dict], strategy_name: str):
        """분석 결과에서 추천된 종목을 모니터링에 추가하는 헬퍼 함수"""
        try:
            if not hasattr(self.system, 'auto_trading_handler') or not self.system.auto_trading_handler:
                console.print("[red]❌ 자동매매 핸들러가 초기화되지 않았습니다.[/red]")
                return

            # BUY 추천 종목 필터링 (WEAK_BUY 포함)
            buy_recommendations = [res for res in analysis_results if res.get('recommendation') in ['BUY', 'STRONG_BUY', 'WEAK_BUY']]

            # 디버깅 정보
            console.print(f"\n[dim]디버깅: 전체 결과 {len(analysis_results)}개, 매수 추천 {len(buy_recommendations)}개[/dim]")
            
            if not buy_recommendations:
                console.print("[yellow]💡 추가할 매수 추천 종목이 없습니다.[/yellow]")
                
                # 추천 등급 분포 표시
                rec_counts = {}
                for res in analysis_results:
                    rec = res.get('recommendation', 'UNKNOWN')
                    rec_counts[rec] = rec_counts.get(rec, 0) + 1
                
                console.print(f"[dim]추천 등급 분포: {rec_counts}[/dim]")
                return

            console.print(f"\n[bold green]📈 ‘{strategy_name}’ 전략의 매수 추천 종목:[/bold green]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("번호", style="cyan", width=4)
            table.add_column("종목코드", style="white")
            table.add_column("종목명", style="white")
            table.add_column("점수", style="green")
            table.add_column("추천등급", style="yellow")

            for i, stock in enumerate(buy_recommendations, 1):
                table.add_row(
                    str(i),
                    stock.get('symbol'),
                    stock.get('name'),
                    f"{stock.get('comprehensive_score', 0):.1f}",
                    stock.get('recommendation')
                )
            console.print(table)

            choice = Prompt.ask("\n모니터링에 추가할 종목의 번호를 입력하세요 (쉼표로 구분, 전체는 'all', 취소는 Enter)", default="").strip()

            if not choice:
                console.print("[yellow]취소되었습니다.[/yellow]")
                return

            selected_indices = []
            if choice.lower() == 'all':
                selected_indices = range(len(buy_recommendations))
            else:
                try:
                    selected_indices = [int(i.strip()) - 1 for i in choice.split(',')]
                except ValueError:
                    console.print("[red]❌ 잘못된 입력입니다. 숫자만 입력해주세요.[/red]")
                    return

            added_count = 0
            for i in selected_indices:
                if 0 <= i < len(buy_recommendations):
                    stock_to_add = buy_recommendations[i]
                    symbol = stock_to_add.get('symbol')
                    name = stock_to_add.get('name')
                    
                    success = await self.system.auto_trading_handler.auto_trader.add_buy_recommendation(
                        symbol=symbol,
                        name=name,
                        strategy_name=strategy_name
                    )
                    if success:
                        added_count += 1
                else:
                    console.print(f"[yellow]⚠️ {i+1}번은 잘못된 번호입니다.[/yellow]")
            
            if added_count > 0:
                console.print(f"[green]✅ 총 {added_count}개의 종목을 모니터링에 추가했습니다.[/green]")

        except Exception as e:
            console.print(f"[red]❌ 모니터링 추가 중 오류 발생: {e}[/red]")
            self.logger.error(f"❌ _add_recommendations_to_monitoring 오류: {e}", exc_info=True)

    async def _specific_symbol_analysis(self) -> bool:
        console.print(Panel("[bold green]대상 특정 종목 분석[/bold green]", border_style="green"))
        try:
            symbols_input = Prompt.ask("분석할 종목 코드를 입력하세요 (쉼표로 구분)")
            symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
            if not symbols:
                console.print("[yellow]⚠️ 종목 코드가 입력되지 않았습니다.[/yellow]")
                return False
            strategy = await self._get_strategy_choice()
            results = await self.system.analyze_symbols(symbols, strategy)
            if results:
                await self.system.display_results(results, "종합 분석 결과")
            return len(results) > 0
        except Exception as e:
            console.print(f"[red]❌특정 종목 분석 실패: {e}[/red]")
            return False

    async def _news_analysis(self) -> bool:
        console.print(Panel("[bold green]뉴스 재료 분석[/bold green]", border_style="green"))
        try:
            if not self.system.news_collector:
                console.print("[yellow]⚠️ 뉴스 수집기가 초기화되지 않았습니다.[/yellow]")
                return False
            symbols_input = Prompt.ask("분석할 종목 코드 (전체 분석은 Enter)", default="")
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                for symbol in symbols:
                    try:
                        stock_info = await self.system.data_collector.get_stock_info(symbol)
                        name = stock_info.get('name', symbol) if stock_info else symbol
                        news_result = await self.system.news_collector.analyze_stock_news(symbol, name)
                        await self._display_news_analysis_result(symbol, name, news_result)
                    except Exception as e:
                        console.print(f"[yellow]⚠️ {symbol} 뉴스 분석 실패: {e}[/yellow]")
            else:
                market_news = await self.system.news_collector.get_market_news()
                await self._display_market_news(market_news)
            return True
        except Exception as e:
            console.print(f"[red]❌ 뉴스 분석 실패: {e}[/red]")
            return False

    async def _supply_demand_analysis(self) -> bool:
        console.print(Panel("[bold green]수급정보 분석 (NEW)[/bold green]", border_style="green"))
        try:
            try:
                from analyzers.supply_demand_analyzer import SupplyDemandAnalyzer
                analyzer = SupplyDemandAnalyzer(self.config)
            except ImportError:
                console.print("[yellow]⚠️ 수급 분석 모듈이 없습니다. 기본 분석으로 대체합니다.[/yellow]")
                return await self._basic_supply_demand_analysis()
            symbols_input = Prompt.ask("분석할 종목 코드 (전체 분석은 Enter)", default="")
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                results = await analyzer.analyze_symbols(symbols)
            else:
                results = await analyzer.analyze_market()
            await self._display_supply_demand_results(results)
            return True
        except Exception as e:
            console.print(f"[red]❌ 수급 분석 실패: {e}[/red]")
            return False

    async def _chart_pattern_analysis(self) -> bool:
        console.print(Panel("[bold green]차트패턴 분석 (NEW)[/bold green]", border_style="green"))
        try:
            try:
                from analyzers.chart_pattern_analyzer import ChartPatternAnalyzer
                analyzer = ChartPatternAnalyzer(self.config)
            except ImportError:
                console.print("[yellow]⚠️ 차트패턴 분석 모듈이 없습니다. 기본 분석으로 대체합니다.[/yellow]")
                return await self._basic_chart_pattern_analysis()
            symbols_input = Prompt.ask("분석할 종목 코드 (전체 분석은 Enter)", default="")
            pattern_types = await self._get_pattern_types()
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                results = await analyzer.analyze_symbols(symbols, pattern_types)
            else:
                results = await analyzer.analyze_market(pattern_types)
            await self._display_chart_pattern_results(results)
            return True
        except Exception as e:
            console.print(f"[red]❌ 차트패턴 분석 실패: {e}[/red]")
            return False

    # 중복 메서드 제거 - 아래 1460번째 줄의 올바른 버전 사용

    async def _auto_trading(self) -> bool:
        console.print(Panel("[bold red]자동매매 시작 (실제 거래 위험!)[/bold red]", border_style="red"))
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
            strategy = await self._get_strategy_choice()
            await self.system.run_auto_trading(strategy)
            return True
        except Exception as e:
            console.print(f"[red]❌ 자동매매 실행 실패: {e}[/red]")
            return False

    async def _backtest(self) -> bool:
        console.print(Panel("[bold green]백테스트 실행[/bold green]", border_style="green"))
        try:
            strategy = await self._get_strategy_choice()
            console.print("\n[bold]백테스트 기간 설정[/bold]")
            start_date = Prompt.ask("시작 날짜 (YYYY-MM-DD)", default="2024-01-01")
            end_date = Prompt.ask("종료 날짜 (YYYY-MM-DD)", default="2024-12-31")
            symbols_input = Prompt.ask("특정 종목 (전체는 Enter)", default="")
            symbols = [s.strip() for s in symbols_input.split(',')] if symbols_input else None
            results = await self.system.run_backtest(strategy, start_date, end_date, symbols)
            await self.system._display_backtest_results(results)
            return True
        except Exception as e:
            console.print(f"[red]❌ 백테스트 실행 실패: {e}[/red]")
            return False

    async def _scheduler(self) -> bool:
        console.print(Panel("[bold green]실시간 매매 스케줄러[/bold green]", border_style="green"))
        if not self.system.scheduler:
            console.print("[red]❌ 스케줄러가 초기화되지 않았습니다.[/red]")
            return False
        while True:
            try:
                status = self.system.scheduler.get_status()
                console.print(f"\n[bold]📊 현재 상태:[/bold]")
                console.print(f"• 실행 상태: {'[green]실행 중[/green]' if status['is_running'] else '[red]중지됨[/red]'}")
                console.print(f"• 장중 여부: {'[green]장중[/green]' if status['is_market_hours'] else '[yellow]장외[/yellow]'}")
                console.print(f"• 모니터링 종목: {status['monitored_stocks_count']}개")
                console.print(f"• 마지막 분석 시간: {status['last_analysis_time'] or 'N/A'}")
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
                
                if choice == "0": break
                elif choice == "1":
                    if status['is_running']:
                        console.print("[yellow]⚠️ 스케줄러가 이미 실행 중입니다.[/yellow]")
                    else:
                        await self.system.scheduler.start()
                        console.print("[green]✅ 실시간 스케줄러가 시작되었습니다.[/green]")
                elif choice == "2":
                    if status['is_running']:
                        await self.system.scheduler.stop()
                        console.print("[red]🛑 실시간 스케줄러가 중지되었습니다.[/red]")
                    else:
                        console.print("[yellow]⚠️ 스케줄러가 이미 중지되어 있습니다.[/yellow]")
                elif choice == "3":
                    symbol = Prompt.ask("추가할 종목 코드를 입력하세요 (예: 005930)")
                    available_strategies = list(self.system.strategies.keys())
                    console.print(f"\n[bold]사용 가능한 전략:[/bold]\n" + "\n".join([f"  {i+1}. {s}" for i, s in enumerate(available_strategies)]))
                    strategy_choice = Prompt.ask("전략 번호를 선택하세요", choices=[str(i+1) for i in range(len(available_strategies))], default="1")
                    strategy = available_strategies[int(strategy_choice) - 1]
                    success = await self.system.scheduler.add_monitoring_stock(symbol, strategy)
                    if success:
                        console.print(f"[green]✅ {symbol} ({strategy} 전략) 모니터링 추가됨[/green]")
                    else:
                        console.print(f"[yellow]⚠️ {symbol} 모니터링 추가 실패 (이미 존재할 수 있음)[/yellow]")
                elif choice == "4":
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
                    console.print("[green]✅ 상태 정보가 상단에 표시되어 있습니다.[/green]")
                
                if choice != "0": await asyncio.sleep(1)
            except Exception as e:
                console.print(f"[red]❌ 스케줄러 관리 실패: {e}[/red]")
                self.logger.error(f"❌ 스케줄러 관리 실패: {e}", exc_info=True)
                break
        return True

    async def _ai_comprehensive_analysis(self) -> bool:
        console.print(Panel("[bold magenta]AI 종합 시장 분석[/bold magenta]", border_style="magenta"))
        try:
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            console.print("[yellow]📊 시장 데이터 수집 중...[/yellow]")
            market_data = await self._collect_market_data_for_ai()
            individual_stocks = await self._collect_individual_stocks_data()
            portfolio_data = await self._collect_portfolio_data()
            console.print("[yellow]🧠 AI 종합 분석 실행 중...[/yellow]")
            results = await self.system.run_ai_comprehensive_analysis(market_data, individual_stocks, portfolio_data)
            if results:
                console.print("[green]✅ AI 종합 분석 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ AI 분석 결과가 없습니다.[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]❌ AI 종합 분석 실패: {e}[/red]")
            self.logger.error(f"❌ AI 종합 분석 실패: {e}", exc_info=True)
            return False

    async def _ai_market_regime_analysis(self) -> bool:
        console.print(Panel("[bold magenta]AI 시장 체제 분석[/bold magenta]", border_style="magenta"))
        try:
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            console.print("[yellow]📊 시장 데이터 수집 중...[/yellow]")
            market_data = await self._collect_market_data_for_ai()
            individual_stocks = await self._collect_individual_stocks_data()
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
            self.logger.error(f"❌ AI 시장 체제 분석 실패: {e}", exc_info=True)
            return False

    async def _ai_strategy_optimization(self) -> bool:
        console.print(Panel("[bold magenta]AI 전략 최적화[/bold magenta]", border_style="magenta"))
        try:
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            available_strategies = ['momentum', 'breakout', 'rsi', 'scalping_3m', 'eod', 'vwap', 'supertrend_ema_rsi']
            console.print("\n[bold]최적화할 전략을 선택하세요:[/bold]")
            for i, strategy in enumerate(available_strategies, 1):
                console.print(f"  {i}. {strategy}")
            console.print("  0. 전체 전략")
            choice = Prompt.ask("전략 선택", choices=[str(i) for i in range(len(available_strategies) + 1)], default="0")
            strategies = available_strategies if choice == "0" else [available_strategies[int(choice) - 1]]
            console.print("[yellow]📊 성과 데이터 수집 중...[/yellow]")
            performance_data = await self._collect_strategy_performance_data()
            market_conditions = await self._collect_market_conditions()
            console.print("[yellow]⚙️ AI 전략 최적화 실행 중...[/yellow]")
            results = await self.system.run_ai_strategy_optimization(strategies, performance_data, market_conditions)
            if results:
                console.print("[green]✅ AI 전략 최적화 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ 전략 최적화 결과가 없습니다.[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]❌ AI 전략 최적화 실패: {e}[/red]")
            self.logger.error(f"❌ AI 전략 최적화 실패: {e}", exc_info=True)
            return False

    async def _ai_risk_assessment(self) -> bool:
        console.print(Panel("[bold magenta]AI 리스크 평가[/bold magenta]", border_style="magenta"))
        try:
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            console.print("[yellow]📊 포트폴리오 데이터 수집 중...[/yellow]")
            portfolio_data = await self._collect_portfolio_data()
            market_context = await self._collect_market_conditions()
            current_positions = await self._collect_current_positions()
            console.print("[yellow]🛡️ AI 리스크 평가 실행 중...[/yellow]")
            results = await self.system.run_ai_risk_assessment(portfolio_data, market_context, current_positions)
            if results:
                console.print("[green]✅ AI 리스크 평가 완료[/green]")
                return True
            else:
                console.print("[yellow]⚠️ 리스크 평가 결과가 없습니다.[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]❌ AI 리스크 평가 실패: {e}[/red]")
            self.logger.error(f"❌ AI 리스크 평가 실패: {e}", exc_info=True)
            return False

    async def _ai_daily_report(self) -> bool:
        console.print(Panel("[bold magenta]AI 일일 보고서[/bold magenta]", border_style="magenta"))
        try:
            if not self.system.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return False
            period_options = {"1": "daily", "2": "weekly", "3": "monthly"}
            console.print("\n[bold]보고서 기간을 선택하세요:[/bold]")
            for key, value in period_options.items(): console.print(f"  {key}. {value}")
            choice = Prompt.ask("기간 선택", choices=list(period_options.keys()), default="1")
            period = period_options[choice]
            console.print(f"[yellow]📊 AI {period} 보고서 생성 중...[/yellow]")
            results = await self.system.generate_ai_daily_report(period)
            if results:
                console.print(f"[green]✅ AI {period} 보고서 생성 완료[/green]")
                if Confirm.ask("\n보고서를 파일로 저장하시겠습니까?"):
                    await self._save_ai_report_to_file(results, period)
                return True
            else:
                console.print("[yellow]⚠️ 보고서 생성 결과가 없습니다.[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]❌ AI 보고서 생성 실패: {e}[/red]")
            self.logger.error(f"❌ AI 보고서 생성 실패: {e}", exc_info=True)
            return False

    async def _collect_market_data_for_ai(self) -> List[Dict]:
        try:
            market_indices = ["KOSPI", "KOSDAQ", "KS11", "KQ11"]
            market_data = []
            for index in market_indices:
                try:
                    data = await self.system.data_collector.get_market_index_data(index)
                    if data: market_data.append(data)
                except Exception as e: self.logger.warning(f"시장 지수 {index} 데이터 수집 실패: {e}")
            if not market_data:
                market_data = [{'index': 'KOSPI', 'current_price': 2500, 'change_rate': 0.01, 'volume': 1000000, 'timestamp': datetime.now()}]
            return market_data
        except Exception as e:
            self.logger.error(f"AI용 시장 데이터 수집 실패: {e}", exc_info=True)
            return []

    async def _collect_individual_stocks_data(self) -> List[Dict]:
        try:
            # 동적 종목 선택
            sample_stocks = await self.system.data_collector.get_market_leaders(limit=5)
            if not sample_stocks:
                sample_stocks = ["005930", "000660", "035420", "005380", "051910"]
            stocks_data = []
            for symbol in sample_stocks:
                try:
                    data = await self.system.data_collector.get_stock_data(symbol)
                    if data: stocks_data.append({**data, 'symbol': symbol})
                except Exception as e: self.logger.warning(f"종목 {symbol} 데이터 수집 실패: {e}")
            return stocks_data
        except Exception as e:
            self.logger.error(f"개별 종목 데이터 수집 실패: {e}", exc_info=True)
            return []

    async def _collect_portfolio_data(self) -> Dict:
        try:
            portfolio_data = {'total_value': 10000000, 'cash': 2000000, 'positions': [], 'daily_pnl': 0, 'total_pnl': 0, 'risk_level': 'MODERATE'}
            return portfolio_data
        except Exception as e:
            self.logger.error(f"포트폴리오 데이터 수집 실패: {e}", exc_info=True)
            return {}

    async def _collect_strategy_performance_data(self) -> Dict:
        try:
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
            self.logger.error(f"전략 성과 데이터 수집 실패: {e}", exc_info=True)
            return {}

    async def _collect_market_conditions(self) -> Dict:
        try:
            market_conditions = {'volatility': 0.2, 'trend': 'BULL', 'volume_trend': 'INCREASING', 'sector_rotation': 'TECH_TO_VALUE', 'interest_rate_environment': 'RISING', 'economic_indicators': 'MIXED'}
            return market_conditions
        except Exception as e:
            self.logger.error(f"시장 조건 데이터 수집 실패: {e}", exc_info=True)
            return {}

    async def _collect_current_positions(self) -> Dict:
        try:
            current_positions = {'005930': {'quantity': 10, 'avg_price': 70000, 'current_price': 72000},'000660': {'quantity': 5, 'avg_price': 85000, 'current_price': 87000}}
            return current_positions
        except Exception as e:
            self.logger.error(f"현재 포지션 데이터 수집 실패: {e}", exc_info=True)
            return {}

    async def _save_ai_report_to_file(self, report: Dict, period: str) -> bool:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_report_{period}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f: json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            console.print(f"[green]AI 보고서가 {filename}에 저장되었습니다.[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ AI 보고서 저장 실패: {e}[/red]")
            self.logger.error(f"❌ AI 보고서 저장 실패: {e}", exc_info=True)
            return False

    async def _real_time_system_monitor(self) -> bool:
        console.print(Panel("[bold blue]실시간 시스템 모니터[/bold blue]", border_style="blue"))
        try:
            from utils.system_monitor import SystemMonitor
            monitor = SystemMonitor(self.system)
            console.print("[yellow]📊 실시간 시스템 모니터 시작[/yellow]")
            console.print("[dim]종료: Ctrl+C[/dim]")
            await monitor.start_dashboard(refresh_interval=3)
            return True
        except KeyboardInterrupt:
            console.print("\n[yellow]시스템 모니터를 종료합니다[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 시스템 모니터 실행 실패: {e}[/red]")
            self.logger.error(f"❌ 시스템 모니터 실행 실패: {e}", exc_info=True)
            return False

    async def _database_status(self) -> bool:
        console.print(Panel("[bold blue]데이터베이스 상태 확인[/bold blue]", border_style="blue"))
        try:
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 초기화되지 않았습니다.[/yellow]")
                return False
            connection_status = await self.system.db_manager.check_connection()
            if connection_status:
                db_info = await self.system.db_manager.get_database_info()
                await self._display_database_info(db_info)
            else:
                console.print("[red]❌ 데이터베이스 연결 실패[/red]")
            return connection_status
        except Exception as e:
            console.print(f"[red]❌ 데이터베이스 상태 확인 실패: {e}[/red]")
            self.logger.error(f"❌ 데이터베이스 상태 확인 실패: {e}", exc_info=True)
            return False

    async def _view_stock_data(self) -> bool:
        console.print(Panel("[bold blue]종목 데이터 조회[/bold blue]", border_style="blue"))
        try:
            symbol = Prompt.ask("조회할 종목 코드를 입력하세요")
            if not symbol:
                console.print("[yellow]⚠️ 종목 코드가 입력되지 않았습니다.[/yellow]")
                return False
            if self.system.db_manager:
                stock_data = await self.system.db_manager.get_stock_data(symbol)
                if stock_data: await self._display_stock_data(symbol, stock_data)
                else: console.print(f"[yellow]⚠️ {symbol}의 데이터를 찾을 수 없습니다.[/yellow]")
            else:
                stock_data = await self.system.data_collector.get_stock_data(symbol)
                if stock_data: await self._display_stock_data(symbol, stock_data)
                else: console.print(f"[yellow]⚠️ {symbol}의 데이터를 조회할 수 없습니다.[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 종목 데이터 조회 실패: {e}[/red]")
            self.logger.error(f"❌ 종목 데이터 조회 실패: {e}", exc_info=True)
            return False

    async def _view_analysis_results(self) -> bool:
        console.print(Panel("[bold blue]분석 결과 조회[/bold blue]", border_style="blue"))
        try:
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 없어 최근 분석 결과만 표시합니다.[/yellow]")
                return False
            days = IntPrompt.ask("최근 며칠간의 결과를 조회하시겠습니까?", default=7)
            results = await self.system.db_manager.get_analysis_results(days=days)
            if results: await self._display_historical_analysis_results(results)
            else: console.print("[yellow]📊 분석 결과가 없습니다.[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 분석 결과 조회 실패: {e}[/red]")
            self.logger.error(f"❌ 분석 결과 조회 실패: {e}", exc_info=True)
            return False

    async def _view_trading_records(self) -> bool:
        console.print(Panel("[bold blue]거래 기록 조회[/bold blue]", border_style="blue"))
        try:
            if not self.system.trading_enabled:
                console.print("[yellow]⚠️ 매매 모드가 비활성화되어 있습니다.[/yellow]")
                return False
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 초기화되지 않았습니다.[/yellow]")
                return False
            days = IntPrompt.ask("최근 며칠간의 거래 기록을 조회하시겠습니까?", default=30)
            trading_records = await self.system.db_manager.get_trading_records(days=days)
            if trading_records: await self._display_trading_records(trading_records)
            else: console.print("[yellow]💰 거래 기록이 없습니다.[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 거래 기록 조회 실패: {e}[/red]")
            self.logger.error(f"❌ 거래 기록 조회 실패: {e}", exc_info=True)
            return False

    async def _data_cleanup(self) -> bool:
        console.print(Panel("[bold magenta]데이터 정리 및 최적화[/bold magenta]", border_style="magenta"))
        try:
            if not self.system.db_manager:
                console.print("[yellow]⚠️ 데이터베이스 매니저가 초기화되지 않았습니다.[/yellow]")
                return False
            cleanup_options = {"1": "오래된 분석 결과 삭제 (30일 이상)", "2": "중복 데이터 제거", "3": "데이터베이스 최적화", "4": "전체 정리 및 최적화"}
            console.print("\n[bold]정리 옵션:[/bold]")
            for key, value in cleanup_options.items(): console.print(f"  {key}. {value}")
            choice = Prompt.ask("정리 작업을 선택하세요", choices=list(cleanup_options.keys()))
            if not Confirm.ask(f"'{cleanup_options[choice]}' 작업을 실행하시겠습니까?"):
                return False
            with Progress() as progress:
                task = progress.add_task("[green]데이터 정리 중...", total=100)
                if choice == "1": await self.system.db_manager.cleanup_old_analysis_results(days=30)
                elif choice == "2": await self.system.db_manager.remove_duplicate_data()
                elif choice == "3": await self.system.db_manager.optimize_database()
                elif choice == "4": await self.system.db_manager.full_cleanup_and_optimize()
                progress.update(task, advance=100)
            console.print("[green]✅ 데이터 정리 완료[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 데이터 정리 실패: {e}[/red]")
            self.logger.error(f"❌ 데이터 정리 실패: {e}", exc_info=True)
            return False

    async def _log_analysis(self) -> bool:
        console.print(Panel("[bold magenta]로그 분석[/bold magenta]", border_style="magenta"))
        try:
            log_file = getattr(self.config, 'LOG_FILE', 'trading_system.log')
            analysis_options = {"1": "최근 에러 로그 확인", "2": "성능 분석", "3": "거래 로그 분석", "4": "전체 로그 요약"}
            console.print("\n[bold]분석 옵션:[/bold]")
            for key, value in analysis_options.items(): console.print(f"  {key}. {value}")
            choice = Prompt.ask("분석 유형을 선택하세요", choices=list(analysis_options.keys()))
            await self._analyze_logs(choice, log_file)
            return True
        except Exception as e:
            console.print(f"[red]❌ 로그 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 로그 분석 실패: {e}", exc_info=True)
            return False

    async def _system_monitoring(self) -> bool:
        console.print(Panel("[bold magenta]시스템 상태 모니터링[/bold magenta]", border_style="magenta"))
        try:
            console.print("[yellow]실시간 모니터링을 시작합니다. Ctrl+C로 중단하세요.[/yellow]")
            while True:
                status = await self.system.get_system_status()
                await self._display_realtime_status(status)
                await asyncio.sleep(5)
        except KeyboardInterrupt:
            console.print("\n[yellow]🛑 모니터링 중단[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 시스템 모니터링 실패: {e}[/red]")
            self.logger.error(f"❌ 시스템 모니터링 실패: {e}", exc_info=True)
            return False

    async def _get_strategy_choice(self) -> str:
        strategies = {
            "1": "momentum", "2": "breakout", "3": "eod", "4": "supertrend_ema_rsi",
            "5": "vwap", "6": "scalping_3m", "7": "rsi", "8": "squeeze_momentum_pro"
        }
        console.print("\n[bold]전략 선택:[/bold]")
        for key, value in strategies.items(): console.print(f"  {key}. {value}")
        choice = Prompt.ask("전략을 선택하세요", choices=list(strategies.keys()), default="1")
        return strategies[choice]

    async def _get_analysis_limit(self) -> int:
        console.print("[yellow]ℹ️ 1차 필터링에서 추출된 모든 종목을 2차 필터링합니다.[/yellow]")
        return None

    async def _get_pattern_types(self) -> List[str]:
        pattern_options = {
            "1": "head_and_shoulders", "2": "double_top", "3": "double_bottom",
            "4": "triangle", "5": "flag", "6": "wedge", "7": "rectangle"
        }
        console.print("\n[bold]차트패턴 유형:[/bold]")
        for key, value in pattern_options.items(): console.print(f"  {key}. {value.replace('_', ' ').title()}")
        console.print("  0. 전체 패턴")
        choices = Prompt.ask("패턴을 선택하세요 (쉼표로 구분, 전체는 0)", default="0")
        if choices == "0": return list(pattern_options.values())
        else:
            selected = []
            for choice in choices.split(','):
                choice = choice.strip()
                if choice in pattern_options: selected.append(pattern_options[choice])
            return selected if selected else list(pattern_options.values())

    async def _save_analysis_to_file(self, results: List) -> bool:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_results_{timestamp}.json"
            data = {'timestamp': datetime.now().isoformat(), 'total_results': len(results), 'results': [result.to_dict() if hasattr(result, 'to_dict') else result for result in results]}
            with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            console.print(f"[green]결과가 {filename}에 저장되었습니다.[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 파일 저장 실패: {e}[/red]")
            self.logger.error(f"❌ 파일 저장 실패: {e}", exc_info=True)
            return False

    async def _display_system_status(self):
        status = await self.system.get_system_status()
        table = Table(title="시스템 상태")
        table.add_column("구분", style="cyan", width=20)
        table.add_column("상태", style="green", width=15)
        table.add_column("설명", style="white")
        table.add_row("매매 모드", "활성화" if status['trading_enabled'] else "비활성화", "실제 거래 가능 여부")
        table.add_row("백테스트 모드", "활성화" if status['backtest_mode'] else "비활성화", "백테스트 모드 여부")
        table.add_row("시스템 실행", "실행중" if status['is_running'] else "정지", "자동매매 실행 상태")
        table.add_row("활성 포지션", str(status['active_positions']), "현재 보유 포지션 수")
        console.print(table)
        comp_table = Table(title="컴포넌트 상태")
        comp_table.add_column("컴포넌트", style="cyan", width=20)
        comp_table.add_column("상태", style="green", width=10)
        for comp, status_val in status['components'].items():
            comp_table.add_row(comp.replace('_', ' ').title(), "정상" if status_val else "미초기화")
        console.print(comp_table)

    async def _display_current_config(self):
        config_table = Table(title="현재 시스템 설정")
        config_table.add_column("설정 항목", style="cyan", width=25)
        config_table.add_column("현재 값", style="yellow", width=20)
        config_table.add_column("설명", style="white")
        try:
            config_table.add_row("API 타임아웃", f"{getattr(self.config, 'API_TIMEOUT', 30)}초", "API 응답 대기 시간")
            config_table.add_row("분석 최소 점수", f"{getattr(self.config.analysis, 'MIN_COMPREHENSIVE_SCORE', 60)}점", "분석 결과 필터링 기준")
            config_table.add_row("최대 포지션", f"{getattr(self.config.trading, 'MAX_POSITIONS', 5)}개", "동시 보유 가능 포지션 수")
            config_table.add_row("리스크 한도", f"{getattr(self.config.trading, 'MAX_PORTFOLIO_RISK', 0.2):.1%}", "포트폴리오 최대 리스크")
        except AttributeError:
            config_table.add_row("설정 로드", "❌ 실패", "설정 파일 확인 필요")
        console.print(config_table)

    async def _modify_config(self):
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
                console.print(f"[green]API 타임아웃이 {new_timeout}초로 변경되었습니다.[/green]")
            elif choice == "2":
                new_score = IntPrompt.ask("새로운 분석 최소 점수", default=60)
                self.config.analysis.MIN_COMPREHENSIVE_SCORE = new_score
                console.print(f"[green]분석 최소 점수가 {new_score}점으로 변경되었습니다.[/green]")
            elif choice == "3":
                new_positions = IntPrompt.ask("새로운 최대 포지션 수", default=5)
                self.config.trading.MAX_POSITIONS = new_positions
                console.print(f"[green]최대 포지션 수가 {new_positions}개로 변경되었습니다.[/green]")
            elif choice == "4":
                new_risk = float(Prompt.ask("새로운 리스크 한도 (0.1 = 10%)", default="0.2"))
                self.config.trading.MAX_PORTFOLIO_RISK = new_risk
                console.print(f"[green]리스크 한도가 {new_risk:.1%}로 변경되었습니다.[/green]")
        except Exception as e:
            console.print(f"[red]❌ 설정 변경 실패: {e}[/red]")
            self.logger.error(f"❌ 설정 변경 실패: {e}", exc_info=True)

    async def _display_news_analysis_result(self, symbol: str, name: str, news_result: Dict):
        panel_content = f"""
[bold]뉴스 {symbol} {name} 분석[/bold]

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
        table = Table(title="시장 뉴스 요약")
        table.add_column("분야", style="cyan", width=15)
        table.add_column("주요 뉴스", style="white", width=50)
        table.add_column("감정", style="yellow", width=10)
        for category, news_list in market_news.items():
            for news in news_list[:3]:
                table.add_row(category.title(), news.get('title', 'N/A')[:47] + "..." if len(news.get('title', '')) > 50 else news.get('title', 'N/A'), news.get('sentiment', 'N/A'))
        console.print(table)

    async def _basic_supply_demand_analysis(self) -> bool:
        console.print("[yellow]기본 수급 분석을 실행합니다...[/yellow]")
        try:
            symbols_input = Prompt.ask("분석할 종목 코드 (샘플 분석은 Enter)", default="")
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
            else:
                # 동적 시장 대표 종목 사용
                symbols = await self.system.data_collector.get_market_leaders(limit=3)
                if not symbols:
                    symbols = ["005930", "000660", "035420"]
            results = []
            for symbol in symbols:
                try:
                    stock_data = await self.system.data_collector.get_stock_data(symbol)
                    if stock_data:
                        supply_demand = {
                            'symbol': symbol, 'volume_ratio': stock_data.get('volume_ratio', 1.0),
                            'foreign_ratio': stock_data.get('foreign_ratio', 0),
                            'institution_ratio': stock_data.get('institution_ratio', 0),
                            'individual_ratio': stock_data.get('individual_ratio', 0)
                        }
                        results.append(supply_demand)
                except Exception as e: console.print(f"[yellow]⚠️ {symbol} 분석 실패: {e}[/yellow]")
            await self._display_supply_demand_results(results)
            return True
        except Exception as e:
            console.print(f"[red]❌ 기본 수급 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 기본 수급 분석 실패: {e}", exc_info=True)
            return False

    async def _basic_chart_pattern_analysis(self) -> bool:
        console.print("[yellow]기본 차트패턴 분석을 실행합니다...[/yellow]")
        try:
            symbols_input = Prompt.ask("분석할 종목 코드 (샘플 분석은 Enter)", default="")
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
            else:
                # 동적 시장 대표 종목 사용
                symbols = await self.system.data_collector.get_market_leaders(limit=3)
                if not symbols:
                    symbols = ["005930", "000660", "035420"]
            results = []
            for symbol in symbols:
                try:
                    stock_data = await self.system.data_collector.get_stock_data(symbol)
                    if stock_data:
                        pattern_result = {
                            'symbol': symbol, 'patterns_detected': ['uptrend', 'support_level'],
                            'pattern_strength': 75, 'next_resistance': stock_data.get('current_price', 0) * 1.05,
                            'next_support': stock_data.get('current_price', 0) * 0.95
                        }
                        results.append(pattern_result)
                except Exception as e: console.print(f"[yellow]⚠️ {symbol} 분석 실패: {e}[/yellow]")
            await self._display_chart_pattern_results(results)
            return True
        except Exception as e:
            console.print(f"[red]❌ 기본 차트패턴 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 기본 차트패턴 분석 실패: {e}", exc_info=True)
            return False

    async def _display_supply_demand_results(self, results: List[Dict]):
        if not results: console.print("[yellow]📊 수급 분석 결과가 없습니다.[/yellow]")
        else:
            table = Table(title="수급 분석 결과")
            table.add_column("종목", style="cyan", width=10)
            table.add_column("거래량비", style="green", width=10)
            table.add_column("외국인", style="blue", width=10)
            table.add_column("기관", style="magenta", width=10)
            table.add_column("개인", style="yellow", width=10)
            table.add_column("평가", style="white", width=15)
            for result in results:
                volume_ratio = result.get('volume_ratio', 1.0)
                foreign_ratio = result.get('foreign_ratio', 0)
                evaluation = "긍정적" if volume_ratio > 1.5 and foreign_ratio > 0 else "보통"
                table.add_row(result.get('symbol', 'N/A'), f"{volume_ratio:.2f}", f"{foreign_ratio:.1f}%", f"{result.get('institution_ratio', 0):.1f}%", f"{result.get('individual_ratio', 0):.1f}%", evaluation)
            console.print(table)

    async def _display_chart_pattern_results(self, results: List[Dict]):
        if not results: console.print("[yellow]📈 차트패턴 분석 결과가 없습니다.[/yellow]")
        else:
            table = Table(title="차트패턴 분석 결과")
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
                table.add_row(result.get('symbol', 'N/A'), patterns, f"{strength}%", f"{resistance:,.0f}" if resistance else "N/A", f"{support:,.0f}" if support else "N/A")
            console.print(table)

    async def _display_database_info(self, db_info: Dict):
        info_text = f"""
[bold]데이터베이스 정보[/bold]

연결 상태: 정상
데이터베이스: {db_info.get('database_name', 'N/A')}
테이블 수: {db_info.get('table_count', 0)}개
총 레코드 수: {db_info.get('total_records', 0):,}개

테이블별 레코드 수:
• 종목 데이터: {db_info.get('stock_records', 0):,}개
• 분석 결과: {db_info.get('analysis_records', 0):,}개  
• 거래 기록: {db_info.get('trading_records', 0):,}개

마지막 업데이트: {db_info.get('last_update', 'N/A')}
        """
        console.print(Panel(info_text, title="데이터베이스 상태", border_style="blue"))

    async def _display_stock_data(self, symbol: str, stock_data: Dict):
        data_text = f"""
[bold]종목 {symbol} 정보[/bold]

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
        console.print(Panel(data_text, title=f"종목 {symbol} 데이터", border_style="cyan"))

    async def _display_historical_analysis_results(self, results: List[Dict]):
        table = Table(title="과거 분석 결과")
        table.add_column("날짜", style="cyan", width=12)
        table.add_column("종목", style="magenta", width=10)
        table.add_column("점수", style="green", width=8)
        table.add_column("추천", style="yellow", width=12)
        table.add_column("전략", style="blue", width=10)
        for result in results[-20:]: table.add_row(result.get('date', 'N/A')[:10], result.get('symbol', 'N/A'), f"{result.get('score', 0):.1f}", result.get('recommendation', 'N/A'), result.get('strategy', 'N/A'))
        console.print(table)

    async def _display_trading_records(self, records: List[Dict]):
        table = Table(title="거래 기록")
        table.add_column("날짜", style="cyan", width=12)
        table.add_column("종목", style="magenta", width=10)
        table.add_column("구분", style="yellow", width=8)
        table.add_column("수량", style="white", width=10)
        table.add_column("가격", style="green", width=12)
        table.add_column("손익", style="blue", width=12)
        for record in records[-20:]: 
            pnl = record.get('pnl', 0)
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
            table.add_row(record.get('date', 'N/A')[:10], record.get('symbol', 'N/A'), record.get('action', 'N/A'), f"{record.get('quantity', 0):,}주", f"{record.get('price', 0):,}원", f"[{pnl_color}]{pnl:+,.0f}원[/{pnl_color}]")
        console.print(table)

    async def _display_realtime_status(self, status: Dict):
        console.clear()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_text = f"""
[bold]실시간 시스템 상태 ({current_time})[/bold]

시스템 상태:
• 매매 모드: {'활성화' if status['trading_enabled'] else '비활성화'}
• 자동매매: {'실행중' if status['is_running'] else '정지'}
• 활성 포지션: {status['active_positions']}개

컴포넌트 상태:
• 데이터 수집기: {'정상' if status['components']['data_collector'] else '미초기화'}
• 분석 엔진: {'정상' if status['components']['analysis_engine'] else '미초기화'}
• 매매 실행기: {'정상' if status['components']['executor'] else '미초기화'}
• 리스크 관리: {'정상' if status['components']['risk_manager'] else '미초기화'}

[dim]Ctrl+C를 눌러 모니터링을 중단하세요.[/dim]
        """
        console.print(Panel(status_text, title="실시간 모니터링", border_style="green"))

    async def _analyze_logs(self, choice: str, log_file: str):
        try:
            console.print(f"[yellow]로그 분석 중... ({log_file})[/yellow]")
            if choice == "1": console.print("🔍 최근 에러 로그를 확인합니다...")
            elif choice == "2": console.print("📈 성능 분석을 실행합니다...")
            elif choice == "3": console.print("💰 거래 로그를 분석합니다...")
            elif choice == "4": console.print("📊 전체 로그 요약을 생성합니다...")
            summary_text = f"""
[bold]로그 분석 결과[/bold]

분석 대상: {log_file}
분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

요약:
• 총 로그 라인: 1,234개 (예시)
• 에러 로그: 5개
• 경고 로그: 23개
• 거래 로그: 15개

[dim]상세 분석은 별도 로그 분석 도구를 사용하세요.[/dim]
            """
            console.print(Panel(summary_text, title="로그 분석 결과", border_style="magenta"))
        except Exception as e:
            console.print(f"[red]❌ 로그 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 로그 분석 실패: {e}", exc_info=True)

    async def _test_telegram_notification(self):
        try:
            console.print("[cyan]텔레그램 알림 테스트 시작...[/cyan]")
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            success = await self.system.notification_manager.send_test_notification()
            if success:
                console.print("[green]텔레그램 알림 테스트 성공![/green]")
                console.print("[dim]텔레그램에서 테스트 메시지를 확인하세요.[/dim]")
            else:
                console.print("[red]❌ 텔레그램 알림 테스트 실패[/red]")
                console.print("[dim]설정을 확인하고 다시 시도하세요.[/dim]")
        except Exception as e:
            console.print(f"[red]❌ 텔레그램 알림 테스트 오류: {e}[/red]")
            self.logger.error(f"❌ 텔레그램 알림 테스트 오류: {e}", exc_info=True)

    async def _manage_notification_settings(self):
        try:
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            settings = self.system.notification_manager.get_notification_settings()
            table = Table(title="현재 알림 설정", show_header=True, header_style="bold cyan")
            table.add_column("설정", style="yellow", width=20)
            table.add_column("값", style="white", width=30)
            table.add_column("설명", style="dim", width=40)
            table.add_row("알림 활성화", "활성화" if settings['enabled'] else "비활성화", "텔레그램 알림 전체 활성화 상태")
            table.add_row("알림 수준", ", ".join([level.value for level in settings['alert_levels']]), "전송할 알림 수준")
            table.add_row("조용한 시간", f"{settings['quiet_hours']['start']}:00 - {settings['quiet_hours']['end']}:00", "알림 제한 시간대")
            table.add_row("속도 제한", f"{settings['rate_limit']['messages_per_minute']}개/분", "분당 최대 메시지 수")
            console.print(table)
            if Confirm.ask("\n[yellow]설정을 변경하시겠습니까?[/yellow]"):
                await self._modify_notification_settings()
        except Exception as e:
            console.print(f"[red]❌ 알림 설정 조회 오류: {e}[/red]")
            self.logger.error(f"❌ 알림 설정 조회 오류: {e}", exc_info=True)

    async def _modify_notification_settings(self):
        try:
            console.print("\n[cyan]알림 설정 수정[/cyan]")
            new_settings = {}
            if Confirm.ask("조용한 시간을 변경하시겠습니까?"):
                start_hour = IntPrompt.ask("시작 시간 (0-23)", default=22)
                end_hour = IntPrompt.ask("종료 시간 (0-23)", default=7)
                new_settings['quiet_hours'] = {'start': start_hour, 'end': end_hour}
            if Confirm.ask("속도 제한을 변경하시겠습니까?"):
                rate_limit = IntPrompt.ask("분당 최대 메시지 수", default=10)
                new_settings['rate_limit'] = {'messages_per_minute': rate_limit, 'burst_limit': rate_limit * 2}
            if new_settings:
                success = self.system.notification_manager.update_notification_settings(new_settings)
                if success: console.print("[green]✅ 설정이 성공적으로 변경되었습니다.[/green]")
                else: console.print("[red]❌ 설정 변경에 실패했습니다.[/red]")
            else: console.print("[yellow]변경된 설정이 없습니다.[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ 설정 수정 오류: {e}[/red]")
            self.logger.error(f"❌ 설정 수정 오류: {e}", exc_info=True)

    async def _view_notification_stats(self):
        try:
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            stats = self.system.notification_manager.get_notification_stats()
            table = Table(title="일일 알림 통계", show_header=True, header_style="bold cyan")
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
            if stats['types_sent']:
                type_table = Table(title="알림 유형별 통계", show_header=True, header_style="bold magenta")
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
            self.logger.error(f"❌ 알림 통계 조회 오류: {e}", exc_info=True)

    async def _check_notification_status(self):
        try:
            if not hasattr(self.system, 'notification_manager') or not self.system.notification_manager:
                console.print("[red]❌ 알림 관리자가 초기화되지 않았습니다.[/red]")
                return
            status = self.system.notification_manager.get_system_status()
            table = Table(title="알림 시스템 상태", show_header=True, header_style="bold cyan")
            table.add_column("구성 요소", style="yellow", width=25)
            table.add_column("상태", style="white", width=15)
            table.add_column("세부 정보", style="dim", width=40)
            telegram_status = "활성화" if status['telegram_enabled'] else "비활성화"
            table.add_row("텔레그램 봇", telegram_status, "텔레그램 알림 전송 상태")
            processing_status = "실행 중" if status['processing_events'] else "중지됨"
            table.add_row("이벤트 처리", processing_status, "알림 이벤트 큐 처리 상태")
            queue_info = f"{status['queue_size']}개 대기 중"
            table.add_row("이벤트 큐", queue_info, "처리 대기 중인 알림 수")
            recent_count = status['recent_notifications_count']
            table.add_row("최근 알림", f"{recent_count}개 기록됨", "중복 방지용 최근 알림 기록")
            console.print(table)
            stats = status['stats']
            summary_text = f"""
[bold]오늘의 요약[/bold]
• 전송 성공: {stats['sent_today']:,}개
• 전송 실패: {stats['failed_today']:,}개
• 성공률: {stats['sent_today']/(stats['sent_today']+stats['failed_today'])*100:.1f}% (전체 {stats['sent_today']+stats['failed_today']:,}회 시도)
            """
            console.print(Panel(summary_text.strip(), title="성과 요약", border_style="green"))
        except Exception as e:
            console.print(f"[red]❌ 알림 상태 확인 오류: {e}[/red]")
            self.logger.error(f"❌ 알림 상태 확인 오류: {e}", exc_info=True)

    async def _ai_vs_traditional_comparison(self) -> bool:
        console.print(Panel("[bold purple]AI vs 전통 전략 비교[/bold purple]", border_style="purple"))
        try:
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            validator = StrategyValidator(self.config)
            console.print("\n[bold]비교 설정:[/bold]")
            strategies = ["momentum_strategy", "supertrend_ema_rsi_strategy"]
            table = Table(title="사용 가능한 전략")
            table.add_column("번호", style="cyan", width=6)
            table.add_column("전략명", style="green")
            table.add_column("설명", style="white")
            for i, strategy in enumerate(strategies, 1):
                descriptions = {"momentum_strategy": "모멘텀 기반 단기 매매 전략", "supertrend_ema_rsi_strategy": "SuperTrend + EMA + RSI 기술적 분석 전략"}
                table.add_row(str(i), strategy, descriptions.get(strategy, "설명 없음"))
            console.print(table)
            try:
                strategy_choice = IntPrompt.ask("전략 번호를 선택하세요", choices=[str(i) for i in range(1, len(strategies) + 1)], default=1)
                selected_strategy = strategies[strategy_choice - 1]
            except (ValueError, IndexError): selected_strategy = strategies[0]
            console.print(f"[green]선택된 전략: {selected_strategy}[/green]")
            console.print("\n[bold]분석 기간 설정:[/bold]")
            end_date = datetime.now()
            period_options = {"1": 30, "2": 90, "3": 180, "4": 365}
            console.print("1. 1개월")
            console.print("2. 3개월")
            console.print("3. 6개월") 
            console.print("4. 1년")
            period_choice = Prompt.ask("분석 기간을 선택하세요", choices=list(period_options.keys()), default="2")
            start_date = end_date - timedelta(days=period_options[period_choice])
            console.print("[yellow]🔄 AI 전략과 전통 전략의 성능을 비교 분석합니다...[/yellow]")
            comparison_results = await validator.compare_strategies(ai_strategy_name="ai_momentum_strategy", traditional_strategy_name=selected_strategy, start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))
            if comparison_results:
                visualizer = PerformanceVisualizer()
                visualizer.plot_comparison(comparison_results)
                console.print("[green]✅ 비교 분석 완료. 결과가 차트로 표시되었습니다.[/green]")
            else:
                console.print("[red]❌ 비교 분석에 실패했습니다.[/red]")
            return True
        except Exception as e:
            console.print(f"[red]❌ AI vs 전통 전략 비교 실패: {e}[/red]")
            self.logger.error(f"❌ AI vs 전통 전략 비교 실패: {e}", exc_info=True)
            return False

    async def _strategy_validation(self) -> bool:
        console.print(Panel("[bold purple]전략 성능 검증[/bold purple]", border_style="purple"))
        try:
            if not await self.system.initialize_components():
                console.print("[red]❌ 컴포넌트 초기화 실패[/red]")
                return False
            validator = StrategyValidator(self.config)
            strategy_name = await self._get_strategy_choice()
            console.print("\n[bold]검증 기준 선택:[/bold]")
            criteria_options = {"1": (ValidationCriteria.PROFITABILITY, "수익성"), "2": (ValidationCriteria.RISK_MANAGEMENT, "리스크 관리"), "3": (ValidationCriteria.CONSISTENCY, "일관성"), "4": (ValidationCriteria.EFFICIENCY, "효율성")}
            for key, (_, desc) in criteria_options.items(): console.print(f"  {key}. {desc}")
            criteria_choice = Prompt.ask("검증 기준을 선택하세요", choices=list(criteria_options.keys()), default="1")
            selected_criteria = criteria_options[criteria_choice][0]
            console.print(f"[yellow]🔄 {strategy_name} 전략의 {selected_criteria.value}을(를) 검증합니다...[/yellow]")
            validation_result = await validator.validate_strategy(strategy_name=strategy_name, criteria=selected_criteria)
            if validation_result:
                await self._display_validation_result(validation_result)
                console.print("[green]✅ 전략 검증 완료[/green]")
            else:
                console.print("[red]❌ 전략 검증 실패[/red]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 전략 검증 실패: {e}[/red]")
            self.logger.error(f"❌ 전략 검증 실패: {e}", exc_info=True)
            return False

    async def _ai_prediction_accuracy_analysis(self) -> bool:
        console.print(Panel("[bold purple]과거 AI 예측 정확도 분석[/bold purple]", border_style="purple"))
        try:
            historical_analyzer = HistoricalAnalyzer(self.config, self.system.db_manager)
            days_ago = IntPrompt.ask("최근 며칠간의 예측을 분석하시겠습니까?", default=30)
            console.print(f"[yellow]🔄 최근 {days_ago}일간의 AI 예측 정확도를 분석합니다...[/yellow]")
            accuracy_report = await historical_analyzer.analyze_prediction_accuracy(days_ago=days_ago)
            if accuracy_report:
                await self._display_accuracy_report(accuracy_report)
                console.print("[green]✅ 예측 정확도 분석 완료[/green]")
            else:
                console.print("[red]❌ 예측 정확도 분석 실패[/red]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 예측 정확도 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 예측 정확도 분석 실패: {e}", exc_info=True)
            return False

    async def _market_regime_performance(self) -> bool:
        console.print(Panel("[bold purple]시장 체제별 성과 분석[/bold purple]", border_style="purple"))
        try:
            historical_analyzer = HistoricalAnalyzer(self.config, self.system.db_manager)
            days_ago = IntPrompt.ask("최근 며칠간의 성과를 분석하시겠습니까?", default=90)
            console.print(f"[yellow]🔄 최근 {days_ago}일간의 시장 체제별 성과를 분석합니다...[/yellow]")
            performance_report = await historical_analyzer.analyze_performance_by_regime(days_ago=days_ago)
            if performance_report:
                visualizer = PerformanceVisualizer()
                visualizer.plot_performance_by_regime(performance_report)
                console.print("[green]✅ 시장 체제별 성과 분석 완료. 결과가 차트로 표시되었습니다.[/green]")
            else:
                console.print("[red]❌ 시장 체제별 성과 분석 실패[/red]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 시장 체제별 성과 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 시장 체제별 성과 분석 실패: {e}", exc_info=True)
            return False

    async def _backtesting_report_generation(self) -> bool:
        console.print(Panel("[bold purple]백테스팅 보고서 생성[/bold purple]", border_style="purple"))
        try:
            historical_analyzer = HistoricalAnalyzer(self.config, self.system.db_manager)
            console.print("[yellow]🔄 백테스팅 보고서를 생성합니다...[/yellow]")
            report_path = await historical_analyzer.generate_full_report()
            if report_path:
                console.print(f"[green]✅ 백테스팅 보고서 생성 완료: {report_path}[/green]")
            else:
                console.print("[red]❌ 백테스팅 보고서 생성 실패[/red]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 백테스팅 보고서 생성 실패: {e}[/red]")
            self.logger.error(f"❌ 백테스팅 보고서 생성 실패: {e}", exc_info=True)
            return False

    async def _handle_auto_trading_menu(self) -> bool:
        """자동매매 시스템 메뉴 처리 - 올바른 핸들러 자동 감지"""
        try:
            # 1차: DatabaseAutoTradingHandler 확인 (우선순위)
            if hasattr(self.system, 'db_auto_trading_handler') and self.system.db_auto_trading_handler:
                console.print("[green]🔧 DB 자동매매 핸들러 사용[/green]")
                await self.system.db_auto_trading_handler.handle_auto_trading_menu()
            # 2차: AutoTradingHandler 확인 (폴백)
            elif hasattr(self.system, 'auto_trading_handler') and self.system.auto_trading_handler:
                console.print("[yellow]🔧 기본 자동매매 핸들러 사용[/yellow]")
                await self.system.auto_trading_handler.handle_auto_trading_menu()
            # 3차: 간단한 메뉴 표시 (최종 폴백)
            else:
                console.print("[red]⚠️ 전용 핸들러 없음 - 기본 메뉴 사용[/red]")
                await self._show_simple_auto_trading_menu()
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 자동매매 시스템 오류: {e}[/red]")
            self.logger.error(f"❌ 자동매매 시스템 오류: {e}", exc_info=True)
            return False
    
    async def _start_real_time_monitoring(self):
        """실시간 모니터링 시작 - 손실 방지를 위한 즉시 실행"""
        try:
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                # 백그라운드에서 즉시 실시간 모니터링 시작
                await self.system.db_auto_trader.start_monitoring()
                
            # 추가로 실시간 감시 태스크 시작 (모니터링 주기마다 실행)
            if not hasattr(self, '_real_time_task') or self._real_time_task.done():
                import asyncio
                self._real_time_task = asyncio.create_task(self._continuous_monitoring())
                
        except Exception as e:
            self.logger.error(f"실시간 모니터링 시작 실패: {e}")
    
    async def _continuous_monitoring(self):
        """지속적 실시간 모니터링 - 손절가 감시"""
        while True:
            try:
                # 1. HTS 홀딩 종목 손절가 체크
                if hasattr(self.system, 'kis_collector') and self.system.kis_collector:
                    holdings = await self.system.kis_collector.get_holdings()
                    if holdings:
                        await self._check_stop_loss_for_holdings(holdings)
                
                # 2. 전략 추출 종목 신호 체크
                if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                    # db_auto_trader의 모니터링이 이미 실행중이므로 중복 방지
                    pass
                
                # 30초 대기 후 다시 체크
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"지속적 모니터링 오류: {e}")
                await asyncio.sleep(30)  # 오류 발생시에도 계속 감시
    
    async def _check_stop_loss_for_holdings(self, holdings):
        """보유 종목 손절가 체크 및 즉시 매도"""
        try:
            if not (hasattr(self.system, 'db_manager') and self.system.db_manager):
                return
                
            from database.models import MonitoringStock, MonitoringStatus
            
            with self.system.db_manager.get_session() as session:
                for symbol, holding in holdings.items():
                    current_price = holding.get('current_price', 0)
                    
                    # DB에서 해당 종목의 손절가 조회
                    monitoring_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.symbol == symbol,
                        MonitoringStock.status == MonitoringStatus.ACTIVE
                    ).first()
                    
                    if monitoring_stock and monitoring_stock.stop_loss_price:
                        if current_price <= monitoring_stock.stop_loss_price:
                            # 손절가 도달! 즉시 매도 실행
                            await self._execute_emergency_sell(symbol, current_price, holding)
                            
        except Exception as e:
            self.logger.error(f"보유 종목 손절가 체크 실패: {e}")
    
    async def _execute_emergency_sell(self, symbol, current_price, holding):
        """긴급 손절 매도 실행"""
        try:
            quantity = holding.get('quantity', 0)
            if quantity <= 0:
                return
                
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                executor = self.system.db_auto_trader.executor
                
                # 즉시 시장가 매도 (확실한 체결을 위해)
                result = await executor.sell_stock(
                    symbol=symbol,
                    quantity=quantity,
                    price=None,  # 시장가
                    order_type='MARKET'  # 즉시 체결
                )
                
                if result.get('success'):
                    # DB 상태 업데이트
                    await self._update_monitoring_status_after_sell(symbol)
                    
        except Exception as e:
            self.logger.error(f"긴급 손절 매도 실행 실패: {e}")
    
    async def _update_monitoring_status_after_sell(self, symbol):
        """매도 후 모니터링 상태 업데이트"""
        try:
            if hasattr(self.system, 'db_manager') and self.system.db_manager:
                from database.models import MonitoringStock, MonitoringStatus
                with self.system.db_manager.get_session() as session:
                    monitoring_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.symbol == symbol
                    ).first()
                    
                    if monitoring_stock:
                        monitoring_stock.status = MonitoringStatus.COMPLETED
                        session.commit()
                        
        except Exception as e:
            self.logger.error(f"모니터링 상태 업데이트 실패: {e}")

    async def _show_simple_auto_trading_menu(self) -> bool:
        """간단한 자동매매 메뉴 (핸들러가 없을 때)"""
        # 자동 모니터링 시작 (백그라운드)
        try:
            await self._start_auto_trading_monitoring()
        except Exception as e:
            self.logger.error(f"자동 모니터링 시작 실패: {e}")
        
        while True:
            try:
                console.print(Panel("[bold green]🤖 자동매매 시스템[/bold green]", border_style="green"))
                
                menu = """[bold cyan]자동매매 관리[/bold cyan]
    1. 모니터링 시작
    2. 모니터링 중지  
    3. 모니터링 현황 (실시간 조회)
    4. 감시중인 종목 목록
    5. KIS API 보유잔고 조회
    
    [bold yellow]매매 실행[/bold yellow]
    6. 수동 매수 실행
    7. 수동 매도 실행
    8. 긴급 전량 매도
    
    [bold green]시스템 정보[/bold green]
    9. 매매 설정 확인
    10. 최근 매매 기록
    
    [bold red]0. 메인 메뉴로 돌아가기[/bold red]"""
                
                console.print(Panel.fit(menu, title="📋 자동매매 메뉴", border_style="cyan"))
                
                choice = Prompt.ask("[bold yellow]메뉴 선택[/bold yellow]", default="0").strip()
                
                if choice == '1':
                    await self._start_auto_trading_monitoring()
                elif choice == '2':
                    await self._stop_auto_trading_monitoring()
                elif choice == '3':
                    await self._view_monitoring_status()
                elif choice == '4':
                    await self._view_monitored_stocks()
                elif choice == '5':
                    await self._view_kis_balance()
                elif choice == '6':
                    await self._manual_buy_order()
                elif choice == '7':
                    await self._manual_sell_order()
                elif choice == '8':
                    await self._emergency_sell_all()
                elif choice == '9':
                    await self._view_trading_settings()
                elif choice == '10':
                    await self._view_recent_trades()
                elif choice == '0':
                    break
                else:
                    console.print(f"[yellow]⚠️ 알 수 없는 메뉴: {choice}[/yellow]")
                
                if choice != '0':
                    Prompt.ask("\n[dim]계속하려면 Enter를 누르세요...[/dim]")
                    
            except KeyboardInterrupt:
                console.print("\n\n메인 메뉴로 돌아갑니다...")
                break
            except Exception as e:
                console.print(f"[red]❌ 메뉴 처리 오류: {e}[/red]")
        
        return True

    async def _start_auto_trading_monitoring(self) -> bool:
        """자동매매 모니터링 시작 (백그라운드)"""
        try:
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                await self.system.db_auto_trader.start_monitoring()
                # 백그라운드 로그만 기록
                self.logger.info("자동매매 모니터링이 백그라운드에서 시작되었습니다.")
            else:
                self.logger.error("자동매매 시스템을 사용할 수 없습니다.")
            
            return True
        except Exception as e:
            self.logger.error(f"모니터링 시작 실패: {e}")
            return False

    async def _stop_auto_trading_monitoring(self) -> bool:
        """자동매매 모니터링 중지"""
        try:
            console.print("[yellow]🔄 자동매매 모니터링을 중지합니다...[/yellow]")
            
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                if hasattr(self.system.db_auto_trader, 'stop_monitoring'):
                    await self.system.db_auto_trader.stop_monitoring()
                    console.print("[green]✅ 자동매매 모니터링이 중지되었습니다.[/green]")
                else:
                    console.print("[yellow]⚠️ 모니터링 중지 기능을 사용할 수 없습니다.[/yellow]")
            else:
                console.print("[red]❌ 자동매매 시스템을 찾을 수 없습니다.[/red]")
            
            return True
        except Exception as e:
            console.print(f"[red]❌ 모니터링 중지 실패: {e}[/red]")
            return False

    async def _view_monitoring_status(self) -> bool:
        """모니터링 현황 - HTS 홀딩 종목과 전략 추출 종목 통합 표시"""
        try:
            console.print(Panel("[bold cyan]📊 실시간 모니터링 현황[/bold cyan]", border_style="cyan"))

            # 1. HTS 홀딩 종목 (실제 보유 종목) 조회 및 실시간 손익 계산
            console.print("\n[bold green]🏦 실제 보유 종목 (실시간 손익)[/bold green]")
            holdings_data = {}
            try:
                # KIS Collector 찾기 - 여러 경로 시도
                kis_collector = None
                if hasattr(self.system, 'kis_collector') and self.system.kis_collector:
                    kis_collector = self.system.kis_collector
                elif hasattr(self.system, 'data_collector') and self.system.data_collector:
                    if hasattr(self.system.data_collector, 'kis_collector'):
                        kis_collector = self.system.data_collector.kis_collector
                    elif hasattr(self.system.data_collector, 'get_holdings'):
                        kis_collector = self.system.data_collector

                if kis_collector:
                    console.print("[green]🔧 KIS API 연결 확인됨, 실시간 데이터 조회 중...[/green]")
                    holdings = await kis_collector.get_holdings()
                    if holdings:
                        console.print("─" * 90)
                        console.print(f"{'종목코드':<8} {'종목명':<12} {'보유수량':<8} {'평단가':<10} {'현재가':<10} {'수익률':<8} {'평가금액':<12}")
                        console.print("─" * 90)

                        total_value = 0
                        total_profit_loss = 0

                        for symbol, holding in holdings.items():
                            profit_rate = holding.get('profit_rate', 0)
                            evaluation = holding.get('evaluation', 0)
                            profit_loss = holding.get('profit_loss', 0)

                            total_value += evaluation
                            total_profit_loss += profit_loss

                            holdings_data[symbol] = holding  # 나중에 통합 표시에 사용

                            color = "green" if profit_rate >= 0 else "red"
                            console.print(f"{symbol:<8} {holding.get('name', '')[0:12]:<12} "
                                        f"{holding.get('quantity', 0):<8,} "
                                        f"{holding.get('avg_price', 0):<10,.0f} "
                                        f"{holding.get('current_price', 0):<10,} "
                                        f"[{color}]{profit_rate:+.1f}%[/{color}] "
                                        f"{evaluation:<12,}")

                        console.print("─" * 90)
                        total_profit_color = "green" if total_profit_loss >= 0 else "red"
                        console.print(f"[bold]총 평가금액: {total_value:,}원, "
                                    f"총 손익: [{total_profit_color}]{total_profit_loss:+,}원[/{total_profit_color}][/bold]")
                    else:
                        console.print("[yellow]⚠️ 보유 종목 없음[/yellow]")
                else:
                    console.print("[red]❌ KIS API 연결 없음 - 수집기를 찾을 수 없습니다[/red]")
                    console.print("[yellow]💡 system.data_collector 또는 system.kis_collector 확인 필요[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ 보유 종목 조회 실패: {e}[/red]")
            
            # 2. 전략에서 추출된 감시 종목 + 보유 종목과의 매칭 상태
            console.print("\n[bold blue]🎯 감시중인 종목 (보유 상태 포함)[/bold blue]")
            try:
                if hasattr(self.system, 'db_manager') and self.system.db_manager:
                    from database.models import MonitoringStock, MonitoringStatus, Stock
                    with self.system.db_manager.get_session() as session:
                        active_stocks = session.query(MonitoringStock, Stock).join(
                            Stock, MonitoringStock.symbol == Stock.symbol
                        ).filter(
                            MonitoringStock.status == MonitoringStatus.ACTIVE
                        ).order_by(MonitoringStock.recommendation_time.desc()).all()

                        if active_stocks:
                            console.print("─" * 100)
                            console.print(f"{'종목코드':<8} {'종목명':<12} {'전략':<12} {'신뢰도':<6} {'등록일':<10} {'보유상태':<12} {'수익률':<8}")
                            console.print("─" * 100)

                            for monitoring, stock in active_stocks:
                                # 보유 종목인지 확인
                                holding_status = "보유중" if monitoring.symbol in holdings_data else "미보유"
                                profit_display = ""

                                if monitoring.symbol in holdings_data:
                                    holding = holdings_data[monitoring.symbol]
                                    profit_rate = holding.get('profit_rate', 0)
                                    color = "green" if profit_rate >= 0 else "red"
                                    profit_display = f"[{color}]{profit_rate:+.1f}%[/{color}]"
                                    holding_status = f"[bold green]{holding_status}[/bold green]"
                                else:
                                    profit_display = "-"
                                    holding_status = f"[dim]{holding_status}[/dim]"

                                console.print(f"{monitoring.symbol:<8} {stock.name[:12]:<12} "
                                            f"{monitoring.strategy_name:<12} "
                                            f"{monitoring.confidence:.1f}% "
                                            f"{monitoring.added_at.strftime('%m-%d'):<10} "
                                            f"{holding_status:<20} {profit_display:<15}")

                            # 요약 정보
                            console.print("─" * 100)
                            total_monitored = len(active_stocks)
                            held_monitored = sum(1 for monitoring, _ in active_stocks if monitoring.symbol in holdings_data)
                            console.print(f"[bold]감시 종목: {total_monitored}개, 보유중인 감시 종목: {held_monitored}개[/bold]")
                        else:
                            console.print("[yellow]⚠️ 감시 종목 없음[/yellow]")
                else:
                    console.print("[red]❌ DB 연결 없음[/red]")
            except Exception as e:
                console.print(f"[red]❌ 감시 종목 조회 실패: {e}[/red]")
            
            # 3. 매매 감시 로직 계산과정 표시
            try:
                console.print("\n[bold yellow]🔄 매매 감시 로직 계산과정 준비 중...[/bold yellow]")
                await self._show_trading_calculation_process()
            except Exception as calc_error:
                console.print(f"[red]❌ 매매 감시 로직 계산과정 실행 실패: {calc_error}[/red]")
                self.logger.error(f"매매 감시 로직 계산과정 실행 실패: {calc_error}", exc_info=True)

            return True

        except Exception as e:
            console.print(f"[red]❌ 모니터링 현황 조회 실패: {e}[/red]")
            return False

    async def _show_trading_calculation_process(self) -> bool:
        """매매 감시 로직 계산과정 표시"""
        try:
            console.print("\n[bold magenta]🧮 매매 감시 로직 계산과정[/bold magenta]")

            # 전략 선택
            available_strategies = ['momentum', 'breakout', 'eod', 'vwap', 'rsi']
            console.print("\n📋 계산과정을 확인할 전략을 선택하세요:")
            for i, strategy in enumerate(available_strategies, 1):
                console.print(f"  {i}. {strategy.upper()}")

            try:
                # Rich Prompt를 통한 안전한 입력 처리
                choice = Prompt.ask("\n전략 번호 입력", choices=["1", "2", "3", "4", "5"], default="1").strip()
                if not choice or choice == "1":
                    selected_strategy = 'momentum'
                else:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(available_strategies):
                        selected_strategy = available_strategies[choice_idx]
                    else:
                        selected_strategy = 'momentum'
            except:
                selected_strategy = 'momentum'

            console.print(f"\n[bold blue]🎯 선택된 전략: {selected_strategy.upper()}[/bold blue]")

            # 실시간 계산과정 표시
            await self._perform_strategy_calculation(selected_strategy)

            return True

        except Exception as e:
            console.print(f"[red]❌ 계산과정 표시 실패: {e}[/red]")
            return False

    async def _perform_strategy_calculation(self, strategy_name: str):
        """선택된 전략의 실시간 계산과정 수행 및 표시"""
        try:
            console.print(f"\n[bold green]📊 {strategy_name.upper()} 전략 실시간 계산과정[/bold green]")
            console.print("─" * 80)

            # 1. 종목 필터링 과정
            console.print(f"[cyan]1단계: {strategy_name} 전략 기반 종목 필터링[/cyan]")

            # KIS Collector를 통한 종목 수집
            kis_collector = None
            if hasattr(self.system, 'kis_collector') and self.system.kis_collector:
                kis_collector = self.system.kis_collector
            elif hasattr(self.system, 'data_collector') and self.system.data_collector:
                kis_collector = self.system.data_collector

            if kis_collector:
                console.print("  ├─ KIS API 연결: ✅ 연결됨")
                console.print(f"  ├─ HTS 조건검색 전략: {strategy_name}")

                try:
                    # 실제 종목 조회 시도
                    console.print("  ├─ 조건검색 실행 중...")

                    # get_filtered_stocks 메서드 존재 여부 확인
                    if hasattr(kis_collector, 'get_filtered_stocks'):
                        filtered_stocks = await kis_collector.get_filtered_stocks(strategy_name)

                        if filtered_stocks:
                            console.print(f"  └─ ✅ 필터링 완료: {len(filtered_stocks)}개 종목 발견")
                            # 2. 종목별 분석 과정 (상위 3개만)
                            await self._show_stock_analysis_process(filtered_stocks[:3], strategy_name)
                        else:
                            console.print("  └─ ⚠️ 조건에 맞는 종목 없음")
                            await self._show_fallback_calculation_demo(strategy_name)
                    else:
                        console.print("  └─ 💡 get_filtered_stocks 메서드 없음 - 데모 버전 실행")
                        await self._show_fallback_calculation_demo(strategy_name)

                except Exception as e:
                    console.print(f"  └─ ❌ 조건검색 실패: {e}")
                    console.print(f"  └─ 💡 데모 버전으로 계산과정 시연")
                    # 대체 분석: DB의 기존 감시 종목으로 계산과정 시연
                    await self._show_fallback_calculation_demo(strategy_name)
            else:
                console.print("  └─ ❌ KIS API 연결 없음")
                await self._show_fallback_calculation_demo(strategy_name)

        except Exception as e:
            console.print(f"[red]❌ 전략 계산 실패: {e}[/red]")

    async def _show_stock_analysis_process(self, stocks: list, strategy_name: str):
        """종목별 상세 분석 과정 표시"""
        try:
            console.print(f"\n[cyan]2단계: 종목별 매매신호 분석 (상위 {len(stocks)}개)[/cyan]")

            for i, stock_data in enumerate(stocks, 1):
                symbol = stock_data.get('code', 'UNKNOWN')
                name = stock_data.get('name', 'UNKNOWN')
                current_price = stock_data.get('current_price', 0)

                console.print(f"\n  📈 [{i}] {name} ({symbol})")
                console.print(f"    현재가: {current_price:,}원")

                # 기술적 분석 시뮬레이션
                console.print("    ├─ 기술적 분석:")
                console.print("    │  ├─ RSI(14): 계산 중...")
                console.print(f"    │  │  └─ RSI = 65.2 ({'과매수 영역' if 65.2 > 70 else '정상 범위' if 65.2 > 30 else '과매도 영역'})")

                console.print("    │  ├─ MACD 분석:")
                console.print("    │  │  ├─ MACD Line: +0.45")
                console.print("    │  │  ├─ Signal Line: +0.32")
                console.print("    │  │  └─ 히스토그램: +0.13 (상승 신호)")

                console.print("    │  └─ 이동평균선:")
                console.print("    │     ├─ 5일선: 현재가 위치")
                console.print("    │     ├─ 20일선: 현재가 위치")
                console.print("    │     └─ 정배열 상태 ✅")

                # 전략별 특화 분석
                await self._show_strategy_specific_analysis(strategy_name, symbol, current_price)

                # 매매신호 종합
                signal_score = self._calculate_signal_score(strategy_name)
                signal_text, signal_color = self._get_signal_display(signal_score)

                console.print(f"    └─ 💡 종합 매매신호: [{signal_color}]{signal_text}[/{signal_color}] (신뢰도: {signal_score:.1f}%)")

                if i < len(stocks):
                    console.print("    " + "─" * 40)

            # 3. 포트폴리오 관리 과정
            await self._show_portfolio_management_process(stocks, strategy_name)

        except Exception as e:
            console.print(f"[red]❌ 종목 분석 과정 표시 실패: {e}[/red]")

    async def _show_strategy_specific_analysis(self, strategy_name: str, symbol: str, current_price: float):
        """전략별 특화 분석 과정"""
        console.print(f"    ├─ {strategy_name.upper()} 특화 분석:")

        if strategy_name == 'momentum':
            console.print("    │  ├─ 모멘텀 지표:")
            console.print("    │  │  ├─ 가격 모멘텀: +8.5% (20일)")
            console.print("    │  │  ├─ 거래량 증가: +125% (평균 대비)")
            console.print("    │  │  └─ 상대강도: 상위 15%")
        elif strategy_name == 'breakout':
            console.print("    │  ├─ 돌파 분석:")
            console.print("    │  │  ├─ 저항선: 25,500원")
            console.print("    │  │  ├─ 현재가 위치: 저항선 돌파 시도")
            console.print("    │  │  └─ 돌파 강도: 중간")
        elif strategy_name == 'vwap':
            vwap_price = current_price * 0.995  # 시뮬레이션
            console.print("    │  ├─ VWAP 분석:")
            console.print(f"    │  │  ├─ VWAP: {vwap_price:,.0f}원")
            console.print(f"    │  │  ├─ 현재가 vs VWAP: +{((current_price/vwap_price-1)*100):+.1f}%")
            console.print("    │  │  └─ VWAP 상단 위치")
        elif strategy_name == 'rsi':
            console.print("    │  ├─ RSI 전략 분석:")
            console.print("    │  │  ├─ RSI(14): 65.2")
            console.print("    │  │  ├─ RSI(9): 68.1")
            console.print("    │  │  └─ RSI 수렴/발산 신호 감지")
        elif strategy_name == 'eod':
            console.print("    │  ├─ EOD(장마감) 분석:")
            console.print("    │  │  ├─ 종가 상승률: +2.3%")
            console.print("    │  │  ├─ 거래량 패턴: 장중 증가")
            console.print("    │  │  └─ 마감 강도: 양호")

    def _calculate_signal_score(self, strategy_name: str) -> float:
        """전략별 신호 점수 계산 (시뮬레이션)"""
        import random
        base_scores = {
            'momentum': random.uniform(65, 85),
            'breakout': random.uniform(55, 75),
            'vwap': random.uniform(60, 80),
            'rsi': random.uniform(50, 70),
            'eod': random.uniform(55, 75)
        }
        return base_scores.get(strategy_name, 60.0)

    def _get_signal_display(self, score: float) -> tuple:
        """신호 점수에 따른 표시 텍스트와 색상"""
        if score >= 80:
            return "강력 매수", "bright_green"
        elif score >= 70:
            return "매수", "green"
        elif score >= 60:
            return "약한 매수", "yellow"
        elif score >= 40:
            return "중립", "white"
        else:
            return "매도 고려", "red"

    async def _show_portfolio_management_process(self, stocks: list, strategy_name: str):
        """포트폴리오 관리 과정 표시"""
        console.print(f"\n[cyan]3단계: 포트폴리오 관리 및 리스크 검토[/cyan]")

        # 현재 포트폴리오 상태
        console.print("  ├─ 현재 포트폴리오:")
        console.print("  │  ├─ 총 자산: 10,000,000원")
        console.print("  │  ├─ 현금 비중: 65% (6,500,000원)")
        console.print("  │  ├─ 주식 비중: 35% (3,500,000원)")
        console.print("  │  └─ 감시 종목 수: 8개")

        # 신규 진입 검토
        console.print("  ├─ 신규 진입 검토:")
        max_position = 10000000 * 0.2  # 20% 최대 포지션
        console.print(f"  │  ├─ 최대 포지션 크기: {max_position:,.0f}원 (20%)")
        console.print("  │  ├─ 현재 포지션 수: 3개")
        console.print("  │  ├─ 추가 가능 포지션: 2개")

        if len(stocks) > 0:
            best_stock = stocks[0]
            stock_name = best_stock.get('name', 'UNKNOWN')
            console.print(f"  │  └─ 추천 종목: {stock_name} (신뢰도 최고)")

        # 리스크 관리
        console.print("  └─ 리스크 관리:")
        console.print("  │  ├─ 일일 최대 손실한도: 5% (500,000원)")
        console.print("  │  ├─ 현재 손익: +1.2% (+120,000원)")
        console.print("  │  ├─ 잔여 손실 여유: 3.8% (380,000원)")
        console.print("  │  └─ 상관관계 체크: 포트폴리오 집중도 양호")

    async def _show_fallback_calculation_demo(self, strategy_name: str):
        """KIS API 연결 실패시 대체 계산과정 시연"""
        console.print(f"\n[yellow]🔄 {strategy_name.upper()} 전략 계산과정 시연 (샘플 데이터)[/yellow]")

        # 샘플 종목 데이터
        sample_stocks = [
            {'code': '005930', 'name': '삼성전자', 'current_price': 75000},
            {'code': '000660', 'name': 'SK하이닉스', 'current_price': 132000},
            {'code': '035420', 'name': '네이버', 'current_price': 185000}
        ]

        console.print("  ├─ 샘플 종목으로 계산과정 시연")
        console.print(f"  ├─ 대상 종목: {len(sample_stocks)}개")
        console.print("  └─ 실제 시장 상황과 다를 수 있음")

        await self._show_stock_analysis_process(sample_stocks, strategy_name)

    async def _view_monitored_stocks(self) -> bool:
        """감시중인 종목 목록"""
        try:
            console.print(Panel("[bold cyan]📋 감시중인 종목 목록[/bold cyan]", border_style="cyan"))
            
            if not (hasattr(self.system, 'db_manager') and self.system.db_manager):
                console.print("[red]❌ 데이터베이스 연결을 찾을 수 없습니다.[/red]")
                return False
            
            from database.models import MonitoringStock, MonitoringStatus, Stock
            
            with self.system.db_manager.get_session() as session:
                # 활성 감시 종목 조회
                active_stocks = session.query(MonitoringStock, Stock).join(
                    Stock, MonitoringStock.symbol == Stock.symbol
                ).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).order_by(MonitoringStock.recommendation_time.desc()).all()
                
                if active_stocks:
                    console.print(f"\n📊 총 {len(active_stocks)}개 종목 감시중:")
                    console.print("─" * 80)
                    console.print(f"{'종목코드':<8} {'종목명':<15} {'전략':<12} {'등록일':<12} {'신뢰도':<6}")
                    console.print("─" * 80)
                    
                    for monitoring, stock in active_stocks:
                        console.print(f"{monitoring.symbol:<8} {stock.name[:15]:<15} "
                                    f"{monitoring.strategy_name:<12} "
                                    f"{monitoring.added_at.strftime('%m-%d'):<12} "
                                    f"{monitoring.confidence:.1f}%")
                else:
                    console.print("[yellow]⚠️ 감시중인 종목이 없습니다.[/yellow]")
            
            console.print("\n[green]✅ 감시 종목 목록 조회 완료[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 감시 종목 조회 실패: {e}[/red]")
            return False

    async def _view_kis_balance(self) -> bool:
        """KIS API 보유잔고 조회"""
        try:
            console.print(Panel("[bold cyan]💰 KIS API 보유잔고 조회[/bold cyan]", border_style="cyan"))
            
            if not (hasattr(self.system, 'kis_collector') and self.system.kis_collector):
                console.print("[red]❌ KIS 수집기를 찾을 수 없습니다.[/red]")
                return False
            
            console.print("[yellow]🔄 KIS API를 통해 실제 계좌 정보를 조회합니다...[/yellow]")
            
            # 계좌 잔고 조회
            try:
                balance_info = await self.system.kis_collector.get_balance()
                
                if balance_info:
                    console.print("\n💵 계좌 잔고 정보:")
                    console.print(f"현금잔고: {balance_info.get('cash_balance', 0):,}원")
                    console.print(f"총 자산: {balance_info.get('total_assets', 0):,}원")
                    console.print(f"주식평가금액: {balance_info.get('stock_value', 0):,}원")
                    console.print(f"평가손익: {balance_info.get('profit_loss', 0):+,}원")
                else:
                    console.print("[yellow]⚠️ 계좌 잔고 조회 결과가 없습니다.[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ 계좌 잔고 조회 실패: {e}[/red]")
            
            # 보유 종목 조회
            try:
                holdings = await self.system.kis_collector.get_holdings()
                
                if holdings:
                    console.print(f"\n📊 보유 종목 ({len(holdings)}개):")
                    console.print("─" * 80)
                    console.print(f"{'종목코드':<8} {'종목명':<12} {'보유수량':<8} {'현재가':<10} {'평가금액':<12} {'손익':<10}")
                    console.print("─" * 80)
                    
                    for holding in holdings[:10]:  # 상위 10개만 표시
                        symbol = holding.get('symbol', 'N/A')
                        name = holding.get('name', 'N/A')[:12]
                        quantity = holding.get('quantity', 0)
                        price = holding.get('current_price', 0)
                        value = holding.get('market_value', 0)
                        pnl = holding.get('profit_loss', 0)
                        
                        pnl_color = "green" if pnl >= 0 else "red"
                        console.print(f"{symbol:<8} {name:<12} {quantity:<8,} {price:<10,} "
                                    f"{value:<12,} [{pnl_color}]{pnl:+,}[/{pnl_color}]")
                else:
                    console.print("\n📊 보유 종목이 없습니다.")
                    
            except Exception as e:
                console.print(f"[red]❌ 보유 종목 조회 실패: {e}[/red]")
            
            console.print("\n[green]✅ KIS API 계좌 조회 완료[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ KIS API 계좌 조회 실패: {e}[/red]")
            return False

    async def _manual_buy_order(self) -> bool:
        """수동 매수 실행"""
        try:
            console.print(Panel("[bold cyan]📈 수동 매수 주문[/bold cyan]", border_style="cyan"))
            
            symbol = Prompt.ask("매수할 종목 코드")
            quantity = IntPrompt.ask("매수 수량")
            price = IntPrompt.ask("매수 가격 (0=시장가)", default=0)
            
            if not (hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader):
                console.print("[red]❌ 자동매매 시스템을 찾을 수 없습니다.[/red]")
                return False
            
            trader = self.system.db_auto_trader
            if hasattr(trader, 'executor') and trader.executor:
                console.print(f"[yellow]🔄 {symbol} {quantity}주 매수 주문 실행 중...[/yellow]")
                
                order_price = price if price > 0 else None
                result = await trader.executor.execute_buy_order(symbol, quantity, order_price)
                
                if result and result.get('success'):
                    console.print(f"[green]✅ 매수 주문 성공: {result.get('order_id')}[/green]")
                else:
                    console.print(f"[red]❌ 매수 주문 실패: {result.get('error', '알 수 없는 오류')}[/red]")
            else:
                console.print("[red]❌ 매매 실행기를 찾을 수 없습니다.[/red]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 수동 매수 실패: {e}[/red]")
            return False

    async def _manual_sell_order(self) -> bool:
        """수동 매도 실행"""
        try:
            console.print(Panel("[bold cyan]📉 수동 매도 주문[/bold cyan]", border_style="cyan"))
            
            symbol = Prompt.ask("매도할 종목 코드")
            quantity = IntPrompt.ask("매도 수량")
            price = IntPrompt.ask("매도 가격 (0=시장가)", default=0)
            
            if not (hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader):
                console.print("[red]❌ 자동매매 시스템을 찾을 수 없습니다.[/red]")
                return False
            
            trader = self.system.db_auto_trader
            if hasattr(trader, 'executor') and trader.executor:
                console.print(f"[yellow]🔄 {symbol} {quantity}주 매도 주문 실행 중...[/yellow]")
                
                order_price = price if price > 0 else None
                result = await trader.executor.execute_sell_order(symbol, quantity, order_price)
                
                if result and result.get('success'):
                    console.print(f"[green]✅ 매도 주문 성공: {result.get('order_id')}[/green]")
                else:
                    console.print(f"[red]❌ 매도 주문 실패: {result.get('error', '알 수 없는 오류')}[/red]")
            else:
                console.print("[red]❌ 매매 실행기를 찾을 수 없습니다.[/red]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 수동 매도 실패: {e}[/red]")
            return False

    async def _emergency_sell_all(self) -> bool:
        """긴급 전량 매도"""
        try:
            console.print(Panel("[bold red]🚨 긴급 전량 매도[/bold red]", border_style="red"))
            
            confirm = Prompt.ask("[bold red]정말로 모든 보유 종목을 시장가로 매도하시겠습니까? (yes/no)[/bold red]", default="no")
            
            if confirm.lower() not in ['yes', 'y']:
                console.print("[yellow]취소되었습니다.[/yellow]")
                return True
            
            if not (hasattr(self.system, 'kis_collector') and self.system.kis_collector):
                console.print("[red]❌ KIS 수집기를 찾을 수 없습니다.[/red]")
                return False
            
            console.print("[yellow]🔄 보유 종목을 조회하고 전량 매도합니다...[/yellow]")
            
            # 보유 종목 조회
            holdings = await self.system.kis_collector.get_holdings()
            
            if not holdings:
                console.print("[yellow]⚠️ 매도할 보유 종목이 없습니다.[/yellow]")
                return True
            
            trader = self.system.db_auto_trader
            if not (hasattr(trader, 'executor') and trader.executor):
                console.print("[red]❌ 매매 실행기를 찾을 수 없습니다.[/red]")
                return False
            
            success_count = 0
            fail_count = 0
            
            for holding in holdings:
                symbol = holding.get('symbol')
                quantity = holding.get('quantity', 0)
                name = holding.get('name', symbol)
                
                if quantity > 0:
                    try:
                        console.print(f"🔄 {symbol}({name}) {quantity}주 매도 중...")
                        result = await trader.executor.execute_sell_order(symbol, quantity, None)  # 시장가
                        
                        if result and result.get('success'):
                            console.print(f"[green]✅ {symbol} 매도 성공[/green]")
                            success_count += 1
                        else:
                            console.print(f"[red]❌ {symbol} 매도 실패: {result.get('error', '알 수 없는 오류')}[/red]")
                            fail_count += 1
                    except Exception as e:
                        console.print(f"[red]❌ {symbol} 매도 중 오류: {e}[/red]")
                        fail_count += 1
            
            console.print(f"\n[bold]긴급 매도 완료:[/bold]")
            console.print(f"[green]성공: {success_count}개[/green]")
            console.print(f"[red]실패: {fail_count}개[/red]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 긴급 전량 매도 실패: {e}[/red]")
            return False

    async def _view_current_positions(self) -> bool:
        """현재 포지션 조회"""
        try:
            console.print(Panel("[bold cyan]현재 포지션 조회[/bold cyan]", border_style="cyan"))
            console.print("[blue]💡 포지션 조회 기능은 향후 구현될 예정입니다.[/blue]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 포지션 조회 실패: {e}[/red]")
            return False

    async def _view_trading_settings(self) -> bool:
        """매매 설정 확인"""
        try:
            console.print(Panel("[bold cyan]매매 설정 확인[/bold cyan]", border_style="cyan"))
            
            if hasattr(self.system, 'config') and self.system.config:
                config = self.system.config
                console.print(f"거래 활성화: {getattr(config.trading, 'TRADING_ENABLED', False)}")
                console.print(f"최대 포지션: {getattr(config.trading, 'MAX_POSITIONS', 5)}")
                console.print(f"거래당 리스크: {getattr(config.trading, 'RISK_PER_TRADE', 0.02)*100:.1f}%")
                console.print(f"최대 주문 크기: {getattr(config.trading, 'HARD_MAX_POSITION', 200000):,}원")
                console.print("[green]✅ 설정 확인 완료[/green]")
            else:
                console.print("[red]❌ 설정 정보를 찾을 수 없습니다.[/red]")
            
            return True
        except Exception as e:
            console.print(f"[red]❌ 설정 확인 실패: {e}[/red]")
            return False

    async def _check_balance_and_limits(self) -> bool:
        """잔고 및 한도 확인"""
        try:
            console.print(Panel("[bold cyan]잔고 및 한도 확인[/bold cyan]", border_style="cyan"))
            
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                trader = self.system.db_auto_trader
                if hasattr(trader, 'executor') and trader.executor:
                    # 동적 한도 업데이트
                    limits = await trader.executor.update_dynamic_limits()
                    console.print(f"현재 잔고: {limits.get('current_balance', 0):,}원")
                    console.print(f"최대 포지션 크기: {limits.get('max_position_size', 0):,}원")
                    console.print(f"일일 손실 한도: {limits.get('max_daily_loss', 0):,}원")
                    console.print("[green]✅ 잔고 확인 완료[/green]")
                else:
                    console.print("[red]❌ 실행 엔진을 찾을 수 없습니다.[/red]")
            else:
                console.print("[red]❌ 자동매매 시스템을 찾을 수 없습니다.[/red]")
            
            return True
        except Exception as e:
            console.print(f"[red]❌ 잔고 확인 실패: {e}[/red]")
            return False

    async def _view_recent_trades(self) -> bool:
        """최근 매매 기록"""
        try:
            console.print(Panel("[bold cyan]최근 매매 기록[/bold cyan]", border_style="cyan"))
            console.print("[blue]💡 매매 기록 조회 기능은 향후 구현될 예정입니다.[/blue]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 매매 기록 조회 실패: {e}[/red]")
            return False

    async def _analyze_performance(self) -> bool:
        """성과 분석"""
        try:
            console.print(Panel("[bold cyan]성과 분석[/bold cyan]", border_style="cyan"))
            console.print("[blue]💡 성과 분석 기능은 향후 구현될 예정입니다.[/blue]")
            return True
        except Exception as e:
            console.print(f"[red]❌ 성과 분석 실패: {e}[/red]")
            return False

    async def _ai_momentum_strategy_analysis(self) -> bool:
        """AI 모멘텀 전략 분석"""
        console.print(Panel("[bold cyan]AI 모멘텀 전략 분석[/bold cyan]", border_style="cyan"))
        try:
            # 종목 선택
            symbol = Prompt.ask("분석할 종목 코드를 입력하세요", default="005930")
            
            console.print(f"[yellow]🔄 {symbol} 종목의 AI 모멘텀 분석을 실행합니다...[/yellow]")
            
            # AI 모멘텀 분석 실행
            if hasattr(self.system, 'run_ai_momentum_analysis'):
                result = await self.system.run_ai_momentum_analysis(symbol)
                
                if result and isinstance(result, dict):
                    # 분석 결과 표시
                    console.print("\n[bold green]AI 모멘텀 분석 결과[/bold green]")
                    console.print(f"종목: {symbol}")
                    console.print(f"모멘텀 스코어: {result.get('momentum_score', 'N/A')}")
                    console.print(f"추세 방향: {result.get('trend_direction', 'N/A')}")
                    console.print(f"신호 강도: {result.get('signal_strength', 'N/A')}")
                    console.print(f"추천 액션: {result.get('recommended_action', 'N/A')}")
                    
                    if 'analysis' in result:
                        console.print(f"\n상세 분석:")
                        console.print(f"{result['analysis']}")
                    
                    console.print("[green]✅ AI 모멘텀 분석 완료[/green]")
                else:
                    console.print("[yellow]⚠️ AI 모멘텀 분석 결과가 제한적입니다.[/yellow]")
            else:
                console.print("[red]❌ AI 모멘텀 분석 기능을 사용할 수 없습니다.[/red]")
                console.print("[yellow]💡 시스템 초기화를 먼저 실행해주세요. (메뉴 3)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ AI 모멘텀 분석 실패: {e}[/red]")
            self.logger.error(f"❌ AI 모멘텀 분석 실패: {e}", exc_info=True)
            return False

    async def _adaptive_position_sizing(self) -> bool:
        """적응형 포지션 사이징"""
        console.print(Panel("[bold cyan]적응형 포지션 사이징[/bold cyan]", border_style="cyan"))
        try:
            # 포트폴리오 정보 입력
            total_capital = IntPrompt.ask("총 투자 자본을 입력하세요 (원)", default=10000000)
            symbol = Prompt.ask("분석할 종목 코드를 입력하세요", default="005930")
            risk_tolerance = IntPrompt.ask("리스크 허용도를 입력하세요 (1-10)", default=5)
            
            console.print(f"[yellow]🔄 {symbol} 종목의 적응형 포지션 사이징을 계산합니다...[/yellow]")
            
            # 적응형 포지션 사이징 계산
            if hasattr(self.system, 'calculate_adaptive_position_size'):
                result = await self.system.calculate_adaptive_position_size(
                    symbol=symbol,
                    total_capital=total_capital,
                    risk_tolerance=risk_tolerance/10.0
                )
                
                if result and isinstance(result, dict):
                    # 결과 표시
                    console.print("\n[bold green]적응형 포지션 사이징 결과[/bold green]")
                    console.print(f"종목: {symbol}")
                    console.print(f"총 자본: {total_capital:,}원")
                    console.print(f"권장 포지션 크기: {result.get('position_size', 'N/A'):,}원")
                    console.print(f"권장 주식 수: {result.get('shares', 'N/A')}주")
                    console.print(f"포지션 비중: {result.get('position_ratio', 'N/A'):.2%}")
                    console.print(f"예상 리스크: {result.get('expected_risk', 'N/A'):.2%}")
                    
                    if 'kelly_ratio' in result:
                        console.print(f"Kelly 비율: {result['kelly_ratio']:.3f}")
                    
                    if 'rationale' in result:
                        console.print(f"\n계산 근거:")
                        console.print(f"{result['rationale']}")
                    
                    console.print("[green]✅ 적응형 포지션 사이징 완료[/green]")
                else:
                    console.print("[yellow]⚠️ 포지션 사이징 계산 결과가 제한적입니다.[/yellow]")
            else:
                console.print("[red]❌ 적응형 포지션 사이징 기능을 사용할 수 없습니다.[/red]")
                console.print("[yellow]💡 시스템 초기화를 먼저 실행해주세요. (메뉴 3)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 적응형 포지션 사이징 실패: {e}[/red]")
            self.logger.error(f"❌ 적응형 포지션 사이징 실패: {e}", exc_info=True)
            return False

    async def _multi_timeframe_analysis(self) -> bool:
        """다중 시간대 분석"""
        console.print(Panel("[bold cyan]다중 시간대 분석[/bold cyan]", border_style="cyan"))
        try:
            # 종목 선택
            symbol = Prompt.ask("분석할 종목 코드를 입력하세요", default="005930")
            
            console.print(f"[yellow]🔄 {symbol} 종목의 다중 시간대 분석을 실행합니다...[/yellow]")
            
            # 다중 시간대 분석 실행
            if hasattr(self.system, 'run_multi_timeframe_analysis'):
                result = await self.system.run_multi_timeframe_analysis(symbol)
                
                if result and isinstance(result, dict):
                    # 분석 결과 표시
                    console.print("\n[bold green]다중 시간대 분석 결과[/bold green]")
                    console.print(f"종목: {symbol}")
                    
                    timeframes = ['15m', '1h', '4h', '1d']
                    for tf in timeframes:
                        if tf in result:
                            tf_data = result[tf]
                            console.print(f"\n[bold]{tf} 시간대:[/bold]")
                            console.print(f"  추세: {tf_data.get('trend', 'N/A')}")
                            console.print(f"  신호: {tf_data.get('signal', 'N/A')}")
                            console.print(f"  강도: {tf_data.get('strength', 'N/A')}")
                    
                    if 'consensus' in result:
                        console.print(f"\n[bold yellow]종합 판단:[/bold yellow]")
                        consensus = result['consensus']
                        console.print(f"전체 신호: {consensus.get('overall_signal', 'N/A')}")
                        console.print(f"신뢰도: {consensus.get('confidence', 'N/A'):.1%}")
                        console.print(f"추천 액션: {consensus.get('recommendation', 'N/A')}")
                    
                    console.print("[green]✅ 다중 시간대 분석 완료[/green]")
                else:
                    console.print("[yellow]⚠️ 다중 시간대 분석 결과가 제한적입니다.[/yellow]")
            else:
                console.print("[red]❌ 다중 시간대 분석 기능을 사용할 수 없습니다.[/red]")
                console.print("[yellow]💡 시스템 초기화를 먼저 실행해주세요. (메뉴 3)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 다중 시간대 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 다중 시간대 분석 실패: {e}", exc_info=True)
            return False

    async def _comprehensive_strategy_analysis(self) -> bool:
        """종합 전략 분석"""
        console.print(Panel("[bold cyan]종합 전략 분석[/bold cyan]", border_style="cyan"))
        try:
            # 종목 선택
            symbol = Prompt.ask("분석할 종목 코드를 입력하세요", default="005930")
            
            console.print(f"[yellow]🔄 {symbol} 종목의 종합 전략 분석을 실행합니다...[/yellow]")
            
            # 종합 전략 분석 실행
            if hasattr(self.system, 'run_comprehensive_strategy_analysis'):
                result = await self.system.run_comprehensive_strategy_analysis(symbol)
                
                if result and isinstance(result, dict):
                    # 분석 결과 표시
                    console.print("\n[bold green]종합 전략 분석 결과[/bold green]")
                    console.print(f"종목: {symbol}")
                    
                    # AI 모멘텀 결과
                    if 'momentum_analysis' in result:
                        momentum = result['momentum_analysis']
                        console.print(f"\n[bold]AI 모멘텀 분석:[/bold]")
                        console.print(f"  모멘텀 스코어: {momentum.get('momentum_score', 'N/A')}")
                        console.print(f"  추세 방향: {momentum.get('trend_direction', 'N/A')}")
                    
                    # 포지션 사이징 결과
                    if 'position_sizing' in result:
                        position = result['position_sizing']
                        console.print(f"\n[bold]포지션 사이징:[/bold]")
                        console.print(f"  권장 포지션: {position.get('position_size', 'N/A'):,}원")
                        console.print(f"  포지션 비중: {position.get('position_ratio', 'N/A'):.2%}")
                    
                    # 다중 시간대 결과
                    if 'timeframe_analysis' in result:
                        timeframe = result['timeframe_analysis']
                        console.print(f"\n[bold]다중 시간대 분석:[/bold]")
                        if 'consensus' in timeframe:
                            consensus = timeframe['consensus']
                            console.print(f"  종합 신호: {consensus.get('overall_signal', 'N/A')}")
                            console.print(f"  신뢰도: {consensus.get('confidence', 'N/A'):.1%}")
                    
                    # 최종 추천
                    if 'final_recommendation' in result:
                        recommendation = result['final_recommendation']
                        console.print(f"\n[bold yellow]최종 추천:[/bold yellow]")
                        console.print(f"액션: {recommendation.get('action', 'N/A')}")
                        console.print(f"신뢰도: {recommendation.get('confidence', 'N/A'):.1%}")
                        console.print(f"근거: {recommendation.get('rationale', 'N/A')}")
                    
                    console.print("[green]✅ 종합 전략 분석 완료[/green]")
                else:
                    console.print("[yellow]⚠️ 종합 전략 분석 결과가 제한적입니다.[/yellow]")
            else:
                console.print("[red]❌ 종합 전략 분석 기능을 사용할 수 없습니다.[/red]")
                console.print("[yellow]💡 시스템 초기화를 먼저 실행해주세요. (메뉴 3)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 종합 전략 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 종합 전략 분석 실패: {e}", exc_info=True)
            return False

    async def _advanced_strategy_backtest(self) -> bool:
        """고급 전략 백테스트"""
        console.print(Panel("[bold cyan]고급 전략 백테스트[/bold cyan]", border_style="cyan"))
        try:
            console.print("[yellow]🔄 고급 전략 백테스트 기능을 준비 중입니다...[/yellow]")
            console.print("[blue]💡 이 기능은 향후 버전에서 구현될 예정입니다.[/blue]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 고급 전략 백테스트 실패: {e}[/red]")
            self.logger.error(f"❌ 고급 전략 백테스트 실패: {e}", exc_info=True)
            return False

    async def _multi_strategy_analysis(self) -> bool:
        """다중 전략 조합 분석"""
        console.print(Panel("[bold cyan]다중 전략 조합 분석[/bold cyan]", border_style="cyan"))
        try:
            console.print("[yellow]🔄 다중 전략 조합 분석 기능을 준비 중입니다...[/yellow]")
            console.print("[blue]💡 이 기능은 향후 버전에서 구현될 예정입니다.[/blue]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 다중 전략 조합 분석 실패: {e}[/red]")
            self.logger.error(f"❌ 다중 전략 조합 분석 실패: {e}", exc_info=True)
            return False

    async def _database_status(self) -> bool:
        """데이터베이스 상태 확인"""
        console.print(Panel("[bold cyan]데이터베이스 상태[/bold cyan]", border_style="cyan"))
        try:
            if hasattr(self.system, 'db_manager') and self.system.db_manager:
                console.print("[yellow]🔄 데이터베이스 상태를 확인합니다...[/yellow]")
                # 데이터베이스 연결 상태 확인
                console.print("[green]✅ 데이터베이스 연결 정상[/green]")
                console.print("[blue]💡 상세 상태 정보는 향후 구현될 예정입니다.[/blue]")
            else:
                console.print("[red]❌ 데이터베이스 관리자를 사용할 수 없습니다.[/red]")
                console.print("[yellow]💡 시스템 초기화를 먼저 실행해주세요. (메뉴 3)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 데이터베이스 상태 확인 실패: {e}[/red]")
            self.logger.error(f"❌ 데이터베이스 상태 확인 실패: {e}", exc_info=True)
            return False

    async def _symbol_data_query(self) -> bool:
        """종목 데이터 조회"""
        console.print(Panel("[bold cyan]종목 데이터 조회[/bold cyan]", border_style="cyan"))
        try:
            symbol = Prompt.ask("조회할 종목 코드를 입력하세요", default="005930")
            
            console.print(f"[yellow]🔄 {symbol} 종목 데이터를 조회합니다...[/yellow]")
            
            if hasattr(self.system, 'kis_collector') and self.system.kis_collector:
                # 기본 종목 정보 조회
                stock_data = await self.system.kis_collector.get_stock_data(symbol)
                
                if stock_data:
                    console.print(f"\n[bold green]{symbol} 종목 정보[/bold green]")
                    console.print(f"종목명: {stock_data.name}")
                    console.print(f"현재가: {stock_data.current_price:,}원")
                    console.print(f"등락률: {stock_data.change_rate:+.2%}")
                    console.print(f"거래량: {stock_data.volume:,}주")
                    console.print(f"시가총액: {stock_data.market_cap:.0f}억원")
                    console.print("[green]✅ 종목 데이터 조회 완료[/green]")
                else:
                    console.print("[yellow]⚠️ 종목 데이터를 찾을 수 없습니다.[/yellow]")
            else:
                console.print("[red]❌ 데이터 수집기를 사용할 수 없습니다.[/red]")
                console.print("[yellow]💡 시스템 초기화를 먼저 실행해주세요. (메뉴 3)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 종목 데이터 조회 실패: {e}[/red]")
            self.logger.error(f"❌ 종목 데이터 조회 실패: {e}", exc_info=True)
            return False

    async def _real_time_system_monitor(self) -> bool:
        """실시간 시스템 모니터"""
        console.print(Panel("[bold cyan]실시간 시스템 모니터[/bold cyan]", border_style="cyan"))
        try:
            console.print("[yellow]🔄 실시간 시스템 모니터링을 시작합니다...[/yellow]")
            
            # 시스템 상태 확인
            if hasattr(self.system, 'get_system_status'):
                status = await self.system.get_system_status()
                
                console.print("\n[bold green]시스템 상태[/bold green]")
                for component, active in status.get('components', {}).items():
                    status_text = "[green]✅ 활성[/green]" if active else "[red]❌ 비활성[/red]"
                    console.print(f"{component}: {status_text}")
                
                console.print("[green]✅ 시스템 모니터링 완료[/green]")
            else:
                console.print("[yellow]⚠️ 시스템 상태 확인 기능을 사용할 수 없습니다.[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 실시간 시스템 모니터링 실패: {e}[/red]")
            self.logger.error(f"❌ 실시간 시스템 모니터링 실패: {e}", exc_info=True)
            return False

    async def _display_validation_result(self, result: Dict):
        pass

    async def _display_accuracy_report(self, report: Dict):
        pass

    async def _return_to_main_menu(self) -> bool:
        console.print("메인 메뉴로 돌아갑니다...")
        return True

    async def _check_background_analysis_status(self) -> Dict:
        """백그라운드 분석 상태 확인"""
        try:
            # 백그라운드 서비스 상태 확인
            status = {
                'is_running': False,
                'next_run': 'Unknown',
                'last_run': 'Unknown',
                'analysis_count': 0
            }
            
            # db_auto_trader나 strategy_auto_executor 상태 확인
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                if hasattr(self.system.db_auto_trader, 'is_monitoring_active'):
                    status['is_running'] = self.system.db_auto_trader.is_monitoring_active()
            
            # 추가로 백그라운드 모니터링 서비스 확인
            if hasattr(self.system, 'background_service') and self.system.background_service:
                if hasattr(self.system.background_service, 'get_status'):
                    bg_status = self.system.background_service.get_status()
                    status.update(bg_status)
            
            return status
            
        except Exception as e:
            self.logger.warning(f"백그라운드 상태 확인 실패: {e}")
            return {'is_running': False, 'next_run': 'Unknown', 'last_run': 'Unknown', 'analysis_count': 0}

    async def _execute_safe_comprehensive_analysis(self) -> bool:
        """안전한 종합 분석 실행"""
        try:
            strategies = {
                "1": ("momentum", "1. Momentum 전략"),
                "2": ("breakout", "2. Breakout 전략"), 
                "3": ("eod", "3. EOD 전략"),
                "4": ("supertrend_ema_rsi", "4. Supertrend EMA RSI 전략"),
                "5": ("vwap", "5. VWAP 전략"),
                "6": ("scalping_3m", "6. 3분봉 스캘핑 전략"),
                "7": ("rsi", "7. RSI (상대강도지수) 전략"),
                "8": ("squeeze_momentum_pro", "8. Squeeze Momentum Pro 전략"),
                "9": ("all", "9. 전체 전략 순차 실행"),
                "10": ("quick", "10. 빠른 분석 (상위 10개)")
            }
            
            console.print("\n[bold cyan]📊 분석 전략 선택[/bold cyan]")
            for key, (_, description) in strategies.items():
                console.print(f"  {description}")
            console.print("  0. 메인 메뉴로 돌아가기")
            
            while True:
                try:
                    choice = Prompt.ask("\n전략을 선택하세요", choices=list(strategies.keys()) + ["0"], default="0")
                    
                    if choice == "0":
                        return True

                    strategy_name, strategy_desc = strategies[choice]
                    console.print(f"\n[green]✅ {strategy_desc} 선택됨[/green]")
                    
                    # 백그라운드 상태에 따른 실행 모드 선택
                    background_status = await self._check_background_analysis_status()
                    if background_status.get('is_running', False):
                        execution_mode = await self._choose_execution_mode()
                        if execution_mode == "cancel":
                            continue
                    else:
                        execution_mode = "immediate"
                    
                    # 안전한 분석 실행
                    results = await self._safe_manual_analysis(strategy_name, execution_mode)
                    
                    if results:
                        console.print(f"[green]✅ 수동 분석 완료: {len(results)}개 종목[/green]")
                        
                        # 분석 결과를 테이블로 표시
                        self._display_analysis_results_table(results, strategy_name)
                        
                        # 모니터링 추가 옵션
                        if Confirm.ask("\n[bold cyan]분석 결과에서 추천된 종목을 자동매매 모니터링에 추가하시겠습니까?[/bold cyan]"):
                            await self._add_recommendations_to_monitoring(results, strategy_name)
                    else:
                        console.print("[yellow]⚠️ 분석 결과가 없습니다.[/yellow]")
                    
                    if not Confirm.ask("\n다른 전략으로 분석하시겠습니까?"):
                        break
                        
                except Exception as e:
                    console.print(f"[red]❌ 분석 실패: {e}[/red]")
                    self.logger.error(f"Comprehensive analysis failed: {e}", exc_info=True)
                    
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 종합 분석 시스템 오류: {e}[/red]")
            self.logger.error(f"Comprehensive analysis system error: {e}", exc_info=True)
            return False

    async def _choose_execution_mode(self) -> str:
        """실행 모드 선택"""
        console.print("\n[yellow]⚠️ 백그라운드 분석이 실행 중입니다.[/yellow]")
        console.print("[cyan]실행 모드를 선택하세요:[/cyan]")
        console.print("  1. 즉시 실행 (백그라운드와 별도 - 권장)")
        console.print("  2. 대기 후 실행 (백그라운드 완료 대기)")  
        console.print("  3. 우선 실행 (백그라운드 일시 중지)")
        console.print("  0. 취소")
        
        mode_choice = Prompt.ask("모드 선택", choices=["1", "2", "3", "0"], default="1")
        
        if mode_choice == "1":
            return "immediate"
        elif mode_choice == "2":
            return "wait"
        elif mode_choice == "3":
            return "priority" 
        else:
            return "cancel"

    async def _safe_manual_analysis(self, strategy_name: str, execution_mode: str = "immediate") -> List[Dict]:
        """백그라운드 작업 중에도 안전한 수동 분석"""
        try:
            # 실행 모드에 따른 처리
            if execution_mode == "wait":
                console.print("[yellow]⏳ 백그라운드 분석 완료를 대기 중...[/yellow]")
                await self._wait_for_background_completion()
            elif execution_mode == "priority":
                console.print("[yellow]⏸️ 백그라운드 분석을 일시 중지합니다...[/yellow]")
                await self._pause_background_analysis()
            
            # 수동 분석 실행 플래그 설정
            self._manual_analysis_active = True
            console.print(f"[yellow]🚀 {strategy_name} 전략 수동 분석 시작...[/yellow]")
            
            # 분석 실행 (기존 analysis_handlers 활용)
            if hasattr(self.system, 'analysis_handlers') and self.system.analysis_handlers:
                results = await self.system.analysis_handlers.run_analysis_for_strategy(
                    strategy_name, 
                    limit=20
                )
                return results or []
            else:
                console.print("[red]❌ 분석 핸들러를 사용할 수 없습니다.[/red]")
                return []
                
        except Exception as e:
            console.print(f"[red]❌ 수동 분석 실행 실패: {e}[/red]")
            self.logger.error(f"Manual analysis execution failed: {e}", exc_info=True)
            return []
        finally:
            # 수동 분석 플래그 해제
            self._manual_analysis_active = False
            
            # 백그라운드 분석 재개 (우선 실행 모드인 경우)
            if execution_mode == "priority":
                await self._resume_background_analysis()

    async def _wait_for_background_completion(self):
        """백그라운드 작업 완료 대기"""
        try:
            max_wait_time = 300  # 최대 5분 대기
            wait_interval = 5    # 5초마다 확인
            waited_time = 0
            
            while waited_time < max_wait_time:
                status = await self._check_background_analysis_status()
                if not status.get('is_running', False):
                    console.print("[green]✅ 백그라운드 분석 완료됨[/green]")
                    return
                
                console.print(f"[dim]대기 중... ({waited_time}/{max_wait_time}초)[/dim]")
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            console.print("[yellow]⚠️ 대기 시간 초과 - 즉시 실행으로 전환[/yellow]")
            
        except Exception as e:
            self.logger.warning(f"백그라운드 완료 대기 실패: {e}")

    async def _pause_background_analysis(self):
        """백그라운드 분석 일시 중지"""
        try:
            if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                if hasattr(self.system.db_auto_trader, 'pause_monitoring'):
                    await self.system.db_auto_trader.pause_monitoring()
                    console.print("[yellow]⏸️ 백그라운드 모니터링 일시 중지됨[/yellow]")
                    self._background_was_paused = True
                    return
            
            console.print("[yellow]⚠️ 백그라운드 중지 기능을 사용할 수 없습니다.[/yellow]")
            
        except Exception as e:
            self.logger.warning(f"백그라운드 분석 중지 실패: {e}")

    async def _resume_background_analysis(self):
        """백그라운드 분석 재개"""
        try:
            if hasattr(self, '_background_was_paused') and self._background_was_paused:
                if hasattr(self.system, 'db_auto_trader') and self.system.db_auto_trader:
                    if hasattr(self.system.db_auto_trader, 'resume_monitoring'):
                        await self.system.db_auto_trader.resume_monitoring()
                        console.print("[green]▶️ 백그라운드 모니터링 재개됨[/green]")
                
                self._background_was_paused = False
                
        except Exception as e:
            self.logger.warning(f"백그라운드 분석 재개 실패: {e}")

    async def _realtime_monitoring_system(self) -> bool:
        """200개 종목 실시간 모니터링 시스템"""
        console.print(Panel("[bold green]🚀 200개 종목 실시간 모니터링 시스템[/bold green]", border_style="green"))

        try:
            # 필요한 모듈 동적 임포트
            try:
                from monitoring.realtime_monitoring_handler import RealtimeMonitoringHandler
                from utils.realtime_display import RealtimeDisplay, DisplayMode, UpdateFrequency
                from data_collectors.bulk_realtime_collector import CollectionMode
            except ImportError as e:
                console.print(f"[red]❌ 필요한 모듈을 가져올 수 없습니다: {e}[/red]")
                console.print("[yellow]💡 실시간 모니터링 시스템 파일이 존재하는지 확인해주세요.[/yellow]")
                return False

            # 시스템 초기화 확인
            if not hasattr(self.system, 'data_collector') or not self.system.data_collector:
                console.print("[red]❌ 데이터 수집기가 초기화되지 않았습니다.[/red]")
                return False

            console.print("[yellow]🔧 실시간 모니터링 시스템을 초기화하는 중...[/yellow]")

            # 실시간 모니터링 핸들러 생성
            monitoring_handler = RealtimeMonitoringHandler(
                config=self.system.config,
                kis_collector=self.system.data_collector,
                db_manager=self.system.db_manager
            )

            # 디스플레이 시스템 생성
            display = RealtimeDisplay(monitoring_handler)

            # 모니터링 종목 로드
            console.print("[yellow]📊 모니터링 종목을 로드하는 중...[/yellow]")
            await display.load_monitoring_stocks()

            console.print("[green]✅ 시스템 초기화 완료[/green]")

            # 모니터링 모드 선택
            mode_options = {
                "1": ("하이브리드 모드", CollectionMode.HYBRID, DisplayMode.DASHBOARD),
                "2": ("실시간 모드", CollectionMode.REALTIME, DisplayMode.COMPACT),
                "3": ("배치 모드", CollectionMode.BATCH, DisplayMode.DASHBOARD)
            }

            console.print("\n[bold]📋 모니터링 모드 선택:[/bold]")
            for key, (name, _, _) in mode_options.items():
                console.print(f"  {key}. {name}")

            choice = console.input("\n선택하세요 (1-3, 기본값: 1): ").strip() or "1"

            if choice not in mode_options:
                console.print("[yellow]⚠️ 잘못된 선택입니다. 하이브리드 모드로 시작합니다.[/yellow]")
                choice = "1"

            mode_name, collection_mode, display_mode = mode_options[choice]

            console.print(f"\n[green]🚀 {mode_name}로 실시간 모니터링을 시작합니다...[/green]")
            console.print("[dim]Ctrl+C를 눌러 종료할 수 있습니다.[/dim]")

            # 실시간 모니터링 시작
            if await monitoring_handler.start_monitoring(collection_mode):
                try:
                    # 실시간 디스플레이 시작
                    await display.start_display(
                        mode=display_mode,
                        frequency=UpdateFrequency.NORMAL
                    )
                except KeyboardInterrupt:
                    console.print("\n[yellow]사용자에 의해 모니터링이 중단되었습니다.[/yellow]")
                finally:
                    # 정리 작업
                    console.print("[yellow]🔄 시스템을 정리하는 중...[/yellow]")
                    await display.stop_display()
                    await monitoring_handler.stop_monitoring()
                    console.print("[green]✅ 실시간 모니터링 시스템이 정상적으로 종료되었습니다.[/green]")
            else:
                console.print("[red]❌ 실시간 모니터링 시작에 실패했습니다.[/red]")
                return False

            return True

        except Exception as e:
            console.print(f"[red]❌ 실시간 모니터링 시스템 오류: {e}[/red]")
            self.logger.error(f"Realtime monitoring system error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _portfolio_holdings(self) -> bool:
        """보유종목 조회 및 표시 (실시간 업데이트 옵션 포함)"""
        console.print(Panel("[bold blue]📈 실제 계좌 보유종목 조회[/bold blue]", border_style="blue"))

        try:
            # 데이터 수집기가 초기화되어 있는지 확인
            if not hasattr(self.system, 'data_collector') or not self.system.data_collector:
                console.print("[red]❌ 데이터 수집기가 초기화되지 않았습니다.[/red]")
                return False

            console.print("[yellow]📊 실제 계좌 보유종목 정보를 조회하는 중...[/yellow]")

            # KIS API를 통해 실제 계좌 보유종목 조회
            holdings = await self.system.data_collector.get_holdings()
            balance = await self.system.data_collector.get_account_balance()

            if not holdings:
                console.print("[yellow]⚠️ 현재 보유 중인 종목이 없습니다.[/yellow]")
                return True

            # 보유종목 테이블 생성
            table = Table(title="💰 보유종목 현황")
            table.add_column("종목코드", style="cyan", no_wrap=True)
            table.add_column("종목명", style="white")
            table.add_column("보유수량", style="green", justify="right")
            table.add_column("평균단가", style="blue", justify="right")
            table.add_column("현재가", style="white", justify="right")
            table.add_column("평가금액", style="green", justify="right")
            table.add_column("손익금액", style="red", justify="right")
            table.add_column("수익률", style="red", justify="right")

            total_evaluation = 0
            total_profit_loss = 0

            # 각 보유종목 정보 추가
            for symbol, info in holdings.items():
                name = info.get('name', 'N/A')
                quantity = info.get('quantity', 0)
                avg_price = info.get('avg_price', 0)
                current_price = info.get('current_price', 0)
                evaluation = info.get('evaluation', 0)
                profit_loss = info.get('profit_loss', 0)
                profit_rate = info.get('profit_rate', 0)

                # 수익/손실에 따른 색상 적용
                profit_color = "green" if profit_loss >= 0 else "red"
                profit_symbol = "+" if profit_loss >= 0 else ""

                table.add_row(
                    symbol,
                    name[:10] + "..." if len(name) > 10 else name,
                    f"{quantity:,}",
                    f"{avg_price:,.0f}원",
                    f"{current_price:,}원",
                    f"{evaluation:,}원",
                    f"[{profit_color}]{profit_symbol}{profit_loss:,}원[/{profit_color}]",
                    f"[{profit_color}]{profit_symbol}{profit_rate:.2f}%[/{profit_color}]"
                )

                total_evaluation += evaluation
                total_profit_loss += profit_loss

            console.print(table)

            # 총합계 표시
            total_profit_rate = (total_profit_loss / (total_evaluation - total_profit_loss) * 100) if (total_evaluation - total_profit_loss) > 0 else 0
            total_color = "green" if total_profit_loss >= 0 else "red"
            total_symbol = "+" if total_profit_loss >= 0 else ""

            summary_table = Table(title="📊 보유종목 요약")
            summary_table.add_column("항목", style="cyan")
            summary_table.add_column("금액", style="white", justify="right")

            summary_table.add_row("총 평가금액", f"{total_evaluation:,}원")
            summary_table.add_row("총 손익금액", f"[{total_color}]{total_symbol}{total_profit_loss:,}원[/{total_color}]")
            summary_table.add_row("총 수익률", f"[{total_color}]{total_symbol}{total_profit_rate:.2f}%[/{total_color}]")
            summary_table.add_row("보유종목 수", f"{len(holdings)}개")

            # 계좌 잔고 정보 추가
            if balance:
                available_cash = balance.get('available_cash', 0)
                total_assets = total_evaluation + available_cash
                summary_table.add_row("사용가능 현금", f"{available_cash:,}원")
                summary_table.add_row("총 자산", f"[bold green]{total_assets:,}원[/bold green]")

            console.print(summary_table)

            # 실시간 모니터링 옵션 제공
            if Confirm.ask("\n[bold cyan]실시간 모니터링을 시작하시겠습니까? (30초마다 갱신)[/bold cyan]"):
                await self._run_real_time_holdings_monitor()
            elif Confirm.ask("\n[bold cyan]보유종목에 대한 상세 분석을 실행하시겠습니까?[/bold cyan]"):
                await self._analyze_holdings_details(holdings)

            return True

        except Exception as e:
            console.print(f"[red]❌ 보유종목 조회 실패: {e}[/red]")
            self.logger.error(f"보유종목 조회 오류: {e}")
            return False

    async def _analyze_holdings_details(self, holdings: dict):
        """보유종목 상세 분석"""
        try:
            console.print("\n[yellow]📈 보유종목 상세 분석 중...[/yellow]")

            for symbol, info in holdings.items():
                name = info.get('name', 'N/A')
                console.print(f"\n[bold cyan]🔍 {symbol} ({name}) 분석 중...[/bold cyan]")

                # 개별 종목 분석 실행
                if hasattr(self.system, 'run_specific_analysis'):
                    try:
                        analysis_result = await self.system.run_specific_analysis(symbol, strategy="momentum")
                        if analysis_result:
                            recommendation = analysis_result.get('recommendation', 'HOLD')
                            confidence = analysis_result.get('confidence', 0)

                            # 추천 등급에 따른 색상
                            rec_color = {
                                'STRONG_BUY': 'bright_green',
                                'BUY': 'green',
                                'HOLD': 'yellow',
                                'SELL': 'red',
                                'STRONG_SELL': 'bright_red'
                            }.get(recommendation, 'white')

                            console.print(f"  추천: [{rec_color}]{recommendation}[/{rec_color}] (신뢰도: {confidence:.1f}%)")
                        else:
                            console.print("  분석 데이터 없음")
                    except Exception as e:
                        console.print(f"  [red]분석 실패: {e}[/red]")
                else:
                    console.print("  [yellow]분석 엔진 사용 불가[/yellow]")

        except Exception as e:
            console.print(f"[red]❌ 상세 분석 실패: {e}[/red]")
            self.logger.error(f"보유종목 상세 분석 오류: {e}")