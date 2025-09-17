#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/strategy_optimizer.py

AI 기반 전략 최적화 엔진 - Phase 4 Advanced AI Features
"""

import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass
from collections import defaultdict

from utils.logger import get_logger
from analyzers.gemini_analyzer import GeminiAnalyzer


@dataclass
class StrategyPerformance:
    """전략 성과 데이터"""
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    volatility: float
    beta: float
    alpha: float
    information_ratio: float
    calmar_ratio: float
    sortino_ratio: float


@dataclass
class OptimizationResult:
    """최적화 결과"""
    strategy_name: str
    original_params: Dict[str, Any]
    optimized_params: Dict[str, Any]
    performance_improvement: float  # 성과 개선률 (%)
    confidence: float  # 최적화 신뢰도
    expected_metrics: Dict[str, float]
    optimization_method: str
    validation_results: Dict[str, Any]
    implementation_date: datetime
    monitoring_frequency: str
    risk_warnings: List[str]
    ai_insights: List[str]


@dataclass
class MarketAdaptation:
    """시장 적응성 분석"""
    strategy_name: str
    market_regime: str
    adaptation_score: float  # 0-100
    performance_in_regime: float
    recommended_adjustments: Dict[str, Any]
    confidence_level: float
    adaptation_priority: str  # HIGH, MEDIUM, LOW
    monitoring_signals: List[str]


class StrategyOptimizer:
    """AI 기반 전략 최적화 엔진"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("StrategyOptimizer")
        self.gemini_analyzer = GeminiAnalyzer(config)
        
        # 최적화 매개변수
        self.optimization_params = {
            'min_sample_size': 30,  # 최소 거래 수
            'confidence_threshold': 0.70,  # 신뢰도 임계값
            'max_parameter_change': 0.30,  # 최대 매개변수 변경률
            'validation_period': 30,  # 검증 기간 (일)
            'reoptimization_frequency': 7  # 재최적화 주기 (일)
        }
        
        # 성과 가중치
        self.performance_weights = {
            'return': 0.25,
            'risk_adjusted_return': 0.25,
            'drawdown': 0.15,
            'win_rate': 0.15,
            'profit_factor': 0.10,
            'stability': 0.10
        }
        
        # 전략별 최적화 가능한 매개변수
        self.optimizable_params = {
            'momentum': {
                'lookback_period': {'min': 5, 'max': 30, 'step': 1},
                'momentum_threshold': {'min': 0.01, 'max': 0.10, 'step': 0.01},
                'volume_factor': {'min': 1.2, 'max': 3.0, 'step': 0.1}
            },
            'breakout': {
                'breakout_period': {'min': 10, 'max': 50, 'step': 5},
                'volume_threshold': {'min': 1.5, 'max': 4.0, 'step': 0.25},
                'confirmation_period': {'min': 1, 'max': 5, 'step': 1}
            },
            'rsi': {
                'rsi_period': {'min': 10, 'max': 25, 'step': 1},
                'oversold_threshold': {'min': 20, 'max': 35, 'step': 5},
                'overbought_threshold': {'min': 65, 'max': 85, 'step': 5},
                'divergence_lookback': {'min': 5, 'max': 20, 'step': 1}
            },
            'scalping_3m': {
                'volume_spike_threshold': {'min': 1.5, 'max': 3.0, 'step': 0.25},
                'profit_target': {'min': 0.3, 'max': 1.0, 'step': 0.1},
                'stop_loss': {'min': 0.2, 'max': 0.5, 'step': 0.05},
                'holding_time_max': {'min': 3, 'max': 15, 'step': 1}
            }
        }
        
        self.logger.info("✅ 전략 최적화 엔진 초기화 완료")
    
    async def optimize_strategy(self, strategy_name: str, 
                              performance_data: Dict,
                              market_conditions: Dict,
                              historical_trades: List[Dict] = None) -> OptimizationResult:
        """전략 매개변수 최적화"""
        try:
            self.logger.info(f"⚙️ {strategy_name} 전략 최적화 시작")
            
            # 1. 현재 성과 분석
            current_performance = await self._analyze_current_performance(
                strategy_name, performance_data, historical_trades
            )
            
            # 2. 최적화 가능성 평가
            optimization_potential = await self._assess_optimization_potential(
                strategy_name, current_performance, market_conditions
            )
            
            if optimization_potential['score'] < 50:
                self.logger.info(f"🔄 {strategy_name} 최적화 불필요 (점수: {optimization_potential['score']})")
                return await self._create_no_optimization_result(strategy_name, current_performance)
            
            # 3. 매개변수 탐색 공간 정의
            parameter_space = await self._define_parameter_space(
                strategy_name, current_performance, market_conditions
            )
            
            # 4. AI 기반 매개변수 최적화
            optimization_candidates = await self._ai_parameter_optimization(
                strategy_name, parameter_space, current_performance, market_conditions
            )
            
            # 5. 백테스팅 기반 검증
            validated_candidates = await self._validate_optimization_candidates(
                strategy_name, optimization_candidates, historical_trades
            )
            
            # 6. 최적 매개변수 선택
            best_candidate = await self._select_best_candidate(
                validated_candidates, current_performance
            )
            
            # 7. 최적화 결과 생성
            optimization_result = await self._create_optimization_result(
                strategy_name, current_performance, best_candidate, market_conditions
            )
            
            self.logger.info(f"✅ {strategy_name} 최적화 완료: {optimization_result.performance_improvement:.1f}% 개선")
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"❌ {strategy_name} 전략 최적화 실패: {e}")
            return self._create_default_optimization_result(strategy_name)
    
    async def analyze_market_adaptation(self, strategy_name: str,
                                      current_regime: str,
                                      performance_history: List[Dict]) -> MarketAdaptation:
        """시장 적응성 분석"""
        try:
            self.logger.info(f"🌐 {strategy_name} 시장 적응성 분석 시작 (체제: {current_regime})")
            
            # 1. 체제별 성과 분석
            regime_performance = await self._analyze_regime_performance(
                strategy_name, current_regime, performance_history
            )
            
            # 2. 적응성 점수 계산
            adaptation_score = await self._calculate_adaptation_score(
                strategy_name, current_regime, regime_performance
            )
            
            # 3. AI 기반 적응성 평가
            ai_adaptation_analysis = await self._ai_adaptation_analysis(
                strategy_name, current_regime, regime_performance
            )
            
            # 4. 조정 권장사항 생성
            recommended_adjustments = await self._generate_adaptation_adjustments(
                strategy_name, current_regime, ai_adaptation_analysis
            )
            
            adaptation = MarketAdaptation(
                strategy_name=strategy_name,
                market_regime=current_regime,
                adaptation_score=adaptation_score,
                performance_in_regime=regime_performance.get('current_performance', 0),
                recommended_adjustments=recommended_adjustments,
                confidence_level=ai_adaptation_analysis.get('confidence', 70),
                adaptation_priority=self._determine_adaptation_priority(adaptation_score),
                monitoring_signals=ai_adaptation_analysis.get('monitoring_signals', [])
            )
            
            self.logger.info(f"✅ {strategy_name} 적응성 분석 완료: {adaptation_score:.1f}점")
            return adaptation
            
        except Exception as e:
            self.logger.error(f"❌ {strategy_name} 적응성 분석 실패: {e}")
            return self._create_default_adaptation(strategy_name, current_regime)
    
    async def multi_strategy_optimization(self, strategies: List[str],
                                        portfolio_performance: Dict,
                                        market_conditions: Dict) -> Dict[str, OptimizationResult]:
        """다중 전략 통합 최적화"""
        try:
            self.logger.info(f"🔄 다중 전략 최적화 시작: {len(strategies)}개 전략")
            
            # 1. 개별 전략 최적화
            individual_optimizations = {}
            for strategy in strategies:
                individual_opt = await self.optimize_strategy(
                    strategy, 
                    portfolio_performance.get(strategy, {}),
                    market_conditions
                )
                individual_optimizations[strategy] = individual_opt
            
            # 2. 전략간 상관관계 분석
            correlation_analysis = await self._analyze_strategy_correlations(
                strategies, portfolio_performance
            )
            
            # 3. 포트폴리오 레벨 최적화
            portfolio_optimization = await self._optimize_strategy_allocation(
                individual_optimizations, correlation_analysis, market_conditions
            )
            
            # 4. 통합 최적화 결과 생성
            integrated_results = await self._create_integrated_optimization(
                individual_optimizations, portfolio_optimization
            )
            
            self.logger.info(f"✅ 다중 전략 최적화 완료: {len(integrated_results)}개 전략")
            return integrated_results
            
        except Exception as e:
            self.logger.error(f"❌ 다중 전략 최적화 실패: {e}")
            return {}
    
    async def dynamic_strategy_selection(self, available_strategies: List[str],
                                       current_market_regime: str,
                                       portfolio_state: Dict,
                                       performance_history: Dict) -> Dict[str, Any]:
        """동적 전략 선택"""
        try:
            self.logger.info(f"🎯 동적 전략 선택 시작 (체제: {current_market_regime})")
            
            # 1. 체제별 전략 성과 분석
            strategy_regime_performance = {}
            for strategy in available_strategies:
                performance = await self._evaluate_strategy_for_regime(
                    strategy, current_market_regime, performance_history.get(strategy, {})
                )
                strategy_regime_performance[strategy] = performance
            
            # 2. AI 기반 전략 순위 매기기
            ai_strategy_ranking = await self._ai_strategy_ranking(
                available_strategies, current_market_regime, 
                strategy_regime_performance, portfolio_state
            )
            
            # 3. 포트폴리오 다양성 고려
            diversification_adjustment = await self._apply_diversification_logic(
                ai_strategy_ranking, portfolio_state
            )
            
            # 4. 최종 전략 선택 및 가중치 결정
            final_selection = await self._finalize_strategy_selection(
                diversification_adjustment, current_market_regime
            )
            
            result = {
                'selected_strategies': final_selection.get('strategies', []),
                'strategy_weights': final_selection.get('weights', {}),
                'confidence': final_selection.get('confidence', 70),
                'rationale': final_selection.get('rationale', []),
                'monitoring_frequency': final_selection.get('monitoring_frequency', 'DAILY'),
                'rebalancing_triggers': final_selection.get('rebalancing_triggers', []),
                'risk_warnings': final_selection.get('risk_warnings', []),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 동적 전략 선택 완료: {len(result['selected_strategies'])}개 전략")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 동적 전략 선택 실패: {e}")
            return {}
    
    async def continuous_optimization_monitoring(self, active_strategies: Dict[str, Dict],
                                               performance_metrics: Dict,
                                               market_changes: Dict) -> Dict[str, Any]:
        """지속적 최적화 모니터링"""
        try:
            self.logger.info("📊 지속적 최적화 모니터링 시작")
            
            optimization_alerts = []
            strategy_health_scores = {}
            
            for strategy_name, strategy_data in active_strategies.items():
                # 1. 전략 건전성 평가
                health_score = await self._evaluate_strategy_health(
                    strategy_name, strategy_data, performance_metrics.get(strategy_name, {})
                )
                strategy_health_scores[strategy_name] = health_score
                
                # 2. 최적화 필요성 감지
                optimization_need = await self._detect_optimization_need(
                    strategy_name, health_score, market_changes
                )
                
                if optimization_need['required']:
                    optimization_alerts.append({
                        'strategy': strategy_name,
                        'urgency': optimization_need['urgency'],
                        'reason': optimization_need['reason'],
                        'recommended_action': optimization_need['action']
                    })
            
            # 3. 시장 변화 대응 평가
            market_response_analysis = await self._analyze_market_response_adequacy(
                active_strategies, market_changes
            )
            
            # 4. AI 기반 종합 모니터링 리포트
            ai_monitoring_report = await self._generate_ai_monitoring_report(
                strategy_health_scores, optimization_alerts, market_response_analysis
            )
            
            monitoring_result = {
                'overall_health_score': np.mean(list(strategy_health_scores.values())),
                'strategy_health_scores': strategy_health_scores,
                'optimization_alerts': optimization_alerts,
                'market_response_adequacy': market_response_analysis.get('adequacy_score', 70),
                'recommended_actions': ai_monitoring_report.get('priority_actions', []),
                'system_stability': ai_monitoring_report.get('stability_assessment', 'STABLE'),
                'next_review_date': datetime.now() + timedelta(days=self.optimization_params['reoptimization_frequency']),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 최적화 모니터링 완료: 전체 건전성 {monitoring_result['overall_health_score']:.1f}점")
            return monitoring_result
            
        except Exception as e:
            self.logger.error(f"❌ 지속적 최적화 모니터링 실패: {e}")
            return {}
    
    async def machine_learning_optimization(self, strategy_name: str,
                                          historical_performance: List[Dict],
                                          market_features: List[Dict]) -> Dict[str, Any]:
        """머신러닝 기반 전략 최적화"""
        try:
            self.logger.info(f"🤖 {strategy_name} 머신러닝 최적화 시작")
            
            # 1. 특성 엔지니어링
            features = await self._engineer_features(historical_performance, market_features)
            
            # 2. 모델 훈련 데이터 준비
            training_data = await self._prepare_training_data(features, historical_performance)
            
            # 3. AI 모델을 통한 파라미터 패턴 분석
            pattern_analysis = await self._ai_parameter_pattern_analysis(
                strategy_name, training_data
            )
            
            # 4. 강화학습 기반 파라미터 탐색
            rl_optimization = await self._reinforcement_learning_optimization(
                strategy_name, pattern_analysis, training_data
            )
            
            # 5. 앙상블 최적화 결과
            ensemble_params = await self._ensemble_optimization_results(
                [pattern_analysis, rl_optimization]
            )
            
            # 6. 백테스팅 검증
            validation_results = await self._validate_ml_optimization(
                strategy_name, ensemble_params, historical_performance
            )
            
            ml_result = {
                'strategy_name': strategy_name,
                'ml_optimized_params': ensemble_params,
                'feature_importance': pattern_analysis.get('feature_importance', {}),
                'model_confidence': validation_results.get('confidence', 0.7),
                'expected_improvement': validation_results.get('improvement', 0.05),
                'risk_metrics': validation_results.get('risk_metrics', {}),
                'implementation_priority': self._determine_ml_priority(validation_results),
                'monitoring_recommendations': self._generate_ml_monitoring_plan(),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 머신러닝 최적화 완료 - 개선 예상: {ml_result['expected_improvement']:.2%}")
            return ml_result
            
        except Exception as e:
            self.logger.error(f"❌ 머신러닝 최적화 실패: {e}")
            return {}
    
    async def genetic_algorithm_optimization(self, strategy_name: str,
                                           parameter_bounds: Dict[str, Tuple],
                                           fitness_function: callable,
                                           generations: int = 50) -> Dict[str, Any]:
        """유전 알고리즘 기반 파라미터 최적화"""
        try:
            self.logger.info(f"🧬 {strategy_name} 유전 알고리즘 최적화 시작")
            
            # 1. 초기 모집단 생성
            population = await self._initialize_ga_population(
                parameter_bounds, population_size=50
            )
            
            best_fitness_history = []
            best_individual = None
            best_fitness = float('-inf')
            
            for generation in range(generations):
                # 2. 적합도 평가
                fitness_scores = []
                for individual in population:
                    try:
                        fitness = await fitness_function(individual)
                        fitness_scores.append(fitness)
                        
                        if fitness > best_fitness:
                            best_fitness = fitness
                            best_individual = individual.copy()
                    except:
                        fitness_scores.append(float('-inf'))
                
                best_fitness_history.append(best_fitness)
                
                # 3. 선택, 교차, 돌연변이
                new_population = await self._ga_evolution_step(
                    population, fitness_scores, parameter_bounds
                )
                population = new_population
                
                # 조기 종료 조건
                if generation > 10 and len(set(best_fitness_history[-5:])) == 1:
                    self.logger.info(f"🎯 GA 조기 수렴: {generation+1} 세대에서 중단")
                    break
            
            # 4. AI 기반 결과 분석
            ga_analysis = await self._analyze_ga_results(
                best_individual, best_fitness, best_fitness_history
            )
            
            ga_result = {
                'strategy_name': strategy_name,
                'best_parameters': best_individual,
                'best_fitness': best_fitness,
                'generations_completed': generation + 1,
                'convergence_analysis': ga_analysis,
                'fitness_history': best_fitness_history,
                'parameter_sensitivity': await self._analyze_parameter_sensitivity(
                    best_individual, parameter_bounds, fitness_function
                ),
                'implementation_confidence': ga_analysis.get('confidence', 0.8),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 유전 알고리즘 최적화 완료 - 최고 적합도: {best_fitness:.4f}")
            return ga_result
            
        except Exception as e:
            self.logger.error(f"❌ 유전 알고리즘 최적화 실패: {e}")
            return {}
    
    async def bayesian_optimization(self, strategy_name: str,
                                  parameter_space: Dict,
                                  objective_function: callable,
                                  n_iterations: int = 30) -> Dict[str, Any]:
        """베이지안 최적화"""
        try:
            self.logger.info(f"📊 {strategy_name} 베이지안 최적화 시작")
            
            # 1. 초기 관찰점 생성
            initial_points = await self._generate_initial_points(parameter_space, n_points=5)
            
            observations = []
            for point in initial_points:
                try:
                    objective_value = await objective_function(point)
                    observations.append({
                        'parameters': point,
                        'objective': objective_value,
                        'iteration': len(observations)
                    })
                except:
                    observations.append({
                        'parameters': point,
                        'objective': float('-inf'),
                        'iteration': len(observations)
                    })
            
            best_observation = max(observations, key=lambda x: x['objective'])
            
            # 2. AI 기반 획득 함수를 통한 반복 최적화
            for iteration in range(n_iterations - len(initial_points)):
                # 가우시안 프로세스 근사를 위해 AI 활용
                next_point = await self._ai_acquisition_function(
                    observations, parameter_space, strategy_name
                )
                
                try:
                    objective_value = await objective_function(next_point)
                    observation = {
                        'parameters': next_point,
                        'objective': objective_value,
                        'iteration': len(observations)
                    }
                    observations.append(observation)
                    
                    if objective_value > best_observation['objective']:
                        best_observation = observation
                        self.logger.info(f"🎯 새로운 최적점 발견: {objective_value:.4f}")
                        
                except:
                    observations.append({
                        'parameters': next_point,
                        'objective': float('-inf'),
                        'iteration': len(observations)
                    })
            
            # 3. 결과 분석
            bayesian_analysis = await self._analyze_bayesian_results(
                observations, best_observation, parameter_space
            )
            
            bayesian_result = {
                'strategy_name': strategy_name,
                'optimal_parameters': best_observation['parameters'],
                'optimal_objective': best_observation['objective'],
                'total_evaluations': len(observations),
                'convergence_analysis': bayesian_analysis,
                'parameter_importance': await self._calculate_parameter_importance(observations),
                'uncertainty_analysis': bayesian_analysis.get('uncertainty', {}),
                'recommendation_confidence': bayesian_analysis.get('confidence', 0.8),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"✅ 베이지안 최적화 완료 - 최적 목표값: {best_observation['objective']:.4f}")
            return bayesian_result
            
        except Exception as e:
            self.logger.error(f"❌ 베이지안 최적화 실패: {e}")
            return {}
    
    # === 내부 헬퍼 메서드들 ===
    
    async def _analyze_current_performance(self, strategy_name: str, 
                                         performance_data: Dict,
                                         historical_trades: List[Dict]) -> StrategyPerformance:
        """현재 성과 분석"""
        try:
            # 기본값 설정
            defaults = {
                'total_return': 0.0,
                'annual_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.5,
                'total_trades': 0
            }
            
            # 실제 데이터에서 추출 또는 기본값 사용
            total_return = performance_data.get('total_return', defaults['total_return'])
            win_rate = performance_data.get('win_rate', defaults['win_rate'])
            total_trades = len(historical_trades) if historical_trades else defaults['total_trades']
            
            # 승패 거래 계산
            if historical_trades:
                winning_trades = len([t for t in historical_trades if t.get('pnl', 0) > 0])
                losing_trades = total_trades - winning_trades
                
                # 평균 승/패 계산
                winning_pnls = [t.get('pnl', 0) for t in historical_trades if t.get('pnl', 0) > 0]
                losing_pnls = [t.get('pnl', 0) for t in historical_trades if t.get('pnl', 0) < 0]
                
                avg_win = np.mean(winning_pnls) if winning_pnls else 0
                avg_loss = abs(np.mean(losing_pnls)) if losing_pnls else 0
                
                profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if avg_loss > 0 and losing_trades > 0 else 1.0
            else:
                winning_trades = int(total_trades * win_rate)
                losing_trades = total_trades - winning_trades
                avg_win = 0.05  # 기본값
                avg_loss = 0.03  # 기본값
                profit_factor = 1.0
            
            return StrategyPerformance(
                strategy_name=strategy_name,
                total_return=total_return,
                annual_return=performance_data.get('annual_return', total_return),
                sharpe_ratio=performance_data.get('sharpe_ratio', defaults['sharpe_ratio']),
                max_drawdown=performance_data.get('max_drawdown', defaults['max_drawdown']),
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                volatility=performance_data.get('volatility', 0.15),
                beta=performance_data.get('beta', 1.0),
                alpha=performance_data.get('alpha', 0.0),
                information_ratio=performance_data.get('information_ratio', 0.0),
                calmar_ratio=performance_data.get('calmar_ratio', 0.0),
                sortino_ratio=performance_data.get('sortino_ratio', 0.0)
            )
            
        except Exception as e:
            self.logger.error(f"❌ {strategy_name} 성과 분석 실패: {e}")
            return self._create_default_performance(strategy_name)
    
    async def _assess_optimization_potential(self, strategy_name: str,
                                           performance: StrategyPerformance,
                                           market_conditions: Dict) -> Dict:
        """최적화 가능성 평가"""
        try:
            potential_score = 0
            reasons = []
            
            # 성과 기준 평가
            if performance.sharpe_ratio < 1.0:
                potential_score += 20
                reasons.append("낮은 샤프 비율")
            
            if performance.max_drawdown > 0.15:
                potential_score += 15
                reasons.append("높은 최대 손실")
            
            if performance.win_rate < 0.45:
                potential_score += 15
                reasons.append("낮은 승률")
            
            if performance.total_trades < self.optimization_params['min_sample_size']:
                potential_score -= 30
                reasons.append("부족한 거래 샘플")
            
            # 시장 조건 고려
            market_volatility = market_conditions.get('volatility', 0.2)
            if market_volatility > 0.3:
                potential_score += 10
                reasons.append("높은 시장 변동성")
            
            # AI 기반 추가 평가
            ai_assessment = await self._ai_optimization_potential_assessment(
                strategy_name, performance, market_conditions
            )
            
            ai_score = ai_assessment.get('potential_score', 0)
            potential_score += ai_score
            reasons.extend(ai_assessment.get('reasons', []))
            
            return {
                'score': max(0, min(100, potential_score)),
                'reasons': reasons,
                'ai_confidence': ai_assessment.get('confidence', 70)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 최적화 가능성 평가 실패: {e}")
            return {'score': 50, 'reasons': ['평가 오류'], 'ai_confidence': 50}
    
    async def _ai_parameter_optimization(self, strategy_name: str,
                                       parameter_space: Dict,
                                       current_performance: StrategyPerformance,
                                       market_conditions: Dict) -> List[Dict]:
        """AI 기반 매개변수 최적화"""
        try:
            # Gemini AI를 통한 매개변수 최적화 추천
            optimization_prompt = f"""
            다음 {strategy_name} 전략의 매개변수를 최적화해주세요:
            
            현재 성과:
            - 총 수익률: {current_performance.total_return:.2%}
            - 샤프 비율: {current_performance.sharpe_ratio:.2f}
            - 최대 손실: {current_performance.max_drawdown:.2%}
            - 승률: {current_performance.win_rate:.2%}
            
            최적화 가능한 매개변수: {json.dumps(parameter_space, indent=2)}
            
            시장 조건:
            - 변동성: {market_conditions.get('volatility', 0.2):.2%}
            - 트렌드: {market_conditions.get('trend', 'NEUTRAL')}
            
            다음 형식으로 3개의 최적화 후보를 제안해주세요:
            {{
                "candidates": [
                    {{
                        "params": {{"param1": value1, "param2": value2}},
                        "expected_improvement": 15.5,
                        "confidence": 85,
                        "rationale": "개선 이유"
                    }}
                ]
            }}
            """
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(optimization_prompt)
            
            if ai_result and 'candidates' in ai_result:
                return ai_result['candidates']
            else:
                # AI 결과가 없으면 기본 후보 생성
                return self._generate_default_optimization_candidates(strategy_name, parameter_space)
                
        except Exception as e:
            self.logger.error(f"❌ AI 매개변수 최적화 실패: {e}")
            return self._generate_default_optimization_candidates(strategy_name, parameter_space)
    
    def _generate_default_optimization_candidates(self, strategy_name: str, parameter_space: Dict) -> List[Dict]:
        """기본 최적화 후보 생성"""
        candidates = []
        
        # 현재 매개변수 기준으로 3개 후보 생성
        for i in range(3):
            params = {}
            for param_name, param_range in parameter_space.items():
                if isinstance(param_range, dict) and 'min' in param_range and 'max' in param_range:
                    # 범위의 25%, 50%, 75% 지점에서 값 선택
                    ratio = 0.25 + (i * 0.25)
                    value = param_range['min'] + (param_range['max'] - param_range['min']) * ratio
                    
                    # step이 있으면 적용
                    if 'step' in param_range:
                        value = round(value / param_range['step']) * param_range['step']
                    
                    params[param_name] = value
            
            candidates.append({
                'params': params,
                'expected_improvement': 5 + i * 5,  # 5%, 10%, 15%
                'confidence': 60 + i * 10,  # 60%, 70%, 80%
                'rationale': f"후보 {i+1}: 균형잡힌 매개변수 조정"
            })
        
        return candidates
    
    def _create_default_performance(self, strategy_name: str) -> StrategyPerformance:
        """기본 성과 데이터 생성"""
        return StrategyPerformance(
            strategy_name=strategy_name,
            total_return=0.0,
            annual_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.5,
            avg_win=0.05,
            avg_loss=0.03,
            profit_factor=1.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            volatility=0.15,
            beta=1.0,
            alpha=0.0,
            information_ratio=0.0,
            calmar_ratio=0.0,
            sortino_ratio=0.0
        )
    
    def _create_default_optimization_result(self, strategy_name: str) -> OptimizationResult:
        """기본 최적화 결과 생성"""
        return OptimizationResult(
            strategy_name=strategy_name,
            original_params={},
            optimized_params={},
            performance_improvement=0.0,
            confidence=50.0,
            expected_metrics={},
            optimization_method="DEFAULT",
            validation_results={},
            implementation_date=datetime.now(),
            monitoring_frequency="WEEKLY",
            risk_warnings=["데이터 부족으로 인한 기본 설정"],
            ai_insights=["추가 데이터 수집 필요"]
        )
    
    def _create_default_adaptation(self, strategy_name: str, regime: str) -> MarketAdaptation:
        """기본 적응성 분석 생성"""
        return MarketAdaptation(
            strategy_name=strategy_name,
            market_regime=regime,
            adaptation_score=60.0,
            performance_in_regime=0.0,
            recommended_adjustments={},
            confidence_level=50.0,
            adaptation_priority="MEDIUM",
            monitoring_signals=["데이터 부족"]
        )
    
    def _determine_adaptation_priority(self, adaptation_score: float) -> str:
        """적응 우선순위 결정"""
        if adaptation_score >= 80:
            return "LOW"
        elif adaptation_score >= 60:
            return "MEDIUM"
        else:
            return "HIGH"
    
    # 추가 헬퍼 메서드들 (간단한 구현)
    async def _define_parameter_space(self, strategy_name: str, performance: StrategyPerformance, market_conditions: Dict) -> Dict:
        return self.optimizable_params.get(strategy_name, {})
    
    async def _validate_optimization_candidates(self, strategy_name: str, candidates: List[Dict], historical_trades: List[Dict]) -> List[Dict]:
        # 간단한 검증 - 실제로는 백테스팅 필요
        return candidates
    
    async def _select_best_candidate(self, candidates: List[Dict], current_performance: StrategyPerformance) -> Dict:
        if not candidates:
            return {'params': {}, 'expected_improvement': 0, 'confidence': 50}
        
        # 가장 높은 개선률과 신뢰도를 가진 후보 선택
        best = max(candidates, key=lambda x: x.get('expected_improvement', 0) * x.get('confidence', 50) / 100)
        return best
    
    async def _create_optimization_result(self, strategy_name: str, current_performance: StrategyPerformance, 
                                        best_candidate: Dict, market_conditions: Dict) -> OptimizationResult:
        return OptimizationResult(
            strategy_name=strategy_name,
            original_params={},  # 실제 구현시 현재 매개변수
            optimized_params=best_candidate.get('params', {}),
            performance_improvement=best_candidate.get('expected_improvement', 0),
            confidence=best_candidate.get('confidence', 70),
            expected_metrics={'sharpe_ratio': current_performance.sharpe_ratio * 1.1},
            optimization_method="AI_ASSISTED",
            validation_results={'validation_score': 75},
            implementation_date=datetime.now(),
            monitoring_frequency="WEEKLY",
            risk_warnings=["최적화 결과 지속 모니터링 필요"],
            ai_insights=[best_candidate.get('rationale', '')]
        )
    
    async def _create_no_optimization_result(self, strategy_name: str, performance: StrategyPerformance) -> OptimizationResult:
        return OptimizationResult(
            strategy_name=strategy_name,
            original_params={},
            optimized_params={},
            performance_improvement=0.0,
            confidence=90.0,
            expected_metrics={},
            optimization_method="NO_OPTIMIZATION",
            validation_results={'reason': '최적화 불필요'},
            implementation_date=datetime.now(),
            monitoring_frequency="MONTHLY",
            risk_warnings=[],
            ai_insights=["현재 전략 매개변수가 적절함"]
        )
    
    # 추가 구현 필요한 메서드들 (간단한 구현)
    async def _ai_optimization_potential_assessment(self, strategy_name: str, performance: StrategyPerformance, market_conditions: Dict) -> Dict:
        return {'potential_score': 20, 'reasons': ['AI 기반 추가 평가'], 'confidence': 70}
    
    async def _analyze_regime_performance(self, strategy_name: str, regime: str, history: List[Dict]) -> Dict:
        return {'current_performance': 0.05, 'regime_fit': 'MODERATE'}
    
    async def _calculate_adaptation_score(self, strategy_name: str, regime: str, performance: Dict) -> float:
        return 65.0  # 기본 적응성 점수
    
    async def _ai_adaptation_analysis(self, strategy_name: str, regime: str, performance: Dict) -> Dict:
        return {'confidence': 70, 'monitoring_signals': ['변동성 변화']}
    
    async def _generate_adaptation_adjustments(self, strategy_name: str, regime: str, ai_analysis: Dict) -> Dict:
        return {'position_sizing': 'REDUCE', 'risk_management': 'TIGHTEN'}
    
    async def _analyze_strategy_correlations(self, strategies: List[str], performance: Dict) -> Dict:
        return {'average_correlation': 0.3, 'high_correlation_pairs': []}
    
    async def _optimize_strategy_allocation(self, individual_opts: Dict, correlation: Dict, market: Dict) -> Dict:
        return {'recommended_weights': {k: 1/len(individual_opts) for k in individual_opts}}
    
    async def _create_integrated_optimization(self, individual: Dict, portfolio: Dict) -> Dict:
        return individual  # 개별 최적화 결과 반환
    
    async def _evaluate_strategy_for_regime(self, strategy: str, regime: str, history: Dict) -> Dict:
        return {'regime_score': 70, 'expected_performance': 0.05}
    
    async def _ai_strategy_ranking(self, strategies: List[str], regime: str, performance: Dict, portfolio: Dict) -> Dict:
        return {'rankings': {s: 70 for s in strategies}}
    
    async def _apply_diversification_logic(self, rankings: Dict, portfolio: Dict) -> Dict:
        return rankings
    
    async def _finalize_strategy_selection(self, adjusted_rankings: Dict, regime: str) -> Dict:
        return {
            'strategies': list(adjusted_rankings.get('rankings', {}).keys())[:3],
            'weights': {k: 0.33 for k in list(adjusted_rankings.get('rankings', {}).keys())[:3]},
            'confidence': 75,
            'rationale': ['균형잡힌 전략 포트폴리오'],
            'monitoring_frequency': 'DAILY',
            'rebalancing_triggers': ['체제 변화', '성과 하락'],
            'risk_warnings': []
        }
    
    async def _evaluate_strategy_health(self, strategy: str, data: Dict, metrics: Dict) -> float:
        return 75.0  # 기본 건전성 점수
    
    async def _detect_optimization_need(self, strategy: str, health_score: float, market_changes: Dict) -> Dict:
        return {
            'required': health_score < 60,
            'urgency': 'MEDIUM' if health_score < 60 else 'LOW',
            'reason': '성과 하락' if health_score < 60 else '정상',
            'action': '매개변수 재검토' if health_score < 60 else '모니터링 지속'
        }
    
    async def _analyze_market_response_adequacy(self, strategies: Dict, market_changes: Dict) -> Dict:
        return {'adequacy_score': 70}
    
    async def _generate_ai_monitoring_report(self, health_scores: Dict, alerts: List, market_response: Dict) -> Dict:
        return {
            'priority_actions': ['정기 모니터링 지속'],
            'stability_assessment': 'STABLE'
        }
    
    # 새로운 고급 최적화 알고리즘 헬퍼 메서드들
    
    async def _engineer_features(self, performance_data: List[Dict], market_data: List[Dict]) -> Dict:
        """특성 엔지니어링"""
        try:
            features = {
                'price_features': [],
                'volume_features': [],
                'technical_features': [],
                'market_regime_features': []
            }
            
            # 가격 특성
            if market_data:
                prices = [d.get('price', 0) for d in market_data[-20:]]
                if prices:
                    features['price_features'] = {
                        'price_momentum': np.mean(np.diff(prices)) if len(prices) > 1 else 0,
                        'price_volatility': np.std(prices),
                        'price_trend': (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0
                    }
            
            # 거래량 특성
            if market_data:
                volumes = [d.get('volume', 0) for d in market_data[-20:]]
                if volumes:
                    features['volume_features'] = {
                        'avg_volume': np.mean(volumes),
                        'volume_volatility': np.std(volumes),
                        'volume_trend': (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] != 0 else 0
                    }
            
            return features
            
        except Exception as e:
            self.logger.error(f"❌ 특성 엔지니어링 실패: {e}")
            return {}
    
    async def _prepare_training_data(self, features: Dict, performance_data: List[Dict]) -> Dict:
        """훈련 데이터 준비"""
        try:
            return {
                'X': features,
                'y': [d.get('return', 0) for d in performance_data[-50:]],  # 최근 50개 수익률
                'weights': [1.0] * min(50, len(performance_data))  # 균등 가중치
            }
        except:
            return {'X': {}, 'y': [], 'weights': []}
    
    async def _ai_parameter_pattern_analysis(self, strategy_name: str, training_data: Dict) -> Dict:
        """AI 파라미터 패턴 분석"""
        try:
            # Gemini AI를 통한 패턴 분석
            pattern_prompt = f"""
            {strategy_name} 전략의 성과 데이터를 분석하여 최적 파라미터 패턴을 찾아주세요.
            
            특성 데이터: {json.dumps(training_data.get('X', {}), indent=2)}
            수익률 데이터 요약: 평균 {np.mean(training_data.get('y', [0])):.3f}, 
                          변동성 {np.std(training_data.get('y', [0])):.3f}
            
            다음 형식으로 분석 결과를 제공해주세요:
            {{
                "optimal_conditions": {{"condition1": "value1", "condition2": "value2"}},
                "feature_importance": {{"feature1": 0.85, "feature2": 0.65}},
                "recommended_params": {{"param1": "value1", "param2": "value2"}},
                "confidence": 80
            }}
            """
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(pattern_prompt)
            
            if ai_result:
                return ai_result
            else:
                return self._default_pattern_analysis()
                
        except Exception as e:
            self.logger.error(f"❌ AI 패턴 분석 실패: {e}")
            return self._default_pattern_analysis()
    
    def _default_pattern_analysis(self) -> Dict:
        """기본 패턴 분석 결과"""
        return {
            'optimal_conditions': {'volatility': 'medium', 'trend': 'positive'},
            'feature_importance': {'price_momentum': 0.7, 'volume_trend': 0.5},
            'recommended_params': {'lookback': 20, 'threshold': 0.02},
            'confidence': 60
        }
    
    async def _reinforcement_learning_optimization(self, strategy_name: str, 
                                                 pattern_analysis: Dict, 
                                                 training_data: Dict) -> Dict:
        """강화학습 기반 최적화 (간소화된 구현)"""
        try:
            # 간단한 Q-learning 스타일 접근법
            state_space = self._discretize_state_space(training_data.get('X', {}))
            action_space = self._define_action_space(strategy_name)
            
            # 학습 시뮬레이션 (실제로는 더 복잡한 RL 알고리즘 필요)
            best_actions = {}
            for state in state_space:
                rewards = []
                for action in action_space:
                    # 간단한 보상 함수
                    reward = self._calculate_reward(state, action, pattern_analysis)
                    rewards.append((action, reward))
                
                best_action = max(rewards, key=lambda x: x[1])[0]
                best_actions[state] = best_action
            
            return {
                'best_policy': best_actions,
                'convergence_score': 0.8,
                'exploration_rate': 0.1,
                'confidence': 0.75
            }
            
        except Exception as e:
            self.logger.error(f"❌ 강화학습 최적화 실패: {e}")
            return {'best_policy': {}, 'confidence': 0.5}
    
    def _discretize_state_space(self, features: Dict) -> List[str]:
        """상태 공간 이산화"""
        states = ['low_volatility', 'medium_volatility', 'high_volatility']
        return states
    
    def _define_action_space(self, strategy_name: str) -> List[Dict]:
        """액션 공간 정의"""
        if strategy_name in self.optimizable_params:
            base_params = self.optimizable_params[strategy_name]
            actions = []
            
            # 각 파라미터의 min, mid, max 값으로 액션 생성
            for param_name, param_range in base_params.items():
                if isinstance(param_range, dict) and 'min' in param_range:
                    min_val = param_range['min']
                    max_val = param_range['max']
                    mid_val = (min_val + max_val) / 2
                    
                    actions.extend([
                        {param_name: min_val},
                        {param_name: mid_val},
                        {param_name: max_val}
                    ])
            
            return actions[:10]  # 최대 10개 액션으로 제한
        
        return [{'default': 1.0}]
    
    def _calculate_reward(self, state: str, action: Dict, pattern_analysis: Dict) -> float:
        """보상 함수"""
        base_reward = 0.5
        
        # 패턴 분석 결과와 액션의 일치도에 따라 보상 조정
        feature_importance = pattern_analysis.get('feature_importance', {})
        
        for param, value in action.items():
            if param in feature_importance:
                importance = feature_importance[param]
                base_reward += importance * 0.3
        
        # 상태에 따른 보상 조정
        if state == 'medium_volatility':
            base_reward += 0.1  # 안정적인 상태 선호
        elif state == 'high_volatility':
            base_reward -= 0.1  # 높은 변동성 패널티
        
        return base_reward
    
    async def _ensemble_optimization_results(self, optimization_results: List[Dict]) -> Dict:
        """앙상블 최적화 결과"""
        try:
            ensemble_params = {}
            total_confidence = 0
            
            for result in optimization_results:
                confidence = result.get('confidence', 0.5)
                total_confidence += confidence
                
                # 패턴 분석 결과에서 추천 파라미터 추출
                if 'recommended_params' in result:
                    for param, value in result['recommended_params'].items():
                        if param not in ensemble_params:
                            ensemble_params[param] = []
                        ensemble_params[param].append((value, confidence))
                
                # 강화학습 결과에서 최적 정책 추출
                if 'best_policy' in result:
                    policy = result['best_policy']
                    # 정책을 파라미터로 변환 (간소화)
                    if policy and 'medium_volatility' in policy:
                        action = policy['medium_volatility']
                        for param, value in action.items():
                            if param not in ensemble_params:
                                ensemble_params[param] = []
                            ensemble_params[param].append((value, confidence))
            
            # 가중 평균으로 최종 파라미터 결정
            final_params = {}
            for param, values in ensemble_params.items():
                if values:
                    weighted_sum = sum(v * w for v, w in values)
                    weight_sum = sum(w for v, w in values)
                    final_params[param] = weighted_sum / weight_sum if weight_sum > 0 else values[0][0]
            
            return {
                'parameters': final_params,
                'ensemble_confidence': total_confidence / len(optimization_results) if optimization_results else 0.5,
                'method_count': len(optimization_results)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 앙상블 결과 생성 실패: {e}")
            return {'parameters': {}, 'ensemble_confidence': 0.5}
    
    async def _validate_ml_optimization(self, strategy_name: str, 
                                      optimized_params: Dict, 
                                      historical_data: List[Dict]) -> Dict:
        """머신러닝 최적화 검증"""
        try:
            if not historical_data:
                return {'confidence': 0.5, 'improvement': 0.0, 'risk_metrics': {}}
            
            # 간단한 백테스팅 시뮬레이션
            baseline_performance = np.mean([d.get('return', 0) for d in historical_data[-30:]])
            
            # 최적화된 파라미터로 예상 성과 계산 (간소화)
            optimization_factor = optimized_params.get('ensemble_confidence', 0.7)
            expected_improvement = baseline_performance * optimization_factor * 0.2  # 20% 최대 개선
            
            risk_metrics = {
                'expected_volatility': np.std([d.get('return', 0) for d in historical_data[-30:]]) * 0.9,
                'max_drawdown_estimate': 0.1,
                'var_95': np.percentile([d.get('return', 0) for d in historical_data[-30:]], 5) if historical_data else -0.05
            }
            
            return {
                'confidence': optimization_factor,
                'improvement': expected_improvement,
                'risk_metrics': risk_metrics,
                'validation_score': 0.8
            }
            
        except Exception as e:
            self.logger.error(f"❌ ML 최적화 검증 실패: {e}")
            return {'confidence': 0.5, 'improvement': 0.0, 'risk_metrics': {}}
    
    def _determine_ml_priority(self, validation_results: Dict) -> str:
        """ML 최적화 우선순위 결정"""
        improvement = validation_results.get('improvement', 0)
        confidence = validation_results.get('confidence', 0)
        
        score = improvement * 100 + confidence * 50
        
        if score > 7:
            return 'HIGH'
        elif score > 3:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_ml_monitoring_plan(self) -> List[str]:
        """ML 모니터링 계획 생성"""
        return [
            '일일 성과 추적',
            '파라미터 drift 모니터링', 
            '모델 재훈련 주기 확인',
            '특성 중요도 변화 감지'
        ]
    
    # 유전 알고리즘 헬퍼 메서드들
    
    async def _initialize_ga_population(self, parameter_bounds: Dict, population_size: int) -> List[Dict]:
        """GA 초기 모집단 생성"""
        population = []
        
        for _ in range(population_size):
            individual = {}
            for param_name, bounds in parameter_bounds.items():
                if isinstance(bounds, tuple) and len(bounds) == 2:
                    min_val, max_val = bounds
                    # 균등 분포에서 랜덤 샘플링
                    individual[param_name] = np.random.uniform(min_val, max_val)
                else:
                    individual[param_name] = 1.0  # 기본값
            
            population.append(individual)
        
        return population
    
    async def _ga_evolution_step(self, population: List[Dict], 
                               fitness_scores: List[float], 
                               parameter_bounds: Dict) -> List[Dict]:
        """GA 진화 단계"""
        try:
            new_population = []
            population_size = len(population)
            
            # 엘리트 선택 (상위 10%)
            elite_count = max(1, population_size // 10)
            elite_indices = np.argsort(fitness_scores)[-elite_count:]
            
            for idx in elite_indices:
                new_population.append(population[idx].copy())
            
            # 나머지 개체 생성 (토너먼트 선택 + 교차 + 돌연변이)
            while len(new_population) < population_size:
                # 부모 선택
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                # 교차
                child = self._crossover(parent1, parent2)
                
                # 돌연변이
                child = self._mutate(child, parameter_bounds)
                
                new_population.append(child)
            
            return new_population[:population_size]
            
        except Exception as e:
            self.logger.error(f"❌ GA 진화 단계 실패: {e}")
            return population
    
    def _tournament_selection(self, population: List[Dict], fitness_scores: List[float], 
                            tournament_size: int = 3) -> Dict:
        """토너먼트 선택"""
        tournament_indices = np.random.choice(len(population), tournament_size, replace=False)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx].copy()
    
    def _crossover(self, parent1: Dict, parent2: Dict, crossover_rate: float = 0.8) -> Dict:
        """교차 연산"""
        child = {}
        
        for param in parent1.keys():
            if np.random.random() < crossover_rate:
                # 균등 교차
                alpha = np.random.random()
                child[param] = alpha * parent1[param] + (1 - alpha) * parent2[param]
            else:
                # 부모 1에서 그대로 복사
                child[param] = parent1[param]
        
        return child
    
    def _mutate(self, individual: Dict, parameter_bounds: Dict, 
              mutation_rate: float = 0.1, mutation_strength: float = 0.1) -> Dict:
        """돌연변이 연산"""
        mutated = individual.copy()
        
        for param, value in mutated.items():
            if np.random.random() < mutation_rate:
                if param in parameter_bounds:
                    bounds = parameter_bounds[param]
                    if isinstance(bounds, tuple) and len(bounds) == 2:
                        min_val, max_val = bounds
                        # 가우시안 돌연변이
                        noise = np.random.normal(0, (max_val - min_val) * mutation_strength)
                        mutated[param] = np.clip(value + noise, min_val, max_val)
        
        return mutated
    
    async def _analyze_ga_results(self, best_individual: Dict, 
                                best_fitness: float, 
                                fitness_history: List[float]) -> Dict:
        """GA 결과 분석"""
        try:
            # 수렴 분석
            convergence_rate = self._calculate_convergence_rate(fitness_history)
            
            # 다양성 분석 (간소화)
            diversity_score = len(set(fitness_history[-10:])) / 10.0 if len(fitness_history) >= 10 else 1.0
            
            return {
                'convergence_rate': convergence_rate,
                'final_fitness': best_fitness,
                'diversity_score': diversity_score,
                'stability': 'HIGH' if convergence_rate < 0.01 else 'MEDIUM',
                'confidence': 0.8 if best_fitness > 0 else 0.6
            }
            
        except:
            return {'convergence_rate': 0.01, 'confidence': 0.6}
    
    def _calculate_convergence_rate(self, fitness_history: List[float]) -> float:
        """수렴률 계산"""
        if len(fitness_history) < 10:
            return 1.0
        
        recent_change = abs(fitness_history[-1] - fitness_history[-10]) / 10
        return recent_change
    
    async def _analyze_parameter_sensitivity(self, best_params: Dict, 
                                           parameter_bounds: Dict, 
                                           fitness_function: callable) -> Dict:
        """파라미터 민감도 분석"""
        try:
            sensitivity = {}
            baseline_fitness = await fitness_function(best_params)
            
            for param, value in best_params.items():
                if param in parameter_bounds:
                    bounds = parameter_bounds[param]
                    if isinstance(bounds, tuple):
                        min_val, max_val = bounds
                        
                        # 파라미터를 +/- 10% 변경하여 민감도 측정
                        delta = (max_val - min_val) * 0.1
                        
                        test_params_up = best_params.copy()
                        test_params_up[param] = min(max_val, value + delta)
                        
                        test_params_down = best_params.copy() 
                        test_params_down[param] = max(min_val, value - delta)
                        
                        try:
                            fitness_up = await fitness_function(test_params_up)
                            fitness_down = await fitness_function(test_params_down)
                            
                            sensitivity[param] = {
                                'sensitivity': abs(fitness_up - fitness_down) / (2 * delta),
                                'direction': 'positive' if fitness_up > fitness_down else 'negative'
                            }
                        except:
                            sensitivity[param] = {'sensitivity': 0.0, 'direction': 'neutral'}
            
            return sensitivity
            
        except Exception as e:
            self.logger.error(f"❌ 파라미터 민감도 분석 실패: {e}")
            return {}
    
    # 베이지안 최적화 헬퍼 메서드들
    
    async def _generate_initial_points(self, parameter_space: Dict, n_points: int) -> List[Dict]:
        """초기 관찰점 생성"""
        points = []
        
        for _ in range(n_points):
            point = {}
            for param_name, param_info in parameter_space.items():
                if isinstance(param_info, dict) and 'min' in param_info and 'max' in param_info:
                    min_val = param_info['min']
                    max_val = param_info['max']
                    point[param_name] = np.random.uniform(min_val, max_val)
                else:
                    point[param_name] = 1.0  # 기본값
            
            points.append(point)
        
        return points
    
    async def _ai_acquisition_function(self, observations: List[Dict], 
                                     parameter_space: Dict, 
                                     strategy_name: str) -> Dict:
        """AI 기반 획득 함수"""
        try:
            # Gemini AI를 통한 다음 탐색점 추천
            acquisition_prompt = f"""
            베이지안 최적화를 위한 다음 탐색점을 추천해주세요.
            
            전략: {strategy_name}
            파라미터 공간: {json.dumps(parameter_space, indent=2)}
            
            기존 관찰 결과 요약:
            - 총 관찰: {len(observations)}개
            - 최고 목적값: {max(obs['objective'] for obs in observations):.4f}
            - 평균 목적값: {np.mean([obs['objective'] for obs in observations]):.4f}
            
            Exploitation과 Exploration의 균형을 고려하여 다음 탐색할 파라미터를 제안해주세요:
            {{
                "parameter_name1": value1,
                "parameter_name2": value2,
                "reasoning": "선택 이유"
            }}
            """
            
            ai_result = await self.gemini_analyzer.analyze_with_custom_prompt(acquisition_prompt)
            
            if ai_result and isinstance(ai_result, dict):
                # reasoning 키 제거
                next_point = {k: v for k, v in ai_result.items() if k != 'reasoning'}
                
                # 파라미터 범위 검증 및 조정
                for param_name, value in next_point.items():
                    if param_name in parameter_space:
                        param_info = parameter_space[param_name]
                        if isinstance(param_info, dict) and 'min' in param_info and 'max' in param_info:
                            next_point[param_name] = np.clip(value, param_info['min'], param_info['max'])
                
                return next_point
            
            # AI 실패시 UCB(Upper Confidence Bound) 방식으로 폴백
            return self._ucb_acquisition(observations, parameter_space)
            
        except Exception as e:
            self.logger.error(f"❌ AI 획득 함수 실패: {e}")
            return self._ucb_acquisition(observations, parameter_space)
    
    def _ucb_acquisition(self, observations: List[Dict], parameter_space: Dict) -> Dict:
        """UCB 획득 함수 (폴백)"""
        # 간단한 랜덤 샘플링으로 대체
        next_point = {}
        for param_name, param_info in parameter_space.items():
            if isinstance(param_info, dict) and 'min' in param_info and 'max' in param_info:
                next_point[param_name] = np.random.uniform(param_info['min'], param_info['max'])
            else:
                next_point[param_name] = 1.0
        
        return next_point
    
    async def _analyze_bayesian_results(self, observations: List[Dict], 
                                      best_observation: Dict, 
                                      parameter_space: Dict) -> Dict:
        """베이지안 최적화 결과 분석"""
        try:
            objectives = [obs['objective'] for obs in observations]
            
            return {
                'convergence_score': self._calculate_bayesian_convergence(objectives),
                'exploration_efficiency': len(set(objectives)) / len(objectives),
                'improvement_rate': (best_observation['objective'] - objectives[0]) / len(observations) if objectives else 0,
                'uncertainty': {
                    'objective_std': np.std(objectives),
                    'parameter_variance': self._calculate_parameter_variance(observations)
                },
                'confidence': 0.8 if best_observation['objective'] > np.mean(objectives) else 0.6
            }
            
        except:
            return {'confidence': 0.6, 'convergence_score': 0.5}
    
    def _calculate_bayesian_convergence(self, objectives: List[float]) -> float:
        """베이지안 최적화 수렴도 계산"""
        if len(objectives) < 5:
            return 0.5
        
        recent_improvement = max(objectives[-5:]) - max(objectives[:-5])
        return max(0, min(1, 1 - recent_improvement / abs(max(objectives))))
    
    def _calculate_parameter_variance(self, observations: List[Dict]) -> Dict:
        """파라미터 분산 계산"""
        if not observations:
            return {}
        
        param_variance = {}
        param_names = observations[0]['parameters'].keys()
        
        for param in param_names:
            values = [obs['parameters'][param] for obs in observations]
            param_variance[param] = np.var(values)
        
        return param_variance
    
    async def _calculate_parameter_importance(self, observations: List[Dict]) -> Dict:
        """파라미터 중요도 계산"""
        try:
            if len(observations) < 5:
                return {}
            
            importance = {}
            param_names = observations[0]['parameters'].keys()
            objectives = [obs['objective'] for obs in observations]
            
            for param in param_names:
                param_values = [obs['parameters'][param] for obs in observations]
                
                # 상관관계 기반 중요도 (간소화)
                correlation = np.corrcoef(param_values, objectives)[0, 1] if len(param_values) > 1 else 0
                importance[param] = abs(correlation) if not np.isnan(correlation) else 0.0
            
            return importance
            
        except:
            return {}