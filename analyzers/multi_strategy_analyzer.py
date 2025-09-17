#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/multi_strategy_analyzer.py

다중 전략 조합 분석기 - 7개 전략의 신호를 통합하여 최종 매매 결정 지원
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class StrategyWeight(Enum):
    """전략별 가중치 타입"""
    EQUAL = "equal"           # 동일 가중치
    PERFORMANCE = "performance"  # 성과 기반 가중치
    VOLATILITY = "volatility"    # 변동성 기반 가중치
    CORRELATION = "correlation"  # 상관관계 기반 가중치
    ADAPTIVE = "adaptive"        # 적응형 가중치


@dataclass
class StrategySignal:
    """개별 전략 신호"""
    strategy_name: str
    action: str
    confidence: float
    score: float
    reasons: List[str]
    target_profit_rate: float
    stop_loss_rate: Optional[float] = None
    holding_period: str = ""
    analysis_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MultiStrategyResult:
    """다중 전략 분석 결과"""
    symbol: str
    final_action: str
    final_confidence: float
    consensus_score: float
    individual_signals: List[StrategySignal]
    weight_distribution: Dict[str, float]
    risk_assessment: Dict[str, Any]
    portfolio_recommendation: Dict[str, Any]
    execution_priority: int  # 1=최고우선순위, 5=최저우선순위
    timestamp: datetime = field(default_factory=datetime.now)


