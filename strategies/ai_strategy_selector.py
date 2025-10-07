#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/ai_strategy_selector.py

AI 기반 동적 전략 선택기 - 시장 체제별 최적 전략 자동 선택
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from utils.logger import get_logger
from analyzers.market_regime_detector import MarketRegimeDetector, MarketRegime


@dataclass
class StrategyPerformance:
    """전략 성과 데이터"""
    strategy_name: str
    regime_type: str
    win_rate: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    last_update: datetime
    confidence_score: float


class AIStrategySelector:
    """AI 기반 전략 선택기"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("AIStrategySelector")
        
        # AI 분석기들
        self.market_regime_detector = MarketRegimeDetector(config)
        
        # 사용 가능한 전략들
        self.available_strategies = {
            'momentum': {
                'class_name': 'MomentumStrategy',
                'optimal_regimes': ['BULL_TREND', 'HIGH_VOLATILITY'],
                'risk_tolerance': 'medium',
                'best_market_conditions': ['trending', 'volatile'],
                'performance_weight': 0.25
            },
            'breakout': {
                'class_name': 'BreakoutStrategy', 
                'optimal_regimes': ['BULL_TREND', 'BEAR_TREND', 'HIGH_VOLATILITY'],
                'risk_tolerance': 'high',
                'best_market_conditions': ['trending', 'breakout'],
                'performance_weight': 0.20
            },
            'scalping_3m': {
                'class_name': 'Scalping3mStrategy',
                'optimal_regimes': ['HIGH_VOLATILITY', 'SIDEWAYS'],
                'risk_tolerance': 'high',
                'best_market_conditions': ['volatile', 'liquid'],
                'performance_weight': 0.15
            },
            'rsi': {
                'class_name': 'RSIStrategy',
                'optimal_regimes': ['SIDEWAYS', 'BEAR_TREND'],
                'risk_tolerance': 'low',
                'best_market_conditions': ['oversold', 'mean_reversion'],
                'performance_weight': 0.15
            },
            'supertrend_ema_rsi': {
                'class_name': 'SupertrendEmaRsiStrategy',
                'optimal_regimes': ['BEAR_TREND', 'SIDEWAYS'],
                'risk_tolerance': 'medium',
                'best_market_conditions': ['trending', 'defensive'],
                'performance_weight': 0.10
            },
            'eod': {
                'class_name': 'EODStrategy',
                'optimal_regimes': ['LOW_VOLATILITY', 'SIDEWAYS'],
                'risk_tolerance': 'low',
                'best_market_conditions': ['stable', 'end_of_day'],
                'performance_weight': 0.10
            },
            'vwap': {
                'class_name': 'VWAPStrategy',
                'optimal_regimes': ['SIDEWAYS', 'LOW_VOLATILITY'],
                'risk_tolerance': 'low',
                'best_market_conditions': ['institutional', 'volume_weighted'],
                'performance_weight': 0.05
            }
        }
        
        # 전략 성과 기록 (메모리 기반 - 추후 DB 연동 가능)
        self.strategy_performance_history = {}
        
        # 현재 선택된 전략
        self.current_strategy = None
        self.current_regime = None
        self.last_selection_time = None
        
        self.logger.info("🧠 AI 전략 선택기 초기화 완료")
    
    async def select_optimal_strategy(self, market_data: List[Dict], 
                                    portfolio_context: Dict = None) -> Dict[str, Any]:
        """최적 전략 선택"""
        try:
            self.logger.info("🎯 AI 기반 최적 전략 선택 시작")
            
            # 1. 현재 시장 체제 감지
            current_regime = await self.market_regime_detector.detect_current_regime(market_data)
            self.current_regime = current_regime
            
            # 2. 전략별 적합도 스코어링
            strategy_scores = await self._score_strategies_for_regime(current_regime, market_data)
            
            # 3. AI 기반 시장 상황 분석
            ai_market_analysis = await self._get_ai_market_insights(current_regime, market_data)
            
            # 4. 포트폴리오 컨텍스트 반영
            context_adjusted_scores = await self._adjust_scores_for_context(
                strategy_scores, portfolio_context, ai_market_analysis
            )
            
            # 5. 최종 전략 선택
            selected_strategy = await self._make_final_selection(
                context_adjusted_scores, current_regime, ai_market_analysis
            )
            
            # 6. 선택 결과 기록
            self.current_strategy = selected_strategy['name']
            self.last_selection_time = datetime.now()
            
            self.logger.info(f"✅ 전략 선택 완료: {selected_strategy['name']} (점수: {selected_strategy['score']:.1f})")
            
            return {
                'selected_strategy': selected_strategy,
                'regime_analysis': {
                    'regime_type': current_regime.regime_type,
                    'sub_regime': current_regime.sub_regime,
                    'confidence': current_regime.confidence
                },
                'ai_insights': ai_market_analysis,
                'strategy_scores': context_adjusted_scores,
                'selection_reasons': selected_strategy.get('reasons', []),
                'risk_assessment': await self._assess_selection_risk(selected_strategy, current_regime),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 전략 선택 실패: {e}")
            return self._get_fallback_strategy()
    
    async def _score_strategies_for_regime(self, regime: MarketRegime, 
                                         market_data: List[Dict]) -> Dict[str, float]:
        """체제별 전략 스코어링"""
        try:
            strategy_scores = {}
            
            for strategy_name, strategy_info in self.available_strategies.items():
                score = 50.0  # 기본 점수
                
                # 1. 체제 적합도 (40점 만점)
                regime_fitness = self._calculate_regime_fitness(
                    strategy_info, regime.regime_type, regime.sub_regime
                )
                score += regime_fitness * 0.4
                
                # 2. 과거 성과 (30점 만점)
                historical_performance = self._get_historical_performance_score(
                    strategy_name, regime.regime_type
                )
                score += historical_performance * 0.3
                
                # 3. 시장 조건 적합도 (20점 만점)
                market_condition_fit = await self._calculate_market_condition_fitness(
                    strategy_info, market_data
                )
                score += market_condition_fit * 0.2
                
                # 4. 변동성 적합도 (10점 만점)
                volatility_fit = self._calculate_volatility_fitness(
                    strategy_info, regime.market_characteristics.get('volatility', 'MEDIUM')
                )
                score += volatility_fit * 0.1
                
                strategy_scores[strategy_name] = max(0, min(100, score))
            
            return strategy_scores
            
        except Exception as e:
            self.logger.error(f"❌ 전략 스코어링 실패: {e}")
            return {name: 50.0 for name in self.available_strategies.keys()}
    
    def _calculate_regime_fitness(self, strategy_info: Dict, regime_type: str, sub_regime: str) -> float:
        """체제 적합도 계산"""
        try:
            optimal_regimes = strategy_info.get('optimal_regimes', [])
            
            if regime_type in optimal_regimes:
                base_score = 30  # 최적 체제
                
                # 서브 체제에 따른 추가 점수
                if sub_regime == 'STRONG':
                    return base_score + 10  # 강한 체제에서 더 높은 점수
                elif sub_regime == 'MODERATE':
                    return base_score + 5
                else:  # WEAK
                    return base_score
            else:
                # 비최적 체제에서의 적합도
                compatibility_matrix = {
                    'BULL_TREND': {'SIDEWAYS': 10, 'BEAR_TREND': 0, 'HIGH_VOLATILITY': 15, 'LOW_VOLATILITY': 5},
                    'BEAR_TREND': {'SIDEWAYS': 10, 'BULL_TREND': 0, 'HIGH_VOLATILITY': 5, 'LOW_VOLATILITY': 15},
                    'SIDEWAYS': {'BULL_TREND': 15, 'BEAR_TREND': 15, 'HIGH_VOLATILITY': 10, 'LOW_VOLATILITY': 20},
                    'HIGH_VOLATILITY': {'BULL_TREND': 20, 'BEAR_TREND': 10, 'SIDEWAYS': 5, 'LOW_VOLATILITY': 0},
                    'LOW_VOLATILITY': {'BULL_TREND': 5, 'BEAR_TREND': 15, 'SIDEWAYS': 20, 'HIGH_VOLATILITY': 0}
                }
                
                return compatibility_matrix.get(regime_type, {}).get(regime_type, 0)
                
        except Exception:
            return 20.0  # 기본값
    
    def _get_historical_performance_score(self, strategy_name: str, regime_type: str) -> float:
        """과거 성과 점수"""
        try:
            performance_key = f"{strategy_name}_{regime_type}"
            performance = self.strategy_performance_history.get(performance_key)
            
            if not performance:
                # 성과 데이터가 없으면 전략의 기본 가중치 사용
                return self.available_strategies[strategy_name]['performance_weight'] * 100
            
            # 성과 기반 점수 계산
            score = 0
            
            # 승률 (40%)
            score += performance.win_rate * 0.4 * 40
            
            # 평균 수익률 (35%)
            if performance.avg_return > 0:
                score += min(performance.avg_return * 100, 20) * 0.35 * 40 / 20
            
            # 샤프 비율 (25%)
            if performance.sharpe_ratio > 0:
                score += min(performance.sharpe_ratio, 3) * 0.25 * 40 / 3
            
            return max(0, min(40, score))
            
        except Exception:
            return 20.0  # 기본값
    
    async def _calculate_market_condition_fitness(self, strategy_info: Dict, market_data: List[Dict]) -> float:
        """시장 조건 적합도 계산"""
        try:
            if not market_data:
                return 10.0  # 기본값
            
            best_conditions = strategy_info.get('best_market_conditions', [])
            score = 0
            
            # 최근 시장 데이터 분석
            recent_data = market_data[-5:] if len(market_data) >= 5 else market_data
            
            # 변동성 계산
            price_changes = [item.get('change_rate', 0) for item in recent_data]
            volatility = np.std(price_changes) if price_changes else 0.02
            
            # 거래량 분석
            volumes = [item.get('volume', 0) for item in recent_data]
            avg_volume = np.mean(volumes) if volumes else 1000000
            volume_trend = 'high' if volumes[-1] > avg_volume * 1.5 else 'normal'
            
            # 조건별 점수 부여
            for condition in best_conditions:
                if condition == 'volatile' and volatility > 0.03:
                    score += 5
                elif condition == 'stable' and volatility < 0.015:
                    score += 5
                elif condition == 'liquid' and volume_trend == 'high':
                    score += 5
                elif condition == 'trending':
                    # 추세 강도 계산 (간단 버전)
                    trend_strength = abs(sum(price_changes) / len(price_changes))
                    if trend_strength > 0.02:
                        score += 5
                elif condition == 'mean_reversion':
                    # 평균 회귀 조건 (RSI 과매수/과매도 영역)
                    recent_change = price_changes[-1] if price_changes else 0
                    if abs(recent_change) > 0.03:  # 3% 이상 움직임
                        score += 5
            
            return min(20, score)
            
        except Exception:
            return 10.0  # 기본값
    
    def _calculate_volatility_fitness(self, strategy_info: Dict, volatility_level: str) -> float:
        """변동성 적합도 계산"""
        try:
            risk_tolerance = strategy_info.get('risk_tolerance', 'medium')
            
            fitness_matrix = {
                'high': {'VERY_HIGH': 10, 'HIGH': 8, 'MEDIUM': 5, 'LOW': 2, 'VERY_LOW': 0},
                'medium': {'VERY_HIGH': 5, 'HIGH': 8, 'MEDIUM': 10, 'LOW': 8, 'VERY_LOW': 5},
                'low': {'VERY_HIGH': 0, 'HIGH': 2, 'MEDIUM': 5, 'LOW': 8, 'VERY_LOW': 10}
            }
            
            return fitness_matrix.get(risk_tolerance, {}).get(volatility_level, 5)
            
        except Exception:
            return 5.0  # 기본값
    
    async def _get_ai_market_insights(self, regime: MarketRegime, market_data: List[Dict]) -> Dict:
        """AI 기반 시장 인사이트"""
        try:
            # Gemini를 통한 시장 분석
            market_analysis_prompt = f"""
