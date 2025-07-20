#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/core/trading_system.py

AI Trading System 메인 클래스 - 간결한 버전
"""

import sys
import asyncio
import argparse
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List,Tuple, Optional, Any
from dataclasses import dataclass

# Rich 라이브러리
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.progress import Progress
except ImportError:
    print("❌ Rich 라이브러리 설치 필요: pip install rich")
    sys.exit(1)

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

console = Console()

def create_logger(name: str = "TradingSystem"):
    """로거 생성"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', '%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # 파일 로그 - 경로 수정
    try:
        Path("logs").mkdir(exist_ok=True)
        log_file = Path("logs") / f"{name.lower()}.log"  # 이 부분이 문제
        # 간단한 수정:
        log_file = f"logs/{name.lower()}.log"  # 문자열 결합으로 변경
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except:
        pass
    
    return logger

@dataclass
class StockData:
    """주식 데이터"""
    symbol: str
    name: str
    current_price: float
    change_rate: float
    volume: int
    trading_value: float
    market_cap: float
    shares_outstanding: int
    high_52w: float
    low_52w: float
    pe_ratio: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[float] = None
    bps: Optional[float] = None
    sector: Optional[str] = None

@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    symbol: str
    name: str
    score: float
    signals: Dict[str, Any]
    analysis_time: datetime
    strategy: str
    recommendation: str
    risk_level: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화 가능한 딕셔너리 변환"""
        def safe_serialize(obj):
            """JSON 직렬화 안전 처리"""
            if obj is None:
                return None
            elif isinstance(obj, (bool, int, float, str)):
                return obj
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: safe_serialize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [safe_serialize(item) for item in obj]
            else:
                return str(obj)
        
        return {
            'symbol': str(self.symbol),
            'name': str(self.name),
            'score': float(self.score),
            'signals': safe_serialize(self.signals),
            'analysis_time': self.analysis_time.isoformat() if isinstance(self.analysis_time, datetime) else str(self.analysis_time),
            'strategy': str(self.strategy),
            'recommendation': str(self.recommendation),
            'risk_level': str(self.risk_level),
            'entry_price': float(self.entry_price) if self.entry_price is not None else None,
            'stop_loss': float(self.stop_loss) if self.stop_loss is not None else None,
            'take_profit': float(self.take_profit) if self.take_profit is not None else None
        }

class SimpleNotifier:
    """간단한 알림"""
    
    def __init__(self, config=None):
        if config is None:
            from config import Config
            self.config = Config()  # 인스턴스 생성
        else:
            self.config = config
        #self.config = config
        self.logger = create_logger("SimpleNotifier")
    
    async def send_analysis_notification(self, results):
        """분석 결과 알림"""
        try:
            if not results:
                return
            
            buy_results = [r for r in results if 'BUY' in r.recommendation]
            self.logger.info(f"📢 분석 완료: {len(results)}개, 매수 신호: {len(buy_results)}개")
            
            if buy_results:
                console.print("\n[bold green]🚀 TOP 매수 추천:[/bold green]")
                for i, result in enumerate(buy_results[:3], 1):
                    console.print(f"{i}. {result.symbol} {result.name} - {result.score:.1f}점")
        except Exception as e:
            self.logger.error(f"❌ 알림 실패: {e}")
    
    async def send_error_message(self, error_msg: str):
        """에러 알림"""
        self.logger.error(f"🚨 {error_msg}")

class TradingSystem:
    """AI Trading System 메인 클래스"""
    
    def __init__(self, trading_enabled: bool = False, backtest_mode: bool = False):
        self.trading_enabled = trading_enabled
        self.backtest_mode = backtest_mode
        self.is_running = False
        self.last_analysis_time = None
        
        self.logger = create_logger("TradingSystem")
        
        # 컴포넌트들
        self.config = None
        self.data_collector = None
        self.news_collector = None
        self.analysis_engine = None
        self.strategies = {}
        self.executor = None
        self.position_manager = None
        self.risk_manager = None
        self.notifier = None
        self.db_manager = None
        self.menu_handlers = None
    
    async def initialize_components(self):
        """컴포넌트 초기화"""
        try:
            self.logger.info("🚀 컴포넌트 초기화 시작...")
            
            # 설정 로드
            try:
                from config import Config
                self.config = Config()
            except:
                self.config = type('Config', (), {})()
            
            # 데이터 수집기
            try:
                from data_collectors.kis_collector import SmartKISCollector
                self.data_collector = SmartKISCollector(self.config)
                await self.data_collector.initialize()
                self.logger.info("✅ 데이터 수집기 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 데이터 수집기 초기화 실패: {e}")
                raise
            
            # 분석 엔진
            try:
                from analyzers.analysis_engine import AnalysisEngine
                self.analysis_engine = AnalysisEngine(self.config)
                self.logger.info("✅ 분석 엔진 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 분석 엔진 초기화 실패: {e}")
                raise
            
            # 뉴스 수집기
            try:
                from data_collectors.news_collector import NewsCollector
                self.news_collector = NewsCollector(self.config)
                self.logger.info("✅ 뉴스 수집기 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 뉴스 수집기 초기화 실패: {e}")
                self.news_collector = None
            
            # 전략
            try:
                from strategies.momentum_strategy import MomentumStrategy
                self.strategies['momentum'] = MomentumStrategy(self.config)
                self.logger.info("✅ 전략 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 전략 초기화 실패: {e}")
                self.strategies = {}
                
                
            try:
                from strategies.supertrend_ema_rsi_strategy import SupertrendEmaRsiStrategy
                self.strategies['supertrend_ema_rsi'] = SupertrendEmaRsiStrategy(self.config)
                self.logger.info("✅ Supertrend EMA RSI 전략 등록 완료")
            except Exception:
                self.logger.debug("Supertrend EMA RSI 전략 로드 실패 (파일이 없을 수 있음)")
            
            # 알림 서비스
            self.notifier = SimpleNotifier(self.config)
            
            # 데이터베이스
            try:
                from database.database_manager import DatabaseManager
                self.db_manager = DatabaseManager(self.config)
                self.logger.info("✅ 데이터베이스 초기화 완료")
            except:
                self.db_manager = None
            
            # 메뉴 핸들러
            try:
                from core.menu_handlers import MenuHandlers
                self.menu_handlers = MenuHandlers(self)
            except:
                self.menu_handlers = None
            
            self.logger.info("✅ 모든 컴포넌트 초기화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 컴포넌트 초기화 실패: {e}")
            return False
    async def display_results(self, results, *args, **kwargs):
        """결과 표시 - 유연한 호환성 메서드 (다양한 호출 방식 지원)"""
        # 추가 인수들은 무시하고 결과만 표시
        await self._display_analysis_results(results)
    async def run_market_analysis(self, strategy: str = 'momentum', limit: int = None) -> List[AnalysisResult]:
        """시장 분석"""
        self.last_analysis_time = datetime.now()
        self.logger.info(f"📊 시장 분석 시작 (전략: {strategy})")
        
        if not await self._check_components():
            return []
        
        try:
            with Progress() as progress:
                task = progress.add_task("[green]시장 분석 중...", total=100)
                
                # 종목 필터링
                progress.update(task, advance=20, description="종목 필터링 중...")
                candidates = await self.data_collector.get_filtered_stocks(limit=limit)
                
                if not candidates:
                    console.print("[red]❌ 종목 필터링 실패[/red]")
                    return []
                
                self.logger.info(f"필터링 결과: {len(candidates)}개 종목")
                
                # 분석 실행
                progress.update(task, advance=20, description="종목 분석 중...")
                results = []
                
                for i, (symbol, name) in enumerate(candidates):
                    try:
                        result = await self.analyze_symbol(symbol, name, strategy)
                        if result:
                            min_score = getattr(self.config, 'MIN_COMPREHENSIVE_SCORE', 60)
                            if hasattr(min_score, 'analysis'):
                                min_score = getattr(min_score.analysis, 'MIN_COMPREHENSIVE_SCORE', 60)
                            
                            if result.score >= min_score:
                                results.append(result)
                        
                        progress.update(task, advance=50/len(candidates))
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ {symbol} 분석 실패: {e}")
                        continue
                
                # 결과 정렬 및 저장
                progress.update(task, advance=10, description="결과 정리 중...")
                results.sort(key=lambda x: x.score, reverse=True)
                
                await self._save_analysis_results(results)
                if results:
                    await self._send_analysis_notification(results[:10])
                
                progress.update(task, advance=0, description="완료!")
            
            console.print(f"[green]✅ 시장 분석 완료: {len(results)}개 신호[/green]")
            return results
            
        except Exception as e:
            console.print(f"[red]❌ 시장 분석 실패: {e}[/red]")
            return []
    
    async def get_filtered_stocks(self, limit: int = 50, use_cache: bool = True) -> List[Tuple[str, str]]:
        """필터링된 종목 리스트 반환 - 종목명 보정 포함"""
        try:
            if not isinstance(limit, int) or limit <= 0:
                limit = 50
            
            self.logger.info(f"🔍 필터링된 종목 조회 시작 (목표: {limit}개)")
            
            # 기존 로직으로 종목 수집
            result = await self._get_filtered_stocks_with_names(limit, use_cache)
            
            # 종목명 후처리 - 숫자나 이상한 이름들 수정
            corrected_result = []
            for symbol, name in result:
                corrected_name = await self._correct_stock_name(symbol, name)
                corrected_result.append((symbol, corrected_name))
            
            self.logger.info(f"✅ 종목명 보정 완료: {len(corrected_result)}개")
            return corrected_result
            
        except Exception as e:
            self.logger.error(f"❌ get_filtered_stocks 실패: {e}")
            return []
    
    async def save_results_to_file(self, results: List[AnalysisResult], filename: str = None):
        """분석 결과를 파일로 저장 - JSON 안전 버전"""
        try:
            if not results:
                console.print("[yellow]저장할 결과가 없습니다.[/yellow]")
                return False
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"analysis_results_{timestamp}.json"
            
            # 안전한 JSON 변환
            safe_data = {
                'timestamp': datetime.now().isoformat(),
                'total_count': len(results),
                'results': []
            }
            
            for result in results:
                try:
                    # 개별 결과 안전 변환
                    safe_result = {
                        'symbol': str(result.symbol),
                        'name': str(result.name),
                        'score': float(result.score),
                        'recommendation': str(result.recommendation),
                        'risk_level': str(result.risk_level),
                        'strategy': str(result.strategy),
                        'analysis_time': result.analysis_time.isoformat() if isinstance(result.analysis_time, datetime) else str(result.analysis_time)
                    }
                    
                    # signals 필드 안전 처리
                    if hasattr(result, 'signals') and result.signals:
                        safe_signals = {}
                        for k, v in result.signals.items():
                            if isinstance(v, (str, int, float, bool)) or v is None:
                                safe_signals[k] = v
                            else:
                                safe_signals[k] = str(v)
                        safe_result['signals'] = safe_signals
                    
                    # 가격 정보 안전 처리
                    if result.entry_price is not None:
                        safe_result['entry_price'] = float(result.entry_price)
                    if result.stop_loss is not None:
                        safe_result['stop_loss'] = float(result.stop_loss)
                    if result.take_profit is not None:
                        safe_result['take_profit'] = float(result.take_profit)
                    
                    safe_data['results'].append(safe_result)
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️ {result.symbol} 변환 실패: {e}[/yellow]")
                    # 최소한의 정보라도 저장
                    safe_data['results'].append({
                        'symbol': str(getattr(result, 'symbol', 'Unknown')),
                        'name': str(getattr(result, 'name', 'Unknown')),
                        'score': float(getattr(result, 'score', 0)),
                        'error': 'Conversion failed'
                    })
            
            # 파일 저장
            filepath = Path("results") / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(safe_data, f, ensure_ascii=False, indent=2)
            
            console.print(f"[green]✅ 파일 저장 완료: {filepath}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 파일 저장 실패: {e}[/red]")
            return False
    
    async def _get_filtered_stocks_with_names(self, limit: int, use_cache: bool) -> List[Tuple[str, str]]:
        """종목명과 함께 필터링된 종목 조회"""
        # 캐시 확인
        if use_cache:
            cached_result = await self._get_cached_filtered_stocks(limit)
            if cached_result:
                self.logger.info(f"✅ 캐시 사용: {len(cached_result)}개")
                return cached_result
        
        # 새로 필터링
        try:
            filtered_data = await self.collect_filtered_stocks(max_stocks=limit)
            if filtered_data:
                result = [(stock['symbol'], stock['name']) for stock in filtered_data]
                await self._save_filtered_stocks_cache(result)
                return result
        except Exception as e:
            self.logger.warning(f"⚠️ collect_filtered_stocks 실패: {e}")
        
        # 직접 필터링
        try:
            result = await self._direct_filtering(limit)
            if result:
                await self._save_filtered_stocks_cache(result)
                return result
        except Exception as e:
            self.logger.warning(f"⚠️ 직접 필터링 실패: {e}")
        
        # Fallback
        return await self._get_major_stocks_as_fallback(limit)
    
    
    async def _correct_stock_name(self, symbol: str, original_name: str) -> str:
        """종목명 보정"""
        try:
            # 문제가 있는 종목명인지 확인
            if (not original_name or 
                original_name.isdigit() or 
                original_name.startswith('종목') or 
                len(original_name) <= 2 or
                original_name in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']):
                
                # 1. pykrx에서 조회 시도
                try:
                    from pykrx import stock as pykrx_stock
                    pykrx_name = pykrx_stock.get_market_ticker_name(symbol)
                    if pykrx_name and pykrx_name.strip() and len(pykrx_name.strip()) > 2:
                        clean_name = self._clean_stock_name(pykrx_name.strip())
                        self.logger.debug(f"✅ {symbol} 종목명 보정: '{original_name}' → '{clean_name}'")
                        return clean_name
                except Exception as e:
                    self.logger.debug(f"⚠️ {symbol} pykrx 조회 실패: {e}")
                
                # 2. 다시 KIS API에서 조회 시도
                try:
                    stock_info = await self.get_stock_info(symbol)
                    if stock_info and stock_info.get('name'):
                        api_name = stock_info['name']
                        if (api_name and 
                            not api_name.isdigit() and 
                            not api_name.startswith('종목') and 
                            len(api_name) > 2):
                            clean_name = self._clean_stock_name(api_name)
                            self.logger.debug(f"✅ {symbol} 종목명 보정: '{original_name}' → '{clean_name}'")
                            return clean_name
                except Exception as e:
                    self.logger.debug(f"⚠️ {symbol} KIS API 재조회 실패: {e}")
                
                # 3. 최후의 수단
                return f'종목{symbol}'
            
            # 원래 이름이 정상이면 그대로 사용
            return self._clean_stock_name(original_name)
            
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} 종목명 보정 실패: {e}")
            return f'종목{symbol}'
    async def analyze_symbol(self, symbol: str, name: str, strategy: str) -> Optional[AnalysisResult]:
        """개별 종목 분석 - 종목명 fallback 강화"""
        try:
            # 기본 데이터 수집
            stock_data = await self.data_collector.get_stock_info(symbol)
            if not stock_data:
                return None
            
            # 종목명 확보 (다중 fallback)
            final_name = name
            
            # 1. 전달받은 name이 문제가 있으면 stock_data에서 가져오기
            if (not final_name or 
                final_name.isdigit() or 
                final_name.startswith('종목') or 
                len(final_name) <= 2):
                final_name = stock_data.get('name', '')
            
            # 2. stock_data의 name도 문제가 있으면 pykrx 시도
            if (not final_name or 
                final_name.isdigit() or 
                final_name.startswith('종목') or 
                len(final_name) <= 2):
                try:
                    from pykrx import stock as pykrx_stock
                    pykrx_name = pykrx_stock.get_market_ticker_name(symbol)
                    if pykrx_name and pykrx_name.strip():
                        final_name = pykrx_name.strip()
                except Exception as e:
                    self.logger.debug(f"⚠️ {symbol} pykrx 종목명 조회 실패: {e}")
            
            # 3. 최종적으로 문제가 있으면 기본 이름
            if (not final_name or 
                final_name.isdigit() or 
                len(final_name) <= 2):
                final_name = f'종목{symbol}'
            
            # 나머지 분석 로직은 동일...
            # (뉴스 분석, 종합 분석, 신호 생성 등)
            
            # 뉴스 분석
            news_data = None
            if self.news_collector:
                try:
                    news_input = {'name': final_name, 'symbol': symbol}
                    news_data = self.news_collector.analyze_stock_materials(news_input)
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 뉴스 분석 실패: {e}")
            
            # 종합 분석
            analysis_result = await self.analysis_engine.analyze_comprehensive(
                symbol=symbol,
                name=final_name,  # 확정된 종목명 사용
                stock_data=stock_data,
                news_data=news_data,
                strategy=strategy
            )
            
            if not analysis_result:
                return None
            
            # 신호 생성
            signals = {'action': 'HOLD', 'strength': 0.5}
            strategy_obj = self.strategies.get(strategy)
            if strategy_obj:
                try:
                    signals = await strategy_obj.generate_signals(stock_data, analysis_result)
                except:
                    pass
            
            # 리스크 평가
            risk_level = self._evaluate_risk(stock_data, analysis_result)
            
            # 추천 등급
            recommendation = self._get_recommendation(analysis_result, signals)
            
            # 가격 계산
            current_price = self._safe_get(stock_data, 'current_price', 0)
            entry_price = current_price
            stop_loss = current_price * 0.95
            take_profit = current_price * 1.10
            
            return AnalysisResult(
                symbol=symbol,
                name=final_name,  # 확정된 종목명 사용
                score=analysis_result.get('comprehensive_score', 0),
                signals=signals,
                analysis_time=datetime.now(),
                strategy=strategy,
                recommendation=recommendation,
                risk_level=risk_level,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 분석 실패: {e}")
            return None
    
    async def analyze_symbols(self, symbols: List[str], strategy: str = 'momentum') -> List[AnalysisResult]:
        """특정 종목들 분석"""
        console.print(f"[yellow]🎯 특정 종목 분석: {len(symbols)}개[/yellow]")
        
        if not await self._check_components():
            return []
        
        results = []
        with Progress() as progress:
            task = progress.add_task("[green]종목 분석 중...", total=len(symbols))
            
            for symbol in symbols:
                try:
                    stock_info = await self.data_collector.get_stock_info(symbol)
                    name = stock_info.get('name', symbol) if stock_info else symbol
                    
                    result = await self.analyze_symbol(symbol, name, strategy)
                    if result:
                        results.append(result)
                    
                    progress.update(task, advance=1)
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 분석 실패: {e}")
                    progress.update(task, advance=1)
        
        results.sort(key=lambda x: x.score, reverse=True)
        console.print(f"[green]✅ 분석 완료: {len(results)}개 결과[/green]")
        return results
    
    def _safe_get(self, data, key, default=None):
        """안전한 데이터 접근"""
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)
    
    def _evaluate_risk(self, stock_data, analysis_result: Dict) -> str:
        """리스크 평가"""
        try:
            change_rate = abs(self._safe_get(stock_data, 'change_rate', 0))
            volume = self._safe_get(stock_data, 'volume', 0)
            market_cap = self._safe_get(stock_data, 'market_cap', 0)
            
            risk_score = 0
            if change_rate > 10:
                risk_score += 2
            elif change_rate > 5:
                risk_score += 1
            
            if volume < 100000:
                risk_score += 1
            if market_cap < 500:
                risk_score += 1
            
            if risk_score >= 3:
                return "HIGH"
            elif risk_score >= 1:
                return "MEDIUM"
            return "LOW"
        except:
            return "MEDIUM"
    
    def _get_recommendation(self, analysis_result: Dict, signals: Dict) -> str:
        """추천 등급"""
        try:
            score = analysis_result.get('comprehensive_score', 0)
            if score >= 80:
                return 'STRONG_BUY'
            elif score >= 70:
                return 'BUY'
            elif score >= 60:
                return 'WEAK_BUY'
            elif score <= 30:
                return 'STRONG_SELL'
            elif score <= 40:
                return 'SELL'
            return 'HOLD'
        except:
            return 'HOLD'
    
    async def _check_components(self) -> bool:
        """컴포넌트 상태 확인"""
        if not self.data_collector or not self.analysis_engine:
            console.print("[yellow]⚠️ 컴포넌트 초기화 중...[/yellow]")
            return await self.initialize_components()
        
        # 세션 상태 확인
        if hasattr(self.data_collector, 'session'):
            if not self.data_collector.session or self.data_collector.session.closed:
                try:
                    await self.data_collector.close()
                    await self.data_collector.initialize()
                except Exception as e:
                    self.logger.error(f"❌ 데이터 수집기 재초기화 실패: {e}")
                    return False
        
        return True
    
    async def _save_analysis_results(self, results: List[AnalysisResult]):
        """분석 결과 저장 - JSON 직렬화 안전 버전"""
        try:
            if not results:
                self.logger.info("💾 저장할 분석 결과가 없습니다")
                return
            
            self.logger.info(f"💾 분석 결과 저장 중... ({len(results)}개 결과)")
            
            if self.db_manager:
                try:
                    await self.db_manager.save_analysis_results(results)
                    self.logger.info("✅ DB 저장 완료")
                except Exception as e:
                    self.logger.warning(f"⚠️ DB 저장 실패: {e}")
            
            # 로컬 파일 저장 (JSON 직렬화 안전 처리)
            try:
                results_dir = Path("data/analysis_results")
                results_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = results_dir / f"analysis_{timestamp}.json"
                
                # JSON 직렬화 안전 처리
                def safe_json_serialize(obj):
                    """JSON 직렬화 안전 함수"""
                    if obj is None:
                        return None
                    elif isinstance(obj, (bool, int, float, str)):
                        return obj
                    elif isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, dict):
                        return {k: safe_json_serialize(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [safe_json_serialize(item) for item in obj]
                    elif hasattr(obj, 'to_dict'):
                        return safe_json_serialize(obj.to_dict())
                    else:
                        return str(obj)
                
                # 결과 데이터 안전 변환
                safe_results = []
                for result in results:
                    try:
                        if hasattr(result, 'to_dict'):
                            safe_result = safe_json_serialize(result.to_dict())
                        else:
                            safe_result = safe_json_serialize(result)
                        safe_results.append(safe_result)
                    except Exception as e:
                        self.logger.warning(f"⚠️ 결과 변환 실패: {e}")
                        # 기본 정보만 저장
                        safe_results.append({
                            'symbol': str(getattr(result, 'symbol', 'Unknown')),
                            'name': str(getattr(result, 'name', 'Unknown')),
                            'score': float(getattr(result, 'score', 0)),
                            'recommendation': str(getattr(result, 'recommendation', 'HOLD')),
                            'risk_level': str(getattr(result, 'risk_level', 'MEDIUM')),
                            'error': 'Conversion failed'
                        })
                
                # 파일 저장
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'total_count': len(safe_results),
                        'results': safe_results
                    }, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"✅ 로컬 파일 저장 완료: {filename}")
                
            except Exception as e:
                self.logger.warning(f"⚠️ 로컬 파일 저장 실패: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ 분석 결과 저장 실패: {e}")
    
    async def _send_analysis_notification(self, results: List[AnalysisResult]):
        """분석 결과 알림"""
        try:
            if self.notifier:
                await self.notifier.send_analysis_notification(results)
        except Exception as e:
            self.logger.error(f"❌ 알림 실패: {e}")
    
    def print_banner(self):
        """시스템 배너"""
        banner = f"""[bold cyan]🚀 AI Trading System v3.0[/bold cyan]

