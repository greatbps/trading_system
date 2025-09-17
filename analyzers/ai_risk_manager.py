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
        
        # Phase 4.2: 동적 리스크 매개변수 (실시간 조정 가능)
        self.risk_params = {
            'max_portfolio_risk': 0.02,      # 일일 최대 2% 리스크
            'max_single_position': 0.10,     # 단일 포지션 최대 10%
            'correlation_threshold': 0.7,    # 상관관계 임계값
            'liquidity_threshold': 1000000,  # 최소 거래대금 (100만원)
            'volatility_multiplier': 2.0,    # 변동성 승수
            'confidence_threshold': 0.70,    # 신뢰도 임계값
            'risk_parity_weight': 0.3,       # 리스크 패리티 가중치
            'momentum_risk_factor': 0.2,     # 모멘텀 리스크 요소
            'market_regime_adjustment': 0.15  # 시장 체제 조정 요소
        }
        
        # Phase 4.2: 실시간 리스크 모니터링
        self.real_time_risk = {
            'current_portfolio_risk': 0.0,
            'risk_budget_used': 0.0,
            'stress_test_results': {},
            'correlation_matrix': {},
            'volatility_forecast': {},
            'last_risk_update': None
        }
        
        # Phase 4.2: 위기 상황 자동 대응 설정
        self.crisis_thresholds = {
            'market_crash': {'vix_threshold': 30, 'portfolio_loss': 0.15},
            'liquidity_crisis': {'volume_drop': 0.5, 'spread_increase': 2.0},
            'correlation_breakdown': {'correlation_spike': 0.9},
            'volatility_spike': {'vol_increase': 3.0}
        }
        
        # Phase 4.2: 동적 손절매/익절매 설정
        self.dynamic_stops = {
            'adaptive_stop_loss': True,
            'volatility_based_stops': True,
            'time_based_stops': True,
            'correlation_based_stops': True
        }
        
        # Kelly Criterion 매개변수
        self.kelly_params = {
            'win_rate_adjustment': 0.9,  # 승률 조정 계수
            'payoff_adjustment': 0.8,   # 수익 조정 계수
            'max_kelly': 0.25           # 최대 Kelly 비율
        }
        
        self.logger.info("✅ AI 리스크 관리자 초기화 완료")
    
    # === Phase 4.2: 실시간 리스크 스코어링 시스템 ===
    
    async def real_time_risk_scoring(self, portfolio_data: Dict, market_conditions: Dict) -> Dict[str, Any]:
        """Phase 4.2: 실시간 리스크 스코어링"""
        try:
            self.logger.info("🔍 실시간 리스크 스코어링 시작")
            
            # 1. 포트폴리오 전체 리스크 계산
            portfolio_risk = await self._calculate_portfolio_risk_real_time(portfolio_data, market_conditions)
            
            # 2. 개별 종목 리스크 분석
            individual_risks = await self._analyze_individual_stock_risks(portfolio_data, market_conditions)
            
            # 3. 시장 리스크 요소 분석
            market_risk_factors = await self._analyze_market_risk_factors(market_conditions)
            
            # 4. 상관관계 리스크 분석
            correlation_analysis = await self._analyze_correlation_risks(portfolio_data, market_conditions)
            
            # 5. 유동성 리스크 평가
            liquidity_risk = await self._assess_liquidity_risk(portfolio_data, market_conditions)
            
            # 6. 종합 리스크 스코어 계산
            overall_risk_score = await self._calculate_comprehensive_risk_score(
                portfolio_risk, individual_risks, market_risk_factors, 
                correlation_analysis, liquidity_risk
            )
            
            # 7. 리스크 등급 및 권장사항
            risk_level, recommendations = self._determine_risk_level_and_actions(overall_risk_score)
            
            # 8. 실시간 모니터링 상태 업데이트
            self.real_time_risk.update({
                'current_portfolio_risk': overall_risk_score,
                'risk_budget_used': portfolio_risk.get('risk_budget_utilization', 0),
                'last_risk_update': datetime.now()
            })
            
            result = {
                'overall_risk_score': overall_risk_score,
                'risk_level': risk_level,
                'portfolio_risk': portfolio_risk,
                'individual_risks': individual_risks,
                'market_factors': market_risk_factors,
                'correlation_analysis': correlation_analysis,
                'liquidity_risk': liquidity_risk,
                'recommendations': recommendations,
                'real_time_alerts': self._generate_real_time_alerts(overall_risk_score),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 실시간 리스크 스코어링 완료: {risk_level} ({overall_risk_score:.1f}점)")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 실시간 리스크 스코어링 실패: {e}")
            return self._create_default_risk_scoring()
    
    async def dynamic_position_adjustment(self, current_positions: Dict, risk_analysis: Dict) -> Dict[str, Any]:
        """Phase 4.2: 동적 포지션 조정"""
        try:
            self.logger.info("⚖️ 동적 포지션 조정 시작")
            
            adjustments = {}
            total_adjustment_value = 0
            
            for symbol, position_data in current_positions.items():
                # 1. 종목별 리스크 평가
                symbol_risk = risk_analysis.get('individual_risks', {}).get(symbol, {})
                
                # 2. 현재 포지션 크기 vs 리스크 분석
                current_size = position_data.get('position_size', 0)
                current_value = position_data.get('current_value', 0)
                
                # 3. 리스크 기반 권장 포지션 크기 계산
                recommended_size = await self._calculate_risk_adjusted_position(
                    symbol, symbol_risk, current_size, risk_analysis
                )
                
                # 4. 조정이 필요한지 판단
                size_difference = recommended_size - current_size
                adjustment_threshold = 0.02  # 2% 이상 차이 시 조정
                
                if abs(size_difference) > adjustment_threshold:
                    adjustment_type = "INCREASE" if size_difference > 0 else "DECREASE"
                    adjustment_reason = self._determine_adjustment_reason(symbol_risk, size_difference)
                    
                    adjustments[symbol] = {
                        'current_size': current_size,
                        'recommended_size': recommended_size,
                        'adjustment_type': adjustment_type,
                        'adjustment_amount': abs(size_difference),
                        'adjustment_value': abs(size_difference) * position_data.get('current_price', 0),
                        'priority': self._calculate_adjustment_priority(symbol_risk, size_difference),
                        'reason': adjustment_reason,
                        'execution_timeline': self._determine_execution_timeline(symbol_risk),
                        'risk_impact': self._assess_adjustment_risk_impact(symbol_risk, size_difference)
                    }
                    
                    total_adjustment_value += adjustments[symbol]['adjustment_value']
            
            # 5. 조정 실행 계획 수립
            execution_plan = self._create_adjustment_execution_plan(adjustments, risk_analysis)
            
            result = {
                'total_adjustments_needed': len(adjustments),
                'total_adjustment_value': total_adjustment_value,
                'position_adjustments': adjustments,
                'execution_plan': execution_plan,
                'expected_risk_improvement': self._calculate_expected_risk_improvement(adjustments),
                'monitoring_requirements': self._generate_monitoring_requirements(adjustments),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 동적 포지션 조정 완료: {len(adjustments)}개 종목, "
                           f"총 조정금액 {total_adjustment_value:,.0f}원")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 동적 포지션 조정 실패: {e}")
            return {'total_adjustments_needed': 0, 'position_adjustments': {}, 'execution_plan': {}}
    
    async def crisis_response_system(self, market_conditions: Dict, portfolio_data: Dict) -> Dict[str, Any]:
        """Phase 4.2: 위기 상황 자동 대응 시스템"""
        try:
            self.logger.info("🚨 위기 대응 시스템 활성화")
            
            # 1. 위기 상황 감지
            crisis_detected = await self._detect_crisis_conditions(market_conditions, portfolio_data)
            
            if not crisis_detected['is_crisis']:
                return {'crisis_detected': False, 'status': 'NORMAL', 'actions': []}
            
            crisis_type = crisis_detected['crisis_type']
            crisis_severity = crisis_detected['severity']
            
            self.logger.warning(f"🚨 위기 감지: {crisis_type} (심각도: {crisis_severity})")
            
            # 2. 위기 유형별 대응 전략
            response_actions = []
            
            if crisis_type == 'MARKET_CRASH':
                response_actions = await self._handle_market_crash(portfolio_data, crisis_detected)
            elif crisis_type == 'LIQUIDITY_CRISIS':
                response_actions = await self._handle_liquidity_crisis(portfolio_data, crisis_detected)
            elif crisis_type == 'VOLATILITY_SPIKE':
                response_actions = await self._handle_volatility_spike(portfolio_data, crisis_detected)
            elif crisis_type == 'CORRELATION_BREAKDOWN':
                response_actions = await self._handle_correlation_breakdown(portfolio_data, crisis_detected)
            
            # 3. 포지션 보호 조치
            protection_measures = await self._implement_position_protection(portfolio_data, crisis_type)
            
            # 4. 동적 손절매 조정
            dynamic_stops = await self._adjust_dynamic_stops(portfolio_data, crisis_type, crisis_severity)
            
            result = {
                'crisis_detected': True,
                'crisis_type': crisis_type,
                'severity': crisis_severity,
                'response_actions': response_actions,
                'protection_measures': protection_measures,
                'dynamic_stops': dynamic_stops,
                'execution_priority': 'IMMEDIATE' if crisis_severity == 'CRITICAL' else 'HIGH',
                'monitoring_frequency': 'REAL_TIME',
                'recovery_indicators': self._define_recovery_indicators(crisis_type),
                'timestamp': datetime.now()
            }
            
            self.logger.warning(f"🚨 위기 대응 계획 수립 완료: {len(response_actions)}개 액션")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 위기 대응 시스템 실패: {e}")
            return {'crisis_detected': False, 'error': str(e)}
    
    async def dynamic_stop_management(self, symbol: str, position_data: Dict, 
                                    market_conditions: Dict, prediction_data: Dict) -> Dict[str, Any]:
        """Phase 4.2: 동적 손절매/익절매 관리"""
        try:
            self.logger.info(f"⚡ {symbol} 동적 손절매 관리 시작")
            
            current_price = position_data.get('current_price', 0)
            entry_price = position_data.get('entry_price', current_price)
            position_size = position_data.get('quantity', 0)
            
            if current_price == 0 or position_size == 0:
                return {'status': 'NO_DATA'}
            
            # 1. 현재 변동성 계산
            volatility = self._calculate_current_volatility(market_conditions, symbol)
            
            # 2. 동적 손절매 레벨 계산
            dynamic_stop_loss = self._calculate_dynamic_stop_loss(
                entry_price, current_price, volatility, prediction_data
            )
            
            # 3. 동적 익절매 레벨 계산  
            dynamic_take_profit = self._calculate_dynamic_take_profit(
                entry_price, current_price, volatility, prediction_data
            )
            
            # 4. 트레일링 스톱 계산
            trailing_stop = self._calculate_trailing_stop(
                entry_price, current_price, volatility
            )
            
            # 5. 최적 손절 레벨 선택
            optimal_stop_loss = self._select_optimal_stop_level(
                dynamic_stop_loss, trailing_stop, position_data
            )
            
            # 6. 실행 권고 생성
            execution_recommendation = self._generate_stop_execution_recommendation(
                symbol, current_price, optimal_stop_loss, dynamic_take_profit, position_data
            )
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'entry_price': entry_price,
                'volatility': volatility,
                'dynamic_stop_loss': dynamic_stop_loss,
                'dynamic_take_profit': dynamic_take_profit,
                'trailing_stop': trailing_stop,
                'optimal_stop_loss': optimal_stop_loss,
                'execution_recommendation': execution_recommendation,
                'risk_reward_ratio': self._calculate_risk_reward_ratio(
                    current_price, optimal_stop_loss, dynamic_take_profit
                ),
                'confidence': prediction_data.get('confidence', 0.5),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ {symbol} 동적 손절매 관리 완료 - 최적 손절: {optimal_stop_loss:.0f}원")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 동적 손절매 관리 실패: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    # === Phase 4.2 헬퍼 메서드들 ===
    
    def _calculate_portfolio_risk_real_time(self, positions: Dict, market_data: Dict) -> Dict:
        """실시간 포트폴리오 리스크 계산"""
        try:
            total_value = sum(pos.get('market_value', 0) for pos in positions.values())
            if total_value == 0:
                return {'risk_score': 0, 'risk_level': 'LOW'}
            
            # 1. 집중도 리스크
            concentration_risk = self._calculate_concentration_risk(positions, total_value)
            
            # 2. 변동성 리스크
            volatility_risk = self._calculate_volatility_risk(positions, market_data)
            
            # 3. 상관관계 리스크
            correlation_risk = self._calculate_correlation_risk(positions)
            
            # 4. 유동성 리스크
            liquidity_risk = self._calculate_liquidity_risk(positions, market_data)
            
            # 종합 리스크 점수
            overall_risk = (
                concentration_risk * 0.3 +
                volatility_risk * 0.25 + 
                correlation_risk * 0.25 +
                liquidity_risk * 0.2
            )
            
            risk_level = self._determine_risk_level(overall_risk)
            
            return {
                'risk_score': overall_risk,
                'risk_level': risk_level,
                'concentration_risk': concentration_risk,
                'volatility_risk': volatility_risk,
                'correlation_risk': correlation_risk,
                'liquidity_risk': liquidity_risk,
                'risk_budget_usage': min(overall_risk / 80 * 100, 100)  # 80점 기준
            }
            
        except Exception as e:
            self.logger.error(f"포트폴리오 리스크 계산 실패: {e}")
            return {'risk_score': 50, 'risk_level': 'MEDIUM'}
    
    def _calculate_position_risk_score(self, symbol: str, position_data: Dict, market_data: Dict) -> Dict:
        """개별 포지션 리스크 점수 계산"""
        try:
            # 1. 가격 변동성 리스크
            volatility = market_data.get(symbol, {}).get('volatility', 0.02)
            volatility_score = min(volatility * 100, 100)
            
            # 2. 포지션 크기 리스크
            position_value = position_data.get('market_value', 0)
            total_portfolio = position_data.get('total_portfolio_value', 1000000)
            size_ratio = position_value / total_portfolio
            size_score = min(size_ratio * 200, 100)  # 50% 이상이면 최고 위험
            
            # 3. 손실 리스크
            current_pnl_pct = position_data.get('unrealized_pnl_pct', 0)
            loss_score = max(-current_pnl_pct * 2, 0) if current_pnl_pct < 0 else 0
            
            # 4. 유동성 리스크
            volume = market_data.get(symbol, {}).get('volume', 0)
            liquidity_score = max(50 - volume / 1000000 * 10, 0)  # 거래량 기반
            
            overall_score = (
                volatility_score * 0.3 +
                size_score * 0.3 +
                loss_score * 0.25 +
                liquidity_score * 0.15
            )
            
            return {
                'overall_score': overall_score,
                'risk_level': self._determine_risk_level(overall_score),
                'volatility_score': volatility_score,
                'size_score': size_score,
                'loss_score': loss_score,
                'liquidity_score': liquidity_score,
                'recommended_action': self._get_risk_action_recommendation(overall_score)
            }
            
        except Exception as e:
            return {'overall_score': 50, 'risk_level': 'MEDIUM', 'error': str(e)}
    
    async def _detect_crisis_conditions(self, market_conditions: Dict, portfolio_data: Dict) -> Dict:
        """위기 상황 감지"""
        try:
            crisis_indicators = []
            crisis_scores = {}
            
            # 1. 시장 크래시 감지
            market_drop = market_conditions.get('kospi_change', 0)
            if market_drop < -3:
                crisis_scores['MARKET_CRASH'] = min(abs(market_drop) / 10 * 100, 100)
                crisis_indicators.append('시장 급락')
            
            # 2. 유동성 위기 감지
            volume_ratio = market_conditions.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:  # 평소 대비 2배 이상 거래량
                crisis_scores['LIQUIDITY_CRISIS'] = min((volume_ratio - 1) * 50, 100)
                crisis_indicators.append('거래량 급증')
            
            # 3. 변동성 급증 감지
            volatility = market_conditions.get('volatility', 0.01)
            if volatility > 0.05:  # 5% 이상 변동성
                crisis_scores['VOLATILITY_SPIKE'] = min(volatility * 1000, 100)
                crisis_indicators.append('변동성 급증')
            
            # 4. 포트폴리오 손실 임계점
            portfolio_pnl = portfolio_data.get('total_unrealized_pnl_pct', 0)
            if portfolio_pnl < -5:  # 5% 이상 손실
                crisis_scores['PORTFOLIO_LOSS'] = min(abs(portfolio_pnl) * 10, 100)
                crisis_indicators.append('포트폴리오 손실 확대')
            
            # 최고 위기 점수와 유형 결정
            if crisis_scores:
                max_crisis_type = max(crisis_scores, key=crisis_scores.get)
                max_score = crisis_scores[max_crisis_type]
                
                severity = 'CRITICAL' if max_score > 80 else 'HIGH' if max_score > 60 else 'MEDIUM'
                
                return {
                    'is_crisis': True,
                    'crisis_type': max_crisis_type,
                    'severity': severity,
                    'crisis_score': max_score,
                    'all_crisis_scores': crisis_scores,
                    'indicators': crisis_indicators
                }
            
            return {'is_crisis': False, 'indicators': []}
            
        except Exception as e:
            self.logger.error(f"위기 감지 실패: {e}")
            return {'is_crisis': False, 'error': str(e)}
    
    def _calculate_current_volatility(self, market_conditions: Dict, symbol: str) -> float:
        """현재 변동성 계산"""
        try:
            # 기본값 설정
            base_volatility = 0.02  # 2%
            
            # 시장 데이터에서 변동성 정보 가져오기
            market_volatility = market_conditions.get('market_volatility', base_volatility)
            symbol_data = market_conditions.get(symbol, {})
            symbol_volatility = symbol_data.get('volatility', base_volatility)
            
            # 최근 가격 변동 반영
            recent_changes = symbol_data.get('recent_price_changes', [])
            if recent_changes:
                recent_volatility = sum(abs(change) for change in recent_changes) / len(recent_changes) / 100
                return max(market_volatility, symbol_volatility, recent_volatility)
            
            return max(market_volatility, symbol_volatility)
            
        except Exception:
            return 0.02  # 기본 2% 변동성
    
    def _calculate_dynamic_stop_loss(self, entry_price: float, current_price: float, 
                                   volatility: float, prediction_data: Dict) -> float:
        """동적 손절매 레벨 계산"""
        try:
            # 기본 손절매율
            base_stop_pct = 0.03  # 3%
            
            # 변동성 기반 조정
            volatility_multiplier = max(1.0, volatility / 0.02)  # 2% 기준
            adjusted_stop_pct = base_stop_pct * volatility_multiplier
            
            # 예측 신뢰도 기반 조정
            confidence = prediction_data.get('confidence', 0.5)
            confidence_multiplier = 1.5 - confidence  # 신뢰도 높으면 손절 여유
            final_stop_pct = adjusted_stop_pct * confidence_multiplier
            
            # 최대 5% 손절로 제한
            final_stop_pct = min(final_stop_pct, 0.05)
            
            return entry_price * (1 - final_stop_pct)
            
        except Exception:
            return entry_price * 0.97  # 기본 3% 손절
    
    def _calculate_dynamic_take_profit(self, entry_price: float, current_price: float,
                                     volatility: float, prediction_data: Dict) -> float:
        """동적 익절매 레벨 계산"""
        try:
            # 기본 익절매율
            base_profit_pct = 0.05  # 5%
            
            # 변동성 기반 조정
            volatility_multiplier = max(1.0, volatility / 0.02)
            adjusted_profit_pct = base_profit_pct * volatility_multiplier
            
            # 예측 신뢰도 기반 조정
            confidence = prediction_data.get('confidence', 0.5)
            confidence_multiplier = 0.5 + confidence  # 신뢰도 높으면 목표 상향
            final_profit_pct = adjusted_profit_pct * confidence_multiplier
            
            return entry_price * (1 + final_profit_pct)
            
        except Exception:
            return entry_price * 1.05  # 기본 5% 익절
    
    def _calculate_trailing_stop(self, entry_price: float, current_price: float, volatility: float) -> float:
        """트레일링 스톱 계산"""
        try:
            if current_price <= entry_price:
                return entry_price * 0.97  # 기본 손절
            
            # 수익 구간에서 트레일링
            profit_pct = (current_price - entry_price) / entry_price
            
            # 변동성 기반 트레일링 거리
            trailing_distance = max(0.02, volatility * 2)  # 최소 2%
            
            # 트레일링 스톱 = 현재가 - (변동성 * 2)
            trailing_stop = current_price * (1 - trailing_distance)
            
            # 손실 방지 (최소한 원금 보호)
            return max(trailing_stop, entry_price * 1.01)
            
        except Exception:
            return entry_price * 0.97
    
    def _select_optimal_stop_level(self, dynamic_stop: float, trailing_stop: float, position_data: Dict) -> float:
        """최적 손절 레벨 선택"""
        try:
            entry_price = position_data.get('entry_price', 0)
            current_price = position_data.get('current_price', 0)
            
            if current_price > entry_price:
                # 수익 구간에서는 트레일링 스톱 선호
                return max(dynamic_stop, trailing_stop)
            else:
                # 손실 구간에서는 동적 손절 선호
                return max(dynamic_stop, entry_price * 0.95)  # 최대 5% 손절
                
        except Exception:
            return position_data.get('entry_price', 0) * 0.97
    
    def _generate_stop_execution_recommendation(self, symbol: str, current_price: float,
                                              stop_loss: float, take_profit: float, position_data: Dict) -> Dict:
        """손절매 실행 권고 생성"""
        try:
            entry_price = position_data.get('entry_price', current_price)
            
            # 현재 수익률 계산
            current_return_pct = (current_price - entry_price) / entry_price * 100
            
            # 리스크/리워드 비율
            risk_amount = entry_price - stop_loss
            reward_amount = take_profit - entry_price
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            
            # 실행 우선순위 결정
            if current_return_pct < -3:  # 3% 이상 손실
                priority = "HIGH"
                action = "IMMEDIATE_STOP_LOSS"
            elif current_return_pct > 5:  # 5% 이상 수익
                priority = "MEDIUM" 
                action = "CONSIDER_PROFIT_TAKING"
            else:
                priority = "LOW"
                action = "MAINTAIN_POSITION"
            
            return {
                'symbol': symbol,
                'recommended_action': action,
                'priority': priority,
                'current_return_pct': current_return_pct,
                'stop_loss_level': stop_loss,
                'take_profit_level': take_profit,
                'risk_reward_ratio': risk_reward_ratio,
                'distance_to_stop': (current_price - stop_loss) / current_price * 100,
                'distance_to_target': (take_profit - current_price) / current_price * 100
            }
            
        except Exception as e:
            return {'recommended_action': 'MONITOR', 'error': str(e)}
    
    def _calculate_risk_reward_ratio(self, current_price: float, stop_loss: float, take_profit: float) -> float:
        """리스크/리워드 비율 계산"""
        try:
            risk = current_price - stop_loss
            reward = take_profit - current_price
            return reward / risk if risk > 0 else 0
        except:
            return 1.0
    
    # === 추가 헬퍼 메서드들 ===
    
    def _calculate_concentration_risk(self, positions: Dict, total_value: float) -> float:
        """집중도 리스크 계산"""
        try:
            if total_value == 0:
                return 0
            
            position_weights = []
            for pos in positions.values():
                weight = pos.get('market_value', 0) / total_value
                position_weights.append(weight)
            
            # HHI (허핀달-허쉬만 지수) 계산
            hhi = sum(weight ** 2 for weight in position_weights)
            
            # 0-100 점수로 변환 (HHI가 높을수록 집중도 위험)
            return min(hhi * 100, 100)
            
        except Exception:
            return 50  # 기본값
    
    def _calculate_volatility_risk(self, positions: Dict, market_data: Dict) -> float:
        """변동성 리스크 계산"""
        try:
            weighted_volatility = 0
            total_weight = 0
            
            for symbol, pos in positions.items():
                weight = pos.get('market_value', 0)
                volatility = market_data.get(symbol, {}).get('volatility', 0.02)
                
                weighted_volatility += volatility * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0
                
            avg_volatility = weighted_volatility / total_weight
            return min(avg_volatility * 500, 100)  # 변동성 5배 스케일
            
        except Exception:
            return 50
    
    def _calculate_correlation_risk(self, positions: Dict) -> float:
        """상관관계 리스크 계산"""
        try:
            # 간단한 섹터 기반 상관관계 추정
            sectors = {}
            for symbol, pos in positions.items():
                sector = self._get_symbol_sector(symbol)
                sectors[sector] = sectors.get(sector, 0) + pos.get('market_value', 0)
            
            if len(sectors) <= 1:
                return 100  # 단일 섹터 = 최고 위험
            
            # 섹터 다양성 기반 리스크 계산
            sector_concentration = max(sectors.values()) / sum(sectors.values())
            return min(sector_concentration * 100, 100)
            
        except Exception:
            return 50
    
    def _calculate_liquidity_risk(self, positions: Dict, market_data: Dict) -> float:
        """유동성 리스크 계산"""
        try:
            weighted_liquidity_risk = 0
            total_weight = 0
            
            for symbol, pos in positions.items():
                weight = pos.get('market_value', 0)
                volume = market_data.get(symbol, {}).get('volume', 1000000)
                
                # 거래량 기반 유동성 리스크 (거래량 낮을수록 위험)
                liquidity_risk = max(50 - volume / 100000, 0)
                
                weighted_liquidity_risk += liquidity_risk * weight
                total_weight += weight
                
            if total_weight == 0:
                return 0
                
            return weighted_liquidity_risk / total_weight
            
        except Exception:
            return 25
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """리스크 점수를 레벨로 변환"""
        if risk_score >= 80:
            return 'CRITICAL'
        elif risk_score >= 60:
            return 'HIGH'
        elif risk_score >= 40:
            return 'MEDIUM'
        elif risk_score >= 20:
            return 'LOW'
        else:
            return 'MINIMAL'
    
    def _get_risk_action_recommendation(self, risk_score: float) -> str:
        """리스크 점수에 따른 액션 권고"""
        if risk_score >= 80:
            return 'IMMEDIATE_REDUCTION'
        elif risk_score >= 60:
            return 'REDUCE_POSITION'
        elif risk_score >= 40:
            return 'MONITOR_CLOSELY'
        else:
            return 'MAINTAIN'
    
    def _get_symbol_sector(self, symbol: str) -> str:
        """종목의 섹터 추정 (간단한 매핑)"""
        # 실제로는 더 정교한 섹터 분류가 필요
        tech_symbols = ['005930', '000660', '035420', '035720']  # 삼성전자, 하이닉스, 네이버, 카카오
        finance_symbols = ['055550', '086790', '316140']  # KB금융, 하나금융, 우리금융
        
        if symbol in tech_symbols:
            return 'TECHNOLOGY'
        elif symbol in finance_symbols:
            return 'FINANCE'
        else:
            return 'OTHER'
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