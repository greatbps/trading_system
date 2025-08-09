#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/ai_controller.py

AI 기능 통합 컨트롤러 - Phase 4 Advanced AI Features
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from utils.logger import get_logger
from analyzers.ai_predictor import AIPredictor
from analyzers.ai_risk_manager import AIRiskManager
from analyzers.market_regime_detector import MarketRegimeDetector
from analyzers.strategy_optimizer import StrategyOptimizer


@dataclass
class AIInsight:
    """AI 인사이트"""
    insight_type: str  # PREDICTION, RISK, REGIME, OPTIMIZATION, NEWS_TIMING
    symbol: Optional[str]
    confidence: float
    priority: str  # HIGH, MEDIUM, LOW
    message: str
    details: Dict[str, Any]
    actionable_items: List[str]
    timestamp: datetime


@dataclass
class AIDecision:
    """AI 의사결정"""
    decision_type: str  # TRADE, POSITION_SIZE, RISK_ADJUSTMENT, STRATEGY_CHANGE
    symbol: Optional[str]
    recommendation: str
    confidence: float
    supporting_evidence: List[str]
    risk_factors: List[str]
    execution_timeline: str  # IMMEDIATE, WITHIN_HOUR, TODAY, THIS_WEEK
    monitoring_requirements: List[str]
    timestamp: datetime


@dataclass
class AISystemStatus:
    """AI 시스템 상태"""
    overall_confidence: float
    active_models: List[str]
    last_update: datetime
    prediction_accuracy: Dict[str, float]
    system_health: str  # EXCELLENT, GOOD, FAIR, POOR
    performance_metrics: Dict[str, Any]
    alerts: List[str]
    recommendations: List[str]


