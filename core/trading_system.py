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

# Database models import
try:
    from database.models import OrderType
except ImportError:
    # Fallback enum if models not available
    from enum import Enum
    class OrderType(Enum):
        MARKET = "MARKET"
        LIMIT = "LIMIT"

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
    """분석 결과 데이터 클래스 (DB 모델과 일치)"""
    filtered_stock_id: int
    stock_id: int
    symbol: str
    name: str
    analysis_datetime: datetime
    strategy: str
    total_score: float
    final_grade: str # BUY, SELL, HOLD 등
    news_score: float
    chart_score: float
    supply_demand_score: float
    signal_strength: Optional[float] = None
    signal_type: Optional[str] = None
    action: Optional[str] = None
    volatility: Optional[float] = None
    liquidity_risk: Optional[float] = None
    market_risk: Optional[float] = None
    risk_level: Optional[str] = None
    technical_details: Optional[Dict] = None
    fundamental_details: Optional[Dict] = None
    sentiment_details: Optional[Dict] = None
    price_at_analysis: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화 가능한 딕셔너리 변환"""
        def safe_serialize(obj):
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
            'filtered_stock_id': self.filtered_stock_id,
            'stock_id': self.stock_id,
            'symbol': self.symbol,
            'name': self.name,
            'analysis_datetime': self.analysis_datetime.isoformat(),
            'strategy': self.strategy,
            'total_score': self.total_score,
            'final_grade': self.final_grade,
            'news_score': self.news_score,
            'chart_score': self.chart_score,
            'supply_demand_score': self.supply_demand_score,
            'signal_strength': safe_serialize(self.signal_strength),
            'signal_type': safe_serialize(self.signal_type),
            'action': safe_serialize(self.action),
            'volatility': safe_serialize(self.volatility),
            'liquidity_risk': safe_serialize(self.liquidity_risk),
            'market_risk': safe_serialize(self.market_risk),
            'risk_level': safe_serialize(self.risk_level),
            'technical_details': safe_serialize(self.technical_details),
            'fundamental_details': safe_serialize(self.fundamental_details),
            'sentiment_details': safe_serialize(self.sentiment_details),
            'price_at_analysis': safe_serialize(self.price_at_analysis),
            'entry_price': safe_serialize(self.entry_price),
            'stop_loss': safe_serialize(self.stop_loss),
            'take_profit': safe_serialize(self.take_profit)
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
        
        # 데이터베이스 연결이 안정적이므로 메모리 캐시 불필요
    
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
            from data_collectors.kis_collector import KISCollector
            self.data_collector = KISCollector(self.config)
            await self.data_collector.initialize()
            self.logger.info("✅ 데이터 수집기 초기화 완료")
            
            # 분석 엔진
            try:
                from analyzers.analysis_engine import AnalysisEngine
                self.analysis_engine = AnalysisEngine(self.config, self.data_collector)
                self.logger.info("✅ 분석 엔진 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 분석 엔진 초기화 실패: {e}")
                print(f"FATAL_ERROR_ANALYSIS_ENGINE: {e}")
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
                self.logger.info("✅ Momentum 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ Momentum 전략 초기화 실패: {e}")

            try:
                from strategies.breakout_strategy import BreakoutStrategy
                self.strategies['breakout'] = BreakoutStrategy(self.config)
                self.logger.info("✅ Breakout 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ Breakout 전략 초기화 실패: {e}")

            try:
                from strategies.eod_strategy import EodStrategy
                self.strategies['eod'] = EodStrategy(self.config)
                self.logger.info("✅ EOD 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ EOD 전략 초기화 실패: {e}")

            try:
                from strategies.supertrend_ema_rsi_strategy import SupertrendEmaRsiStrategy
                self.strategies['supertrend_ema_rsi'] = SupertrendEmaRsiStrategy(self.config)
                self.logger.info("✅ Supertrend EMA RSI 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ Supertrend EMA RSI 전략 로드 실패: {e}")

            try:
                from strategies.vwap_strategy import VwapStrategy
                self.strategies['vwap'] = VwapStrategy(self.config)
                self.logger.info("✅ VWAP 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ VWAP 전략 로드 실패: {e}")
            
            # 3분봉 스캘핑 전략
            try:
                from strategies.scalping_3m_strategy import Scalping3mStrategy
                self.strategies['scalping_3m'] = Scalping3mStrategy(self.config)
                self.logger.info("✅ 3분봉 스캘핑 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 3분봉 스캘핑 전략 로드 실패: {e}")
            
            # RSI 전략
            try:
                from strategies.rsi_strategy import RsiStrategy
                self.strategies['rsi'] = RsiStrategy(self.config)
                self.logger.info("✅ RSI 전략 등록 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ RSI 전략 로드 실패: {e}")
            
            # 알림 서비스
            self.notifier = SimpleNotifier(self.config)
            
            # 실시간 스케줄러
            try:
                from core.scheduler import TradingScheduler
                self.scheduler = TradingScheduler(self)
                self.logger.info("✅ 실시간 스케줄러 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 실시간 스케줄러 초기화 실패: {e}")
                self.scheduler = None
            
            # AI 컨트롤러 초기화
            try:
                from analyzers.ai_controller import AIController
                self.ai_controller = AIController(self.config)
                self.logger.info("✅ AI 컨트롤러 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ AI 컨트롤러 초기화 실패: {e}")
                self.ai_controller = None
            
            # 데이터베이스
            try:
                from database.database_manager import DatabaseManager
                self.db_manager = DatabaseManager(self.config)
                self.logger.info("✅ 데이터베이스 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
                self.db_manager = None
            
            # Trading 모듈들 초기화
            try:
                from trading.executor import TradingExecutor
                from trading.position_manager import PositionManager
                from trading.risk_manager import RiskManager
                
                self.trading_executor = TradingExecutor(self.config, self.data_collector, self.db_manager)
                self.position_manager = PositionManager(self.config, self.data_collector, self.db_manager)
                self.risk_manager = RiskManager(self.config, self.data_collector, self.position_manager, self.trading_executor, self.db_manager)
                
                self.logger.info("✅ Trading 모듈들 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ Trading 모듈 초기화 실패: {e}")
                self.trading_executor = None
                self.position_manager = None
                self.risk_manager = None
            
            
            # 알림 관리자 (Phase 5)
            try:
                from notifications.notification_manager import NotificationManager
                self.notification_manager = NotificationManager(self.config)
                await self.notification_manager.start_processing()
                self.logger.info("✅ 알림 관리자 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 알림 관리자 초기화 실패: {e}")
                self.notification_manager = None
            
            # 분석 핸들러
            try:
                from core.analysis_handlers import AnalysisHandlers
                self.analysis_handlers = AnalysisHandlers(self)
                self.logger.info("✅ 분석 핸들러 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 분석 핸들러 초기화 실패: {e}")
                self.analysis_handlers = None
            
            # 메뉴 핸들러
            try:
                from core.menu_handlers import MenuHandlers
                self.menu_handlers = MenuHandlers(self)
                self.logger.info("✅ 메뉴 핸들러 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ 메뉴 핸들러 초기화 실패: {e}")
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
    async def run_market_analysis(self, strategy: str = 'momentum', limit: int = None) -> List[Dict]:
        """
        시장 분석 (2단계 필터링)을 수행합니다.
        1. 1차 필터링 (HTS 조건검색) 결과를 DB에서 가져옵니다.
        2. 각 종목을 2차 필터링 (종합 분석)합니다.
        3. 분석 결과를 DB에 저장하고 최종 결과를 반환합니다.
        """
        self.last_analysis_time = datetime.now()
        limit_msg = "모든 종목" if limit is None else f"최대 {limit}개"
        self.logger.info(f"📊 시장 분석 시작 (전략: {strategy}, {limit_msg})")

        if not await self._check_components():
            return []

        try:
            with Progress() as progress:
                progress_task = progress.add_task("[green]시장 분석 중...", total=100)

                # 1. 1차 필터링: HTS 조건검색 또는 기본 종목
                progress.update(progress_task, advance=10, description="1차 필터링 (HTS 조건검색 또는 기본 종목) 실행...")
                
                # DB가 없으면 기본 종목들로 진행
                if not self.db_manager:
                    self.logger.error("❌ 데이터베이스 없음. 필터링 불가능합니다.")
                    return []
                else:
                    # DB 연결 안정성 강화 - 예외 처리 추가
                    try:
                        latest_history = await self.db_manager.db_operations.get_latest_filter_history(strategy)
                        
                        # 하루에 한 번만 실행하도록 체크
                        if latest_history and latest_history.filter_date.date() == datetime.now().date():
                            self.logger.info("✅ 오늘 이미 1차 필터링을 수행했습니다. DB 데이터를 사용합니다.")
                            try:
                                candidates = await self.db_manager.db_operations.get_filtered_stocks_for_history(latest_history.id)
                            except Exception as e:
                                self.logger.warning(f"⚠️ DB에서 필터링된 종목 조회 실패: {e}")
                                self.logger.info("🔄 기본 종목으로 대체합니다.")
                                candidates = None
                        else:
                            candidates = None
                    except Exception as db_error:
                        self.logger.warning(f"⚠️ DB 조회 완전 실패: {type(db_error).__name__}: {db_error}")
                        self.logger.info("🔄 DB 없이 진행합니다.")
                        latest_history = None
                        candidates = None
                    
                    # DB 조회 실패 시 새로운 필터링 실행
                    if not candidates:
                        hts_condition_id = self.config.trading.HTS_CONDITIONAL_SEARCH_IDS.get(strategy)
                        if not hts_condition_id:
                            self.logger.error(f"❌ HTS 조건검색식 ID가 없습니다: {strategy}")
                            return []
                        
                        # HTS 조건검색 실행 (개선된 버전)
                        self.logger.info(f"📡 HTS 조건검색 실행: 전략={strategy}, 조건ID={hts_condition_id}")
                        symbols_from_hts = await self.data_collector.get_stocks_by_condition(hts_condition_id)
                        
                        if not symbols_from_hts:
                            console.print(f"[red]❌ HTS 조건검색식 [{hts_condition_id}]에서 종목을 찾지 못했습니다.[/red]")
                            self.logger.error(f"HTS 조건검색 실패 - 필터링 불가능")
                            return []
                        else:
                            self.logger.info(f"✅ HTS 조건검색 성공: {len(symbols_from_hts)}개 종목 발견")
                            
                            # HTS에서 가져온 종목의 경우 API로 정보 조회
                            candidates_data = []
                            for symbol in symbols_from_hts:
                                try:
                                    stock_info = await self.data_collector.get_stock_info(symbol)
                                    if stock_info:
                                        # StockData 객체에서 속성 직접 접근
                                        stock_name = stock_info.name if hasattr(stock_info, 'name') else symbol
                                        candidates_data.append({'stock_code': symbol, 'stock_name': stock_name})
                                    else:
                                        # stock_info가 None인 경우 기본값 사용
                                        candidates_data.append({'stock_code': symbol, 'stock_name': symbol})
                                except Exception as e:
                                    self.logger.warning(f"⚠️ {symbol} 종목 정보 조회 실패: {e}")
                                    candidates_data.append({'stock_code': symbol, 'stock_name': symbol})
                        
                        # DB 저장 시도 (실패해도 계속 진행)
                        try:
                            filter_history = await self.db_manager.db_operations.save_filter_history(strategy, candidates_data)
                            if filter_history:
                                try:
                                    candidates = await self.db_manager.db_operations.get_filtered_stocks_for_history(filter_history.id)
                                except Exception as e:
                                    self.logger.warning(f"⚠️ DB에서 필터링된 종목 조회 실패: {e}")
                                    candidates = None
                            else:
                                self.logger.warning("⚠️ 1차 필터링 이력 저장 실패 - 메모리에서 계속 진행")
                                candidates = None
                        except Exception as save_error:
                            self.logger.warning(f"⚠️ DB 저장 완전 실패: {type(save_error).__name__}: {save_error}")
                            self.logger.info("🔄 DB 없이 메모리에서 계속 진행")
                            candidates = None
                        
                        # DB 실패 시 메모리에서 임시 객체 생성
                        if not candidates:
                            self.logger.info("🔄 DB 실패로 메모리에서 임시 객체 생성")
                            candidates = []
                            for i, data in enumerate(candidates_data):
                                temp_stock = type('Stock', (), {
                                    'id': i,
                                    'stock_id': i,
                                    'stock_code': data['stock_code'],
                                    'stock_name': data['stock_name']
                                })()
                                candidates.append(temp_stock)

                if not candidates:
                    console.print("[red]❌ 1차 필터링된 종목이 없습니다.[/red]")
                    return []
                
                self.logger.info(f"✅ 1차 필터링 완료: {len(candidates)}개 종목 선정")
                progress.update(progress_task, advance=20)

                # 2. 2차 필터링: 종합 분석 실행
                # limit이 None이면 기본값 설정
                actual_limit = limit if limit is not None else 20
                progress.update(progress_task, advance=10, description=f"2차 필터링 (종합 분석) 실행... (상위 {actual_limit}개)")
                
                final_results = []
                analysis_tasks = []
                
                # 상위 limit 개수만큼만 분석
                stocks_to_analyze = candidates[:actual_limit]
                self.logger.info(f"🔍 종합 분석 대상: {len(stocks_to_analyze)}개 종목")

                for i, filtered_stock in enumerate(stocks_to_analyze):
                    # 진행률 업데이트
                    progress_desc = f"2차 필터링 준비 중... ({i+1}/{len(stocks_to_analyze)}) {filtered_stock.stock_code}"
                    progress.update(progress_task, advance=0, description=progress_desc)
                    
                    # DB가 있으면 이미 분석된 종목은 건너뛰기
                    if self.db_manager:
                        existing_analysis = await self.db_manager.db_operations.get_analysis_result_by_filtered_stock_id(filtered_stock.id)
                        if existing_analysis:
                            self.logger.info(f"🔄 {filtered_stock.stock_code}는 이미 분석되었습니다. 건너뜁니다.")
                            continue

                    try:
                        stock_info = await self.data_collector.get_stock_info(filtered_stock.stock_code)
                        if stock_info:
                            analysis_task = self.analysis_engine.analyze_comprehensive(
                                symbol=filtered_stock.stock_code,
                                name=filtered_stock.stock_name,
                                stock_data=stock_info,
                                strategy=strategy
                            )
                            analysis_tasks.append((filtered_stock, analysis_task))
                        else:
                            self.logger.warning(f"⚠️ {filtered_stock.stock_code} 주식 정보 조회 실패")
                    except Exception as e:
                        self.logger.error(f"❌ {filtered_stock.stock_code} 분석 준비 실패: {e}")
                        continue

                # 분석할 대상이 없으면 조기 반환
                if not analysis_tasks:
                    self.logger.warning("⚠️ 분석할 종목이 없습니다 (모두 이미 분석되었거나 데이터 없음)")
                    return []

                # 병렬로 분석 실행 (타임아웃 추가)
                self.logger.info(f"🔄 {len(analysis_tasks)}개 종목 병렬 분석 시작...")
                try:
                    analysis_results_raw = await asyncio.wait_for(
                        asyncio.gather(*[t[1] for t in analysis_tasks], return_exceptions=True),
                        timeout=300  # 5분 타임아웃
                    )
                    self.logger.info(f"✅ 병렬 분석 완료: {len(analysis_results_raw)}개 결과")
                except asyncio.TimeoutError:
                    self.logger.error("❌ 분석 타임아웃 (5분) - 부분 결과로 진행")
                    analysis_results_raw = []
                
                progress.update(progress_task, advance=50)
                progress.update(progress_task, advance=0, description="분석 결과 저장 중...")

                # 3. 분석 결과 저장 및 정리
                for i, result_data in enumerate(analysis_results_raw):
                    filtered_stock, _ = analysis_tasks[i]
                    if isinstance(result_data, Exception) or result_data is None:
                        self.logger.error(f"❌ {filtered_stock.stock_code} 분석 실패: {result_data}")
                        continue
                    
                    # DB에 저장 시도 (DB가 있으면)
                    db_save_success = False
                    if self.db_manager:
                        try:
                            saved_analysis = await self.db_manager.db_operations.save_analysis_result(
                                filtered_stock_id=filtered_stock.id,
                                stock_id=filtered_stock.stock_id,
                                analysis_data=result_data
                            )
                            if saved_analysis:
                                db_save_success = True
                                pass  # DB 저장 성공
                        except Exception as e:
                            self.logger.warning(f"⚠️ DB 저장 실패 {filtered_stock.stock_code}: {e}")
                    
                    # DB 저장 실패 시 로그만 기록
                    if not db_save_success:
                        self.logger.error(f"❌ {filtered_stock.stock_code} 분석 결과 DB 저장 실패")
                    
                    # 결과를 최종 리스트에 추가 (DB 또는 캐시 저장 성공)
                    final_results.append(result_data)

                progress.update(progress_task, advance=20)

            # 최종 결과 정렬 및 반환
            final_results.sort(key=lambda x: x.get('comprehensive_score', 0), reverse=True)
            
            console.print(f"[green]✅ 시장 분석 완료: {len(final_results)}개 종목 분석 완료[/green]")
            return final_results

        except Exception as e:
            console.print(f"[red]❌ 시장 분석 실패: {e}[/red]")
            import traceback
            traceback.print_exc()
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
            self.logger.error(f"❌ 직접 필터링 실패: {e}")
            return []
    
    async def _get_cached_filtered_stocks(self, limit: int) -> Optional[List[Tuple[str, str]]]:
        """캐시된 필터링 종목 조회"""
        # TODO: 캐시 구현
        return None
    
    async def collect_filtered_stocks(self, max_stocks: int = 50) -> List[Dict]:
        """필터링된 종목 수집"""
        # TODO: 실제 필터링 로직 구현
        return []
    
    async def _save_filtered_stocks_cache(self, result: List[Tuple[str, str]]):
        """필터링 결과 캐시 저장"""
        # TODO: 캐시 저장 구현
        pass
    
    async def _direct_filtering(self, limit: int) -> List[Tuple[str, str]]:
        """직접 필터링"""
        # TODO: 직접 필터링 구현
        return []
    
    
    async def _save_filter_history(self, strategy: str, filter_type: str, 
                                 hts_condition: str = None, hts_result_count: int = 0,
                                 hts_symbols: list = None, ai_result_count: int = 0,
                                 ai_symbols: list = None, ai_avg_score: float = 0.0) -> bool:
        """FilterHistory에 필터링 결과 저장"""
        try:
            if not self.db_manager:
                return False
                
            from datetime import datetime
            
            # FilterHistory 레코드 생성 - 올바른 필드명 사용
            filter_data = {
                'filter_date': datetime.now(),
                'strategy': strategy,
                'filter_type': filter_type,
                'hts_condition': hts_condition or f'{strategy}_조건검색',
                'hts_result_count': hts_result_count,
                'hts_symbols': hts_symbols or [],
                'ai_analyzed_count': ai_result_count,
                'ai_passed_count': ai_result_count,
                'final_symbols': ai_symbols or [],
                'final_count': ai_result_count,
                'avg_score': ai_avg_score,
                'execution_time': datetime.now(),
                'status': 'COMPLETED',
                'error_message': None
            }
            
            # DB에 저장 (db_operations 메서드 사용)
            await self.db_manager.db_operations.save_filter_history_record(filter_data)
            self.logger.info(f"✅ FilterHistory 저장 완료: {filter_type} (HTS:{hts_result_count}, AI:{ai_result_count})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ FilterHistory 저장 실패: {e}")
            return False
    
    
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
    
    def _clean_stock_name(self, name: str) -> str:
        """종목명 정리"""
        if not name:
            return name
        # 불필요한 문자 제거
        cleaned = name.strip()
        # 추가 정리 로직 필요시 여기에 추가
        return cleaned
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """종목 정보 조회 (data_collector 래퍼)"""
        if self.data_collector:
            return await self.data_collector.get_stock_info(symbol)
        return None
    
    async def analyze_symbol(self, symbol: str, name: str, strategy: str, stock_id: int = None, filtered_stock_id: int = None) -> Optional[AnalysisResult]:
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
            analysis_result_raw = await self.analysis_engine.analyze_comprehensive(
                symbol=symbol,
                name=final_name,  # 확정된 종목명 사용
                stock_data=stock_data,
                news_data=news_data,
                strategy=strategy
            )
            
            if not analysis_result_raw:
                return None
            
            # 신호 생성
            signals = {'action': 'HOLD', 'strength': 0.5}
            strategy_obj = self.strategies.get(strategy)
            if strategy_obj:
                try:
                    signals = await strategy_obj.generate_signals(stock_data, analysis_result_raw) # analysis_result_raw 사용
                except:
                    pass
            
            # 리스크 평가
            risk_level = self._evaluate_risk(stock_data, analysis_result_raw) # analysis_result_raw 사용
            
            # 추천 등급
            final_grade = self._get_recommendation(analysis_result_raw, signals) # analysis_result_raw 사용
            
            # 가격 계산
            current_price = self._safe_get(stock_data, 'current_price', 0)
            entry_price = current_price
            stop_loss = current_price * 0.95
            take_profit = current_price * 1.10
            
            return AnalysisResult(
                filtered_stock_id=filtered_stock_id,
                stock_id=stock_id,
                symbol=symbol,
                name=final_name,
                analysis_datetime=datetime.now(),
                strategy=strategy,
                total_score=analysis_result_raw.get('comprehensive_score', 0),
                final_grade=final_grade,
                news_score=analysis_result_raw.get('sentiment_score', 0),
                chart_score=analysis_result_raw.get('technical_score', 0),
                supply_demand_score=analysis_result_raw.get('fundamental_score', 0), # 임시로 fundamental_score 사용
                signal_strength=signals.get('strength'),
                signal_type=signals.get('type'),
                action=signals.get('action'),
                volatility=analysis_result_raw.get('volatility'),
                liquidity_risk=analysis_result_raw.get('liquidity_risk'),
                market_risk=analysis_result_raw.get('market_risk'),
                risk_level=risk_level,
                technical_details=analysis_result_raw.get('technical_details'),
                fundamental_details=analysis_result_raw.get('fundamental_details'),
                sentiment_details=analysis_result_raw.get('sentiment_details'),
                price_at_analysis=current_price,
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
    
    def _evaluate_risk(self, stock_data, analysis_result: AnalysisResult) -> str:
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
            
            # 분석 결과의 리스크 레벨도 반영
            if analysis_result.risk_level == "HIGH":
                risk_score += 2
            elif analysis_result.risk_level == "MEDIUM":
                risk_score += 1

            if risk_score >= 3:
                return "HIGH"
            elif risk_score >= 1:
                return "MEDIUM"
            return "LOW"
        except:
            return "MEDIUM"
    
    def _get_recommendation(self, analysis_result: AnalysisResult, signals: Dict) -> str:
        """추천 등급"""
        try:
            score = analysis_result.total_score
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
        banner = f"""[bold cyan]AI Trading System v4.0 - Phase 4: Advanced AI Features[/bold cyan]

