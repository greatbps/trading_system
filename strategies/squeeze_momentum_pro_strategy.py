#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_system/strategies/squeeze_momentum_pro_strategy.py

Squeeze Momentum Pro Strategy
"""

from .base_strategy import BaseStrategy
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class SqueezeMomentumProStrategy(BaseStrategy):
    """
    Identifies periods of low volatility (a "squeeze") and trades the subsequent breakout.
    - Squeeze Condition: Bollinger Bands go inside Keltner Channels.
    - Signal: When the squeeze is released, a signal is generated based on momentum direction.
    """

    def __init__(self, config):
        super().__init__(config)
        self.name = "SqueezeMomentumProStrategy"
        self.params = {
            'bb_period': 20,          # Bollinger Bands period
            'bb_std_dev': 2.0,      # Bollinger Bands standard deviation
            'kc_period': 20,          # Keltner Channels period
            'kc_atr_multiplier': 1.5, # Keltner Channels ATR multiplier
            'momentum_period': 12,    # Momentum Oscillator period
            'min_data_period': 30     # Minimum data points needed
        }
        self.logger.info("📈 Squeeze Momentum Pro 전략 초기화 완료")

    async def generate_signals(self, stock_data: Any, analysis_result: Dict, price_data: List[Dict] = None) -> Dict[str, Any]:
        """Generates trading signals based on the Squeeze Momentum Pro strategy."""
        try:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            
            if not price_data or len(price_data) < self.params['min_data_period']:
                self.logger.warning(f"⚠️ {symbol} 데이터 부족 - 필요: {self.params['min_data_period']}개, 보유: {len(price_data) if price_data else 0}개")
                return self._create_empty_signal()

            self.logger.info(f"📊 {symbol} Squeeze Momentum Pro 신호 생성 중...")
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)

            # 1. Calculate indicators
            df = self._calculate_indicators(df)

            # 2. Identify squeeze and fire conditions
            squeeze_fired, momentum_direction = self._get_squeeze_fire_condition(df)

            # 3. Generate signal and score
            if squeeze_fired:
                score = 75 if momentum_direction == 'BULLISH' else 25
                signal_type = "BUY" if momentum_direction == 'BULLISH' else "SELL"
                action = signal_type
                confidence = 0.75
                risk_level = "MEDIUM"
                details = {'squeeze_fired': True, 'momentum_direction': momentum_direction}
            else:
                score = 50
                signal_type = "HOLD"
                action = "HOLD"
                confidence = 0.5
                risk_level = "LOW"
                details = {'squeeze_fired': False, 'squeeze_on': df['squeeze_on'].iloc[-1]}

            return {
                'signal_strength': round(score, 1),
                'signal_type': signal_type,
                'action': action,
                'confidence': confidence,
                'details': details,
                'risk_level': risk_level,
                'timestamp': pd.Timestamp.now().isoformat()
            }

        except Exception as e:
            symbol = getattr(stock_data, 'symbol', 'UNKNOWN')
            self.logger.error(f"❌ {symbol} Squeeze Momentum Pro 신호 생성 실패: {e}", exc_info=True)
            return self._create_empty_signal()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Bollinger Bands
        bb_period = self.params['bb_period']
        bb_std_dev = self.params['bb_std_dev']
        df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * bb_std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * bb_std_dev)

        # Keltner Channels
        kc_period = self.params['kc_period']
        kc_atr_multiplier = self.params['kc_atr_multiplier']
        tr1 = pd.DataFrame(df['high'] - df['low'])
        tr2 = pd.DataFrame(abs(df['high'] - df['close'].shift()))
        tr3 = pd.DataFrame(abs(df['low'] - df['close'].shift()))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.ewm(span=kc_period, adjust=False).mean()
        df['kc_middle'] = df['close'].ewm(span=kc_period, adjust=False).mean()
        df['kc_upper'] = df['kc_middle'] + (df['atr'] * kc_atr_multiplier)
        df['kc_lower'] = df['kc_middle'] - (df['atr'] * kc_atr_multiplier)

        # Squeeze Condition
        df['squeeze_on'] = (df['bb_lower'] > df['kc_lower']) & (df['bb_upper'] < df['kc_upper'])

        # Momentum Oscillator
        momentum_period = self.params['momentum_period']
        df['momentum'] = df['close'] - df['close'].rolling(window=momentum_period).mean()
        
        return df

    def _get_squeeze_fire_condition(self, df: pd.DataFrame) -> tuple[bool, str]:
        if len(df) < 2:
            return False, 'NEUTRAL'

        squeeze_just_released = df['squeeze_on'].iloc[-2] and not df['squeeze_on'].iloc[-1]
        
        if squeeze_just_released:
            momentum_value = df['momentum'].iloc[-1]
            if momentum_value > 0:
                return True, 'BULLISH'
            elif momentum_value < 0:
                return True, 'BEARISH'
        
        return False, 'NEUTRAL'

    def _create_empty_signal(self) -> Dict[str, Any]:
        """Creates a neutral signal when analysis cannot be performed."""
        return {
            'signal_strength': 50.0,
            'signal_type': "HOLD",
            'action': "HOLD",
            'confidence': 0.5,
            'details': {'error': 'Insufficient data or calculation error'},
            'risk_level': "UNKNOWN",
            'timestamp': pd.Timestamp.now().isoformat()
        }
