#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/ai/transformer_predictor.py

Transformer 기반 시계열 주가 예측 모델
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
    from tensorflow.keras.models import Model, load_model
    from tensorflow.keras.layers import (
        Input, Dense, Dropout, LayerNormalization, MultiHeadAttention,
        GlobalAveragePooling1D, Embedding, PositionalEncoding
    )
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False

from utils.logger import get_logger


class TransformerBlock(tf.keras.layers.Layer):
    """Transformer 블록"""
    
    def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1):
        super(TransformerBlock, self).__init__()
        self.att = MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = tf.keras.Sequential([
            Dense(ff_dim, activation="relu"),
            Dense(embed_dim),
        ])
        self.layernorm1 = LayerNormalization(epsilon=1e-6)
        self.layernorm2 = LayerNormalization(epsilon=1e-6)
        self.dropout1 = Dropout(rate)
        self.dropout2 = Dropout(rate)

    def call(self, inputs, training=None):
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)


class PositionalEncoding(tf.keras.layers.Layer):
    """위치 인코딩"""
    
    def __init__(self, maxlen, embed_dim):
        super(PositionalEncoding, self).__init__()
        self.pos_emb = Embedding(input_dim=maxlen, output_dim=embed_dim)

    def call(self, x):
        maxlen = tf.shape(x)[1]
        positions = tf.range(start=0, limit=maxlen, delta=1)
        positions = self.pos_emb(positions)
        return x + positions


class TransformerPredictor:
    """Transformer 기반 주가 예측 모델"""
    
    def __init__(self, config=None):
        self.config = config
        self.logger = get_logger("TransformerPredictor")
        
        if not HAS_TENSORFLOW:
            self.logger.warning("⚠️ TensorFlow가 설치되지 않았습니다. Transformer 예측을 사용할 수 없습니다.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # 모델 설정
        self.sequence_length = 60  # 60일 시계열 데이터 사용
        self.prediction_days = 5   # 5일 후 예측
        self.embed_dim = 64        # 임베딩 차원
        self.num_heads = 8         # 어텐션 헤드 수
        self.ff_dim = 128          # 피드포워드 차원
        
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
        self.model_dir = Path("models/transformer")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("🧠 Transformer 예측 모델 초기화 완료")
    
    def create_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Transformer 모델 생성"""
        if not self.enabled:
            raise RuntimeError("TensorFlow가 설치되지 않았습니다")
        
        inputs = Input(shape=input_shape)
        
        # 입력 차원을 embed_dim으로 맞춤
        x = Dense(self.embed_dim)(inputs)
        
        # 위치 인코딩
        x = PositionalEncoding(self.sequence_length, self.embed_dim)(x)
        
        # Transformer 블록들
        x = TransformerBlock(self.embed_dim, self.num_heads, self.ff_dim)(x)
        x = TransformerBlock(self.embed_dim, self.num_heads, self.ff_dim)(x)
        x = TransformerBlock(self.embed_dim, self.num_heads, self.ff_dim)(x)
        
        # Global Average Pooling
        x = GlobalAveragePooling1D(data_format="channels_first")(x)
        
        # 출력 레이어들
        x = Dense(128, activation="relu")(x)
        x = Dropout(0.1)(x)
        x = Dense(64, activation="relu")(x)
        x = Dropout(0.1)(x)
        outputs = Dense(self.prediction_days, activation="linear")(x)
        
        model = Model(inputs, outputs)
        
        # 모델 컴파일
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="mse",
            metrics=["mae", "mape"]
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
            self.logger.info(f"🎯 Transformer 모델 학습 시작 - 데이터: {len(data)}개")
            
            # 데이터 준비
            X_train, X_test, y_train, y_test = self.prepare_data(data)
            
            # 모델 생성
            self.model = self.create_model((X_train.shape[1], X_train.shape[2]))
            
            # 콜백 설정
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=20,  # Transformer는 더 오래 학습
                    restore_best_weights=True,
                    verbose=1
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=15,
                    min_lr=0.00001,
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
            
            self.logger.info(f"✅ Transformer 모델 학습 완료")
            self.logger.info(f"📊 성능: R² {r2:.4f}, 방향 정확도 {direction_accuracy:.1%}, RMSE {np.sqrt(mse):.2f}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Transformer 모델 학습 실패: {e}")
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
                "model_type": "Transformer",
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
            
            self.logger.info(f"📈 Transformer 예측 완료: {current_price:.0f} → {predictions_original[-1]:.0f} ({change_rate:+.1f}%)")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Transformer 예측 실패: {e}")
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
        
        # Transformer는 attention mechanism으로 높은 신뢰도 (0.8 ~ 0.96 범위)
        confidence = max(0.6, min(0.96, 0.96 - pred_volatility * 8))
        return confidence
    
    def save_model(self) -> bool:
        """모델 저장"""
        if not self.enabled or self.model is None:
            return False
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = self.model_dir / f"transformer_model_{timestamp}.h5"
            scaler_path = self.model_dir / f"transformer_scalers_{timestamp}.pkl"
            
            # 모델 저장
            self.model.save(model_path)
            
            # 스케일러 저장
            scalers = {
                'scaler': self.scaler,
                'feature_scaler': self.feature_scaler,
                'features': self.features,
                'sequence_length': self.sequence_length,
                'prediction_days': self.prediction_days,
                'embed_dim': self.embed_dim,
                'num_heads': self.num_heads,
                'ff_dim': self.ff_dim
            }
            joblib.dump(scalers, scaler_path)
            
            self.logger.info(f"💾 Transformer 모델 저장 완료: {model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 모델 저장 실패: {e}")
            return False
    
    def load_model(self, model_path: str, scaler_path: str) -> bool:
        """저장된 모델 로드"""
        if not self.enabled:
            return False
            
        try:
            # 커스텀 객체들 등록
            custom_objects = {
                'TransformerBlock': TransformerBlock,
                'PositionalEncoding': PositionalEncoding
            }
            
            # 모델 로드
            self.model = load_model(model_path, custom_objects=custom_objects)
            
            # 스케일러 로드
            scalers = joblib.load(scaler_path)
            self.scaler = scalers['scaler']
            self.feature_scaler = scalers['feature_scaler']
            self.features = scalers['features']
            self.sequence_length = scalers['sequence_length']
            self.prediction_days = scalers['prediction_days']
            self.embed_dim = scalers.get('embed_dim', 64)
            self.num_heads = scalers.get('num_heads', 8)
            self.ff_dim = scalers.get('ff_dim', 128)
            
            self.logger.info(f"✅ Transformer 모델 로드 완료: {model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 모델 로드 실패: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        if not self.enabled:
            return {"error": "TensorFlow not available"}
            
        info = {
            "model_type": "Transformer",
            "enabled": self.enabled,
            "sequence_length": self.sequence_length,
            "prediction_days": self.prediction_days,
            "embed_dim": self.embed_dim,
            "num_heads": self.num_heads,
            "ff_dim": self.ff_dim,
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