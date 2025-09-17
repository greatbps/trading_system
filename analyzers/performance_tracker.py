#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/analyzers/performance_tracker.py

성과 추적기 - 과거 예측 정확도를 통한 분석기별 가중치 조정
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from collections import defaultdict, deque
import json

from utils.logger import get_logger
from database.database_manager import DatabaseManager


class PredictionOutcome(Enum):
    """예측 결과"""
    CORRECT = "correct"           # 예측 정확
    INCORRECT = "incorrect"       # 예측 틀림
    PARTIALLY_CORRECT = "partial" # 부분 정확
    PENDING = "pending"           # 결과 대기 중


@dataclass
class AnalyzerPerformance:
    """분석기 성과"""
    analyzer_name: str
    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy_rate: float = 0.0
    
    # 시간 윈도우별 성과 (최근 1일, 7일, 30일)
    accuracy_1d: float = 0.0
    accuracy_7d: float = 0.0
    accuracy_30d: float = 0.0
    
    # 예측 신뢰도 분포
    high_confidence_accuracy: float = 0.0  # 신뢰도 > 80%
    medium_confidence_accuracy: float = 0.0  # 신뢰도 50-80%
    low_confidence_accuracy: float = 0.0   # 신뢰도 < 50%
    
    # 시장 상황별 성과
    high_volatility_accuracy: float = 0.0
    normal_volatility_accuracy: float = 0.0
    low_volatility_accuracy: float = 0.0
    
    # 가중치 조정 팩터
    weight_adjustment_factor: float = 1.0  # 0.5 ~ 1.5 범위
    
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PredictionRecord:
    """예측 기록"""
    prediction_id: str
    analyzer_name: str
    symbol: str
    prediction_time: datetime
    prediction_score: float
    confidence: float
    expected_direction: str  # "up", "down", "hold"
    
    # 검증 정보
    validation_time: Optional[datetime] = None
    actual_outcome: Optional[PredictionOutcome] = None
    actual_return: Optional[float] = None
    
    # 컨텍스트 정보
    market_condition: Optional[str] = None
    volatility_regime: Optional[str] = None
    strategy_used: Optional[str] = None


