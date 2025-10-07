#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/trading/auto_trader.py

자동매매 시스템 - Buy 추천 종목 모니터링 및 자동 매수/매도
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, asdict

from utils.logger import get_logger
from .executor import TradingExecutor, OrderSide, ExecutionResult
from data_collectors.chart_data_collector import ChartDataCollector
from analyzers.technical_indicators import RealTechnicalIndicators
from database.models import OrderType, TradeType
from .smart_rebalancer import SmartRebalancer


class SignalType(Enum):
    """매매 신호 타입"""
    BUY_SIGNAL = "BUY_SIGNAL"
    SELL_SIGNAL = "SELL_SIGNAL"
    HOLD = "HOLD"


class TimeFrame(Enum):
    """시간 프레임"""
    SHORT_TERM = "SHORT_TERM"  # 1분, 3분, 5분, 15분봉
    MID_TERM = "MID_TERM"      # 30분, 1시간, 일봉


@dataclass
class TradingCondition:
    """매매 조건 정의"""
    # 이평선 조건
    ema_5_above_20: bool = False
    ema_golden_cross: bool = False
    ema_dead_cross: bool = False
    
    # 캔들 조건
    volume_candle_breakout: bool = False
    support_bounce: bool = False
    resistance_rejection: bool = False
    
    # 거래량 조건
    volume_surge: bool = False
    volume_decline: bool = False
    
    # 보조지표 조건
    rsi_oversold_bounce: bool = False    # RSI 40 부근 반등
    rsi_normal_uptrend: bool = False     # RSI 정상 + 상승 추세
    rsi_overbought_decline: bool = False # RSI 70 이상 하락
    macd_golden_cross: bool = False
    macd_dead_cross: bool = False
    
    # 추가 필터
    news_positive: bool = False
    fundamental_strong: bool = False
    

@dataclass
class MonitoringStock:
    """모니터링 중인 종목"""
    symbol: str
    name: str
    recommendation_time: datetime
    strategy_name: str
    target_price: Optional[int] = None
    stop_loss_price: Optional[int] = None
    monitoring_active: bool = True
    last_check_time: Optional[datetime] = None
    current_price: Optional[int] = None