class MultiStrategyAnalyzer:
    """다중 전략 조합 분석기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 전략별 기본 가중치 (과거 성과 기반 초기값)
        self.default_weights = {
            'momentum': 0.18,           # 모멘텀 전략 (높은 수익률)
            'breakout': 0.16,          # 돌파 전략 (중-높은 수익률)
            'supertrend_ema_rsi': 0.15, # SuperTrend (안정적)
            'rsi': 0.14,               # RSI 전략 (새로 완성, 검증 필요)
            'scalping_3m': 0.13,       # 3분봉 스캘핑 (새로 완성, 검증 필요)
            'vwap': 0.12,              # VWAP (안정적, 보수적)
            'eod': 0.12                # EOD (중장기, 안정적)
        }
        
        # 시장 상황별 전략 선호도
        self.market_regime_weights = {
            'bull_market': {  # 강세장
                'momentum': 0.25, 'breakout': 0.20, 'scalping_3m': 0.15,
                'supertrend_ema_rsi': 0.15, 'rsi': 0.10, 'vwap': 0.08, 'eod': 0.07
            },
            'bear_market': {  # 약세장
                'rsi': 0.22, 'vwap': 0.20, 'eod': 0.18,
                'supertrend_ema_rsi': 0.15, 'momentum': 0.10, 'breakout': 0.08, 'scalping_3m': 0.07
            },
            'sideways': {    # 횡보장
                'scalping_3m': 0.20, 'rsi': 0.18, 'vwap': 0.16,
                'supertrend_ema_rsi': 0.15, 'eod': 0.12, 'momentum': 0.10, 'breakout': 0.09
            }
        }
        
        self.logger.info("✅ 다중 전략 분석기 초기화 완료")
    
    async def analyze_multi_strategy_signals(
        self, 
        symbol: str, 
        individual_signals: List[StrategySignal],
        market_regime: str = "sideways",
        weight_type: StrategyWeight = StrategyWeight.ADAPTIVE
    ) -> MultiStrategyResult:
        """다중 전략 신호 종합 분석"""
        try:
            self.logger.info(f"📊 {symbol} 다중 전략 분석 시작 ({len(individual_signals)}개 전략)")
            
            if not individual_signals:
                return self._create_neutral_result(symbol, "신호 없음")
            
            # 1. 전략별 가중치 계산
            weights = await self._calculate_strategy_weights(
                individual_signals, market_regime, weight_type
            )
            
            # 2. 가중평균 신호 계산
            consensus_result = await self._calculate_consensus_signal(
                individual_signals, weights
            )
            
            # 3. 리스크 평가
            risk_assessment = await self._assess_multi_strategy_risk(
                individual_signals, consensus_result
            )
            
            # 4. 포트폴리오 추천
            portfolio_recommendation = await self._generate_portfolio_recommendation(
                symbol, consensus_result, risk_assessment
            )
            
            # 5. 실행 우선순위 결정
            execution_priority = self._determine_execution_priority(
                consensus_result, risk_assessment
            )
            
            result = MultiStrategyResult(
                symbol=symbol,
                final_action=consensus_result['action'],
                final_confidence=consensus_result['confidence'],
                consensus_score=consensus_result['score'],
                individual_signals=individual_signals,
                weight_distribution=weights,
                risk_assessment=risk_assessment,
                portfolio_recommendation=portfolio_recommendation,
                execution_priority=execution_priority
            )
            
            self.logger.info(f"✅ {symbol} 다중 전략 분석 완료: {result.final_action} (신뢰도: {result.final_confidence:.1f}%)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 다중 전략 분석 실패: {e}")
            return self._create_neutral_result(symbol, f"분석 오류: {str(e)}")
    
    async def _calculate_strategy_weights(
        self, 
        signals: List[StrategySignal], 
        market_regime: str,
        weight_type: StrategyWeight
    ) -> Dict[str, float]:
        """전략별 가중치 계산"""
        try:
            if weight_type == StrategyWeight.EQUAL:
                # 동일 가중치
                num_strategies = len(signals)
                return {signal.strategy_name: 1.0/num_strategies for signal in signals}
            
            elif weight_type == StrategyWeight.PERFORMANCE:
                # 성과 기반 가중치 (기본 가중치 사용)
                return {signal.strategy_name: self.default_weights.get(signal.strategy_name, 0.1) 
                       for signal in signals}
            
            elif weight_type == StrategyWeight.VOLATILITY:
                # 변동성 기반 가중치 (안정적인 전략에 높은 가중치)
                volatility_weights = {
                    'vwap': 0.20, 'eod': 0.18, 'supertrend_ema_rsi': 0.16,
                    'rsi': 0.15, 'momentum': 0.12, 'breakout': 0.10, 'scalping_3m': 0.09
                }
                return {signal.strategy_name: volatility_weights.get(signal.strategy_name, 0.1) 
                       for signal in signals}
            
            elif weight_type == StrategyWeight.CORRELATION:
                # 상관관계 기반 가중치 (상관성 낮은 전략에 높은 가중치)
                correlation_weights = {
                    'scalping_3m': 0.18, 'eod': 0.17, 'vwap': 0.16,
                    'rsi': 0.15, 'supertrend_ema_rsi': 0.14, 'momentum': 0.11, 'breakout': 0.09
                }
                return {signal.strategy_name: correlation_weights.get(signal.strategy_name, 0.1) 
                       for signal in signals}
            
            else:  # ADAPTIVE
                # 적응형 가중치: 시장 상황 + 신호 강도 조합
                regime_weights = self.market_regime_weights.get(market_regime, self.default_weights)
                
                # 신호 강도에 따른 동적 조정
                adjusted_weights = {}
                total_adjustment = 0
                
                for signal in signals:
                    base_weight = regime_weights.get(signal.strategy_name, 0.1)
                    
                    # 신호 강도에 따른 조정 (-1.0 ~ +1.0)
                    strength_factor = min(max(signal.score / 100.0, -1.0), 1.0)
                    
                    # 신뢰도에 따른 조정
                    confidence_factor = signal.confidence / 100.0
                    
                    # 조정된 가중치 = 기본 가중치 * (1 + 0.3 * 강도 * 신뢰도)
                    adjustment = 0.3 * strength_factor * confidence_factor
                    adjusted_weight = base_weight * (1 + adjustment)
                    
                    adjusted_weights[signal.strategy_name] = adjusted_weight
                    total_adjustment += adjusted_weight
                
                # 정규화
                if total_adjustment > 0:
                    for strategy in adjusted_weights:
                        adjusted_weights[strategy] /= total_adjustment
                
                return adjusted_weights
                
        except Exception as e:
            self.logger.error(f"❌ 가중치 계산 실패: {e}")
            # 폴백: 동일 가중치
            num_strategies = len(signals)
            return {signal.strategy_name: 1.0/num_strategies for signal in signals}
    
    async def _calculate_consensus_signal(
        self, 
        signals: List[StrategySignal], 
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """가중평균 합의 신호 계산"""
        try:
            total_weighted_score = 0
            total_weighted_confidence = 0
            action_votes = {'BUY': 0, 'STRONG_BUY': 0, 'SELL': 0, 'STRONG_SELL': 0, 'HOLD': 0}
            all_reasons = []
            
            for signal in signals:
                weight = weights.get(signal.strategy_name, 0)
                
                # 점수와 신뢰도 가중평균
                total_weighted_score += signal.score * weight
                total_weighted_confidence += signal.confidence * weight
                
                # 액션 투표 (가중치 적용)
                action = signal.action
                if action in action_votes:
                    action_votes[action] += weight
                
                # 이유 수집 (상위 전략들만)
                if weight > 0.1:  # 가중치 10% 이상인 전략만
                    strategy_reasons = [f"[{signal.strategy_name}] {reason}" 
                                      for reason in signal.reasons[:2]]
                    all_reasons.extend(strategy_reasons)
            
            # 최종 액션 결정 (투표 결과)
            final_action = max(action_votes, key=action_votes.get)
            
            # 신호 강도에 따른 액션 조정
            if total_weighted_score >= 40:
                if final_action == 'BUY':
                    final_action = 'STRONG_BUY'
            elif total_weighted_score >= 20:
                if final_action not in ['BUY', 'STRONG_BUY']:
                    final_action = 'BUY'
            elif total_weighted_score <= -30:
                if final_action == 'SELL':
                    final_action = 'STRONG_SELL'
            elif total_weighted_score <= -15:
                if final_action not in ['SELL', 'STRONG_SELL']:
                    final_action = 'SELL'
            else:
                final_action = 'HOLD'
            
            return {
                'action': final_action,
                'score': total_weighted_score,
                'confidence': min(total_weighted_confidence, 95.0),
                'reasons': all_reasons[:5],  # 상위 5개 이유
                'vote_distribution': action_votes
            }
            
        except Exception as e:
            self.logger.error(f"❌ 합의 신호 계산 실패: {e}")
            return {
                'action': 'HOLD',
                'score': 0,
                'confidence': 50.0,
                'reasons': ['합의 신호 계산 오류'],
                'vote_distribution': {'HOLD': 1.0}
            }
    
    async def _assess_multi_strategy_risk(
        self, 
        signals: List[StrategySignal], 
        consensus_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """다중 전략 리스크 평가"""
        try:
            # 1. 신호 일치도 분석
            actions = [signal.action for signal in signals]
            action_consensus = len(set(actions)) / len(actions) if actions else 1.0
            
            # 2. 신뢰도 분산 분석
            confidences = [signal.confidence for signal in signals]
            confidence_std = self._calculate_std(confidences) if confidences else 0
            
            # 3. 전략 다양성 점수
            strategy_diversity = len(signals) / 7.0  # 최대 7개 전략
            
            # 4. 리스크 레벨 계산
            risk_factors = {
                'signal_disagreement': action_consensus,  # 낮을수록 위험
                'confidence_volatility': min(confidence_std / 20.0, 1.0),  # 높을수록 위험
                'strategy_coverage': strategy_diversity,  # 높을수록 안전
                'consensus_strength': min(abs(consensus_result['score']) / 50.0, 1.0)  # 높을수록 안전
            }
            
            # 종합 리스크 점수 (0-100, 낮을수록 위험)
            risk_score = (
                (1 - risk_factors['signal_disagreement']) * 25 +
                risk_factors['confidence_volatility'] * 25 +
                risk_factors['strategy_coverage'] * 25 +
                risk_factors['consensus_strength'] * 25
            )
            
            if risk_score >= 75:
                risk_level = "LOW"
            elif risk_score >= 50:
                risk_level = "MEDIUM"
            elif risk_score >= 25:
                risk_level = "HIGH"
            else:
                risk_level = "VERY_HIGH"
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'factors': risk_factors,
                'signal_consensus': len(set(actions)) <= 2,  # 2개 이하 액션 = 높은 합의
                'recommendation': self._get_risk_recommendation(risk_level, risk_score)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 평가 실패: {e}")
            return {
                'risk_level': 'HIGH',
                'risk_score': 25,
                'factors': {},
                'signal_consensus': False,
                'recommendation': '리스크 평가 오류로 신중한 접근 권장'
            }
    
    async def _generate_portfolio_recommendation(
        self, 
        symbol: str, 
        consensus_result: Dict[str, Any], 
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """포트폴리오 추천 생성"""
        try:
            action = consensus_result['action']
            confidence = consensus_result['confidence']
            risk_level = risk_assessment['risk_level']
            
            # 기본 포지션 크기 (리스크 기반)
            base_position_sizes = {
                'LOW': 0.15,      # 15%
                'MEDIUM': 0.10,   # 10%
                'HIGH': 0.05,     # 5%
                'VERY_HIGH': 0.02 # 2%
            }
            
            base_size = base_position_sizes.get(risk_level, 0.05)
            
            # 신뢰도 기반 조정
            confidence_multiplier = confidence / 100.0
            recommended_size = base_size * confidence_multiplier
            
            # 액션별 추천 사항
            if action in ['STRONG_BUY', 'BUY']:
                recommendation = {
                    'action': 'BUY',
                    'position_size_pct': min(recommended_size * 100, 20.0),  # 최대 20%
                    'entry_strategy': 'GRADUAL' if risk_level in ['HIGH', 'VERY_HIGH'] else 'IMMEDIATE',
                    'stop_loss_pct': 3.0 if risk_level == 'LOW' else 2.0,
                    'take_profit_pct': 8.0 if action == 'STRONG_BUY' else 5.0,
                    'holding_period': '단기' if 'scalping' in str(consensus_result) else '중기'
                }
            elif action in ['STRONG_SELL', 'SELL']:
                recommendation = {
                    'action': 'AVOID_OR_SELL',
                    'position_size_pct': 0,
                    'entry_strategy': 'NONE',
                    'stop_loss_pct': 0,
                    'take_profit_pct': 0,
                    'holding_period': 'N/A'
                }
            else:  # HOLD
                recommendation = {
                    'action': 'HOLD',
                    'position_size_pct': 0,
                    'entry_strategy': 'WAIT',
                    'stop_loss_pct': 0,
                    'take_profit_pct': 0,
                    'holding_period': '대기'
                }
            
            # 추가 권장 사항
            additional_notes = []
            if risk_level in ['HIGH', 'VERY_HIGH']:
                additional_notes.append("높은 리스크: 소액 투자 권장")
            if confidence < 70:
                additional_notes.append("낮은 신뢰도: 추가 검증 필요")
            if len(set([s.action for s in []])) > 3:  # 신호가 분산된 경우 (임시)
                additional_notes.append("신호 분산: 관망 권장")
            
            recommendation['additional_notes'] = additional_notes
            recommendation['risk_level'] = risk_level
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 추천 생성 실패: {e}")
            return {
                'action': 'HOLD',
                'position_size_pct': 0,
                'entry_strategy': 'WAIT',
                'risk_level': 'HIGH',
                'additional_notes': ['분석 오류로 대기 권장']
            }
    
    def _determine_execution_priority(
        self, 
        consensus_result: Dict[str, Any], 
        risk_assessment: Dict[str, Any]
    ) -> int:
        """실행 우선순위 결정 (1=최고, 5=최저)"""
        action = consensus_result['action']
        confidence = consensus_result['confidence']
        score = abs(consensus_result['score'])
        risk_level = risk_assessment['risk_level']
        
        # 기본 우선순위
        if action in ['STRONG_BUY', 'STRONG_SELL'] and confidence >= 85 and score >= 40:
            priority = 1  # 최고 우선순위
        elif action in ['BUY', 'SELL'] and confidence >= 75 and score >= 25:
            priority = 2  # 높은 우선순위
        elif action in ['BUY', 'SELL'] and confidence >= 65:
            priority = 3  # 중간 우선순위
        elif action == 'HOLD' or confidence < 65:
            priority = 4  # 낮은 우선순위
        else:
            priority = 5  # 최저 우선순위
        
        # 리스크에 따른 조정
        if risk_level == 'VERY_HIGH':
            priority = min(priority + 2, 5)
        elif risk_level == 'HIGH':
            priority = min(priority + 1, 5)
        elif risk_level == 'LOW':
            priority = max(priority - 1, 1)
        
        return priority
    
    def _calculate_std(self, values: List[float]) -> float:
        """표준편차 계산"""
        if len(values) <= 1:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _get_risk_recommendation(self, risk_level: str, risk_score: float) -> str:
        """리스크 레벨별 추천 사항"""
        recommendations = {
            'LOW': '안전한 투자 환경, 적극적 투자 고려',
            'MEDIUM': '적정 리스크, 분할 매수 권장',
            'HIGH': '높은 리스크, 소액 테스트 투자만',
            'VERY_HIGH': '매우 높은 리스크, 투자 보류 권장'
        }
        return recommendations.get(risk_level, '신중한 접근 권장')
    
    def _create_neutral_result(self, symbol: str, reason: str) -> MultiStrategyResult:
        """중립 결과 생성"""
        return MultiStrategyResult(
            symbol=symbol,
            final_action='HOLD',
            final_confidence=50.0,
            consensus_score=0,
            individual_signals=[],
            weight_distribution={},
            risk_assessment={'risk_level': 'HIGH', 'risk_score': 25},
            portfolio_recommendation={'action': 'HOLD', 'position_size_pct': 0},
            execution_priority=5
        )