class PerformanceTracker:
    """성과 추적기 - 분석기별 예측 정확도 추적 및 가중치 조정"""
    
    def __init__(self, config, database_manager: DatabaseManager):
        self.config = config
        self.logger = get_logger("PerformanceTracker")
        self.db_manager = database_manager
        
        # 성과 추적 데이터
        self.analyzer_performances: Dict[str, AnalyzerPerformance] = {}
        self.prediction_records: deque = deque(maxlen=10000)  # 최근 1만개 기록
        
        # 분석기 목록
        self.analyzer_names = [
            'technical', 'sentiment', 'supply_demand', 
            'chart_pattern', 'fundamental', 'mtf', 'multi_llm'
        ]
        
        # 성과 평가 설정
        self.validation_hours = 24  # 24시간 후 결과 검증
        self.min_predictions_for_adjustment = 20  # 최소 예측 횟수
        self.performance_decay_rate = 0.95  # 시간에 따른 성과 가중치 감소
        
        # 초기화
        self._initialize_analyzer_performances()
        
        self.logger.info("✅ PerformanceTracker 초기화 완료")
    
    def _initialize_analyzer_performances(self):
        """분석기 성과 초기화"""
        for analyzer_name in self.analyzer_names:
            self.analyzer_performances[analyzer_name] = AnalyzerPerformance(
                analyzer_name=analyzer_name
            )
    
    async def record_prediction(self, analyzer_name: str, symbol: str, 
                              prediction_score: float, confidence: float,
                              expected_direction: str, strategy: str = None,
                              market_condition: str = None,
                              volatility_regime: str = None) -> str:
        """예측 기록 저장"""
        try:
            prediction_id = f"{analyzer_name}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            record = PredictionRecord(
                prediction_id=prediction_id,
                analyzer_name=analyzer_name,
                symbol=symbol,
                prediction_time=datetime.now(),
                prediction_score=prediction_score,
                confidence=confidence,
                expected_direction=expected_direction,
                market_condition=market_condition,
                volatility_regime=volatility_regime,
                strategy_used=strategy
            )
            
            self.prediction_records.append(record)
            
            # 데이터베이스에 저장 (옵션)
            await self._save_prediction_to_db(record)
            
            self.logger.debug(f"📝 예측 기록 저장: {analyzer_name} - {symbol} ({expected_direction})")
            return prediction_id
            
        except Exception as e:
            self.logger.error(f"❌ 예측 기록 저장 실패: {e}")
            return ""
    
    async def validate_predictions(self):
        """예측 결과 검증 - 정기적으로 실행"""
        try:
            current_time = datetime.now()
            validation_count = 0
            
            for record in self.prediction_records:
                # 아직 검증되지 않고 충분한 시간이 경과한 예측들
                if (record.actual_outcome is None and 
                    record.prediction_time + timedelta(hours=self.validation_hours) <= current_time):
                    
                    # 실제 결과 조회 및 검증
                    outcome = await self._validate_single_prediction(record)
                    if outcome is not None:
                        record.actual_outcome = outcome.outcome
                        record.actual_return = outcome.actual_return
                        record.validation_time = current_time
                        validation_count += 1
            
            if validation_count > 0:
                # 성과 업데이트
                await self._update_analyzer_performances()
                self.logger.info(f"✅ {validation_count}개 예측 검증 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 예측 검증 실패: {e}")
    
    async def _validate_single_prediction(self, record: PredictionRecord) -> Optional[Any]:
        """단일 예측 검증"""
        try:
            # 실제 가격 데이터 조회 (prediction_time부터 validation_hours 후까지)
            start_time = record.prediction_time
            end_time = start_time + timedelta(hours=self.validation_hours)
            
            # 실제 구현에서는 database_manager를 통해 가격 데이터 조회
            # 현재는 모의 검증
            actual_return = np.random.normal(0, 0.02)  # 모의 수익률
            
            # 예측 방향과 실제 결과 비교
            predicted_direction = record.expected_direction
            actual_direction = "up" if actual_return > 0.01 else "down" if actual_return < -0.01 else "hold"
            
            # 결과 판정
            if predicted_direction == actual_direction:
                outcome = PredictionOutcome.CORRECT
            elif (predicted_direction in ["up", "down"] and actual_direction == "hold") or \
                 (predicted_direction == "hold" and actual_direction in ["up", "down"]):
                outcome = PredictionOutcome.PARTIALLY_CORRECT
            else:
                outcome = PredictionOutcome.INCORRECT
            
            return type('ValidationResult', (), {
                'outcome': outcome,
                'actual_return': actual_return
            })()
            
        except Exception as e:
            self.logger.warning(f"⚠️ 예측 검증 실패 ({record.prediction_id}): {e}")
            return None
    
    async def _update_analyzer_performances(self):
        """분석기별 성과 업데이트"""
        try:
            # 각 분석기별로 성과 계산
            for analyzer_name in self.analyzer_names:
                analyzer_records = [r for r in self.prediction_records 
                                  if r.analyzer_name == analyzer_name and r.actual_outcome is not None]
                
                if not analyzer_records:
                    continue
                
                performance = self.analyzer_performances[analyzer_name]
                
                # 전체 성과
                total_predictions = len(analyzer_records)
                correct_predictions = len([r for r in analyzer_records 
                                         if r.actual_outcome == PredictionOutcome.CORRECT])
                partially_correct = len([r for r in analyzer_records 
                                       if r.actual_outcome == PredictionOutcome.PARTIALLY_CORRECT])
                
                # 부분 정답은 0.5점으로 계산
                effective_correct = correct_predictions + (partially_correct * 0.5)
                accuracy_rate = effective_correct / total_predictions if total_predictions > 0 else 0
                
                # 시간 윈도우별 성과
                current_time = datetime.now()
                
                records_1d = [r for r in analyzer_records 
                             if r.validation_time and (current_time - r.validation_time).days <= 1]
                records_7d = [r for r in analyzer_records 
                             if r.validation_time and (current_time - r.validation_time).days <= 7]
                records_30d = [r for r in analyzer_records 
                              if r.validation_time and (current_time - r.validation_time).days <= 30]
                
                accuracy_1d = self._calculate_accuracy(records_1d)
                accuracy_7d = self._calculate_accuracy(records_7d)
                accuracy_30d = self._calculate_accuracy(records_30d)
                
                # 신뢰도별 성과
                high_conf_records = [r for r in analyzer_records if r.confidence > 0.8]
                medium_conf_records = [r for r in analyzer_records if 0.5 <= r.confidence <= 0.8]
                low_conf_records = [r for r in analyzer_records if r.confidence < 0.5]
                
                high_conf_accuracy = self._calculate_accuracy(high_conf_records)
                medium_conf_accuracy = self._calculate_accuracy(medium_conf_records)
                low_conf_accuracy = self._calculate_accuracy(low_conf_records)
                
                # 가중치 조정 팩터 계산
                weight_factor = self._calculate_weight_adjustment_factor(
                    accuracy_rate, accuracy_7d, total_predictions
                )
                
                # 성과 업데이트
                performance.total_predictions = total_predictions
                performance.correct_predictions = correct_predictions
                performance.accuracy_rate = accuracy_rate
                performance.accuracy_1d = accuracy_1d
                performance.accuracy_7d = accuracy_7d
                performance.accuracy_30d = accuracy_30d
                performance.high_confidence_accuracy = high_conf_accuracy
                performance.medium_confidence_accuracy = medium_conf_accuracy
                performance.low_confidence_accuracy = low_conf_accuracy
                performance.weight_adjustment_factor = weight_factor
                performance.last_updated = current_time
                
                self.logger.debug(f"📊 {analyzer_name} 성과 업데이트: 정확도 {accuracy_rate:.3f}, 조정팩터 {weight_factor:.3f}")
            
        except Exception as e:
            self.logger.error(f"❌ 성과 업데이트 실패: {e}")
    
    def _calculate_accuracy(self, records: List[PredictionRecord]) -> float:
        """정확도 계산"""
        if not records:
            return 0.0
        
        correct_count = len([r for r in records if r.actual_outcome == PredictionOutcome.CORRECT])
        partial_count = len([r for r in records if r.actual_outcome == PredictionOutcome.PARTIALLY_CORRECT])
        
        effective_correct = correct_count + (partial_count * 0.5)
        return effective_correct / len(records)
    
    def _calculate_weight_adjustment_factor(self, overall_accuracy: float, 
                                          recent_accuracy: float, 
                                          total_predictions: int) -> float:
        """가중치 조정 팩터 계산"""
        
        # 최소 예측 횟수 확인
        if total_predictions < self.min_predictions_for_adjustment:
            return 1.0  # 기본값
        
        # 최근 성과에 더 높은 가중치 부여
        weighted_accuracy = (overall_accuracy * 0.3) + (recent_accuracy * 0.7)
        
        # 0.5 ~ 1.5 범위로 조정
        if weighted_accuracy > 0.7:
            factor = min(1.5, 1.0 + (weighted_accuracy - 0.7) * 2.0)
        elif weighted_accuracy < 0.3:
            factor = max(0.5, 1.0 - (0.3 - weighted_accuracy) * 2.0)
        else:
            factor = 0.5 + (weighted_accuracy * (1.0 / 0.4))  # 0.3-0.7 범위를 0.5-1.0으로 매핑
        
        return round(factor, 3)
    
    def get_weight_adjustments(self) -> Dict[str, float]:
        """현재 가중치 조정 팩터 반환"""
        return {
            analyzer_name: performance.weight_adjustment_factor
            for analyzer_name, performance in self.analyzer_performances.items()
        }
    
    def get_analyzer_performance(self, analyzer_name: str) -> Optional[AnalyzerPerformance]:
        """특정 분석기 성과 조회"""
        return self.analyzer_performances.get(analyzer_name)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성과 요약 정보"""
        try:
            summary = {
                'total_analyzers': len(self.analyzer_performances),
                'total_predictions': sum(p.total_predictions for p in self.analyzer_performances.values()),
                'average_accuracy': np.mean([p.accuracy_rate for p in self.analyzer_performances.values()]),
                'best_performer': None,
                'worst_performer': None,
                'analyzer_details': {}
            }
            
            # 최고/최저 성과 분석기
            if self.analyzer_performances:
                best = max(self.analyzer_performances.values(), key=lambda x: x.accuracy_rate)
                worst = min(self.analyzer_performances.values(), key=lambda x: x.accuracy_rate)
                summary['best_performer'] = {
                    'name': best.analyzer_name,
                    'accuracy': best.accuracy_rate,
                    'weight_factor': best.weight_adjustment_factor
                }
                summary['worst_performer'] = {
                    'name': worst.analyzer_name,
                    'accuracy': worst.accuracy_rate,
                    'weight_factor': worst.weight_adjustment_factor
                }
            
            # 분석기별 세부 정보
            for name, performance in self.analyzer_performances.items():
                summary['analyzer_details'][name] = {
                    'accuracy_rate': performance.accuracy_rate,
                    'total_predictions': performance.total_predictions,
                    'weight_adjustment_factor': performance.weight_adjustment_factor,
                    'accuracy_7d': performance.accuracy_7d,
                    'high_confidence_accuracy': performance.high_confidence_accuracy
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ 성과 요약 생성 실패: {e}")
            return {}
    
    async def _save_prediction_to_db(self, record: PredictionRecord):
        """예측 기록을 데이터베이스에 저장 (옵션)"""
        try:
            # 실제 구현에서는 database_manager를 통해 저장
            # 현재는 로그만 출력
            self.logger.debug(f"💾 예측 기록 DB 저장: {record.prediction_id}")
        except Exception as e:
            self.logger.warning(f"⚠️ 예측 기록 DB 저장 실패: {e}")
    
    async def cleanup_old_records(self, days_to_keep: int = 90):
        """오래된 예측 기록 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            # 메모리에서 정리
            self.prediction_records = deque(
                [r for r in self.prediction_records if r.prediction_time > cutoff_time],
                maxlen=10000
            )
            
            self.logger.info(f"🧹 {days_to_keep}일 이전 예측 기록 정리 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 예측 기록 정리 실패: {e}")
    
    async def export_performance_data(self, filepath: str):
        """성과 데이터 내보내기"""
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'analyzer_performances': {
                    name: {
                        'accuracy_rate': perf.accuracy_rate,
                        'total_predictions': perf.total_predictions,
                        'weight_adjustment_factor': perf.weight_adjustment_factor,
                        'accuracy_1d': perf.accuracy_1d,
                        'accuracy_7d': perf.accuracy_7d,
                        'accuracy_30d': perf.accuracy_30d,
                        'last_updated': perf.last_updated.isoformat()
                    }
                    for name, perf in self.analyzer_performances.items()
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📤 성과 데이터 내보내기 완료: {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ 성과 데이터 내보내기 실패: {e}")