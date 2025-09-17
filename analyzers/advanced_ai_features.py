#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/advanced_ai_features.py

AI Controller 고도화 - Phase 8 Advanced Features
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import pickle
from pathlib import Path

from utils.logger import get_logger
from utils.error_handler import async_error_handler, safe_execute

class LearningMode(Enum):
    """학습 모드"""
    REAL_TIME = "real_time"
    BATCH = "batch"
    HYBRID = "hybrid"
    REINFORCEMENT = "reinforcement"

class MarketCondition(Enum):
    """시장 상황"""
    BULL_STRONG = "bull_strong"
    BULL_WEAK = "bull_weak"
    BEAR_STRONG = "bear_strong"
    BEAR_WEAK = "bear_weak"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

@dataclass
class PredictionModel:
    """예측 모델 정보"""
    model_id: str
    model_type: str  # LSTM, GRU, Transformer, Ensemble
    accuracy: float
    last_trained: datetime
    training_samples: int
    feature_count: int
    performance_metrics: Dict[str, float]
    is_active: bool = True

@dataclass
class MarketSignal:
    """시장 신호"""
    signal_type: str  # BUY, SELL, HOLD, STRONG_BUY, STRONG_SELL
    symbol: str
    strength: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    time_horizon: str  # SHORT, MEDIUM, LONG
    supporting_indicators: List[str]
    risk_reward_ratio: float
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AILearningResult:
    """AI 학습 결과"""
    model_improvements: Dict[str, float]
    new_patterns_discovered: List[str]
    accuracy_changes: Dict[str, float]
    feature_importance_updates: Dict[str, float]
    recommended_actions: List[str]
    learning_metrics: Dict[str, Any]