class AutoTrader:
    """자동매매 시스템"""
    
    def __init__(self, config, kis_collector, executor: TradingExecutor, analysis_engine=None, db_manager=None):
        self.config = config
        self.kis_collector = kis_collector
        self.executor = executor
        self.analysis_engine = analysis_engine
        self.db_manager = db_manager # Store db_manager
        self.logger = get_logger("AutoTrader")
        
        # KIS Collector에 DB 매니저 연결 (일일 손실 한도 체크용)
        if hasattr(self.kis_collector, 'db_manager'):
            self.kis_collector.db_manager = db_manager
        
        # 실제 기술적 지표 계산 시스템 (Phase 2 업그레이드)
        self.chart_data_collector = ChartDataCollector(kis_collector)
        self.technical_indicators = RealTechnicalIndicators()
        
        # 스마트 리밸런서 (매매 조건 기반 동적 포트폴리오 관리) - DB 연동
        self.smart_rebalancer = SmartRebalancer(config, db_manager)
        
        self.logger.info("🚀 AutoTrader 초기화 완료 - 실제 기술적 지표 엔진 + 스마트 리밸런서 탑재")
        
        # 모니터링 상태
        self.monitoring_stocks: Dict[str, MonitoringStock] = {}
        self.is_monitoring = False
        self.monitoring_interval = 30  # 30초마다 체크
        
        # 매매 설정
        self.max_positions = getattr(config.trading, 'MAX_POSITIONS', 10)  # config.py = 10
        self.position_size = getattr(config.trading, 'POSITION_SIZE', 1000000)  # 100만원
        self.stop_loss_pct = getattr(config.trading, 'STOP_LOSS_PCT', 0.05)     # 5% 손절
        self.take_profit_pct = getattr(config.trading, 'TAKE_PROFIT_PCT', 0.10) # 10% 익절
        
        # 매매 시간 설정
        self.trading_start_time = "09:00"
        self.trading_end_time = "15:20"
        
        # 초기 모니터링 종목 로드 (DB에서)
        asyncio.create_task(self._load_initial_monitoring_stocks())
        
        self.logger.info("🤖 AutoTrader 초기화 완료")
    
    async def _load_initial_monitoring_stocks(self):
        """데이터베이스에서 초기 모니터링 종목을 로드합니다."""
        try:
            if not self.db_manager:
                self.logger.warning("데이터베이스 매니저가 초기화되지 않아 모니터링 종목을 로드할 수 없습니다.")
                return

            from database.models import MonitoringStock as DbMonitoringStock, MonitoringType

            self.logger.debug("데이터베이스에서 모니터링 종목 로드 중...")
            with self.db_manager.get_session() as session:
                
                # 직접 SQL 쿼리 실행하여 문제 진단
                from sqlalchemy import text
                raw_db_stocks_result = session.execute(text("SELECT * FROM monitoring_stocks WHERE status = 'active' AND monitoring_type = 'TRADING'")).fetchall()
                self.logger.debug(f"활성 모니터링 종목 {len(raw_db_stocks_result)}개 조회")
                
                db_stocks = []
                for row in raw_db_stocks_result:
                    # SQLAlchemy ORM 모델 객체로 변환 (필요한 필드만)
                    db_stocks.append(DbMonitoringStock(
                        id=row.id,
                        symbol=row.symbol,
                        name=row.name,
                        recommendation_time=row.recommendation_time,
                        strategy_name=row.strategy_name,
                        target_price=row.target_price,
                        stop_loss_price=row.stop_loss_price,
                        monitoring_active=row.monitoring_active,
                        last_check_time=row.last_check_time,
                        current_price=row.current_price,
                        monitoring_type=row.monitoring_type, # Ensure monitoring_type is included
                        status=row.status # Ensure status is included
                    ))

                self.logger.debug(f"DB 모니터링 객체 {len(db_stocks)}개 생성")
                
                # db_stocks = DbMonitoringStock.get_active_monitoring(session, MonitoringType.TRADING)
                # self.logger.debug(f"get_active_monitoring returned {len(db_stocks)} stocks.")
                
                for db_stock in db_stocks:
                    if db_stock.symbol not in self.monitoring_stocks:
                        # DB 모델을 AutoTrader의 MonitoringStock dataclass로 변환
                        monitoring_stock = MonitoringStock(
                            symbol=db_stock.symbol,
                            name=db_stock.name,
                            recommendation_time=db_stock.recommendation_time,
                            strategy_name=db_stock.strategy_name,
                            target_price=db_stock.target_price,
                            stop_loss_price=db_stock.stop_loss_price,
                            monitoring_active=db_stock.monitoring_active,
                            last_check_time=db_stock.last_check_time,
                            current_price=db_stock.current_price
                        )
                        self.monitoring_stocks[db_stock.symbol] = monitoring_stock
                        self.logger.debug(f"DB에서 로드: {db_stock.symbol} ({db_stock.name}) - {db_stock.strategy_name}")
            
            self.logger.info(f"📊 DB에서 총 {len(self.monitoring_stocks)}개 모니터링 종목 로드 완료")

        except Exception as e:
            self.logger.error(f"데이터베이스에서 모니터링 종목 로드 실패: {e}")

    async def start_monitoring(self):
        """모니터링 시작 - 개선된 예외 처리"""
        if self.is_monitoring:
            self.logger.warning("⚠️ 이미 모니터링이 실행 중입니다")
            return
        
        # HTS에서 보유종목 로드하여 모니터링에 추가 (DB 로드 후 실행)
        await self.load_holdings_from_hts()
        
        self.is_monitoring = True
        self.logger.info("🔍 자동매매 모니터링 시작")
        
        try:
            while self.is_monitoring:
                try:
                    if self._is_trading_time():
                        await self._monitoring_cycle()
                    else:
                        self.logger.info("📴 장외시간 - 모니터링 대기 중...")
                except Exception as cycle_error:
                    self.logger.error(f"❌ 모니터링 사이클 오류: {cycle_error}")
                    # 개별 사이클 오류는 전체 모니터링을 중단시키지 않음
                
                await asyncio.sleep(self.monitoring_interval)
                
        except Exception as e:
            self.logger.error(f"❌ 모니터링 중 치명적 오류: {e}")
        finally:
            self.is_monitoring = False
            self.logger.info("🔴 자동매매 모니터링 종료")
        
        # 매매 시간 설정
        self.trading_start_time = "09:00"
        self.trading_end_time = "15:20"
        
        self.logger.info("🤖 AutoTrader 초기화 완료")
    
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.is_monitoring:
            self.logger.warning("⚠️ 이미 모니터링이 실행 중입니다")
            return
        
        # 데이터베이스에서 초기 모니터링 종목을 로드
        await self._load_initial_monitoring_stocks()

        # HTS에서 보유종목 로드하여 모니터링에 추가 (DB 로드 후 실행)
        await self.load_holdings_from_hts()
        
        self.is_monitoring = True
        self.logger.info("🔍 자동매매 모니터링 시작")
        
        try:
            while self.is_monitoring:
                if self._is_trading_time():
                    await self._monitoring_cycle()
                else:
                    self.logger.info("📴 장외시간 - 모니터링 대기 중...")
                
                await asyncio.sleep(self.monitoring_interval)
                
        except Exception as e:
            self.logger.error(f"❌ 모니터링 중 오류: {e}")
        finally:
            self.is_monitoring = False
            self.logger.info("🔴 자동매매 모니터링 종료")
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        self.logger.info("🛑 자동매매 모니터링 중지 요청")
    
    async def add_buy_recommendation(self, symbol: str, name: str, strategy_name: str, 
                                  target_price: Optional[int] = None) -> bool:
        """Buy 추천 종목을 모니터링 리스트에 추가"""
        try:
            if symbol in self.monitoring_stocks:
                self.logger.warning(f"⚠️ {symbol}({name})은 이미 모니터링 중입니다")
                return False
            
            # 현재 포지션 수 확인 - DB 기반 (더 정확함)
            try:
                if self.db_manager:
                    # DB에서 실제 활성 포지션 수 확인
                    from sqlalchemy.orm import Session
                    from database.models import MonitoringStock as DBMonitoringStock, MonitoringStatus, MonitoringType
                    
                    with Session(self.db_manager.engine) as session:
                        active_positions = session.query(DBMonitoringStock).filter(
                            DBMonitoringStock.status == MonitoringStatus.ACTIVE.value,
                            DBMonitoringStock.monitoring_active == True,
                            DBMonitoringStock.monitoring_type == MonitoringType.TRADING.value
                        ).count()
                else:
                    # DB 없을 경우 메모리 기반 확인 (폴백)
                    active_positions = len([s for s in self.monitoring_stocks.values() if s.monitoring_active])
                    
                if active_positions >= self.max_positions:
                    self.logger.warning(f"⚠️ 최대 포지션 수 초과: {active_positions}/{self.max_positions}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"❌ 포지션 수 확인 실패: {e}")
                # 에러 시 안전하게 추가 불허
                return False
            
            # 모니터링 종목 추가
            monitoring_stock = MonitoringStock(
                symbol=symbol,
                name=name,
                recommendation_time=datetime.now(),
                strategy_name=strategy_name,
                target_price=target_price
            )
            
            self.monitoring_stocks[symbol] = monitoring_stock
            
            # 데이터베이스에 저장
            if self.db_manager:
                from database.models import MonitoringStock as DbMonitoringStock, MonitoringType
                from sqlalchemy.orm import Session
                
                try:
                    with self.db_manager.get_session() as session:
                        # 이미 활성 상태로 존재하는지 확인
                        db_stock = session.query(DbMonitoringStock).filter(
                            DbMonitoringStock.symbol == symbol,
                            DbMonitoringStock.monitoring_type == MonitoringType.TRADING.value,
                            DbMonitoringStock.status == 'ACTIVE'
                        ).first()
                        
                        if not db_stock:
                            # DB에 새 모니터링 종목 추가
                            new_db_stock = DbMonitoringStock(
                                symbol=symbol,
                                name=name,
                                monitoring_type=MonitoringType.TRADING.value,
                                strategy_name=strategy_name,
                                target_price=target_price,
                                add_reason="AutoTrader recommendation",
                                status='ACTIVE',
                                monitoring_active=True,
                                recommendation_time=monitoring_stock.recommendation_time
                            )
                            session.add(new_db_stock)
                            session.commit()
                            self.logger.info(f"✅ DB에 모니터링 추가: {symbol}({name})")
                        else:
                            self.logger.info(f"ℹ️ DB에 이미 모니터링 중인 종목: {symbol}({name})")
                except Exception as db_error:
                    self.logger.error(f"❌ DB 저장 실패: {symbol}({name}) - {db_error}")

            # 초기 가격 정보 수집
            await self._update_stock_price(symbol)
            
            self.logger.info(f"📋 모니터링 추가: {symbol}({name}) - {strategy_name} 전략")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 추가 실패: {e}")
            return False
    
    async def remove_monitoring(self, symbol: str, reason: str = "수동 제거") -> bool:
        """모니터링에서 종목 제거"""
        try:
            if symbol not in self.monitoring_stocks:
                self.logger.warning(f"⚠️ {symbol}은 모니터링 중이 아닙니다")
                return False
            
            removed_stock = self.monitoring_stocks.pop(symbol)
            self.logger.info(f"🗑️ 모니터링 제거: {symbol}({removed_stock.name})")

            # 데이터베이스 업데이트
            if self.db_manager:
                from database.models import MonitoringStock as DbMonitoringStock, MonitoringStatus
                with self.db_manager.get_session() as session:
                    db_stock = DbMonitoringStock.get_by_symbol_and_type(session, symbol, MonitoringType.TRADING)
                    if db_stock:
                        db_stock.status = MonitoringStatus.REMOVED.value
                        db_stock.monitoring_active = False
                        db_stock.completed_time = datetime.now()
                        db_stock.remove_reason = reason
                        session.add(db_stock)
                        session.commit()
                        self.logger.info(f"✅ DB에서 {symbol} 모니터링 상태 업데이트 완료 (제거됨)")
                    else:
                        self.logger.warning(f"⚠️ DB에서 {symbol} 모니터링 종목을 찾을 수 없습니다.")

            return True
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 제거 실패: {e}")
            return False
    
    async def _monitoring_cycle(self):
        """모니터링 사이클 실행"""
        try:
            if not self.monitoring_stocks:
                return
            
            self.logger.debug(f"🔍 모니터링 사이클 시작 ({len(self.monitoring_stocks)}개 종목)")
            
            # 모든 모니터링 종목 병렬 처리
            tasks = []
            for symbol, stock in self.monitoring_stocks.items():
                if stock.monitoring_active:
                    tasks.append(self._check_trading_signal(symbol, stock))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"❌ 모니터링 사이클 오류: {e}")
    
    async def _check_trading_signal(self, symbol: str, stock: MonitoringStock):
        """개별 종목의 매매 신호 체크"""
        try:
            # 1. 현재 가격 업데이트
            await self._update_stock_price(symbol)
            stock.last_check_time = datetime.now()
            
            # 2. 기술적 분석 데이터 수집
            tech_data = await self._get_technical_data(symbol)
            if not tech_data:
                return
            
            # 3. 매매 조건 분석
            conditions = await self._analyze_trading_conditions(symbol, tech_data)
            
            # 4. 매매 신호 판단 (보유종목 vs 신규 매수 대상 구분)
            if stock.strategy_name == "holding_stock":
                # 보유종목은 매도 신호만 체크
                signal = self._determine_sell_signal_for_holding(conditions, stock)
            else:
                # 신규 매수 대상은 기존 로직 사용
                signal = self._determine_trading_signal(conditions, stock, tech_data)
            
            # 5. 신호에 따른 액션 실행
            if signal == SignalType.BUY_SIGNAL:
                # 매수 신호 발생 시 스마트 리밸런서를 통해 평가
                await self._process_buy_signal_with_rebalancing(symbol, stock, tech_data, conditions)
            elif signal == SignalType.SELL_SIGNAL:
                await self._execute_sell_signal(symbol, stock, tech_data)
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 신호 체크 실패: {e}")
    
    async def _get_technical_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        실제 기술적 분석 데이터 수집 (Phase 2 업그레이드)
        
        🚨 기존 치명적 문제 완전 해결:
        - OLD: ema_5 = current_price * 1.02 (완전히 잘못됨)
        - NEW: 실제 지수 이동평균 (과거 30일 데이터 기반)
        
        - OLD: rsi = 50 + (change_rate * 2) (RSI 공식과 무관)  
        - NEW: 실제 상대강도지수 (14일 상승/하락 평균)
        """
        try:
            # 1. 차트 데이터 수집 (일봉 30일)
            chart_data = await self.chart_data_collector.get_daily_chart_data(symbol, days=30)
            
            if not chart_data or len(chart_data) < 5:
                self.logger.warning(f"⚠️ {symbol}: 차트 데이터 부족 ({len(chart_data) if chart_data else 0}일)")
                return await self._get_fallback_technical_data(symbol)
            
            # 2. 실제 기술적 지표 계산
            tech_result = self.technical_indicators.calculate_all_indicators(symbol, chart_data)
            
            if tech_result and tech_result.get('data_quality') == 'real_calculation':
                # 성공: 실제 계산 결과 사용
                self.logger.debug(f"✅ {symbol}: 실제 기술적 지표 계산 완료 (EMA5: {tech_result['ema_5']:.0f}, RSI: {tech_result['rsi']:.1f})")
                return tech_result
            else:
                # 실패: 폴백 사용
                self.logger.warning(f"⚠️ {symbol}: 기술적 지표 계산 실패, 폴백 사용")
                return await self._get_fallback_technical_data(symbol)
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} 실제 기술적 데이터 수집 실패: {e}")
            return await self._get_fallback_technical_data(symbol)
    
    async def _get_fallback_technical_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        기술적 지표 계산 실패 시 폴백 데이터
        (기존 임시 계산보다는 낫지만 여전히 제한적)
        """
        try:
            # 기본 주식 정보
            stock_info = await self.kis_collector.get_stock_info(symbol)
            if not stock_info:
                return None
            
            current_price = stock_info.current_price if stock_info.current_price else 0
            volume = stock_info.volume if stock_info.volume else 0
            change_rate = stock_info.change_rate if stock_info.change_rate else 0
            
            # 기본값 설정 (실제 계산이 불가능한 경우)
            return {
                'current_price': current_price,
                'volume': volume,
                'change_rate': change_rate,
                'ema_5': current_price * 1.001,    # 약간 높게 설정하여 매매 신호 구분
                'ema_20': current_price * 0.999,   # 약간 낮게 설정하여 실제 계산 실패 시에도 최소 구분
                'rsi': 50,                   # 중립값 (기존: 50 + (change_rate * 2))
                'macd_line': 0,              # 중립값
                'macd_signal': 0,            # 중립값  
                'macd_histogram': 0,         # 중립값
                'signals': {
                    'ema_5_signal': 'hold',
                    'ema_20_signal': 'hold',
                    'rsi_signal': 'hold',
                    'macd_signal': 'hold',
                    'composite_signal': 'hold',
                    'composite_confidence': 0.0
                },
                'volume_avg': max(volume * 1.2, 100000),  # 개선된 평균 거래량 추정
                'timestamp': datetime.now(),
                'data_quality': 'fallback'   # 폴백 데이터임을 표시
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 폴백 데이터 생성 실패: {e}")
            return None
    
    async def _analyze_trading_conditions(self, symbol: str, tech_data: Dict) -> TradingCondition:
        """매매 조건 분석"""
        try:
            condition = TradingCondition()
            
            current_price = tech_data['current_price']
            volume = tech_data['volume']
            ema_5 = tech_data['ema_5']
            ema_20 = tech_data['ema_20']
            rsi = tech_data['rsi']
            volume_avg = tech_data['volume_avg']
            change_rate = tech_data['change_rate']
            
            # 이평선 조건
            condition.ema_5_above_20 = ema_5 > ema_20
            # 골든크로스/데드크로스는 이전 데이터와 비교 필요 (임시로 단순화)
            
            # 캔들 조건
            condition.volume_candle_breakout = (volume > volume_avg * 1.5 and change_rate > 2.0)
            condition.support_bounce = (change_rate > 1.0 and rsi < 40)
            condition.resistance_rejection = (change_rate < -1.0 and rsi > 60)
            
            # 거래량 조건
            condition.volume_surge = volume > volume_avg * 2.0
            condition.volume_decline = volume < volume_avg * 0.5
            
            # RSI 조건 - 개선됨
            condition.rsi_oversold_bounce = (rsi < 40 and change_rate > 0)  # RSI 40 미만으로 완화
            condition.rsi_normal_uptrend = (rsi < 60 and change_rate > 0.5)  # 새 조건: RSI 정상 + 상승
            condition.rsi_overbought_decline = (rsi > 70 and change_rate < 0)
            
            # 뉴스/펀더멘탈 조건 (실제로는 분석 엔진에서 가져와야 함)
            # condition.news_positive = await self._check_recent_news(symbol)
            # condition.fundamental_strong = await self._check_fundamental(symbol)
            
            return condition
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 조건 분석 실패: {e}")
            return TradingCondition()
    
    def _determine_trading_signal(self, conditions: TradingCondition, stock: MonitoringStock, tech_data: Dict) -> SignalType:
        """매매 신호 판단 - 매매조건.md 기반 점수 시스템"""
        try:
            buy_score = 0
            buy_reasons = []
            
            current_price = tech_data['current_price']
            ema_5 = tech_data['ema_5']
            ema_20 = tech_data['ema_20']
            rsi = tech_data['rsi']
            volume = tech_data['volume']
            volume_avg = tech_data['volume_avg']
            change_rate = tech_data['change_rate']
            
            # === 단기 매수 기준 (3분봉, 5분봉, 15분봉) ===
            
            # 1. 이평선 조건 (25점)
            if ema_5 > ema_20:  # 5EMA > 20EMA 돌파
                buy_score += 15
                buy_reasons.append("5EMA>20EMA")
                
                # 이평선 수렴 후 확장 (보너스)
                ema_gap_ratio = (ema_5 - ema_20) / ema_20 * 100
                if 0.2 < ema_gap_ratio < 1.5:  # 수렴 후 확산 구간
                    buy_score += 10
                    buy_reasons.append("이평선확산")
            
            # 2. 캔들 + 거래량 조건 (30점)
            if change_rate > 1.0 and volume > volume_avg * 1.3:  # 거래량 동반 양봉
                buy_score += 20
                buy_reasons.append("거래량동반양봉")
                
                if change_rate > 2.5:  # 강한 양봉 (장대양봉)
                    buy_score += 10
                    buy_reasons.append("장대양봉")
            
            # 3. 저점 지지 반등 (20점)
            if change_rate > 0.5 and rsi < 45:  # 저점에서 양봉 출현
                buy_score += 15
                buy_reasons.append("저점지지반등")
                
                if rsi < 35:  # 강한 과매도에서 반등
                    buy_score += 5
                    buy_reasons.append("과매도반등")
            
            # 4. 거래량 급증 (15점)
            if volume > volume_avg * 2.0:  # 거래량 폭증
                buy_score += 15
                buy_reasons.append("거래량폭증")
            elif volume > volume_avg * 1.5:  # 거래량 급증
                buy_score += 10
                buy_reasons.append("거래량급증")
            
            # 5. RSI 조건 (20점)
            if 25 <= rsi <= 35 and change_rate > 0:  # RSI 30 부근 반등
                buy_score += 20
                buy_reasons.append("RSI과매도반등")
            elif 35 < rsi <= 45 and change_rate > 1.0:  # RSI 40 부근 강한 반등
                buy_score += 15
                buy_reasons.append("RSI저점반등")
            elif 45 < rsi < 65 and change_rate > 1.5:  # RSI 정상 + 강한 상승
                buy_score += 10
                buy_reasons.append("RSI정상상승")
            
            # 6. 추세 및 모멘텀 (10점)
            if change_rate > 2.0:  # 강한 상승 모멘텀
                buy_score += 10
                buy_reasons.append("강한모멘텀")
            elif change_rate > 1.0:  # 상승 모멘텀
                buy_score += 5
                buy_reasons.append("상승모멘텀")
            
            # === 매도 신호 확인 ===
            sell_score = 0
            sell_reasons = []
            
            # 매도 조건들
            if rsi > 75 and change_rate < -1.0:  # RSI 과매수 + 하락
                sell_score += 20
                sell_reasons.append("RSI과매수하락")
            
            if ema_5 < ema_20 and change_rate < -1.5:  # 이평선 이탈 + 하락
                sell_score += 15
                sell_reasons.append("이평선이탈")
            
            if volume < volume_avg * 0.7 and change_rate < -1.0:  # 거래량 감소 + 음봉
                sell_score += 10
                sell_reasons.append("거래량감소음봉")
            
            # === 최종 신호 판단 ===
            
            # 강한 매수 신호 (80점 이상)
            if buy_score >= 80:
                self.logger.info(f"🚀 {stock.symbol} 강한 매수 신호 - 점수: {buy_score}점")
                self.logger.info(f"   💎 매수 이유: {', '.join(buy_reasons)}")
                return SignalType.BUY_SIGNAL
            
            # 일반 매수 신호 (60점 이상)
            elif buy_score >= 60:
                self.logger.info(f"📈 {stock.symbol} 매수 신호 - 점수: {buy_score}점")
                self.logger.info(f"   💡 매수 이유: {', '.join(buy_reasons)}")
                return SignalType.BUY_SIGNAL
            
            # 약한 매수 신호 (45점 이상) - 관심 종목
            elif buy_score >= 45:
                self.logger.info(f"⚡ {stock.symbol} 관심 대상 - 점수: {buy_score}점")
                self.logger.info(f"   👀 이유: {', '.join(buy_reasons)}")
                # 추가 조건이 맞으면 매수
                if len(buy_reasons) >= 2:  # 2개 이상 근거가 있으면 매수
                    return SignalType.BUY_SIGNAL
                return SignalType.HOLD
            
            # 매도 신호 (15점 이상)
            elif sell_score >= 15:
                self.logger.info(f"📉 {stock.symbol} 매도 신호 - 점수: {sell_score}점")
                self.logger.info(f"   🔻 매도 이유: {', '.join(sell_reasons)}")
                return SignalType.SELL_SIGNAL
            
            # 보통 상태
            else:
                if buy_score > 0:
                    self.logger.debug(f"🔍 {stock.symbol} 매수 점수: {buy_score}점 (임계값 미달)")
                return SignalType.HOLD
            
        except Exception as e:
            self.logger.error(f"❌ {stock.symbol} 신호 판단 실패: {e}")
            return SignalType.HOLD
    
    async def _process_buy_signal_with_rebalancing(self, symbol: str, stock: MonitoringStock, 
                                                 tech_data: Dict, conditions: TradingCondition):
        """매수 신호 발생 시 스마트 리밸런싱을 통한 처리"""
        try:
            self.logger.info(f"🎯 {symbol} 매수 신호 처리 시작 - 스마트 리밸런싱 적용")
            
            # 1. 매매 신호 점수 재계산 (리밸런서용)
            trading_signal_score = await self._calculate_trading_signal_score(tech_data, conditions)
            
            # 2. 종목 기본 정보 구성
            stock_data = {
                'symbol': symbol,
                'name': stock.name,
                'current_price': tech_data['current_price'],
                'change_rate': tech_data['change_rate'],
                'volume': tech_data['volume'],
                'market_cap': tech_data.get('market_cap', 1000),  # 기본값
                'sector': tech_data.get('sector', 'OTHER'),
                'recommendation_score': 75  # 기본 추천 점수
            }
            
            # 3. 스마트 리밸런서에 후보 추가
            rebalance_result = await self.smart_rebalancer.add_new_candidate(
                symbol, stock_data, tech_data, trading_signal_score
            )
            
            # 4. 리밸런싱 결과 확인
            if rebalance_result.get('error'):
                self.logger.error(f"❌ {symbol} 리밸런싱 실패: {rebalance_result['error']}")
                return
            
            new_stock_rank = rebalance_result['new_stock']['rank']
            changes_needed = rebalance_result['action_required']
            
            # 5. Top 5 진입 시 매수 실행
            if new_stock_rank <= 5:
                self.logger.info(f"🏆 {symbol} Top 5 진입 (순위: {new_stock_rank}) - 매수 실행")
                await self._execute_buy_signal(symbol, stock, tech_data)
                
                # 6. 리밸런싱이 필요한 경우 기존 종목 매도 처리
                if changes_needed:
                    await self._handle_rebalancing_actions(rebalance_result['rebalancing'])
            else:
                self.logger.info(f"📊 {symbol} 평가 완료 - 순위: {new_stock_rank} (Top 5 미진입)")
                self.logger.info(f"   💡 매매신호점수: {trading_signal_score:.1f}, "
                               f"종합점수: {rebalance_result['new_stock']['evaluation'].total_score:.1f}")
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} 스마트 리밸런싱 처리 실패: {e}")
    
    async def _calculate_trading_signal_score(self, tech_data: Dict, conditions: TradingCondition) -> float:
        """매매 신호 점수 계산 (리밸런서용)"""
        try:
            # 앞서 구현한 매매 신호 판단 로직과 동일한 점수 계산
            buy_score = 0
            
            current_price = tech_data['current_price']
            ema_5 = tech_data['ema_5']
            ema_20 = tech_data['ema_20']
            rsi = tech_data['rsi']
            volume = tech_data['volume']
            volume_avg = tech_data['volume_avg']
            change_rate = tech_data['change_rate']
            
            # 1. 이평선 조건 (25점)
            if ema_5 > ema_20:
                buy_score += 15
                ema_gap_ratio = (ema_5 - ema_20) / ema_20 * 100
                if 0.2 < ema_gap_ratio < 1.5:
                    buy_score += 10
            
            # 2. 캔들 + 거래량 조건 (30점)
            if change_rate > 1.0 and volume > volume_avg * 1.3:
                buy_score += 20
                if change_rate > 2.5:
                    buy_score += 10
            
            # 3. 저점 지지 반등 (20점)
            if change_rate > 0.5 and rsi < 45:
                buy_score += 15
                if rsi < 35:
                    buy_score += 5
            
            # 4. 거래량 급증 (15점)
            if volume > volume_avg * 2.0:
                buy_score += 15
            elif volume > volume_avg * 1.5:
                buy_score += 10
            
            # 5. RSI 조건 (20점)
            if 25 <= rsi <= 35 and change_rate > 0:
                buy_score += 20
            elif 35 < rsi <= 45 and change_rate > 1.0:
                buy_score += 15
            elif 45 < rsi < 65 and change_rate > 1.5:
                buy_score += 10
            
            # 6. 추세 및 모멘텀 (10점)
            if change_rate > 2.0:
                buy_score += 10
            elif change_rate > 1.0:
                buy_score += 5
            
            return max(0, min(100, buy_score))
            
        except Exception as e:
            self.logger.error(f"❌ 매매 신호 점수 계산 실패: {e}")
            return 50.0  # 기본값
    
    async def _handle_rebalancing_actions(self, rebalancing_info: Dict):
        """리밸런싱 액션 처리"""
        try:
            changes = rebalancing_info.get('changes', {})
            removed_symbols = changes.get('removed', [])
            
            if not removed_symbols:
                return
            
            self.logger.info(f"🔄 리밸런싱 실행 - 매도 대상: {', '.join(removed_symbols)}")
            
            # Top 5에서 제외된 종목들 매도 처리
            for symbol in removed_symbols:
                if symbol in self.monitoring_stocks:
                    stock = self.monitoring_stocks[symbol]
                    
                    # 보유 중인 종목인지 확인 (실제로는 포트폴리오에서 확인해야 함)
                    if stock.strategy_name == "holding_stock":
                        self.logger.info(f"📉 {symbol} 리밸런싱 매도 실행")
                        
                        # 현재 가격 조회
                        tech_data = await self._get_technical_data(symbol)
                        if tech_data:
                            await self._execute_sell_signal(symbol, stock, tech_data)
                    else:
                        # 아직 매수하지 않은 종목은 모니터링에서만 제거
                        self.logger.info(f"👀 {symbol} 모니터링 종료 (매수 전)")
                        await self.remove_monitoring(symbol)
            
        except Exception as e:
            self.logger.error(f"❌ 리밸런싱 액션 처리 실패: {e}")
    
    async def _execute_buy_signal(self, symbol: str, stock: MonitoringStock, tech_data: Dict):
        """매수 신호 실행"""
        try:
            current_price = tech_data['current_price']
            
            # 매수 수량 계산 (포지션 크기 기준)
            quantity = self.position_size // current_price
            if quantity < 1:
                self.logger.warning(f"⚠️ {symbol} 매수 수량 부족: {quantity}")
                return
            
            # 손절가/목표가 설정
            stop_loss_price = int(current_price * (1 - self.stop_loss_pct))
            target_price = int(current_price * (1 + self.take_profit_pct))
            
            self.logger.info(f"🚀 {symbol} 매수 실행: {quantity}주 @ {current_price:,}원")
            self.logger.info(f"   📍 손절가: {stop_loss_price:,}원 | 목표가: {target_price:,}원")
            
            # 실제 매수 주문 실행
            result = await self.executor.execute_buy_order(
                symbol=symbol,
                quantity=quantity,
                price=current_price,  # 지정가 주문
                order_type=OrderType.LIMIT
            )
            
            if result['success']:
                # 매수 성공 시 목표가/손절가 업데이트
                stock.target_price = target_price
                stock.stop_loss_price = stop_loss_price
                self.logger.info(f"✅ {symbol} 매수 주문 성공: 주문번호 {result.get('order_id')}")

                # 데이터베이스에 매수 정보 업데이트
                if self.db_manager:
                    from database.models import MonitoringStock as DbMonitoringStock, MonitoringType
                    try:
                        with self.db_manager.get_session() as session:
                            db_stock = session.query(DbMonitoringStock).filter(
                                DbMonitoringStock.symbol == symbol,
                                DbMonitoringStock.monitoring_type == MonitoringType.TRADING.value,
                                DbMonitoringStock.status == 'ACTIVE'
                            ).first()
                            
                            if db_stock:
                                db_stock.buy_price = current_price
                                db_stock.avg_price = current_price # 첫 매수이므로 평단가 동일
                                db_stock.buy_quantity = quantity
                                db_stock.holding_quantity = quantity
                                db_stock.buy_amount = current_price * quantity
                                db_stock.buy_time = datetime.now()
                                db_stock.stop_loss_price = stop_loss_price
                                db_stock.target_price = target_price
                                session.commit()
                                self.logger.info(f"💾 DB 업데이트 완료: {symbol} 매수 정보 기록")
                            else:
                                self.logger.warning(f"⚠️ DB에서 {symbol}을 찾을 수 없어 매수 정보를 기록하지 못했습니다.")
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 매수 정보 DB 업데이트 실패: {e}")

            else:
                self.logger.error(f"❌ {symbol} 매수 주문 실패: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} 매수 실행 실패: {e}")
    
    async def _execute_sell_signal(self, symbol: str, stock: MonitoringStock, tech_data: Dict):
        """매도 신호 실행"""
        try:
            current_price = tech_data['current_price']
            
            # DB에서 보유 수량 및 매수 정보 확인
            if not self.db_manager:
                self.logger.error(f"❌ {symbol} 매도 실패: DB 매니저가 없습니다.")
                return

            from database.models import MonitoringStock as DbMonitoringStock, MonitoringType, MonitoringStatus, TradeHistory, WinLossStatus
            
            with self.db_manager.get_session() as session:
                db_stock = session.query(DbMonitoringStock).filter(
                    DbMonitoringStock.symbol == symbol,
                    DbMonitoringStock.monitoring_type == MonitoringType.TRADING.value,
                    DbMonitoringStock.status == MonitoringStatus.ACTIVE.value
                ).first()

                if not db_stock or not db_stock.holding_quantity or db_stock.holding_quantity <= 0:
                    self.logger.warning(f"⚠️ {symbol} 매도 신호가 발생했으나 DB에 보유 수량이 없습니다.")
                    # 메모리에서도 제거하여 불필요한 반복 방지
                    if symbol in self.monitoring_stocks:
                        del self.monitoring_stocks[symbol]
                    return

                quantity_to_sell = db_stock.holding_quantity
                buy_price = db_stock.avg_price
                buy_trade_id = db_stock.buy_trade_id # 매수 시 기록된 trade.id
                
                self.logger.info(f"📉 {symbol} 매도 실행: {quantity_to_sell}주 @ {current_price:,}원")
                
                # 실제 매도 주문 실행
                result = await self.executor.execute_sell_order(
                    symbol=symbol,
                    quantity=quantity_to_sell,
                    price=current_price,  # 지정가 주문
                    order_type=OrderType.LIMIT
                )
                
                if result['success']:
                    self.logger.info(f"✅ {symbol} 매도 주문 성공: 주문번호 {result.get('order_id')}")
                    
                    # 1. monitoring_stocks 상태 업데이트 (COMPLETED)
                    profit_loss = (current_price - buy_price) * quantity_to_sell
                    profit_rate = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                    
                    db_stock.status = MonitoringStatus.COMPLETED.value
                    db_stock.monitoring_active = False
                    db_stock.sell_time = datetime.now()
                    db_stock.completed_time = datetime.now()
                    db_stock.profit_loss = profit_loss
                    db_stock.profit_rate = profit_rate
                    db_stock.remove_reason = f"매도 완료 (수익률: {profit_rate:.2f}%)"
                    
                    # 2. trade_history 에 기록
                    new_history = TradeHistory(
                        stock_id=db_stock.stock_id,
                        strategy_name=stock.strategy_name,
                        buy_trade_id=buy_trade_id,
                        sell_trade_id=None, # 실제로는 sell trade id를 연결해야 함
                        buy_date=db_stock.buy_time,
                        sell_date=datetime.now(),
                        buy_price=buy_price,
                        sell_price=current_price,
                        quantity=quantity_to_sell,
                        profit_loss=profit_loss,
                        profit_loss_rate=profit_rate,
                        holding_period_days=(datetime.now() - db_stock.buy_time).days,
                        status=WinLossStatus.WIN if profit_loss > 0 else WinLossStatus.LOSS
                    )
                    session.add(new_history)
                    
                    session.commit()
                    self.logger.info(f"💾 DB 업데이트 완료: {symbol} 매도 처리 및 거래 기록 저장")

                    # 3. 메모리에서 제거
                    if symbol in self.monitoring_stocks:
                        del self.monitoring_stocks[symbol]
                else:
                    self.logger.error(f"❌ {symbol} 매도 주문 실패: {result.get('error')}")
        except Exception as e:
            self.logger.error(f"❌ {symbol} 매도 실행 실패: {e}")

    async def _execute_emergency_sell_order(self, symbol: str, current_price: float, reason: str = "stop_loss"):
        """응급 매도 주문 실행 (손절가 도달 시)"""
        try:
            self.logger.warning(f"🚨 {symbol} 응급 매도 신호! 사유: {reason}, 현재가: {current_price:,}원")
            
            # KIS API를 통해 실제 보유 수량 조회
            holdings = await self.kis_collector.get_holdings()
            if not holdings or symbol not in holdings:
                self.logger.error(f"❌ {symbol} 보유 종목 정보 없음")
                return False
            
            holding_info = holdings[symbol]
            quantity = holding_info.get('quantity', 0)
            
            if quantity <= 0:
                self.logger.error(f"❌ {symbol} 보유 수량 없음: {quantity}")
                return False
            
            self.logger.info(f"🔥 {symbol} 응급 매도 실행: {quantity}주 @ {current_price:,}원")
            
            # 시장가 주문으로 즉시 매도 (손절 시에는 빠른 체결이 중요)
            result = await self.executor.execute_sell_order(
                symbol=symbol,
                quantity=quantity,
                price=None,  # 시장가 주문
                order_type=OrderType.MARKET
            )
            
            if result and result.get('success'):
                # 매도 성공 시 모니터링에서 제거
                if symbol in self.monitoring_stocks:
                    await self.remove_monitoring(symbol, reason=f"응급매도완료({reason})")
                
                self.logger.info(f"✅ {symbol} 응급 매도 성공: 주문번호 {result.get('order_id')}")
                
                # 손절 알림
                avg_price = holding_info.get('avg_price', 0)
                if avg_price > 0:
                    loss_rate = ((current_price - avg_price) / avg_price) * 100
                    self.logger.warning(f"💔 {symbol} 손절 완료 - 손실률: {loss_rate:.1f}%")
                
                return True
            else:
                error_msg = result.get('error', '알 수 없는 오류') if result else '결과 없음'
                self.logger.error(f"❌ {symbol} 응급 매도 실패: {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} 응급 매도 실행 중 오류: {e}")
            return False
    
    async def _update_stock_price(self, symbol: str):
        """종목 가격 정보 업데이트"""
        try:
            if symbol not in self.monitoring_stocks:
                return
            
            # 현재가는 실시간 API 조회로만 처리 (DB 저장 없음)
            current_price = await self.kis_collector.get_current_price(symbol)
            if current_price:
                    # 목표가: 현재가 + 익절 비율
                    self.monitoring_stocks[symbol].target_price = int(current_price * (1 + self.take_profit_pct))
                    # 손절가: 현재가 - 손절 비율  
                    self.monitoring_stocks[symbol].stop_loss_price = int(current_price * (1 - self.stop_loss_pct))
                
                self.logger.debug(f"💰 {symbol} 가격 업데이트: {current_price:,}원" if current_price else f"⚠️ {symbol} 가격 정보 없음")
                
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} 가격 업데이트 실패: {e}")
    
    def _is_trading_time(self) -> bool:
        """현재가 거래 시간인지 확인"""
        now = datetime.now()
        
        # 주말 확인
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False
        
        # 시간 확인
        current_time = now.strftime("%H:%M")
        return self.trading_start_time <= current_time <= self.trading_end_time
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """모니터링 상태 조회 (수익률, 매수가 포함)"""
        monitoring_stocks_info = {}
        
        # 보유 종목 정보 한 번만 조회
        holdings = {}
        try:
            if hasattr(self, 'executor') and self.executor and hasattr(self.executor, 'kis_collector'):
                holdings = await self.executor.kis_collector.get_holdings() or {}
        except Exception as e:
            self.logger.debug(f"보유 종목 조회 실패: {e}")
        
        for symbol, stock in self.monitoring_stocks.items():
            # 실시간 현재가 조회 (KIS API 호출만 사용, 폴백 없음)
            current_price = await self.kis_collector.get_current_price(symbol)
            if not current_price or current_price <= 0:
                continue  # API 실패시 해당 종목 건너뛰기
            
            # 매수가 계산 (포트폴리오에서 평균 매수가 조회)
            buy_price = None
            profit_rate = None
            
            try:
                if symbol in holdings:
                    avg_price = getattr(holdings[symbol], 'avg_price', 0)
                    if avg_price > 0:
                        buy_price = avg_price
                        
                        # 실시간 현재가로 수익률 계산
                        if current_price and buy_price:
                            profit_rate = ((current_price - buy_price) / buy_price) * 100
                
            except Exception as e:
                self.logger.debug(f"매수가/수익률 계산 실패 {symbol}: {e}")
            
            # 등록일 포맷팅
            added_time = stock.recommendation_time.strftime('%m-%d %H:%M') if stock.recommendation_time else 'N/A'
            
            monitoring_stocks_info[symbol] = {
                'name': stock.name,
                'strategy': stock.strategy_name,
                'recommendation_time': stock.recommendation_time.isoformat() if stock.recommendation_time else None,
                'added_time': added_time,
                'current_price': current_price,  # 실시간 현재가 사용
                'buy_price': buy_price,
                'profit_rate': profit_rate,  # 실시간 현재가로 계산된 수익률
                'target_price': stock.target_price,
                'stop_loss_price': stock.stop_loss_price,
                'last_check': stock.last_check_time.isoformat() if stock.last_check_time else None,
                'monitoring_active': stock.monitoring_active
            }
        
        return {
            'is_monitoring': self.is_monitoring,
            'monitoring_count': len(self.monitoring_stocks),
            'active_count': len([s for s in self.monitoring_stocks.values() if s.monitoring_active]),
            'trading_enabled': self.executor.is_trading_enabled(),
            'monitoring_stocks': monitoring_stocks_info
        }
    
    async def save_monitoring_state(self, filepath: str):
        """모니터링 상태를 파일에 저장"""
        try:
            state = {
                'monitoring_stocks': {
                    symbol: asdict(stock) 
                    for symbol, stock in self.monitoring_stocks.items()
                },
                'last_saved': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"💾 모니터링 상태 저장: {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 상태 저장 실패: {e}")
    
    async def load_monitoring_state(self, filepath: str):
        """파일에서 모니터링 상태 복원"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.monitoring_stocks = {}
            for symbol, stock_data in state.get('monitoring_stocks', {}).items():
                # 문자열을 datetime으로 변환
                if isinstance(stock_data.get('recommendation_time'), str):
                    stock_data['recommendation_time'] = datetime.fromisoformat(stock_data['recommendation_time'])
                if isinstance(stock_data.get('last_check_time'), str) and stock_data.get('last_check_time'):
                    stock_data['last_check_time'] = datetime.fromisoformat(stock_data['last_check_time'])
                
                self.monitoring_stocks[symbol] = MonitoringStock(**stock_data)
            
            self.logger.info(f"📂 모니터링 상태 복원: {len(self.monitoring_stocks)}개 종목")
            
        except Exception as e:
            self.logger.error(f"❌ 모니터링 상태 복원 실패: {e}")
    
    async def load_holdings_from_hts(self):
        """HTS에서 보유종목을 가져와서 매도 모니터링에 추가"""
        try:
            self.logger.info("📋 HTS 보유종목 조회 중...")
            
            # KIS API를 통해 보유종목 조회
            holdings = await self.kis_collector.get_holdings()
            
            if not holdings:
                self.logger.info("ℹ️ HTS에 보유종목이 없습니다")
                return
            
            added_count = 0
            for symbol, holding_info in holdings.items():
                try:
                    # 이미 모니터링 중인 종목은 건너뛰기
                    if symbol in self.monitoring_stocks:
                        self.logger.debug(f"⚠️ {symbol}은 이미 모니터링 중입니다")
                        continue
                    
                    # 종목 정보 추출
                    quantity = holding_info.get('quantity', 0)
                    avg_price = holding_info.get('avg_price', 0)
                    current_price = holding_info.get('current_price', 0)
                    
                    if quantity <= 0:
                        continue
                    
                    # 종목명 조회
                    stock_info = await self.kis_collector.get_stock_info(symbol)
                    if stock_info:
                        # StockData 객체인지 Dict인지 확인하여 처리
                        if hasattr(stock_info, 'name'):
                            name = stock_info.name or f'종목{symbol}'
                        else:
                            name = stock_info.get('name', f'종목{symbol}')
                    else:
                        name = f'종목{symbol}'
                    
                    # MonitoringStock 객체 생성 (보유종목용)
                    monitoring_stock = MonitoringStock(
                        symbol=symbol,
                        name=name,
                        recommendation_time=datetime.now(),
                        strategy_name="holding_stock",  # 보유종목 표시
                        target_price=None,  # 보유종목은 목표가 없음
                        stop_loss_price=int(avg_price * (1 - self.stop_loss_pct)),  # 평균단가 기준 손절가
                        monitoring_active=True,
                        current_price=current_price
                    )
                    
                    # 모니터링 리스트에 추가
                    self.monitoring_stocks[symbol] = monitoring_stock
                    added_count += 1
                    
                    self.logger.info(f"📈 보유종목 모니터링 추가: {symbol}({name}) - {quantity}주, 평단가: {avg_price:,}원")
                    
                except Exception as e:
                    self.logger.error(f"❌ {symbol} 보유종목 추가 실패: {e}")
                    continue
            
            if added_count > 0:
                self.logger.info(f"✅ 총 {added_count}개 보유종목이 매도 모니터링에 추가되었습니다")
            else:
                self.logger.info("ℹ️ 모니터링에 추가된 보유종목이 없습니다")
                
        except Exception as e:
            self.logger.error(f"❌ HTS 보유종목 로드 실패: {e}")
    
    def _determine_sell_signal_for_holding(self, conditions: TradingCondition, stock: MonitoringStock) -> SignalType:
        """보유종목 매도 신호 판단 (매수 신호와 다른 로직)"""
        try:
            # 보유종목 매도 신호 조건들
            sell_signals = []
            
            # 손절 조건 (평균단가 기준)
            if stock.stop_loss_price and stock.current_price and stock.current_price <= stock.stop_loss_price:
                sell_signals.append("손절가도달")
            
            # 익절 조건 (평균단가 기준 10% 이상 상승)
            if stock.current_price and hasattr(stock, 'avg_price'):
                avg_price = getattr(stock, 'avg_price', stock.current_price)
                if stock.current_price >= avg_price * (1 + self.take_profit_pct):
                    sell_signals.append("익절목표달성")
            
            # 기술적 매도 신호
            if conditions.resistance_rejection:
                sell_signals.append("저항선거부")
            
            if conditions.rsi_overbought_decline:
                sell_signals.append("RSI과매수하락")
            
            if conditions.ema_dead_cross:
                sell_signals.append("이평선데드크로스")
            
            # 매도 신호 판단 (보유종목은 더 보수적으로)
            if "손절가도달" in sell_signals:
                self.logger.info(f"🚨 {stock.symbol} 손절 신호: {', '.join(sell_signals)}")
                return SignalType.SELL_SIGNAL
            elif len(sell_signals) >= 2:  # 2개 이상 매도 신호
                self.logger.info(f"📉 {stock.symbol} 매도 신호: {', '.join(sell_signals)}")
                return SignalType.SELL_SIGNAL
            
            return SignalType.HOLD
            
        except Exception as e:
            self.logger.error(f"❌ {stock.symbol} 매도 신호 판단 실패: {e}")
            return SignalType.HOLD
    
    async def _execute_emergency_sell_order(self, symbol: str, current_price: float, reason: str = "stop_loss"):
        """응급 매도 주문 실행 (손절가 도달 시) - DatabaseAutoTradingHandler에서 호출"""
        try:
            self.logger.warning(f"🚨 {symbol} 응급 매도 주문 시작: {reason}")
            
            # 실제 KIS API에서 보유 수량 조회 (최대 2회 재시도)
            holdings = None
            for attempt in range(2):
                try:
                    holdings = await self.kis_collector.get_holdings()
                    if holdings and symbol in holdings:
                        break
                    elif attempt == 0:  # 첫 번째 시도 실패 시 잠깐 대기 후 재시도
                        self.logger.info(f"🔄 {symbol} 첫 번째 보유종목 조회 실패, 1초 후 재시도...")
                        await asyncio.sleep(1)
                except Exception as e:
                    self.logger.warning(f"⚠️ {symbol} 보유종목 조회 시도 {attempt+1} 실패: {e}")
                    if attempt == 0:
                        await asyncio.sleep(1)
            
            if not holdings:
                self.logger.error(f"❌ {symbol} 전체 보유종목 조회 실패 - 매도 불가")
                self.logger.error(f"   📊 KIS API holdings 응답: {holdings}")
                return False
                
            if symbol not in holdings:
                self.logger.warning(f"⚠️ {symbol} 현재 보유하지 않은 종목 - 매도 불가")
                self.logger.warning(f"   📊 보유종목 목록 ({len(holdings)}개): {list(holdings.keys())}")
                return False
                
            holding = holdings[symbol]
            # StockData 객체의 속성으로 접근
            quantity = getattr(holding, 'quantity', 0)
            avg_price = getattr(holding, 'avg_price', 0)
            
            if quantity <= 0:
                self.logger.warning(f"⚠️ {symbol} 보유 수량 없음 (수량: {quantity}) - 매도 불가")
                self.logger.warning(f"   📊 보유 정보: quantity={quantity}, avg_price={avg_price}")
                # 수량이 0이면 이미 매도된 종목일 수 있으므로 정상 처리로 간주
                return True
                
            # 예상 손익 계산
            profit_loss = (current_price - avg_price) * quantity if avg_price > 0 else 0
            profit_rate = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                
            self.logger.error(f"🚨 {symbol} 긴급 매도 실행:")
            self.logger.error(f"   📊 수량: {quantity:,}주, 평단가: {avg_price:,}원")
            self.logger.error(f"   📈 현재가: {current_price:,}원, 예상 손익: {profit_loss:+,.0f}원 ({profit_rate:+.1f}%)")
            self.logger.error(f"   🎯 사유: {reason}")
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 보유 정보 조회 실패: {e}")
            return False
            
        # 응급 매도 주문 실행 (시장가 주문으로 즉시 매도)
        try:
            result = await self.executor.sell_stock(
                symbol=symbol,
                quantity=quantity,
                price=None,  # 시장가 주문
                order_type='MARKET'  # 시장가로 즉시 매도
            )
            
            if result and result.get('success'):
                self.logger.error(f"✅ {symbol} 응급 매도 주문 성공!")
                self.logger.error(f"   📋 주문번호: {result.get('order_id')}")
                self.logger.error(f"   💰 예상 손익: {profit_loss:+,.0f}원 ({profit_rate:+.1f}%)")
                return True
                
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'No response'
                self.logger.error(f"❌ {symbol} 응급 매도 주문 실패: {error_msg}")
                return False
                    
        except Exception as e:
            self.logger.error(f"❌ {symbol} 응급 매도 주문 실행 중 오류: {e}")
            return False
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} 응급 매도 처리 중 심각한 오류: {e}")
            return False