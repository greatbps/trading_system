#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/ai/online_learning_system.py

실시간 온라인 학습 시스템
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import asyncio
import threading
from collections import deque
import joblib
from pathlib import Path

try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

from .ensemble_predictor import EnsemblePredictor
from utils.logger import get_logger


class OnlineLearningSystem:
    """실시간 온라인 학습 시스템"""
    
    def __init__(self, config=None, db_manager=None):
        self.config = config
        self.db_manager = db_manager
        self.logger = get_logger("OnlineLearningSystem")
        
        if not HAS_TENSORFLOW:
            self.logger.warning("⚠️ TensorFlow가 설치되지 않았습니다. 온라인 학습을 사용할 수 없습니다.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # 앙상블 예측 모델
        self.ensemble_model = EnsemblePredictor(config)
        
        # 온라인 학습 설정
        self.learning_interval = 24 * 3600  # 24시간마다 재학습 (초)
        self.min_new_data_points = 50       # 최소 새 데이터 포인트 수
        self.max_training_data_days = 365   # 최대 학습 데이터 기간 (일)
        
        # 실시간 데이터 버퍼
        self.data_buffer = deque(maxlen=1000)  # 최대 1000개 데이터 포인트
        self.prediction_feedback = deque(maxlen=500)  # 예측 피드백 저장
        
        # 학습 스케줄링
        self.is_learning = False
        self.last_training_time = None
        self.training_thread = None
        self.stop_learning = False
        
        # 성능 모니터링
        self.performance_metrics = {
            'prediction_accuracy': deque(maxlen=100),
            'direction_accuracy': deque(maxlen=100),
            'confidence_scores': deque(maxlen=100),
            'learning_iterations': 0
        }
        
        # 모델 저장 경로
        self.model_dir = Path("models/online_learning")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("🔄 온라인 학습 시스템 초기화 완료")
    
    def start_online_learning(self):
        """온라인 학습 시작"""
        if not self.enabled:
            self.logger.warning("⚠️ 온라인 학습이 비활성화되어 있습니다")
            return False
            
        try:
            if self.is_learning:
                self.logger.warning("⚠️ 온라인 학습이 이미 실행 중입니다")
                return False
            
            self.stop_learning = False
            self.training_thread = threading.Thread(target=self._learning_loop, daemon=True)
            self.training_thread.start()
            
            self.logger.info("🚀 온라인 학습 시작")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 온라인 학습 시작 실패: {e}")
            return False
    
    def stop_online_learning(self):
        """온라인 학습 중지"""
        try:
            self.stop_learning = True
            
            if self.training_thread and self.training_thread.is_alive():
                self.training_thread.join(timeout=10)
            
            self.is_learning = False
            self.logger.info("🛑 온라인 학습 중지")
            
        except Exception as e:
            self.logger.error(f"❌ 온라인 학습 중지 실패: {e}")
    
    def _learning_loop(self):
        """학습 루프"""
        self.is_learning = True
        
        while not self.stop_learning:
            try:
                # 새 데이터 수집
                self._collect_new_data()
                
                # 학습 필요 여부 확인
                if self._should_retrain():
                    self._perform_incremental_learning()
                
                # 성능 평가
                self._evaluate_performance()
                
                # 학습 간격만큼 대기
                time.sleep(3600)  # 1시간마다 체크
                
            except Exception as e:
                self.logger.error(f"❌ 학습 루프 오류: {e}")
                time.sleep(3600)  # 오류 발생시 1시간 대기
        
        self.is_learning = False
    
    def _collect_new_data(self):
        """새로운 시장 데이터 수집"""
        try:
            if not self.db_manager:
                return
            
            # DB에서 최근 데이터 조회
            with self.db_manager.get_session() as session:
                # 최근 24시간 데이터 조회 (실제 구현에서는 적절한 쿼리 사용)
                cutoff_time = datetime.now() - timedelta(days=1)
                
                # 여기서는 임시로 빈 데이터 반환
                # 실제로는 주가 데이터 테이블에서 조회
                new_data_points = []
                
                if new_data_points:
                    self.data_buffer.extend(new_data_points)
                    self.logger.debug(f"📊 새 데이터 수집: {len(new_data_points)}개")
                
        except Exception as e:
            self.logger.error(f"❌ 새 데이터 수집 실패: {e}")
    
    def _should_retrain(self) -> bool:
        """재학습 필요 여부 판단"""
        try:
            # 1. 마지막 학습으로부터 충분한 시간이 경과했는가?
            if self.last_training_time:
                time_since_last = (datetime.now() - self.last_training_time).total_seconds()
                if time_since_last < self.learning_interval:
                    return False
            
            # 2. 충분한 새 데이터가 있는가?
            if len(self.data_buffer) < self.min_new_data_points:
                return False
            
            # 3. 성능 저하가 감지되었는가?
            if len(self.performance_metrics['prediction_accuracy']) >= 10:
                recent_accuracy = np.mean(list(self.performance_metrics['prediction_accuracy'])[-10:])
                if recent_accuracy < 0.6:  # 60% 미만이면 재학습
                    self.logger.info(f"📉 성능 저하 감지: {recent_accuracy:.1%}")
                    return True
            
            # 4. 정기 재학습 시간인가?
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 재학습 판단 오류: {e}")
            return False
    
    def _perform_incremental_learning(self):
        """점진적 학습 수행"""
        try:
            self.logger.info("🔄 점진적 학습 시작")
            
            # 학습 데이터 준비
            training_data = self._prepare_training_data()
            if training_data is None or len(training_data) < 100:
                self.logger.warning("⚠️ 학습 데이터 부족")
                return
            
            # 앙상블 모델 재학습
            training_result = self.ensemble_model.train_all_models(
                data=training_data,
                epochs=50,  # 온라인 학습은 적은 에포크
                batch_size=16
            )
            
            if 'error' not in training_result:
                self.last_training_time = datetime.now()
                self.performance_metrics['learning_iterations'] += 1
                
                # 학습 결과 로깅
                avg_r2 = training_result.get('avg_r2_score', 0)
                avg_direction_acc = training_result.get('avg_direction_accuracy', 0)
                
                self.logger.info(f"✅ 점진적 학습 완료")
                self.logger.info(f"📊 성능: R² {avg_r2:.4f}, 방향 정확도 {avg_direction_acc:.1%}")
                
                # 모델 저장
                self._save_learning_checkpoint()
                
            else:
                self.logger.error(f"❌ 점진적 학습 실패: {training_result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"❌ 점진적 학습 오류: {e}")
    
    def _prepare_training_data(self) -> Optional[pd.DataFrame]:
        """학습 데이터 준비"""
        try:
            if not self.db_manager:
                return None
            
            # 최근 N일간의 주가 데이터 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.max_training_data_days)
            
            # 실제 구현에서는 DB에서 주가 데이터 조회
            # 여기서는 임시 데이터 생성
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # 임시 주가 데이터 (실제로는 DB에서 조회)
            np.random.seed(42)
            base_price = 50000
            price_changes = np.random.normal(0, 0.02, len(dates))
            prices = [base_price]
            
            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(max(1000, new_price))  # 최소 1000원
            
            training_data = pd.DataFrame({
                'date': dates,
                'open': [p * np.random.uniform(0.98, 1.02) for p in prices],
                'high': [p * np.random.uniform(1.00, 1.05) for p in prices],
                'low': [p * np.random.uniform(0.95, 1.00) for p in prices],
                'close': prices,
                'volume': [np.random.randint(100000, 1000000) for _ in prices]
            })
            
            return training_data
            
        except Exception as e:
            self.logger.error(f"❌ 학습 데이터 준비 실패: {e}")
            return None
    
    def _evaluate_performance(self):
        """성능 평가"""
        try:
            if not self.prediction_feedback:
                return
            
            # 최근 예측들의 정확도 계산
            recent_predictions = list(self.prediction_feedback)[-20:]  # 최근 20개
            
            if len(recent_predictions) < 5:
                return
            
            accuracies = []
            direction_accuracies = []
            confidences = []
            
            for feedback in recent_predictions:
                if 'actual_price' in feedback and 'predicted_price' in feedback:
                    actual = feedback['actual_price']
                    predicted = feedback['predicted_price']
                    
                    # 가격 정확도 (MAPE 기반)
                    accuracy = 1 - abs(actual - predicted) / actual
                    accuracies.append(max(0, accuracy))
                    
                    # 방향 정확도
                    actual_direction = feedback.get('actual_direction', 0)
                    predicted_direction = feedback.get('predicted_direction', 0)
                    direction_match = (actual_direction * predicted_direction) > 0
                    direction_accuracies.append(1 if direction_match else 0)
                    
                    # 신뢰도
                    confidence = feedback.get('confidence', 0.8)
                    confidences.append(confidence)
            
            # 성능 메트릭 업데이트
            if accuracies:
                avg_accuracy = np.mean(accuracies)
                self.performance_metrics['prediction_accuracy'].append(avg_accuracy)
            
            if direction_accuracies:
                avg_direction_acc = np.mean(direction_accuracies)
                self.performance_metrics['direction_accuracy'].append(avg_direction_acc)
            
            if confidences:
                avg_confidence = np.mean(confidences)
                self.performance_metrics['confidence_scores'].append(avg_confidence)
            
            # 성능 로깅
            if len(self.performance_metrics['prediction_accuracy']) >= 5:
                recent_perf = np.mean(list(self.performance_metrics['prediction_accuracy'])[-5:])
                self.logger.debug(f"📊 최근 예측 정확도: {recent_perf:.1%}")
                
        except Exception as e:
            self.logger.error(f"❌ 성능 평가 오류: {e}")
    
    def add_prediction_feedback(self, prediction_data: Dict[str, Any], actual_data: Dict[str, Any]):
        """예측 피드백 추가"""
        try:
            feedback = {
                'timestamp': datetime.now().isoformat(),
                'predicted_price': prediction_data.get('predicted_price'),
                'predicted_direction': prediction_data.get('predicted_direction'),
                'confidence': prediction_data.get('confidence'),
                'actual_price': actual_data.get('actual_price'),
                'actual_direction': actual_data.get('actual_direction'),
                'symbol': prediction_data.get('symbol', 'UNKNOWN')
            }
            
            self.prediction_feedback.append(feedback)
            self.logger.debug(f"📝 예측 피드백 추가: {feedback['symbol']}")
            
        except Exception as e:
            self.logger.error(f"❌ 예측 피드백 추가 실패: {e}")
    
    def _save_learning_checkpoint(self):
        """학습 체크포인트 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_path = self.model_dir / f"online_learning_checkpoint_{timestamp}.pkl"
            
            checkpoint_data = {
                'last_training_time': self.last_training_time,
                'learning_iterations': self.performance_metrics['learning_iterations'],
                'performance_metrics': {
                    'prediction_accuracy': list(self.performance_metrics['prediction_accuracy']),
                    'direction_accuracy': list(self.performance_metrics['direction_accuracy']),
                    'confidence_scores': list(self.performance_metrics['confidence_scores'])
                },
                'model_weights': self.ensemble_model.model_weights.copy(),
                'saved_at': datetime.now().isoformat()
            }
            
            joblib.dump(checkpoint_data, checkpoint_path)
            self.logger.info(f"💾 학습 체크포인트 저장: {checkpoint_path}")
            
        except Exception as e:
            self.logger.error(f"❌ 체크포인트 저장 실패: {e}")
    
    def load_learning_checkpoint(self, checkpoint_path: str) -> bool:
        """학습 체크포인트 로드"""
        try:
            checkpoint_data = joblib.load(checkpoint_path)
            
            self.last_training_time = checkpoint_data.get('last_training_time')
            self.performance_metrics['learning_iterations'] = checkpoint_data.get('learning_iterations', 0)
            
            # 성능 메트릭 복원
            perf_data = checkpoint_data.get('performance_metrics', {})
            self.performance_metrics['prediction_accuracy'] = deque(
                perf_data.get('prediction_accuracy', []), maxlen=100
            )
            self.performance_metrics['direction_accuracy'] = deque(
                perf_data.get('direction_accuracy', []), maxlen=100
            )
            self.performance_metrics['confidence_scores'] = deque(
                perf_data.get('confidence_scores', []), maxlen=100
            )
            
            # 모델 가중치 복원
            if 'model_weights' in checkpoint_data:
                self.ensemble_model.model_weights = checkpoint_data['model_weights']
            
            self.logger.info(f"✅ 학습 체크포인트 로드: {checkpoint_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 체크포인트 로드 실패: {e}")
            return False
    
    def get_learning_status(self) -> Dict[str, Any]:
        """온라인 학습 상태 반환"""
        try:
            # 최근 성능 계산
            recent_accuracy = 0
            recent_direction_acc = 0
            recent_confidence = 0
            
            if self.performance_metrics['prediction_accuracy']:
                recent_accuracy = np.mean(list(self.performance_metrics['prediction_accuracy'])[-10:])
            
            if self.performance_metrics['direction_accuracy']:
                recent_direction_acc = np.mean(list(self.performance_metrics['direction_accuracy'])[-10:])
            
            if self.performance_metrics['confidence_scores']:
                recent_confidence = np.mean(list(self.performance_metrics['confidence_scores'])[-10:])
            
            # 다음 학습 시간 예측
            next_learning_time = None
            if self.last_training_time:
                next_learning_time = (self.last_training_time + timedelta(seconds=self.learning_interval)).isoformat()
            
            status = {
                'enabled': self.enabled,
                'is_learning': self.is_learning,
                'learning_iterations': self.performance_metrics['learning_iterations'],
                'last_training_time': self.last_training_time.isoformat() if self.last_training_time else None,
                'next_learning_time': next_learning_time,
                'data_buffer_size': len(self.data_buffer),
                'feedback_count': len(self.prediction_feedback),
                'recent_performance': {
                    'prediction_accuracy': float(recent_accuracy),
                    'direction_accuracy': float(recent_direction_acc),
                    'average_confidence': float(recent_confidence)
                },
                'ensemble_model_info': self.ensemble_model.get_model_info()
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ 학습 상태 조회 실패: {e}")
            return {'error': str(e)}