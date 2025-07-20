#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/main.py

AI Trading System with News Analysis - 메인 실행 파일
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Rich UI 라이브러리
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Prompt, Confirm

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 전역 콘솔 객체
console = Console()

# ======================== KISCollector 헬퍼 함수들 ========================

async def safe_get_filtered_stocks(collector, limit: int = 50):
    """KISCollector에서 안전하게 필터링된 종목 조회 - 종목명 포함"""
    try:
        if hasattr(collector, 'get_filtered_stocks'):
            stocks = await collector.get_filtered_stocks(limit)
        elif hasattr(collector, 'get_filtered_stocks_pykrx'):
            stocks = await collector.get_filtered_stocks_pykrx(limit)
        else:
            # 기본 종목 리스트 반환
            all_stocks = await collector.get_stock_list()
            stocks = all_stocks[:limit]
        
        # 종목명이 없는 경우 pykrx로 보완
        enhanced_stocks = []
        for symbol, name in stocks:
            if not name or name.startswith('종목'):
                try:
                    from pykrx import stock as pykrx_stock
                    real_name = pykrx_stock.get_market_ticker_name(symbol)
                    if real_name:
                        name = real_name
                except:
                    pass
            enhanced_stocks.append((symbol, name))
        
        return enhanced_stocks
        
    except Exception as e:
        collector.logger.error(f"❌ 안전한 종목 조회 실패: {e}")
        # 최후의 수단
        return [("005930", "삼성전자"), ("000660", "SK하이닉스"), ("035420", "NAVER")]

def check_collector_methods(collector):
    """KISCollector 필수 메서드 존재 여부 확인"""
    required_methods = ['get_stock_list', 'get_stock_info', '_meets_filter_criteria']
    missing = [m for m in required_methods if not hasattr(collector, m)]
    
    if missing:
        collector.logger.error(f"❌ 누락된 메서드: {missing}")
        return False
    
    collector.logger.info("✅ 필수 메서드 모두 존재")
    return True

async def ensure_collector_methods(collector):
    """KISCollector에 필요한 메서드가 없으면 추가"""
    try:
        # get_filtered_stocks 메서드가 없으면 추가
        if not hasattr(collector, 'get_filtered_stocks'):
            async def get_filtered_stocks(limit: int = 50, use_cache: bool = True):
                """필터링된 종목 리스트 반환"""
                try:
                    # pykrx 방식 우선 시도
                    if hasattr(collector, 'get_filtered_stocks_pykrx'):
                        return await collector.get_filtered_stocks_pykrx(limit, use_cache)
                    
                    # 기본 방식
                    collector.logger.info(f"🔍 기본 필터링 시작 (목표: {limit}개)")
                    
                    # 캐시 확인
                    if use_cache and hasattr(collector, '_get_cached_filtered_stocks'):
                        cached_stocks = await collector._get_cached_filtered_stocks(limit)
                        if cached_stocks:
                            return cached_stocks
                    
                    # 전체 종목 리스트 조회
                    all_stocks = await collector.get_stock_list()
                    
                    # 샘플링
                    import random
                    sample_size = min(300, len(all_stocks))
                    sample_stocks = random.sample(all_stocks, sample_size)
                    
                    filtered_stocks = []
                    for symbol, name in sample_stocks:
                        if len(filtered_stocks) >= limit:
                            break
                            
                        try:
                            stock_info = await collector.get_stock_info(symbol)
                            if stock_info and collector._meets_filter_criteria(stock_info):
                                filtered_stocks.append((symbol, stock_info['name']))
                            await asyncio.sleep(0.05)
                        except:
                            continue
                    
                    if not filtered_stocks:
                        return await collector._get_major_stocks_as_fallback(limit)
                    
                    return filtered_stocks
                    
                except Exception as e:
                    collector.logger.error(f"❌ 필터링 실패: {e}")
                    return await collector._get_major_stocks_as_fallback(limit)
            
            # 메서드를 collector 객체에 바인딩
            import types
            collector.get_filtered_stocks = types.MethodType(get_filtered_stocks, collector)
            collector.logger.info("✅ get_filtered_stocks 메서드 추가됨")
        
        return True
        
    except Exception as e:
        collector.logger.error(f"❌ 메서드 추가 실패: {e}")
        return False

# ======================== TradingSystem 클래스 ========================

