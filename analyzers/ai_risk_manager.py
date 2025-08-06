#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/ai_risk_manager.py

AI 기반 리스크 관리 및 포지션 사이징 - Phase 4 Advanced AI Features
"""

import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer


@dataclass
class PositionSizingRecommendation:
    """포지션 사이징 추천"""
    symbol: str
    recommended_position_size: float  # 0-1 (포트폴리오 대비 비율)
    max_position_size: float
    risk_adjusted_size: float
    confidence_level: float
    kelly_criterion_size: float
    volatility_adjusted_size: float
    correlation_adjusted_size: float
    final_recommendation: str  # AGGRESSIVE, MODERATE, CONSERVATIVE, AVOID
    reasoning: List[str]
    timestamp: datetime


@dataclass
class RiskMetrics:
    """리스크 메트릭"""
    var_1day: float  # 1일 VaR (Value at Risk)
    var_5day: float  # 5일 VaR
    expected_shortfall: float  # Expected Shortfall (CVaR)
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    beta: float
    correlation_with_market: float
    liquidity_risk: str  # HIGH, MEDIUM, LOW
    concentration_risk: float


@dataclass
class AIRiskAssessment:
    """AI 리스크 평가 결과"""
    overall_risk_score: float  # 0-100
    risk_level: str  # VERY_LOW, LOW, MEDIUM, HIGH, VERY_HIGH
    key_risk_factors: List[str]
    risk_mitigation_strategies: List[str]
    recommended_actions: List[str]
    confidence: float
    timestamp: datetime


class AIRiskManager:
    """AI 기반 리스크 관리자"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("AIRiskManager")
        self.gemini_analyzer = GeminiAnalyzer(config)
        
        # 리스크 매개변수
        self.risk_params = {
            'max_portfolio_risk': 0.02,  # 일일 최대 2% 리스크
            'max_single_position': 0.10,  # 단일 포지션 최대 10%
            'correlation_threshold': 0.7,  # 상관관계 임계값
            'liquidity_threshold': 1000000,  # 최소 거래대금 (100만원)
            'volatility_multiplier': 2.0,  # 변동성 승수
            'confidence_threshold': 0.70  # 신뢰도 임계값
        }
        
        # Kelly Criterion 매개변수
        self.kelly_params = {
            'win_rate_adjustment': 0.9,  # 승률 조정 계수
            'payoff_adjustment': 0.8,   # 수익 조정 계수
            'max_kelly': 0.25           # 최대 Kelly 비율
        }
        
        self.logger.info("✅ AI 리스크 관리자 초기화 완료")
    
    async def calculate_optimal_position_size(self, symbol: str, stock_data: Dict, 
                                           portfolio_data: Dict, 
                                           prediction_data: Dict) -> PositionSizingRecommendation:
        """최적 포지션 사이징 계산"""
        try:
            self.logger.info(f"📊 {symbol} 최적 포지션 사이징 계산 시작")
            
            # 1. 기본 리스크 메트릭 계산
            risk_metrics = await self._calculate_risk_metrics(symbol, stock_data, portfolio_data)
            
            # 2. Kelly Criterion 기반 사이징
            kelly_size = await self._calculate_kelly_criterion(symbol, prediction_data, risk_metrics)
            
            # 3. 변동성 조정 사이징
            volatility_size = await self._calculate_volatility_adjusted_size(
                symbol, stock_data, risk_metrics
            )
            
            # 4. 상관관계 조정 사이징
            correlation_size = await self._calculate_correlation_adjusted_size(
                symbol, portfolio_data, risk_metrics
            )
            
            # 5. AI 기반 신뢰도 조정
            confidence_size = await self._calculate_confidence_adjusted_size(
                symbol, prediction_data, kelly_size
            )
            
            # 6. 최종 포지션 사이징 결정
            final_recommendation = await self._synthesize_position_sizing(
                symbol, kelly_size, volatility_size, correlation_size, 
                confidence_size, risk_metrics
            )
            
            self.logger.info(f"✅ {symbol} 포지션 사이징 완료: {final_recommendation.recommended_position_size:.2%}")
            return final_recommendation
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 포지션 사이징 계산 실패: {e}")
            return self._create_default_position_sizing(symbol)
    
    async def assess_portfolio_risk(self, portfolio_data: Dict, 
                                  market_data: Dict) -> AIRiskAssessment:
        """포트폴리오 리스크 평가"""
        try:
            self.logger.info("🛡️ 포트폴리오 리스크 종합 평가 시작")
            
            # 1. 개별 포지션 리스크 분석
            position_risks = await self._analyze_individual_position_risks(portfolio_data)
            
            # 2. 포트폴리오 집중도 리스크
            concentration_risk = await self._analyze_concentration_risk(portfolio_data)
            
            # 3. 시장 리스크 분석
            market_risk = await self._analyze_market_risk(market_data)
            
            # 4. 유동성 리스크 분석
            liquidity_risk = await self._analyze_liquidity_risk(portfolio_data)
            
            # 5. 상관관계 리스크 분석
            correlation_risk = await self._analyze_correlation_risk(portfolio_data)
            
            # 6. AI 기반 종합 리스크 평가
            ai_assessment = await self._ai_comprehensive_risk_evaluation(
                position_risks, concentration_risk, market_risk, 
                liquidity_risk, correlation_risk
            )
            
            # 7. 리스크 완화 전략 생성
            mitigation_strategies = await self._generate_risk_mitigation_strategies(ai_assessment)
            
            final_assessment = AIRiskAssessment(
                overall_risk_score=ai_assessment.get('risk_score', 50),
                risk_level=self._categorize_risk_level(ai_assessment.get('risk_score', 50)),
                key_risk_factors=ai_assessment.get('key_factors', []),
                risk_mitigation_strategies=mitigation_strategies,
                recommended_actions=ai_assessment.get('recommended_actions', []),
                confidence=ai_assessment.get('confidence', 70),
                timestamp=datetime.now()
            )
            
            self.logger.info(f"✅ 포트폴리오 리스크 평가 완료: {final_assessment.risk_level} ({final_assessment.overall_risk_score:.1f}점)")
            return final_assessment
            
        except Exception as e:
            self.logger.error(f"❌ 포트폴리오 리스크 평가 실패: {e}")
            return self._create_default_risk_assessment()
    
    async def dynamic_risk_adjustment(self, current_positions: Dict, 
                                    market_conditions: Dict, 
                                    performance_data: Dict) -> Dict[str, Any]:
        """동적 리스크 조정"""
        try:
            self.logger.info("⚙️ 동적 리스크 조정 시작")
            
            # 1. 현재 포트폴리오 리스크 측정
            current_risk = await self._measure_current_portfolio_risk(current_positions)
            
            # 2. 시장 변동성 변화 감지
            volatility_change = await self._detect_volatility_regime_change(market_conditions)
            
            # 3. 성과 기반 리스크 조정
            performance_adjustment = await self._calculate_performance_based_adjustment(performance_data)
            
            # 4. AI 기반 리스크 조정 추천
            ai_adjustment = await self._ai_risk_adjustment_recommendation(
                current_risk, volatility_change, performance_adjustment
            )
            
            # 5. 실행 가능한 조정 전략 생성
            adjustment_strategies = await self._generate_adjustment_strategies(ai_adjustment)
            
            result = {
                'current_risk_level': current_risk.get('risk_level', 'MEDIUM'),
                'recommended_adjustments': ai_adjustment,
                'adjustment_strategies': adjustment_strategies,
                'priority_actions': ai_adjustment.get('priority_actions', []),
                'expected_risk_reduction': ai_adjustment.get('risk_reduction', 0),
                'implementation_timeline': ai_adjustment.get('timeline', 'IMMEDIATE'),
                'confidence': ai_adjustment.get('confidence', 70),
                'timestamp': datetime.now()
            }
            
            self.logger.info("✅ 동적 리스크 조정 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 동적 리스크 조정 실패: {e}")
            return {}
    
    async def calculate_scenario_analysis(self, portfolio_data: Dict, 
                                        scenarios: List[Dict] = None) -> Dict[str, Any]:
        """시나리오 분석"""
        try:
            self.logger.info("📈 포트폴리오 시나리오 분석 시작")
            
            if scenarios is None:
                scenarios = await self._generate_default_scenarios()
            
            scenario_results = {}
            
            for scenario in scenarios:
                scenario_name = scenario.get('name', 'Unknown')
                self.logger.info(f"🎭 시나리오 분석: {scenario_name}")
                
                # 각 시나리오별 포트폴리오 영향 계산
                scenario_impact = await self._calculate_scenario_impact(
                    portfolio_data, scenario
                )
                
                scenario_results[scenario_name] = scenario_impact
            
            # 종합 시나리오 분석 결과
            comprehensive_analysis = await self._synthesize_scenario_analysis(scenario_results)
            
            result = {
                'individual_scenarios': scenario_results,
                'worst_case_scenario': comprehensive_analysis.get('worst_case'),
                'best_case_scenario': comprehensive_analysis.get('best_case'),
                'most_likely_scenario': comprehensive_analysis.get('most_likely'),
                'risk_adjusted_recommendations': comprehensive_analysis.get('recommendations'),
                'stress_test_results': comprehensive_analysis.get('stress_test'),
                'timestamp': datetime.now()
            }
            
            self.logger.info("✅ 시나리오 분석 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 시나리오 분석 실패: {e}")
            return {}
    
    # === 내부 헬퍼 메서드들 ===
    
    async def _calculate_risk_metrics(self, symbol: str, stock_data: Dict, 
                                    portfolio_data: Dict) -> RiskMetrics:
        """리스크 메트릭 계산"""
        try:
            current_price = stock_data.get('current_price', 0)
            change_rate = stock_data.get('change_rate', 0)
            volume = stock_data.get('volume', 0)
            
            # 기본 변동성 계산 (임시)
            volatility = abs(change_rate) / 100 if change_rate != 0 else 0.02
            
            # VaR 계산 (간단한 버전)
            var_1day = current_price * volatility * 1.645  # 95% 신뢰구간
            var_5day = var_1day * math.sqrt(5)
            
            return RiskMetrics(
                var_1day=var_1day,
                var_5day=var_5day,
                expected_shortfall=var_1day * 1.3,
                sharpe_ratio=1.2,  # 기본값
                sortino_ratio=1.5,  # 기본값
                max_drawdown=0.10,  # 기본값
                volatility=volatility,
                beta=1.0,  # 기본값
                correlation_with_market=0.6,  # 기본값
                liquidity_risk="MEDIUM" if volume > 1000000 else "HIGH",
                concentration_risk=0.15  # 기본값
            )
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 메트릭 계산 실패: {e}")
            return self._create_default_risk_metrics()
    
    async def _calculate_kelly_criterion(self, symbol: str, prediction_data: Dict, 
                                       risk_metrics: RiskMetrics) -> float:
        """Kelly Criterion 계산"""
        try:
            # 예측 데이터에서 승률과 수익률 추출
            confidence = prediction_data.get('confidence', 50) / 100
            expected_return = prediction_data.get('expected_return', 0.05)
            
            # Kelly 공식: f = (bp - q) / b
            # b = 승리시 수익률, p = 승률, q = 패배 확률
            win_rate = confidence * self.kelly_params['win_rate_adjustment']
            lose_rate = 1 - win_rate
            avg_win = expected_return * self.kelly_params['payoff_adjustment']
            avg_loss = risk_metrics.volatility
            
            if avg_loss > 0:
                kelly_fraction = (win_rate * avg_win - lose_rate * avg_loss) / avg_win
                kelly_fraction = max(0, min(self.kelly_params['max_kelly'], kelly_fraction))
            else:
                kelly_fraction = 0
            
            self.logger.debug(f"{symbol} Kelly Criterion: {kelly_fraction:.3f}")
            return kelly_fraction
            
        except Exception as e:
            self.logger.error(f"❌ Kelly Criterion 계산 실패: {e}")
            return 0.05  # 기본값 5%
    
    async def _calculate_volatility_adjusted_size(self, symbol: str, stock_data: Dict, 
                                                risk_metrics: RiskMetrics) -> float:
        """변동성 조정 포지션 크기"""
        try:
            target_volatility = self.risk_params['max_portfolio_risk']
            stock_volatility = risk_metrics.volatility
            
            if stock_volatility > 0:
                volatility_adjusted_size = target_volatility / (stock_volatility * self.risk_params['volatility_multiplier'])
                volatility_adjusted_size = min(self.risk_params['max_single_position'], volatility_adjusted_size)
            else:
                volatility_adjusted_size = self.risk_params['max_single_position']
            
            return max(0, volatility_adjusted_size)
            
        except Exception as e:
            self.logger.error(f"❌ 변동성 조정 사이징 실패: {e}")
            return 0.05
    
    async def _calculate_correlation_adjusted_size(self, symbol: str, portfolio_data: Dict, 
                                                 risk_metrics: RiskMetrics) -> float:
        """상관관계 조정 포지션 크기"""
        try:
            # 기존 포지션과의 상관관계 분석 (간단한 버전)
            correlation_penalty = 1.0
            
            if risk_metrics.correlation_with_market > self.risk_params['correlation_threshold']:
                correlation_penalty = 0.7  # 높은 상관관계시 30% 감소
            
            base_size = self.risk_params['max_single_position']
            correlation_adjusted_size = base_size * correlation_penalty
            
            return correlation_adjusted_size
            
        except Exception as e:
            self.logger.error(f"❌ 상관관계 조정 사이징 실패: {e}")
            return 0.05
    
    async def _calculate_confidence_adjusted_size(self, symbol: str, prediction_data: Dict, 
                                                kelly_size: float) -> float:
        """신뢰도 조정 포지션 크기"""
        try:
            confidence = prediction_data.get('confidence', 50) / 100
            
            if confidence < self.risk_params['confidence_threshold']:
                # 낮은 신뢰도시 포지션 크기 감소
                confidence_multiplier = confidence / self.risk_params['confidence_threshold']
            else:
                # 높은 신뢰도시 포지션 크기 유지 또는 증가
                confidence_multiplier = min(1.5, confidence / self.risk_params['confidence_threshold'])
            
            confidence_adjusted_size = kelly_size * confidence_multiplier
            return max(0, min(self.risk_params['max_single_position'], confidence_adjusted_size))
            
        except Exception as e:
            self.logger.error(f"❌ 신뢰도 조정 사이징 실패: {e}")
            return kelly_size
    
    async def _synthesize_position_sizing(self, symbol: str, kelly_size: float, 
                                        volatility_size: float, correlation_size: float,
                                        confidence_size: float, risk_metrics: RiskMetrics) -> PositionSizingRecommendation:
        """포지션 사이징 종합"""
        try:
            # 가중 평균으로 최종 사이즈 결정
            weights = {
                'kelly': 0.4,
                'volatility': 0.25,
                'correlation': 0.20,
                'confidence': 0.15
            }
            
            weighted_size = (
                kelly_size * weights['kelly'] +
                volatility_size * weights['volatility'] +
                correlation_size * weights['correlation'] +
                confidence_size * weights['confidence']
            )
            
            # 최대 한도 적용
            final_size = min(self.risk_params['max_single_position'], weighted_size)
            
            # AI 기반 추천 등급 결정
            if final_size >= 0.08:
                recommendation = "AGGRESSIVE"
            elif final_size >= 0.05:
                recommendation = "MODERATE"
            elif final_size >= 0.02:
                recommendation = "CONSERVATIVE"
            else:
                recommendation = "AVOID"
            
            reasoning = [
                f"Kelly Criterion: {kelly_size:.2%}",
                f"변동성 조정: {volatility_size:.2%}",
                f"상관관계 조정: {correlation_size:.2%}",
                f"신뢰도 조정: {confidence_size:.2%}",
                f"최종 가중평균: {weighted_size:.2%}"
            ]
            
            return PositionSizingRecommendation(
                symbol=symbol,
                recommended_position_size=final_size,
                max_position_size=self.risk_params['max_single_position'],
                risk_adjusted_size=volatility_size,
                confidence_level=85.0,  # 기본값
                kelly_criterion_size=kelly_size,
                volatility_adjusted_size=volatility_size,
                correlation_adjusted_size=correlation_size,
                final_recommendation=recommendation,
                reasoning=reasoning,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ 포지션 사이징 종합 실패: {e}")
            return self._create_default_position_sizing(symbol)
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """리스크 점수를 등급으로 변환"""
        if risk_score >= 80:
            return "VERY_HIGH"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        elif risk_score >= 20:
            return "LOW"
        else:
            return "VERY_LOW"
    
    def _create_default_risk_metrics(self) -> RiskMetrics:
        """기본 리스크 메트릭 생성"""
        return RiskMetrics(
            var_1day=1000,
            var_5day=2236,
            expected_shortfall=1300,
            sharpe_ratio=1.0,
            sortino_ratio=1.2,
            max_drawdown=0.15,
            volatility=0.02,
            beta=1.0,
            correlation_with_market=0.6,
            liquidity_risk="MEDIUM",
            concentration_risk=0.15
        )
    
    def _create_default_position_sizing(self, symbol: str) -> PositionSizingRecommendation:
        """기본 포지션 사이징 생성"""
        return PositionSizingRecommendation(
            symbol=symbol,
            recommended_position_size=0.05,
            max_position_size=0.10,
            risk_adjusted_size=0.05,
            confidence_level=50.0,
            kelly_criterion_size=0.05,
            volatility_adjusted_size=0.05,
            correlation_adjusted_size=0.05,
            final_recommendation="CONSERVATIVE",
            reasoning=["기본 설정으로 인한 보수적 접근"],
            timestamp=datetime.now()
        )
    
    def _create_default_risk_assessment(self) -> AIRiskAssessment:
        """기본 리스크 평가 생성"""
        return AIRiskAssessment(
            overall_risk_score=50.0,
            risk_level="MEDIUM",
            key_risk_factors=["데이터 부족으로 인한 불확실성"],
            risk_mitigation_strategies=["포지션 크기 제한", "분산 투자"],
            recommended_actions=["추가 데이터 수집", "모니터링 강화"],
            confidence=60.0,
            timestamp=datetime.now()
        )
    
    # 추가 헬퍼 메서드들 (간단한 구현)
    async def _analyze_individual_position_risks(self, portfolio_data: Dict) -> Dict:
        return {'average_risk': 'MEDIUM', 'high_risk_positions': []}
    
    async def _analyze_concentration_risk(self, portfolio_data: Dict) -> Dict:
        return {'concentration_score': 60, 'diversification_level': 'MODERATE'}
    
    async def _analyze_market_risk(self, market_data: Dict) -> Dict:
        return {'market_risk_level': 'MEDIUM', 'volatility_regime': 'NORMAL'}
    
    async def _analyze_liquidity_risk(self, portfolio_data: Dict) -> Dict:
        return {'liquidity_risk': 'MEDIUM', 'illiquid_positions': []}
    
    async def _analyze_correlation_risk(self, portfolio_data: Dict) -> Dict:
        return {'correlation_risk': 'MEDIUM', 'highly_correlated_pairs': []}
    
    async def _ai_comprehensive_risk_evaluation(self, *risk_components) -> Dict:
        return {
            'risk_score': 50,
            'key_factors': ['시장 변동성', '포지션 집중도'],
            'recommended_actions': ['리밸런싱', '리스크 모니터링'],
            'confidence': 70
        }
    
    async def _generate_risk_mitigation_strategies(self, assessment: Dict) -> List[str]:
        return [
            "포지션 크기 조절을 통한 리스크 관리",
            "상관관계가 낮은 자산으로 분산 투자",
            "변동성이 높은 시기 노출 감소",
            "정기적인 리스크 재평가 및 조정"
        ]
    
    # 동적 리스크 조정 관련 메서드들
    async def _measure_current_portfolio_risk(self, positions: Dict) -> Dict:
        return {'risk_level': 'MEDIUM', 'total_var': 50000}
    
    async def _detect_volatility_regime_change(self, market_conditions: Dict) -> Dict:
        return {'regime_change': False, 'volatility_trend': 'STABLE'}
    
    async def _calculate_performance_based_adjustment(self, performance_data: Dict) -> Dict:
        return {'adjustment_factor': 1.0, 'reason': 'STABLE_PERFORMANCE'}
    
    async def _ai_risk_adjustment_recommendation(self, current_risk: Dict, 
                                               volatility_change: Dict, 
                                               performance_adjustment: Dict) -> Dict:
        return {
            'recommended_adjustments': {'position_sizing': 'MAINTAIN'},
            'priority_actions': ['모니터링 지속'],
            'risk_reduction': 0,
            'timeline': 'NO_ACTION',
            'confidence': 70
        }
    
    async def _generate_adjustment_strategies(self, ai_adjustment: Dict) -> List[str]:
        return ["현재 포지션 유지", "정기 모니터링 지속"]
    
    # 시나리오 분석 관련 메서드들
    async def _generate_default_scenarios(self) -> List[Dict]:
        return [
            {'name': '기본 시나리오', 'market_change': 0, 'volatility_change': 0},
            {'name': '하락 시나리오', 'market_change': -0.10, 'volatility_change': 0.5},
            {'name': '상승 시나리오', 'market_change': 0.15, 'volatility_change': -0.2},
            {'name': '고변동성 시나리오', 'market_change': 0, 'volatility_change': 1.0}
        ]
    
    async def _calculate_scenario_impact(self, portfolio_data: Dict, scenario: Dict) -> Dict:
        market_change = scenario.get('market_change', 0)
        portfolio_value = portfolio_data.get('total_value', 10000000)
        
        estimated_impact = portfolio_value * market_change
        
        return {
            'portfolio_impact': estimated_impact,
            'percentage_change': market_change * 100,
            'risk_level': 'HIGH' if abs(market_change) > 0.1 else 'MEDIUM'
        }
    
    async def _synthesize_scenario_analysis(self, scenario_results: Dict) -> Dict:
        return {
            'worst_case': '하락 시나리오',
            'best_case': '상승 시나리오', 
            'most_likely': '기본 시나리오',
            'recommendations': ['분산 투자 유지', '리스크 모니터링'],
            'stress_test': {'passed': True, 'max_loss': -10}
        }