#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/config/enhanced_trading_config.py

향상된 자동매매 설정 - 요청하신 조건 반영
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class TradingMode(Enum):
    """매매 모드"""
    CONSERVATIVE = "conservative"  # 보수적
    BALANCED = "balanced"         # 균형
    AGGRESSIVE = "aggressive"     # 공격적
    SCALPING = "scalping"        # 스캘핑

class RiskLevel(Enum):
    """리스크 레벨"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"

@dataclass
class TimeFrameConfig:
    """시간대별 설정"""
    enabled: bool
    weight: float
    min_data_points: int
    lookback_period: int

@dataclass
class IndicatorConfig:
    """지표별 설정"""
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    ema_short: int = 20
    ema_long: int = 60
    
    supertrend_period: int = 10
    supertrend_multiplier: float = 2.5
    
    atr_period: int = 14
    atr_multiplier: float = 1.5
    
    bollinger_period: int = 20
    bollinger_std: float = 2.0

@dataclass
class RiskManagementConfig:
    """리스크 관리 설정"""
    # 기본 손절/익절
    default_stop_loss_ratio: float = 0.05    # 5%
    default_take_profit_ratio: float = 0.10   # 10%
    
    # ATR 기반 동적 조정
    use_atr_stops: bool = True
    atr_stop_multiplier: float = 1.5
    atr_profit_multiplier: float = 3.0
    
    # 손익비
    min_risk_reward_ratio: float = 2.0        # 최소 1:2
    max_risk_reward_ratio: float = 4.0        # 최대 1:4
    
    # 포지션 사이징
    max_position_size: float = 0.10          # 계좌의 10%
    max_total_exposure: float = 0.50         # 총 노출 50%
    
    # 상관관계 제한
    max_correlated_positions: int = 3       # 동일 섹터 최대 3개
    
    # 일일 제한
    max_daily_trades: int = 5               # 일일 최대 거래
    max_daily_loss: float = 0.03            # 일일 최대 손실 3%

@dataclass
class EntryConditionsConfig:
    """진입 조건 설정"""
    # 추세 정렬 조건
    require_trend_alignment: bool = True
    min_trend_alignment_score: float = 0.7
    
    # 거래량 조건
    require_volume_confirmation: bool = True
    min_volume_ratio: float = 1.5
    volume_spike_threshold: float = 2.0
    
    # 기술적 지표 조건
    require_technical_confluence: bool = True
    min_indicator_consensus: float = 0.6
    
    # 시간대 필터
    allowed_trading_hours: List[int] = None  # None이면 모든 시간
    avoid_opening_minutes: int = 10         # 개장 후 10분 회피
    avoid_closing_minutes: int = 10         # 마감 전 10분 회피
    
    # 뉴스/이벤트 필터
    avoid_earnings_days: bool = True
    avoid_ex_dividend_days: bool = False
    
    # 변동성 필터
    min_volatility: float = 0.01           # 최소 1% 변동성
    max_volatility: float = 0.08           # 최대 8% 변동성

@dataclass
class ExitConditionsConfig:
    """청산 조건 설정"""
    # 손절 조건
    use_trailing_stop: bool = True
    trailing_stop_distance: float = 0.02    # 2%
    
    # 익절 조건
    use_partial_profit_taking: bool = True
    profit_levels: List[float] = None       # [0.05, 0.10, 0.15] = 5%, 10%, 15%
    profit_percentages: List[float] = None  # [30, 50, 20] = 30%, 50%, 20% 청산
    
    # 추세 전환 감지
    exit_on_trend_reversal: bool = True
    trend_reversal_threshold: float = 0.3
    
    # 시간 기반 청산
    max_holding_period_hours: int = 24      # 최대 보유 24시간
    force_eod_exit: bool = False            # 장마감 전 강제 청산
    
    # 기술적 신호 기반
    exit_on_rsi_extreme: bool = True        # RSI 극값에서 청산
    exit_on_macd_divergence: bool = True    # MACD 다이버전스 시 청산

@dataclass
class FilteringConfig:
    """필터링 조건 설정"""
    # 시장 상황 필터
    avoid_low_volume_markets: bool = True
    min_market_volume_ratio: float = 0.8
    
    # 개별 종목 필터
    min_stock_price: float = 1000           # 최소 주가 1,000원
    max_stock_price: float = 500000         # 최대 주가 50만원
    
    min_market_cap: int = 100000            # 최소 시가총액 1,000억
    min_daily_volume: int = 100000          # 최소 일일 거래량 10만주
    
    # 기술적 필터
    require_liquid_options: bool = False    # 옵션 유동성 요구 안함
    avoid_penny_stocks: bool = True         # 페니스톡 회피
    
    # 업종/테마 필터
    allowed_sectors: List[str] = None       # None이면 모든 업종
    blocked_sectors: List[str] = None       # 제외할 업종
    
    # ESG 필터 (선택사항)
    require_esg_score: bool = False
    min_esg_score: float = 0.0

class EnhancedTradingConfig:
    """향상된 자동매매 통합 설정"""
    
    def __init__(self, mode: TradingMode = TradingMode.BALANCED):
        self.mode = mode
        self.risk_level = self._get_risk_level_for_mode(mode)
        
        # 시간대별 설정
        self.timeframes = self._setup_timeframes()
        
        # 기술적 지표 설정
        self.indicators = self._setup_indicators()
        
        # 리스크 관리
        self.risk_management = self._setup_risk_management()
        
        # 진입 조건
        self.entry_conditions = self._setup_entry_conditions()
        
        # 청산 조건
        self.exit_conditions = self._setup_exit_conditions()
        
        # 필터링 조건
        self.filtering = self._setup_filtering()
        
        # 모드별 세부 조정
        self._adjust_for_mode()

    def _get_risk_level_for_mode(self, mode: TradingMode) -> RiskLevel:
        """모드별 리스크 레벨 반환"""
        mapping = {
            TradingMode.CONSERVATIVE: RiskLevel.LOW,
            TradingMode.BALANCED: RiskLevel.MEDIUM,
            TradingMode.AGGRESSIVE: RiskLevel.HIGH,
            TradingMode.SCALPING: RiskLevel.HIGH
        }
        return mapping.get(mode, RiskLevel.MEDIUM)

    def _setup_timeframes(self) -> Dict[str, TimeFrameConfig]:
        """시간대별 설정 초기화"""
        return {
            "1m": TimeFrameConfig(True, 0.05, 50, 100),
            "3m": TimeFrameConfig(True, 0.10, 50, 100),
            "5m": TimeFrameConfig(True, 0.15, 50, 100),
            "15m": TimeFrameConfig(True, 0.20, 50, 100),
            "30m": TimeFrameConfig(True, 0.25, 50, 100),
            "1h": TimeFrameConfig(True, 0.30, 50, 100),
            "1d": TimeFrameConfig(True, 0.35, 50, 200)
        }

    def _setup_indicators(self) -> IndicatorConfig:
        """기술적 지표 설정 초기화"""
        return IndicatorConfig()

    def _setup_risk_management(self) -> RiskManagementConfig:
        """리스크 관리 설정 초기화"""
        return RiskManagementConfig()

    def _setup_entry_conditions(self) -> EntryConditionsConfig:
        """진입 조건 설정 초기화"""
        config = EntryConditionsConfig()
        config.allowed_trading_hours = list(range(9, 16))  # 9시-15시
        return config

    def _setup_exit_conditions(self) -> ExitConditionsConfig:
        """청산 조건 설정 초기화"""
        config = ExitConditionsConfig()
        config.profit_levels = [0.05, 0.10, 0.15]    # 5%, 10%, 15%
        config.profit_percentages = [30, 50, 20]      # 30%, 50%, 20% 청산
        return config

    def _setup_filtering(self) -> FilteringConfig:
        """필터링 조건 설정 초기화"""
        return FilteringConfig()

    def _adjust_for_mode(self):
        """모드별 세부 조정"""
        if self.mode == TradingMode.CONSERVATIVE:
            self._apply_conservative_settings()
        elif self.mode == TradingMode.AGGRESSIVE:
            self._apply_aggressive_settings()
        elif self.mode == TradingMode.SCALPING:
            self._apply_scalping_settings()
        # BALANCED는 기본 설정 사용

    def _apply_conservative_settings(self):
        """보수적 모드 설정"""
        # 리스크 관리 강화
        self.risk_management.max_position_size = 0.05      # 5%로 축소
        self.risk_management.max_total_exposure = 0.30     # 30%로 축소
        self.risk_management.max_daily_trades = 3          # 일일 3거래로 제한
        
        # 진입 조건 강화
        self.entry_conditions.min_trend_alignment_score = 0.8
        self.entry_conditions.min_volume_ratio = 2.0
        self.entry_conditions.min_indicator_consensus = 0.7
        
        # 필터링 강화
        self.filtering.min_market_cap = 500000             # 5,000억 이상
        self.filtering.min_daily_volume = 200000           # 20만주 이상

    def _apply_aggressive_settings(self):
        """공격적 모드 설정"""
        # 리스크 관리 완화
        self.risk_management.max_position_size = 0.15      # 15%로 확대
        self.risk_management.max_total_exposure = 0.70     # 70%로 확대
        self.risk_management.max_daily_trades = 10         # 일일 10거래
        
        # 진입 조건 완화
        self.entry_conditions.min_trend_alignment_score = 0.6
        self.entry_conditions.min_volume_ratio = 1.2
        self.entry_conditions.min_indicator_consensus = 0.5
        
        # 리워드 증대
        self.risk_management.max_risk_reward_ratio = 5.0

    def _apply_scalping_settings(self):
        """스캘핑 모드 설정"""
        # 단기 시간대 집중
        self.timeframes["1d"].enabled = False
        self.timeframes["1h"].weight = 0.15
        self.timeframes["30m"].weight = 0.20
        self.timeframes["15m"].weight = 0.25
        self.timeframes["5m"].weight = 0.25
        self.timeframes["3m"].weight = 0.15
        
        # 빠른 진입/청산
        self.risk_management.default_stop_loss_ratio = 0.003  # 0.3%
        self.risk_management.default_take_profit_ratio = 0.006 # 0.6%
        
        # 거래 빈도 증가
        self.risk_management.max_daily_trades = 20
        
        # 보유 시간 단축
        self.exit_conditions.max_holding_period_hours = 2   # 2시간
        
        # 트레일링 스톱 강화
        self.exit_conditions.trailing_stop_distance = 0.005 # 0.5%

    def get_strategy_weights_for_market(self, market_condition: str) -> Dict[str, float]:
        """시장 상황별 전략 가중치 반환"""
        if self.mode == TradingMode.SCALPING:
            return {
                "scalping_3m": 0.60,
                "multi_timeframe": 0.25,
                "momentum": 0.15
            }
        
        weights_map = {
            "trending_up": {
                "momentum": 0.35,
                "multi_timeframe": 0.30,
                "supertrend_ema_rsi": 0.25,
                "eod": 0.05,
                "scalping_3m": 0.05
            },
            "trending_down": {
                "multi_timeframe": 0.40,
                "momentum": 0.20,
                "supertrend_ema_rsi": 0.20,
                "eod": 0.10,
                "scalping_3m": 0.10
            },
            "sideways": {
                "scalping_3m": 0.40,
                "multi_timeframe": 0.25,
                "supertrend_ema_rsi": 0.20,
                "momentum": 0.10,
                "eod": 0.05
            },
            "volatile": {
                "scalping_3m": 0.35,
                "multi_timeframe": 0.30,
                "momentum": 0.20,
                "supertrend_ema_rsi": 0.10,
                "eod": 0.05
            }
        }
        
        return weights_map.get(market_condition, weights_map["sideways"])

    def to_dict(self) -> Dict:
        """설정을 딕셔너리로 변환"""
        return {
            "mode": self.mode.value,
            "risk_level": self.risk_level.value,
            "timeframes": {k: v.__dict__ for k, v in self.timeframes.items()},
            "indicators": self.indicators.__dict__,
            "risk_management": self.risk_management.__dict__,
            "entry_conditions": self.entry_conditions.__dict__,
            "exit_conditions": self.exit_conditions.__dict__,
            "filtering": self.filtering.__dict__
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'EnhancedTradingConfig':
        """딕셔너리에서 설정 복원"""
        mode = TradingMode(data.get("mode", "balanced"))
        config = cls(mode)
        
        # 각 섹션별 복원 로직 구현
        if "risk_management" in data:
            for key, value in data["risk_management"].items():
                if hasattr(config.risk_management, key):
                    setattr(config.risk_management, key, value)
        
        if "entry_conditions" in data:
            for key, value in data["entry_conditions"].items():
                if hasattr(config.entry_conditions, key):
                    setattr(config.entry_conditions, key, value)
        
        # 다른 섹션들도 유사하게 복원...
        
        return config

    def validate(self) -> List[str]:
        """설정 유효성 검증"""
        errors = []
        
        # 리스크 관리 검증
        if self.risk_management.max_position_size > 0.5:
            errors.append("포지션 크기가 50%를 초과할 수 없습니다")
        
        if self.risk_management.min_risk_reward_ratio < 1.0:
            errors.append("최소 손익비는 1:1 이상이어야 합니다")
        
        # 시간대 가중치 검증
        total_weight = sum(tf.weight for tf in self.timeframes.values() if tf.enabled)
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"시간대 가중치 합계가 1.0이 아닙니다 (현재: {total_weight:.3f})")
        
        # 기타 검증...
        
        return errors

# 사전 정의된 설정들
PRESET_CONFIGS = {
    "conservative": EnhancedTradingConfig(TradingMode.CONSERVATIVE),
    "balanced": EnhancedTradingConfig(TradingMode.BALANCED),
    "aggressive": EnhancedTradingConfig(TradingMode.AGGRESSIVE),
    "scalping": EnhancedTradingConfig(TradingMode.SCALPING)
}