class AdvancedAIFeatures:
    """고급 AI 기능 모음"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger("AdvancedAI")
        
        # 모델 저장소
        self.models_dir = Path("ai_models")
        self.models_dir.mkdir(exist_ok=True)
        
        # 활성 모델들
        self.active_models: Dict[str, PredictionModel] = {}
        self.model_performance_history = {}
        
        # 학습 설정
        self.learning_config = {
            'min_samples_for_training': 100,
            'max_model_age_days': 30,
            'accuracy_threshold': 0.65,
            'retraining_frequency_hours': 24,
            'ensemble_model_count': 5,
            'feature_selection_threshold': 0.7
        }
        
        # 실시간 데이터 버퍼
        self.market_data_buffer = []
        self.prediction_buffer = []
        self.signal_history = []
        
        # 성능 추적
        self.performance_tracker = {
            'predictions_made': 0,
            'correct_predictions': 0,
            'trades_executed': 0,
            'successful_trades': 0,
            'total_profit_loss': 0.0,
            'model_updates': 0
        }
        
        self.logger.info("🚀 고급 AI 기능 초기화 완료")
    
    @async_error_handler("market_pattern_recognition")
    async def advanced_pattern_recognition(self, market_data: List[Dict], 
                                         lookback_days: int = 30) -> Dict[str, Any]:
        """고급 패턴 인식"""
        try:
            self.logger.info("🔍 고급 패턴 인식 시작")
            
            # 1. 다중 시간프레임 패턴 분석
            patterns = {
                'short_term': await self._analyze_patterns(market_data, timeframe='5m'),
                'medium_term': await self._analyze_patterns(market_data, timeframe='1h'),
                'long_term': await self._analyze_patterns(market_data, timeframe='1d')
            }
            
            # 2. 숨겨진 패턴 발견
            hidden_patterns = await self._discover_hidden_patterns(market_data)
            
            # 3. 패턴 신뢰도 평가
            pattern_confidence = await self._evaluate_pattern_confidence(patterns, hidden_patterns)
            
            # 4. 실행 가능한 패턴 필터링
            actionable_patterns = await self._filter_actionable_patterns(
                patterns, pattern_confidence
            )
            
            return {
                'identified_patterns': patterns,
                'hidden_patterns': hidden_patterns,
                'pattern_confidence': pattern_confidence,
                'actionable_patterns': actionable_patterns,
                'pattern_strength': len(actionable_patterns),
                'analysis_timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"패턴 인식 중 오류: {e}")
            return {'error': str(e)}
    
    @async_error_handler("adaptive_learning")
    async def adaptive_learning_system(self, new_data: List[Dict], 
                                     trading_results: List[Dict]) -> AILearningResult:
        """적응형 학습 시스템"""
        try:
            self.logger.info("🧠 적응형 학습 시작")
            
            # 1. 새 데이터 품질 검증
            validated_data = await self._validate_training_data(new_data)
            
            # 2. 모델 성능 평가
            current_performance = await self._evaluate_model_performance(trading_results)
            
            # 3. 학습 필요성 판단
            learning_needed = await self._assess_learning_necessity(
                current_performance, validated_data
            )
            
            if not learning_needed:
                return AILearningResult(
                    model_improvements={},
                    new_patterns_discovered=[],
                    accuracy_changes={},
                    feature_importance_updates={},
                    recommended_actions=["No learning required"],
                    learning_metrics={'status': 'stable'}
                )
            
            # 4. 적응형 학습 실행
            learning_results = await self._execute_adaptive_learning(
                validated_data, current_performance
            )
            
            # 5. 모델 업데이트
            await self._update_models(learning_results)
            
            # 6. 성능 추적 업데이트
            self.performance_tracker['model_updates'] += 1
            
            return learning_results
            
        except Exception as e:
            self.logger.error(f"적응형 학습 중 오류: {e}")
            return AILearningResult(
                model_improvements={},
                new_patterns_discovered=[],
                accuracy_changes={},
                feature_importance_updates={},
                recommended_actions=[f"Learning failed: {e}"],
                learning_metrics={'error': str(e)}
            )
    
    @async_error_handler("intelligent_signal_generation")
    async def intelligent_signal_generation(self, symbols: List[str], 
                                          market_context: Dict) -> List[MarketSignal]:
        """지능형 신호 생성"""
        try:
            self.logger.info(f"📡 {len(symbols)}개 종목 지능형 신호 생성")
            
            signals = []
            
            for symbol in symbols:
                # 1. 다중 모델 예측
                predictions = await self._multi_model_prediction(symbol, market_context)
                
                # 2. 앙상블 예측 결합
                ensemble_prediction = await self._combine_predictions(predictions)
                
                # 3. 시장 상황 고려
                context_adjusted = await self._adjust_for_market_context(
                    ensemble_prediction, market_context
                )
                
                # 4. 신호 생성
                if context_adjusted['confidence'] >= self.learning_config['accuracy_threshold']:
                    signal = await self._generate_market_signal(symbol, context_adjusted)
                    signals.append(signal)
            
            # 5. 신호 우선순위 정렬
            prioritized_signals = await self._prioritize_signals(signals)
            
            # 6. 신호 히스토리 업데이트
            self.signal_history.extend(prioritized_signals)
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]
            
            return prioritized_signals
            
        except Exception as e:
            self.logger.error(f"신호 생성 중 오류: {e}")
            return []
    
    @async_error_handler("portfolio_optimization")
    async def ai_portfolio_optimization(self, current_portfolio: Dict, 
                                      available_capital: float,
                                      risk_tolerance: str) -> Dict[str, Any]:
        """AI 포트폴리오 최적화"""
        try:
            self.logger.info("💼 AI 포트폴리오 최적화 시작")
            
            # 1. 현재 포트폴리오 분석
            portfolio_analysis = await self._analyze_current_portfolio(current_portfolio)
            
            # 2. 위험 수준별 최적화
            risk_level = self._convert_risk_tolerance(risk_tolerance)
            optimization_params = await self._get_optimization_parameters(risk_level)
            
            # 3. AI 기반 자산 배분
            optimal_allocation = await self._calculate_optimal_allocation(
                portfolio_analysis, available_capital, optimization_params
            )
            
            # 4. 리밸런싱 권장사항
            rebalancing_actions = await self._generate_rebalancing_actions(
                current_portfolio, optimal_allocation
            )
            
            # 5. 예상 성과 시뮬레이션
            performance_projection = await self._simulate_portfolio_performance(
                optimal_allocation, optimization_params
            )
            
            return {
                'current_analysis': portfolio_analysis,
                'optimal_allocation': optimal_allocation,
                'rebalancing_actions': rebalancing_actions,
                'performance_projection': performance_projection,
                'risk_metrics': {
                    'expected_return': performance_projection.get('expected_return', 0),
                    'volatility': performance_projection.get('volatility', 0),
                    'sharpe_ratio': performance_projection.get('sharpe_ratio', 0),
                    'max_drawdown': performance_projection.get('max_drawdown', 0)
                },
                'optimization_timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"포트폴리오 최적화 중 오류: {e}")
            return {'error': str(e)}
    
    async def _analyze_patterns(self, data: List[Dict], timeframe: str) -> Dict[str, Any]:
        """패턴 분석 (내부 메서드)"""
        # 시간프레임별 패턴 분석 로직
        patterns_found = []
        
        # 간단한 패턴 인식 (실제로는 더 복잡한 알고리즘 사용)
        if len(data) >= 20:
            # 상승/하락 패턴 감지
            prices = [float(d.get('price', 0)) for d in data[-20:]]
            if prices:
                trend = 'up' if prices[-1] > prices[0] else 'down'
                strength = abs(prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
                
                patterns_found.append({
                    'type': f'trend_{trend}',
                    'strength': min(strength * 100, 100),
                    'timeframe': timeframe,
                    'confidence': min(strength * 10, 1.0)
                })
        
        return {
            'timeframe': timeframe,
            'patterns': patterns_found,
            'pattern_count': len(patterns_found)
        }
    
    async def _discover_hidden_patterns(self, data: List[Dict]) -> List[Dict]:
        """숨겨진 패턴 발견"""
        hidden_patterns = []
        
        # 가격 변동성 패턴
        if len(data) >= 10:
            prices = [float(d.get('price', 0)) for d in data[-10:]]
            if prices:
                volatility = np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
                
                if volatility > 0.05:  # 5% 이상 변동성
                    hidden_patterns.append({
                        'type': 'high_volatility_cluster',
                        'strength': min(volatility * 20, 100),
                        'description': f'높은 변동성 패턴 감지 (변동성: {volatility:.2%})',
                        'actionable': volatility > 0.1
                    })
        
        return hidden_patterns
    
    async def _evaluate_pattern_confidence(self, patterns: Dict, hidden_patterns: List) -> Dict[str, float]:
        """패턴 신뢰도 평가"""
        confidence_scores = {}
        
        # 시간프레임별 패턴 신뢰도
        for timeframe, pattern_data in patterns.items():
            total_confidence = 0
            pattern_count = len(pattern_data.get('patterns', []))
            
            if pattern_count > 0:
                for pattern in pattern_data['patterns']:
                    total_confidence += pattern.get('confidence', 0)
                confidence_scores[timeframe] = total_confidence / pattern_count
            else:
                confidence_scores[timeframe] = 0.0
        
        # 숨겨진 패턴 신뢰도
        if hidden_patterns:
            hidden_confidence = sum(p.get('strength', 0) for p in hidden_patterns) / len(hidden_patterns) / 100
            confidence_scores['hidden_patterns'] = hidden_confidence
        
        return confidence_scores
    
    async def _filter_actionable_patterns(self, patterns: Dict, confidence: Dict) -> List[Dict]:
        """실행 가능한 패턴 필터링"""
        actionable = []
        confidence_threshold = 0.6
        
        for timeframe, pattern_data in patterns.items():
            if confidence.get(timeframe, 0) >= confidence_threshold:
                for pattern in pattern_data.get('patterns', []):
                    if pattern.get('confidence', 0) >= confidence_threshold:
                        actionable.append({
                            'timeframe': timeframe,
                            'pattern': pattern,
                            'action_priority': 'HIGH' if pattern['confidence'] > 0.8 else 'MEDIUM'
                        })
        
        return actionable
    
    def get_ai_system_status(self) -> Dict[str, Any]:
        """AI 시스템 상태 반환"""
        total_predictions = self.performance_tracker['predictions_made']
        accuracy = (self.performance_tracker['correct_predictions'] / total_predictions 
                   if total_predictions > 0 else 0)
        
        return {
            'active_models': len(self.active_models),
            'prediction_accuracy': accuracy,
            'total_predictions': total_predictions,
            'model_updates': self.performance_tracker['model_updates'],
            'signal_history_size': len(self.signal_history),
            'system_health': self._assess_system_health(),
            'last_update': datetime.now(),
            'performance_metrics': self.performance_tracker
        }
    
    def _assess_system_health(self) -> str:
        """시스템 건강도 평가"""
        accuracy = (self.performance_tracker['correct_predictions'] / 
                   max(self.performance_tracker['predictions_made'], 1))
        
        if accuracy >= 0.8:
            return "EXCELLENT"
        elif accuracy >= 0.7:
            return "GOOD"
        elif accuracy >= 0.6:
            return "FAIR"
        else:
            return "NEEDS_IMPROVEMENT"

# 추가 헬퍼 메서드들 (스텁 구현)
    async def _validate_training_data(self, data: List[Dict]) -> List[Dict]:
        return [d for d in data if d.get('price') and d.get('volume')]
    
    async def _evaluate_model_performance(self, results: List[Dict]) -> Dict[str, float]:
        return {'accuracy': 0.75, 'precision': 0.8, 'recall': 0.7}
    
    async def _assess_learning_necessity(self, performance: Dict, data: List[Dict]) -> bool:
        return performance.get('accuracy', 0) < 0.8 and len(data) >= 50
    
    async def _execute_adaptive_learning(self, data: List[Dict], performance: Dict) -> AILearningResult:
        return AILearningResult(
            model_improvements={'accuracy': 0.05},
            new_patterns_discovered=['volatility_cluster'],
            accuracy_changes={'model_1': 0.03},
            feature_importance_updates={'volume': 0.1},
            recommended_actions=['Increase volume weight'],
            learning_metrics={'samples_processed': len(data)}
        )
    
    async def _update_models(self, results: AILearningResult) -> None:
        self.logger.info(f"모델 업데이트 완료: {results.model_improvements}")

if __name__ == "__main__":
    # 테스트
    import asyncio
    
    async def test_advanced_ai():
        class MockConfig:
            pass
        
        ai = AdvancedAIFeatures(MockConfig())
        
        # 테스트 데이터
        test_data = [
            {'symbol': 'TEST001', 'price': 100 + i, 'volume': 1000 * (i+1)}
            for i in range(30)
        ]
        
        # 패턴 인식 테스트
        patterns = await ai.advanced_pattern_recognition(test_data)
        print(f"패턴 인식 결과: {patterns}")
        
        # 시스템 상태 확인
        status = ai.get_ai_system_status()
        print(f"AI 시스템 상태: {status}")
    
    asyncio.run(test_advanced_ai())