#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/market_condition_analyzer.py

실시간 시장 상황 분석기 - 변동성과 시간대별 시장 특성 분석
"""

import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

from utils.logger import get_logger
from utils.market_schedule_manager import MarketScheduleManager, MarketStatus, TradingSession


class VolatilityRegime(Enum):
    """변동성 체제"""
    LOW = "low"           # 변동성 < 20th percentile
    NORMAL = "normal"     # 20th <= 변동성 < 80th percentile
    HIGH = "high"         # 변동성 >= 80th percentile
    EXTREME = "extreme"   # 변동성 >= 95th percentile


class TradingTimeRegime(Enum):
    """시간대별 거래 특성"""
    OPENING_RUSH = "opening_rush"     # 09:00-09:30 (개장 러시)
    MORNING_STABLE = "morning_stable" # 09:30-11:30 (오전 안정)
    PRE_LUNCH = "pre_lunch"          # 11:30-12:00 (점심 전)
    LUNCH_QUIET = "lunch_quiet"       # 12:00-13:00 (점심 시간)
    AFTERNOON_ACTIVE = "afternoon_active" # 13:00-14:30 (오후 활성)
    CLOSING_RUSH = "closing_rush"     # 14:30-15:30 (마감 러시)
    AFTER_HOURS = "after_hours"       # 15:30-16:00 (장후 거래)


@dataclass
class MarketCondition:
    """시장 상황"""
    volatility_regime: VolatilityRegime
    trading_time_regime: TradingTimeRegime
    market_status: MarketStatus
    volatility_percentile: float  # 0-100
    vix_equivalent: float        # VIX 유사 지표
    intraday_momentum: float     # 장중 모멘텀 (-1 to 1)
    sector_rotation_active: bool # 섹터 로테이션 활성 여부
    
    # 시간 관련
    current_time: datetime = field(default_factory=datetime.now)
    market_open_minutes: int = 0  # 개장 후 경과 시간(분)
    
    # 가중치 조정 팩터들
    technical_weight_factor: float = 1.0    # 기술적 분석 가중치 조정
    sentiment_weight_factor: float = 1.0    # 감성 분석 가중치 조정
    momentum_weight_factor: float = 1.0     # 모멘텀 가중치 조정
    volume_weight_factor: float = 1.0       # 거래량 분석 가중치 조정


class MarketConditionAnalyzer:
    """실시간 시장 상황 분석기"""
    
    def __init__(self, config, data_collector=None):
        self.config = config
        self.logger = get_logger("MarketConditionAnalyzer")
        self.data_collector = data_collector
        try:
            # MarketScheduleManager 초기화 시도
            self.market_schedule_manager = MarketScheduleManager(config, None)
        except:
            # 초기화 실패 시 None으로 설정 (폴백 로직에서 처리)
            self.market_schedule_manager = None
        
        # 변동성 계산을 위한 히스토리 (최근 20일)
        self.volatility_history: List[float] = []
        self.max_history_days = 20
        
        # 시간대별 특성 캐시
        self.time_regime_cache: Dict[str, Any] = {}
        self.last_analysis_time: Optional[datetime] = None
        
        self.logger.info("✅ MarketConditionAnalyzer 초기화 완료")
    
    async def analyze_current_condition(self, symbol: str = "KOSPI200") -> MarketCondition:
        """현재 시장 상황 분석"""
        try:
            current_time = datetime.now()
            
            # 1. 시장 상태 확인
            market_status = await self._get_current_market_status()
            trading_time_regime = self._determine_trading_time_regime(current_time)
            
            # 2. 변동성 분석
            volatility_data = await self._analyze_volatility(symbol)
            
            # 3. 장중 모멘텀 분석
            intraday_momentum = await self._calculate_intraday_momentum(symbol)
            
            # 4. 섹터 로테이션 감지
            sector_rotation_active = await self._detect_sector_rotation()
            
            # 5. 가중치 조정 팩터 계산
            weight_factors = self._calculate_weight_factors(
                volatility_data['regime'], 
                trading_time_regime,
                market_status
            )
            
            condition = MarketCondition(
                volatility_regime=volatility_data['regime'],
                trading_time_regime=trading_time_regime,
                market_status=market_status,
                volatility_percentile=volatility_data['percentile'],
                vix_equivalent=volatility_data['vix_equivalent'],
                intraday_momentum=intraday_momentum,
                sector_rotation_active=sector_rotation_active,
                current_time=current_time,
                market_open_minutes=self._calculate_market_open_minutes(current_time),
                **weight_factors
            )
            
            self.last_analysis_time = current_time
            self.logger.info(f"✅ 시장 상황 분석 완료: {condition.volatility_regime.value}, {condition.trading_time_regime.value}")
            
            return condition
            
        except Exception as e:
            self.logger.error(f"❌ 시장 상황 분석 실패: {e}")
            # 기본값 반환
            return self._get_default_condition()
    
    async def _get_current_market_status(self) -> MarketStatus:
        """현재 시장 상태 확인"""
        try:
            if self.market_schedule_manager:
                current_time = datetime.now()
                market_info = await self.market_schedule_manager.get_current_market_status()
                return market_info.get('status', MarketStatus.CLOSED)
        except:
            pass
        
        # 기본 로직으로 폴백
        return self._determine_market_status_by_time(datetime.now())
    
    def _determine_trading_time_regime(self, current_time: datetime) -> TradingTimeRegime:
        """시간대별 거래 특성 결정"""
        current_time_obj = current_time.time()
        
        if time(9, 0) <= current_time_obj < time(9, 30):
            return TradingTimeRegime.OPENING_RUSH
        elif time(9, 30) <= current_time_obj < time(11, 30):
            return TradingTimeRegime.MORNING_STABLE
        elif time(11, 30) <= current_time_obj < time(12, 0):
            return TradingTimeRegime.PRE_LUNCH
        elif time(12, 0) <= current_time_obj < time(13, 0):
            return TradingTimeRegime.LUNCH_QUIET
        elif time(13, 0) <= current_time_obj < time(14, 30):
            return TradingTimeRegime.AFTERNOON_ACTIVE
        elif time(14, 30) <= current_time_obj < time(15, 30):
            return TradingTimeRegime.CLOSING_RUSH
        elif time(15, 30) <= current_time_obj < time(16, 0):
            return TradingTimeRegime.AFTER_HOURS
        else:
            return TradingTimeRegime.AFTER_HOURS
    
    async def _analyze_volatility(self, symbol: str) -> Dict[str, Any]:
        """변동성 분석"""
        try:
            # 최근 20일 데이터 확보 (실제 구현에서는 data_collector 사용)
            if self.data_collector:
                # 실제 데이터 수집
                price_data = await self._get_recent_price_data(symbol, 20)
                daily_returns = self._calculate_daily_returns(price_data)
                current_volatility = np.std(daily_returns) * np.sqrt(252)  # 연환산
            else:
                # 모의 데이터 (개발/테스트용)
                current_volatility = np.random.normal(0.25, 0.05)
            
            # 히스토리 업데이트
            self.volatility_history.append(current_volatility)
            if len(self.volatility_history) > self.max_history_days:
                self.volatility_history.pop(0)
            
            # 백분위 계산
            if len(self.volatility_history) > 5:
                percentile = (np.searchsorted(sorted(self.volatility_history), current_volatility) / 
                            len(self.volatility_history)) * 100
            else:
                percentile = 50.0  # 기본값
            
            # 체제 결정
            if percentile < 20:
                regime = VolatilityRegime.LOW
            elif percentile < 80:
                regime = VolatilityRegime.NORMAL
            elif percentile < 95:
                regime = VolatilityRegime.HIGH
            else:
                regime = VolatilityRegime.EXTREME
            
            # VIX 유사 지표 (0-100)
            vix_equivalent = min(100, max(0, current_volatility * 100))
            
            return {
                'regime': regime,
                'percentile': percentile,
                'vix_equivalent': vix_equivalent,
                'current_volatility': current_volatility
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ 변동성 분석 실패, 기본값 사용: {e}")
            return {
                'regime': VolatilityRegime.NORMAL,
                'percentile': 50.0,
                'vix_equivalent': 25.0,
                'current_volatility': 0.25
            }
    
    async def _calculate_intraday_momentum(self, symbol: str) -> float:
        """장중 모멘텀 계산 (-1 to 1)"""
        try:
            if self.data_collector:
                # 실제 장중 데이터 분석
                intraday_data = await self._get_intraday_data(symbol)
                if intraday_data:
                    # 개장가 대비 현재가 모멘텀
                    open_price = intraday_data['open']
                    current_price = intraday_data['current']
                    momentum = (current_price - open_price) / open_price
                    return np.tanh(momentum * 10)  # -1 to 1 범위로 정규화
            
            # 모의 데이터
            return np.random.uniform(-0.5, 0.5)
            
        except Exception as e:
            self.logger.warning(f"⚠️ 장중 모멘텀 계산 실패: {e}")
            return 0.0
    
    async def _detect_sector_rotation(self) -> bool:
        """섹터 로테이션 감지"""
        try:
            # 실제 구현에서는 섹터별 수익률 분산 분석
            # 현재는 모의 로직
            return np.random.random() > 0.7  # 30% 확률로 활성
        except:
            return False
    
    def _calculate_weight_factors(self, volatility_regime: VolatilityRegime, 
                                time_regime: TradingTimeRegime,
                                market_status: MarketStatus) -> Dict[str, float]:
        """시장 상황에 따른 가중치 조정 팩터 계산"""
        
        # 기본값
        factors = {
            'technical_weight_factor': 1.0,
            'sentiment_weight_factor': 1.0,
            'momentum_weight_factor': 1.0,
            'volume_weight_factor': 1.0
        }
        
        # 변동성에 따른 조정
        if volatility_regime == VolatilityRegime.LOW:
            factors['technical_weight_factor'] = 0.8  # 기술적 분석 비중 감소
            factors['momentum_weight_factor'] = 0.7   # 모멘텀 신호 약화
        elif volatility_regime == VolatilityRegime.HIGH:
            factors['technical_weight_factor'] = 1.2  # 기술적 분석 비중 증가
            factors['sentiment_weight_factor'] = 0.8  # 감성 분석 신뢰도 감소
        elif volatility_regime == VolatilityRegime.EXTREME:
            factors['technical_weight_factor'] = 1.3
            factors['sentiment_weight_factor'] = 0.6
            factors['volume_weight_factor'] = 1.2     # 거래량 분석 중요도 증가
        
        # 시간대에 따른 조정
        if time_regime == TradingTimeRegime.OPENING_RUSH:
            factors['volume_weight_factor'] = 1.3     # 개장 시 거래량 중요
            factors['momentum_weight_factor'] = 1.2
        elif time_regime == TradingTimeRegime.LUNCH_QUIET:
            factors['technical_weight_factor'] = 0.9  # 점심시간 기술적 신호 약화
            factors['volume_weight_factor'] = 0.8
        elif time_regime == TradingTimeRegime.CLOSING_RUSH:
            factors['momentum_weight_factor'] = 1.3   # 마감 시 모멘텀 중요
            factors['volume_weight_factor'] = 1.2
        
        return factors
    
    def _calculate_market_open_minutes(self, current_time: datetime) -> int:
        """개장 후 경과 시간 계산 (분)"""
        market_open = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
        if current_time >= market_open:
            return int((current_time - market_open).total_seconds() / 60)
        return 0
    
    def _determine_market_status_by_time(self, current_time: datetime) -> MarketStatus:
        """시간 기반 시장 상태 판단 (폴백)"""
        current_time_obj = current_time.time()
        weekday = current_time.weekday()
        
        # 주말
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return MarketStatus.WEEKEND
        
        # 평일
        if time(8, 0) <= current_time_obj < time(9, 0):
            return MarketStatus.PRE_MARKET
        elif time(9, 0) <= current_time_obj < time(12, 0):
            return MarketStatus.OPEN
        elif time(12, 0) <= current_time_obj < time(13, 0):
            return MarketStatus.LUNCH_BREAK
        elif time(13, 0) <= current_time_obj < time(15, 30):
            return MarketStatus.OPEN
        elif time(15, 30) <= current_time_obj < time(16, 0):
            return MarketStatus.AFTER_HOURS
        else:
            return MarketStatus.CLOSED
    
    def _get_default_condition(self) -> MarketCondition:
        """기본 시장 상황 반환"""
        return MarketCondition(
            volatility_regime=VolatilityRegime.NORMAL,
            trading_time_regime=TradingTimeRegime.MORNING_STABLE,
            market_status=MarketStatus.OPEN,
            volatility_percentile=50.0,
            vix_equivalent=25.0,
            intraday_momentum=0.0,
            sector_rotation_active=False,
            current_time=datetime.now(),
            market_open_minutes=0,
            technical_weight_factor=1.0,
            sentiment_weight_factor=1.0,
            momentum_weight_factor=1.0,
            volume_weight_factor=1.0
        )
    
    async def _get_recent_price_data(self, symbol: str, days: int) -> pd.DataFrame:
        """최근 가격 데이터 조회 (실제 구현)"""
        # 실제 구현에서는 data_collector를 통해 데이터 수집
        # 현재는 모의 데이터 반환
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        prices = 100 + np.cumsum(np.random.normal(0, 1, days))
        return pd.DataFrame({'date': dates, 'close': prices})
    
    def _calculate_daily_returns(self, price_data: pd.DataFrame) -> np.ndarray:
        """일별 수익률 계산"""
        prices = price_data['close'].values
        returns = np.diff(prices) / prices[:-1]
        return returns
    
    async def _get_intraday_data(self, symbol: str) -> Dict[str, float]:
        """장중 데이터 조회"""
        # 모의 데이터
        return {
            'open': 100.0,
            'current': 101.5,
            'high': 102.0,
            'low': 99.5,
            'volume': 1000000
        }