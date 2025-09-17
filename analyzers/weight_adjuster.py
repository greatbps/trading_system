#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/weight_adjuster.py

동적 가중치 조정기 - 시장 상황과 성과 추적 결과를 바탕으로 분석기별 가중치 동적 조정
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import numpy as np
import json

from utils.logger import get_logger
from analyzers.market_condition_analyzer import MarketConditionAnalyzer, MarketCondition, VolatilityRegime, TradingTimeRegime
from analyzers.performance_tracker import PerformanceTracker, AnalyzerPerformance


@dataclass
class WeightAdjustmentReason:
    """가중치 조정 근거"""
    reason_type: str  # "market_condition", "performance", "combined"
    description: str
    adjustment_factor: float
    confidence: float  # 0.0 - 1.0


@dataclass
class DynamicWeights:
    """동적 가중치"""
    base_weights: Dict[str, float]
    adjusted_weights: Dict[str, float]
    adjustment_reasons: List[WeightAdjustmentReason]
    market_condition: MarketCondition
    adjustment_timestamp: datetime
    confidence_score: float  # 전체 조정의 신뢰도


class WeightAdjuster:
    """동적 가중치 조정기"""
    
    def __init__(self, config, market_condition_analyzer: MarketConditionAnalyzer, 
                 performance_tracker: PerformanceTracker):
        self.config = config
        self.logger = get_logger("WeightAdjuster")
        self.market_analyzer = market_condition_analyzer
        self.performance_tracker = performance_tracker
        
        # 조정 설정
        self.max_weight_change = 0.3  # 최대 30% 가중치 변경
        self.min_weight_threshold = 0.03  # 최소 가중치 3%
        self.max_weight_threshold = 0.50  # 최대 가중치 50%
        
        # 조정 이력
        self.adjustment_history: List[DynamicWeights] = []
        self.max_history_size = 100
        
        # 기본 전략별 가중치 (ConsensusEngine과 동일)
        self.base_strategy_weights = {
            'momentum': {'technical': 0.25, 'sentiment': 0.15, 'supply_demand': 0.20, 'chart_pattern': 0.10, 'fundamental': 0.05, 'mtf': 0.25},
            'breakout': {'technical': 0.30, 'sentiment': 0.10, 'supply_demand': 0.15, 'chart_pattern': 0.15, 'fundamental': 0.05, 'mtf': 0.25},
            'vwap': {'technical': 0.35, 'sentiment': 0.10, 'supply_demand': 0.20, 'chart_pattern': 0.05, 'fundamental': 0.05, 'mtf': 0.25},
            'supertrend_ema_rsi': {'technical': 0.30, 'sentiment': 0.15, 'supply_demand': 0.15, 'chart_pattern': 0.10, 'fundamental': 0.05, 'mtf': 0.25},
            'eod': {'technical': 0.20, 'sentiment': 0.20, 'supply_demand': 0.20, 'chart_pattern': 0.10, 'fundamental': 0.10, 'mtf': 0.20}
        }
        
        self.logger.info("✅ WeightAdjuster 초기화 완료")
    
    async def get_dynamic_weights(self, strategy: str, multi_llm_enabled: bool = False) -> DynamicWeights:
        """동적 가중치 계산 및 반환"""
        try:
            # 1. 기본 가중치 가져오기
            base_weights = self._get_base_weights(strategy, multi_llm_enabled)
            
            # 2. 현재 시장 상황 분석
            market_condition = await self.market_analyzer.analyze_current_condition()
            
            # 3. 성과 기반 조정 팩터 계산
            performance_adjustments = self.performance_tracker.get_weight_adjustments()
            
            # 4. 시장 상황 기반 조정 팩터 계산
            market_adjustments = self._calculate_market_based_adjustments(market_condition)
            
            # 5. 종합 가중치 조정
            adjusted_weights, adjustment_reasons = self._apply_adjustments(
                base_weights, market_adjustments, performance_adjustments, market_condition
            )
            
            # 6. 가중치 정규화 및 유효성 검증
            final_weights = self._normalize_and_validate_weights(adjusted_weights)
            
            # 7. 신뢰도 스코어 계산
            confidence_score = self._calculate_confidence_score(adjustment_reasons, market_condition)
            
            # 8. 결과 생성
            dynamic_weights = DynamicWeights(
                base_weights=base_weights,
                adjusted_weights=final_weights,
                adjustment_reasons=adjustment_reasons,
                market_condition=market_condition,
                adjustment_timestamp=datetime.now(),
                confidence_score=confidence_score
            )
            
            # 9. 이력 저장
            self._save_adjustment_history(dynamic_weights)
            
            self.logger.info(f"🎯 동적 가중치 조정 완료 - 신뢰도: {confidence_score:.3f}")
            return dynamic_weights
            
        except Exception as e:
            self.logger.error(f"❌ 동적 가중치 계산 실패: {e}")
            # 기본 가중치 반환
            return self._get_fallback_weights(strategy, multi_llm_enabled)
    
    def _get_base_weights(self, strategy: str, multi_llm_enabled: bool) -> Dict[str, float]:
        """기본 가중치 가져오기 (ConsensusEngine과 동일한 로직)"""
        base_weights = self.base_strategy_weights.get(strategy, self.base_strategy_weights['momentum']).copy()
        
        if multi_llm_enabled:
            llm_weight = 0.20
            for key in base_weights:
                base_weights[key] *= (1 - llm_weight)
            base_weights['multi_llm'] = llm_weight
        
        return base_weights
    
    def _calculate_market_based_adjustments(self, market_condition: MarketCondition) -> Dict[str, float]:
        """시장 상황 기반 조정 팩터 계산"""
        adjustments = {}
        
        # MarketCondition에서 이미 계산된 팩터들 사용
        adjustments['technical'] = market_condition.technical_weight_factor
        adjustments['sentiment'] = market_condition.sentiment_weight_factor
        adjustments['supply_demand'] = market_condition.volume_weight_factor  # 거래량 분석을 수급 분석에 반영
        adjustments['chart_pattern'] = market_condition.technical_weight_factor * 0.8  # 기술적 분석과 유사하지만 약간 낮게
        adjustments['fundamental'] = 1.0  # 펀더멘털 분석은 시장 상황에 덜 민감
        adjustments['mtf'] = market_condition.momentum_weight_factor
        
        # multi_llm이 있는 경우
        if 'multi_llm' in [key for key in adjustments.keys()]:
            adjustments['multi_llm'] = 1.0  # LLM 분석은 기본값 유지
        
        return adjustments
    
    def _apply_adjustments(self, base_weights: Dict[str, float], 
                          market_adjustments: Dict[str, float],
                          performance_adjustments: Dict[str, float],
                          market_condition: MarketCondition) -> Tuple[Dict[str, float], List[WeightAdjustmentReason]]:
        """가중치 조정 적용"""
        
        adjusted_weights = base_weights.copy()
        adjustment_reasons = []
        
        for analyzer_name, base_weight in base_weights.items():
            
            # 1. 시장 상황 조정
            market_factor = market_adjustments.get(analyzer_name, 1.0)
            
            # 2. 성과 기반 조정
            performance_factor = performance_adjustments.get(analyzer_name, 1.0)
            
            # 3. 종합 조정 팩터 계산 (가중 평균)
            combined_factor = (market_factor * 0.6) + (performance_factor * 0.4)
            
            # 4. 최대 변경 한도 적용
            max_factor = 1.0 + self.max_weight_change
            min_factor = 1.0 - self.max_weight_change
            combined_factor = np.clip(combined_factor, min_factor, max_factor)
            
            # 5. 가중치 적용
            new_weight = base_weight * combined_factor
            adjusted_weights[analyzer_name] = new_weight
            
            # 6. 조정 근거 기록
            if abs(combined_factor - 1.0) > 0.05:  # 5% 이상 변경된 경우만 기록
                reason = WeightAdjustmentReason(
                    reason_type="combined",
                    description=f"{analyzer_name}: 시장조정 {market_factor:.3f} × 성과조정 {performance_factor:.3f}",
                    adjustment_factor=combined_factor,
                    confidence=self._calculate_adjustment_confidence(market_factor, performance_factor)
                )
                adjustment_reasons.append(reason)
        
        return adjusted_weights, adjustment_reasons
    
    def _normalize_and_validate_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """가중치 정규화 및 유효성 검증"""
        
        # 1. 최소/최대 임계값 적용
        for key in weights:
            weights[key] = np.clip(weights[key], self.min_weight_threshold, self.max_weight_threshold)
        
        # 2. 정규화 (합계가 1.0이 되도록)
        total_weight = sum(weights.values())
        if total_weight > 0:
            normalized_weights = {key: value / total_weight for key, value in weights.items()}
        else:
            # 비상 처리: 모든 가중치가 0이 된 경우
            normalized_weights = {key: 1.0 / len(weights) for key in weights}
        
        # 3. 정밀도 조정
        normalized_weights = {key: round(value, 4) for key, value in normalized_weights.items()}
        
        return normalized_weights
    
    def _calculate_adjustment_confidence(self, market_factor: float, performance_factor: float) -> float:
        """조정의 신뢰도 계산"""
        # 두 팩터가 같은 방향으로 조정될 때 신뢰도가 높음
        if (market_factor > 1.0 and performance_factor > 1.0) or \
           (market_factor < 1.0 and performance_factor < 1.0):
            return min(1.0, 0.7 + abs(market_factor - 1.0) + abs(performance_factor - 1.0))
        else:
            return max(0.3, 0.5 - abs(market_factor - performance_factor) * 0.5)
    
    def _calculate_confidence_score(self, adjustment_reasons: List[WeightAdjustmentReason],
                                  market_condition: MarketCondition) -> float:
        """전체 조정의 신뢰도 스코어 계산"""
        if not adjustment_reasons:
            return 0.8  # 조정이 없으면 기본 신뢰도
        
        # 개별 조정의 신뢰도 평균
        individual_confidence = np.mean([reason.confidence for reason in adjustment_reasons])
        
        # 시장 상황의 명확성 (변동성이 극단적일 때 더 확실한 조정)
        market_clarity = 0.5
        if market_condition.volatility_regime.value in ["high", "extreme"]:
            market_clarity = 0.8
        elif market_condition.volatility_regime.value == "low":
            market_clarity = 0.7
        
        # 종합 신뢰도 (개별 신뢰도 70% + 시장 명확성 30%)
        overall_confidence = (individual_confidence * 0.7) + (market_clarity * 0.3)
        
        return min(1.0, overall_confidence)
    
    def _save_adjustment_history(self, dynamic_weights: DynamicWeights):
        """조정 이력 저장"""
        self.adjustment_history.append(dynamic_weights)
        
        # 최대 크기 유지
        if len(self.adjustment_history) > self.max_history_size:
            self.adjustment_history.pop(0)
    
    def _get_fallback_weights(self, strategy: str, multi_llm_enabled: bool) -> DynamicWeights:
        """비상시 기본 가중치 반환"""
        base_weights = self._get_base_weights(strategy, multi_llm_enabled)
        
        return DynamicWeights(
            base_weights=base_weights,
            adjusted_weights=base_weights,
            adjustment_reasons=[],
            market_condition=MarketCondition(
                volatility_regime=VolatilityRegime.NORMAL,
                trading_time_regime=TradingTimeRegime.MORNING_STABLE,
                market_status=None,
                volatility_percentile=50.0,
                vix_equivalent=25.0,
                intraday_momentum=0.0,
                sector_rotation_active=False
            ),
            adjustment_timestamp=datetime.now(),
            confidence_score=0.5
        )
    
    def get_adjustment_history(self, hours: int = 24) -> List[DynamicWeights]:
        """최근 조정 이력 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [adj for adj in self.adjustment_history if adj.adjustment_timestamp > cutoff_time]
    
    def get_adjustment_statistics(self) -> Dict[str, Any]:
        """조정 통계 정보"""
        try:
            if not self.adjustment_history:
                return {}
            
            recent_adjustments = self.get_adjustment_history(24)  # 최근 24시간
            
            stats = {
                'total_adjustments': len(self.adjustment_history),
                'recent_adjustments_24h': len(recent_adjustments),
                'average_confidence': np.mean([adj.confidence_score for adj in recent_adjustments]) if recent_adjustments else 0,
                'most_adjusted_analyzer': None,
                'adjustment_frequency_by_hour': {},
                'volatility_regime_distribution': {}
            }
            
            if recent_adjustments:
                # 가장 많이 조정된 분석기
                adjustment_counts = {}
                for adj in recent_adjustments:
                    for reason in adj.adjustment_reasons:
                        analyzer = reason.description.split(':')[0]
                        adjustment_counts[analyzer] = adjustment_counts.get(analyzer, 0) + 1
                
                if adjustment_counts:
                    stats['most_adjusted_analyzer'] = max(adjustment_counts, key=adjustment_counts.get)
                
                # 변동성 체제별 분포
                volatility_counts = {}
                for adj in recent_adjustments:
                    regime = adj.market_condition.volatility_regime.value
                    volatility_counts[regime] = volatility_counts.get(regime, 0) + 1
                
                stats['volatility_regime_distribution'] = volatility_counts
            
            return stats
            
        except Exception as e:
            self.logger.error(f"❌ 조정 통계 생성 실패: {e}")
            return {}
    
    async def export_adjustment_history(self, filepath: str):
        """조정 이력 내보내기"""
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_records': len(self.adjustment_history),
                'adjustments': []
            }
            
            for adj in self.adjustment_history:
                adjustment_data = {
                    'timestamp': adj.adjustment_timestamp.isoformat(),
                    'confidence_score': adj.confidence_score,
                    'base_weights': adj.base_weights,
                    'adjusted_weights': adj.adjusted_weights,
                    'market_condition': {
                        'volatility_regime': adj.market_condition.volatility_regime.value,
                        'trading_time_regime': adj.market_condition.trading_time_regime.value,
                        'volatility_percentile': adj.market_condition.volatility_percentile,
                        'intraday_momentum': adj.market_condition.intraday_momentum
                    },
                    'adjustment_reasons': [
                        {
                            'reason_type': reason.reason_type,
                            'description': reason.description,
                            'adjustment_factor': reason.adjustment_factor,
                            'confidence': reason.confidence
                        }
                        for reason in adj.adjustment_reasons
                    ]
                }
                export_data['adjustments'].append(adjustment_data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📤 조정 이력 내보내기 완료: {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ 조정 이력 내보내기 실패: {e}")