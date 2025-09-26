#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/ai_momentum_strategy.py

AI 기반 고급 모멘텀 전략 - Phase 8+ 신규 전략
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from strategies.base_strategy import BaseStrategy, Signal, SignalType
from utils.logger import get_logger


@dataclass
class AISignal:
    """AI 신호 데이터 클래스"""
    signal_type: str  # MOMENTUM_STRONG, MOMENTUM_WEAK, REVERSAL, NEUTRAL
    confidence: float  # 0.0 - 1.0
    predicted_direction: str  # UP, DOWN, SIDEWAYS
    expected_return: float  # 예상 수익률
    risk_level: str  # LOW, MEDIUM, HIGH
    timeframe: str  # 1H, 4H, 1D
    generated_at: datetime


@dataclass
class MarketRegimeSignal:
    """시장 체제 신호"""
    regime: str  # BULL, BEAR, SIDEWAYS, HIGH_VOLATILITY
    strength: float  # 0.0 - 1.0
    transition_probability: float  # 체제 전환 확률
    recommended_exposure: float  # 권장 노출도 (0.0 - 1.0)


class AIMomentumStrategy(BaseStrategy):
    """AI 기반 고급 모멘텀 전략"""
    
    def __init__(self, config, data_collector, ai_controller=None):
        super().__init__(config)
        self.ai_controller = ai_controller
        self.logger = get_logger(f"AIMomentumStrategy")
        
        # 전략 파라미터
        self.momentum_period = config.get('ai_momentum', {}).get('momentum_period', 14)
        self.ai_confidence_threshold = config.get('ai_momentum', {}).get('ai_confidence_threshold', 0.7)
        self.risk_adjustment_factor = config.get('ai_momentum', {}).get('risk_adjustment_factor', 0.5)
        self.max_position_size = config.get('ai_momentum', {}).get('max_position_size', 0.1)
        self.stop_loss_multiplier = config.get('ai_momentum', {}).get('stop_loss_multiplier', 2.0)
        
        # 다중 시간대 분석
        self.timeframes = ['1H', '4H', '1D']
        self.timeframe_weights = {'1H': 0.2, '4H': 0.3, '1D': 0.5}
        
        # AI 신호 저장
        self.ai_signals_cache = {}
        self.market_regime_cache = None
        self.last_ai_analysis = None
        
        self.logger.info("🚀 AI 기반 고급 모멘텀 전략 초기화 완료")
    
    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """매매 신호 생성 (추상 메서드 구현) - BaseStrategy의 generate_signals를 구현"""
        # StockData 객체 또는 dict에서 안전하게 symbol을 가져옴
        if hasattr(stock_data, 'symbol'):
            symbol = stock_data.symbol
        elif isinstance(stock_data, dict):
            symbol = stock_data.get('symbol')
        else:
            symbol = None
        if not symbol:
            self.logger.error("Symbol not found in stock_data for generate_signals.")
            return {"signal_type": SignalType.HOLD.value, "confidence": 0.0, "metadata": {"error": "Symbol missing"}}

        # analyze 메서드는 symbol과 timeframe을 받으므로, 여기서는 기본 timeframe을 사용
        # analyze 메서드가 stock_data를 직접 처리하도록 수정하거나,
        # stock_data에서 필요한 정보를 추출하여 analyze에 전달해야 함.
        # 현재 analyze는 price_data를 내부적으로 수집하므로, symbol만 전달.
        signal = await self.analyze(symbol) 

        # Signal 객체를 BaseStrategy의 generate_signals가 기대하는 딕셔너리 형태로 변환
        return {
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence,
            "metadata": signal.metadata
        }
    
    async def analyze(self, symbol: str, timeframe: str = '1D') -> Signal:
        """메인 분석 로직"""
        try:
            self.logger.debug(f"🔍 {symbol} AI 모멘텀 분석 시작 ({timeframe})")
            
            # 1. 기본 가격 데이터 수집
            price_data = await self.data_collector.get_historical_data(
                symbol, period='3M', interval=timeframe
            )
            
            if not price_data or len(price_data) < self.momentum_period + 10:
                self.logger.warning(f"⚠️ {symbol} 데이터 부족")
                return Signal(SignalType.HOLD, 0.0, {})
            
            # 2. AI 신호 생성 및 수집
            ai_signals = await self._generate_ai_signals(symbol, price_data, timeframe)
            
            # 3. 시장 체제 분석
            market_regime = await self._analyze_market_regime(symbol, price_data)
            
            # 4. 다중 시간대 모멘텀 분석
            multi_timeframe_signals = await self._multi_timeframe_analysis(symbol)
            
            # 5. 기술적 모멘텀 지표 계산
            technical_signals = await self._calculate_technical_momentum(price_data)
            
            # 6. AI + 기술적 신호 융합
            composite_signal = await self._fuse_signals(
                ai_signals, technical_signals, multi_timeframe_signals, market_regime
            )
            
            # 7. 리스크 조정된 최종 신호 생성
            final_signal = await self._apply_risk_management(
                composite_signal, symbol, market_regime
            )
            
            self.logger.info(f"✅ {symbol} AI 모멘텀 분석 완료: {final_signal.signal_type.name} (신뢰도: {final_signal.confidence:.2f})")
            
            return final_signal
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} AI 모멘텀 분석 실패: {e}")
            return Signal(SignalType.HOLD, 0.0, {'error': str(e)})
    
    async def _generate_ai_signals(self, symbol: str, price_data: List[Dict], timeframe: str) -> List[AISignal]:
        """AI 기반 신호 생성"""
        try:
            ai_signals = []
            
            if not self.ai_controller:
                self.logger.warning("⚠️ AI 컨트롤러 없음, 기본 신호 사용")
                return self._generate_fallback_signals(price_data, timeframe)
            
            # AI 예측 모델 실행
            try:
                # 현재 가격과 기술적 지표를 AI 모델에 입력
                current_price = price_data[-1]['close']
                prices = [float(item['close']) for item in price_data[-30:]]
                volumes = [float(item['volume']) for item in price_data[-30:]]
                
                # AI 예측 요청
                prediction_result = await self.ai_controller.predictor.predict_price_movement(
                    symbol, prices, volumes, timeframe
                )
                
                if prediction_result and prediction_result.confidence > 0.5:
                    ai_signal = AISignal(
                        signal_type=self._map_prediction_to_signal(prediction_result.direction, prediction_result.confidence),
                        confidence=prediction_result.confidence,
                        predicted_direction=prediction_result.direction,
                        expected_return=prediction_result.expected_return,
                        risk_level=prediction_result.risk_level,
                        timeframe=timeframe,
                        generated_at=datetime.now()
                    )
                    ai_signals.append(ai_signal)
                    
                    self.logger.debug(f"🤖 AI 신호: {ai_signal.signal_type} (신뢰도: {ai_signal.confidence:.2f})")
                
            except Exception as e:
                self.logger.warning(f"⚠️ AI 예측 실패: {e}, 폴백 신호 사용")
                return self._generate_fallback_signals(price_data, timeframe)
            
            # 캐시에 저장
            self.ai_signals_cache[f"{symbol}_{timeframe}"] = ai_signals
            
            return ai_signals
            
        except Exception as e:
            self.logger.error(f"❌ AI 신호 생성 실패: {e}")
            return self._generate_fallback_signals(price_data, timeframe)
    
    async def _analyze_market_regime(self, symbol: str, price_data: List[Dict]) -> MarketRegimeSignal:
        """시장 체제 분석"""
        try:
            if not self.ai_controller or not hasattr(self.ai_controller, 'regime_detector'):
                return self._generate_fallback_regime(price_data)
            
            # 시장 데이터 준비
            market_data = [
                {
                    'symbol': symbol,
                    'price': item['close'],
                    'change_rate': item.get('change_rate', 0),
                    'volume': item['volume']
                }
                for item in price_data[-50:]  # 최근 50일 데이터
            ]
            
            # AI 체제 감지
            regime_result = await self.ai_controller.regime_detector.detect_current_regime(
                market_data, [{'symbol': symbol, 'name': symbol}]
            )
            
            market_regime = MarketRegimeSignal(
                regime=regime_result.regime_type,
                strength=regime_result.confidence / 100.0,
                transition_probability=0.3,  # 기본값
                recommended_exposure=self._calculate_exposure_from_regime(regime_result.regime_type)
            )
            
            self.market_regime_cache = market_regime
            return market_regime
            
        except Exception as e:
            self.logger.warning(f"⚠️ 시장 체제 분석 실패: {e}")
            return self._generate_fallback_regime(price_data)
    
    async def _multi_timeframe_analysis(self, symbol: str) -> Dict[str, float]:
        """다중 시간대 분석"""
        try:
            timeframe_scores = {}
            
            for tf in self.timeframes:
                try:
                    # 각 시간대별 모멘텀 점수 계산
                    tf_data = await self.data_collector.get_historical_data(
                        symbol, period='1M', interval=tf
                    )
                    
                    if tf_data and len(tf_data) >= self.momentum_period:
                        momentum_score = self._calculate_momentum_score(tf_data)
                        timeframe_scores[tf] = momentum_score
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ {tf} 시간대 분석 실패: {e}")
                    timeframe_scores[tf] = 0.0
            
            return timeframe_scores
            
        except Exception as e:
            self.logger.error(f"❌ 다중 시간대 분석 실패: {e}")
            return {tf: 0.0 for tf in self.timeframes}
    
    async def _calculate_technical_momentum(self, price_data: List[Dict]) -> Dict[str, float]:
        """기술적 모멘텀 지표 계산"""
        try:
            closes = np.array([float(item['close']) for item in price_data])
            volumes = np.array([float(item['volume']) for item in price_data])
            
            # RSI 계산
            rsi = self._calculate_rsi(closes, 14)
            
            # MACD 계산
            macd_line, macd_signal, macd_histogram = self._calculate_macd(closes)
            
            # 볼린저 밴드
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes, 20)
            
            # 거래량 가중 평균가격 (VWAP)
            vwap = self._calculate_vwap(closes, volumes)
            
            # 모멘텀 점수 종합
            momentum_signals = {
                'rsi_momentum': self._rsi_momentum_score(rsi[-1]),
                'macd_momentum': self._macd_momentum_score(macd_line[-1], macd_signal[-1], macd_histogram[-1]),
                'bb_momentum': self._bb_momentum_score(closes[-1], bb_upper[-1], bb_middle[-1], bb_lower[-1]),
                'vwap_momentum': self._vwap_momentum_score(closes[-1], vwap[-1]),
                'price_momentum': self._price_momentum_score(closes)
            }
            
            return momentum_signals
            
        except Exception as e:
            self.logger.error(f"❌ 기술적 모멘텀 계산 실패: {e}")
            return {'momentum_score': 0.0}
    
    async def _fuse_signals(self, ai_signals: List[AISignal], technical_signals: Dict, 
                          multi_tf_signals: Dict, market_regime: MarketRegimeSignal) -> Dict[str, Any]:
        """신호 융합"""
        try:
            # AI 신호 가중 평균
            ai_score = 0.0
            ai_confidence = 0.0
            if ai_signals:
                for signal in ai_signals:
                    weight = signal.confidence
                    direction_score = 1.0 if signal.predicted_direction == 'UP' else -1.0 if signal.predicted_direction == 'DOWN' else 0.0
                    ai_score += direction_score * weight
                    ai_confidence += signal.confidence
                ai_score /= len(ai_signals)
                ai_confidence /= len(ai_signals)
            
            # 기술적 신호 가중 평균
            technical_score = np.mean(list(technical_signals.values()))
            
            # 다중 시간대 신호 가중 평균
            multi_tf_score = sum(score * self.timeframe_weights[tf] for tf, score in multi_tf_signals.items())
            
            # 시장 체제 조정
            regime_multiplier = self._get_regime_multiplier(market_regime.regime)
            
            # 최종 신호 융합
            final_score = (
                ai_score * 0.4 +
                technical_score * 0.3 +
                multi_tf_score * 0.3
            ) * regime_multiplier
            
            final_confidence = (ai_confidence * 0.5 + abs(technical_score) * 0.3 + abs(multi_tf_score) * 0.2)
            
            return {
                'score': final_score,
                'confidence': min(final_confidence, 1.0),
                'ai_contribution': ai_score,
                'technical_contribution': technical_score,
                'multi_tf_contribution': multi_tf_score,
                'regime_adjustment': regime_multiplier
            }
            
        except Exception as e:
            self.logger.error(f"❌ 신호 융합 실패: {e}")
            return {'score': 0.0, 'confidence': 0.0}
    
    async def _apply_risk_management(self, composite_signal: Dict, symbol: str, 
                                   market_regime: MarketRegimeSignal) -> Signal:
        """리스크 관리 적용"""
        try:
            score = composite_signal.get('score', 0.0)
            confidence = composite_signal.get('confidence', 0.0)
            
            # 신뢰도 임계값 체크
            if confidence < self.ai_confidence_threshold:
                return Signal(SignalType.HOLD, confidence, composite_signal)
            
            # 시장 체제에 따른 포지션 크기 조정
            base_position_size = min(self.max_position_size, confidence * self.max_position_size)
            adjusted_position_size = base_position_size * market_regime.recommended_exposure
            
            # 신호 유형 결정
            if score > 0.3 and confidence > self.ai_confidence_threshold:
                signal_type = SignalType.BUY
            elif score < -0.3 and confidence > self.ai_confidence_threshold:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            # 추가 메타데이터
            metadata = {
                **composite_signal,
                'position_size': adjusted_position_size,
                'market_regime': market_regime.regime,
                'regime_strength': market_regime.strength,
                'stop_loss_multiplier': self.stop_loss_multiplier,
                'strategy_type': 'ai_momentum'
            }
            
            return Signal(signal_type, confidence, metadata)
            
        except Exception as e:
            self.logger.error(f"❌ 리스크 관리 적용 실패: {e}")
            return Signal(SignalType.HOLD, 0.0, {'error': str(e)})
    
    # 헬퍼 메서드들
    def _map_prediction_to_signal(self, direction: str, confidence: float) -> str:
        """AI 예측을 신호로 매핑"""
        if confidence > 0.8:
            return f"MOMENTUM_STRONG_{direction}"
        elif confidence > 0.6:
            return f"MOMENTUM_WEAK_{direction}"
        else:
            return "NEUTRAL"
    
    def _generate_fallback_signals(self, price_data: List[Dict], timeframe: str) -> List[AISignal]:
        """AI 없을 때 폴백 신호"""
        closes = [float(item['close']) for item in price_data[-20:]]
        momentum = (closes[-1] - closes[-10]) / closes[-10]
        
        if momentum > 0.02:
            signal_type = "MOMENTUM_WEAK_UP"
            direction = "UP"
        elif momentum < -0.02:
            signal_type = "MOMENTUM_WEAK_DOWN"
            direction = "DOWN"
        else:
            signal_type = "NEUTRAL"
            direction = "SIDEWAYS"
        
        return [AISignal(
            signal_type=signal_type,
            confidence=min(abs(momentum) * 10, 0.7),
            predicted_direction=direction,
            expected_return=momentum,
            risk_level="MEDIUM",
            timeframe=timeframe,
            generated_at=datetime.now()
        )]
    
    def _generate_fallback_regime(self, price_data: List[Dict]) -> MarketRegimeSignal:
        """폴백 시장 체제"""
        closes = [float(item['close']) for item in price_data[-30:]]
        volatility = np.std(closes) / np.mean(closes)
        
        if volatility > 0.03:
            regime = "HIGH_VOLATILITY"
            exposure = 0.5
        else:
            recent_trend = (closes[-1] - closes[-10]) / closes[-10]
            if recent_trend > 0.05:
                regime = "BULL"
                exposure = 0.8
            elif recent_trend < -0.05:
                regime = "BEAR"
                exposure = 0.3
            else:
                regime = "SIDEWAYS"
                exposure = 0.6
        
        return MarketRegimeSignal(
            regime=regime,
            strength=min(volatility * 10, 1.0),
            transition_probability=0.3,
            recommended_exposure=exposure
        )
    
    def _calculate_exposure_from_regime(self, regime: str) -> float:
        """체제별 노출도 계산"""
        regime_exposure = {
            'BULL_TREND': 0.9,
            'BEAR_TREND': 0.2,
            'SIDEWAYS': 0.6,
            'HIGH_VOLATILITY': 0.4,
            'LOW_VOLATILITY': 0.7
        }
        return regime_exposure.get(regime, 0.6)
    
    def _get_regime_multiplier(self, regime: str) -> float:
        """체제별 신호 승수"""
        multipliers = {
            'BULL_TREND': 1.2,
            'BEAR_TREND': 0.7,
            'SIDEWAYS': 0.9,
            'HIGH_VOLATILITY': 0.8,
            'LOW_VOLATILITY': 1.1
        }
        return multipliers.get(regime, 1.0)
    
    def _calculate_momentum_score(self, price_data: List[Dict]) -> float:
        """모멘텀 점수 계산"""
        closes = [float(item['close']) for item in price_data]
        if len(closes) < self.momentum_period:
            return 0.0
        
        current_price = closes[-1]
        past_price = closes[-self.momentum_period]
        return (current_price - past_price) / past_price
    
    # 기술적 지표 계산 메서드들
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI 계산"""
        deltas = np.diff(prices)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.convolve(gain, np.ones(period), 'valid') / period
        avg_loss = np.convolve(loss, np.ones(period), 'valid') / period
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray, fast=12, slow=26, signal=9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD 계산"""
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        macd_signal = self._calculate_ema(macd_line, signal)
        macd_histogram = macd_line - macd_signal
        return macd_line, macd_signal, macd_histogram
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """EMA 계산"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """볼린저 밴드 계산"""
        sma = np.convolve(prices, np.ones(period), 'valid') / period
        std = np.array([np.std(prices[i-period+1:i+1]) for i in range(period-1, len(prices))])
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    def _calculate_vwap(self, prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """VWAP 계산"""
        typical_price = prices  # 단순화
        vwap = np.cumsum(typical_price * volumes) / np.cumsum(volumes)
        return vwap
    
    # 모멘텀 점수 계산 메서드들
    def _rsi_momentum_score(self, rsi: float) -> float:
        """RSI 기반 모멘텀 점수"""
        if rsi > 70:
            return -0.5  # 과매수
        elif rsi < 30:
            return 0.5   # 과매도
        elif rsi > 50:
            return (rsi - 50) / 50
        else:
            return (rsi - 50) / 50
    
    def _macd_momentum_score(self, macd: float, signal: float, histogram: float) -> float:
        """MACD 기반 모멘텀 점수"""
        if macd > signal and histogram > 0:
            return 0.7
        elif macd < signal and histogram < 0:
            return -0.7
        else:
            return 0.0
    
    def _bb_momentum_score(self, price: float, upper: float, middle: float, lower: float) -> float:
        """볼린저 밴드 기반 점수"""
        if price > upper:
            return -0.3  # 과매수
        elif price < lower:
            return 0.3   # 과매도
        elif price > middle:
            return 0.2
        else:
            return -0.2
    
    def _vwap_momentum_score(self, price: float, vwap: float) -> float:
        """VWAP 기반 점수"""
        ratio = (price - vwap) / vwap
        return np.tanh(ratio * 10) * 0.5  # -0.5 to 0.5
    
    def _price_momentum_score(self, prices: np.ndarray) -> float:
        """가격 모멘텀 점수"""
        if len(prices) < 10:
            return 0.0
        
        short_momentum = (prices[-1] - prices[-5]) / prices[-5]
        long_momentum = (prices[-1] - prices[-10]) / prices[-10]
        
        return (short_momentum * 0.6 + long_momentum * 0.4) * 2  # 증폭