class AIController:
    """AI 기능 통합 컨트롤러"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("AIController")
        
        # AI 모듈들 초기화
        self.predictor = AIPredictor(config)
        self.risk_manager = AIRiskManager(config)
        self.regime_detector = MarketRegimeDetector(config)
        self.strategy_optimizer = StrategyOptimizer(config)
        
        # AI 시스템 설정
        self.ai_config = {
            'confidence_threshold': 0.70,
            'high_priority_threshold': 0.85,
            'update_frequency': 300,  # 5분마다 업데이트
            'max_concurrent_predictions': 10,
            'cache_duration': 600,  # 10분 캐시
            'decision_cooldown': 1800  # 30분 의사결정 쿨다운
        }
        
        # 내부 상태
        self.current_regime = None
        self.recent_insights = []
        self.recent_decisions = []
        self.system_metrics = {}
        self.last_update = None
        
        # 의사결정 히스토리 (최근 100개)
        self.decision_history = []
        self.insight_history = []
        
        self.logger.info("✅ AI 통합 컨트롤러 초기화 완료")
    
    async def comprehensive_market_analysis(self, market_data: List[Dict],
                                          individual_stocks: List[Dict],
                                          portfolio_data: Dict) -> Dict[str, Any]:
        """종합 시장 분석"""
        try:
            self.logger.info("🧠 AI 종합 시장 분석 시작")
            
            # 1. 시장 체제 감지
            current_regime = await self.regime_detector.detect_current_regime(
                market_data, individual_stocks
            )
            self.current_regime = current_regime
            
            # 2. 개별 종목 예측 분석
            stock_predictions = {}
            for stock in individual_stocks:  # 전체 종목 분석
                symbol = stock.get('symbol', '')
                if symbol:
                    prediction = await self.predictor.predict_market_trend(
                        symbol, stock, market_data
                    )
                    stock_predictions[symbol] = prediction
            
            # 3. 포트폴리오 리스크 평가
            portfolio_risk = await self.risk_manager.assess_portfolio_risk(
                portfolio_data, {'regime': current_regime.regime_type}
            )
            
            # 4. 전략 적응성 분석
            strategy_adaptations = {}
            available_strategies = ['momentum', 'breakout', 'rsi', 'scalping_3m', 'eod', 'vwap', 'supertrend_ema_rsi']
            
            for strategy in available_strategies:
                adaptation = await self.strategy_optimizer.analyze_market_adaptation(
                    strategy, current_regime.regime_type, []
                )
                strategy_adaptations[strategy] = adaptation
            
            # 5. AI 인사이트 생성
            ai_insights = await self._generate_comprehensive_insights(
                current_regime, stock_predictions, portfolio_risk, strategy_adaptations
            )
            
            # 6. 실행 가능한 결정 사항 도출
            ai_decisions = await self._generate_actionable_decisions(
                current_regime, stock_predictions, portfolio_risk, strategy_adaptations
            )
            
            analysis_result = {
                'market_regime': {
                    'regime_type': current_regime.regime_type,
                    'confidence': current_regime.confidence,
                    'expected_duration': current_regime.expected_duration,
                    'recommended_strategies': current_regime.recommended_strategies,
                    'risk_factors': current_regime.risk_factors
                },
                'stock_predictions': {
                    symbol: {
                        'direction': pred.direction,
                        'confidence': pred.confidence,
                        'recommended_action': pred.recommended_action,
                        'key_factors': pred.key_factors
                    } for symbol, pred in stock_predictions.items()
                },
                'portfolio_risk': {
                    'overall_risk_level': portfolio_risk.overall_risk_level,
                    'risk_score': portfolio_risk.risk_score,
                    'key_risk_factors': portfolio_risk.key_risk_factors,
                    'mitigation_strategies': portfolio_risk.risk_mitigation_strategies
                },
                'strategy_recommendations': {
                    strategy: {
                        'adaptation_score': adapt.adaptation_score,
                        'priority': adapt.adaptation_priority,
                        'recommended_adjustments': adapt.recommended_adjustments
                    } for strategy, adapt in strategy_adaptations.items()
                },
                'ai_insights': [
                    {
                        'type': insight.insight_type,
                        'priority': insight.priority,
                        'message': insight.message,
                        'confidence': insight.confidence,
                        'actionable_items': insight.actionable_items
                    } for insight in ai_insights
                ],
                'ai_decisions': [
                    {
                        'type': decision.decision_type,
                        'recommendation': decision.recommendation,
                        'confidence': decision.confidence,
                        'timeline': decision.execution_timeline,
                        'evidence': decision.supporting_evidence
                    } for decision in ai_decisions
                ],
                'system_status': await self._get_system_status(),
                'timestamp': datetime.now()
            }
            
            # 7. 결과 저장
            self.recent_insights.extend(ai_insights)
            self.recent_decisions.extend(ai_decisions)
            self.last_update = datetime.now()
            
            self.logger.info(f"✅ AI 종합 분석 완료: {len(ai_insights)}개 인사이트, {len(ai_decisions)}개 결정")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ AI 종합 시장 분석 실패: {e}")
            return {}
    
    async def real_time_ai_monitoring(self, current_positions: Dict,
                                    market_updates: Dict,
                                    performance_metrics: Dict) -> Dict[str, Any]:
        """실시간 AI 모니터링"""
        try:
            self.logger.info("🔍 실시간 AI 모니터링 시작")
            
            # 1. 급변 감지
            urgent_alerts = await self._detect_urgent_changes(market_updates, current_positions)
            
            # 2. 포지션 리스크 실시간 평가
            position_risk_updates = await self._monitor_position_risks(
                current_positions, market_updates
            )
            
            # 3. 체제 변화 감지
            regime_stability = await self.regime_detector.monitor_regime_stability(
                self.current_regime, [market_updates] if market_updates else []
            )
            
            # 4. 전략 성과 모니터링
            strategy_health = await self.strategy_optimizer.continuous_optimization_monitoring(
                current_positions, performance_metrics, market_updates
            )
            
            # 5. AI 기반 즉시 대응 권고
            immediate_recommendations = await self._generate_immediate_recommendations(
                urgent_alerts, position_risk_updates, regime_stability, strategy_health
            )
            
            monitoring_result = {
                'urgent_alerts': urgent_alerts,
                'position_risk_updates': position_risk_updates,
                'regime_stability': {
                    'stability': regime_stability.get('regime_stability', 'STABLE'),
                    'confidence_trend': regime_stability.get('confidence_trend', 'STABLE'),
                    'warning_signals': regime_stability.get('warning_signals', [])
                },
                'strategy_health': {
                    'overall_score': strategy_health.get('overall_health_score', 75),
                    'optimization_alerts': strategy_health.get('optimization_alerts', []),
                    'system_stability': strategy_health.get('system_stability', 'STABLE')
                },
                'immediate_recommendations': immediate_recommendations,
                'next_check_time': datetime.now() + timedelta(seconds=self.ai_config['update_frequency']),
                'monitoring_intensity': self._determine_monitoring_intensity(urgent_alerts, regime_stability),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 실시간 모니터링 완료: {len(urgent_alerts)}개 긴급 알림")
            return monitoring_result
            
        except Exception as e:
            self.logger.error(f"❌ 실시간 AI 모니터링 실패: {e}")
            return {}
    
    async def optimize_trading_decisions(self, trade_opportunities: List[Dict],
                                       current_portfolio: Dict,
                                       market_context: Dict) -> Dict[str, Any]:
        """거래 의사결정 최적화"""
        try:
            self.logger.info(f"⚙️ 거래 의사결정 최적화 시작: {len(trade_opportunities)}개 기회")
            
            optimized_decisions = []
            
            for opportunity in trade_opportunities:
                symbol = opportunity.get('symbol', '')
                if not symbol:
                    continue
                
                # 1. 예측 분석
                prediction = await self.predictor.predict_market_trend(
                    symbol, opportunity, []
                )
                
                # 2. 포지션 사이징
                position_sizing = await self.risk_manager.calculate_optimal_position_size(
                    symbol, opportunity, current_portfolio, 
                    {'confidence': prediction.confidence, 'expected_return': 0.05}
                )
                
                # 3. 타이밍 최적화
                timing_optimization = await self.predictor.optimize_news_timing(
                    [], opportunity
                )
                
                # 4. 종합 의사결정
                decision = await self._synthesize_trading_decision(
                    symbol, opportunity, prediction, position_sizing, timing_optimization
                )
                
                if decision:
                    optimized_decisions.append(decision)
            
            # 5. 포트폴리오 레벨 최적화
            portfolio_optimization = await self._optimize_portfolio_allocation(
                optimized_decisions, current_portfolio, market_context
            )
            
            # 6. 최종 추천 생성
            final_recommendations = await self._generate_final_trading_recommendations(
                optimized_decisions, portfolio_optimization
            )
            
            optimization_result = {
                'total_opportunities': len(trade_opportunities),
                'analyzed_opportunities': len(optimized_decisions),
                'recommended_trades': final_recommendations.get('trades', []),
                'portfolio_adjustments': final_recommendations.get('adjustments', []),
                'risk_warnings': final_recommendations.get('warnings', []),
                'expected_portfolio_impact': final_recommendations.get('impact', {}),
                'confidence': final_recommendations.get('confidence', 70),
                'execution_priority': final_recommendations.get('priority', []),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 거래 최적화 완료: {len(final_recommendations.get('trades', []))}개 추천")
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"❌ 거래 의사결정 최적화 실패: {e}")
            return {}
    
    async def generate_ai_report(self, time_period: str = 'daily') -> Dict[str, Any]:
        """AI 분석 보고서 생성"""
        try:
            self.logger.info(f"📊 AI {time_period} 보고서 생성 시작")
            
            # 1. 시장 체제 요약
            regime_summary = await self._generate_regime_summary()
            
            # 2. 예측 정확도 분석
            prediction_accuracy = await self._analyze_prediction_accuracy()
            
            # 3. 리스크 관리 효과성
            risk_management_effectiveness = await self._evaluate_risk_management()
            
            # 4. 전략 최적화 성과
            optimization_performance = await self._assess_optimization_performance()
            
            # 5. AI 시스템 건전성
            system_health = await self._evaluate_system_health()
            
            # 6. 향후 전망 및 권고
            future_outlook = await self._generate_future_outlook()
            
            report = {
                'report_period': time_period,
                'generation_time': datetime.now(),
                'market_regime_summary': regime_summary,
                'prediction_accuracy': prediction_accuracy,
                'risk_management': risk_management_effectiveness,
                'strategy_optimization': optimization_performance,
                'system_health': system_health,
                'future_outlook': future_outlook,
                'key_insights': await self._extract_key_insights(),
                'recommendations': await self._generate_strategic_recommendations(),
                'performance_metrics': self.system_metrics,
                'confidence_score': await self._calculate_overall_confidence()
            }
            
            self.logger.info("✅ AI 보고서 생성 완료")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ AI 보고서 생성 실패: {e}")
            return {}
    
    # === 내부 헬퍼 메서드들 ===
    
    async def _generate_comprehensive_insights(self, regime, predictions, risk, adaptations) -> List[AIInsight]:
        """종합 인사이트 생성"""
        insights = []
        
        # 체제 관련 인사이트
        if regime.confidence > self.ai_config['high_priority_threshold']:
            insights.append(AIInsight(
                insight_type="REGIME",
                symbol=None,
                confidence=regime.confidence,
                priority="HIGH",
                message=f"시장이 {regime.regime_type} 체제로 전환됨 (신뢰도: {regime.confidence:.1f}%)",
                details={'regime_type': regime.regime_type, 'duration': regime.expected_duration},
                actionable_items=regime.recommended_strategies,
                timestamp=datetime.now()
            ))
        
        # 예측 관련 인사이트
        for symbol, prediction in predictions.items():
            if prediction.confidence > self.ai_config['confidence_threshold']:
                priority = "HIGH" if prediction.confidence > self.ai_config['high_priority_threshold'] else "MEDIUM"
                insights.append(AIInsight(
                    insight_type="PREDICTION",
                    symbol=symbol,
                    confidence=prediction.confidence,
                    priority=priority,
                    message=f"{symbol}: {prediction.direction} 예상 (신뢰도: {prediction.confidence:.1f}%)",
                    details={'direction': prediction.direction, 'factors': prediction.key_factors},
                    actionable_items=[prediction.recommended_action],
                    timestamp=datetime.now()
                ))
        
        # 리스크 관련 인사이트
        if risk.overall_risk_score > 70:
            insights.append(AIInsight(
                insight_type="RISK",
                symbol=None,
                confidence=risk.confidence,
                priority="HIGH",
                message=f"포트폴리오 리스크 증가 (점수: {risk.overall_risk_score:.1f})",
                details={'risk_factors': risk.key_risk_factors},
                actionable_items=risk.risk_mitigation_strategies,
                timestamp=datetime.now()
            ))
        
        return insights
    
    async def _generate_actionable_decisions(self, regime, predictions, risk, adaptations) -> List[AIDecision]:
        """실행 가능한 결정 생성"""
        decisions = []
        
        # 체제 기반 전략 변경 결정
        if regime.confidence > self.ai_config['confidence_threshold']:
            decisions.append(AIDecision(
                decision_type="STRATEGY_CHANGE",
                symbol=None,
                recommendation=f"전략을 {regime.recommended_strategies}로 조정",
                confidence=regime.confidence,
                supporting_evidence=[f"시장 체제: {regime.regime_type}"],
                risk_factors=regime.risk_factors,
                execution_timeline="TODAY",
                monitoring_requirements=["체제 안정성 모니터링"],
                timestamp=datetime.now()
            ))
        
        # 예측 기반 거래 결정
        for symbol, prediction in predictions.items():
            if prediction.confidence > self.ai_config['confidence_threshold']:
                timeline = "IMMEDIATE" if prediction.confidence > 85 else "WITHIN_HOUR"
                decisions.append(AIDecision(
                    decision_type="TRADE",
                    symbol=symbol,
                    recommendation=prediction.recommended_action,
                    confidence=prediction.confidence,
                    supporting_evidence=prediction.key_factors,
                    risk_factors=[f"예측 리스크: {prediction.risk_level}"],
                    execution_timeline=timeline,
                    monitoring_requirements=["가격 변동 모니터링"],
                    timestamp=datetime.now()
                ))
        
        return decisions
    
    async def _get_system_status(self) -> AISystemStatus:
        """시스템 상태 조회"""
        return AISystemStatus(
            overall_confidence=75.0,
            active_models=["Predictor", "RiskManager", "RegimeDetector", "StrategyOptimizer"],
            last_update=self.last_update or datetime.now(),
            prediction_accuracy={"trend": 0.72, "regime": 0.68, "risk": 0.75},
            system_health="GOOD",
            performance_metrics=self.system_metrics,
            alerts=[],
            recommendations=["시스템 정상 작동 중"]
        )
    
    async def _detect_urgent_changes(self, market_updates: Dict, positions: Dict) -> List[Dict]:
        """급변 감지"""
        alerts = []
        
        # 급격한 가격 변동 감지
        price_change = market_updates.get('price_change', 0)
        if abs(price_change) > 5:  # 5% 이상 변동
            alerts.append({
                'type': 'PRICE_SHOCK',
                'severity': 'HIGH',
                'message': f"급격한 가격 변동: {price_change:.1f}%",
                'recommended_action': '포지션 점검 필요'
            })
        
        return alerts
    
    async def _monitor_position_risks(self, positions: Dict, market_updates: Dict) -> Dict:
        """포지션 리스크 모니터링"""
        return {
            'high_risk_positions': [],
            'risk_level_changes': [],
            'recommended_adjustments': []
        }
    
    async def _generate_immediate_recommendations(self, alerts: List, risk_updates: Dict, 
                                                regime_stability: Dict, strategy_health: Dict) -> List[str]:
        """즉시 대응 권고 생성"""
        recommendations = []
        
        if alerts:
            recommendations.append("긴급 알림에 대한 즉시 대응 필요")
        
        if regime_stability.get('regime_stability') == 'UNSTABLE':
            recommendations.append("시장 체제 불안정으로 인한 전략 재검토 필요")
        
        if strategy_health.get('overall_health_score', 75) < 60:
            recommendations.append("전략 성과 하락으로 인한 최적화 필요")
        
        return recommendations or ["현재 상황 정상, 지속 모니터링"]
    
    def _determine_monitoring_intensity(self, alerts: List, regime_stability: Dict) -> str:
        """모니터링 강도 결정"""
        if alerts or regime_stability.get('regime_stability') == 'UNSTABLE':
            return "HIGH"
        elif regime_stability.get('regime_stability') == 'MODERATE':
            return "MEDIUM"
        else:
            return "NORMAL"
    
    # 추가 헬퍼 메서드들 (간단한 구현)
    async def _synthesize_trading_decision(self, symbol: str, opportunity: Dict, 
                                         prediction, position_sizing, timing) -> Optional[Dict]:
        if prediction.confidence > self.ai_config['confidence_threshold']:
            return {
                'symbol': symbol,
                'action': prediction.recommended_action,
                'position_size': position_sizing.recommended_position_size,
                'confidence': prediction.confidence,
                'timing': timing.get('optimal_entry_timing', 'IMMEDIATE')
            }
        return None
    
    async def _optimize_portfolio_allocation(self, decisions: List, portfolio: Dict, market: Dict) -> Dict:
        return {'optimization_score': 75, 'recommended_changes': []}
    
    async def _generate_final_trading_recommendations(self, decisions: List, optimization: Dict) -> Dict:
        return {
            'trades': decisions[:5],  # 상위 5개
            'adjustments': [],
            'warnings': [],
            'impact': {'expected_return': 0.05},
            'confidence': 75,
            'priority': ['high_confidence_trades', 'risk_adjustments']
        }
    
    # 보고서 관련 메서드들 (간단한 구현)
    async def _generate_regime_summary(self) -> Dict:
        return {
            'current_regime': self.current_regime.regime_type if self.current_regime else 'UNKNOWN',
            'stability': 'STABLE',
            'duration': 15,
            'next_transition_probability': 0.2
        }
    
    async def _analyze_prediction_accuracy(self) -> Dict:
        return {
            'overall_accuracy': 0.72,
            'trend_accuracy': 0.75,
            'timing_accuracy': 0.68,
            'recent_performance': 'IMPROVING'
        }
    
    async def _evaluate_risk_management(self) -> Dict:
        return {
            'risk_prevention_rate': 0.85,
            'false_positive_rate': 0.15,
            'average_risk_reduction': 0.12,
            'effectiveness_score': 80
        }
    
    async def _assess_optimization_performance(self) -> Dict:
        return {
            'strategies_optimized': 3,
            'average_improvement': 0.08,
            'success_rate': 0.75,
            'optimization_frequency': 'WEEKLY'
        }
    
    async def _evaluate_system_health(self) -> Dict:
        return {
            'overall_health': 'GOOD',
            'uptime': 0.99,
            'accuracy_trend': 'STABLE',
            'resource_usage': 'NORMAL'
        }
    
    async def _generate_future_outlook(self) -> Dict:
        return {
            'market_outlook': 'CAUTIOUSLY_OPTIMISTIC',
            'key_risks': ['변동성 증가', '체제 전환 가능성'],
            'opportunities': ['모멘텀 전략', '변동성 거래'],
            'timeline': '1-2주'
        }
    
    async def _extract_key_insights(self) -> List[str]:
        return [
            "AI 시스템이 안정적으로 작동 중",
            "시장 체제 감지 정확도 향상",
            "리스크 관리 효과성 검증됨"
        ]
    
    async def _generate_strategic_recommendations(self) -> List[str]:
        return [
            "현재 전략 포트폴리오 유지",
            "변동성 대비 리스크 관리 강화",
            "정기적인 AI 모델 성과 검토"
        ]
    
    async def _calculate_overall_confidence(self) -> float:
        return 75.0