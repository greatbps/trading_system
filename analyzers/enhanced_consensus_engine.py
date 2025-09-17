#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/enhanced_consensus_engine.py

향상된 종합 분석 엔진 - 동적 가중치 조정이 적용된 ConsensusEngine 확장
기존 ConsensusEngine과 완전 호환되면서 새로운 기능을 추가
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import numpy as np

from utils.logger import get_logger
from analyzers.consensus_engine import ConsensusEngine  # 기존 엔진 상속
from analyzers.market_condition_analyzer import MarketConditionAnalyzer
from analyzers.performance_tracker import PerformanceTracker
from analyzers.weight_adjuster import WeightAdjuster, DynamicWeights


class EnhancedConsensusEngine(ConsensusEngine):
    """
    향상된 종합 분석 엔진
    
    기존 ConsensusEngine을 상속하여 동적 가중치 조정 기능을 추가.
    기존 인터페이스와 완전 호환되면서 새로운 기능 제공.
    """
    
    def __init__(self, config=None, data_collector=None, database_manager=None, enable_dynamic_weights=True):
        # 기존 ConsensusEngine 초기화
        super().__init__(config)
        
        self.logger = get_logger("EnhancedConsensusEngine")
        self.enable_dynamic_weights = enable_dynamic_weights
        
        # 새로운 구성 요소들 (선택적 초기화)
        self.market_analyzer: Optional[MarketConditionAnalyzer] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.weight_adjuster: Optional[WeightAdjuster] = None
        
        # 동적 가중치 기능이 활성화된 경우에만 초기화
        if self.enable_dynamic_weights:
            self._initialize_dynamic_components(data_collector, database_manager)
        
        # 통계 및 모니터링
        self.dynamic_weight_usage_count = 0
        self.fallback_usage_count = 0
        self.last_weights_used: Optional[DynamicWeights] = None
        
        self.logger.info(f"✅ EnhancedConsensusEngine 초기화 완료 (동적가중치: {'활성' if enable_dynamic_weights else '비활성'})")
    
    def _initialize_dynamic_components(self, data_collector=None, database_manager=None):
        """동적 가중치 구성 요소 초기화"""
        try:
            # MarketConditionAnalyzer 초기화
            self.market_analyzer = MarketConditionAnalyzer(self.config, data_collector)
            
            # PerformanceTracker 초기화 (database_manager가 있는 경우만)
            if database_manager:
                self.performance_tracker = PerformanceTracker(self.config, database_manager)
                
                # WeightAdjuster 초기화
                self.weight_adjuster = WeightAdjuster(
                    self.config, 
                    self.market_analyzer, 
                    self.performance_tracker
                )
                
                self.logger.info("✅ 동적 가중치 구성 요소 초기화 완료")
            else:
                self.logger.warning("⚠️ DatabaseManager가 없어 동적 가중치 시스템 비활성화")
                self.enable_dynamic_weights = False  # 동적 기능 비활성화
                
        except Exception as e:
            self.logger.error(f"❌ 동적 구성 요소 초기화 실패: {e}")
            self.enable_dynamic_weights = False  # 동적 기능 비활성화
    
    def _create_mock_performance_tracker(self):
        """모의 PerformanceTracker (테스트/개발용)"""
        class MockPerformanceTracker:
            def get_weight_adjustments(self):
                # 기본 조정 팩터 (모든 분석기 동일)
                return {
                    'technical': 1.0,
                    'sentiment': 1.0,
                    'supply_demand': 1.0,
                    'chart_pattern': 1.0,
                    'fundamental': 1.0,
                    'mtf': 1.0,
                    'multi_llm': 1.0
                }
            
            async def record_prediction(self, *args, **kwargs):
                return "mock_prediction_id"
            
            async def validate_predictions(self):
                pass
        
        return MockPerformanceTracker()
    
    def synthesize(self, analysis_results: Dict, strategy: str, 
                   enable_dynamic=None, prediction_context: Dict = None) -> Tuple[float, Dict]:
        """
        종합 분석 결과 생성 (기존 인터페이스 유지 + 확장)
        
        Args:
            analysis_results: 분석 결과 (기존과 동일)
            strategy: 전략명 (기존과 동일)
            enable_dynamic: 동적 가중치 사용 여부 (새로운 옵션, None이면 클래스 설정 사용)
            prediction_context: 예측 기록용 컨텍스트 정보 (새로운 옵션)
        
        Returns:
            Tuple[float, Dict]: (최종 점수, 점수 세부사항) - 기존과 동일
        """
        try:
            # 동적 가중치 사용 여부 결정
            use_dynamic = enable_dynamic if enable_dynamic is not None else self.enable_dynamic_weights
            
            if use_dynamic and self._is_dynamic_system_ready():
                # 동적 가중치 시스템 사용 (동기적 실행)
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 이미 실행 중인 루프가 있는 경우 새 스레드에서 실행
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self._synthesize_with_dynamic_weights(analysis_results, strategy, prediction_context)
                            )
                            return future.result()
                    else:
                        return loop.run_until_complete(
                            self._synthesize_with_dynamic_weights(analysis_results, strategy, prediction_context)
                        )
                except RuntimeError:
                    # 이벤트 루프가 없는 경우 새로 생성
                    return asyncio.run(
                        self._synthesize_with_dynamic_weights(analysis_results, strategy, prediction_context)
                    )
            else:
                # 기존 시스템 사용 (완전 호환)
                self.fallback_usage_count += 1
                return super().synthesize(analysis_results, strategy)
                
        except Exception as e:
            self.logger.error(f"❌ Enhanced 종합 분석 실패: {e}")
            # 에러 시 기존 시스템으로 폴백
            self.fallback_usage_count += 1
            return super().synthesize(analysis_results, strategy)
    
    def _is_dynamic_system_ready(self) -> bool:
        """동적 시스템 준비 상태 확인"""
        return (self.enable_dynamic_weights and 
                self.market_analyzer is not None and 
                self.performance_tracker is not None and 
                self.weight_adjuster is not None)
    
    async def _synthesize_with_dynamic_weights(self, analysis_results: Dict, strategy: str,
                                             prediction_context: Dict = None) -> Tuple[float, Dict]:
        """동적 가중치를 사용한 종합 분석"""
        
        self.logger.info("🎯 동적 가중치 기반 종합 분석 시작...")
        
        # 1. 점수 추출 (기존 로직 사용)
        scores = self._extract_scores(analysis_results)
        
        # 2. 동적 가중치 계산
        multi_llm_enabled = 'multi_llm' in scores
        dynamic_weights = await self.weight_adjuster.get_dynamic_weights(strategy, multi_llm_enabled)
        self.last_weights_used = dynamic_weights
        
        # 3. 가중 점수 계산 (동적 가중치 사용)
        base_score = self._calculate_weighted_score(scores, dynamic_weights.adjusted_weights)
        
        # 4. 시너지/발산 보정 (기존 로직 사용)
        synergy_bonus = self._calculate_synergy_bonus(scores)
        divergence_penalty = self._calculate_divergence_penalty(scores)
        
        # 5. 최종 점수 계산
        final_score = base_score + synergy_bonus - divergence_penalty
        final_score = min(100, max(0, final_score))
        
        # 6. 변동 적용 (기존 로직 약간 수정)
        final_score = self._apply_dynamic_variation(final_score, scores, dynamic_weights)
        
        # 7. 예측 기록 (성과 추적용)
        await self._record_predictions_for_tracking(scores, final_score, strategy, prediction_context)
        
        # 8. 상세 정보 생성
        score_details = {
            'base_score': round(base_score, 2),
            'synergy_bonus': round(synergy_bonus, 2),
            'divergence_penalty': round(divergence_penalty, 2),
            'weights_used': dynamic_weights.adjusted_weights,
            'base_weights': dynamic_weights.base_weights,
            'individual_scores': scores,
            'market_condition': {
                'volatility_regime': dynamic_weights.market_condition.volatility_regime.value,
                'trading_time_regime': dynamic_weights.market_condition.trading_time_regime.value,
                'confidence_score': dynamic_weights.confidence_score
            },
            'adjustment_reasons': [
                {
                    'type': reason.reason_type,
                    'description': reason.description,
                    'confidence': reason.confidence
                }
                for reason in dynamic_weights.adjustment_reasons
            ],
            'dynamic_analysis_used': True
        }
        
        self.dynamic_weight_usage_count += 1
        self.logger.info(f"✅ 동적 가중치 종합 분석 완료: 최종 점수 {final_score:.2f} (신뢰도: {dynamic_weights.confidence_score:.3f})")
        
        return final_score, score_details
    
    def _apply_dynamic_variation(self, final_score: float, scores: Dict, dynamic_weights: DynamicWeights) -> float:
        """동적 환경을 고려한 점수 변동"""
        
        # 시장 변동성에 따른 변동 조정
        volatility_regime = dynamic_weights.market_condition.volatility_regime.value
        
        if volatility_regime == "high":
            # 높은 변동성 시기에는 더 큰 변동
            variation_range = 6.0
        elif volatility_regime == "extreme":
            # 극도로 높은 변동성 시기
            variation_range = 8.0
        elif volatility_regime == "low":
            # 낮은 변동성 시기에는 작은 변동
            variation_range = 3.0
        else:
            # 일반적인 경우
            variation_range = 5.0
        
        # 기존 로직과 유사하지만 시장 상황 반영
        if 20 < final_score < 95:
            import random
            base_variation = random.uniform(-variation_range, variation_range)
            
            # 개별 점수 분산 반영
            individual_scores = list(scores.values())
            score_variance = sum((s - final_score)**2 for s in individual_scores) / len(individual_scores)
            variance_factor = min(1.0, score_variance / 100)
            
            additional_variation = random.uniform(-2.0, 2.0) * variance_factor
            total_variation = base_variation + additional_variation
            
            final_score = min(100, max(0, final_score + total_variation))
            
            self.logger.info(f"🔧 [동적 변동 적용] {volatility_regime} 체제, 변동: {total_variation:.2f}")
        
        return final_score
    
    async def _record_predictions_for_tracking(self, scores: Dict, final_score: float, 
                                             strategy: str, prediction_context: Dict = None):
        """성과 추적을 위한 예측 기록"""
        try:
            if not self.performance_tracker or not prediction_context:
                return
            
            symbol = prediction_context.get('symbol', 'UNKNOWN')
            
            # 예측 방향 결정
            if final_score > 70:
                expected_direction = "up"
            elif final_score < 30:
                expected_direction = "down"
            else:
                expected_direction = "hold"
            
            # 신뢰도 계산 (점수와 일치성에 기반)
            confidence = min(1.0, abs(final_score - 50) / 50.0)
            
            # 시장 상황 정보
            market_condition_info = None
            volatility_regime = None
            
            if self.last_weights_used:
                market_condition_info = self.last_weights_used.market_condition.trading_time_regime.value
                volatility_regime = self.last_weights_used.market_condition.volatility_regime.value
            
            # 각 분석기별 예측 기록
            for analyzer_name, score in scores.items():
                await self.performance_tracker.record_prediction(
                    analyzer_name=analyzer_name,
                    symbol=symbol,
                    prediction_score=score,
                    confidence=confidence,
                    expected_direction=expected_direction,
                    strategy=strategy,
                    market_condition=market_condition_info,
                    volatility_regime=volatility_regime
                )
            
        except Exception as e:
            self.logger.warning(f"⚠️ 예측 기록 실패: {e}")
    
    # ============= 기존 ConsensusEngine과 호환을 위한 메서드들 =============
    
    def get_strategy_weights(self, strategy: str, multi_llm_enabled: bool = False) -> Dict[str, float]:
        """
        전략별 가중치 조회 (기존 API 호환)
        동적 시스템이 활성화되어 있으면 최근 동적 가중치 반환, 아니면 기존 방식
        """
        if self.enable_dynamic_weights and self.last_weights_used:
            return self.last_weights_used.adjusted_weights
        else:
            return self._get_strategy_weights(strategy, multi_llm_enabled)
    
    async def get_current_market_condition(self):
        """현재 시장 상황 조회"""
        if self.market_analyzer:
            return await self.market_analyzer.analyze_current_condition()
        return None
    
    def get_performance_summary(self):
        """성과 요약 조회"""
        if self.performance_tracker:
            return self.performance_tracker.get_performance_summary()
        return {}
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """시스템 통계 조회"""
        stats = {
            'dynamic_weight_enabled': self.enable_dynamic_weights,
            'dynamic_usage_count': self.dynamic_weight_usage_count,
            'fallback_usage_count': self.fallback_usage_count,
            'total_synthesize_calls': self.dynamic_weight_usage_count + self.fallback_usage_count,
            'dynamic_usage_rate': 0.0,
            'system_components_ready': self._is_dynamic_system_ready(),
            'last_weights_timestamp': None
        }
        
        if stats['total_synthesize_calls'] > 0:
            stats['dynamic_usage_rate'] = self.dynamic_weight_usage_count / stats['total_synthesize_calls']
        
        if self.last_weights_used:
            stats['last_weights_timestamp'] = self.last_weights_used.adjustment_timestamp.isoformat()
        
        # 추가 통계 (각 구성 요소별)
        if self.weight_adjuster:
            stats['weight_adjustment_stats'] = self.weight_adjuster.get_adjustment_statistics()
        
        return stats
    
    async def validate_predictions(self):
        """예측 결과 검증 (정기 실행용)"""
        if self.performance_tracker:
            await self.performance_tracker.validate_predictions()
    
    def enable_dynamic_features(self, enable: bool):
        """동적 기능 활성화/비활성화"""
        if enable and not self._is_dynamic_system_ready():
            self.logger.warning("⚠️ 동적 시스템 구성 요소가 준비되지 않아 활성화할 수 없습니다")
            return False
        
        self.enable_dynamic_weights = enable
        self.logger.info(f"🔧 동적 가중치 기능 {'활성화' if enable else '비활성화'}")
        return True
    
    async def cleanup_and_maintenance(self):
        """정리 및 유지보수 작업"""
        try:
            # 성과 추적 데이터 정리
            if self.performance_tracker:
                await self.performance_tracker.cleanup_old_records(90)  # 90일 이전 데이터 정리
            
            # 조정 이력 정리 (WeightAdjuster 내부에서 자동 관리됨)
            
            self.logger.info("🧹 시스템 정리 및 유지보수 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 시스템 유지보수 실패: {e}")


# ============= 기존 시스템과의 호환성을 위한 팩토리 함수 =============

def create_consensus_engine(config=None, enhanced=False, **kwargs):
    """
    ConsensusEngine 생성 팩토리 함수
    
    Args:
        config: 설정 정보
        enhanced: True이면 EnhancedConsensusEngine, False이면 기존 ConsensusEngine
        **kwargs: 추가 파라미터 (data_collector, database_manager 등)
    
    Returns:
        ConsensusEngine 또는 EnhancedConsensusEngine 인스턴스
    """
    if enhanced:
        return EnhancedConsensusEngine(config, **kwargs)
    else:
        return ConsensusEngine(config)


# ============= 기존 코드와의 호환성을 위한 별칭 =============

# 기존 코드에서 ConsensusEngine을 import하는 경우를 위한 호환성
# (필요시 활성화)
# ConsensusEngine = EnhancedConsensusEngine