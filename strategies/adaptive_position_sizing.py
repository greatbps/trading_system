#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/adaptive_position_sizing.py

적응형 포지션 사이징 시스템 - 시장 변동성에 따른 동적 포지션 크기 조정
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger


class VolatilityRegime(Enum):
    """변동성 체제"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskLevel(Enum):
    """리스크 레벨"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class PositionSizeRecommendation:
    """포지션 크기 추천"""
    recommended_size: float  # 추천 포지션 크기 (0.0 - 1.0)
    max_size: float  # 최대 허용 크기
    min_size: float  # 최소 크기
    volatility_adjustment: float  # 변동성 조정 팩터
    correlation_adjustment: float  # 상관관계 조정 팩터
    kelly_fraction: float  # 켈리 공식 기반 크기
    risk_parity_weight: float  # 리스크 패리티 가중치
    confidence: float  # 추천 신뢰도
    reasoning: List[str]  # 결정 근거


@dataclass
class MarketVolatilityMetrics:
    """시장 변동성 지표"""
    current_volatility: float  # 현재 변동성
    historical_volatility: float  # 역사적 변동성
    volatility_percentile: float  # 변동성 백분위
    volatility_regime: VolatilityRegime  # 변동성 체제
    garch_forecast: float  # GARCH 예측 변동성
    realized_volatility: float  # 실현 변동성
    implied_volatility: Optional[float] = None  # 내재 변동성 (옵션 데이터)


