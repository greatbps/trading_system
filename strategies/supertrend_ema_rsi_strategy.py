#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/supertrend_ema_rsi_strategy.py

Supertrend + EMA + RSI 조합 전략
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

from strategies.base_strategy import BaseStrategy

class SupertrendEmaRsiStrategy(BaseStrategy):
    """Supertrend + EMA + RSI 조합 전략"""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = "SupertrendEmaRsiStrategy"
        
        # 한국 시장 최적화 파라미터
        self.params = {
            'supertrend_period': 10,
            'supertrend_multiplier': 2.5,
            'ema_short': 20,
            'ema_long': 60,
            'rsi_period': 14,
            'rsi_threshold': 55
        }
    
    async def generate_signals(self, stock_data: Any, analysis_result: Dict) -> Dict[str, Any]:
        """매매 신호 생성"""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            
            # 차트 데이터 가져오기 (실제로는 데이터 수집기에서)
            chart_data = await self._get_chart_data(symbol)
            
            if not chart_data or len(chart_data) < self.params['ema_long']:
                return self._create_empty_signal()
            
            # DataFrame 변환
            df = pd.DataFrame(chart_data)
            df = self._ensure_numeric_columns(df)
            
            # 지표 계산
            supertrend_data = self._calculate_supertrend(df)
            ema_data = self._calculate_ema(df)
            rsi_data = self._calculate_rsi(df)
            
            # 신호 생성
            signal = self._generate_combined_signal(supertrend_data, ema_data, rsi_data, stock_data)
            
            return signal
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 신호 생성 실패: {e}")
            return self._create_empty_signal()
    
    def _calculate_supertrend(self, df: pd.DataFrame) -> Dict:
        """Supertrend 계산"""
        period = self.params['supertrend_period']
        multiplier = self.params['supertrend_multiplier']
        
        # True Range 계산
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(period).mean()
        
        # Basic Bands
        hl2 = (df['high'] + df['low']) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        # Supertrend 계산
        supertrend = [np.nan] * len(df)
        direction = [True] * len(df)  # True: 상승, False: 하락
        
        for i in range(period, len(df)):
            if df['close'].iloc[i] <= lower_band.iloc[i-1]:
                direction[i] = False
            elif df['close'].iloc[i] >= upper_band.iloc[i-1]:
                direction[i] = True
            else:
                direction[i] = direction[i-1]
            
            supertrend[i] = lower_band.iloc[i] if direction[i] else upper_band.iloc[i]
        
        current_supertrend = supertrend[-1]
        current_direction = direction[-1]
        current_price = df['close'].iloc[-1]
        
        return {
            'supertrend_value': current_supertrend,
            'direction': current_direction,
            'signal_strength': self._calculate_supertrend_strength(current_price, current_supertrend, current_direction)
        }
    
    def _calculate_ema(self, df: pd.DataFrame) -> Dict:
        """EMA 계산"""
        ema_short = df['close'].ewm(span=self.params['ema_short']).mean()
        ema_long = df['close'].ewm(span=self.params['ema_long']).mean()
        
        current_short = ema_short.iloc[-1]
        current_long = ema_long.iloc[-1]
        prev_short = ema_short.iloc[-2]
        prev_long = ema_long.iloc[-2]
        
        # 골든크로스/데드크로스 확인
        golden_cross = current_short > current_long and prev_short <= prev_long
        dead_cross = current_short < current_long and prev_short >= prev_long
        
        return {
            'ema_short': current_short,
            'ema_long': current_long,
            'golden_cross': golden_cross,
            'dead_cross': dead_cross,
            'ema_bullish': current_short > current_long,
            'signal_strength': self._calculate_ema_strength(current_short, current_long, golden_cross)
        }
    
    def _calculate_rsi(self, df: pd.DataFrame) -> Dict:
        """RSI 계산"""
        period = self.params['rsi_period']
        
        delta = df['close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(window=period).mean()
        avg_loss = pd.Series(loss).rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        
        return {
            'rsi_value': current_rsi,
            'rsi_bullish': current_rsi > self.params['rsi_threshold'],
            'signal_strength': self._calculate_rsi_strength(current_rsi)
        }
    
    def _generate_combined_signal(self, supertrend_data: Dict, ema_data: Dict, 
                                rsi_data: Dict, stock_data: Any) -> Dict[str, Any]:
        """조합 신호 생성"""
        
        # 매수 조건: 모든 조건 만족
        supertrend_bullish = supertrend_data['direction']
        ema_bullish = ema_data['ema_bullish']
        rsi_bullish = rsi_data['rsi_bullish']
        
        buy_signal = supertrend_bullish and ema_bullish and rsi_bullish
        
        # 신호 강도 계산
        signal_strength = (
            supertrend_data['signal_strength'] * 0.4 +
            ema_data['signal_strength'] * 0.3 +
            rsi_data['signal_strength'] * 0.3
        )
        
        # 신호 타입 결정
        if buy_signal and signal_strength >= 75:
            signal_type = "STRONG_BUY"
            action = "BUY"
        elif buy_signal and signal_strength >= 60:
            signal_type = "BUY"
            action = "BUY"
        elif not supertrend_bullish or not ema_bullish:
            signal_type = "SELL"
            action = "SELL"
        else:
            signal_type = "HOLD"
            action = "HOLD"
        
        return {
            'signal_strength': round(signal_strength, 1),
            'signal_type': signal_type,
            'action': action,
            'confidence': min(1.0, signal_strength / 100),
            'details': {
                'supertrend': supertrend_data,
                'ema': ema_data,
                'rsi': rsi_data
            },
            'risk_level': self._assess_risk_level(signal_strength, stock_data),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_supertrend_strength(self, price: float, supertrend: float, direction: bool) -> float:
        """Supertrend 신호 강도 계산"""
        if np.isnan(supertrend):
            return 50.0
        
        distance_ratio = abs(price - supertrend) / supertrend
        
        if direction:  # 상승 추세
            return min(100, 60 + (distance_ratio * 1000))
        else:  # 하락 추세
            return max(0, 40 - (distance_ratio * 1000))
    
    def _calculate_ema_strength(self, ema_short: float, ema_long: float, golden_cross: bool) -> float:
        """EMA 신호 강도 계산"""
        gap_ratio = (ema_short - ema_long) / ema_long
        
        base_strength = 50 + (gap_ratio * 500)  # 격차에 따른 기본 강도
        
        if golden_cross:
            base_strength += 20  # 골든크로스 보너스
        
        return max(0, min(100, base_strength))
    
    def _calculate_rsi_strength(self, rsi: float) -> float:
        """RSI 신호 강도 계산"""
        if rsi > 70:
            return max(0, 100 - (rsi - 70) * 2)  # 과매수 페널티
        elif rsi < 30:
            return max(0, rsi)  # 과매도
        else:
            return min(100, rsi + 20)  # 정상 범위
    
    def _assess_risk_level(self, signal_strength: float, stock_data: Any) -> str:
        """리스크 레벨 평가"""
        risk_factors = 0
        
        # 신호 강도가 극단적이면 위험
        if signal_strength > 90 or signal_strength < 10:
            risk_factors += 1
        
        # 기타 리스크 요소들 (기존 momentum_strategy 로직 활용)
        change_rate = getattr(stock_data, 'change_rate', 0)
        if abs(change_rate) > 5:
            risk_factors += 1
        
        if risk_factors >= 2:
            return "HIGH"
        elif risk_factors >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _ensure_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """숫자형 컬럼 보장"""
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    
    async def _get_chart_data(self, symbol: str) -> List[Dict]:
        """차트 데이터 조회 (임시 구현)"""
        # 실제로는 데이터 수집기에서 가져옴
        # 더미 데이터 대신 빈 리스트 반환
        return []
    
    def _create_empty_signal(self) -> Dict[str, Any]:
        """빈 신호 생성"""
        return {
            'signal_strength': 50.0,
            'signal_type': 'HOLD',
            'action': 'HOLD',
            'confidence': 0.5,
            'details': {},
            'risk_level': 'MEDIUM',
            'timestamp': datetime.now().isoformat()
        }