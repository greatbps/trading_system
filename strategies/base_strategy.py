#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/base_strategy.py

전략 기본 클래스 - 강화된 리스크 관리 및 포지션 사이징
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from utils.logger import get_logger


class SignalType(Enum):
    """신호 유형"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    WEAK_BUY = "WEAK_BUY"
    WEAK_SELL = "WEAK_SELL"


class RiskLevel(Enum):
    """리스크 레벨"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class Signal:
    """매매 신호 데이터 클래스"""
    signal_type: SignalType
    confidence: float  # 0.0 - 1.0
    strength: float    # 0.0 - 100.0
    risk_level: RiskLevel
    metadata: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'signal_type': self.signal_type.value,
            'confidence': self.confidence,
            'strength': self.strength,
            'risk_level': self.risk_level.value,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class BaseStrategy(ABC):
    """전략 기본 클래스 - 강화된 리스크 관리"""

    def __init__(self, config):
        self.config = config
        self.logger = get_logger(f"Strategy_{self.__class__.__name__}")
        self.name = self.__class__.__name__

        # 리스크 관리 설정
        self.risk_params = {
            'max_position_risk': 0.02,    # 포지션당 최대 리스크 (2%)
            'max_daily_risk': 0.05,       # 일일 최대 리스크 (5%)
            'volatility_lookback': 20,    # 변동성 계산 기간
            'atr_multiplier': 2.0,        # ATR 기반 손절 배수
            'risk_free_rate': 0.03,       # 무위험 수익률 (3%)
            'sharpe_threshold': 1.5       # 최소 샤프 비율
        }

        # 포지션 사이징 모델
        self.position_models = {
            'fixed_fractional': self._calculate_fixed_fractional,
            'kelly_criterion': self._calculate_kelly_criterion,
            'risk_parity': self._calculate_risk_parity,
            'volatility_adjusted': self._calculate_volatility_adjusted
        }

        # 기본 포지션 사이징 모델
        self.default_sizing_model = 'volatility_adjusted'
        
    @abstractmethod
    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """매매 신호 생성 (추상 메서드)"""
        pass
    
    async def calculate_position_size(self, signal: Dict, account_info: Dict,
                                    price_data: List[Dict] = None, model: str = None) -> Dict[str, Any]:
        """고급 포지션 크기 계산"""
        try:
            # 포지션 사이징 모델 선택
            sizing_model = model or self.default_sizing_model

            if sizing_model not in self.position_models:
                self.logger.warning(f"⚠️ 알 수 없는 포지션 모델: {sizing_model}, 기본 모델 사용")
                sizing_model = self.default_sizing_model

            # 계좌 정보 추출
            account_balance = account_info.get('available_amount', 0)
            current_positions = account_info.get('current_positions', 0)
            max_positions = self.config.trading.MAX_POSITIONS

            # 기본 검증
            if account_balance <= 0:
                return self._create_zero_position("계좌 잔고 부족")

            if current_positions >= max_positions:
                return self._create_zero_position("최대 포지션 수 초과")

            # 신호 정보 추출
            signal_strength = signal.get('signal_strength', 50)
            confidence = signal.get('confidence', 0.5)
            risk_level = signal.get('risk_level', 'MEDIUM')

            # 포지션 사이징 모델 실행
            sizing_func = self.position_models[sizing_model]
            position_info = await sizing_func(
                signal, account_info, price_data, account_balance
            )

            # 추가 안전 검증
            position_info = self._apply_safety_limits(position_info, account_balance)

            self.logger.info(f"✅ 포지션 계산 완료 ({sizing_model}): {position_info['position_amount']:,}원")

            return position_info

        except Exception as e:
            self.logger.error(f"❌ 포지션 크기 계산 실패: {e}")
            return self._create_zero_position(f"계산 오류: {str(e)}")

    async def _calculate_volatility_adjusted(self, signal: Dict, account_info: Dict,
                                           price_data: List[Dict], account_balance: float) -> Dict[str, Any]:
        """변동성 조정 포지션 사이징"""
        try:
            # 변동성 계산
            volatility = self._calculate_volatility(price_data)

            # 신호 정보
            confidence = signal.get('confidence', 0.5)
            risk_level = signal.get('risk_level', 'MEDIUM')

            # 기본 리스크 예산 (계좌의 2%)
            risk_budget = account_balance * self.risk_params['max_position_risk']

            # 리스크 레벨에 따른 조정
            risk_multipliers = {
                'LOW': 1.2,
                'MEDIUM': 1.0,
                'HIGH': 0.7,
                'EXTREME': 0.4
            }
            risk_multiplier = risk_multipliers.get(risk_level, 1.0)

            # 변동성 조정 (변동성이 높을수록 포지션 크기 감소)
            volatility_factor = max(0.3, min(1.5, 1.0 / (1.0 + volatility)))

            # 신뢰도 조정
            confidence_factor = 0.5 + (confidence * 0.5)  # 0.5 ~ 1.0 범위

            # 최종 포지션 금액 계산
            position_amount = (
                risk_budget *
                risk_multiplier *
                volatility_factor *
                confidence_factor
            )

            return {
                'position_amount': int(position_amount),
                'sizing_model': 'volatility_adjusted',
                'risk_budget': int(risk_budget),
                'volatility': volatility,
                'volatility_factor': volatility_factor,
                'confidence_factor': confidence_factor,
                'risk_multiplier': risk_multiplier,
                'reason': 'volatility_adjusted_calculation'
            }

        except Exception as e:
            self.logger.error(f"❌ 변동성 조정 계산 실패: {e}")
            return self._create_zero_position(f"변동성 계산 오류: {str(e)}")

    async def _calculate_fixed_fractional(self, signal: Dict, account_info: Dict,
                                        price_data: List[Dict], account_balance: float) -> Dict[str, Any]:
        """고정 비율 포지션 사이징"""
        try:
            # 기본 비율 (계좌의 15%)
            base_fraction = 0.15

            # 신호 강도에 따른 조정
            signal_strength = signal.get('signal_strength', 50)
            strength_factor = signal_strength / 100

            # 신뢰도 조정
            confidence = signal.get('confidence', 0.5)

            # 최종 포지션 금액
            position_amount = account_balance * base_fraction * strength_factor * confidence

            return {
                'position_amount': int(position_amount),
                'sizing_model': 'fixed_fractional',
                'base_fraction': base_fraction,
                'strength_factor': strength_factor,
                'confidence': confidence,
                'reason': 'fixed_fractional_calculation'
            }

        except Exception as e:
            return self._create_zero_position(f"고정비율 계산 오류: {str(e)}")

    async def _calculate_kelly_criterion(self, signal: Dict, account_info: Dict,
                                       price_data: List[Dict], account_balance: float) -> Dict[str, Any]:
        """켈리 기준 포지션 사이징 (간단 버전)"""
        try:
            # 승률과 평균 손익비 추정 (실제로는 백테스팅 데이터 필요)
            estimated_win_rate = 0.55  # 55% 승률 가정
            estimated_avg_win = 0.08   # 평균 8% 수익
            estimated_avg_loss = 0.04  # 평균 4% 손실

            # 켈리 비율 계산: f = (bp - q) / b
            # b = 평균수익/평균손실, p = 승률, q = 패률
            b = estimated_avg_win / estimated_avg_loss
            p = estimated_win_rate
            q = 1 - p

            kelly_fraction = (b * p - q) / b

            # 안전을 위해 25% 축소 (Quarter Kelly)
            safe_kelly = kelly_fraction * 0.25

            # 신뢰도로 추가 조정
            confidence = signal.get('confidence', 0.5)
            adjusted_kelly = safe_kelly * confidence

            # 최대 20%로 제한
            final_fraction = max(0, min(0.2, adjusted_kelly))

            position_amount = account_balance * final_fraction

            return {
                'position_amount': int(position_amount),
                'sizing_model': 'kelly_criterion',
                'kelly_fraction': kelly_fraction,
                'safe_kelly': safe_kelly,
                'final_fraction': final_fraction,
                'estimated_win_rate': estimated_win_rate,
                'reason': 'kelly_criterion_calculation'
            }

        except Exception as e:
            return self._create_zero_position(f"켈리기준 계산 오류: {str(e)}")

    async def _calculate_risk_parity(self, signal: Dict, account_info: Dict,
                                   price_data: List[Dict], account_balance: float) -> Dict[str, Any]:
        """리스크 패리티 포지션 사이징"""
        try:
            # 변동성 계산
            volatility = self._calculate_volatility(price_data)

            # 목표 변동성 (연 15%)
            target_volatility = 0.15

            # 리스크 예산 (계좌의 2%)
            risk_budget = account_balance * self.risk_params['max_position_risk']

            # 변동성 기반 포지션 크기 조정
            if volatility > 0:
                volatility_adjusted_size = (target_volatility / volatility) * risk_budget
            else:
                volatility_adjusted_size = risk_budget

            # 신뢰도 조정
            confidence = signal.get('confidence', 0.5)
            position_amount = volatility_adjusted_size * confidence

            return {
                'position_amount': int(position_amount),
                'sizing_model': 'risk_parity',
                'volatility': volatility,
                'target_volatility': target_volatility,
                'risk_budget': int(risk_budget),
                'confidence': confidence,
                'reason': 'risk_parity_calculation'
            }

        except Exception as e:
            return self._create_zero_position(f"리스크패리티 계산 오류: {str(e)}")

    def _calculate_volatility(self, price_data: List[Dict], period: int = 20) -> float:
        """가격 변동성 계산 (연환산)"""
        try:
            if not price_data or len(price_data) < 2:
                return 0.2  # 기본 변동성 20%

            # 수익률 계산
            prices = [float(d['close']) for d in price_data[-period-1:]]
            returns = []

            for i in range(1, len(prices)):
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

            if len(returns) < 2:
                return 0.2

            # 일간 변동성 계산
            daily_volatility = np.std(returns)

            # 연환산 (√252)
            annual_volatility = daily_volatility * np.sqrt(252)

            return float(annual_volatility)

        except Exception:
            return 0.2  # 기본값

    def _apply_safety_limits(self, position_info: Dict, account_balance: float) -> Dict[str, Any]:
        """안전 한도 적용"""
        try:
            position_amount = position_info.get('position_amount', 0)

            # 최대 한도 (계좌의 40%)
            max_amount = account_balance * 0.4

            # 최소 한도 (10,000원)
            min_amount = 10000

            # 한도 적용
            if position_amount > max_amount:
                position_info['position_amount'] = int(max_amount)
                position_info['limited_by'] = 'max_limit'
            elif position_amount < min_amount:
                position_info['position_amount'] = 0
                position_info['limited_by'] = 'min_limit'

            return position_info

        except Exception:
            return self._create_zero_position("안전한도 적용 오류")

    def _create_zero_position(self, reason: str) -> Dict[str, Any]:
        """제로 포지션 생성"""
        return {
            'position_amount': 0,
            'sizing_model': 'none',
            'reason': reason,
            'limited_by': 'safety_check'
        }
    
    async def calculate_stop_loss(self, stock_data: Dict, entry_price: float) -> float:
        """손절가 계산 (기본 구현)"""
        return entry_price * (1 - self.config.trading.STOP_LOSS_RATIO)
    
    async def calculate_take_profit(self, stock_data: Dict, entry_price: float) -> float:
        """익절가 계산 (기본 구현)"""
        return entry_price * (1 + self.config.trading.TAKE_PROFIT_RATIO)
    
    def validate_signal(self, signal: Dict) -> bool:
        """신호 유효성 검사"""
        required_fields = ['signal_strength', 'signal_type', 'action', 'confidence']
        return all(field in signal for field in required_fields)