5개 영역 통합 분석: 기술적 + 펀더멘털 + 뉴스 + 수급 + 패턴
AI 고급 기능: 예측 + 리스크 관리 + 체제 감지 + 전략 최적화

매매 모드: {'[red]활성화[/red]' if self.trading_enabled else '[yellow]비활성화[/yellow]'}
백테스트: {'[red]활성화[/red]' if self.backtest_mode else '[yellow]비활성화[/yellow]'}
AI 컨트롤러: {'[green]초기화됨[/green]' if hasattr(self, 'ai_controller') and self.ai_controller else '[red]미초기화[/red]'}"""
        
        console.print(Panel.fit(banner, title="AI Trading System v4.0", border_style="cyan"))
    
    def show_main_menu(self):
        """메인 메뉴 표시 - MenuHandlers에 위임"""
        try:
            if not self.menu_handlers:
                from core.menu_handlers import MenuHandlers
                self.menu_handlers = MenuHandlers(self)
            
            # MenuHandlers의 show_main_menu 사용
            self.menu_handlers.show_main_menu()
        except Exception as e:
            # 폴백: 간단한 메뉴 표시
            console.print(Panel("메뉴를 불러올 수 없습니다. MenuHandlers 오류입니다.", title="오류", border_style="red"))
    
    def get_user_choice(self) -> str:
        """사용자 입력 - MenuHandlers에 위임"""
        try:
            if not self.menu_handlers:
                from core.menu_handlers import MenuHandlers
                self.menu_handlers = MenuHandlers(self)
                
            return self.menu_handlers.get_user_choice()
        except KeyboardInterrupt:
            return "0"
        except Exception as e:
            # 폴백: 직접 입력 받기
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
    
    async def _display_analysis_results(self, results: List[Dict]):
        """분석 결과(딕셔셔리 리스트)를 테이블로 표시합니다."""
        if not results:
            console.print("[yellow]📊 분석 결과 없음[/yellow]")
            return

        table = Table(title=f"📊 분석 결과 (상위 {min(len(results), 20)}개)")
        table.add_column("순위", style="cyan", width=4)
        table.add_column("종목코드", style="magenta", width=8)
        table.add_column("종목명", style="white", width=12)
        table.add_column("종합점수", style="green", width=8)
        table.add_column("추천등급", style="yellow", width=12)
        table.add_column("기술", style="blue", width=6)
        table.add_column("수급", style="blue", width=6)
        table.add_column("뉴스", style="blue", width=6)
        table.add_column("패턴", style="blue", width=6)

        for i, result in enumerate(results[:20]):
            name = result.get('name', 'N/A')
            display_name = name[:10] + "…" if len(name) > 10 else name

            table.add_row(
                str(i + 1),
                result.get('symbol', 'N/A'),
                display_name,
                f"{result.get('comprehensive_score', 0):.1f}",
                result.get('recommendation', 'N/A'),
                f"{result.get('technical_score', 0):.0f}",
                f"{result.get('supply_demand_score', 0):.0f}",
                f"{result.get('sentiment_score', 0):.0f}",
                f"{result.get('chart_pattern_score', 0):.0f}"
            )
        
        console.print(table)

    async def execute_auto_buy(self, results: List[Dict], top_n: int = 3, budget_per_stock: int = 1000000) -> Dict[str, Any]:
        """분석 결과 상위 점수 종목 자동 매수"""
        try:
            self.logger.info(f"🚀 자동 매수 시작: 상위 {top_n}개 종목, 종목당 {budget_per_stock:,}원")
            
            # 1. 매수 가능 여부 확인
            if not hasattr(self, 'trading_executor') or not self.trading_executor:
                self.logger.error("❌ Trading Executor가 초기화되지 않았습니다")
                return {'success': False, 'reason': 'Trading Executor 없음'}
            
            # 2. 상위 점수 종목 선별 (STRONG_BUY, BUY만)
            buy_candidates = []
            for result in results[:top_n * 2]:  # 여유분 확보
                if result.get('recommendation') in ['STRONG_BUY', 'BUY']:
                    score = result.get('comprehensive_score', 0)
                    if score >= 70:  # 최소 70점 이상만
                        buy_candidates.append(result)
                        if len(buy_candidates) >= top_n:
                            break
            
            if not buy_candidates:
                self.logger.warning("⚠️ 매수 조건을 만족하는 종목이 없습니다 (70점 이상, BUY 등급)")
                return {'success': False, 'reason': '매수 조건 불만족'}
            
            # 3. 매수 실행 결과
            execution_results = []
            total_success = 0
            total_failed = 0
            
            console.print(f"\n[bold green][TARGET] 자동 매수 대상: {len(buy_candidates)}개 종목[/bold green]")
            
            for i, stock in enumerate(buy_candidates, 1):
                symbol = stock.get('symbol')
                name = stock.get('name', 'N/A')
                score = stock.get('comprehensive_score', 0)
                recommendation = stock.get('recommendation', 'N/A')
                
                console.print(f"\n[cyan]매수 {i}/{len(buy_candidates)}: {symbol}({name}) - 점수: {score:.1f}, 등급: {recommendation}[/cyan]")
                
                # 현재 주가 정보 조회
                current_stock_data = await self.data_collector.get_stock_info(symbol)
                if not current_stock_data:
                    self.logger.warning(f"⚠️ {symbol} 주가 정보 조회 실패")
                    execution_results.append({
                        'symbol': symbol, 'name': name, 'status': 'FAILED',
                        'reason': '주가 정보 조회 실패'
                    })
                    total_failed += 1
                    continue
                
                current_price = current_stock_data.current_price
                quantity = max(1, int(budget_per_stock / current_price))  # 최소 1주
                expected_amount = quantity * current_price
                
                console.print(f"  현재가: {current_price:,}원, 수량: {quantity:,}주, 예상금액: {expected_amount:,}원")
                
                # 매수 주문 실행
                order_result = await self.trading_executor.execute_buy_order(
                    symbol=symbol,
                    quantity=quantity,
                    price=None,  # 시장가 주문
                    order_type=OrderType.MARKET
                )
                
                if order_result.get('status') == 'SUCCESS':
                    console.print(f"  [green]✅ 매수 성공[/green]")
                    total_success += 1
                    execution_results.append({
                        'symbol': symbol, 'name': name, 'status': 'SUCCESS',
                        'quantity': quantity, 'price': current_price,
                        'amount': expected_amount
                    })
                else:
                    console.print(f"  [red]❌ 매수 실패: {order_result.get('reason', '알 수 없는 오류')}[/red]")
                    total_failed += 1
                    execution_results.append({
                        'symbol': symbol, 'name': name, 'status': 'FAILED',
                        'reason': order_result.get('reason', '알 수 없는 오류')
                    })
                
                # 주문 간 간격 (초당 주문 제한 준수)
                await asyncio.sleep(1)
            
            # 4. 결과 요약
            console.print(f"\n[bold][RESULT] 자동 매수 완료[/bold]")
            console.print(f"성공: {total_success}건, 실패: {total_failed}건")
            
            return {
                'success': True,
                'total_orders': len(buy_candidates),
                'successful_orders': total_success,
                'failed_orders': total_failed,
                'execution_results': execution_results
            }
            
        except Exception as e:
            self.logger.error(f"❌ 자동 매수 실행 실패: {e}")
            return {'success': False, 'reason': f'실행 오류: {str(e)}'}

    async def run_analysis_and_auto_buy(self, strategy: str = 'momentum', top_n: int = 3, 
                                       budget_per_stock: int = 1000000) -> Dict[str, Any]:
        """시장 분석 후 상위 점수 종목 자동 매수"""
        try:
            console.print(f"[bold cyan][START] 시장 분석 및 자동 매수 시작[/bold cyan]")
            console.print(f"전략: {strategy}, 상위 {top_n}개 종목, 종목당 {budget_per_stock:,}원")
            
            # 1. 시장 분석 실행
            analysis_results = await self.run_market_analysis(strategy=strategy)
            
            if not analysis_results:
                console.print("[red]❌ 분석 결과가 없어 매수를 진행할 수 없습니다[/red]")
                return {'success': False, 'reason': '분석 결과 없음'}
            
            # 2. 분석 결과 표시
            await self._display_analysis_results(analysis_results)
            
            # 3. 매수 확인
            if not self.trading_enabled:
                console.print("[yellow]⚠️ 매매 모드가 비활성화되어 있습니다. 시뮬레이션으로 진행합니다.[/yellow]")
            
            user_confirm = Prompt.ask(
                f"\n상위 {top_n}개 종목을 자동 매수하시겠습니까?", 
                choices=["y", "n"], 
                default="n"
            )
            
            if user_confirm.lower() != 'y':
                console.print("[yellow][CANCEL] 자동 매수를 취소했습니다[/yellow]")
                return {'success': False, 'reason': '사용자 취소'}
            
            # 4. 자동 매수 실행
            buy_result = await self.execute_auto_buy(analysis_results, top_n, budget_per_stock)
            
            return buy_result
            
        except Exception as e:
            self.logger.error(f"❌ 분석 및 자동 매수 실패: {e}")
            return {'success': False, 'reason': f'실행 오류: {str(e)}'}

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
    
    # === Phase 4: Advanced AI Features ===
    
    async def run_ai_comprehensive_analysis(self, market_data: List[Dict] = None,
                                          individual_stocks: List[Dict] = None,
                                          portfolio_data: Dict = None) -> Dict[str, Any]:
        """AI 종합 분석 실행"""
        try:
            if not self.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return {}
            
            console.print("[cyan]🧠 AI 종합 분석 시작...[/cyan]")
            
            # 기본 데이터 준비
            if market_data is None:
                market_data = []
            
            if individual_stocks is None:
                # HTS 조건검색에서 종목 추출 (실제 API 사용)
                stocks_from_hts = await self.data_collector.get_stocks_by_condition("momentum")
                if not stocks_from_hts:
                    console.print("[yellow]⚠️ HTS에서 종목을 가져올 수 없습니다. 개별 종목 분석을 건너뜁니다.[/yellow]")
                    return []
                individual_stocks = []
                for symbol in stocks_from_hts[:20]:  # 최대 20개 종목
                    try:
                        stock_info = await self.data_collector.get_stock_info(symbol)
                        if stock_info:
                            individual_stocks.append({
                                'symbol': symbol,
                                'name': stock_info.name,
                                'current_price': stock_info.current_price,
                                'change_rate': stock_info.change_rate,
                                'volume': stock_info.volume
                            })
                    except Exception as e:
                        self.logger.warning(f"⚠️ {symbol} 정보 조회 실패: {e}")
            
            if portfolio_data is None:
                portfolio_data = {'total_value': 10000000, 'positions': {}}
            
            # AI 종합 분석 실행
            analysis_result = await self.ai_controller.comprehensive_market_analysis(
                market_data, individual_stocks, portfolio_data
            )
            
            # 결과 표시
            await self._display_ai_analysis_results(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ AI 종합 분석 실패: {e}")
            console.print(f"[red]❌ AI 종합 분석 실패: {e}[/red]")
            return {}
    
    async def run_ai_market_regime_analysis(self) -> Dict[str, Any]:
        """AI 시장 체제 분석"""
        try:
            if not self.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return {}
            
            console.print("[cyan]🌐 AI 시장 체제 분석 시작...[/cyan]")
            
            # 시장 데이터 수집
            market_data = []
            individual_stocks = []
            
            # HTS 조건검색에서 종목 데이터 수집
            stocks_from_hts = await self.data_collector.get_stocks_by_condition("momentum")
            if not stocks_from_hts:
                console.print("[yellow]⚠️ HTS에서 종목을 가져올 수 없습니다. AI 시장 분석을 건너뜁니다.[/yellow]")
                return []
                
            for symbol in stocks_from_hts[:30]:  # 최대 30개 종목
                try:
                    stock_info = await self.data_collector.get_stock_info(symbol)
                    if stock_info:
                        stock_dict = {
                            'symbol': symbol,
                            'name': stock_info.name,
                            'current_price': stock_info.current_price,
                            'change_rate': stock_info.change_rate,
                            'volume': stock_info.volume,
                            'trading_value': stock_info.trading_value
                        }
                        individual_stocks.append(stock_dict)
                        market_data.append(stock_dict)
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 데이터 수집 실패: {e}")
            
            # 시장 체제 감지
            current_regime = await self.ai_controller.regime_detector.detect_current_regime(
                market_data, individual_stocks
            )
            
            # 결과 표시
            await self._display_regime_analysis(current_regime)
            
            return {
                'regime_type': current_regime.regime_type,
                'confidence': current_regime.confidence,
                'expected_duration': current_regime.expected_duration,
                'recommended_strategies': current_regime.recommended_strategies,
                'risk_factors': current_regime.risk_factors,
                'market_characteristics': current_regime.market_characteristics
            }
            
        except Exception as e:
            self.logger.error(f"❌ AI 시장 체제 분석 실패: {e}")
            console.print(f"[red]❌ AI 시장 체제 분석 실패: {e}[/red]")
            return {}
    
    async def run_ai_strategy_optimization(self, strategy_name: str = None) -> Dict[str, Any]:
        """AI 전략 최적화"""
        try:
            if not self.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return {}
            
            if strategy_name is None:
                # 사용 가능한 전략 목록 표시
                available_strategies = list(self.strategies.keys())
                console.print("\n[bold]사용 가능한 전략:[/bold]")
                for i, strategy in enumerate(available_strategies, 1):
                    console.print(f"  {i}. {strategy}")
                
                from rich.prompt import Prompt
                choice = Prompt.ask("최적화할 전략 번호를 선택하세요", 
                                  choices=[str(i) for i in range(1, len(available_strategies) + 1)],
                                  default="1")
                strategy_name = available_strategies[int(choice) - 1]
            
            console.print(f"[cyan]⚙️ {strategy_name} 전략 AI 최적화 시작...[/cyan]")
            
            # 모의 성과 데이터 (실제 구현에서는 실제 성과 데이터 사용)
            performance_data = {
                'total_return': 0.08,
                'sharpe_ratio': 1.2,
                'max_drawdown': 0.12,
                'win_rate': 0.65,
                'volatility': 0.15
            }
            
            # 시장 조건 데이터
            market_conditions = {
                'volatility': 0.20,
                'trend': 'NEUTRAL',
                'regime': 'SIDEWAYS'
            }
            
            # 전략 최적화 실행
            optimization_result = await self.ai_controller.strategy_optimizer.optimize_strategy(
                strategy_name, performance_data, market_conditions
            )
            
            # 결과 표시
            await self._display_optimization_results(optimization_result)
            
            return {
                'strategy_name': optimization_result.strategy_name,
                'performance_improvement': optimization_result.performance_improvement,
                'confidence': optimization_result.confidence,
                'optimized_params': optimization_result.optimized_params,
                'ai_insights': optimization_result.ai_insights
            }
            
        except Exception as e:
            self.logger.error(f"❌ AI 전략 최적화 실패: {e}")
            console.print(f"[red]❌ AI 전략 최적화 실패: {e}[/red]")
            return {}
    
    async def run_ai_risk_assessment(self, portfolio_data: Dict = None) -> Dict[str, Any]:
        """AI 리스크 평가"""
        try:
            if not self.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return {}
            
            console.print("[cyan]🛡️ AI 포트폴리오 리스크 평가 시작...[/cyan]")
            
            # 기본 포트폴리오 데이터
            if portfolio_data is None:
                portfolio_data = {
                    'total_value': 10000000,
                    'positions': {
                        '005930': {'value': 3000000, 'quantity': 100},
                        '000660': {'value': 2000000, 'quantity': 50},
                        '035420': {'value': 1500000, 'quantity': 30}
                    },
                    'cash': 3500000
                }
            
            # 시장 데이터
            market_data = {'volatility': 0.20, 'trend': 'NEUTRAL'}
            
            # AI 리스크 평가 실행
            risk_assessment = await self.ai_controller.risk_manager.assess_portfolio_risk(
                portfolio_data, market_data
            )
            
            # 결과 표시
            await self._display_risk_assessment(risk_assessment)
            
            return {
                'overall_risk_level': risk_assessment.overall_risk_level,
                'risk_score': risk_assessment.risk_score,
                'key_risk_factors': risk_assessment.key_risk_factors,
                'mitigation_strategies': risk_assessment.risk_mitigation_strategies,
                'confidence': risk_assessment.confidence
            }
            
        except Exception as e:
            self.logger.error(f"❌ AI 리스크 평가 실패: {e}")
            console.print(f"[red]❌ AI 리스크 평가 실패: {e}[/red]")
            return {}
    
    async def generate_ai_daily_report(self) -> Dict[str, Any]:
        """AI 일일 보고서 생성"""
        try:
            if not self.ai_controller:
                console.print("[yellow]⚠️ AI 컨트롤러가 초기화되지 않았습니다.[/yellow]")
                return {}
            
            console.print("[cyan]📊 AI 일일 보고서 생성 중...[/cyan]")
            
            # AI 보고서 생성
            report = await self.ai_controller.generate_ai_report('daily')
            
            # 결과 표시
            await self._display_ai_report(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ AI 보고서 생성 실패: {e}")
            console.print(f"[red]❌ AI 보고서 생성 실패: {e}[/red]")
            return {}
    
    # === AI 결과 표시 메서드들 ===
    
    async def _display_ai_analysis_results(self, analysis_result: Dict):
        """AI 분석 결과 표시"""
        try:
            if not analysis_result:
                return
            
            # 시장 체제 정보
            regime_info = analysis_result.get('market_regime', {})
            console.print(Panel(
                f"[bold blue]🌐 시장 체제[/bold blue]\n"
                f"• 체제: {regime_info.get('regime_type', 'UNKNOWN')}\n"
                f"• 신뢰도: {regime_info.get('confidence', 0):.1f}%\n"
                f"• 예상 지속기간: {regime_info.get('expected_duration', 0)}일\n"
                f"• 추천 전략: {', '.join(regime_info.get('recommended_strategies', []))}",
                title="🧠 AI 시장 분석",
                border_style="blue"
            ))
            
            # 주요 인사이트
            insights = analysis_result.get('ai_insights', [])
            if insights:
                insight_text = "\n".join([
                    f"• [{insight.get('priority', 'MEDIUM')}] {insight.get('message', '')}"
                    for insight in insights[:5]
                ])
                console.print(Panel(
                    f"[bold green]💡 주요 인사이트[/bold green]\n{insight_text}",
                    title="🎯 AI 인사이트",
                    border_style="green"
                ))
            
            # AI 결정 사항
            decisions = analysis_result.get('ai_decisions', [])
            if decisions:
                decision_text = "\n".join([
                    f"• {decision.get('recommendation', '')} (신뢰도: {decision.get('confidence', 0):.1f}%)"
                    for decision in decisions[:3]
                ])
                console.print(Panel(
                    f"[bold yellow]⚙️ AI 추천 결정[/bold yellow]\n{decision_text}",
                    title="🎯 실행 권고",
                    border_style="yellow"
                ))
            
        except Exception as e:
            self.logger.error(f"❌ AI 결과 표시 실패: {e}")
    
    async def _display_regime_analysis(self, regime):
        """시장 체제 분석 결과 표시"""
        try:
            console.print(Panel(
                f"[bold cyan]🌐 시장 체제 분석 결과[/bold cyan]\n\n"
                f"[green]체제 정보[/green]\n"
                f"• 체제 유형: {regime.regime_type}\n"
                f"• 세부 체제: {regime.sub_regime}\n"
                f"• 신뢰도: {regime.confidence:.1f}%\n"
                f"• 예상 지속기간: {regime.expected_duration}일\n\n"
                f"[yellow]주요 특징[/yellow]\n"
                f"• {chr(10).join([f'  - {indicator}' for indicator in regime.key_indicators])}\n\n"
                f"[blue]추천 전략[/blue]\n"
                f"• {', '.join(regime.recommended_strategies)}\n\n"
                f"[red]리스크 요인[/red]\n"
                f"• {chr(10).join([f'  - {risk}' for risk in regime.risk_factors])}",
                title="🧠 AI 시장 체제 분석",
                border_style="cyan"
            ))
            
        except Exception as e:
            self.logger.error(f"❌ 체제 분석 표시 실패: {e}")
    
    async def _display_optimization_results(self, result):
        """최적화 결과 표시"""
        try:
            console.print(Panel(
                f"[bold green]⚙️ {result.strategy_name} 전략 최적화 결과[/bold green]\n\n"
                f"[yellow]성과 개선[/yellow]\n"
                f"• 예상 개선률: {result.performance_improvement:.1f}%\n"
                f"• 최적화 신뢰도: {result.confidence:.1f}%\n"
                f"• 최적화 방법: {result.optimization_method}\n\n"
                f"[blue]AI 인사이트[/blue]\n"
                f"• {chr(10).join([f'  - {insight}' for insight in result.ai_insights])}\n\n"
                f"[red]주의사항[/red]\n"
                f"• {chr(10).join([f'  - {warning}' for warning in result.risk_warnings])}\n\n"
                f"[green]모니터링[/green]\n"
                f"• 모니터링 주기: {result.monitoring_frequency}",
                title="🎯 전략 최적화",
                border_style="green"
            ))
            
        except Exception as e:
            self.logger.error(f"❌ 최적화 결과 표시 실패: {e}")
    
    async def _display_risk_assessment(self, assessment):
        """리스크 평가 결과 표시"""
        try:
            console.print(Panel(
                f"[bold red]🛡️ AI 포트폴리오 리스크 평가[/bold red]\n\n"
                f"[yellow]전체 리스크[/yellow]\n"
                f"• 리스크 레벨: {assessment.overall_risk_level}\n"
                f"• 리스크 점수: {assessment.risk_score:.1f}/100\n"
                f"• 평가 신뢰도: {assessment.confidence:.1f}%\n\n"
                f"[red]주요 리스크 요인[/red]\n"
                f"• {chr(10).join([f'  - {factor}' for factor in assessment.key_risk_factors])}\n\n"
                f"[green]완화 전략[/green]\n"
                f"• {chr(10).join([f'  - {strategy}' for strategy in assessment.risk_mitigation_strategies])}\n\n"
                f"[blue]권장 조치[/blue]\n"
                f"• {chr(10).join([f'  - {action}' for action in assessment.recommended_actions])}",
                title="⚠️ 리스크 관리",
                border_style="red"
            ))
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 평가 표시 실패: {e}")
    
    async def _display_ai_report(self, report):
        """AI 보고서 표시"""
        try:
            console.print(Panel(
                f"[bold cyan]📊 AI 일일 보고서[/bold cyan]\n\n"
                f"[green]시장 상황[/green]\n"
                f"• 현재 체제: {report.get('market_regime_summary', {}).get('current_regime', 'UNKNOWN')}\n"
                f"• 체제 안정성: {report.get('market_regime_summary', {}).get('stability', 'STABLE')}\n\n"
                f"[yellow]예측 정확도[/yellow]\n"
                f"• 전체 정확도: {report.get('prediction_accuracy', {}).get('overall_accuracy', 0):.1%}\n"
                f"• 트렌드 정확도: {report.get('prediction_accuracy', {}).get('trend_accuracy', 0):.1%}\n\n"
                f"[blue]시스템 건전성[/blue]\n"
                f"• 전체 상태: {report.get('system_health', {}).get('overall_health', 'GOOD')}\n"
                f"• 가동률: {report.get('system_health', {}).get('uptime', 0):.1%}\n\n"
                f"[magenta]주요 인사이트[/magenta]\n"
                f"• {chr(10).join([f'  - {insight}' for insight in report.get('key_insights', [])])}\n\n"
                f"[green]전략적 권고[/green]\n"
                f"• {chr(10).join([f'  - {rec}' for rec in report.get('recommendations', [])])}",
                title="📈 AI 분석 보고서",
                border_style="cyan"
            ))
            
        except Exception as e:
            self.logger.error(f"❌ AI 보고서 표시 실패: {e}")
    
    # === 기존 시스템 상태 메서드 업데이트 ===
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 (AI 기능 포함)"""
        base_status = {
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
                'db_manager': self.db_manager is not None,
                'scheduler': self.scheduler is not None,
                'ai_controller': self.ai_controller is not None,  # Phase 4 추가
            }
        }
        
        # AI 컨트롤러 상태 추가
        if self.ai_controller:
            try:
                ai_status = await self.ai_controller._get_system_status()
                base_status['ai_system'] = {
                    'overall_confidence': ai_status.overall_confidence,
                    'active_models': ai_status.active_models,
                    'system_health': ai_status.system_health,
                    'prediction_accuracy': ai_status.prediction_accuracy
                }
            except Exception as e:
                base_status['ai_system'] = {'error': str(e)}
        
        return base_status
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            console.print("[yellow]정리 중...[/yellow]")
            self.is_running = False
            
            # 캐시 통계 제거 - 단순화
            
            # 알림 관리자 정리
            if hasattr(self, 'notification_manager') and self.notification_manager:
                await self.notification_manager.cleanup()
            
            # 데이터 수집기 정리 (aiohttp 세션 포함)
            if self.data_collector:
                if hasattr(self.data_collector, 'cleanup'):
                    await self.data_collector.cleanup()
                else:
                    await self.data_collector.close()
            
            console.print("[green]정리 완료[/green]")
        except Exception as e:
            console.print(f"[yellow]정리 중 오류: {e}[/yellow]")
    
    async def stop(self):
        """시스템 정지"""
        console.print("[yellow]🛑 정지 중...[/yellow]")
        await self.cleanup()
        console.print("[bold]✅ 정지 완료[/bold]")