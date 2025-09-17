#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/ai/ensemble_predictor.py

앙상블 기반 주가 예측 모델 (LSTM + GRU + Transformer)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import joblib
from pathlib import Path

from .lstm_predictor import LSTMPredictor
from .gru_predictor import GRUPredictor
from .transformer_predictor import TransformerPredictor
from utils.logger import get_logger


class EnsemblePredictor:
    """앙상블 기반 주가 예측 모델"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("EnsemblePredictor")
        
        # 개별 예측 모델들
        self.lstm_model = LSTMPredictor(config)
        self.gru_model = GRUPredictor(config)
        self.transformer_model = TransformerPredictor(config)
        
        # 모델 가중치 (성능에 따라 동적 조정)
        self.model_weights = {
            'lstm': 0.35,      # LSTM 가중치
            'gru': 0.30,       # GRU 가중치  
            'transformer': 0.35 # Transformer 가중치
        }
        
        # 성능 추적
        self.training_history = []
        self.prediction_history = []
        
        # 모델 저장 경로
        self.model_dir = Path("models/ensemble")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # 활성 모델 확인
        self.active_models = []
        if self.lstm_model.enabled:
            self.active_models.append('lstm')
        if self.gru_model.enabled:
            self.active_models.append('gru')
        if self.transformer_model.enabled:
            self.active_models.append('transformer')
        
        if not self.active_models:
            self.logger.error("❌ 활성화된 모델이 없습니다. TensorFlow를 설치하세요.")
            self.enabled = False
        else:
            self.enabled = True
            self.logger.info(f"🤖 Ensemble 예측 모델 초기화 완료 - 활성 모델: {self.active_models}")
    
    def train_all_models(self, data: pd.DataFrame, epochs: int = 100, batch_size: int = 32) -> Dict[str, Any]:
        """모든 모델 학습"""
        if not self.enabled:
            return {"error": "No active models available"}
            
        try:
            self.logger.info(f"🎯 Ensemble 모델 학습 시작 - 데이터: {len(data)}개")
            
            results = {}
            training_start = datetime.now()
            
            # LSTM 모델 학습
            if 'lstm' in self.active_models:
                self.logger.info("📊 LSTM 모델 학습 중...")
                lstm_result = self.lstm_model.train(data, epochs, batch_size)
                results['lstm'] = lstm_result
            
            # GRU 모델 학습
            if 'gru' in self.active_models:
                self.logger.info("📊 GRU 모델 학습 중...")
                gru_result = self.gru_model.train(data, epochs, batch_size)
                results['gru'] = gru_result
            
            # Transformer 모델 학습
            if 'transformer' in self.active_models:
                self.logger.info("📊 Transformer 모델 학습 중...")
                transformer_result = self.transformer_model.train(data, epochs, batch_size)
                results['transformer'] = transformer_result
            
            training_end = datetime.now()
            training_duration = (training_end - training_start).total_seconds()
            
            # 모델 성능 기반 가중치 조정
            self._update_model_weights(results)
            
            # 앙상블 결과 생성
            ensemble_result = {
                "ensemble_training_time": training_duration,
                "active_models": self.active_models,
                "model_weights": self.model_weights.copy(),
                "individual_results": results,
                "training_completed_at": training_end.isoformat()
            }
            
            # 성능 메트릭 평균 계산
            performance_metrics = ['r2_score', 'direction_accuracy', 'rmse', 'mae']
            for metric in performance_metrics:
                values = []
                for model_name in self.active_models:
                    if model_name in results and metric in results[model_name]:
                        values.append(results[model_name][metric])
                if values:
                    ensemble_result[f"avg_{metric}"] = sum(values) / len(values)
            
            self.training_history.append(ensemble_result)
            
            # 모델 가중치 저장
            self.save_weights()
            
            self.logger.info("✅ Ensemble 모델 학습 완료")
            self.logger.info(f"📊 가중치: LSTM({self.model_weights['lstm']:.2f}), GRU({self.model_weights['gru']:.2f}), Transformer({self.model_weights['transformer']:.2f})")
            
            return ensemble_result
            
        except Exception as e:
            self.logger.error(f"❌ Ensemble 모델 학습 실패: {e}")
            return {"error": str(e)}
    
    def predict(self, data: pd.DataFrame, days: int = 5) -> Dict[str, Any]:
        """앙상블 예측 수행"""
        if not self.enabled:
            return {"error": "No active models available"}
            
        try:
            self.logger.info("🔮 Ensemble 예측 시작")
            
            predictions = {}
            valid_predictions = []
            model_confidences = []
            
            # 개별 모델 예측 수행
            if 'lstm' in self.active_models and self.lstm_model.model is not None:
                lstm_pred = self.lstm_model.predict(data, days)
                if 'error' not in lstm_pred:
                    predictions['lstm'] = lstm_pred
                    valid_predictions.append(('lstm', lstm_pred))
                    model_confidences.append(lstm_pred.get('confidence', 0.8))
            
            if 'gru' in self.active_models and self.gru_model.model is not None:
                gru_pred = self.gru_model.predict(data, days)
                if 'error' not in gru_pred:
                    predictions['gru'] = gru_pred
                    valid_predictions.append(('gru', gru_pred))
                    model_confidences.append(gru_pred.get('confidence', 0.75))
            
            if 'transformer' in self.active_models and self.transformer_model.model is not None:
                transformer_pred = self.transformer_model.predict(data, days)
                if 'error' not in transformer_pred:
                    predictions['transformer'] = transformer_pred
                    valid_predictions.append(('transformer', transformer_pred))
                    model_confidences.append(transformer_pred.get('confidence', 0.85))
            
            if not valid_predictions:
                return {"error": "No valid predictions available"}
            
            # 앙상블 예측 계산
            ensemble_result = self._calculate_ensemble_prediction(valid_predictions, data, days)
            ensemble_result["individual_predictions"] = predictions
            
            # 예측 이력 저장
            self.prediction_history.append({
                "timestamp": datetime.now().isoformat(),
                "ensemble_prediction": ensemble_result,
                "individual_predictions": predictions
            })
            
            self.logger.info(f"✅ Ensemble 예측 완료 - 신뢰도: {ensemble_result.get('confidence', 0):.1%}")
            
            return ensemble_result
            
        except Exception as e:
            self.logger.error(f"❌ Ensemble 예측 실패: {e}")
            return {"error": str(e)}
    
    def _calculate_ensemble_prediction(self, valid_predictions: List[Tuple], data: pd.DataFrame, days: int) -> Dict[str, Any]:
        """앙상블 예측 계산"""
        current_price = float(data['close'].iloc[-1])
        
        # 가중 평균으로 앙상블 예측 계산
        ensemble_predictions = []
        total_weight = 0
        individual_confidences = []
        
        for day in range(days):
            weighted_sum = 0
            weight_sum = 0
            
            for model_name, prediction in valid_predictions:
                if day < len(prediction['predictions']):
                    pred_price = prediction['predictions'][day]['predicted_price']
                    model_weight = self.model_weights.get(model_name, 0.33)
                    model_confidence = prediction.get('confidence', 0.8)
                    
                    # 가중치 = 모델 가중치 × 모델 신뢰도
                    combined_weight = model_weight * model_confidence
                    
                    weighted_sum += pred_price * combined_weight
                    weight_sum += combined_weight
            
            if weight_sum > 0:
                ensemble_pred_price = weighted_sum / weight_sum
                change_rate = ((ensemble_pred_price - current_price) / current_price) * 100
                
                ensemble_predictions.append({
                    "day": day + 1,
                    "predicted_price": float(ensemble_pred_price),
                    "change_rate": float(change_rate),
                    "change_amount": float(ensemble_pred_price - current_price)
                })
        
        # 앙상블 신뢰도 계산 (개별 모델 신뢰도의 가중 평균)
        ensemble_confidence = 0
        confidence_weight_sum = 0
        
        for model_name, prediction in valid_predictions:
            model_weight = self.model_weights.get(model_name, 0.33)
            model_confidence = prediction.get('confidence', 0.8)
            ensemble_confidence += model_confidence * model_weight
            confidence_weight_sum += model_weight
        
        if confidence_weight_sum > 0:
            ensemble_confidence = ensemble_confidence / confidence_weight_sum
        
        # 최종 예측 방향 결정
        final_price = ensemble_predictions[-1]['predicted_price'] if ensemble_predictions else current_price
        trend = "상승" if final_price > current_price else "하락"
        
        # 예측 불일치도 계산 (모델간 예측 차이)
        prediction_variance = self._calculate_prediction_variance(valid_predictions, days)
        
        # 불일치도가 높으면 신뢰도 조정
        if prediction_variance > 0.05:  # 5% 이상 차이
            ensemble_confidence *= (1 - prediction_variance)
        
        result = {
            "current_price": current_price,
            "predictions": ensemble_predictions,
            "confidence": float(ensemble_confidence),
            "trend": trend,
            "prediction_horizon": f"{days}일",
            "model_type": "Ensemble",
            "active_models": self.active_models,
            "model_weights": self.model_weights.copy(),
            "prediction_variance": float(prediction_variance),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _calculate_prediction_variance(self, valid_predictions: List[Tuple], days: int) -> float:
        """예측간 분산 계산"""
        if len(valid_predictions) < 2:
            return 0.0
        
        variances = []
        
        for day in range(days):
            day_predictions = []
            
            for model_name, prediction in valid_predictions:
                if day < len(prediction['predictions']):
                    day_predictions.append(prediction['predictions'][day]['predicted_price'])
            
            if len(day_predictions) >= 2:
                variance = np.var(day_predictions) / np.mean(day_predictions)
                variances.append(variance)
        
        return np.mean(variances) if variances else 0.0
    
    def _update_model_weights(self, training_results: Dict[str, Any]) -> None:
        """학습 결과를 바탕으로 모델 가중치 업데이트"""
        try:
            # 성능 점수 계산 (R² score + direction accuracy)
            model_scores = {}
            
            for model_name in self.active_models:
                if model_name in training_results:
                    result = training_results[model_name]
                    r2_score = result.get('r2_score', 0)
                    direction_acc = result.get('direction_accuracy', 0.5)
                    
                    # 복합 점수 계산 (R² 60% + 방향 정확도 40%)
                    composite_score = (r2_score * 0.6) + (direction_acc * 0.4)
                    model_scores[model_name] = max(0.1, composite_score)  # 최소 0.1
            
            if not model_scores:
                return
            
            # 점수 기반 가중치 계산
            total_score = sum(model_scores.values())
            
            for model_name in self.active_models:
                if model_name in model_scores:
                    # 점수 비율로 가중치 계산 (최소 0.1, 최대 0.6)
                    raw_weight = model_scores[model_name] / total_score
                    self.model_weights[model_name] = max(0.1, min(0.6, raw_weight))
            
            # 가중치 정규화 (합이 1이 되도록)
            total_weight = sum(self.model_weights[m] for m in self.active_models)
            for model_name in self.active_models:
                self.model_weights[model_name] /= total_weight
                
            self.logger.info(f"📊 모델 가중치 업데이트: {self.model_weights}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ 가중치 업데이트 실패: {e}")
    
    def save_weights(self) -> bool:
        """모델 가중치 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            weights_path = self.model_dir / f"ensemble_weights_{timestamp}.pkl"
            
            weights_data = {
                'model_weights': self.model_weights,
                'active_models': self.active_models,
                'training_history': self.training_history[-5:],  # 최근 5개만
                'saved_at': datetime.now().isoformat()
            }
            
            joblib.dump(weights_data, weights_path)
            self.logger.info(f"💾 Ensemble 가중치 저장 완료: {weights_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 가중치 저장 실패: {e}")
            return False
    
    def load_weights(self, weights_path: str) -> bool:
        """저장된 가중치 로드"""
        try:
            weights_data = joblib.load(weights_path)
            
            self.model_weights = weights_data.get('model_weights', self.model_weights)
            loaded_active_models = weights_data.get('active_models', [])
            
            # 현재 활성 모델과 로드된 모델 교집합만 사용
            self.active_models = [m for m in loaded_active_models if m in self.active_models]
            
            if 'training_history' in weights_data:
                self.training_history.extend(weights_data['training_history'])
            
            self.logger.info(f"✅ Ensemble 가중치 로드 완료: {weights_path}")
            self.logger.info(f"📊 로드된 가중치: {self.model_weights}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 가중치 로드 실패: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        info = {
            "model_type": "Ensemble",
            "enabled": self.enabled,
            "active_models": self.active_models,
            "model_weights": self.model_weights.copy(),
            "training_history_count": len(self.training_history),
            "prediction_history_count": len(self.prediction_history)
        }
        
        # 개별 모델 정보
        if 'lstm' in self.active_models:
            info['lstm_info'] = self.lstm_model.get_model_info()
        if 'gru' in self.active_models:
            info['gru_info'] = self.gru_model.get_model_info()
        if 'transformer' in self.active_models:
            info['transformer_info'] = self.transformer_model.get_model_info()
        
        # 최근 성능 정보
        if self.training_history:
            latest = self.training_history[-1]
            info["latest_ensemble_performance"] = {
                "avg_r2_score": latest.get("avg_r2_score"),
                "avg_direction_accuracy": latest.get("avg_direction_accuracy"),
                "avg_rmse": latest.get("avg_rmse"),
                "training_completed_at": latest.get("training_completed_at")
            }
        
        return info