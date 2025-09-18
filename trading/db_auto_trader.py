#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/db_auto_trader.py

DB 연동 자동매매 시스템 - 영구 저장/복원 지원
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
from utils.logger import get_logger
from database.models import (
    MonitoringStock, MonitoringStatus, MonitoringType, OrderType
)
from .executor import TradingExecutor, OrderSide, ExecutionResult
from data_collectors.chart_data_collector import ChartDataCollector
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.technical_indicators import PriceData
from utils.pattern_detector import PatternDetector


@dataclass
class TradingSignal:
    """매매 신호"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    price: int
    reason: str
    timestamp: datetime


class DatabaseAutoTrader:
    """DB 연동 자동매매 시스템"""
    
    def __init__(self, config, kis_collector, executor: TradingExecutor, market_manager, analysis_engine=None, db_manager=None):
        self.config = config
        self.kis_collector = kis_collector
        self.executor = executor
        self.market_manager = market_manager
        self.analysis_engine = analysis_engine
        self.db_manager = db_manager
        self.logger = get_logger("DatabaseAutoTrader")
        
        # 실제 기술적 지표 계산 시스템
        self.chart_data_collector = ChartDataCollector(kis_collector)
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.pattern_detector = PatternDetector(config) # Instantiate PatternDetector
        
        # 스마트 리밸런서 (DB 연동)
        from trading.smart_rebalancer import SmartRebalancer
        self.smart_rebalancer = SmartRebalancer(config, db_manager)
        
        # 전략 자동 실행 시스템
        self.strategy_auto_executor = None
        self.strategy_execution_enabled = True  # 기본적으로 활성화
        
        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_interval = 30  # 30초마다 체크
        
        # 매매 설정
        self.max_positions = getattr(config.trading, 'MAX_POSITIONS', 5)
        self.risk_per_trade = getattr(config.trading, 'RISK_PER_TRADE', 0.02)  # 2%
        
        # 설정 파일 경로
        self.settings_file = Path("D:/trading_system/configs/trading_settings.json")
        
        # 매매 기능 자동 활성화
        try:
            if hasattr(self.executor, 'enable_trading'):
                self.executor.enable_trading()
                self.logger.info("✅ 매매 기능이 자동으로 활성화되었습니다.")
            else:
                self.logger.warning("⚠️ 매매 활성화 메서드를 찾을 수 없습니다.")
        except Exception as e:
            self.logger.error(f"❌ 매매 기능 자동 활성화 실패: {e}")
        
        self.logger.info("🤖 DatabaseAutoTrader 초기화 완료 - DB 연동")
    
    async def initialize_strategy_auto_executor(self):
        """전략 자동 실행 시스템 초기화"""
        if not self.strategy_execution_enabled:
            return
        
        try:
            from strategy_auto_executor import StrategyAutoExecutor
            self.strategy_auto_executor = StrategyAutoExecutor(self.config, self.db_manager)
            
            # 시스템 초기화
            if await self.strategy_auto_executor.initialize_system():
                self.logger.info("✅ 전략 자동 실행 시스템 초기화 완료")
            else:
                self.logger.error("❌ 전략 자동 실행 시스템 초기화 실패")
                self.strategy_auto_executor = None
                
        except Exception as e:
            self.logger.error(f"❌ 전략 자동 실행 시스템 로드 실패: {e}")
            self.strategy_auto_executor = None
    
    def _load_trading_settings(self) -> Dict[str, Any]:
        """매매 설정 로드"""
        default_settings = {
            'target_profit_rate': 10.0,     # 목표 수익률 10%
            'stop_loss_rate': 5.0,          # 손절 비율 5%
        }
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                    default_settings.update(user_settings)
                    self.logger.debug(f"✅ 매매 설정 로드: 목표 수익률 {default_settings['target_profit_rate']:.1f}%, 손절 비율 {default_settings['stop_loss_rate']:.1f}%")
            
            return default_settings
            
        except Exception as e:
            self.logger.error(f"매매 설정 로드 실패: {e}")
            return default_settings
    
    async def start_monitoring(self):
        """모니터링 시작"""
        try:
            if self.is_monitoring:
                self.logger.warning("이미 모니터링이 실행 중입니다")
                return
            
            # 전략 자동 실행 시스템 초기화 (모니터링 시작 시 한 번)
            await self.initialize_strategy_auto_executor()
            
            self.is_monitoring = True
            # 백그라운드 로그만 기록
            pass  # 자동매매 모니터링 시작 메시지 제거
            
            # 메인 모니터링 루프
            while self.is_monitoring:
                try:
                    await self._monitoring_cycle()
                    
                    # 전략 자동 실행 체크 (기존 모니터링과 함께)
                    if self.strategy_auto_executor:
                        await self.strategy_auto_executor.run_auto_execution_cycle()
                    
                    await asyncio.sleep(self.monitoring_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"❌ 모니터링 사이클 오류: {e}")
                    await asyncio.sleep(self.monitoring_interval)
            
            self.logger.info("🛑 자동매매 모니터링 종료")
            
            # 전략 자동 실행 시스템 정리
            if self.strategy_auto_executor:
                self.strategy_auto_executor.stop_auto_execution()
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 시작 실패: {e}")
            self.is_monitoring = False
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        try:
            self.is_monitoring = False
            self.logger.info("🛑 자동매매 모니터링 중지 요청")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 중지 오류: {e}")
    
    async def _monitoring_cycle(self):
        """모니터링 사이클 실행"""
        try:
            # [추가] 시장 시간 확인
            if not self.market_manager.is_monitoring_allowed_now():
                status_info = self.market_manager.get_current_status_info()
                self.logger.debug(f"시장 운영 시간이 아닙니다. 현재 상태: {status_info.get('market_status_korean', '알 수 없음')}. 모니터링 사이클을 건너뜁니다.")
                return

            # 현재가 업데이트는 실시간 API 호출로만 처리 (DB 저장 없음)
            
            # 보유 종목을 모니터링 목록에 추가 (주기적으로 실행)
            await self.import_portfolio_to_monitoring()

            # KIS API에서 실제 보유 종목 목록 가져오기
            try:
                holdings = await self.kis_collector.get_holdings()
                if holdings:
                    # 수량이 0보다 큰 종목의 심볼만 세트로 저장
                    actual_holding_symbols = {symbol for symbol, holding in holdings.items() if getattr(holding, 'quantity', 0) > 0}
                else:
                    actual_holding_symbols = set()
            except Exception as e:
                self.logger.error(f"❌ KIS API에서 보유 종목 조회 실패: {e}")
                actual_holding_symbols = set() # 실패 시 빈 세트로 초기화하여 안전하게 처리

            # DB에서 활성 모니터링 종목 가져오기 - ID만 가져와서 세션 바인딩 문제 해결
            with self.db_manager.get_session() as session:
                monitoring_data = session.query(
                    MonitoringStock.id,
                    MonitoringStock.symbol, 
                    MonitoringStock.name
                ).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE.value,
                    MonitoringStock.monitoring_type.in_([MonitoringType.TRADING, MonitoringType.PORTFOLIO])
                ).all()
            
            if not monitoring_data:
                self.logger.debug("모니터링할 종목이 없습니다")
                return

            # [FIX] TRADING 타입은 실제 보유 여부와 무관하게 분석, PORTFOLIO 타입만 보유종목 필터링
            filtered_monitoring_data = [
                stock for stock in monitoring_data 
                if (stock.symbol in actual_holding_symbols or 
                    stock.monitoring_type == MonitoringType.TRADING)
            ]

            if not filtered_monitoring_data:
                self.logger.debug("분석 대상 모니터링 종목이 없습니다.")
                return
            
            # 백그라운드 로그만 기록
            pass  # 모니터링 실행 메시지 제거
            
            # 각 종목 분석 (개별 종목 타임아웃 적용 - 안정성 우선)
            for i, stock_data in enumerate(filtered_monitoring_data, 1):
                try:
                    self.logger.debug(f"📊 [{i}/{len(filtered_monitoring_data)}] {stock_data.symbol}({stock_data.name}) 분석 중...")
                    # 개별 종목 분석에 타임아웃 적용 (15초로 단축)
                    analyze_task = asyncio.create_task(
                        self._analyze_stock_by_id(stock_data.id, stock_data.symbol, stock_data.name)
                    )
                    await asyncio.wait_for(analyze_task, timeout=15.0)
                    
                except asyncio.TimeoutError:
                    self.logger.warning(f"⚠️ {stock_data.symbol} 분석 타임아웃 (15초) - 다음 종목으로 넘어감")
                except Exception as e:
                    self.logger.error(f"❌ {stock_data.symbol} 분석 오류: {e} - 계속 진행")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 사이클 오류: {e}")
    
    async def _analyze_stock_by_id(self, stock_id: int, symbol: str, name: str):
        """개별 종목 분석 및 매매 신호 생성 - ID 기반"""
        try:
            # 현재가 조회 (재시도 로직 추가)
            current_price = None
            for attempt in range(3):
                current_price = await self.kis_collector.get_current_price(symbol)
                if current_price:
                    break
                if attempt < 2:
                    await asyncio.sleep(0.5)  # 0.5초 대기 후 재시도
            
            if not current_price:
                self.logger.warning(f"❌ {symbol} 현재가 3회 시도 실패 - 스킵")
                return
            
            # DB에 현재가 업데이트
            with self.db_manager.get_session() as session:
                db_stock = session.query(MonitoringStock).filter(
                    MonitoringStock.id == stock_id
                ).first()
                if db_stock:
                    db_stock.last_check_time = datetime.now()
                    
                    # 알고리즘 기반 목표가 및 손절가 재계산
                    # 설정 파일에서 목표 수익률 로드
                    settings = self._load_trading_settings()
                    take_profit_ratio = settings['target_profit_rate'] / 100  # 백분율을 비율로 변환
                    
                    # 목표가 재계산 (현재가 + 설정된 수익률)
                    new_target_price = int(current_price * (1 + take_profit_ratio))
                    
                    # 알고리즘 기반 손절가 계산
                    new_stop_loss_price = self.calculate_stop_loss_price(current_price, db_stock.strategy_name)
                    self.logger.debug(f"🔍 {symbol} 손절가 계산 결과: {new_stop_loss_price}")

                    # 기존 목표가/손절가가 없거나, 현재가와 너무 차이나는 경우에만 업데이트
                    # (예: 20% 이상 차이 나면 업데이트)
                    if db_stock.target_price is None or abs(db_stock.target_price - new_target_price) / new_target_price > 0.2:
                        db_stock.target_price = new_target_price
                        self.logger.debug(f"📈 {symbol} 목표가 업데이트: {new_target_price:,}원")
                    
                    # 손절가 업데이트 로직 개선 - 항상 업데이트하도록 수정
                    if new_stop_loss_price:
                        if (db_stock.stop_loss_price is None or 
                            abs(db_stock.stop_loss_price - new_stop_loss_price) / new_stop_loss_price > 0.05):  # 5% 차이시 업데이트
                            old_stop_loss = db_stock.stop_loss_price
                            db_stock.stop_loss_price = new_stop_loss_price
                            self.logger.info(f"💡 {symbol} 알고리즘 손절가 업데이트: {old_stop_loss or 0:,}원 → {new_stop_loss_price:,}원")
                        else:
                            self.logger.debug(f"💡 {symbol} 손절가 변화 없음: {db_stock.stop_loss_price:,}원")
                    else:
                        self.logger.warning(f"⚠️ {symbol} 손절가 계산 실패 - None 반환")

                    session.commit()
            
            # 차트 데이터 수집 (타임아웃 및 오류 방지)
            chart_data = []
            try:
                chart_data_task = asyncio.create_task(self._get_chart_data(symbol))
                chart_data = await asyncio.wait_for(chart_data_task, timeout=8.0)
                if not chart_data:
                    self.logger.debug(f"📊 {symbol} 차트 데이터 없음 - 현재가 기반 간단 분석으로 진행")
                    chart_data = []
            except asyncio.TimeoutError:
                self.logger.warning(f"⚠️ {symbol} 차트 데이터 조회 타임아웃 (8초) - 기본값 사용")
                chart_data = []
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} 차트 데이터 조회 실패: {e} - 기본값 사용")
                chart_data = []
            
            # 기술적 분석 (타임아웃 및 오류 방지)
            try:
                # OHLCV 데이터를 기술적 분석기가 이해할 수 있는 형태로 변환
                formatted_data = []
                for price_data in chart_data:
                    formatted_data.append({
                        'date': price_data.timestamp,
                        'open': float(price_data.open),
                        'high': float(price_data.high),
                        'low': float(price_data.low),
                        'close': float(price_data.close),
                        'volume': int(price_data.volume)
                    })

                # 기술적 지표 계산에 타임아웃 적용
                technical_analysis_task = asyncio.create_task(
                    self.technical_analyzer.analyze_stock(symbol, formatted_data)
                )
                technical_data = await asyncio.wait_for(technical_analysis_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning(f"⚠️ {symbol} 기술적 분석 타임아웃 (5초) - 기본값 사용")
                technical_data = {
                    'technical_score': 30,  # 기본 점수
                    'indicators': {
                        'rsi': 50,
                        'ma5': current_price,
                        'ma20': current_price,
                        'ma_signal': 'HOLD',
                        'macd_trend': 'NEUTRAL',
                        'macd_signal': 0,
                        'macd_histogram': 0,
                        'volume': 0,
                        'avg_volume': 0
                    }
                }
            except Exception as e:
                self.logger.warning(f"⚠️ {symbol} 기술적 분석 실패: {e} - 기본값 사용")
                technical_data = {
                    'technical_score': 30,  # 기본 점수
                    'indicators': {
                        'rsi': 50,
                        'ma5': current_price,
                        'ma20': current_price,
                        'ma_signal': 'HOLD',
                        'macd_trend': 'NEUTRAL',
                        'macd_signal': 0,
                        'macd_histogram': 0,
                        'volume': 0,
                        'avg_volume': 0
                    }
                }
            
            # DB에서 최신 모니터링 정보 조회 및 매매 신호 생성
            with self.db_manager.get_session() as session:
                fresh_monitoring_stock = session.query(MonitoringStock).filter(
                    MonitoringStock.id == stock_id
                ).first()
                if not fresh_monitoring_stock:
                    self.logger.warning(f"❌ {symbol} 모니터링 정보를 찾을 수 없음")
                    return
                
                # 매매 신호 생성 (타임아웃 적용)
                try:
                    signal_task = asyncio.create_task(
                        self._generate_trading_signal(
                            symbol, name, current_price, technical_data, fresh_monitoring_stock, chart_data
                        )
                    )
                    signal = await asyncio.wait_for(signal_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning(f"⚠️ {symbol} 매매 신호 생성 타임아웃 (5초) - 스킵")
                    signal = None
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 매매 신호 생성 실패: {e} - 스킵")
                    signal = None
            
                # 매매 신호 처리 (타임아웃 적용)
                if signal and signal.signal_type in ['BUY', 'SELL']:
                    try:
                        process_task = asyncio.create_task(
                            self._process_trading_signal(signal, fresh_monitoring_stock)
                        )
                        await asyncio.wait_for(process_task, timeout=10.0)
                    except asyncio.TimeoutError:
                        self.logger.warning(f"⚠️ {symbol} 매매 신호 처리 타임아웃 (10초)")
                    except Exception as e:
                        self.logger.warning(f"⚠️ {symbol} 매매 신호 처리 실패: {e}")
            
            self.logger.debug(f"✅ {symbol}({name}) 분석 완료 - 신호: {signal.signal_type if signal else 'NONE'}")
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 분석 실패: {e}")
            # 분석 실패해도 현재가는 DB에 업데이트 (최소한의 동작 보장)
            try:
                with self.db_manager.get_session() as session:
                    db_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.id == stock_id
                    ).first()
                    if db_stock:
                        db_stock.last_check_time = datetime.now()
                        session.commit()
            except:
                pass  # 이것도 실패하면 그냥 넘어감

    async def _get_chart_data(self, symbol: str) -> List[Any]:
        """차트 데이터 가져오기 (타임아웃 적용)"""
        try:
            # 최근 60일 일봉 데이터 요청
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            request = {
                'symbol': symbol,
                'period': 'D',
                'start_date': start_date.strftime('%Y%m%d'),
                'end_date': end_date.strftime('%Y%m%d')
            }
            
            # 차트 데이터 수집 (재시도 포함)
            chart_data = None
            for attempt in range(2):
                try:
                    chart_data = await asyncio.wait_for(
                        self.chart_data_collector._fetch_chart_data(request), 
                        timeout=10.0
                    )
                    if chart_data:
                        break
                except asyncio.TimeoutError:
                    if attempt == 0:
                        self.logger.debug(f"🔄 {symbol} 차트 데이터 재시도 중...")
                        await asyncio.sleep(0.5)
                    else:
                        self.logger.warning(f"시간초과 {symbol} 차트 데이터 조회 실패 - 스킵")
                        return []
                except Exception as e:
                    self.logger.warning(f"❌ {symbol} 차트 데이터 오류: {e}")
                    return []
            
            if not chart_data:
                self.logger.debug(f"📊 {symbol} 차트 데이터 없음")
                return []
            
            price_data_list = []
            
            for data in chart_data:
                price_data = PriceData(
                    timestamp=datetime.strptime(data.get('date', ''), '%Y%m%d'),
                    open=int(data.get('open', 0)),
                    high=int(data.get('high', 0)),
                    low=int(data.get('low', 0)),
                    close=int(data.get('close', 0)),
                    volume=int(data.get('volume', 0))
                )
                price_data_list.append(price_data)
            
            return price_data_list
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 차트 데이터 수집 실패: {e}")
            return []
    
    async def _generate_trading_signal(
        self, 
        symbol: str, 
        name: str,
        current_price: int, 
        technical_data: Dict,
        monitoring_stock: MonitoringStock,
        chart_data: List[PriceData] # Added chart_data
    ) -> Optional[TradingSignal]:
        """매매 신호 생성"""
        try:
            # KIS API를 통해 실제 보유 여부 확인
            try:
                holdings = await self.kis_collector.get_holdings()
                is_held = symbol in holdings and getattr(holdings.get(symbol), 'quantity', 0) > 0
            except Exception as e:
                self.logger.error(f"❌ {symbol} 보유 정보 조회 실패: {e}")
                is_held = False

            # 기술적 지표 추출 (실제 키 이름에 맞게 수정)
            indicators = technical_data.get('indicators', {})

            rsi = indicators.get('rsi', 50)
            ma5 = indicators.get('ma5', current_price)
            ma20 = indicators.get('ma20', current_price)
            volume = indicators.get('volume', 0)
            avg_volume = indicators.get('avg_volume', 0)

            # 신호들
            ma_signal = indicators.get('ma_signal', 'HOLD')
            macd_trend = indicators.get('macd_trend', 'NEUTRAL')
            macd_signal_val = indicators.get('macd_signal', 0)
            macd_histogram_val = indicators.get('macd_histogram', 0)

            # --- 캔들 패턴 분석 ---
            ohlcv_dicts = []
            for price_data_item in chart_data:
                ohlcv_dicts.append({
                    'open': price_data_item.open,
                    'high': price_data_item.high,
                    'low': price_data_item.low,
                    'close': price_data_item.close,
                    'volume': price_data_item.volume
                })
            
            pattern_analysis_result = self.pattern_detector.detect_patterns(
                stock_data={'symbol': symbol, 'name': name}, # Pass minimal stock_data
                symbol=symbol,
                name=name,
                ohlcv_data=ohlcv_dicts
            )
            
            detected_patterns = pattern_analysis_result.get('detected_patterns', [])
            pattern_overall_score = pattern_analysis_result.get('overall_score', 50.0)
            # --- 캔들 패턴 분석 끝 ---
            
            # 매수 조건 확인 (실제 지표에 맞게 수정)
            buy_conditions = []

            # 1. MA 신호가 매수
            if ma_signal == 'BUY':
                buy_conditions.append("MA_매수신호")

            # 2. 골든크로스 (5일 MA > 20일 MA)
            if ma5 > ma20 * 1.01:  # 1% 이상 상회
                buy_conditions.append("골든크로스")

            # 3. RSI 과매도 구간 반등 (범위 확대)
            if 30 <= rsi <= 45:  # 범위 확대
                buy_conditions.append("RSI_과매도반등")

            # 4. 거래량 급증 (조건 완화)
            if avg_volume > 0 and volume > avg_volume * 1.2:  # 1.5배 → 1.2배로 완화
                buy_conditions.append("거래량_급증")

            # 5. MACD 상승 추세
            if macd_trend == 'BULLISH':
                buy_conditions.append("MACD_상승추세")

            # --- 캔들 패턴 매수 조건 추가 ---
            for pattern in detected_patterns:
                if pattern.get('type') == 'bullish' and pattern.get('confidence', 0) >= 0.7:
                    buy_conditions.append(f"캔들패턴_{pattern['name']}")
            # --- 캔들 패턴 매수 조건 추가 끝 ---

            # --- MACD 매수 조건 추가 ---
            # MACD 히스토그램이 양수이고 상승 추세일 때
            if macd_histogram_val > 0 and macd_trend == 'BULLISH':
                buy_conditions.append("MACD_골든크로스")
            # --- MACD 매수 조건 추가 끝 ---
            
            # 매도 조건 확인
            sell_conditions = []

            # [BUG FIX] 실제 보유한 종목에 대해서만 매도 조건 검사
            if is_held:
                # 1. MA 신호가 매도
                if ma_signal == 'SELL':
                    sell_conditions.append("MA_매도신호")

                # 2. 데드크로스 (5일 MA < 20일 MA)
                if ma5 < ma20 * 0.99:  # 1% 이상 하회
                    sell_conditions.append("데드크로스")
                
                # 3. RSI 과매수 구간 (기준 75 → 70으로 하향)
                if rsi >= 70:
                    sell_conditions.append("RSI_과매수")
                
                # 4. 목표가 달성 - 현재 monitoring_stock에서 확인
                if monitoring_stock.target_price and current_price >= monitoring_stock.target_price:
                    sell_conditions.append("목표가_달성")
                
                # 5. 손절가 조건 - 현재가가 손절가 이하로 하락
                self.logger.debug(f"🔍 {symbol} 손절가 확인: 현재가 {current_price:,} vs 손절가 {monitoring_stock.stop_loss_price:,}" if monitoring_stock.stop_loss_price else f"🔍 {symbol} 손절가 없음")
                if monitoring_stock.stop_loss_price and current_price <= monitoring_stock.stop_loss_price:
                    sell_conditions.append("손절가_도달")
                    # 백그라운드 로그만 기록
                    pass  # 손절가 도달 메시지 제거

                # --- 캔들 패턴 매도 조건 추가 ---
                for pattern in detected_patterns:
                    if pattern.get('type') == 'bearish' and pattern.get('confidence', 0) >= 0.7:
                        sell_conditions.append(f"캔들패턴_{pattern['name']}")
                # --- 캔들 패턴 매도 조건 추가 끝 ---

                # --- MACD 매도 조건 추가 ---
                # MACD 히스토그램이 음수이고 하락 추세일 때
                if macd_histogram_val < 0 and macd_trend == 'BEARISH':
                    sell_conditions.append("MACD_데드크로스")
                # --- MACD 매도 조건 추가 끝 ---
            
            # 신호 결정
            signal_type = 'HOLD'
            confidence = 0.0
            reason = "조건 미충족"
            
            # 패턴 점수를 신뢰도에 반영
            pattern_confidence_boost = (pattern_overall_score - 50) / 100 * 0.2 # 50점 기준, 최대 0.2 가중
            
            # 손절가 조건을 최우선으로 처리 (매수보다 우선)
            if "손절가_도달" in sell_conditions:  # 손절가 도달시 즉시 매도
                signal_type = 'SELL'
                confidence = 0.99  # 최고 신뢰도로 즉시 매도
                reason = f"🚨긴급손절: {', '.join(sell_conditions)}"
                # 백그라운드 로그만 기록
                pass  # 손절가 도달 즉시 매도 실행 메시지 제거
                
                # 추가 손절 조건 체크 (수익률 기준)
                try:
                    # KIS에서 보유종목 정보 조회
                    holdings = await self.kis_collector.get_holdings()
                    if symbol in holdings:
                        holding_info = holdings[symbol]
                        profit_rate = holding_info.get('profit_rate', 0.0)
                        
                        # -5% 이하 손실시 강제 손절 조건 추가
                        if profit_rate <= -5.0:
                            self.logger.error(f"⚠️ {symbol} 심각한 손실 감지: {profit_rate:.2f}% - 강제 손절 실행")
                            confidence = 1.0  # 100% 신뢰도로 강제 매도
                            reason = f"🚨강제손절: 손실률 {profit_rate:.2f}%"
                        
                except Exception as e:
                    self.logger.error(f"❌ {symbol} 보유종목 손실률 확인 실패: {e}")
                
            elif "목표가_달성" in sell_conditions:  # 목표가 달성시 수익 실현
                signal_type = 'SELL'
                confidence = 0.85  # 높은 신뢰도로 수익 실현
                reason = f"수익실현: {', '.join(sell_conditions)}"
                self.logger.info(f"💰 {symbol} 수익실현 신호 발생: {reason}")

            else:
                # 기술적 점수 추출
                technical_score = technical_data.get('technical_score', 50)

                # 70점 이상 종목은 1개 조건만으로도 매수 (강화된 매수 조건)
                if (len(buy_conditions) >= 1 and technical_score >= 70) or len(buy_conditions) >= 2:
                    signal_type = 'BUY'
                    confidence = min(0.9, len(buy_conditions) * 0.3 + 0.5 + pattern_confidence_boost)  # composite_confidence 대신 기본값 사용
                    reason = f"매수조건: {', '.join(buy_conditions)}"
                    if technical_score >= 70:
                        reason += f" (고점수:{technical_score:.0f}점)"

                elif len(sell_conditions) >= 2:  # 2개 이상 조건 충족시 매도
                    signal_type = 'SELL'
                    confidence = min(0.9, len(sell_conditions) * 0.3 + 0.5 + pattern_confidence_boost)  # composite_confidence 대신 기본값 사용
                    reason = f"매도조건: {', '.join(sell_conditions)}"
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                reason=reason,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 신호 생성 실패: {e}")
            return None
    
    async def _process_trading_signal(self, signal: TradingSignal, monitoring_stock: MonitoringStock):
        """매매 신호 처리"""
        try:
            # 백그라운드 로그만 기록
            pass  # 신호 처리 시작 메시지 제거
            # 손절 신호는 낮은 신뢰도에도 실행 (긴급상황)
            if signal.signal_type == 'SELL' and ('손절' in signal.reason or '강제' in signal.reason):
                # 백그라운드 로그만 기록
                pass  # 긴급 매도 신호 메시지 제거
            elif signal.confidence < 0.7:  # 신뢰도 임계값을 원래대로 복구
                self.logger.debug(f"📊 {signal.symbol} 신뢰도 부족 ({signal.confidence:.2f}) - 신호 무시")
                return
            
            # 매매 가능한지 확인하고 자동 활성화
            if not self.executor.is_trading_enabled():
                self.logger.warning("⚠️ 매매 기능이 비활성화되어 있습니다. 자동으로 활성화합니다.")
                try:
                    if hasattr(self.executor, 'enable_trading'):
                        self.executor.enable_trading()
                        self.logger.info("✅ 매매 기능이 자동으로 활성화되었습니다.")
                    else:
                        self.logger.error("❌ 매매 기능 활성화 메서드를 찾을 수 없습니다.")
                        return
                except Exception as e:
                    self.logger.error(f"❌ 매매 기능 자동 활성화 실패: {e}")
                    return
            
            if signal.signal_type == 'BUY':
                await self._execute_buy_order(signal, monitoring_stock)
            elif signal.signal_type == 'SELL':
                await self._execute_sell_order(signal, monitoring_stock)
            
        except Exception as e:
            self.logger.error(f"❌ {signal.symbol} 매매 신호 처리 실패: {e}")
    
    async def _execute_buy_order(self, signal: TradingSignal, monitoring_stock: MonitoringStock):
        """매수 주문 실행 및 매수 정보 기록"""
        try:
            await self.executor.update_dynamic_limits()
            symbol = signal.symbol
            current_price = signal.price
            
            portfolio = await self.executor.get_portfolio_position(symbol)
            if portfolio and getattr(portfolio, 'quantity', 0) > 0:
                # 백그라운드 로그만 기록
                pass  # 이미 보유중 매수 스킵 메시지 제거
                return
            
            account_info = await self.executor.get_account_info()
            if not account_info:
                self.logger.error("❌ 계좌 정보 조회 실패")
                return
            
            available_cash = account_info.get('available_cash', 0)
            max_position_value = self.executor._max_position_size
            
            quantity = max_position_value // current_price
            if quantity <= 0:
                # 백그라운드 로그만 기록
                pass  # 매수 자금 부족 메시지 제거
                return
            
            # 백그라운드 로그만 기록
            pass  # 매수 주문 실행 메시지 제거
            # 백그라운드 로그만 기록
            pass  # 사유 메시지 제거
            
            result = await self.executor.execute_buy_order(
                symbol=symbol,
                quantity=quantity,
                price=current_price,
                order_type=OrderType.LIMIT
            )
            
            if result and result.get('success'):
                buy_trade = result.get('trade_object')
                self.logger.info(f"✅ {symbol} 매수 주문 성공: {result.get('order_id')}")
                
                # 매수 성공 시, MonitoringStock에 buy_trade_id 기록
                if buy_trade:
                    with self.db_manager.get_session() as session:
                        db_stock = session.query(MonitoringStock).filter(
                            MonitoringStock.id == monitoring_stock.id
                        ).first()
                        if db_stock:
                            db_stock.buy_trade_id = buy_trade.id
                            session.commit()
                            self.logger.info(f"🔗 {symbol}의 매수 정보(Trade ID: {buy_trade.id})를 모니터링에 연결했습니다.")
                        else:
                            self.logger.error(f"❌ {symbol}의 모니터링 정보를 찾을 수 없어 매수 정보를 연결하지 못했습니다.")
            else:
                self.logger.error(f"❌ {symbol} 매수 주문 실패: {result.get('message') if result else 'Unknown error'}")
            
        except Exception as e:
            self.logger.error(f"❌ {signal.symbol} 매수 주문 실행 실패: {e}")
    
    async def _execute_sell_order(self, signal: TradingSignal, monitoring_stock: MonitoringStock):
        """매도 주문 실행 및 거래 기록 생성"""
        try:
            symbol = signal.symbol
            current_price = signal.price
            
            # 실제 KIS API에서 보유 종목 직접 조회 (손절 확실히 실행)
            try:
                holdings = await self.kis_collector.get_holdings()
                if not holdings or symbol not in holdings:
                    # 정말 보유 종목이 없는 경우에만 스킵
                    return
                
                portfolio = holdings[symbol]
                if getattr(portfolio, 'quantity', 0) <= 0:
                    return
            except Exception as e:
                self.logger.error(f"보유 종목 조회 실패: {e}")
                return
            
            quantity = getattr(portfolio, 'quantity', 0)
            avg_price = getattr(portfolio, 'avg_price', 0)
            
            profit_loss = (current_price - avg_price) * quantity
            profit_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
            
            # 백그라운드 로그만 기록
            pass  # 매도 주문 실행 메시지 제거
            # 백그라운드 로그만 기록
            pass  # 예상 손익 메시지 제거
            # 백그라운드 로그만 기록
            pass  # 사유 메시지 제거
            
            result = await self.executor.sell_stock(
                symbol=symbol,
                quantity=quantity,
                price=current_price,
                order_type='LIMIT'
            )
            
            if result and result.get('success'):
                sell_trade = result.get('trade_object')
                self.logger.info(f"✅ {symbol} 매도 주문 성공: {result.get('order_id')}")
                
                # 거래 기록 생성
                if sell_trade:
                    await self._create_trade_history(monitoring_stock.id, sell_trade)
                
                # 매도 완료 후 모니터링 완료 처리
                with self.db_manager.get_session() as session:
                    db_stock = session.query(MonitoringStock).filter(
                        MonitoringStock.id == monitoring_stock.id
                    ).first()
                    if db_stock:
                        db_stock.status = MonitoringStatus.COMPLETED.value
                        db_stock.completed_time = datetime.now()
                        db_stock.removal_reason = "sell_completed"
                        db_stock.removal_details = f"매도 완료: {signal.reason}"
                        session.commit()
                        self.logger.info(f"📊 {symbol} 모니터링 완료 처리")
            else:
                self.logger.error(f"❌ {symbol} 매도 주문 실패: {result.get('message') if result else 'Unknown error'}")
            
        except Exception as e:
            self.logger.error(f"❌ {signal.symbol} 매도 주문 실행 실패: {e}")

    async def _create_trade_history(self, monitoring_stock_id: int, sell_trade: 'Trade'):
        """거래 기록(TradeHistory) 생성"""
        from database.models import Trade, TradeHistory, WinLossStatus
        try:
            with self.db_manager.get_session() as session:
                # 1. 모니터링 정보 조회
                mon_stock = session.query(MonitoringStock).filter(MonitoringStock.id == monitoring_stock_id).first()
                if not mon_stock:
                    self.logger.error(f"[History] 모니터링 정보(ID: {monitoring_stock_id})를 찾지 못해 거래 기록 생성 실패")
                    return

                if not mon_stock.buy_trade_id:
                    self.logger.warning(f"[History] {mon_stock.symbol}에 연결된 매수 정보(buy_trade_id)가 없어 기록을 생성할 수 없습니다.")
                    return

                # 2. 매수/매도 거래 정보 조회
                buy_trade = session.query(Trade).filter(Trade.id == mon_stock.buy_trade_id).first()
                if not buy_trade:
                    self.logger.error(f"[History] 매수 거래(ID: {mon_stock.buy_trade_id})를 찾지 못해 기록 생성 실패")
                    return

                # 3. TradeHistory 객체 생성 및 데이터 계산
                pnl = sell_trade.executed_price - buy_trade.executed_price
                pnl_rate = (pnl / buy_trade.executed_price) * 100 if buy_trade.executed_price > 0 else 0
                holding_period = sell_trade.execution_time - buy_trade.execution_time

                status = WinLossStatus.DRAW
                if pnl_rate > 0:
                    status = WinLossStatus.WIN
                elif pnl_rate < 0:
                    status = WinLossStatus.LOSS

                history = TradeHistory(
                    stock_id=mon_stock.stock_id,
                    strategy_name=mon_stock.strategy_name,
                    buy_trade_id=buy_trade.id,
                    sell_trade_id=sell_trade.id,
                    buy_date=buy_trade.execution_time,
                    sell_date=sell_trade.execution_time,
                    buy_price=buy_trade.executed_price,
                    sell_price=sell_trade.executed_price,
                    quantity=sell_trade.executed_quantity,
                    profit_loss=pnl * sell_trade.executed_quantity,
                    profit_loss_rate=pnl_rate,
                    holding_period_days=holding_period.days,
                    status=status
                )

                session.add(history)
                session.commit()
                self.logger.info(f"📈 거래 기록 생성 완료: {mon_stock.symbol} ({mon_stock.strategy_name}) - 수익률: {pnl_rate:.2f}% ")

        except Exception as e:
            self.logger.error(f"❌ 거래 기록 생성 중 심각한 오류 발생: {e}")
    
    async def add_buy_recommendation(self, symbol: str, name: str, strategy_name: str,
                                  target_price: Optional[int] = None, stop_loss_price: Optional[int] = None,
                                  monitoring_type: MonitoringType = MonitoringType.TRADING) -> bool:
        """Buy 추천 종목을 DB 모니터링 리스트에 추가 (Stock 테이블 연동 수정)"""
        try:
            # DB 매니저 유효성 검사
            if not self.db_manager:
                self.logger.error("❌ DB 매니저가 초기화되지 않았습니다. 모니터링 추가를 건너뜁니다.")
                return False
                
            with self.db_manager.get_session() as session:
                # --- Start of Fix ---
                # 1. stocks 테이블에 종목 정보가 있는지 확인하고, 없으면 추가
                from database.models import Stock
                stock_entry = session.query(Stock).filter(Stock.symbol == symbol).first()
                actual_name = name

                if not stock_entry:
                    self.logger.info(f"ℹ️ '{symbol}'에 대한 정보가 'stocks' 테이블에 없습니다. KIS API에서 조회하여 추가합니다.")
                    try:
                        stock_info = await self.kis_collector.get_stock_info(symbol)
                        if stock_info:
                            actual_name = stock_info.name
                            new_stock = Stock(
                                symbol=stock_info.symbol,
                                name=stock_info.name,
                                market=stock_info.market.value,
                                current_price=stock_info.current_price,
                                market_cap=int(stock_info.market_cap * 1_000_000_000), # 억 단위 -> 원 단위
                                pe_ratio=stock_info.pe_ratio,
                                pbr=stock_info.pbr,
                                is_active=True
                            )
                            session.add(new_stock)
                            self.logger.info(f"✅ '{symbol}'({actual_name}) 정보를 'stocks' 테이블에 추가했습니다.")
                        else:
                            self.logger.warning(f"⚠️ KIS API get_stock_info()에서 '{symbol}' 정보를 조회하지 못했습니다. 고급 종목명 추출을 시도합니다.")
                            # KIS API get_stock_info() 실패 시 현재가 조회를 통한 고급 종목명 추출 시도
                            try:
                                # 현재가 조회 API를 직접 호출하여 응답 데이터에서 종목명 추출
                                result = await self.kis_collector._make_api_request(
                                    method="GET",
                                    endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
                                    params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
                                    tr_id="FHKST01010100"
                                )
                                
                                output = result.get('output', {})
                                if output:
                                    # KIS collector의 고급 종목명 추출 로직 활용
                                    extracted_name = self.kis_collector._extract_stock_name(output, symbol)
                                    
                                    # 임시 이름이 아닌 경우에만 사용
                                    if extracted_name and not extracted_name.startswith('종목'):
                                        actual_name = extracted_name
                                        self.logger.info(f"✅ '{symbol}' 고급 종목명 추출 성공: '{actual_name}'")
                                        
                                        # 기본 정보로 Stock 추가
                                        current_price = self.kis_collector._safe_int_parse(output.get('stck_prpr', '0'))
                                        market_div = output.get('mrkt_div_cd', '')
                                        market_value = "KOSPI" if market_div == "J" else "KOSDAQ"
                                        
                                        new_stock = Stock(
                                            symbol=symbol,
                                            name=actual_name,
                                            market=market_value,
                                            current_price=current_price,
                                            market_cap=0,  # 기본값
                                            pe_ratio=None,
                                            pbr=None,
                                            is_active=True
                                        )
                                        session.add(new_stock)
                                        self.logger.info(f"✅ '{symbol}'({actual_name}) 고급 추출로 'stocks' 테이블에 추가했습니다.")
                                    else:
                                        self.logger.warning(f"⚠️ '{symbol}' 고급 종목명 추출도 실패 (임시명: {extracted_name})")
                                else:
                                    self.logger.warning(f"⚠️ '{symbol}' 현재가 API 응답 데이터가 없습니다.")
                            except Exception as fallback_error:
                                self.logger.error(f"❌ '{symbol}' 고급 종목명 추출 실패: {fallback_error}")
                    except Exception as e:
                        self.logger.error(f"❌ KIS API 조회 또는 'stocks' 테이블 추가 중 오류 발생: {e}")

                else:
                    actual_name = stock_entry.name # DB에 있는 이름을 사용

                # --- End of Fix ---

                # 2. 이미 모니터링 중인지 확인
                existing = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status.in_([MonitoringStatus.ACTIVE.value, MonitoringStatus.PAUSED.value])
                ).first()

                if existing:
                    self.logger.warning(f"⚠️ {symbol}({actual_name})은 이미 모니터링 중입니다")
                    return False

                # 3. 현재 활성 포지션 수 확인 및 리밸런싱 (기존 로직 유지)
                active_count = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).count()

                if active_count >= self.max_positions:
                    self.logger.warning(f"⚠️ 최대 포지션 수 초과: {active_count}/{self.max_positions}")
                    # 스마트 리밸런서 로직은 그대로 유지
                    if hasattr(self, 'smart_rebalancer') and self.smart_rebalancer:
                        candidate_data = {'symbol': symbol, 'name': actual_name, 'strategy_name': strategy_name}
                        rebalance_success = await self.smart_rebalancer.add_candidate_and_rebalance(candidate_data)
                        if rebalance_success:
                            self.logger.info(f"✅ 스마트 리밸런싱 성공: {symbol}({actual_name}) 추가됨")
                            return True
                        else:
                            self.logger.warning(f"⚠️ 스마트 리밸런싱 실패: {symbol}({actual_name}) 점수가 기존 종목보다 낮음")
                            return False
                    return False

                # 4. 새 모니터링 종목 생성
                new_monitoring = MonitoringStock(
                    symbol=symbol,
                    name=actual_name,
                    status=MonitoringStatus.ACTIVE.value,
                    strategy_name=strategy_name,
                    target_price=target_price,
                    stop_loss_price=stop_loss_price,
                    monitoring_type=monitoring_type,
                    recommendation_time=datetime.now()
                )
                session.add(new_monitoring)
                session.commit()

                # 5. 현재가 및 손절가 업데이트 (기존 로직 유지)
                try:
                    current_price = await self.kis_collector.get_current_price(symbol)
                    if current_price:
                        if not new_monitoring.stop_loss_price:
                            calculated_stop_loss = self.calculate_stop_loss_price(current_price, strategy_name)
                            if calculated_stop_loss:
                                new_monitoring.stop_loss_price = calculated_stop_loss
                                self.logger.info(f"💡 {symbol} 초기 손절가 설정: {calculated_stop_loss:,}원")
                        session.commit()
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 현재가/손절가 업데이트 실패: {e}")

                self.logger.info(f"📋 모니터링 추가: {symbol}({actual_name}) - {strategy_name} 전략")
                return True

        except Exception as e:
            self.logger.error(f"❌ {symbol}({name}) 모니터링 추가 실패: {e}")
            return False
    
    async def remove_monitoring(self, symbol: str) -> bool:
        """DB 모니터링에서 종목 제거"""
        try:
            # DB 매니저 유효성 검사
            if not self.db_manager:
                self.logger.error("❌ DB 매니저가 초기화되지 않았습니다. 모니터링 제거를 건너뜁니다.")
                return False
                
            with self.db_manager.get_session() as session:
                monitoring_stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).first()
                
                if not monitoring_stock:
                    self.logger.warning(f"⚠️ {symbol}은 모니터링 중이 아닙니다")
                    return False
                
                # 모니터링 완료 처리
                monitoring_stock.status = MonitoringStatus.REMOVED.value
                monitoring_stock.removed_at = datetime.now()
                monitoring_stock.removal_reason = "user_request"
                monitoring_stock.removal_details = "사용자 요청으로 제거"
                session.commit()
                
                self.logger.info(f"🗑️ 모니터링 제거: {symbol}({monitoring_stock.name})")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} 모니터링 제거 실패: {e}")
            return False
    
    async def import_portfolio_to_monitoring(self) -> Dict[str, Any]:
        """계좌의 보유종목을 가져와서 모니터링에 추가"""
        try:
            # 백그라운드 로그만 기록
            pass  # 포트폴리오 가져오기 시작 메시지 제거
            
            # 계좌 보유종목 조회 (직접 KIS collector 사용)
            try:
                holdings_dict = await self.kis_collector.get_holdings()
                if holdings_dict:
                    portfolio_holdings = list(holdings_dict.values())
                    # 백그라운드 로그만 기록
                    pass  # KIS API 보유종목 조회 메시지 제거
                else:
                    portfolio_holdings = []
                    self.logger.warning("⚠️ KIS API에서 보유종목 조회 결과 없음")
            except Exception as e:
                self.logger.error(f"❌ KIS API 보유종목 조회 실패: {e}")
                portfolio_holdings = []
            if not portfolio_holdings:
                self.logger.warning("❌ 보유종목 조회 실패 또는 보유종목 없음")
                return {
                    'success': False,
                    'message': '보유종목이 없거나 조회에 실패했습니다',
                    'added_count': 0,
                    'skipped_count': 0,
                    'failed_count': 0
                }
            
            # 백그라운드 로그만 기록
            pass  # 보유종목 발견 메시지 제거
            
            # 결과 추적
            added_count = 0
            skipped_count = 0
            failed_count = 0
            results = []
            
            # 각 보유종목을 모니터링에 추가
            for holding in portfolio_holdings:
                try:
                    symbol = holding.get('symbol', '')
                    name = holding.get('name', '')
                    quantity = holding.get('quantity', 0)
                    avg_price = holding.get('avg_price', 0)
                    current_price = holding.get('current_price', 0)
                    
                    if not symbol or quantity <= 0:
                        self.logger.debug(f"⚠️ 유효하지 않은 보유종목: {symbol}")
                        skipped_count += 1
                        continue
                    
                    # 이미 모니터링 중인지 확인
                    with self.db_manager.get_session() as session:
                        existing = session.query(MonitoringStock).filter(
                            MonitoringStock.symbol == symbol,
                            MonitoringStock.status.in_([
                                MonitoringStatus.ACTIVE.value,
                                MonitoringStatus.PAUSED.value
                            ])
                        ).first()
                        
                        if existing:
                            self.logger.debug(f"⚠️ {symbol}({name})은 이미 모니터링 중입니다")
                            skipped_count += 1
                            results.append({
                                'symbol': symbol,
                                'name': name,
                                'status': 'skipped',
                                'reason': '이미 모니터링 중'
                            })
                            continue
                    
                    # 목표가와 손절가 자동 계산
                    target_price = None
                    stop_loss_price = None
                    
                    # 설정에서 수익률과 손절률 로드
                    settings = self._load_trading_settings()
                    profit_ratio = 1 + (settings['target_profit_rate'] / 100)
                    loss_ratio = 1 - (settings['stop_loss_rate'] / 100)
                    
                    if avg_price > 0:
                        # 목표가: 평균단가 + 설정된 수익률
                        target_price = int(avg_price * profit_ratio)
                        # 손절가: 평균단가 - 설정된 손절률
                        stop_loss_price = int(avg_price * loss_ratio)
                    elif current_price > 0:
                        # 현재가 기준으로 계산
                        target_price = int(current_price * profit_ratio)
                        stop_loss_price = int(current_price * loss_ratio)
                    
                    # 모니터링에 추가
                    success = await self.add_buy_recommendation(
                        symbol=symbol,
                        name=name,
                        strategy_name="portfolio_import",
                        target_price=target_price,
                        stop_loss_price=stop_loss_price,
                        monitoring_type=MonitoringType.PORTFOLIO
                    )
                    
                    if success:
                        added_count += 1
                        self.logger.info(f"✅ {symbol}({name}) 모니터링 추가 완료")
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'status': 'added',
                            'avg_price': avg_price,
                            'current_price': current_price,
                            'target_price': target_price,
                            'stop_loss_price': stop_loss_price,
                            'quantity': quantity
                        })
                    else:
                        failed_count += 1
                        self.logger.warning(f"❌ {symbol}({name}) 모니터링 추가 실패")
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'status': 'failed',
                            'reason': '추가 실패'
                        })
                        
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"❌ 보유종목 처리 오류: {e}")
                    results.append({
                        'symbol': holding.get('symbol', 'Unknown'),
                        'name': holding.get('name', 'Unknown'),
                        'status': 'failed',
                        'reason': str(e)
                    })
            
            # 결과 요약
            result_summary = {
                'success': True,
                'message': f'포트폴리오 가져오기 완료: {added_count}개 추가, {skipped_count}개 건너뜀, {failed_count}개 실패',
                'added_count': added_count,
                'skipped_count': skipped_count,
                'failed_count': failed_count,
                'total_processed': len(portfolio_holdings),
                'results': results
            }
            
            # 백그라운드 로그만 기록
            pass  # 포트폴리오 가져오기 완료 메시지 제거
            return result_summary
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 가져오기 실패: {e}")
            return {
                'success': False,
                'message': f'포트폴리오 가져오기 실패: {str(e)}',
                'added_count': 0,
                'skipped_count': 0,
                'failed_count': 0
            }
    
    async def get_monitoring_status(self) -> Dict[str, Any]: # async로 변경
        """모니터링 상태 정보 반환"""
        try:
            with self.db_manager.get_session() as session:
                trading_stocks = session.query(MonitoringStock).filter(
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).all()
                
                status_info = {
                    'is_monitoring': self.is_monitoring,
                    'trading_enabled': self.executor.is_trading_enabled(),
                    'monitoring_count': len(trading_stocks),
                    'active_count': len(trading_stocks),
                    'monitoring_stocks': {}
                }
                
                for stock in trading_stocks:
                    # 실시간 현재가 조회 (KIS API 호출만 사용, 폴백 없음)
                    current_price = await self.kis_collector.get_current_price(stock.symbol)
                    if not current_price or current_price <= 0:
                        continue  # API 실패시 해당 종목 건너뛰기
                    
                    # 포트폴리오 정보 조회
                    portfolio_position = await self.executor.get_portfolio_position(stock.symbol)
                    
                    buy_price = None
                    profit_rate = 0.0
                    actual_stop_loss_price = stock.stop_loss_price # 기본값은 모니터링 스톡의 손절가

                    if portfolio_position:
                        buy_price = portfolio_position.get('avg_price', 0)
                        
                        # 실시간 현재가로 수익률 계산
                        if buy_price is not None and buy_price > 0 and current_price is not None and current_price > 0:
                            profit_rate = ((current_price - buy_price) / buy_price) * 100
                        
                        # 포트폴리오에 손절가 정보가 있다면 사용 (없으면 MonitoringStock의 값 사용)
                        if portfolio_position.get('stop_loss_price') is not None:
                            actual_stop_loss_price = portfolio_position.get('stop_loss_price')

                    status_info['monitoring_stocks'][stock.symbol] = {
                        'name': stock.name,
                        'strategy': stock.strategy_name,
                        'current_price': current_price,  # 실시간 현재가 사용
                        'target_price': stock.target_price,
                        'stop_loss_price': actual_stop_loss_price,
                        'buy_price': buy_price,
                        'profit_rate': round(profit_rate, 2),  # 실시간 현재가로 계산된 수익률
                        'added_time': stock.recommendation_time.strftime('%m-%d %H:%M') if stock.recommendation_time else None,
                        'last_check_time': stock.last_check_time.strftime('%m-%d %H:%M') if stock.last_check_time else None
                    }
                
                return status_info
                
        except Exception as e:
            self.logger.error(f"❌ 모니터링 상태 조회 실패: {e}")
            return {
                'is_monitoring': False,
                'trading_enabled': False,
                'monitoring_count': 0,
                'active_count': 0,
                'monitoring_stocks': {}
            }

    async def get_active_positions_count(self) -> int:
        """활성 포지션 수 조회"""
        try:
            with self.db_manager.get_session() as session:
                count = session.query(MonitoringStock).filter(
                    MonitoringStock.monitoring_type == MonitoringType.TRADING,
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).count()
                return count
        except Exception as e:
            self.logger.error(f"❌ 활성 포지션 수 조회 실패: {e}")
            return 0
    
    def calculate_stop_loss_price(self, current_price: int, strategy_name: str = None) -> int:
        """알고리즘 기반 손절가 계산"""
        try:
            if not current_price or current_price <= 0:
                return None
            
            # 설정 파일에서 손절 비율 로드
            settings = self._load_trading_settings()
            default_stop_loss_ratio = settings['stop_loss_rate'] / 100  # 백분율을 비율로 변환
            
            # 전략별 맞춤 손절가 설정
            strategy_stop_loss_ratios = {
                'momentum': 0.03,      # 모멘텀: 3% (더 큰 변동성 허용)
                'reversal': 0.025,     # 반전: 2.5%
                'breakout': 0.035,     # 돌파: 3.5% (가장 큰 변동성 허용)
                'support_resistance': 0.02,  # 지지/저항: 2%
                'pattern': 0.025,      # 패턴: 2.5%
                'volume': 0.03,        # 거래량: 3%
                'default': 0.02        # 기본: 2%
            }
            
            # 전략에 따른 손절 비율 결정
            stop_loss_ratio = strategy_stop_loss_ratios.get(
                strategy_name.lower() if strategy_name else 'default',
                default_stop_loss_ratio
            )
            
            # 손절가 계산 (현재가에서 손절 비율만큼 하락)
            stop_loss_price = int(current_price * (1 - stop_loss_ratio))
            
            # 최소 손절가 보장 (현재가의 90% 이상은 보장)
            min_stop_loss = int(current_price * 0.9)
            stop_loss_price = max(stop_loss_price, min_stop_loss)
            
            # 가격 단위 조정 (100원 단위로 반올림)
            stop_loss_price = round(stop_loss_price / 100) * 100
            
            self.logger.debug(f"💡 손절가 계산: {current_price:,}원 → {stop_loss_price:,}원 ({stop_loss_ratio*100:.1f}% 손절)")
            return stop_loss_price
            
        except Exception as e:
            self.logger.error(f"❌ 손절가 계산 실패: {e}")
            return None
    
    # 현재가 일괄 업데이트 메서드 제거됨 - 실시간 API 호출만 사용
    
    async def _execute_emergency_sell_order(self, symbol: str, current_price: float, reason: str = "stop_loss", holding_info: dict = None):
        """응급 매도 주문 실행 (손절가 도달 시) - 강화된 오류 처리 및 재시도 로직"""
        max_retries = 3
        retry_delay = 1  # 1초 대기
        
        for attempt in range(max_retries):
            try:
                self.logger.warning(f"🚨 {symbol} 응급 매도 주문 시작: {reason} (시도 {attempt + 1}/{max_retries})")
                
                # 1. KIS API 연결 상태 확인 
                if not self.kis_collector:
                    self.logger.error(f"❌ {symbol} KIS API 연결 없음")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return False
                
                # 2. 보유 정보 확인 (안전한 속성 접근)
                quantity = 0
                avg_price = 0
                
                if holding_info:
                    # 안전한 속성 접근 - StockData 객체와 딕셔너리 모두 지원
                    try:
                        if hasattr(holding_info, 'quantity'):
                            quantity = holding_info.quantity
                        elif isinstance(holding_info, dict):
                            quantity = holding_info.get('quantity', 0)
                        else:
                            quantity = getattr(holding_info, 'quantity', 0)
                            
                        if hasattr(holding_info, 'avg_price'):
                            avg_price = holding_info.avg_price
                        elif isinstance(holding_info, dict):
                            avg_price = holding_info.get('avg_price', 0)
                        else:
                            avg_price = getattr(holding_info, 'avg_price', 0)
                    except Exception as attr_error:
                        self.logger.error(f"⚠️ {symbol} 보유정보 속성 접근 오류: {attr_error}")
                        # 재시도를 위해 API에서 다시 조회
                        holding_info = None
                
                if not holding_info or quantity <= 0:
                    # KIS API에서 실시간 보유 정보 재조회
                    try:
                        holdings = await asyncio.wait_for(self.kis_collector.get_holdings(), timeout=10.0)
                        if holdings and symbol in holdings:
                            holding = holdings[symbol]
                            # 안전한 속성 접근
                            if hasattr(holding, 'quantity'):
                                quantity = holding.quantity
                                avg_price = holding.avg_price
                            else:
                                quantity = getattr(holding, 'quantity', 0)
                                avg_price = getattr(holding, 'avg_price', 0)
                        else:
                            self.logger.warning(f"⚠️ {symbol} KIS API에서 보유 종목을 찾을 수 없음")
                    except asyncio.TimeoutError:
                        self.logger.error(f"❌ {symbol} KIS API 타임아웃 (10초)")
                    except Exception as api_error:
                        self.logger.error(f"❌ {symbol} KIS API 호출 실패: {api_error}")
                
                if quantity <= 0:
                    self.logger.warning(f"⚠️ {symbol} 보유 수량 없음 (수량: {quantity}) - 매도 불가")
                    return False
                
                # 3. 손익 계산
                profit_loss = (current_price - avg_price) * quantity if avg_price > 0 else 0
                profit_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                
                self.logger.error(f"🚨 {symbol} 긴급 매도 실행:")
                self.logger.error(f"   📊 수량: {quantity:,}주, 평단가: {avg_price:,}원")
                self.logger.error(f"   📈 현재가: {current_price:,}원, 예상 손익: {profit_loss:+,.0f}원 ({profit_rate:+.1f}%)")
                self.logger.error(f"   🎯 사유: {reason}")
                
                # 4. Executor 연결 상태 확인
                if not hasattr(self, 'executor') or not self.executor:
                    self.logger.error(f"❌ {symbol} TradingExecutor 없음")
                    return False
                
                # 5. 매도 주문 실행 (강화된 오류 처리)
                try:
                    result = await asyncio.wait_for(
                        self.executor.sell_stock(
                            symbol=symbol,
                            quantity=quantity,
                            price=None,  # 시장가 주문
                            order_type='MARKET'  # 시장가로 즉시 매도
                        ),
                        timeout=15.0  # 15초 타임아웃
                    )
                    
                    if result and result.get('success'):
                        self.logger.error(f"✅ {symbol} 응급 매도 주문 성공!")
                        self.logger.error(f"   📋 주문번호: {result.get('order_id')}")
                        self.logger.error(f"   💰 예상 손익: {profit_loss:+,.0f}원 ({profit_rate:+.1f}%)")
                        
                        # 매도 완료 후 모니터링 상태 업데이트
                        try:
                            await self._update_monitoring_after_emergency_sell(symbol, reason, result)
                        except Exception as update_error:
                            self.logger.error(f"⚠️ {symbol} 모니터링 상태 업데이트 실패: {update_error}")
                        
                        return True
                    else:
                        error_msg = result.get('message', 'Unknown error') if result else 'No response from executor'
                        self.logger.error(f"❌ {symbol} 응급 매도 주문 실패: {error_msg}")
                        
                        # 특정 오류의 경우 재시도하지 않음
                        if 'KIS API 연결 필요' in error_msg or 'API 연결' in error_msg:
                            self.logger.error(f"💡 {symbol} API 연결 문제 감지 - 재시도 중")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay * (attempt + 1))  # 점진적 지연
                                continue
                        return False
                        
                except asyncio.TimeoutError:
                    self.logger.error(f"❌ {symbol} 매도 주문 타임아웃 (15초)")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return False
                    
                except Exception as sell_error:
                    self.logger.error(f"❌ {symbol} 매도 주문 실행 중 오류: {sell_error}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return False
                
            except Exception as e:
                self.logger.error(f"❌ {symbol} 응급 매도 처리 중 심각한 오류 (시도 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"🔄 {symbol} {retry_delay}초 후 재시도...")
                    await asyncio.sleep(retry_delay)
                    continue
                
        # 모든 재시도 실패
        self.logger.error(f"💀 {symbol} {max_retries}회 시도 후 응급 매도 완전 실패")
        return False
    
    async def _update_monitoring_after_emergency_sell(self, symbol: str, reason: str, sell_result: Dict):
        """응급 매도 후 모니터링 상태 업데이트"""
        try:
            with self.db_manager.get_session() as session:
                monitoring_stock = session.query(MonitoringStock).filter(
                    MonitoringStock.symbol == symbol,
                    MonitoringStock.status == MonitoringStatus.ACTIVE
                ).first()

                if monitoring_stock:
                    # 모니터링 완료 처리
                    monitoring_stock.status = MonitoringStatus.COMPLETED.value
                    monitoring_stock.completed_time = datetime.now()
                    monitoring_stock.removal_reason = "emergency_sell"
                    monitoring_stock.removal_details = f"응급 매도 완료: {reason} (주문번호: {sell_result.get('order_id', 'N/A')})"
                    session.commit()

                    self.logger.info(f"📊 {symbol} 응급 매도 후 모니터링 완료 처리")
                else:
                    self.logger.warning(f"⚠️ {symbol} 모니터링 정보를 찾을 수 없음")

        except Exception as e:
            self.logger.error(f"❌ {symbol} 응급 매도 후 모니터링 업데이트 실패: {e}")

    async def get_available_balance(self) -> int:
        """가용 자금 조회"""
        try:
            account_info = await self.executor.get_account_info()
            if account_info:
                available_cash = account_info.get('available_cash', 0)
                self.logger.debug(f"💰 가용 자금 조회: {available_cash:,}원")
                return available_cash
            else:
                self.logger.error("❌ 계좌 정보 조회 실패")
                return 0
        except Exception as e:
            self.logger.error(f"❌ 가용 자금 조회 실패: {e}")
            return 0

    async def place_buy_order(self, symbol: str, amount: int) -> Dict[str, Any]:
        """자동 매수 주문 실행"""
        try:
            # 현재가 조회
            current_price = await self.kis_collector.get_current_price(symbol)
            if not current_price:
                return {"success": False, "message": "현재가 조회 실패"}

            # 매수 수량 계산
            quantity = amount // current_price
            if quantity <= 0:
                return {"success": False, "message": "매수 수량 부족"}

            # 매수 주문 실행
            result = await self.executor.execute_buy_order(
                symbol=symbol,
                quantity=quantity,
                price=current_price,
                order_type=OrderType.LIMIT
            )

            return result if result else {"success": False, "message": "매수 주문 실행 실패"}

        except Exception as e:
            self.logger.error(f"❌ {symbol} 자동 매수 주문 실패: {e}")
            return {"success": False, "message": str(e)}