📊 5개 영역 통합 분석: 기술적 + 펀더멘털 + 뉴스 + 수급 + 패턴

매매 모드: {'🔴 활성화' if self.trading_enabled else '🟡 비활성화'}
백테스트: {'🔴 활성화' if self.backtest_mode else '🟡 비활성화'}"""
        
        console.print(Panel.fit(banner, title="AI Trading System", border_style="cyan"))
    
    def show_main_menu(self):
        """메인 메뉴"""
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
    
    async def run_interactive_mode(self):
        """대화형 모드"""
        self.print_banner()
        console.print(f"[dim]시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")
        
        while True:
            try:
                self.show_main_menu()
                choice = self.get_user_choice()
                
                if choice == "0":
                    console.print("\n[bold]👋 종료합니다[/bold]")
                    break
                
                success = await self._execute_menu_choice(choice)
                
                if success:
                    console.print(Panel("[green]✅ 완료[/green]", border_style="green"))
                elif success is False:
                    console.print(Panel("[red]❌ 실패[/red]", border_style="red"))
                
                if choice != "0":
                    Prompt.ask("\n[dim]계속하려면 Enter[/dim]", default="")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]🛑 중단[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]❌ 오류: {e}[/red]")
    
    async def _execute_menu_choice(self, choice: str) -> Optional[bool]:
        """메뉴 실행"""
        # menu_handlers가 없으면 강제 초기화 시도
        if not self.menu_handlers:
            try:
                from core.menu_handlers import MenuHandlers
                self.menu_handlers = MenuHandlers(self)
                self.logger.info("✅ 메뉴 핸들러 지연 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 메뉴 핸들러 초기화 실패: {e}")
        
        # menu_handlers 사용
        if self.menu_handlers:
            return await self.menu_handlers.execute_menu_choice(choice)
        
        # 기존 기본 메뉴 (변경 없음)
        if choice == "1":
            return await self._run_system_test()
        elif choice == "4":
            results = await self.run_market_analysis()
            await self._display_analysis_results(results)
            return len(results) > 0
        elif choice == "5":
            symbols = Prompt.ask("종목 코드 (쉼표 구분)", default="005930")
            symbol_list = [s.strip() for s in symbols.split(',')]
            results = await self.analyze_symbols(symbol_list)
            await self._display_analysis_results(results)
            return len(results) > 0
        else:
            console.print("[yellow]⚠️ 미구현 메뉴[/yellow]")
            return None
    
    async def _run_system_test(self) -> bool:
        """시스템 테스트"""
        console.print("[yellow]🔧 시스템 테스트 중...[/yellow]")
        
        try:
            if not await self.initialize_components():
                return False
            
            # 데이터 수집 테스트
            stock_data = await self.data_collector.get_stock_info("005930")
            if not stock_data:
                console.print("[red]❌ 데이터 수집 실패[/red]")
                return False
            
            # 분석 테스트
            result = await self.analyze_symbol("005930", "삼성전자", "momentum")
            if not result:
                console.print("[red]❌ 분석 실패[/red]")
                return False
            
            console.print("[green]✅ 모든 테스트 통과[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 테스트 실패: {e}[/red]")
            return False
    
    async def _display_analysis_results(self, results: List[AnalysisResult]):
        """분석 결과 표시 - 종목명 fallback 포함 + 손절가/익절가 추가"""
        if not results:
            console.print("[yellow]📊 분석 결과 없음[/yellow]")
            return
        
        # 결과 테이블 - 손절가/익절가 컬럼 추가
        table = Table(title=f"📊 분석 결과 (상위 {min(len(results), 20)}개)")
        table.add_column("순위", style="cyan", width=4)
        table.add_column("종목코드", style="magenta", width=8)
        table.add_column("종목명", style="white", width=12)
        table.add_column("점수", style="green", width=6)
        table.add_column("추천", style="yellow", width=8)
        table.add_column("현재가", style="blue", width=8)
        table.add_column("손절가", style="red", width=8)
        table.add_column("익절가", style="bright_green", width=8)
        table.add_column("리스크", style="orange3", width=6)
        
        for i, result in enumerate(results[:20]):
            # 종목명 fallback 처리 (기존 로직 유지)
            name = result.name
            
            # 1. 종목명이 숫자이거나 비어있으면 재조회
            if (not name or 
                name.isdigit() or 
                name.startswith('종목') or 
                len(name) <= 2):
                
                try:
                    # 데이터 컬렉터에서 재조회
                    if hasattr(self, 'data_collector') and self.data_collector:
                        stock_info = await self.data_collector.get_stock_info(result.symbol)
                        if stock_info and stock_info.get('name'):
                            name = stock_info['name']
                except Exception as e:
                    self.logger.debug(f"⚠️ {result.symbol} 종목명 재조회 실패: {e}")
            
            # 2. 여전히 문제가 있으면 pykrx 시도
            if (not name or 
                name.isdigit() or 
                name.startswith('종목') or 
                len(name) <= 2):
                
                try:
                    from pykrx import stock as pykrx_stock
                    pykrx_name = pykrx_stock.get_market_ticker_name(result.symbol)
                    if pykrx_name and pykrx_name.strip():
                        name = pykrx_name.strip()
                except Exception as e:
                    self.logger.debug(f"⚠️ {result.symbol} pykrx 조회 실패: {e}")
            
            # 3. 최후의 수단
            if (not name or 
                name.isdigit() or 
                name.startswith('종목') or 
                len(name) <= 2):
                name = f'종목{result.symbol}'
            
            # 종목명 길이 제한 (테이블 레이아웃을 위해)
            if len(name) > 10:
                display_name = name[:9] + "…"
            else:
                display_name = name
            
            # 가격 정보 포맷팅
            entry_price = "N/A"
            stop_loss = "N/A"
            take_profit = "N/A"
            
            # 현재가 (진입가)
            if hasattr(result, 'entry_price') and result.entry_price:
                entry_price = f"{result.entry_price:,.0f}"
            elif hasattr(result, 'current_price') and result.current_price:
                entry_price = f"{result.current_price:,.0f}"
            
            # 손절가
            if hasattr(result, 'stop_loss') and result.stop_loss:
                stop_loss = f"{result.stop_loss:,.0f}"
            elif hasattr(result, 'entry_price') and result.entry_price:
                # 기본 손절가 계산 (진입가의 5% 하락)
                calculated_stop = result.entry_price * 0.95
                stop_loss = f"{calculated_stop:,.0f}"
            
            # 익절가
            if hasattr(result, 'take_profit') and result.take_profit:
                take_profit = f"{result.take_profit:,.0f}"
            elif hasattr(result, 'entry_price') and result.entry_price:
                # 기본 익절가 계산 (진입가의 10% 상승)
                calculated_profit = result.entry_price * 1.10
                take_profit = f"{calculated_profit:,.0f}"
            
            # 추천 텍스트 길이 제한
            recommendation = result.recommendation
            if len(recommendation) > 6:
                rec_display = recommendation[:5] + "…"
            else:
                rec_display = recommendation
            
            # 리스크 레벨 길이 제한
            risk_level = result.risk_level
            if len(risk_level) > 5:
                risk_display = risk_level[:4] + "…"
            else:
                risk_display = risk_level
            
            table.add_row(
                str(i + 1),
                result.symbol,
                display_name,
                f"{result.score:.1f}",
                rec_display,
                entry_price,
                stop_loss,
                take_profit,
                risk_display
            )
        
        console.print(table)
        
        # 개선된 요약 통계 표시
        await self._display_result_summary(results)

    async def _display_result_summary(self, results: List[AnalysisResult]):
        """분석 결과 요약 통계"""
        if not results:
            return
        
        total_count = len(results)
        avg_score = sum(r.score for r in results) / total_count
        
        # 추천 분포
        buy_count = len([r for r in results if 'BUY' in r.recommendation.upper()])
        hold_count = len([r for r in results if 'HOLD' in r.recommendation.upper()])
        sell_count = len([r for r in results if 'SELL' in r.recommendation.upper()])
        
        # 점수 분포
        high_score = len([r for r in results if r.score >= 80])
        med_score = len([r for r in results if 60 <= r.score < 80])
        low_score = len([r for r in results if r.score < 60])
        
        # 리스크 분포
        low_risk = len([r for r in results if 'LOW' in r.risk_level.upper()])
        med_risk = len([r for r in results if 'MED' in r.risk_level.upper()])
        high_risk = len([r for r in results if 'HIGH' in r.risk_level.upper()])
        
        # 손절가/익절가 통계
        valid_prices = []
        profit_ratios = []
        loss_ratios = []
        
        for r in results:
            if (hasattr(r, 'entry_price') and r.entry_price and
                hasattr(r, 'stop_loss') and r.stop_loss and
                hasattr(r, 'take_profit') and r.take_profit):
                
                valid_prices.append(r)
                
                # 손익률 계산
                loss_ratio = (r.entry_price - r.stop_loss) / r.entry_price * 100
                profit_ratio = (r.take_profit - r.entry_price) / r.entry_price * 100
                
                loss_ratios.append(loss_ratio)
                profit_ratios.append(profit_ratio)
        
        avg_loss_ratio = sum(loss_ratios) / len(loss_ratios) if loss_ratios else 0
        avg_profit_ratio = sum(profit_ratios) / len(profit_ratios) if profit_ratios else 0
        
        summary_content = f"""[bold cyan]📊 분석 결과 요약[/bold cyan]

    [green]기본 통계[/green]
    • 총 분석 종목: {total_count}개
    • 평균 점수: {avg_score:.1f}점
    • 가격 정보 보유: {len(valid_prices)}개

    [yellow]추천 분포[/yellow]
    • 🚀 매수 추천: {buy_count}개 ({buy_count/total_count*100:.1f}%)
    • 📊 보유 추천: {hold_count}개 ({hold_count/total_count*100:.1f}%)
    • 📉 매도 추천: {sell_count}개 ({sell_count/total_count*100:.1f}%)

    [blue]점수 분포[/blue]
    • 🔥 고득점(80+): {high_score}개
    • 📈 중간점수(60-79): {med_score}개
    • 📊 저득점(<60): {low_score}개

    [red]리스크 분포[/red]
    • 🟢 저위험: {low_risk}개
    • 🟡 중위험: {med_risk}개
    • 🔴 고위험: {high_risk}개"""

        if profit_ratios and loss_ratios:
            summary_content += f"""

    [magenta]손익률 통계[/magenta]
    • 평균 예상 수익률: +{avg_profit_ratio:.1f}%
    • 평균 예상 손실률: -{avg_loss_ratio:.1f}%
    • 위험-수익 비율: 1:{avg_profit_ratio/avg_loss_ratio:.1f}"""

        summary_content += f"""

    [bold blue]💡 투자 가이드[/bold blue]
    1. 🎯 80점 이상 고득점 종목 우선 검토
    2. 📊 손절가/익절가 준수로 리스크 관리
    3. 🚀 매수 추천 종목 중 저위험부터 검토
    4. 💰 분산투자로 포트폴리오 위험 분산"""

        console.print(Panel(
            summary_content,
            title="📈 투자 분석 요약",
            border_style="cyan",
            width=70
        ))
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태"""
        return {
            'timestamp': datetime.now().isoformat(),
            'trading_enabled': self.trading_enabled,
            'backtest_mode': self.backtest_mode,
            'is_running': self.is_running,
            'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'components': {
                'data_collector': self.data_collector is not None,
                'analysis_engine': self.analysis_engine is not None,
                'news_collector': self.news_collector is not None,
                'strategies': len(self.strategies),
                'notifier': self.notifier is not None,
                'db_manager': self.db_manager is not None
            }
        }
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            console.print("[yellow]🧹 정리 중...[/yellow]")
            self.is_running = False
            
            if self.data_collector:
                await self.data_collector.close()
            
            console.print("[green]✅ 정리 완료[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ 정리 중 오류: {e}[/yellow]")
    
    async def stop(self):
        """시스템 정지"""
        console.print("[yellow]🛑 정지 중...[/yellow]")
        await self.cleanup()
        console.print("[bold]✅ 정지 완료[/bold]")