현재 시장 상황을 분석하여 최적 매매 전략을 추천해주세요:

시장 체제: {regime.regime_type} ({regime.sub_regime})
체제 신뢰도: {regime.confidence:.1f}%
주요 지표: {', '.join(regime.key_indicators)}
리스크 요소: {', '.join(regime.risk_factors)}

다음 JSON 형식으로 답변해주세요:
{{
    "market_sentiment": "bullish/bearish/neutral",
    "recommended_approach": "aggressive/moderate/conservative",
    "key_opportunities": ["기회1", "기회2", "기회3"],
    "major_risks": ["리스크1", "리스크2"],
    "strategy_preferences": {{
        "momentum": 0.0~1.0,
        "breakout": 0.0~1.0,
        "mean_reversion": 0.0~1.0,
        "defensive": 0.0~1.0
    }},
    "confidence": 0.0~1.0
}}
"""
            
            # LLM 제거됨 - 기본값 사용
            return self._get_default_market_insights()
                
        except Exception as e:
            self.logger.warning(f"⚠️ AI 시장 인사이트 획득 실패: {e}")
            return self._get_default_market_insights()
    
    def _get_default_market_insights(self) -> Dict:
        """기본 시장 인사이트"""
        return {
            'market_sentiment': 'neutral',
            'recommended_approach': 'moderate',
            'key_opportunities': ['기술적 분석 신호'],
            'major_risks': ['시장 불확실성'],
            'strategy_preferences': {
                'momentum': 0.6,
                'breakout': 0.4,
                'mean_reversion': 0.5,
                'defensive': 0.7
            },
            'confidence': 0.5
        }
    
    async def _adjust_scores_for_context(self, strategy_scores: Dict[str, float], 
                                       portfolio_context: Dict, ai_insights: Dict) -> Dict[str, float]:
        """포트폴리오 컨텍스트 및 AI 인사이트 반영"""
        try:
            adjusted_scores = strategy_scores.copy()
            
            # AI 인사이트 반영
            if ai_insights.get('confidence', 0) > 0.6:
                strategy_preferences = ai_insights.get('strategy_preferences', {})
                
                # AI 선호도에 따른 점수 조정
                for strategy_name in adjusted_scores:
                    if 'momentum' in strategy_name and strategy_preferences.get('momentum', 0.5) > 0.7:
                        adjusted_scores[strategy_name] += 10
                    elif 'breakout' in strategy_name and strategy_preferences.get('breakout', 0.5) > 0.7:
                        adjusted_scores[strategy_name] += 10
                    elif 'rsi' in strategy_name and strategy_preferences.get('mean_reversion', 0.5) > 0.7:
                        adjusted_scores[strategy_name] += 10
                    elif strategy_preferences.get('defensive', 0.5) > 0.7:
                        # 보수적 전략들 우대
                        if strategy_name in ['eod', 'vwap', 'rsi']:
                            adjusted_scores[strategy_name] += 8
            
            # 포트폴리오 컨텍스트 반영
            if portfolio_context:
                current_exposure = portfolio_context.get('risk_exposure', 'medium')
                recent_performance = portfolio_context.get('recent_performance', 0)
                
                # 최근 성과가 좋지 않으면 보수적 전략 선호
                if recent_performance < -0.05:  # -5% 이하
                    for strategy_name in ['eod', 'vwap', 'rsi']:
                        adjusted_scores[strategy_name] += 15
                    for strategy_name in ['scalping_3m', 'breakout']:
                        adjusted_scores[strategy_name] -= 10
                
                # 리스크 노출도에 따른 조정
                if current_exposure == 'high':
                    # 고위험 전략 점수 하향
                    for strategy_name, strategy_info in self.available_strategies.items():
                        if strategy_info.get('risk_tolerance') == 'high':
                            adjusted_scores[strategy_name] -= 5
            
            # 점수 범위 제한
            for strategy_name in adjusted_scores:
                adjusted_scores[strategy_name] = max(0, min(100, adjusted_scores[strategy_name]))
            
            return adjusted_scores
            
        except Exception as e:
            self.logger.error(f"❌ 컨텍스트 점수 조정 실패: {e}")
            return strategy_scores
    
    async def _make_final_selection(self, strategy_scores: Dict[str, float], 
                                  regime: MarketRegime, ai_insights: Dict) -> Dict[str, Any]:
        """최종 전략 선택"""
        try:
            # 점수 순으로 정렬
            sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
            
            # 최고 점수 전략 선택
            selected_name, selected_score = sorted_strategies[0]
            
            # 선택 이유 생성
            reasons = []
            
            # 체제 적합성
            if regime.regime_type in self.available_strategies[selected_name]['optimal_regimes']:
                reasons.append(f"{regime.regime_type} 체제에 최적화됨")
            
            # AI 추천
            if ai_insights.get('confidence', 0) > 0.6:
                market_sentiment = ai_insights.get('market_sentiment', 'neutral')
                if market_sentiment != 'neutral':
                    reasons.append(f"AI 분석: {market_sentiment} 시장 전망")
            
            # 성과 우수성
            if selected_score > 75:
                reasons.append("종합 점수 우수 (75점 이상)")
            
            # 점수 차이가 클 경우
            if len(sorted_strategies) > 1 and selected_score - sorted_strategies[1][1] > 15:
                reasons.append("다른 전략 대비 현저한 우위")
            
            return {
                'name': selected_name,
                'score': selected_score,
                'class_name': self.available_strategies[selected_name]['class_name'],
                'reasons': reasons,
                'runner_up': {
                    'name': sorted_strategies[1][0] if len(sorted_strategies) > 1 else None,
                    'score': sorted_strategies[1][1] if len(sorted_strategies) > 1 else 0
                },
                'selection_confidence': min(1.0, selected_score / 100)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 최종 전략 선택 실패: {e}")
            return {
                'name': 'momentum',
                'score': 60.0,
                'class_name': 'MomentumStrategy',
                'reasons': ['기본 전략 (선택 실패)'],
                'selection_confidence': 0.6
            }
    
    async def _assess_selection_risk(self, selected_strategy: Dict, regime: MarketRegime) -> Dict:
        """선택된 전략의 리스크 평가"""
        try:
            strategy_name = selected_strategy['name']
            strategy_info = self.available_strategies.get(strategy_name, {})
            
            risk_factors = []
            risk_level = 'MEDIUM'
            
            # 체제 불일치 리스크
            optimal_regimes = strategy_info.get('optimal_regimes', [])
            if regime.regime_type not in optimal_regimes:
                risk_factors.append('체제 불일치')
                risk_level = 'HIGH'
            
            # 체제 신뢰도 리스크
            if regime.confidence < 60:
                risk_factors.append('체제 감지 신뢰도 낮음')
                if risk_level != 'HIGH':
                    risk_level = 'MEDIUM_HIGH'
            
            # 전략별 고유 리스크
            strategy_risk_tolerance = strategy_info.get('risk_tolerance', 'medium')
            if strategy_risk_tolerance == 'high':
                risk_factors.append('고위험 전략')
                if risk_level == 'MEDIUM':
                    risk_level = 'MEDIUM_HIGH'
            
            # 선택 신뢰도 리스크
            if selected_strategy.get('selection_confidence', 1.0) < 0.7:
                risk_factors.append('선택 신뢰도 낮음')
            
            return {
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'recommended_position_size': self._get_recommended_position_size(risk_level),
                'monitoring_frequency': self._get_monitoring_frequency(risk_level)
            }
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 평가 실패: {e}")
            return {
                'risk_level': 'MEDIUM',
                'risk_factors': ['평가 실패'],
                'recommended_position_size': 0.05,
                'monitoring_frequency': 'HOURLY'
            }
    
    def _get_recommended_position_size(self, risk_level: str) -> float:
        """리스크 레벨별 포지션 사이즈"""
        position_sizes = {
            'LOW': 0.15,
            'MEDIUM': 0.10,
            'MEDIUM_HIGH': 0.07,
            'HIGH': 0.05,
            'VERY_HIGH': 0.03
        }
        return position_sizes.get(risk_level, 0.10)
    
    def _get_monitoring_frequency(self, risk_level: str) -> str:
        """리스크 레벨별 모니터링 주기"""
        frequencies = {
            'LOW': 'DAILY',
            'MEDIUM': 'HOURLY',
            'MEDIUM_HIGH': '30MIN',
            'HIGH': '15MIN',
            'VERY_HIGH': '5MIN'
        }
        return frequencies.get(risk_level, 'HOURLY')
    
    def _get_fallback_strategy(self) -> Dict[str, Any]:
        """폴백 전략"""
        return {
            'selected_strategy': {
                'name': 'momentum',
                'score': 60.0,
                'class_name': 'MomentumStrategy',
                'reasons': ['시스템 기본 전략'],
                'selection_confidence': 0.6
            },
            'regime_analysis': {
                'regime_type': 'UNKNOWN',
                'sub_regime': 'MODERATE',
                'confidence': 50.0
            },
            'ai_insights': self._get_default_market_insights(),
            'strategy_scores': {'momentum': 60.0},
            'risk_assessment': {
                'risk_level': 'MEDIUM',
                'risk_factors': ['분석 실패'],
                'recommended_position_size': 0.05,
                'monitoring_frequency': 'HOURLY'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def update_strategy_performance(self, strategy_name: str, regime_type: str, 
                                        trade_result: Dict) -> None:
        """전략 성과 업데이트"""
        try:
            performance_key = f"{strategy_name}_{regime_type}"
            
            if performance_key not in self.strategy_performance_history:
                self.strategy_performance_history[performance_key] = StrategyPerformance(
                    strategy_name=strategy_name,
                    regime_type=regime_type,
                    win_rate=0.0,
                    avg_return=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    total_trades=0,
                    last_update=datetime.now(),
                    confidence_score=0.5
                )
            
            performance = self.strategy_performance_history[performance_key]
            
            # 성과 업데이트 로직 (간단 버전)
            is_win = trade_result.get('profit', 0) > 0
            return_rate = trade_result.get('return_rate', 0)
            
            # 이동 평균 업데이트
            alpha = 0.1  # 학습률
            performance.win_rate = performance.win_rate * (1 - alpha) + (1.0 if is_win else 0.0) * alpha
            performance.avg_return = performance.avg_return * (1 - alpha) + return_rate * alpha
            performance.total_trades += 1
            performance.last_update = datetime.now()
            
            # 신뢰도 점수 업데이트
            performance.confidence_score = min(1.0, performance.total_trades / 50.0)
            
            self.logger.debug(f"📊 {strategy_name} ({regime_type}) 성과 업데이트 - 승률: {performance.win_rate:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ 전략 성과 업데이트 실패: {e}")
    
    def get_current_selection_info(self) -> Dict[str, Any]:
        """현재 선택 정보"""
        return {
            'current_strategy': self.current_strategy,
            'current_regime': self.current_regime.regime_type if self.current_regime else None,
            'last_selection_time': self.last_selection_time.isoformat() if self.last_selection_time else None,
            'selection_age_minutes': (datetime.now() - self.last_selection_time).total_seconds() / 60 if self.last_selection_time else None
        }