class TradingSystem:
    """AI Trading System 메인 클래스"""
    
    def __init__(self):
        self.config = None
        self.logger = None
        self._initialize_system()
    
    def _initialize_system(self):
        """시스템 초기화"""
        try:
            # Config 로드
            from config import Config
            self.config = Config
            
            # Logger 설정
            from utils.logger import get_logger
            self.logger = get_logger("TradingSystem")
            
            console.print("[green]✅ 시스템 초기화 완료[/green]")
            
        except ImportError as e:
            console.print(f"[red]❌ 시스템 초기화 실패: {e}[/red]")
            console.print("[yellow]💡 필요한 모듈이 설치되어 있는지 확인하세요.[/yellow]")
            sys.exit(1)
    
    def print_banner(self):
        """시스템 배너 출력"""
        banner_text = (
            "[bold cyan]🚀 AI Trading System v2.0[/bold cyan]\n\n"
            "📊 실시간 주식 분석 + 📰 뉴스 재료 분석\n"
            "🔍 기술적 분석 + 펀더멘털 분석 + 뉴스 감정 분석\n"
            "💰 리스크 관리 + 포지션 관리 + 자동 알림\n\n"
            "🎯 [bold green]가중치: 장기재료 > 중기재료 > 단기재료[/bold green]"
        )
        
        console.print(Panel.fit(
            banner_text,
            title="AI Trading System",
            border_style="cyan"
        ))
    
    def show_main_menu(self):
        """메인 메뉴 표시"""
        menu_items = [
            ("[bold cyan]🔧 시스템 관리[/bold cyan]", [
                ("1", "시스템 테스트 및 상태 확인"),
                ("2", "설정 확인 및 변경")
            ]),
            ("[bold green]📊 분석 및 매매[/bold green]", [
                ("3", "실시간 종목 분석 ([yellow]뉴스 분석 포함[/yellow])"),
                ("4", "뉴스 재료 분석만 실행"),
                ("5", "자동매매 시작 ([red]실제 거래[/red])"),
                ("6", "백테스트 실행"),
                ("7", "스케줄러 시작")
            ]),
            ("[bold blue]🗄️ 데이터베이스[/bold blue]", [
                ("8", "데이터베이스 상태 확인"),
                ("9", "종목 데이터 조회"),
                ("10", "분석 결과 조회"),
                ("11", "거래 기록 조회")
            ]),
            ("[bold magenta]🛠️ 고급 기능[/bold magenta]", [
                ("12", "데이터 정리 및 최적화"),
                ("13", "로그 분석")
            ])
        ]
        
        menu_text = ""
        for category, items in menu_items:
            menu_text += f"{category}\n"
            for num, desc in items:
                menu_text += f"  {num}. {desc}\n"
            menu_text += "\n"
        
        menu_text += "  [bold red]0. 종료[/bold red]"
        
        console.print(Panel.fit(
            menu_text,
            title="📋 메인 메뉴",
            border_style="cyan"
        ))
    
    def get_user_choice(self) -> str:
        """사용자 선택 입력받기"""
        try:
            return Prompt.ask(
                "\n[bold yellow]메뉴를 선택하세요[/bold yellow]",
                default="0"
            ).strip()
        except KeyboardInterrupt:
            return "0"
    
    async def run_interactive_mode(self):
        """대화형 모드 실행"""
        self.print_banner()
        console.print(f"[dim]시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")
        
        while True:
            try:
                self.show_main_menu()
                choice = self.get_user_choice()
                
                if choice == "0":
                    console.print("\n[bold]👋 프로그램을 종료합니다.[/bold]")
                    break
                
                # 메뉴 실행
                success = await self._execute_menu_choice(choice)
                
                # 결과 표시
                if success:
                    console.print(Panel("[bold green]✅ 작업 완료[/bold green]", border_style="green"))
                elif success is False:  # None이 아닌 False인 경우에만
                    console.print(Panel("[bold red]❌ 작업 실패[/bold red]", border_style="red"))
                
                if choice != "0":
                    Prompt.ask("\n[dim]계속하려면 Enter를 누르세요[/dim]", default="")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]🛑 사용자 중단[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]❌ 오류 발생: {e}[/red]")
                Prompt.ask("\n[dim]계속하려면 Enter를 누르세요[/dim]", default="")
    
    async def _execute_menu_choice(self, choice: str) -> Optional[bool]:
        """메뉴 선택 실행"""
        menu_handlers = {
            "1": self._system_test,
            "2": self._show_config,
            "3": self._comprehensive_analysis,
            "4": self._news_analysis_only,
            "5": self._auto_trading,
            "6": self._backtest,
            "7": self._scheduler,
            "8": self._db_status,
            "9": self._db_stocks,
            "10": self._db_analysis,
            "11": self._db_trades,
            "12": self._data_cleanup,
            "13": self._log_analysis
        }
        
        handler = menu_handlers.get(choice)
        if handler:
            return await handler()
        else:
            console.print(f"[red]❌ 잘못된 선택: {choice}[/red]")
            return None
    
    # ======================== 메뉴 핸들러들 ========================
    
    async def _system_test(self) -> bool:
        """시스템 테스트"""
        console.print("[bold]🧪 시스템 테스트 시작[/bold]")
        
        test_modules = [
            ("설정 시스템", self._test_config),
            ("데이터베이스", self._test_database),
            ("데이터 수집기", self._test_collectors),
            ("뉴스 수집기", self._test_news_collector),
            ("분석 엔진", self._test_analyzers),
            ("전략 모듈", self._test_strategies)
        ]
        
        results = {}
        
        with Progress() as progress:
            task = progress.add_task("[cyan]테스트 진행 중...", total=len(test_modules))
            
            for name, test_func in test_modules:
                progress.update(task, description=f"[cyan]{name} 테스트 중...[/cyan]")
                try:
                    results[name] = await test_func()
                    status = "✅" if results[name] else "❌"
                    console.print(f"{status} {name}")
                except Exception as e:
                    results[name] = False
                    console.print(f"❌ {name} - 오류: {e}")
                
                progress.advance(task)
        
        # 결과 테이블 표시
        self._show_test_results(results)
        
        passed = sum(results.values())
        total = len(results)
        return passed >= total * 0.7  # 70% 이상 통과
    
    async def _test_config(self) -> bool:
        """설정 테스트"""
        try:
            self.config.validate()
            return True
        except Exception:
            return False
    
    async def _test_database(self) -> bool:
        """데이터베이스 테스트"""
        try:
            from database.database_manager import DatabaseManager
            db_manager = DatabaseManager(self.config)
            await db_manager.create_tables()
            await db_manager.close()
            return True
        except Exception:
            return False
    
    async def _test_collectors(self) -> bool:
        """데이터 수집기 테스트"""
        try:
            from data_collectors.kis_collector import KISCollector
            collector = KISCollector(self.config)
            # 필요한 메서드들이 있는지 확인하고 없으면 추가
            await ensure_collector_methods(collector)
            check_collector_methods(collector)
            return True
        except Exception as e:
            console.print(f"[red]데이터 수집기 테스트 실패: {e}[/red]")
            return False
    
    async def _test_news_collector(self) -> bool:
        """뉴스 수집기 테스트"""
        try:
            from data_collectors.news_collector import NewsCollector
            news_collector = NewsCollector(self.config)
            # 간단한 테스트
            test_result = news_collector.get_news_analysis_summary("삼성전자", "005930")
            return True
        except Exception:
            return False
    
    async def _test_analyzers(self) -> bool:
        """분석 엔진 테스트"""
        try:
            from analyzers.analysis_engine import AnalysisEngine
            AnalysisEngine(self.config)
            return True
        except Exception:
            return False
    
    async def _test_strategies(self) -> bool:
        """전략 모듈 테스트"""
        try:
            from strategies.momentum_strategy import MomentumStrategy
            MomentumStrategy(self.config)
            return True
        except Exception:
            return False
    
    def _show_test_results(self, results: Dict[str, bool]):
        """테스트 결과 테이블 표시"""
        table = Table(title="🧪 시스템 테스트 결과")
        table.add_column("모듈", style="cyan")
        table.add_column("상태", style="bold")
        table.add_column("설명")
        
        for module, result in results.items():
            if result:
                status = "[green]✅ 통과[/green]"
                desc = "정상 작동"
            else:
                status = "[red]❌ 실패[/red]"
                desc = "확인 필요"
            
            table.add_row(module, status, desc)
        
        console.print(table)
        
        passed = sum(results.values())
        total = len(results)
        success_rate = (passed / total) * 100
        
        if success_rate == 100:
            console.print(Panel(
                "[bold green]🎉 모든 테스트 통과! 시스템이 정상 작동합니다.[/bold green]",
                border_style="green"
            ))
        elif success_rate >= 70:
            console.print(Panel(
                f"[bold yellow]⚠️ {success_rate:.0f}% 테스트 통과. 일부 기능 확인 필요.[/bold yellow]",
                border_style="yellow"
            ))
        else:
            console.print(Panel(
                f"[bold red]❌ {success_rate:.0f}% 테스트 실패. 설치 및 설정 확인 필요.[/bold red]",
                border_style="red"
            ))
    
    async def _show_config(self) -> bool:
        """설정 정보 표시"""
        config_info = (
            f"[bold]🔧 시스템 설정 정보[/bold]\n\n"
            f"환경: {self.config.ENVIRONMENT}\n"
            f"데이터베이스: {self.config.database.DB_URL}\n"
            f"KIS API: {'✅ 설정됨' if self.config.api.KIS_APP_KEY else '❌ 미설정'}\n"
            f"네이버 API: {'✅ 설정됨' if self.config.api.NAVER_CLIENT_ID else '❌ 미설정'}\n"
            f"텔레그램: {'✅ 설정됨' if self.config.api.TELEGRAM_BOT_TOKEN else '❌ 미설정'}"
        )
        
        console.print(Panel(config_info, title="설정 정보", border_style="blue"))
        return True
    
    async def _comprehensive_analysis(self) -> bool:
        """종합 분석 (뉴스 포함) - 수정된 버전"""
        console.print("[bold]🔍 종합 분석 (뉴스 분석 포함)[/bold]")
        
        # 옵션 수집
        options = self._get_analysis_options(include_news=True)
        if not options:
            return False
        
        try:
            from analyzers.analysis_engine import AnalysisEngine
            from data_collectors.kis_collector import KISCollector
            from database.database_manager import DatabaseManager
            
            # 시스템 초기화
            db_manager = DatabaseManager(self.config)
            analysis_engine = AnalysisEngine(self.config)
            
            # analyze_stock 메서드를 직접 추가 (동적으로)
            import types
            async def analyze_stock(stock_data, strategy="momentum", include_news=True):
                """analyze_comprehensive의 래퍼 함수"""
                try:
                    # StockData 객체에서 정보 추출
                    if hasattr(stock_data, 'symbol') and hasattr(stock_data, 'name'):
                        symbol = stock_data.symbol
                        name = stock_data.name
                    else:
                        symbol = stock_data.get('symbol', 'UNKNOWN')
                        name = stock_data.get('name', 'Unknown')
                    
                    # analyze_comprehensive 호출
                    return await analysis_engine.analyze_comprehensive(
                        symbol=symbol,
                        name=name,
                        stock_data=stock_data,
                        strategy=strategy
                    )
                except Exception as e:
                    analysis_engine.logger.error(f"❌ analyze_stock 실패: {e}")
                    return None
            
            # 메서드를 동적으로 바인딩
            analysis_engine.analyze_stock = types.MethodType(analyze_stock, analysis_engine)
            
            async with KISCollector(self.config) as kis_collector:
                await kis_collector.initialize()
                
                # KISCollector 메서드 확인 및 추가
                await ensure_collector_methods(kis_collector)
                
                # 종목 선택
                target_symbols = await self._get_target_symbols(kis_collector, options)
                if not target_symbols:
                    console.print("[red]❌ 분석할 종목이 없습니다.[/red]")
                    return False
                
                # 분석 실행
                results = await self._run_comprehensive_analysis(
                    analysis_engine, kis_collector, db_manager, target_symbols, options
                )
                
                # 결과 표시
                if results:
                    self._display_analysis_results(results, include_news=True)
                    await db_manager.close()
                    return True
                else:
                    await db_manager.close()
                    return False
        
        except Exception as e:
            console.print(f"[red]❌ 종합 분석 실패: {e}[/red]")
            return False


    
    async def _news_analysis_only(self) -> bool:
        """뉴스 분석만 실행"""
        console.print("[bold]📰 뉴스 재료 분석[/bold]")
        
        # 옵션 수집
        options = self._get_analysis_options(news_only=True)
        if not options:
            return False
        
        try:
            from data_collectors.news_collector import NewsCollector
            from data_collectors.kis_collector import KISCollector
            
            news_collector = NewsCollector(self.config)
            
            # 종목 리스트 가져오기
            if options.get("symbols"):
                stock_list = [(symbol, f"종목{symbol}") for symbol in options["symbols"]]
            else:
                async with KISCollector(self.config) as kis_collector:
                    await kis_collector.initialize()
                    await ensure_collector_methods(kis_collector)
                    stock_list = await safe_get_filtered_stocks(kis_collector, limit=options.get("limit", 20))
            
            # 뉴스 분석 실행
            results = await self._run_news_analysis(news_collector, stock_list)
            
            # 결과 표시
            if results:
                self._display_news_results(results)
                return True
            else:
                console.print("[yellow]📰 뉴스 재료를 발견한 종목이 없습니다.[/yellow]")
                return False
        
        except Exception as e:
            console.print(f"[red]❌ 뉴스 분석 실패: {e}[/red]")
            return False
    
    async def _run_news_analysis(self, news_collector, stock_list: List[tuple]) -> List[Dict]:
        """뉴스 분석 실행"""
        results = []
        
        with Progress() as progress:
            task = progress.add_task("[cyan]뉴스 분석 중...", total=len(stock_list))
            
            for symbol, name in stock_list:
                progress.update(task, description=f"[cyan]{symbol} 뉴스 분석 중...[/cyan]")
                
                try:
                    # 뉴스 분석
                    analysis_result = news_collector.get_news_analysis_summary(name, symbol)
                    
                    if analysis_result and analysis_result.get('has_material_news'):
                        results.append({
                            'stock_info': {'symbol': symbol, 'name': name},
                            'material_summary': analysis_result
                        })
                        
                        progress.update(task, description=f"[green]{symbol} 재료 발견![/green]")
                    
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️ {symbol} 뉴스 분석 실패: {e}[/yellow]")
                
                progress.advance(task)
        
        return results
    
    async def _auto_trading(self) -> bool:
        """자동매매"""
        console.print("[bold red]💰 자동매매 모드[/bold red]")
        console.print("[bold red]⚠️ 실제 돈이 거래됩니다![/bold red]")
        
        if not Confirm.ask("정말 자동매매를 시작하시겠습니까?"):
            return False
        
        console.print(Panel(
            "[bold yellow]🚧 자동매매 기능은 현재 개발 중입니다.[/bold yellow]",
            title="개발 중",
            border_style="yellow"
        ))
        return True
    
    async def _backtest(self) -> bool:
        """백테스트"""
        console.print("[bold]📈 백테스트[/bold]")
        console.print(Panel(
            "[bold yellow]🚧 백테스트 기능은 현재 개발 중입니다.[/bold yellow]",
            title="개발 중",
            border_style="yellow"
        ))
        return True
    
    async def _scheduler(self) -> bool:
        """스케줄러"""
        console.print("[bold]⏰ 스케줄러[/bold]")
        console.print(Panel(
            "[bold yellow]🚧 스케줄러 기능은 현재 개발 중입니다.[/bold yellow]",
            title="개발 중",
            border_style="yellow"
        ))
        return True
    
    async def _db_status(self) -> bool:
        """데이터베이스 상태"""
        console.print("[bold]🗄️ 데이터베이스 상태 확인[/bold]")
        
        try:
            from database.database_manager import DatabaseManager
            from database.db_operations import DatabaseOperations
            
            db_manager = DatabaseManager(self.config)
            db_ops = DatabaseOperations(db_manager)
            
            report = await db_ops.get_status_report()
            db_ops.print_status_report(report)
            
            await db_manager.close()
            return True
        
        except Exception as e:
            console.print(f"[red]❌ 데이터베이스 상태 확인 실패: {e}[/red]")
            return False
    
    async def _db_stocks(self) -> bool:
        """종목 데이터 조회"""
        console.print("[bold]📈 종목 데이터 조회[/bold]")
        
        options = self._get_db_query_options()
        
        try:
            from database.database_manager import DatabaseManager
            from database.db_operations import DatabaseOperations
            
            db_manager = DatabaseManager(self.config)
            db_ops = DatabaseOperations(db_manager)
            
            report = await db_ops.get_stocks_report(
                limit=options.get("limit", 50),
                symbols=options.get("symbols")
            )
            db_ops.print_stocks_report(report)
            
            await db_manager.close()
            return True
        
        except Exception as e:
            console.print(f"[red]❌ 종목 데이터 조회 실패: {e}[/red]")
            return False
    
    async def _db_analysis(self) -> bool:
        """분석 결과 조회"""
        console.print("[bold]🔍 분석 결과 조회[/bold]")
        
        options = self._get_db_query_options()
        
        try:
            from database.database_manager import DatabaseManager
            from database.db_operations import DatabaseOperations
            
            db_manager = DatabaseManager(self.config)
            db_ops = DatabaseOperations(db_manager)
            
            report = await db_ops.get_analysis_report(
                limit=options.get("limit", 50),
                symbols=options.get("symbols")
            )
            db_ops.print_analysis_report(report)
            
            await db_manager.close()
            return True
        
        except Exception as e:
            console.print(f"[red]❌ 분석 결과 조회 실패: {e}[/red]")
            return False
    
    async def _db_trades(self) -> bool:
        """거래 기록 조회"""
        console.print("[bold]💰 거래 기록 조회[/bold]")
        
        options = self._get_db_query_options()
        
        try:
            from database.database_manager import DatabaseManager
            from database.db_operations import DatabaseOperations
            
            db_manager = DatabaseManager(self.config)
            db_ops = DatabaseOperations(db_manager)
            
            report = await db_ops.get_trades_report(
                symbols=options.get("symbols")
            )
            db_ops.print_trades_report(report)
            
            await db_manager.close()
            return True
        
        except Exception as e:
            console.print(f"[red]❌ 거래 기록 조회 실패: {e}[/red]")
            return False
    
    async def _data_cleanup(self) -> bool:
        """데이터 정리"""
        console.print("[bold]🧹 데이터 정리[/bold]")
        
        if not Confirm.ask("90일 이전 데이터를 정리하시겠습니까?"):
            return False
        
        try:
            from database.database_manager import DatabaseManager
            
            db_manager = DatabaseManager(self.config)
            
            with Progress() as progress:
                task = progress.add_task("[cyan]데이터 정리 중...", total=100)
                await db_manager.cleanup_old_data(days_to_keep=90)
                progress.update(task, completed=100)
            
            await db_manager.close()
            console.print("[green]✅ 데이터 정리 완료[/green]")
            return True
        
        except Exception as e:
            console.print(f"[red]❌ 데이터 정리 실패: {e}[/red]")
            return False
    
    async def _log_analysis(self) -> bool:
        """로그 분석"""
        console.print("[bold]📊 로그 분석[/bold]")
        
        try:
            from database.database_manager import DatabaseManager
            
            db_manager = DatabaseManager(self.config)
            logs = await db_manager.get_system_logs(hours=24, limit=1000)
            
            if logs:
                self._display_log_analysis(logs)
            else:
                console.print("[yellow]📝 분석할 로그가 없습니다.[/yellow]")
            
            await db_manager.close()
            return True
        
        except Exception as e:
            console.print(f"[red]❌ 로그 분석 실패: {e}[/red]")
            return False
    
    # ======================== 유틸리티 메서드들 ========================
    
    def _get_analysis_options(self, include_news=False, news_only=False) -> Dict:
        """분석 옵션 수집"""
        options = {}
        
        try:
            # 종목 선택
            console.print("분석 방식을 선택하세요:")
            console.print("1. 전체 종목 (기본)")
            console.print("2. 특정 종목 지정")
            console.print("3. 상위 N개 종목")
            
            choice = Prompt.ask(
                "선택",
                choices=["1", "2", "3"],
                default="1"
            )
            
            if choice == "2":
                symbols_input = Prompt.ask("종목코드 입력 (쉼표로 구분, 예: 005930,000660)")
                if symbols_input:
                    options["symbols"] = [s.strip() for s in symbols_input.split(",")]
            elif choice == "3":
                limit = Prompt.ask("조회할 종목 수", default="20")
                options["limit"] = int(limit) if limit.isdigit() else 20
            else:
                options["limit"] = 20
            
            # 전략 선택 (종합 분석인 경우)
            if include_news and not news_only:
                console.print("\n전략 선택:")
                console.print("1. momentum (모멘텀)")
                console.print("2. breakout (돌파)")
                console.print("3. mean_reversion (평균회귀)")
                console.print("4. eod (종가 기반)")
                
                strategy_choice = Prompt.ask("전략 선택", choices=["1", "2", "3", "4"], default="1")
                strategy_map = {"1": "momentum", "2": "breakout", "3": "mean_reversion", "4": "eod"}
                options["strategy"] = strategy_map[strategy_choice]
            
            return options
        
        except Exception as e:
            console.print(f"[red]❌ 옵션 설정 실패: {e}[/red]")
            return {}
    
    def _get_db_query_options(self) -> Dict:
        """DB 조회 옵션 수집"""
        options = {}
        
        try:
            # 조회 방식 선택
            console.print("조회 방식:")
            console.print("1. 전체 조회")
            console.print("2. 특정 종목")
            
            choice = Prompt.ask("선택", choices=["1", "2"], default="1")
            
            if choice == "2":
                symbols_input = Prompt.ask("종목코드 입력 (쉼표로 구분)")
                if symbols_input:
                    options["symbols"] = [s.strip() for s in symbols_input.split(",")]
            
            # 조회 개수
            limit = Prompt.ask("조회할 개수", default="50")
            options["limit"] = int(limit) if limit.isdigit() else 50
            
            return options
        
        except Exception:
            return {"limit": 50}
    
    async def _get_target_symbols(self, kis_collector, options: Dict) -> List[str]:
        """분석 대상 종목 리스트 가져오기"""
        if options.get("symbols"):
            return options["symbols"]
        else:
            stocks = await safe_get_filtered_stocks(kis_collector, limit=options.get("limit", 20))
            return [symbol for symbol, name in stocks]
    
    async def _run_comprehensive_analysis(self, analysis_engine, kis_collector, db_manager, 
                                    target_symbols: List[str], options: Dict) -> List[Dict]:
        """종합 분석 실행 - 종목명 개선"""
        results = []
        strategy = options.get("strategy", "momentum")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]종합 분석 중...", total=len(target_symbols))
            
            for symbol in target_symbols:
                progress.update(task, description=f"[cyan]{symbol} 분석 중...[/cyan]")
                
                try:
                    # 데이터 조회
                    stock_info = await kis_collector.get_stock_info(symbol)
                    if not stock_info:
                        progress.advance(task)
                        continue
                    
                    # 종목명 확보 (여러 방법 시도)
                    stock_name = None
                    
                    # 1. stock_info에서 종목명 가져오기
                    if isinstance(stock_info, dict):
                        stock_name = stock_info.get('name') or stock_info.get('hts_kor_isnm')
                    
                    # 2. 종목명이 없으면 pykrx로 조회 시도
                    if not stock_name or stock_name.startswith('종목'):
                        try:
                            from pykrx import stock as pykrx_stock
                            stock_name = pykrx_stock.get_market_ticker_name(symbol)
                            if stock_name:
                                self.logger.debug(f"✅ {symbol} pykrx에서 종목명 조회: {stock_name}")
                        except Exception as e:
                            self.logger.debug(f"⚠️ {symbol} pykrx 종목명 조회 실패: {e}")
                    
                    # 3. 여전히 없으면 필터링된 종목 리스트에서 찾기
                    if not stock_name or stock_name.startswith('종목'):
                        try:
                            # kis_collector의 캐시된 종목 리스트에서 찾기
                            if hasattr(kis_collector, '_cached_stock_names'):
                                stock_name = kis_collector._cached_stock_names.get(symbol)
                        except:
                            pass
                    
                    # 4. 최후의 수단: 기본 이름
                    if not stock_name:
                        stock_name = f"종목{symbol}"
                    
                    # stock_info에 종목명 업데이트
                    if isinstance(stock_info, dict):
                        stock_info['name'] = stock_name
                    
                    # StockData 생성
                    stock_data = kis_collector.create_stock_data(stock_info)
                    if not stock_data:
                        progress.advance(task)
                        continue
                    
                    # 종목명이 여전히 "종목코드" 형태면 수정
                    if stock_data.name.startswith('종목') and len(stock_data.name) == 9:
                        stock_data.name = stock_name
                    
                    # 분석 실행
                    analysis_result = await analysis_engine.analyze_comprehensive(
                        symbol=stock_data.symbol,
                        name=stock_data.name,  # 확실한 종목명 사용
                        stock_data=stock_data,
                        strategy=strategy
                    )
                    
                    if analysis_result:
                        # 결과에도 종목명 확실히 설정
                        analysis_result['name'] = stock_name
                        results.append(analysis_result)
                        self.logger.debug(f"✅ {symbol} ({stock_name}) 분석 완료")
                    
                    await asyncio.sleep(0.2)
                
                except Exception as e:
                    console.print(f"[yellow]⚠️ {symbol} 분석 실패: {e}[/yellow]")
                    self.logger.debug(f"⚠️ {symbol} 분석 실패: {e}")
                
                progress.advance(task)
        
        return results
    
    
    def _display_analysis_results(self, results: List[Dict], include_news=False):
        """종합 분석 결과 표시 - 종목명 개선"""
        if not results:
            console.print("[yellow]📊 분석 결과가 없습니다.[/yellow]")
            return
        
        # 결과 정렬
        sorted_results = sorted(results, key=lambda x: x.get('comprehensive_score', 0), reverse=True)
        
        # 결과 테이블 생성
        table = Table(title="📈 종합 분석 결과")
        table.add_column("순위", style="cyan", width=6)
        table.add_column("종목", style="bold", width=15)
        table.add_column("점수", style="green", width=8)
        table.add_column("추천", style="yellow", width=12)
        table.add_column("신호", style="blue", width=8)
        if include_news:
            table.add_column("뉴스재료", style="magenta", width=12)
        table.add_column("리스크", style="red", width=10)
        
        for i, result in enumerate(sorted_results[:15], 1):
            symbol = result.get('symbol', 'N/A')
            name = result.get('name', f'종목{symbol}')
            
            # 종목명이 여전히 "종목코드" 형태면 pykrx로 다시 시도
            if name.startswith('종목') and len(name) == 9:
                try:
                    from pykrx import stock as pykrx_stock
                    real_name = pykrx_stock.get_market_ticker_name(symbol)
                    if real_name and not real_name.startswith('종목'):
                        name = real_name
                except:
                    pass
            
            # 추천 등급 색상
            rec = result.get('recommendation', 'HOLD')
            if rec in ['STRONG_BUY', 'BUY']:
                rec_display = f"[bold green]{rec}[/bold green]"
            elif rec in ['STRONG_SELL', 'SELL']:
                rec_display = f"[bold red]{rec}[/bold red]"
            else:
                rec_display = f"[yellow]{rec}[/yellow]"
            
            # 리스크 레벨 색상
            risk = result.get('risk_level', 'MEDIUM')
            if risk == 'HIGH':
                risk_display = f"[bold red]{risk}[/bold red]"
            elif risk == 'LOW':
                risk_display = f"[bold green]{risk}[/bold green]"
            else:
                risk_display = f"[yellow]{risk}[/yellow]"
            
            # 종목명 길이 제한 (15자)
            display_name = name[:12] + "..." if len(name) > 12 else name
            
            row_data = [
                str(i),
                f"{symbol}\n{display_name}",  # 실제 종목명 표시
                f"{result.get('comprehensive_score', 0):.1f}",
                rec_display,
                f"{result.get('signal_strength', 0):.1f}",
            ]
            
            # 뉴스 정보 추가
            if include_news:
                news_info = result.get('sentiment_analysis', {})
                if news_info.get('has_material'):
                    material_type = news_info.get('material_type', '없음')
                    material_score = news_info.get('raw_material_score', 0)
                    news_display = f"{material_type}\n({material_score:.1f})"
                else:
                    news_display = "재료없음"
                row_data.append(news_display)
            
            row_data.append(risk_display)
            table.add_row(*row_data)
        
        console.print(table)
        
        # 통계 정보
        self._display_analysis_stats(results, include_news)
    
    def _display_news_results(self, results: List[Dict]):
        """뉴스 분석 결과 표시"""
        if not results:
            console.print("[yellow]📰 뉴스 재료가 발견된 종목이 없습니다.[/yellow]")
            return
        
        # 가중치 점수순 정렬
        sorted_results = sorted(results, 
                              key=lambda x: x['material_summary'].get('weighted_score', 0), 
                              reverse=True)
        
        # 결과 테이블 생성
        table = Table(title="📰 뉴스 재료 분석 결과")
        table.add_column("순위", style="cyan", width=6)
        table.add_column("종목", style="bold", width=15)
        table.add_column("재료타입", style="green", width=10)
        table.add_column("점수", style="yellow", width=8)
        table.add_column("뉴스수", style="blue", width=8)
        table.add_column("주요키워드", style="magenta", width=20)
        
        for i, result in enumerate(sorted_results[:20], 1):
            stock_info = result['stock_info']
            summary = result['material_summary']
            
            symbol = stock_info.get('symbol', '')
            name = stock_info.get('name', '')
            material_type = summary.get('primary_material', '재료없음')
            weighted_score = summary.get('weighted_score', 0)
            news_count = summary.get('news_count', 0)
            keywords = summary.get('material_keywords', [])[:3]
            
            # 재료 타입별 색상
            if material_type == '장기재료':
                material_display = f"[bold green]{material_type}[/bold green]"
            elif material_type == '중기재료':
                material_display = f"[bold yellow]{material_type}[/bold yellow]"
            elif material_type == '단기재료':
                material_display = f"[bold blue]{material_type}[/bold blue]"
            else:
                material_display = material_type
            
            table.add_row(
                str(i),
                f"{symbol}\n{name[:10]}",
                material_display,
                f"{weighted_score:.1f}",
                str(news_count),
                ", ".join(keywords[:2]) + ("..." if len(keywords) > 2 else "")
            )
        
        console.print(table)
        
        # 통계 정보
        self._display_news_stats(results)
    
    def _display_analysis_stats(self, results: List[Dict], include_news=False):
        """분석 통계 표시"""
        if not results:
            return
            
        avg_score = sum(r.get('comprehensive_score', 0) for r in results) / len(results)
        buy_signals = len([r for r in results if r.get('recommendation') in ['BUY', 'STRONG_BUY']])
        high_scores = len([r for r in results if r.get('comprehensive_score', 0) >= 80])
        
        stats_text = (
            f"[bold]📊 분석 통계[/bold]\n\n"
            f"전체 분석: {len(results)}개\n"
            f"평균 점수: {avg_score:.1f}\n"
            f"매수 신호: {buy_signals}개\n"
            f"고득점(80+): {high_scores}개"
        )
        
        if include_news:
            material_stocks = len([r for r in results if r.get('sentiment_analysis', {}).get('has_material')])
            stats_text += f"\n뉴스재료: {material_stocks}개"
        
        console.print(Panel(stats_text, title="분석 요약", border_style="green"))
    
    def _display_news_stats(self, results: List[Dict]):
        """뉴스 통계 표시"""
        # 재료 타입별 통계
        type_stats = {}
        for result in results:
            mat_type = result['material_summary'].get('primary_material')
            type_stats[mat_type] = type_stats.get(mat_type, 0) + 1
        
        stats_text = "\n".join([f"{mat_type}: {count}개" for mat_type, count in type_stats.items()])
        
        panel_text = (
            f"[bold]📊 뉴스 재료 통계[/bold]\n\n"
            f"재료 발견: {len(results)}개\n\n"
            f"[bold]재료 타입별 분포:[/bold]\n{stats_text}"
        )
        
        console.print(Panel(panel_text, title="뉴스 분석 요약", border_style="blue"))
    
    def _display_log_analysis(self, logs: List[Dict]):
        """로그 분석 결과 표시"""
        error_logs = [log for log in logs if log['level'] == 'ERROR']
        warning_logs = [log for log in logs if log['level'] == 'WARNING']
        total_logs = len(logs)
        
        # 로그 통계 테이블
        table = Table(title="📝 최근 24시간 로그 분석")
        table.add_column("레벨", style="bold")
        table.add_column("개수", style="cyan")
        table.add_column("비율", style="yellow")
        
        table.add_row("전체", str(total_logs), "100%")
        table.add_row("ERROR", str(len(error_logs)), f"{len(error_logs)/total_logs*100:.1f}%")
        table.add_row("WARNING", str(len(warning_logs)), f"{len(warning_logs)/total_logs*100:.1f}%")
        table.add_row("INFO", str(total_logs - len(error_logs) - len(warning_logs)), 
                     f"{(total_logs - len(error_logs) - len(warning_logs))/total_logs*100:.1f}%")
        
        console.print(table)
        
        # 최근 오류 로그 표시
        if error_logs:
            console.print("\n[bold red]❌ 최근 오류 로그 (최근 5개):[/bold red]")
            for log in error_logs[:5]:
                console.print(f"  {log['timestamp']} - {log['module']}: {log['message']}")
    
    # ======================== 명령행 모드 ========================
    
    async def run_command_line_mode(self):
        """명령행 모드 실행"""
        parser = argparse.ArgumentParser(
            description="AI Trading System with News Analysis",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
사용 예시:
  python main.py --mode test                     # 시스템 테스트
  python main.py --mode analysis               # 종합 분석 (뉴스 포함)
  python main.py --mode news                   # 뉴스 분석만
  python main.py --mode analysis --symbols 005930,000660  # 특정 종목 분석
            """
        )
        
        parser.add_argument(
            '--mode', 
            choices=['test', 'analysis', 'news', 'trading', 'backtest', 'db-status'],
            default='test',
            help='실행 모드'
        )
        
        parser.add_argument(
            '--strategy',
            choices=['momentum', 'breakout', 'mean_reversion', 'eod'],
            default='momentum',
            help='분석 전략'
        )
        
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='분석할 종목코드 (예: 005930 000660)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='분석할 종목 수'
        )
        
        parser.add_argument(
            '--auto',
            action='store_true',
            help='자동매매 활성화'
        )
        
        args = parser.parse_args()
        
        # 옵션 설정
        options = {
            'strategy': args.strategy,
            'symbols': args.symbols,
            'limit': args.limit,
            'auto_confirmed': args.auto
        }
        
        # 모드별 실행
        if args.mode == 'test':
            success = await self._system_test()
        elif args.mode == 'analysis':
            success = await self._run_cli_comprehensive_analysis(options)
        elif args.mode == 'news':
            success = await self._run_cli_news_analysis(options)
        elif args.mode == 'trading':
            success = await self._auto_trading() if args.auto else False
        elif args.mode == 'backtest':
            success = await self._backtest()
        elif args.mode == 'db-status':
            success = await self._db_status()
        else:
            console.print(f"[red]❌ 지원하지 않는 모드: {args.mode}[/red]")
            success = False
        
        return success
    
    async def _comprehensive_analysis(self) -> bool:
        """종합 분석 (뉴스 포함) - 간단한 버전"""
        console.print("[bold]🔍 종합 분석 (뉴스 분석 포함)[/bold]")
        
        # 옵션 수집
        options = self._get_analysis_options(include_news=True)
        if not options:
            return False
        
        try:
            from analyzers.analysis_engine import AnalysisEngine
            from data_collectors.kis_collector import KISCollector
            from database.database_manager import DatabaseManager
            
            # 시스템 초기화
            db_manager = DatabaseManager(self.config)
            analysis_engine = AnalysisEngine(self.config)
            
            # analyze_stock 메서드 추가 없이 바로 진행
            async with KISCollector(self.config) as kis_collector:
                await kis_collector.initialize()
                
                # KISCollector 메서드 확인 및 추가
                await ensure_collector_methods(kis_collector)
                
                # 종목 선택
                target_symbols = await self._get_target_symbols(kis_collector, options)
                if not target_symbols:
                    console.print("[red]❌ 분석할 종목이 없습니다.[/red]")
                    return False
                
                # 분석 실행
                results = await self._run_comprehensive_analysis(
                    analysis_engine, kis_collector, db_manager, target_symbols, options
                )
                
                # 결과 표시
                if results:
                    self._display_analysis_results(results, include_news=True)
                    await db_manager.close()
                    return True
                else:
                    await db_manager.close()
                    return False
        
        except Exception as e:
            console.print(f"[red]❌ 종합 분석 실패: {e}[/red]")
            return False

    async def _run_cli_comprehensive_analysis(self, options: Dict) -> bool:
        """CLI 종합 분석 - 간단한 버전"""
        console.print("[bold]🔍 종합 분석 시작 (CLI 모드)[/bold]")
        
        try:
            from analyzers.analysis_engine import AnalysisEngine
            from data_collectors.kis_collector import KISCollector
            from database.database_manager import DatabaseManager
            
            db_manager = DatabaseManager(self.config)
            analysis_engine = AnalysisEngine(self.config)
            
            # analyze_stock 메서드 추가 없이 바로 진행
            async with KISCollector(self.config) as kis_collector:
                await kis_collector.initialize()
                await ensure_collector_methods(kis_collector)
                
                target_symbols = await self._get_target_symbols(kis_collector, options)
                if not target_symbols:
                    console.print("[red]❌ 분석할 종목이 없습니다.[/red]")
                    return False
                
                results = await self._run_comprehensive_analysis(
                    analysis_engine, kis_collector, db_manager, target_symbols, options
                )
                
                if results:
                    self._display_analysis_results(results, include_news=True)
                    await db_manager.close()
                    return True
                else:
                    await db_manager.close()
                    return False
        
        except Exception as e:
            console.print(f"[red]❌ CLI 종합 분석 실패: {e}[/red]")
            return False

# ======================== 메인 실행 부분 ========================

async def main():
    """메인 함수"""
    system = TradingSystem()
    
    try:
        # 명령행 인수가 있으면 CLI 모드, 없으면 대화형 모드
        if len(sys.argv) > 1:
            success = await system.run_command_line_mode()
            sys.exit(0 if success else 1)
        else:
            await system.run_interactive_mode()
    
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 프로그램이 중단되었습니다.[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 치명적 오류: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 프로그램이 중단되었습니다.[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 치명적 오류: {e}[/red]")
        sys.exit(1)