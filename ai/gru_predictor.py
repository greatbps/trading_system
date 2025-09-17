#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/ai/gru_predictor.py

GRU 기반 시계열 주가 예측 모델
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import joblib
import os
from pathlib import Path

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import GRU, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

from utils.logger import get_logger


class GRUPredictor:
    """GRU 기반 주가 예측 모델"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("GRUPredictor")
        
        if not HAS_TENSORFLOW:
            self.logger.warning("⚠️ TensorFlow가 설치되지 않았습니다. GRU 예측을 사용할 수 없습니다.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # 모델 설정
        self.sequence_length = 60  # 60일 시계열 데이터 사용
        self.prediction_days = 5   # 5일 후 예측
        self.features = [
            'close', 'volume', 'high', 'low', 'open',
            'rsi', 'macd', 'bb_upper', 'bb_lower', 'ema_20', 'ema_60'
        ]
        
        # 모델 컴포넌트
        self.model = None
        self.scaler = MinMaxScaler()
        self.feature_scaler = MinMaxScaler()
        
        # 성능 추적
        self.training_history = []
        self.prediction_accuracy = []
        
        # 모델 저장 경로
        self.model_dir = Path("models/gru")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("🧠 GRU 예측 모델 초기화 완료")
    
    def create_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """GRU 모델 생성"""
        if not self.enabled:
            raise RuntimeError("TensorFlow가 설치되지 않았습니다")
            
        model = Sequential([
            # 첫 번째 GRU 레이어
            GRU(units=128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            BatchNormalization(),
            
            # 두 번째 GRU 레이어  
            GRU(units=128, return_sequences=True),
            Dropout(0.2),
            BatchNormalization(),
            
            # 세 번째 GRU 레이어
            GRU(units=64, return_sequences=False),
            Dropout(0.2),
            BatchNormalization(),
            
            # Dense 레이어들
            Dense(units=50, activation='relu'),
            Dropout(0.2),
            Dense(units=25, activation='relu'),
            Dense(units=self.prediction_days, activation='linear')  # 5일 예측
        ])
        
        # 모델 컴파일
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae', 'mape']
        )
        
        return model
    
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """학습 데이터 준비"""
        # 기술적 지표 계산
        data = self._add_technical_indicators(data)
        
        # 특성 선택
        available_features = [col for col in self.features if col in data.columns]
        if len(available_features) < len(self.features):
            self.logger.warning(f"⚠️ 일부 특성이 누락됨: {set(self.features) - set(available_features)}")
        
        feature_data = data[available_features].fillna(method='ffill').fillna(method='bfill')
        target_data = data['close'].values
        
        # 정규화
        scaled_features = self.feature_scaler.fit_transform(feature_data)
        scaled_target = self.scaler.fit_transform(target_data.reshape(-1, 1)).flatten()
        
        # 시계열 데이터 생성
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_target) - self.prediction_days):
            # 60일간의 특성 데이터
            X.append(scaled_features[i-self.sequence_length:i])
            # 5일 후의 종가들 (1일, 2일, 3일, 4일, 5일 후)
            y.append(scaled_target[i+1:i+self.prediction_days+1])
        
        X = np.array(X)
        y = np.array(y)
        
        # 훈련/검증 분할 (80:20)
        split_idx = int(0.8 * len(X))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, X_test, y_train, y_test
    
    def train(self, data: pd.DataFrame, epochs: int = 100, batch_size: int = 32) -> Dict[str, Any]:
        """모델 학습"""
        if not self.enabled:
            return {"error": "TensorFlow not available"}
            
        try:
            self.logger.info(f"🎯 GRU 모델 학습 시작 - 데이터: {len(data)}개")
            
            # 데이터 준비
            X_train, X_test, y_train, y_test = self.prepare_data(data)
            
            # 모델 생성
            self.model = self.create_model((X_train.shape[1], X_train.shape[2]))
            
            # 콜백 설정
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=15,
                    restore_best_weights=True,
                    verbose=1
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=10,
                    min_lr=0.0001,
                    verbose=1
                )
            ]
            
            # 모델 학습
            history = self.model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(X_test, y_test),
                callbacks=callbacks,
                verbose=1,
                shuffle=True
            )
            
            # 성능 평가
            train_loss = self.model.evaluate(X_train, y_train, verbose=0)
            test_loss = self.model.evaluate(X_test, y_test, verbose=0)
            
            # 예측 성능 계산
            y_pred = self.model.predict(X_test)
            
            # 스케일 역변환
            y_test_original = self.scaler.inverse_transform(
                y_test.reshape(-1, self.prediction_days)
            )
            y_pred_original = self.scaler.inverse_transform(
                y_pred.reshape(-1, self.prediction_days)
            )
            
            # 성능 지표 계산
            mae = mean_absolute_error(y_test_original.flatten(), y_pred_original.flatten())
            mse = mean_squared_error(y_test_original.flatten(), y_pred_original.flatten())
            r2 = r2_score(y_test_original.flatten(), y_pred_original.flatten())
            
            # 방향 정확도 계산 (상승/하락 예측 정확도)
            direction_accuracy = self._calculate_direction_accuracy(
                y_test_original, y_pred_original
            )
            
            results = {
                "train_loss": float(train_loss[0]),
                "test_loss": float(test_loss[0]), 
                "mae": float(mae),
                "mse": float(mse),
                "rmse": float(np.sqrt(mse)),
                "r2_score": float(r2),
                "direction_accuracy": float(direction_accuracy),
                "epochs_completed": len(history.history['loss']),
                "training_time": datetime.now().isoformat()
            }
            
            self.training_history.append(results)
            
            # 모델 저장
            self.save_model()
            
            self.logger.info(f"✅ GRU 모델 학습 완료")
            self.logger.info(f"📊 성능: R² {r2:.4f}, 방향 정확도 {direction_accuracy:.1%}, RMSE {np.sqrt(mse):.2f}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ GRU 모델 학습 실패: {e}")
            return {"error": str(e)}
    
    def predict(self, data: pd.DataFrame, days: int = 5) -> Dict[str, Any]:
        """주가 예측"""
        if not self.enabled or self.model is None:
            return {"error": "Model not available"}
            
        try:
            # 최근 데이터로 예측 준비
            data = self._add_technical_indicators(data)
            available_features = [col for col in self.features if col in data.columns]
            feature_data = data[available_features].fillna(method='ffill').fillna(method='bfill')
            
            # 최근 sequence_length만큼의 데이터 사용
            recent_data = feature_data.tail(self.sequence_length)
            scaled_data = self.feature_scaler.transform(recent_data)
            
            # 예측을 위한 입력 형태 변환
            X_pred = scaled_data.reshape(1, self.sequence_length, len(available_features))
            
            # 예측 수행
            predictions = self.model.predict(X_pred, verbose=0)
            
            # 스케일 역변환
            predictions_original = self.scaler.inverse_transform(
                predictions.reshape(-1, self.prediction_days)
            ).flatten()
            
            current_price = float(data['close'].iloc[-1])
            
            # 예측 결과 구성
            results = {
                "current_price": current_price,
                "predictions": [],
                "confidence": self._calculate_prediction_confidence(predictions_original, current_price),
                "trend": "상승" if predictions_original[-1] > current_price else "하락",
                "prediction_horizon": f"{days}일",
                "model_type": "GRU",
                "timestamp": datetime.now().isoformat()
            }
            
            # 일별 예측 결과
            for i, pred_price in enumerate(predictions_original[:days]):
                change_rate = ((pred_price - current_price) / current_price) * 100
                results["predictions"].append({
                    "day": i + 1,
                    "predicted_price": float(pred_price),
                    "change_rate": float(change_rate),
                    "change_amount": float(pred_price - current_price)
                })
            
            self.logger.info(f"📈 GRU 예측 완료: {current_price:.0f} → {predictions_original[-1]:.0f} ({change_rate:+.1f}%)")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ GRU 예측 실패: {e}")
            return {"error": str(e)}
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 추가"""
        df = data.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        
        # Bollinger Bands
        rolling_mean = df['close'].rolling(window=20).mean()
        rolling_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = rolling_mean + (rolling_std * 2)
        df['bb_lower'] = rolling_mean - (rolling_std * 2)
        
        # EMA
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_60'] = df['close'].ewm(span=60).mean()
        
        return df
    
    def _calculate_direction_accuracy(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """방향 예측 정확도 계산"""
        # 첫 번째 날의 예측 방향만 평가 (단순화)
        true_direction = np.sign(y_true[:, 0] - y_true[:, -1])  # 실제 방향
        pred_direction = np.sign(y_pred[:, 0] - y_true[:, -1])  # 예측 방향
        
        accuracy = np.mean(true_direction == pred_direction)
        return accuracy
    
    def _calculate_prediction_confidence(self, predictions: np.ndarray, current_price: float) -> float:
        """예측 신뢰도 계산"""
        # 예측 가격들의 변동성을 기반으로 신뢰도 계산
        pred_volatility = np.std(predictions) / current_price
        
        # GRU는 LSTM보다 빠르지만 약간 낮은 신뢰도 (0.75 ~ 0.92 범위)
        confidence = max(0.5, min(0.92, 0.92 - pred_volatility * 10))
        return confidence
    
    def save_model(self) -> bool:
        """모델 저장"""
        if not self.enabled or self.model is None:
            return False
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = self.model_dir / f"gru_model_{timestamp}.h5"
            scaler_path = self.model_dir / f"gru_scalers_{timestamp}.pkl"
            
            # 모델 저장
            self.model.save(model_path)
            
            # 스케일러 저장
            scalers = {
                'scaler': self.scaler,
                'feature_scaler': self.feature_scaler,
                'features': self.features,
                'sequence_length': self.sequence_length,
                'prediction_days': self.prediction_days
            }
            joblib.dump(scalers, scaler_path)
            
            self.logger.info(f"💾 GRU 모델 저장 완료: {model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 모델 저장 실패: {e}")
            return False
    
    def load_model(self, model_path: str, scaler_path: str) -> bool:
        """저장된 모델 로드"""
        if not self.enabled:
            return False
            
        try:
            # 모델 로드
            self.model = load_model(model_path)
            
            # 스케일러 로드
            scalers = joblib.load(scaler_path)
            self.scaler = scalers['scaler']
            self.feature_scaler = scalers['feature_scaler']
            self.features = scalers['features']
            self.sequence_length = scalers['sequence_length']
            self.prediction_days = scalers['prediction_days']
            
            self.logger.info(f"✅ GRU 모델 로드 완료: {model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 모델 로드 실패: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        if not self.enabled:
            return {"error": "TensorFlow not available"}
            
        info = {
            "model_type": "GRU",
            "enabled": self.enabled,
            "sequence_length": self.sequence_length,
            "prediction_days": self.prediction_days,
            "features": self.features,
            "training_history_count": len(self.training_history)
        }
        
        if self.model:
            info["model_summary"] = {
                "total_params": self.model.count_params(),
                "layers": len(self.model.layers)
            }
            
        if self.training_history:
            latest = self.training_history[-1]
            info["latest_performance"] = {
                "r2_score": latest.get("r2_score"),
                "direction_accuracy": latest.get("direction_accuracy"),
                "rmse": latest.get("rmse")
            }
        
        return info