class AdaptivePositionSizing:
    """적응형 포지션 사이징 시스템"""
    
    def __init__(self, config, data_collector, portfolio_manager=None):
        self.config = config
        self.data_collector = data_collector
        self.portfolio_manager = portfolio_manager
        self.logger = get_logger("AdaptivePositionSizing")
        
        # 설정 파라미터
        self.base_position_size = config.get('position_sizing', {}).get('base_size', 0.1)
        self.max_position_size = config.get('position_sizing', {}).get('max_size', 0.2)
        self.min_position_size = config.get('position_sizing', {}).get('min_size', 0.01)
        self.volatility_lookback = config.get('position_sizing', {}).get('volatility_lookback', 30)
        self.correlation_threshold = config.get('position_sizing', {}).get('correlation_threshold', 0.7)
        self.kelly_fraction_limit = config.get('position_sizing', {}).get('kelly_limit', 0.25)
        
        # 리스크 파라미터
        self.risk_level = RiskLevel(config.get('position_sizing', {}).get('risk_level', 'moderate'))
        self.max_portfolio_volatility = config.get('position_sizing', {}).get('max_portfolio_vol', 0.15)
        self.target_sharpe_ratio = config.get('position_sizing', {}).get('target_sharpe', 1.5)
        
        # 변동성 체제별 승수
        self.volatility_multipliers = {
            VolatilityRegime.VERY_LOW: 1.5,
            VolatilityRegime.LOW: 1.2,
            VolatilityRegime.MEDIUM: 1.0,
            VolatilityRegime.HIGH: 0.7,
            VolatilityRegime.VERY_HIGH: 0.4
        }
        
        # 리스크 레벨별 승수
        self.risk_multipliers = {
            RiskLevel.CONSERVATIVE: 0.6,
            RiskLevel.MODERATE: 1.0,
            RiskLevel.AGGRESSIVE: 1.4
        }
        
        self.logger.info("📊 적응형 포지션 사이징 시스템 초기화 완료")
    
    async def calculate_position_size(self, symbol: str, signal_strength: float, 
                                    expected_return: float, stop_loss_distance: float,
                                    portfolio_context: Dict = None) -> PositionSizeRecommendation:
        """메인 포지션 크기 계산"""
        try:
            self.logger.debug(f"📏 {symbol} 포지션 크기 계산 시작")
            
            # 1. 시장 변동성 분석
            volatility_metrics = await self._analyze_market_volatility(symbol)
            
            # 2. 포트폴리오 상관관계 분석
            correlation_metrics = await self._analyze_portfolio_correlations(symbol, portfolio_context)
            
            # 3. 켈리 공식 기반 최적 크기
            kelly_size = await self._calculate_kelly_fraction(
                expected_return, stop_loss_distance, volatility_metrics
            )
            
            # 4. 리스크 패리티 가중치
            risk_parity_weight = await self._calculate_risk_parity_weight(
                symbol, volatility_metrics, portfolio_context
            )
            
            # 5. 변동성 조정
            volatility_adjustment = self._calculate_volatility_adjustment(volatility_metrics)
            
            # 6. 상관관계 조정
            correlation_adjustment = self._calculate_correlation_adjustment(correlation_metrics)
            
            # 7. 신호 강도 조정
            signal_adjustment = self._calculate_signal_adjustment(signal_strength)
            
            # 8. 최종 포지션 크기 계산
            base_size = self.base_position_size
            adjusted_size = (
                base_size * 
                volatility_adjustment * 
                correlation_adjustment * 
                signal_adjustment *
                self.risk_multipliers[self.risk_level]
            )
            
            # 켈리 공식과 리스크 패리티 고려
            kelly_adjusted_size = min(kelly_size, adjusted_size)
            final_size = (kelly_adjusted_size * 0.7 + risk_parity_weight * 0.3)
            
            # 제한 적용
            final_size = max(self.min_position_size, min(self.max_position_size, final_size))
            
            # 추천 객체 생성
            recommendation = PositionSizeRecommendation(
                recommended_size=final_size,
                max_size=self.max_position_size,
                min_size=self.min_position_size,
                volatility_adjustment=volatility_adjustment,
                correlation_adjustment=correlation_adjustment,
                kelly_fraction=kelly_size,
                risk_parity_weight=risk_parity_weight,
                confidence=self._calculate_confidence(volatility_metrics, correlation_metrics),
                reasoning=self._generate_reasoning(
                    volatility_metrics, correlation_metrics, signal_strength, 
                    volatility_adjustment, correlation_adjustment
                )
            )
            
            self.logger.info(f"✅ {symbol} 포지션 크기: {final_size:.3f} (신뢰도: {recommendation.confidence:.2f})")
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 포지션 크기 계산 실패: {e}")
            return self._create_fallback_recommendation()
    
    async def _analyze_market_volatility(self, symbol: str) -> MarketVolatilityMetrics:
        """시장 변동성 분석"""
        try:
            # 역사적 가격 데이터 수집
            price_data = await self.data_collector.get_historical_data(
                symbol, period='6M', interval='1D'
            )
            
            if not price_data or len(price_data) < self.volatility_lookback:
                return self._create_default_volatility_metrics()
            
            prices = np.array([float(item['close']) for item in price_data])
            returns = np.diff(np.log(prices))
            
            # 현재 변동성 (최근 30일)
            recent_returns = returns[-self.volatility_lookback:]
            current_volatility = np.std(recent_returns) * np.sqrt(252)  # 연환산
            
            # 역사적 변동성 (전체 기간)
            historical_volatility = np.std(returns) * np.sqrt(252)
            
            # 변동성 백분위 계산
            rolling_volatility = []
            for i in range(self.volatility_lookback, len(returns)):
                window_returns = returns[i-self.volatility_lookback:i]
                vol = np.std(window_returns) * np.sqrt(252)
                rolling_volatility.append(vol)
            
            volatility_percentile = (np.sum(np.array(rolling_volatility) < current_volatility) / 
                                   len(rolling_volatility)) * 100
            
            # GARCH 예측 (간단한 근사)
            garch_forecast = self._simple_garch_forecast(returns)
            
            # 실현 변동성
            realized_volatility = np.sqrt(np.sum(recent_returns**2)) * np.sqrt(252)
            
            # 변동성 체제 결정
            volatility_regime = self._determine_volatility_regime(volatility_percentile)
            
            return MarketVolatilityMetrics(
                current_volatility=current_volatility,
                historical_volatility=historical_volatility,
                volatility_percentile=volatility_percentile,
                volatility_regime=volatility_regime,
                garch_forecast=garch_forecast,
                realized_volatility=realized_volatility
            )
            
        except Exception as e:
            self.logger.error(f"❌ 변동성 분석 실패: {e}")
            return self._create_default_volatility_metrics()
    
    async def _analyze_portfolio_correlations(self, symbol: str, portfolio_context: Dict = None) -> Dict[str, float]:
        """포트폴리오 상관관계 분석"""
        try:
            if not portfolio_context or 'positions' not in portfolio_context:
                return {'average_correlation': 0.0, 'max_correlation': 0.0, 'correlation_risk': 0.0}
            
            correlations = []
            
            # 현재 포트폴리오 종목들과의 상관관계 계산
            for existing_symbol in portfolio_context['positions'].keys():
                if existing_symbol != symbol:
                    correlation = await self._calculate_correlation(symbol, existing_symbol)
                    if correlation is not None:
                        correlations.append(correlation)
            
            if not correlations:
                return {'average_correlation': 0.0, 'max_correlation': 0.0, 'correlation_risk': 0.0}
            
            avg_correlation = np.mean(correlations)
            max_correlation = np.max(correlations)
            correlation_risk = np.sum(np.array(correlations) > self.correlation_threshold) / len(correlations)
            
            return {
                'average_correlation': avg_correlation,
                'max_correlation': max_correlation,
                'correlation_risk': correlation_risk,
                'correlations': correlations
            }
            
        except Exception as e:
            self.logger.error(f"❌ 상관관계 분석 실패: {e}")
            return {'average_correlation': 0.0, 'max_correlation': 0.0, 'correlation_risk': 0.0}
    
    async def _calculate_correlation(self, symbol1: str, symbol2: str, period: str = '3M') -> Optional[float]:
        """두 종목 간 상관관계 계산"""
        try:
            # 두 종목의 가격 데이터 수집
            data1 = await self.data_collector.get_historical_data(symbol1, period=period, interval='1D')
            data2 = await self.data_collector.get_historical_data(symbol2, period=period, interval='1D')
            
            if not data1 or not data2 or len(data1) < 30 or len(data2) < 30:
                return None
            
            # 공통 날짜 찾기 (간단한 구현)
            min_length = min(len(data1), len(data2))
            
            prices1 = np.array([float(item['close']) for item in data1[-min_length:]])
            prices2 = np.array([float(item['close']) for item in data2[-min_length:]])
            
            returns1 = np.diff(np.log(prices1))
            returns2 = np.diff(np.log(prices2))
            
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.warning(f"⚠️ {symbol1}-{symbol2} 상관관계 계산 실패: {e}")
            return None
    
    async def _calculate_kelly_fraction(self, expected_return: float, stop_loss_distance: float,
                                      volatility_metrics: MarketVolatilityMetrics) -> float:
        """켈리 공식 기반 최적 포지션 크기"""
        try:
            if stop_loss_distance <= 0 or volatility_metrics.current_volatility <= 0:
                return self.base_position_size
            
            # 승률 추정 (신호 강도와 변동성 기반)
            win_probability = max(0.4, min(0.7, 0.5 + expected_return / (2 * volatility_metrics.current_volatility)))
            
            # 평균 손실 대비 평균 이익 비율
            win_loss_ratio = abs(expected_return) / stop_loss_distance if stop_loss_distance > 0 else 1.0
            
            # 켈리 공식: f = (bp - q) / b
            # b = win_loss_ratio, p = win_probability, q = 1 - p
            kelly_fraction = (win_loss_ratio * win_probability - (1 - win_probability)) / win_loss_ratio
            
            # 제한 적용
            kelly_fraction = max(0.0, min(self.kelly_fraction_limit, kelly_fraction))
            
            return kelly_fraction
            
        except Exception as e:
            self.logger.error(f"❌ 켈리 공식 계산 실패: {e}")
            return self.base_position_size
    
    async def _calculate_risk_parity_weight(self, symbol: str, volatility_metrics: MarketVolatilityMetrics,
                                          portfolio_context: Dict = None) -> float:
        """리스크 패리티 가중치 계산"""
        try:
            if not portfolio_context or 'positions' not in portfolio_context:
                return self.base_position_size
            
            # 현재 종목의 변동성
            target_volatility = volatility_metrics.current_volatility
            
            if target_volatility <= 0:
                return self.base_position_size
            
            # 목표 리스크 기여도
            num_positions = len(portfolio_context['positions']) + 1  # 새 포지션 포함
            target_risk_contribution = 1.0 / num_positions
            
            # 포트폴리오 전체 변동성 대비 비중 계산
            portfolio_volatility = self._estimate_portfolio_volatility(portfolio_context)
            
            if portfolio_volatility <= 0:
                return self.base_position_size
            
            # 리스크 패리티 가중치
            risk_parity_weight = target_risk_contribution * (portfolio_volatility / target_volatility)
            
            # 제한 적용
            return max(self.min_position_size, min(self.max_position_size, risk_parity_weight))
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 패리티 계산 실패: {e}")
            return self.base_position_size
    
    def _calculate_volatility_adjustment(self, volatility_metrics: MarketVolatilityMetrics) -> float:
        """변동성 기반 조정"""
        try:
            base_multiplier = self.volatility_multipliers[volatility_metrics.volatility_regime]
            
            # 변동성 백분위 기반 미세 조정
            percentile_adjustment = 1.0
            if volatility_metrics.volatility_percentile > 80:
                percentile_adjustment = 0.8
            elif volatility_metrics.volatility_percentile > 60:
                percentile_adjustment = 0.9
            elif volatility_metrics.volatility_percentile < 20:
                percentile_adjustment = 1.2
            elif volatility_metrics.volatility_percentile < 40:
                percentile_adjustment = 1.1
            
            return base_multiplier * percentile_adjustment
            
        except Exception as e:
            self.logger.error(f"❌ 변동성 조정 계산 실패: {e}")
            return 1.0
    
    def _calculate_correlation_adjustment(self, correlation_metrics: Dict[str, float]) -> float:
        """상관관계 기반 조정"""
        try:
            correlation_risk = correlation_metrics.get('correlation_risk', 0.0)
            max_correlation = correlation_metrics.get('max_correlation', 0.0)
            
            # 높은 상관관계일수록 포지션 크기 감소
            if max_correlation > 0.8:
                correlation_adjustment = 0.6
            elif max_correlation > 0.6:
                correlation_adjustment = 0.8
            elif correlation_risk > 0.5:
                correlation_adjustment = 0.7
            elif correlation_risk > 0.3:
                correlation_adjustment = 0.9
            else:
                correlation_adjustment = 1.0
            
            return correlation_adjustment
            
        except Exception as e:
            self.logger.error(f"❌ 상관관계 조정 계산 실패: {e}")
            return 1.0
    
    def _calculate_signal_adjustment(self, signal_strength: float) -> float:
        """신호 강도 기반 조정"""
        try:
            # 신호 강도가 높을수록 포지션 크기 증가
            if signal_strength > 0.8:
                return 1.3
            elif signal_strength > 0.6:
                return 1.1
            elif signal_strength > 0.4:
                return 1.0
            elif signal_strength > 0.2:
                return 0.8
            else:
                return 0.6
                
        except Exception as e:
            self.logger.error(f"❌ 신호 조정 계산 실패: {e}")
            return 1.0
    
    def _simple_garch_forecast(self, returns: np.ndarray, alpha: float = 0.1, beta: float = 0.85) -> float:
        """간단한 GARCH 변동성 예측"""
        try:
            if len(returns) < 10:
                return np.std(returns) * np.sqrt(252)
            
            # 장기 평균 변동성
            long_term_var = np.var(returns)
            
            # 최근 변동성
            recent_var = returns[-1]**2
            
            # 이전 예측 변동성 (간단히 이전 기간 변동성 사용)
            prev_var = np.var(returns[-10:])
            
            # GARCH(1,1) 예측
            forecast_var = (1 - alpha - beta) * long_term_var + alpha * recent_var + beta * prev_var
            
            return np.sqrt(forecast_var * 252)
            
        except Exception as e:
            self.logger.error(f"❌ GARCH 예측 실패: {e}")
            return np.std(returns) * np.sqrt(252)
    
    def _determine_volatility_regime(self, volatility_percentile: float) -> VolatilityRegime:
        """변동성 체제 결정"""
        if volatility_percentile >= 90:
            return VolatilityRegime.VERY_HIGH
        elif volatility_percentile >= 70:
            return VolatilityRegime.HIGH
        elif volatility_percentile >= 30:
            return VolatilityRegime.MEDIUM
        elif volatility_percentile >= 10:
            return VolatilityRegime.LOW
        else:
            return VolatilityRegime.VERY_LOW
    
    def _estimate_portfolio_volatility(self, portfolio_context: Dict) -> float:
        """포트폴리오 전체 변동성 추정"""
        try:
            if not portfolio_context or 'positions' not in portfolio_context:
                return 0.15  # 기본값
            
            # 간단한 구현: 평균 변동성 사용
            # 실제로는 상관관계 매트릭스를 사용해야 함
            return 0.15  # 임시 값
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 변동성 추정 실패: {e}")
            return 0.15
    
    def _calculate_confidence(self, volatility_metrics: MarketVolatilityMetrics, 
                            correlation_metrics: Dict[str, float]) -> float:
        """추천 신뢰도 계산"""
        try:
            confidence = 0.5  # 기본 신뢰도
            
            # 변동성 데이터 품질
            if volatility_metrics.volatility_percentile > 0:
                confidence += 0.2
            
            # 상관관계 데이터 품질
            if 'correlations' in correlation_metrics and len(correlation_metrics['correlations']) > 0:
                confidence += 0.2
            
            # 체제의 명확성
            if volatility_metrics.volatility_regime in [VolatilityRegime.VERY_LOW, VolatilityRegime.VERY_HIGH]:
                confidence += 0.1
            
            return min(1.0, confidence)
            
        except Exception as e:
            self.logger.error(f"❌ 신뢰도 계산 실패: {e}")
            return 0.5
    
    def _generate_reasoning(self, volatility_metrics: MarketVolatilityMetrics,
                          correlation_metrics: Dict[str, float], signal_strength: float,
                          volatility_adjustment: float, correlation_adjustment: float) -> List[str]:
        """결정 근거 생성"""
        reasoning = []
        
        reasoning.append(f"변동성 체제: {volatility_metrics.volatility_regime.value}")
        reasoning.append(f"현재 변동성: {volatility_metrics.current_volatility:.3f}")
        reasoning.append(f"변동성 백분위: {volatility_metrics.volatility_percentile:.1f}%")
        reasoning.append(f"변동성 조정: {volatility_adjustment:.2f}x")
        
        max_corr = correlation_metrics.get('max_correlation', 0.0)
        reasoning.append(f"최대 상관관계: {max_corr:.2f}")
        reasoning.append(f"상관관계 조정: {correlation_adjustment:.2f}x")
        
        reasoning.append(f"신호 강도: {signal_strength:.2f}")
        reasoning.append(f"리스크 레벨: {self.risk_level.value}")
        
        return reasoning
    
    def _create_default_volatility_metrics(self) -> MarketVolatilityMetrics:
        """기본 변동성 지표"""
        return MarketVolatilityMetrics(
            current_volatility=0.20,
            historical_volatility=0.20,
            volatility_percentile=50.0,
            volatility_regime=VolatilityRegime.MEDIUM,
            garch_forecast=0.20,
            realized_volatility=0.20
        )
    
    def _create_fallback_recommendation(self) -> PositionSizeRecommendation:
        """폴백 추천"""
        return PositionSizeRecommendation(
            recommended_size=self.base_position_size,
            max_size=self.max_position_size,
            min_size=self.min_position_size,
            volatility_adjustment=1.0,
            correlation_adjustment=1.0,
            kelly_fraction=self.base_position_size,
            risk_parity_weight=self.base_position_size,
            confidence=0.5,
            reasoning=["기본값 사용 (데이터 부족)"]
        )